import argparse
import json
import os
import sys
from datetime import datetime, timezone

import yaml

from src.modules import refresh_start, refresh_monitor


def _log_startup_error(message):
    print(
        json.dumps(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "ERROR",
                "command": "startup",
                "message": message,
            }
        ),
        file=sys.stderr,
    )


def load_config():
    config_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../config/config.yaml")
    )
    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        _log_startup_error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        _log_startup_error(f"Configuration file is malformed: {e}")
        sys.exit(1)


def main():
    config = load_config()
    defaults = config.get("defaults", {})

    parser = argparse.ArgumentParser(
        description="AWS ASG Instance Refresh manager",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- start subparser ---
    start_parser = subparsers.add_parser(
        "start",
        help="Start an ASG instance refresh",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    start_parser.add_argument("--tag-key", required=True, help="ASG tag key to match")
    start_parser.add_argument(
        "--tag-value", required=True, help="ASG tag value to match"
    )
    start_parser.add_argument(
        "--min-healthy-percentage",
        type=int,
        default=defaults.get("min_healthy_percentage", 90),
        help="Minimum percentage of healthy instances during refresh",
    )
    start_parser.add_argument(
        "--max-healthy-percentage",
        type=int,
        default=defaults.get("max_healthy_percentage", 100),
        help=(
            "Maximum percentage of total capacity above desired"
            " during refresh (100-200)"
        ),
    )
    start_parser.add_argument(
        "--instance-warmup",
        type=int,
        default=defaults.get("instance_warmup", 300),
        help="Seconds to wait after a new instance is in service",
    )
    start_parser.add_argument(
        "--no-skip-matching",
        action="store_true",
        help="Disable skipping of instances already on the latest launch template",
    )
    start_parser.add_argument(
        "--checkpoint-percentages",
        nargs="+",
        type=int,
        metavar="PCT",
        help="List of percentage thresholds at which to pause the refresh",
    )
    start_parser.add_argument(
        "--checkpoint-delay",
        type=int,
        default=3600,
        help="Seconds to wait at each checkpoint before continuing",
    )

    # --- monitor subparser ---
    monitor_parser = subparsers.add_parser(
        "monitor",
        help="Monitor an in-progress ASG instance refresh",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    monitor_parser.add_argument("--tag-key", required=True, help="ASG tag key to match")
    monitor_parser.add_argument(
        "--tag-value", required=True, help="ASG tag value to match"
    )
    monitor_parser.add_argument(
        "--refresh-id",
        default=None,
        help="Instance refresh ID (default: read from artifact file)",
    )
    monitor_parser.add_argument(
        "--poll-interval",
        type=int,
        default=defaults.get("poll_interval", 30),
        help="Seconds between status polls",
    )
    monitor_parser.add_argument(
        "--timeout",
        type=int,
        default=defaults.get("timeout", 1800),
        help="Maximum seconds to wait before timing out",
    )

    args = parser.parse_args()

    if args.command == "start":
        refresh_start.start(args, config)
    elif args.command == "monitor":
        refresh_monitor.monitor(args, config)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
