"""Exercise the local persisted job API after migrations and T-203 are installed.

Requires an explicit case ID. Does not load environment files or invoke an SDK.
"""
import argparse
import json
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "http://127.0.0.1:8000/api/v1/ui"


def call(path, body=None):
    payload = json.dumps(body).encode() if body is not None else None
    request = Request(
        BASE + path, data=payload, headers={"Content-Type": "application/json"}
    )
    with urlopen(request, timeout=10) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", type=int, required=True)
    parser.add_argument("--acknowledged-carry-over", action="store_true")
    args = parser.parse_args()
    accepted = call(
        f"/cases/{args.case_id}/agent-runs",
        {"acknowledgedCarryOver": args.acknowledged_carry_over},
    )
    run_id = accepted["runId"]
    deadline = time.monotonic() + 1000
    while time.monotonic() < deadline:
        progress = call(f"/agent-runs/{run_id}")
        if progress["outcome"] != "running":
            print(
                json.dumps(
                    {
                        key: progress[key]
                        for key in (
                            "runId",
                            "outcome",
                            "stopReason",
                            "versionId",
                            "isComplete",
                        )
                    }
                )
            )
            return 0 if progress["outcome"] == "success" else 1
        time.sleep(1)
    print("Polling deadline reached")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HTTPError as error:
        print(f"Local API rejected the request (HTTP {error.code})")
        raise SystemExit(1) from None
