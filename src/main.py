import argparse
import sys

from src.modules.module_a import process
from src.modules.module_b import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python Docker container application")
    parser.add_argument(
        "--config",
        default="/app/config/config.yaml",
        help="Path to the configuration file (default: /app/config/config.yaml)",
    )
    parser.add_argument("--input", help="Path to the input file")
    parser.add_argument("--output", help="Path to the output file")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    process(config, args.input, args.output)


if __name__ == "__main__":
    main()
    sys.exit(0)
