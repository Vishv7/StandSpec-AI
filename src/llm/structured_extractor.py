"""
Bounded Structured Requirement Extractor — StandSpec AI (Phase P1-C.6)
Extracts structured tender clauses using bounded LLM assist with:
1. Strict JSON schema validation against schemas/llm_extraction.schema.json.
2. Verbatim character-span verification (rejecting hallucinated spans).
3. Deterministic NLP/regex extraction fallback.
4. Mode attribution: DETERMINISTIC, LLM_ASSISTED, DETERMINISTIC_FALLBACK, LLM_UNAVAILABLE.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional

import jsonschema

from src.extraction.requirement_extractor import RequirementExtractor
from src.llm.provider import BaseLLMProvider, DisabledLLMProvider, get_llm_provider
from src.query.open_world_contract import OpenWorldQuery


SCHEMA_PATH = Path(__file__).resolve().parent.parent.parent / "schemas" / "llm_extraction.schema.json"


class BoundedStructuredExtractor:
    """
    Bounded Requirement Extractor with verbatim span verification.
    Attempts structured LLM extraction with JSON schema validation.
    Always falls back gracefully to the deterministic extractor.
    Supports explicit execution modes:
      - DETERMINISTIC_ONLY
      - LLM_ASSISTED
      - LLM_PROVIDER_UNAVAILABLE
      - LLM_DISABLED_FALLBACK
      - LLM_ERROR_FALLBACK
      - DETERMINISTIC_FALLBACK
      - LLM_UNAVAILABLE
    """

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        default_mode: Optional[str] = None,
    ):
        self.llm_provider = llm_provider
        self.default_mode = default_mode
        self.deterministic_extractor = RequirementExtractor()
        self._schema = None

    def _get_schema(self) -> dict:
        if self._schema is None:
            if SCHEMA_PATH.exists():
                with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                    self._schema = json.load(f)
            else:
                self._schema = {}
        return self._schema

    def _verify_and_filter_grounding(self, query_text: str, candidate_fields: dict) -> dict:
        """
        Validates character spans against the raw query text.
        Rejects ungrounded or hallucinated extractions.
        """
        grounded = {}
        for key, field in candidate_fields.items():
            if isinstance(field, str):
                field_val = field.strip()
                if not field_val:
                    continue
                # Ground against query_text
                idx = query_text.lower().find(field_val.lower())
                if idx >= 0:
                    grounded[key] = {
                        "value": field_val,
                        "evidence_text": query_text[idx:idx + len(field_val)],
                        "start_char": idx,
                        "end_char": idx + len(field_val),
                        "confidence": 0.85,
                    }
                else:
                    # REJECT: Verbatim value substring does not exist in query_text.
                    # Weak token overlap fallback is strictly prohibited.
                    continue
                continue

            if not isinstance(field, dict):
                continue

            val = field.get("value")
            ev_text = field.get("evidence_text")
            start = field.get("start_char")
            end = field.get("end_char")
            conf = field.get("confidence", 0.0)

            if not val or not ev_text:
                continue

            # 1. Exact span match check
            if (
                isinstance(start, int)
                and isinstance(end, int)
                and 0 <= start < end <= len(query_text)
                and query_text[start:end] == ev_text
            ):
                grounded[key] = {
                    "value": str(val).strip(),
                    "evidence_text": ev_text,
                    "start_char": start,
                    "end_char": end,
                    "confidence": float(conf),
                }
            # 2. Substring fallback offset re-alignment
            elif ev_text in query_text:
                found_idx = query_text.find(ev_text)
                grounded[key] = {
                    "value": str(val).strip(),
                    "evidence_text": ev_text,
                    "start_char": found_idx,
                    "end_char": found_idx + len(ev_text),
                    "confidence": float(conf),
                }
            else:
                # REJECT: Verbatim evidence text does not exist in query_text!
                continue

        return grounded

    def extract(
        self, query_text: str, query_id: str = "Q_AUTO_001", mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract requirements from tender text using bounded LLM assist.
        Returns a normalized requirement object conforming to schemas/normalized_requirement.schema.json.
        """
        target_mode = mode or self.default_mode

        # 1. Explicit deterministic-only mode
        if target_mode == "DETERMINISTIC_ONLY":
            det_res = self.deterministic_extractor.extract(query_text, query_id=query_id)
            det_res["extractor_mode"] = "DETERMINISTIC_ONLY"
            return det_res

        # 2. Check LLM provider availability
        if not self.llm_provider or not self.llm_provider.is_available():
            det_res = self.deterministic_extractor.extract(query_text, query_id=query_id)
            if target_mode in ("LLM_PROVIDER_UNAVAILABLE", "LLM_DISABLED_FALLBACK", "LLM_UNAVAILABLE"):
                det_res["extractor_mode"] = target_mode
            elif isinstance(self.llm_provider, DisabledLLMProvider) or getattr(self.llm_provider, "reason", None) == "LLM_DISABLED":
                det_res["extractor_mode"] = "LLM_DISABLED_FALLBACK"
            else:
                det_res["extractor_mode"] = "LLM_UNAVAILABLE"
            return det_res

        prompt = (
            "Extract structured technical procurement requirements from this Indian government tender clause.\n"
            f"Tender Clause: \"{query_text}\"\n\n"
            "For each attribute present, provide an object with:\n"
            "- \"value\": the technical value\n"
            "- \"evidence_text\": the EXACT verbatim substring from the clause proving this\n"
            "- \"start_char\": 0-indexed start character offset of evidence_text in the clause\n"
            "- \"end_char\": 0-indexed end character offset of evidence_text in the clause\n"
            "- \"confidence\": confidence between 0.0 and 1.0\n\n"
            "Supported attributes: product, material, grade, dimensions, voltage, capacity, application, installation.\n"
            "If an attribute is not present, omit it or set it to null."
        )

        try:
            raw_json_str = self.llm_provider.generate(prompt, json_mode=True)
            extracted_dict = json.loads(raw_json_str)

            # JSON Schema Validation
            schema = self._get_schema()
            if schema:
                jsonschema.validate(instance=extracted_dict, schema=schema)

            # Grounding and span verification
            grounded_fields = self._verify_and_filter_grounding(query_text, extracted_dict)

            # Deterministic base
            det_result = self.deterministic_extractor.extract(query_text, query_id=query_id)
            reqs = det_result.get("requirements", {})

            # Safely merge verified grounded fields into deterministic requirements
            for key, field_info in grounded_fields.items():
                if key not in reqs or reqs[key] is None or reqs[key].get("confidence", 0.0) < field_info["confidence"]:
                    reqs[key] = {
                        "value": field_info["value"],
                        "confidence": field_info["confidence"],
                        "source_span": field_info["evidence_text"],
                        "start_char": field_info["start_char"],
                        "end_char": field_info["end_char"],
                        "normalization": field_info["value"],
                    }

            # Update product status if newly grounded
            if reqs.get("product") and reqs["product"].get("value"):
                det_result["product_status"] = "EXTRACTED"

            # Re-run missing discriminators and query sufficiency on merged requirements
            missing_discriminators = self.deterministic_extractor._identify_missing_discriminators(
                reqs, raw_text=query_text
            )
            query_sufficiency = self.deterministic_extractor._evaluate_query_sufficiency(
                query_text, reqs, missing_discriminators
            )
            contradictions = self.deterministic_extractor._detect_contradictions(query_text, reqs)
            if contradictions:
                query_sufficiency["contradictions"] = contradictions

            det_result["requirements"] = reqs
            det_result["missing_discriminators"] = missing_discriminators
            det_result["query_sufficiency"] = query_sufficiency
            det_result["contradictions"] = contradictions
            det_result["extractor_mode"] = "LLM_ASSISTED"
            return det_result

        except Exception:
            # Deterministic fallback on any error (parse error, schema failure, timeout, ungrounded rejection)
            fallback_res = self.deterministic_extractor.extract(query_text, query_id=query_id)
            if target_mode == "LLM_ERROR_FALLBACK":
                fallback_res["extractor_mode"] = "LLM_ERROR_FALLBACK"
            else:
                fallback_res["extractor_mode"] = "DETERMINISTIC_FALLBACK"
            return fallback_res

    def extract_to_open_world_query(
        self, query_text: str, query_id: str = "Q_AUTO_001", mode: Optional[str] = None
    ) -> OpenWorldQuery:
        """
        Extracts tender text and reconciles it into the canonical OpenWorldQuery contract.
        Ensures strict separation between raw text, extracted requirements, and query sufficiency.
        """
        norm = self.extract(query_text, query_id=query_id, mode=mode)
        reqs = norm.get("requirements", {})
        proc_obj = reqs.get("product", {}).get("value") if isinstance(reqs.get("product"), dict) else None

        suff = norm.get("query_sufficiency", {})
        status = suff.get("status", "SUFFICIENT")

        return OpenWorldQuery(
            raw_text=query_text,
            language=norm.get("language_detection", {}).get("detected", "en"),
            procurement_object=proc_obj,
            object_type="PRODUCT",
            technical_intent="SUPPLY",
            requirements=reqs,
            constraints=norm.get("constraints", []),
            requested_designations=norm.get("requested_designations", []),
            application_context=norm.get("application_context"),
            query_sufficiency=status,
            contradictions=norm.get("contradictions", []),
            metadata={
                "query_id": query_id,
                "extractor_mode": norm.get("extractor_mode"),
            },
        )

