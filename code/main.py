"""
Anchor — Main entry point.

Usage:
  python code/main.py demo     — run the poisoned-page demo
  python code/main.py server   — start the model server
"""

import sys
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s  %(message)s",
)


def main():
    if len(sys.argv) < 2:
        print("Usage: python code/main.py [demo|server]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "demo":
        from agent.loop import run_demo
        result = run_demo()
        print("\n" + "=" * 60)
        print("DEMO RESULTS")
        print("=" * 60)
        print(json.dumps(result, indent=2))

        if result["vanilla"]["secret_leaked"]:
            print("\n⚠  Vanilla agent: SECRET LEAKED")
        else:
            print("\n✓  Vanilla agent: secret safe")

        if result["anchor"]["secret_leaked"]:
            print("\n⚠  Anchor agent: SECRET LEAKED")
        else:
            print("\n✓  Anchor agent: secret safe")

        if result["anchor"]["blocked_action"]:
            print(f"   Blocked action: {result['anchor']['blocked_action']}")

    elif cmd == "server":
        import uvicorn
        uvicorn.run("model.server:app", host="0.0.0.0", port=8000, reload=True)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
