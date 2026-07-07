import argparse
import subprocess


def cli() -> None:
    parser = argparse.ArgumentParser(description="Bump the tdc-charts package version.")
    parser.add_argument("part", choices=["major", "minor", "patch"])
    args = parser.parse_args()
    subprocess.run(["uv", "version", "--bump", args.part], check=True)
