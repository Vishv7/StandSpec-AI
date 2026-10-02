"""
System Integrity Checker — StandSpec AI (Phase 17, Checkpoint 7)
PS 26108 §18: Release-gate system integrity validation.

Performs a comprehensive pre-release integrity check across all modules:
  1. Module import verification — all Checkpoint 1-6 modules loadable
  2. Cross-module contract verification — interfaces are compatible
  3. Version consistency — all version tokens agree
  4. Component registry — enumerates all hardened components
  5. Release readiness gate — pass/fail decision for release

This is the FINAL gate before a release candidate can be shipped.
"""

import importlib
import sys
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class IntegrityCheck:
    """A single integrity check result."""
    check_id: str
    component: str
    status: str  # PASS, FAIL, SKIP
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class IntegrityReport:
    """Complete integrity check report."""
    timestamp: str = ""
    checks: List[IntegrityCheck] = field(default_factory=list)
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    is_release_ready: bool = False

    def add(self, check: IntegrityCheck):
        self.checks.append(check)
        self.total += 1
        if check.status == "PASS":
            self.passed += 1
        elif check.status == "FAIL":
            self.failed += 1
        elif check.status == "SKIP":
            self.skipped += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_checks": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "is_release_ready": self.is_release_ready,
            "checks": [
                {
                    "check_id": c.check_id,
                    "component": c.component,
                    "status": c.status,
                    "message": c.message,
                }
                for c in self.checks
            ],
        }


# ── Module Registry ──
# All modules that must be importable for a valid release

CHECKPOINT_MODULES = {
    "CP1": {
        "name": "Evidence + Lifecycle + Regulatory",
        "modules": [
            "src.recommendation.evidence_bundle",
            "src.recommendation.lifecycle_gate",
            "src.recommendation.regulatory_gate",
        ],
    },
    "CP2": {
        "name": "Material + Product + Applicability",
        "modules": [
            "src.recommendation.applicability.material_concepts",
            "src.recommendation.applicability.product_concepts",
            "src.recommendation.applicability.discriminator_policy",
            "src.recommendation.applicability.core",
        ],
    },
    "CP3": {
        "name": "Retrieval + Reranking",
        "modules": [
            "src.retrieval.retrieval_diagnostics",
            "src.retrieval.fusion",
            "src.evaluation.error_taxonomy",
        ],
    },
    "CP4": {
        "name": "Decision + Abstention + Explanation",
        "modules": [
            "src.recommendation.decision_state_machine",
            "src.calibration.policy",
            "src.recommendation.explanation_templates",
        ],
    },
    "CP5": {
        "name": "Multilingual + Agent Layer",
        "modules": [
            "src.extraction.multilingual_normalizer",
            "src.agent.safety_invariants",
        ],
    },
    "CP6": {
        "name": "Evaluation + Benchmarking",
        "modules": [
            "src.evaluation.benchmark_validator",
            "src.evaluation.benchmark_integrity",
            "src.evaluation.metrics",
        ],
    },
}

CORE_MODULES = [
    "src.recommendation.engine",
    "src.extraction.requirement_extractor",
    "src.extraction.normalizer",
    "src.retrieval.bm25_retriever",
    "src.retrieval.dense_retriever",
    "src.retrieval.graph_expansion",
    "src.retrieval.cross_encoder",
    "src.recommendation.role_classifier",
    "src.recommendation.consistency_gate",
    "src.version",
]


def check_module_imports(report: IntegrityReport):
    """Verify all checkpoint modules can be imported."""
    for cp_id, cp_info in CHECKPOINT_MODULES.items():
        for mod_path in cp_info["modules"]:
            try:
                importlib.import_module(mod_path)
                report.add(IntegrityCheck(
                    check_id=f"IMPORT-{cp_id}",
                    component=mod_path,
                    status="PASS",
                    message=f"Module {mod_path} imported successfully",
                ))
            except Exception as e:
                report.add(IntegrityCheck(
                    check_id=f"IMPORT-{cp_id}",
                    component=mod_path,
                    status="FAIL",
                    message=f"Module {mod_path} import failed: {e}",
                ))

    for mod_path in CORE_MODULES:
        try:
            importlib.import_module(mod_path)
            report.add(IntegrityCheck(
                check_id="IMPORT-CORE",
                component=mod_path,
                status="PASS",
                message=f"Core module {mod_path} imported successfully",
            ))
        except Exception as e:
            report.add(IntegrityCheck(
                check_id="IMPORT-CORE",
                component=mod_path,
                status="FAIL",
                message=f"Core module {mod_path} import failed: {e}",
            ))


def check_version_consistency(report: IntegrityReport):
    """Verify version tokens are consistent."""
    try:
        from src.version import ENGINE_VERSION, RELEASE_ID
        report.add(IntegrityCheck(
            check_id="VERSION-ENGINE",
            component="src.version",
            status="PASS",
            message=f"Engine version: {ENGINE_VERSION}, Release: {RELEASE_ID}",
            details={"engine_version": ENGINE_VERSION, "release_id": RELEASE_ID},
        ))

        # Verify RELEASE_ID contains ENGINE_VERSION
        version_digits = ENGINE_VERSION.replace(".", "_")
        if version_digits not in RELEASE_ID.replace(".", "_"):
            report.add(IntegrityCheck(
                check_id="VERSION-CONSISTENCY",
                component="src.version",
                status="FAIL",
                message=f"RELEASE_ID '{RELEASE_ID}' doesn't contain ENGINE_VERSION '{ENGINE_VERSION}'",
            ))
        else:
            report.add(IntegrityCheck(
                check_id="VERSION-CONSISTENCY",
                component="src.version",
                status="PASS",
                message="RELEASE_ID and ENGINE_VERSION are consistent",
            ))
    except Exception as e:
        report.add(IntegrityCheck(
            check_id="VERSION-ENGINE",
            component="src.version",
            status="FAIL",
            message=f"Version check failed: {e}",
        ))


def check_decision_state_contract(report: IntegrityReport):
    """Verify decision state machine contract."""
    try:
        from src.recommendation.decision_state_machine import (
            DecisionState, DECISION_STATE_SPECS, VALID_TRANSITIONS,
        )

        # All terminal states must have specs
        terminal = [s for s in DecisionState if s != DecisionState.PROCESSING]
        all_have_specs = all(s.value in DECISION_STATE_SPECS for s in terminal)

        if all_have_specs:
            report.add(IntegrityCheck(
                check_id="CONTRACT-DECISION",
                component="decision_state_machine",
                status="PASS",
                message=f"All {len(terminal)} terminal states have specifications",
            ))
        else:
            missing = [s.value for s in terminal if s.value not in DECISION_STATE_SPECS]
            report.add(IntegrityCheck(
                check_id="CONTRACT-DECISION",
                component="decision_state_machine",
                status="FAIL",
                message=f"Missing specs for: {missing}",
            ))

        # All states must have transitions defined
        all_have_transitions = all(s.value in VALID_TRANSITIONS for s in DecisionState)
        if all_have_transitions:
            report.add(IntegrityCheck(
                check_id="CONTRACT-TRANSITIONS",
                component="decision_state_machine",
                status="PASS",
                message="All states have transition rules defined",
            ))
        else:
            report.add(IntegrityCheck(
                check_id="CONTRACT-TRANSITIONS",
                component="decision_state_machine",
                status="FAIL",
                message="Some states missing transition rules",
            ))

    except Exception as e:
        report.add(IntegrityCheck(
            check_id="CONTRACT-DECISION",
            component="decision_state_machine",
            status="FAIL",
            message=f"Decision state contract check failed: {e}",
        ))


def check_error_taxonomy_completeness(report: IntegrityReport):
    """Verify error taxonomy has all labels."""
    try:
        from src.evaluation.error_taxonomy import ErrorLabel
        labels = [e.value for e in ErrorLabel]

        # Must have retrieval failure labels from Phase 7
        phase7_labels = [
            "RETRIEVAL_MISS_SEMANTIC_GAP", "RETRIEVAL_MISS_BOTH_CHANNELS",
            "RETRIEVAL_LOW_FUSION_RANK", "RETRIEVAL_CROSS_ENCODER_DISPLACEMENT",
            "RETRIEVAL_GRAPH_EXPANSION_MISS",
        ]
        missing = [l for l in phase7_labels if l not in labels]

        if not missing:
            report.add(IntegrityCheck(
                check_id="TAXONOMY-PHASE7",
                component="error_taxonomy",
                status="PASS",
                message=f"All Phase 7 retrieval labels present ({len(labels)} total labels)",
            ))
        else:
            report.add(IntegrityCheck(
                check_id="TAXONOMY-PHASE7",
                component="error_taxonomy",
                status="FAIL",
                message=f"Missing Phase 7 labels: {missing}",
            ))
    except Exception as e:
        report.add(IntegrityCheck(
            check_id="TAXONOMY-PHASE7",
            component="error_taxonomy",
            status="FAIL",
            message=f"Error taxonomy check failed: {e}",
        ))


def check_explanation_templates(report: IntegrityReport):
    """Verify explanation templates cover all decision states."""
    try:
        from src.recommendation.explanation_templates import generate_explanation

        states = [
            "PRIMARY_RECOMMENDATION_AVAILABLE",
            "CONDITIONAL_RECOMMENDATION",
            "MULTIPLE_POSSIBLE_STANDARDS",
            "EXPERT_REVIEW_REQUIRED",
            "NO_CONFIDENT_MATCH",
            "INSUFFICIENT_INFORMATION",
            "OUTSIDE_PROTOTYPE_COVERAGE",
            "CONTRADICTORY_SPECIFICATIONS",
        ]

        for state in states:
            result = {
                "decision_state": state,
                "primary_recommendation": {"standard_designation": "IS 4984:2016", "title": "Test", "calibrated_confidence": 0.5, "applicability": {}, "lifecycle": {}, "regulatory": {}} if state in ("PRIMARY_RECOMMENDATION_AVAILABLE", "CONDITIONAL_RECOMMENDATION", "MULTIPLE_POSSIBLE_STANDARDS") else None,
                "review_candidate": {"designation": "IS 4984:2016"} if state == "EXPERT_REVIEW_REQUIRED" else None,
                "candidate_recommendations": [],
            }
            exp = generate_explanation(result)
            if exp.decision_state == state and exp.headline:
                report.add(IntegrityCheck(
                    check_id="TEMPLATE-COVERAGE",
                    component=f"explanation_templates.{state}",
                    status="PASS",
                    message=f"Template for {state} generates valid explanation",
                ))
            else:
                report.add(IntegrityCheck(
                    check_id="TEMPLATE-COVERAGE",
                    component=f"explanation_templates.{state}",
                    status="FAIL",
                    message=f"Template for {state} produced invalid output",
                ))
    except Exception as e:
        report.add(IntegrityCheck(
            check_id="TEMPLATE-COVERAGE",
            component="explanation_templates",
            status="FAIL",
            message=f"Explanation template check failed: {e}",
        ))


def run_integrity_check() -> IntegrityReport:
    """
    Run the full system integrity check.
    Returns an IntegrityReport with pass/fail gate decision.
    """
    report = IntegrityReport(
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # 1. Module imports
    check_module_imports(report)

    # 2. Version consistency
    check_version_consistency(report)

    # 3. Decision state contract
    check_decision_state_contract(report)

    # 4. Error taxonomy completeness
    check_error_taxonomy_completeness(report)

    # 5. Explanation template coverage
    check_explanation_templates(report)

    # Release readiness gate
    report.is_release_ready = (report.failed == 0)

    return report


def generate_component_registry() -> Dict[str, Any]:
    """
    Generate a registry of all hardened components across all checkpoints.
    Used for release manifest and audit trail.
    """
    registry = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoints": {},
    }

    for cp_id, cp_info in CHECKPOINT_MODULES.items():
        cp_entry = {
            "name": cp_info["name"],
            "modules": [],
        }
        for mod_path in cp_info["modules"]:
            mod_entry = {"module": mod_path, "importable": False}
            try:
                mod = importlib.import_module(mod_path)
                mod_entry["importable"] = True
                # Extract public classes/functions
                public = [name for name in dir(mod) if not name.startswith("_")]
                mod_entry["exports"] = public[:20]  # Cap for readability
            except Exception:
                pass
            cp_entry["modules"].append(mod_entry)

        registry["checkpoints"][cp_id] = cp_entry

    return registry
