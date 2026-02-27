import json
import os
import sys
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

from src.modules.asg_lookup import lookup_asg


def _log(level, message):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "command": "start",
        "message": message,
    }
    if level == "ERROR":
        print(json.dumps(entry), file=sys.stderr)
    else:
        print(json.dumps(entry))


def start(args, config):
    artifacts = config.get("artifacts", {})

    min_healthy = args.min_healthy_percentage
    max_healthy = args.max_healthy_percentage
    instance_warmup = args.instance_warmup
    skip_matching = not args.no_skip_matching

    if not (100 <= max_healthy <= 200):
        _log(
            "ERROR",
            f"--max-healthy-percentage must be between 100 and 200, got {max_healthy}",
        )
        sys.exit(3)

    if min_healthy > max_healthy:
        _log(
            "ERROR",
            f"--min-healthy-percentage ({min_healthy}) must be <= --max-healthy-percentage ({max_healthy})",
        )
        sys.exit(3)

    client = boto3.client("autoscaling")
    asg_name = lookup_asg(client, args.tag_key, args.tag_value, "start")

    preferences = {
        "MinHealthyPercentage": min_healthy,
        "MaxHealthyPercentage": max_healthy,
        "InstanceWarmup": instance_warmup,
        "SkipMatching": skip_matching,
    }

    if args.checkpoint_percentages:
        preferences["CheckpointPercentages"] = args.checkpoint_percentages
        preferences["CheckpointDelay"] = args.checkpoint_delay

    _log("INFO", f"Starting instance refresh for ASG: {asg_name}")

    try:
        response = client.start_instance_refresh(
            AutoScalingGroupName=asg_name,
            Preferences=preferences,
        )
    except ClientError as e:
        _log("ERROR", f"AWS error starting instance refresh: {e}")
        sys.exit(2)

    refresh_id = response["InstanceRefreshId"]
    _log("INFO", f"Instance refresh started with ID: {refresh_id}")

    output_dir = artifacts.get("output_dir", "outputs")
    filename = artifacts.get("refresh_env_filename", "refresh.env")
    output_path = os.path.join(output_dir, filename)

    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(f"INSTANCE_REFRESH_ID={refresh_id}\n")
    except OSError as e:
        _log("ERROR", f"Failed to write artifact file {output_path}: {e}")
        sys.exit(4)

    _log("INFO", f"Wrote refresh ID to {output_path}")
    sys.exit(0)
