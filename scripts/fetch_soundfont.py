"""
Helper script to download MuseScore_General.sf2 for Bearmony.
Run this if you need to refresh the asset or fetch it in CI.
"""
import os, sys, hashlib, shutil
from pathlib import Path
import urllib.request

URL = os.environ.get("BEARMONY_SF2_URL") or "https://your-stable-url/MuseScore_General.sf2"
DEST = Path(__file__).parent.parent / "bearmony" / "assets" / "soundfonts" / "MuseScore_General.sf2"
CACHE_HASH = "sha256:REPLACE_WITH_ACTUAL_HASH"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()

def main():
    print(f"Downloading SoundFont from {URL}...")
    with urllib.request.urlopen(URL, timeout=60) as r, open(DEST, "wb") as f:
        shutil.copyfileobj(r, f)
    print(f"Saved to {DEST}")
    if CACHE_HASH != "sha256:REPLACE_WITH_ACTUAL_HASH":
        actual = sha256(DEST)
        print(f"SHA256: {actual}")
        if actual != CACHE_HASH:
            print("Hash mismatch! Aborting.")
            DEST.unlink(missing_ok=True)
            sys.exit(1)

if __name__ == "__main__":
    main()
