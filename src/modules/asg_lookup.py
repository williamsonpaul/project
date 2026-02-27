import json
import sys
from datetime import datetime, timezone


def _log(level, message, command):
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "command": command,
        "message": message,
    }
    if level == "ERROR":
        print(json.dumps(entry), file=sys.stderr)
    else:
        print(json.dumps(entry))


def lookup_asg(client, tag_key, tag_value, command):
    """Paginate DescribeAutoScalingGroups and return the name of the single ASG
    whose tags contain an exact (case-sensitive) match for tag_key=tag_value.

    Exits with code 1 if zero or more than one ASG matches.
    """
    matching = []
    paginator = client.get_paginator("describe_auto_scaling_groups")
    for page in paginator.paginate():
        for asg in page.get("AutoScalingGroups", []):
            for tag in asg.get("Tags", []):
                if tag["Key"] == tag_key and tag["Value"] == tag_value:
                    matching.append(asg["AutoScalingGroupName"])
                    break

    if len(matching) == 0:
        _log(
            "ERROR",
            f"No ASG found with tag {tag_key}={tag_value}",
            command,
        )
        sys.exit(1)

    if len(matching) > 1:
        _log(
            "ERROR",
            f"Multiple ASGs found with tag {tag_key}={tag_value}: {matching}",
            command,
        )
        sys.exit(1)

    asg_name = matching[0]
    _log("INFO", f"Found ASG: {asg_name}", command)
    return asg_name
