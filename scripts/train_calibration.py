"""
Offline Statistical Calibration Pipeline — StandSpec AI
Fits PlattScaler (logistic calibration) on calibration benchmark queries.
Saves the fitted model artifact to data/models/calibrator_v1.json with full provenance.
"""

import sys
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.engine import StandSpecRecommendationEngine
from src.calibration.calibrator import PlattScaler, compute_ece, compute_brier_score


def train_calibrator(
    benchmark_path: Path,
    graph_path: Path,
    output_path: Path,
    max_iter: int = 100,
    l2_reg: float = 0.01,
) -> dict:
    print(f"Loading knowledge graph from {graph_path}...")
    with open(graph_path, "r", encoding="utf-8") as f:
        graph = json.load(f)

    print(f"Loading calibration benchmark from {benchmark_path}...")
    with open(benchmark_path, "r", encoding="utf-8") as f:
        raw_content = f.read()
        split_hash = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        queries = [json.loads(line) for line in raw_content.splitlines() if line.strip() and not line.startswith("#")]

    print(f"Loaded {len(queries)} calibration queries. Split SHA256: {split_hash[:16]}...")

    # Initialize recommendation engine without pre-existing calibration artifact
    engine = StandSpecRecommendationEngine(graph)

    raw_scores = []
    labels = []
    query_details = []

    print("Executing retrieval and reranking for calibration queries...")
    for q in queries:
        qid = q.get("query_id")
        raw_text = q.get("query", {}).get("raw_text", "")
        eval_date = q.get("source", {}).get("evaluation_as_of_date")
        expected_golds = {g["standard_designation"] for g in q.get("gold_standards", [])}
        expected_bases = {g.get("standard_designation", "").split(":")[0].strip() for g in q.get("gold_standards", [])}

        output = engine.recommend(raw_text, evaluation_date=eval_date, top_k=5)
        candidates = output.get("candidate_recommendations", [])

        if candidates:
            top_cand = candidates[0]
            score = float(top_cand.get("confidence_score", 0.0))
            cand_desig = top_cand.get("standard_designation", "")
            cand_base = cand_desig.split(":")[0].strip()
            
            # Label = 1 if top candidate is gold standard match (exact or base)
            is_correct = 1 if (cand_desig in expected_golds or cand_base in expected_bases) else 0
        else:
            score = 0.0
            is_correct = 0

        raw_scores.append(score)
        labels.append(is_correct)
        query_details.append({
            "query_id": qid,
            "raw_score": score,
            "label": is_correct,
        })

    # Metrics before calibration
    raw_probs = [max(min(s, 1.0), 0.0) for s in raw_scores]
    ece_before = compute_ece(raw_probs, labels, n_bins=5)
    brier_before = compute_brier_score(raw_probs, labels)

    print(f"\nPre-calibration metrics (N={len(labels)}, Positives={sum(labels)}):")
    print(f"  Raw ECE:   {ece_before:.4f}")
    print(f"  Raw Brier: {brier_before:.4f}")

    # Fit Platt Scaler
    calibrator = PlattScaler(a=2.0, b=-1.0, is_fitted=False)
    calibrator.fit(raw_scores, labels, max_iter=max_iter, l2_reg=l2_reg)

    # Post-calibration metrics
    cal_probs = [calibrator.predict_proba(s) for s in raw_scores]
    ece_after = compute_ece(cal_probs, labels, n_bins=5)
    brier_after = compute_brier_score(cal_probs, labels)

    print(f"\nPost-calibration metrics:")
    print(f"  Optimal A: {calibrator.a:.4f}")
    print(f"  Optimal B: {calibrator.b:.4f}")
    print(f"  Calibrated ECE:   {ece_after:.4f}")
    print(f"  Calibrated Brier: {brier_after:.4f}")

    metadata = {
        "calibrator_version": "1.0.0",
        "fit_timestamp": datetime.now(timezone.utc).isoformat(),
        "benchmark_file": str(benchmark_path.relative_to(PROJECT_ROOT) if benchmark_path.is_relative_to(PROJECT_ROOT) else benchmark_path),
        "split_sha256": split_hash,
        "n_samples": len(labels),
        "positive_count": sum(labels),
        "negative_count": len(labels) - sum(labels),
        "optimal_a": calibrator.a,
        "optimal_b": calibrator.b,
        "ece_before": ece_before,
        "ece_after": ece_after,
        "brier_before": brier_before,
        "brier_after": brier_after,
        "l2_reg": l2_reg,
        "max_iter": max_iter,
    }

    calibrator.metadata = metadata
    calibrator.save(output_path)
    print(f"\nSuccessfully saved calibrated artifact to {output_path}")

    return metadata


def main():
    parser = argparse.ArgumentParser(description="Train statistical calibrator for StandSpec AI")
    parser.add_argument(
        "--benchmark-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "benchmarks" / "train.jsonl",
        help="Path to calibration / training benchmark jsonl",
    )
    parser.add_argument(
        "--graph-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "standards_graph.json",
        help="Path to standards knowledge graph json",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "models" / "calibrator_v1.json",
        help="Destination path for calibrator artifact",
    )
    parser.add_argument("--max-iter", type=int, default=100)
    parser.add_argument("--l2-reg", type=float, default=0.01)

    args = parser.parse_args()
    train_calibrator(
        benchmark_path=args.benchmark_path,
        graph_path=args.graph_path,
        output_path=args.output_path,
        max_iter=args.max_iter,
        l2_reg=args.l2_reg,
    )


if __name__ == "__main__":
    main()
