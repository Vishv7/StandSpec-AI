"""
Architectural Test: Production vs Benchmark Isolation (Phase P1-E Section 2).
Enforces that production runtime code NEVER depends on or reads benchmark datasets,
benchmark IDs, benchmark gold answers, or benchmark files.

Only:
- src/evaluation/
- scripts/evaluate_*.py
- benchmark validation / calibration tooling
may consume benchmark data.
"""

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_ROOT / "src"

BENCHMARK_NAMES = {
    "train.jsonl",
    "val.jsonl",
    "test.jsonl",
    "adversarial.jsonl",
    "challenge.jsonl",
    "coverage_boundary.jsonl",
    "open_world.jsonl",
    "benchmarks",
}

FORBIDDEN_PATTERNS = [
    "data/benchmarks",
    "data\\benchmarks",
    "train.jsonl",
    "val.jsonl",
    "test.jsonl",
    "adversarial.jsonl",
    "challenge.jsonl",
    "coverage_boundary.jsonl",
    "open_world.jsonl",
]


def test_no_production_file_imports_or_references_benchmarks():
    """
    Scans every Python file in src/ (except src/evaluation/) to ensure
    zero reference to benchmark filenames, directories, or benchmark IDs.
    """
    production_files = []
    for py_file in SRC_DIR.rglob("*.py"):
        # src/evaluation is specifically designated for evaluation tooling
        if "evaluation" in py_file.parts:
            continue
        production_files.append(py_file)

    assert len(production_files) > 0, "No production files found to test"

    violations = []

    for py_file in production_files:
        content = py_file.read_text(encoding="utf-8")
        rel_path = py_file.relative_to(PROJECT_ROOT)

        # 1. Check for literal string occurrences of forbidden benchmark names
        for pattern in FORBIDDEN_PATTERNS:
            if pattern in content:
                violations.append(f"{rel_path}: references forbidden pattern '{pattern}'")

        # 2. Check AST for imports referencing benchmarks or evaluate scripts
        tree = ast.parse(content, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "benchmark" in alias.name or "evaluate" in alias.name:
                        violations.append(f"{rel_path}: imports '{alias.name}'")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if "benchmark" in mod or "evaluate" in mod:
                    violations.append(f"{rel_path}: imports from '{mod}'")

    assert not violations, "Benchmark isolation violated in production code:\n" + "\n".join(violations)


def test_engine_init_and_recommend_without_benchmarks():
    """
    Verifies that the StandSpecRecommendationEngine initializes and processes
    an unseen query without opening any benchmark files.
    """
    import json
    from unittest.mock import patch
    from src.recommendation.engine import StandSpecRecommendationEngine

    graph_path = PROJECT_ROOT / "data" / "processed" / "standards_graph.json"
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    original_open = open

    def guarded_open(file, *args, **kwargs):
        file_str = str(file)
        if "data/benchmarks" in file_str or "data\\benchmarks" in file_str:
            raise PermissionError(f"Production engine attempted to open benchmark file: {file_str}")
        return original_open(file, *args, **kwargs)

    with patch("builtins.open", side_effect=guarded_open):
        engine = StandSpecRecommendationEngine(graph)
        result = engine.recommend("Procure high tensile deformed steel bars for RCC construction")
        assert result is not None
        assert "decision_state" in result
        assert "provenance" in result
