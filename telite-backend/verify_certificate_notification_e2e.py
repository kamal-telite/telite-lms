"""Run the N5B certificate notification verification gate."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent
    commands = [
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_certificate_notifications.py",
            "tests/test_certificate_runtime.py",
            "-q",
        ],
    ]

    for command in commands:
        print(f"Running: {' '.join(command)}")
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode != 0:
            print("Certificate notification verification failed.")
            return result.returncode

    print("CERTIFICATE NOTIFICATION VERIFICATION PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
