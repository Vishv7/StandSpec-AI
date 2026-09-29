"""
StandSpec AI — LLM-Powered Agentic RAG Decision Engine CLI
Phase P1-F (Sections 51 & 52)

Usage:
  python scripts/run_agent.py --query "Supply of 1.1 kV XLPE insulated three-core power cables"
  python scripts/run_agent.py --query "Supply of uPVC pipes as per IS 1180 Part 1" --trace
  python scripts/run_agent.py --interactive
  python scripts/run_agent.py --query "..." --json
"""

import sys
import os
import json
import argparse
import time
from typing import Optional, Dict, Any

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure utf-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.agent.agent import StandSpecAgent
from src.version import ENGINE_VERSION, RELEASE_ID


def format_status(state: str) -> str:
    color_map = {
        "PRIMARY_RECOMMENDATION_AVAILABLE": "\033[92m[+] PRIMARY_RECOMMENDATION_AVAILABLE\033[0m",
        "CONDITIONAL_RECOMMENDATION": "\033[93m[^] CONDITIONAL_RECOMMENDATION\033[0m",
        "MULTIPLE_POSSIBLE_STANDARDS": "\033[94m[*] MULTIPLE_POSSIBLE_STANDARDS\033[0m",
        "CLARIFICATION_REQUIRED": "\033[96m[?] CLARIFICATION_REQUIRED\033[0m",
        "EXPERT_REVIEW_REQUIRED": "\033[93m[!] EXPERT_REVIEW_REQUIRED\033[0m",
        "NO_CONFIDENT_MATCH": "\033[91m[-] NO_CONFIDENT_MATCH\033[0m",
        "OUTSIDE_PROTOTYPE_COVERAGE": "\033[95m[x] OUTSIDE_PROTOTYPE_COVERAGE\033[0m",
    }
    return color_map.get(state, f"\033[97m{state}\033[0m")


def display_agent_result(res: Dict[str, Any], show_trace: bool = False):
    print("\n" + "=" * 78)
    print(f" STANDSPEC AI v{ENGINE_VERSION} — AGENT PROCUREMENT DECISION")
    print(f" Release: {RELEASE_ID}")
    print("=" * 78)

    state = res.get("decision_state", "UNKNOWN")
    print(f"\n  Decision State : {format_status(state)}")
    print(f"  Confidence     : {res.get('confidence', 'MEDIUM')}")

    # Primary Recommendation
    primary = res.get("primary_recommendation")
    if primary:
        print("\n  \033[1m[PRIMARY RECOMMENDED STANDARD]\033[0m")
        print(f"    Designation  : \033[92m\033[1m{primary.get('designation')}\033[0m")
        print(f"    Title        : {primary.get('title', 'N/A')}")
        print(f"    Claim Level  : {primary.get('claim_level', 'VERIFIED')}")
        if primary.get("matched_attributes"):
            print(f"    Matched Attr : {', '.join(primary.get('matched_attributes'))}")
        if primary.get("reason"):
            print(f"    Match Reason : {primary.get('reason')}")

    # Alternatives
    alts = res.get("alternative_standards", [])
    if alts:
        print(f"\n  \033[1m[ALTERNATIVE STANDARDS ({len(alts)})]\033[0m")
        for alt in alts:
            print(f"    - {alt.get('designation')}: {alt.get('title', '')}")

    # Expert Review Candidate
    rev = res.get("review_candidate")
    if rev:
        print("\n  \033[1m[CANDIDATE FOR EXPERT REVIEW]\033[0m")
        print(f"    Designation  : {rev.get('designation')}")
        print(f"    Title        : {rev.get('title', 'N/A')}")
        print(f"    Reason       : {rev.get('reason')}")
        if rev.get("evidence_gaps"):
            print(f"    Evidence Gaps: {', '.join(rev.get('evidence_gaps'))}")

    # Clarifications
    clarifs = res.get("clarifications_needed", [])
    if clarifs:
        print("\n  \033[1m[CLARIFICATIONS NEEDED / MISSING SPECIFICATIONS]\033[0m")
        for c in clarifs:
            print(f"    ? {c}")

    # Lifecycle & Regulatory Status
    life = res.get("lifecycle", {})
    reg = res.get("regulatory", {})
    print("\n  \033[1m[STATUTORY & LIFECYCLE COMPLIANCE]\033[0m")
    print(f"    Lifecycle State   : {life.get('state', 'N/A')}")
    if life.get("recommended_edition"):
        print(f"    Valid Edition     : {life.get('recommended_edition')}")
    print(f"    Regulatory State  : {reg.get('state', 'N/A')}")
    if reg.get("qco_order_number"):
        print(f"    Mandatory QCO     : {reg.get('qco_order_number')}")
    if reg.get("statement"):
        print(f"    Statutory Order   : {reg.get('statement')}")

    # Natural Language Officer Summary
    explanation = res.get("natural_language_explanation")
    if explanation:
        print("\n  \033[1m[NATURAL LANGUAGE OFFICER SUMMARY]\033[0m")
        print(f"    {explanation}")

    # Agent Audit Metadata
    meta = res.get("agent_metadata", {})
    print("\n  \033[1m[AGENT AUDIT TRACE]\033[0m")
    print(f"    Execution Mode    : {meta.get('execution_mode')}")
    print(f"    Steps Taken       : {meta.get('step_count')} (max 6)")
    print(f"    Search Rounds     : {meta.get('search_rounds')}")
    print(f"    Revision Rounds   : {meta.get('revision_rounds')}")
    print(f"    Validator Gate    : \033[92m{meta.get('validator_status')}\033[0m")
    print(f"    Engine Latency    : {meta.get('latency_ms')} ms")

    # Tool Calls Trace
    if show_trace:
        tool_calls = res.get("tool_calls", [])
        print(f"\n  \033[1m[DISPATCHED TOOL CALLS ({len(tool_calls)})]\033[0m")
        for i, tc in enumerate(tool_calls, 1):
            args_repr = json.dumps(tc.get("arguments", {}), ensure_ascii=False)
            status = tc.get("status", "SUCCESS")
            print(f"    {i}. [{tc.get('tool')}] status={status} args={args_repr[:120]}")

    print("\n" + "=" * 78 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="StandSpec AI — LLM-Powered Agentic RAG Decision Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--query", "-q", type=str, help="Procurement requirement text or tender line item")
    parser.add_argument("--mode", "-m", choices=["auto", "offline", "llm"], default="auto", help="Execution mode")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive procurement session")
    parser.add_argument("--trace", "-t", action="store_true", help="Display full tool call and validator trace")
    parser.add_argument("--json", "-j", action="store_true", help="Output machine JSON format only")
    parser.add_argument("--eval-date", type=str, default=None, help="Evaluation as-of date (YYYY-MM-DD)")

    args = parser.parse_args()

    # Initialize Agent from release graph
    print(f"Initializing StandSpecAgent from release manifest ({RELEASE_ID})...", file=sys.stderr)
    agent = StandSpecAgent.from_release()

    if args.interactive:
        print("\n" + "=" * 78)
        print(" STANDSPEC AI — INTERACTIVE PROCUREMENT OFFICER SESSION")
        print(" Type procurement requirements or tender specifications.")
        print(" Type 'exit' or 'quit' to end session.")
        print("=" * 78 + "\n")

        while True:
            try:
                raw_query = input("\033[1mProcurement Query > \033[0m").strip()
                if not raw_query:
                    continue
                if raw_query.lower() in ("exit", "quit", "q"):
                    print("Exiting StandSpec AI. Session concluded.")
                    break

                res = agent.answer(raw_query, mode=args.mode, evaluation_date=args.eval_date)
                if args.json:
                    print(json.dumps(res, indent=2, ensure_ascii=False))
                else:
                    display_agent_result(res, show_trace=args.trace)

            except (KeyboardInterrupt, EOFError):
                print("\nSession interrupted. Exiting.")
                break
            except Exception as e:
                print(f"\033[91mError evaluating query: {e}\033[0m", file=sys.stderr)

    elif args.query:
        res = agent.answer(args.query, mode=args.mode, evaluation_date=args.eval_date)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            display_agent_result(res, show_trace=args.trace)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
