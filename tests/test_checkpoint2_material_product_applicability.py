"""
Regression Tests for Checkpoint 2: Product / Material / Applicability Semantics
PS 26108 Phases 4-6.

Phase 4: Material Compatibility Layer
Phase 5: Product Family Matching
Phase 6: Required Discriminators
"""

import pytest
from src.recommendation.applicability.material_concepts import (
    resolve_material,
    resolve_material_compatibility,
    extract_material_from_text,
    MaterialMatchResult,
    MaterialFamily,
    get_material_family,
)
from src.recommendation.applicability.product_concepts import (
    resolve_base_product,
    build_product_signature,
    compare_products,
    detect_product_from_title,
    ProductSignature,
    PRODUCT_FAMILIES,
)
from src.recommendation.applicability.discriminator_policy import (
    get_discriminator_policy,
    get_mandatory_discriminators,
    evaluate_discriminator_coverage,
    DiscriminatorLevel,
)
from src.recommendation.applicability.state import AttributeStatus
from src.recommendation.applicability.core import GenericApplicabilityEngine
from src.recommendation.applicability.ced_registry import CEDRuleRegistry
from src.recommendation.applicability.etd_registry import ETDRuleRegistry


# ============================================================================
# Phase 4: Material Compatibility Layer
# ============================================================================

class TestMaterialResolution:
    """Tests for canonical material resolution from raw strings."""

    @pytest.mark.parametrize("raw,expected", [
        ("HDPE", "HDPE"),
        ("hdpe", "HDPE"),
        ("high density polyethylene", "HDPE"),
        ("PE-HD", "HDPE"),
        ("polyethylene", "HDPE"),
        ("PVC", "PVC"),
        ("polyvinyl chloride", "PVC"),
        ("uPVC", "UPVC"),
        ("unplasticized pvc", "UPVC"),
        ("XLPE", "XLPE"),
        ("crosslinked polyethylene", "XLPE"),
        ("cross-linked polyethylene", "XLPE"),
        ("cast iron", "CAST_IRON"),
        ("ductile iron", "DUCTILE_IRON"),
        ("DI", "DUCTILE_IRON"),
        ("copper", "COPPER"),
        ("aluminium", "ALUMINIUM"),
        ("aluminum", "ALUMINIUM"),
        ("tmt", "TMT_STEEL"),
        ("Fe 500D", "TMT_STEEL"),
        ("opc", "OPC"),
        ("portland cement", "OPC"),
    ])
    def test_resolve_material(self, raw, expected):
        result = resolve_material(raw)
        assert result == expected, f"resolve_material('{raw}') = {result}, expected {expected}"

    def test_resolve_unknown_material(self):
        assert resolve_material("unobtanium") is None
        assert resolve_material("") is None
        assert resolve_material(None) is None


class TestMaterialCompatibility:
    """Tests for concept-level material compatibility checks."""

    def test_hdpe_vs_cast_iron_is_mismatch(self):
        """HDPE pipe vs cast iron pipe → MISMATCH (polymer vs ferrous)."""
        result, reason = resolve_material_compatibility("HDPE", "cast iron")
        assert result == MaterialMatchResult.MISMATCH, f"Expected MISMATCH, got {result}: {reason}"

    def test_upvc_vs_cast_iron_is_mismatch(self):
        """uPVC vs cast iron → MISMATCH."""
        result, reason = resolve_material_compatibility("uPVC", "cast iron")
        assert result == MaterialMatchResult.MISMATCH

    def test_xlpe_vs_paper_insulated_is_mismatch(self):
        """XLPE cable vs paper-insulated cable → MISMATCH."""
        result, reason = resolve_material_compatibility("XLPE", "paper insulated")
        assert result == MaterialMatchResult.MISMATCH

    def test_aluminium_vs_copper_is_mismatch(self):
        """Aluminium conductor vs copper conductor → MISMATCH."""
        result, reason = resolve_material_compatibility("aluminium", "copper")
        assert result == MaterialMatchResult.MISMATCH

    def test_concrete_vs_pvc_is_mismatch(self):
        """Concrete vs PVC → MISMATCH (cementitious vs polymer)."""
        result, reason = resolve_material_compatibility("concrete", "PVC")
        assert result == MaterialMatchResult.MISMATCH

    def test_hdpe_vs_polyethylene_is_match(self):
        """HDPE query + 'polyethylene' scope → MATCH."""
        result, reason = resolve_material_compatibility("HDPE", "polyethylene")
        assert result == MaterialMatchResult.MATCH, f"Expected MATCH, got {result}: {reason}"

    def test_pvc_vs_pvc_is_match(self):
        """Same material → MATCH."""
        result, reason = resolve_material_compatibility("PVC", "PVC")
        assert result == MaterialMatchResult.MATCH

    def test_hdpe_vs_absent_material_is_unknown(self):
        """HDPE query + absent candidate material → UNKNOWN."""
        result, reason = resolve_material_compatibility("HDPE", "")
        assert result == MaterialMatchResult.UNKNOWN

    def test_steel_vs_nonferrous_is_mismatch(self):
        """Steel vs aluminium → MISMATCH (ferrous vs non-ferrous)."""
        result, reason = resolve_material_compatibility("mild steel", "aluminium")
        assert result == MaterialMatchResult.MISMATCH

    def test_ductile_iron_vs_cast_iron_is_mismatch(self):
        """DI vs CI → MISMATCH (distinct iron types)."""
        result, reason = resolve_material_compatibility("ductile iron", "cast iron")
        assert result == MaterialMatchResult.MISMATCH


class TestMaterialFamilies:
    """Tests for material family classification."""

    def test_hdpe_is_polymer(self):
        assert get_material_family("HDPE") == MaterialFamily.POLYMER

    def test_cast_iron_is_ferrous(self):
        assert get_material_family("CAST_IRON") == MaterialFamily.FERROUS_METAL

    def test_copper_is_nonferrous(self):
        assert get_material_family("COPPER") == MaterialFamily.NON_FERROUS_METAL

    def test_opc_is_cementitious(self):
        assert get_material_family("OPC") == MaterialFamily.CEMENTITIOUS

    def test_unknown_material(self):
        assert get_material_family("UNOBTANIUM") == MaterialFamily.UNKNOWN


class TestMaterialExtraction:
    """Tests for extracting material from title/scope text."""

    def test_extract_hdpe_from_title(self):
        result = extract_material_from_text("High Density Polyethylene Pipes for Water Supply")
        assert result == "HDPE"

    def test_extract_xlpe_from_title(self):
        result = extract_material_from_text("XLPE Insulated Power Cables")
        assert result == "XLPE"

    def test_extract_cast_iron_from_title(self):
        result = extract_material_from_text("Centrifugally Cast Iron Pipes for Water")
        assert result == "CAST_IRON"


# ============================================================================
# Phase 5: Product Family Matching
# ============================================================================

class TestProductResolution:
    """Tests for base product resolution from text."""

    @pytest.mark.parametrize("text,expected", [
        ("HDPE pipe for water supply", "pipe"),
        ("power cable 11 kV XLPE", "cable"),
        ("distribution transformer 100 kVA", "transformer"),
        ("gate valve 150mm", "valve"),
        ("static energy meter", "meter"),
        ("LED luminaire", "luminaire"),
        ("TMT rebar Fe 500D", "rebar"),
        ("overhead conductor ACSR", "conductor"),
        ("circuit breaker MCCB", "switchgear"),
    ])
    def test_resolve_base_product(self, text, expected):
        result = resolve_base_product(text)
        assert result == expected, f"resolve_base_product('{text}') = {result}, expected {expected}"


class TestProductFamilyMatching:
    """Tests for product family comparison."""

    def test_pipe_vs_fitting_is_mismatch(self):
        """Pipe vs pipe fitting → different families."""
        q = build_product_signature("HDPE pipe")
        c = build_product_signature("pipe fitting")
        result = compare_products(q, c)
        assert result.match_type == "MISMATCH", f"Expected MISMATCH: {result.reason}"

    def test_pipe_vs_valve_is_mismatch(self):
        """Pipe vs valve → different families."""
        q = build_product_signature("HDPE pressure pipe")
        c = build_product_signature("gate valve")
        result = compare_products(q, c)
        assert result.match_type == "MISMATCH", f"Expected MISMATCH: {result.reason}"

    def test_cable_vs_conductor_is_mismatch(self):
        """Cable vs overhead conductor → different families."""
        q = build_product_signature("XLPE power cable")
        c = build_product_signature("overhead conductor ACSR")
        result = compare_products(q, c)
        assert result.match_type == "MISMATCH", f"Expected MISMATCH: {result.reason}"

    def test_transformer_vs_switchgear_is_mismatch(self):
        """Transformer vs switchgear → different families."""
        q = build_product_signature("distribution transformer")
        c = build_product_signature("circuit breaker MCCB")
        result = compare_products(q, c)
        assert result.match_type == "MISMATCH", f"Expected MISMATCH: {result.reason}"

    def test_same_product_is_match(self):
        """Same product type → MATCH."""
        q = build_product_signature("XLPE power cable 11 kV")
        c = build_product_signature("power cable XLPE insulated")
        result = compare_products(q, c)
        assert result.match_type == "MATCH", f"Expected MATCH: {result.reason}"

    def test_pipe_same_base_is_match(self):
        """Same base product → MATCH."""
        q = build_product_signature("HDPE pipe for water")
        c = build_product_signature("polyethylene pipe for water supply")
        result = compare_products(q, c)
        assert result.match_type in ("MATCH", "RELATED"), f"Expected MATCH/RELATED: {result.reason}"

    def test_cable_vs_meter_is_mismatch(self):
        """Cable vs meter → different families."""
        q = build_product_signature("XLPE cable")
        c = build_product_signature("energy meter")
        result = compare_products(q, c)
        assert result.match_type == "MISMATCH"


class TestProductSignatureBuilding:
    """Tests for ProductSignature construction."""

    def test_pipe_signature_has_ced_domain(self):
        sig = build_product_signature("HDPE pipe")
        assert sig.domain == "CED"
        assert sig.base_product == "pipe"

    def test_cable_signature_has_etd_domain(self):
        sig = build_product_signature("XLPE power cable")
        assert sig.domain == "ETD"
        assert sig.base_product == "cable"

    def test_title_detection(self):
        sig = detect_product_from_title("Crosslinked Polyethylene Insulated Power Cables")
        assert sig is not None
        assert sig.base_product == "cable"


# ============================================================================
# Phase 6: Required Discriminators
# ============================================================================

class TestDiscriminatorPolicy:
    """Tests for product-family discriminator requirements."""

    def test_cable_mandatory_discriminators(self):
        mandatories = get_mandatory_discriminators("cable")
        assert "voltage" in mandatories
        assert "insulation" in mandatories

    def test_pipe_mandatory_discriminators(self):
        mandatories = get_mandatory_discriminators("pipe")
        assert "material" in mandatories
        assert "application" in mandatories

    def test_transformer_mandatory_discriminators(self):
        mandatories = get_mandatory_discriminators("transformer")
        assert "voltage_ratio" in mandatories

    def test_meter_mandatory_discriminators(self):
        mandatories = get_mandatory_discriminators("meter")
        assert "meter_type" in mandatories

    def test_unknown_product_has_no_policy(self):
        mandatories = get_mandatory_discriminators("spaceship")
        assert len(mandatories) == 0

    def test_coverage_evaluation_all_present(self):
        result = evaluate_discriminator_coverage("cable", {
            "voltage": "11 kV",
            "insulation": "XLPE",
            "conductor": "aluminium",
        })
        assert result["coverage_sufficient"] is True
        assert result["should_abstain"] is False
        assert len(result["mandatory_missing"]) == 0

    def test_coverage_evaluation_missing_mandatory(self):
        result = evaluate_discriminator_coverage("cable", {
            "conductor": "aluminium",
            # Missing: voltage, insulation
        })
        assert result["coverage_sufficient"] is False
        assert result["should_abstain"] is True
        assert "voltage" in result["mandatory_missing"]
        assert "insulation" in result["mandatory_missing"]

    def test_policy_exists_flag(self):
        result = evaluate_discriminator_coverage("cable", {})
        assert result["policy_exists"] is True

        result2 = evaluate_discriminator_coverage("spaceship", {})
        assert result2["policy_exists"] is False


# ============================================================================
# Integration: Material concepts with applicability engine
# ============================================================================

class TestApplicabilityMaterialIntegration:
    """Tests that material taxonomy is correctly integrated into the applicability engine."""

    @pytest.fixture
    def engine(self):
        e = GenericApplicabilityEngine()
        e.register(CEDRuleRegistry())
        e.register(ETDRuleRegistry())
        return e

    def test_hdpe_query_vs_cast_iron_standard(self, engine):
        """HDPE pipe query must never surface cast iron pipe standards with positive applicability."""
        candidate = {
            "designation": "IS 1536:2001",
            "title": "Centrifugally Cast (Spun) Iron Pressure Pipes for Water, Gas and Sewage",
            "scope": "This standard covers centrifugally cast (spun) iron pressure pipes for use in water supply, gas distribution and sewage.",
            "is_hydrated": True,
            "recommendation_ready": True,
        }
        requirements = {
            "requirements": {
                "product": {"value": "HDPE pipe"},
                "material": {"value": "HDPE"},
                "application": {"value": "water supply"},
            },
            "raw_text": "Supply of HDPE pipes conforming to IS 4984 for potable water distribution",
        }
        result = engine.evaluate_applicability(candidate, requirements)
        assert result["state"] != "APPLICABLE", \
            f"HDPE query should NOT return APPLICABLE for cast iron standard. Got: {result['state']}"

    def test_xlpe_cable_vs_pvc_cable_standard(self, engine):
        """XLPE cable query vs PVC cable standard should detect material distinction."""
        candidate = {
            "designation": "IS 1554 (Part 1):1988",
            "title": "PVC Insulated Electric Cables for Working Voltages up to 1100V",
            "scope": "Covers PVC insulated cables up to 1100 V.",
            "is_hydrated": True,
            "recommendation_ready": True,
        }
        requirements = {
            "requirements": {
                "product": {"value": "power cable"},
                "material": {"value": "XLPE"},
                "voltage": {"value": "11 kV"},
            },
            "raw_text": "Procurement of 11 kV XLPE insulated power cable",
        }
        result = engine.evaluate_applicability(candidate, requirements)
        # Should NOT be APPLICABLE since material (XLPE vs PVC) is different
        assert result["state"] != "APPLICABLE", \
            f"XLPE query should NOT be APPLICABLE to PVC standard. Got: {result['state']}"
