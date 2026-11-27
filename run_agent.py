"""
Runs the Needle 2 agent with the tools defined in agent_tools.py.

Reads AGENT_QUERY from the environment, runs the agent loop, prints
a structured report, and exits non-zero on low confidence so CI
surfaces the failure.
"""
import json
import os
import sys

import needle

from agent_tools import read_file, run_command, post_comment, set_label


SYSTEM_PROMPT = (
    "You are a careful CI assistant working inside a GitHub repository. "
    "Use the provided tools to inspect files and act on pull requests. "
    "Never guess file contents — read them. Prefer minimal, safe actions."
)


def main() -> int:
    query = os.environ.get("AGENT_QUERY", "").strip()
    if not query:
        print("ERROR: AGENT_QUERY env var is empty.", file=sys.stderr)
        return 1

    print("=== QUERY ===")
    print(query)
    print()

    agent = needle.Needle(
        tools=[read_file, run_command, post_comment, set_label],
        system=SYSTEM_PROMPT,
    )

    try:
        response = agent.run(query, max_steps=6)
    except Exception as e:
        print(f"ERROR: agent.run failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    reasoning = response.get("reasoning", "(none)")
    confidence = response.get("confidence", None)
    calls = response.get("function_calls", [])
    results = response.get("results", [])
    suppressed = response.get("suppressed_calls", [])

    print("=== REASONING ===")
    print(reasoning)
    print()

    print("=== CONFIDENCE ===")
    print(confidence)
    print()

    print("=== FUNCTION CALLS ===")
    print(json.dumps(calls, indent=2, default=str))
    print()

    print("=== RESULTS ===")
    print(json.dumps(results, indent=2, default=str))
    print()

    if suppressed:
        print("=== SUPPRESSED (below confidence floor) ===")
        print(json.dumps(suppressed, indent=2, default=str))
        print()

    os.makedirs("output", exist_ok=True)
    with open("output/agent_result.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "query": query,
                "reasoning": reasoning,
                "confidence": confidence,
                "function_calls": calls,
                "results": results,
                "suppressed_calls": suppressed,
            },
            f,
            indent=2,
            default=str,
        )

    if isinstance(confidence, (int, float)) and confidence < 0.5:
        print(f"\nLOW CONFIDENCE ({confidence:.2f}) — not acting further.", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
