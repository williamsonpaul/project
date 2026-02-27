import json
import os
import sys
import time
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from src.modules.asg_lookup import lookup_asg

_TERMINAL_STATES = {
    "Successful": 0,
    "Failed": 1,
    "Cancelled": 2,
    "RollbackSuccessful": 4,
    "RollbackFailed": 5,
}


def _log(level, message):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "command": "monitor",
        "message": message,
    }
    if level == "ERROR":
        print(json.dumps(entry), file=sys.stderr)
    else:
        print(json.dumps(entry))


def _read_refresh_id_from_artifact(artifacts):
    output_dir = artifacts.get("output_dir", "outputs")
    filename = artifacts.get("refresh_env_filename", "refresh.env")
    path = os.path.join(output_dir, filename)
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("INSTANCE_REFRESH_ID="):
                    return line.strip().split("=", 1)[1]
    except OSError:
        pass
    return None


def monitor(args, config):
    artifacts = config.get("artifacts", {})

    refresh_id = args.refresh_id
    if not refresh_id:
        refresh_id = _read_refresh_id_from_artifact(artifacts)
    if not refresh_id:
        _log(
            "ERROR",
            "No refresh ID provided via --refresh-id and none found in artifact file",
        )
        sys.exit(3)

    _log("INFO", f"Monitoring instance refresh ID: {refresh_id}")

    client = boto3.client("autoscaling")

    try:
        asg_name = lookup_asg(client, args.tag_key, args.tag_value, "monitor")
    except SystemExit:
        sys.exit(2)

    poll_interval = args.poll_interval
    timeout = args.timeout
    start_time = time.monotonic()

    while True:
        elapsed = time.monotonic() - start_time

        if elapsed >= timeout:
            _log(
                "ERROR",
                f"Timed out after {elapsed:.0f}s waiting for refresh"
                f" {refresh_id} to reach a terminal state",
            )
            sys.exit(3)

        try:
            response = client.describe_instance_refreshes(
                AutoScalingGroupName=asg_name,
                InstanceRefreshIds=[refresh_id],
            )
        except ClientError as e:
            _log("ERROR", f"AWS error describing instance refresh: {e}")
            sys.exit(2)

        refreshes = response.get("InstanceRefreshes", [])
        if not refreshes:
            _log("ERROR", f"No instance refresh found with ID: {refresh_id}")
            sys.exit(2)

        refresh = refreshes[0]
        status = refresh.get("Status", "Unknown")
        pct = refresh.get("PercentageComplete", 0)

        _log(
            "INFO",
            f"Status: {status}, PercentageComplete: {pct}%, Elapsed: {elapsed:.0f}s",
        )

        if status in _TERMINAL_STATES:
            exit_code = _TERMINAL_STATES[status]
            _log(
                "INFO",
                f"Instance refresh reached terminal state:"
                f" {status} after {elapsed:.0f}s",
            )
            sys.exit(exit_code)

        time.sleep(poll_interval)
