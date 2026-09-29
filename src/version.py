"""
Authoritative Version and Release Identity — StandSpec AI

Single source of truth for ALL system versions, release identifiers,
schema contracts, and component version identities.

Every version token here is consumed by:
- scripts/generate_release_manifest.py
- engine.py provenance blocks
- evaluation artifacts
- schema validation
"""

# ── Core Engine ──
ENGINE_VERSION = "3.0.0"
RELEASE_ID = "STANDSPEC_PROTOTYPE_CED_ETD_V3_0_0"

# ── Collector / Parser ──
COLLECTOR_VERSION = "1.2.1"
PARSER_VERSION = "1.2.1"

# ── Schema Versions (per contract) ──
FORMAT_VERSION = "2.0"
SCHEMA_VERSION = "2.0"
COLLECTOR_SCHEMA_VERSION = "1.2"
GRAPH_SCHEMA_VERSION = "2.1"
RECOMMENDATION_RESULT_SCHEMA_VERSION = "2.1"
NORMALIZED_REQUIREMENT_SCHEMA_VERSION = "2.1"
BENCHMARK_SCHEMA_VERSION = "2.1"
REGULATORY_SCHEMA_VERSION = "1.0"

# ── Taxonomy / Model Versions ──
ROLE_TAXONOMY_VERSION = "1.0.0"
LIFECYCLE_MODEL_VERSION = "2.0"
LLM_CONTRACT_VERSION = "1.0.0"

# ── Evaluator ──
EVALUATOR_VERSION = "2.1.0"

# ── Runtime ──
PYTHON_RUNTIME = "3.14.6"
PYTEST_VERSION = "9.1.1"

# ── Composite identity for human display ──
__version__ = ENGINE_VERSION
