"""Rebuild the dataset and refit the deployed model through today."""
from __future__ import annotations

import subprocess
import sys


def run(script: str) -> None:
    subprocess.run([sys.executable, script], check=True)


if __name__ == "__main__":
    run("scripts/build_dataset.py")
    run("scripts/train_model_sklearn.py")
