"""Explicit acquisition of upstream source, never an import-time download."""

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

VERSION = "2026.8.3"
REMOTE_URL = (
    f"https://raw.githubusercontent.com/home-assistant/core/{VERSION}/"
    "homeassistant/components/broadlink/remote.py"
)
REMOTE_SHA256 = "ff67b5280fdc8aaec99f1847abfe9c407d15486089a9db2555b676dd0e6ce8f6"


def verify_source(data):
    """Reject even a one-byte change before any source is executed."""
    digest = hashlib.sha256(data).hexdigest()
    if digest != REMOTE_SHA256:
        raise ValueError(f"Pinned Broadlink source hash mismatch: {digest}")
    return data.decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    with urlopen(REMOTE_URL, timeout=30) as response:
        data = response.read()
    verify_source(data)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_bytes(data)
    print(f"Verified HA {VERSION} Broadlink remote.py: {REMOTE_SHA256}")


if __name__ == "__main__":
    main()
