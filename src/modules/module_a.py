import sys


def process(config: dict, input_path: str | None, output_path: str | None) -> None:
    app_name = config.get("app", {}).get("name", "app")
    log_level = config.get("app", {}).get("log_level", "INFO")

    print(f"[{log_level}] {app_name}: processing started", flush=True)

    if input_path:
        print(f"[{log_level}] Input:  {input_path}", flush=True)
    if output_path:
        print(f"[{log_level}] Output: {output_path}", flush=True)

    if not input_path and not output_path:
        print(f"[{log_level}] No input/output paths provided; nothing to do.", file=sys.stderr)

    print(f"[{log_level}] {app_name}: processing complete", flush=True)
