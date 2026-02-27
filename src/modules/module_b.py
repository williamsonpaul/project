import sys

import yaml


def load_config(path: str) -> dict:
    try:
        with open(path) as f:
            config = yaml.safe_load(f)
        if config is None:
            print(f"ERROR: Config file is empty: {path}", file=sys.stderr)
            sys.exit(1)
        return config
    except FileNotFoundError:
        print(f"ERROR: Config file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse config file: {e}", file=sys.stderr)
        sys.exit(1)
