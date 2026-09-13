"""Launcher script for YouTube Analyzer Streamlit Dashboard."""

import os
import subprocess
import sys
from pathlib import Path


def main():
    dashboard_path = Path(__file__).resolve().parent / "dashboard.py"
    if not dashboard_path.exists():
        print(f"Error: Could not find {dashboard_path}")
        sys.exit(1)

    print(f"Launching dashboard from: {dashboard_path}")

    # Configure UTF-8 and disable telemetry prompt
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(dashboard_path),
        "--server.headless=false",
    ]

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
