"""Run the N5C.3 learning path completion notification verification gate."""

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
            "tests/test_learning_path_completion_notifications.py",
            "tests/test_learning_path_runtime.py",
            "-q",
        ],
    ]

    for command in commands:
        print(f"Running: {' '.join(command)}")
        result = subprocess.run(command, cwd=root, check=False)
        if result.returncode != 0:
            print("Learning path completion notification verification failed.")
            return result.returncode

    print("LEARNING PATH COMPLETION NOTIFICATION VERIFICATION PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
