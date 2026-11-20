"""Run an AgentDojo script with its tool clock frozen:  python frozen_clock.py <script.py> [args...]

AgentDojo's write tools (send_email, create_file, append_to_file, share_file) stamp outputs with the wall clock.
benign-instruction-bench labels a tool output "injected" when it differs from the clean replay, so a timestamp
that ticks between the two replays makes a benign output look injected, and the set changes on every rebuild.
Only the three clock reads are patched (agentdojo 0.1.34: cloud_drive_client, email_client, Email.timestamp);
replacing datetime.datetime globally breaks YAML dumping of the tool results.
"""
import datetime as _dt
import runpy
import sys
from types import SimpleNamespace

FIXED = _dt.datetime(2026, 1, 1, 12, 0, 0)


def freeze():
    from agentdojo.default_suites.v1.tools import cloud_drive_client, email_client
    from agentdojo.default_suites.v1.tools.types import Email

    clock = SimpleNamespace(datetime=SimpleNamespace(now=lambda: FIXED))  # these modules only call datetime.datetime.now()
    cloud_drive_client.datetime = clock
    email_client.datetime = clock
    Email.model_fields["timestamp"].default_factory = lambda: FIXED
    Email.model_rebuild(force=True)


def main():
    freeze()
    script = sys.argv[1]
    sys.argv = sys.argv[1:]
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main()
