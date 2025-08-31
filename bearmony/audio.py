from __future__ import annotations
import os, sys, hashlib, shutil
from pathlib import Path

try:
    # Py3.9+: use importlib.resources.files
    from importlib.resources import files as pkg_files
except Exception:  # pragma: no cover
    pkg_files = None

APP_NAME = "Bearmony"
ENV_VAR = "BEARMONY_SF2"
CACHE_BASENAME = "MuseScore_General.sf2"
CACHE_HASH = "sha256:REPLACE_WITH_ACTUAL_HASH"  # see CI step below

def _appdata_dir() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    d = base / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d

def _settings_file() -> Path:
    return _appdata_dir() / "settings.ini"

def _read_user_sf2_from_settings() -> str | None:
    ini = _settings_file()
    if ini.exists():
        for line in ini.read_text().splitlines():
            if line.strip().startswith("sf2="):
                p = line.split("=", 1)[1].strip().strip('"')
                if p and Path(p).exists():
                    return p
    return None

def _bundled_sf2() -> str | None:
    # Look for packaged asset: bearmony/assets/soundfonts/*.sf2
    if pkg_files:
        try:
            sf2_dir = pkg_files("bearmony") / "assets" / "soundfonts"
            for cand in ("MuseScore_General.sf2", "FluidR3_GM.sf2"):
                p = sf2_dir / cand
                if p.is_file():
                    return str(p)
        except Exception:
            pass
    # PyInstaller onefile: assets are in sys._MEIPASS
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    for rel in ("assets/soundfonts/MuseScore_General.sf2", "assets/soundfonts/FluidR3_GM.sf2"):
        p = base / rel
        if p.exists():
            return str(p)
    return None

def _cached_sf2() -> str | None:
    p = _appdata_dir() / CACHE_BASENAME
    return str(p) if p.exists() else None

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()

def _download_sf2_if_needed() -> str | None:
    # defer import (no internet in some builds; also optional)
    try:
        import urllib.request
    except Exception:
        return None
    url = os.environ.get("BEARMONY_SF2_URL") or "https://…/MuseScore_General.sf2"  # set by CI
    dest = _appdata_dir() / CACHE_BASENAME
    if dest.exists() and (not CACHE_HASH or _sha256(dest) == CACHE_HASH):
        return str(dest)
    try:
        with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        if CACHE_HASH and _sha256(dest) != CACHE_HASH:
            dest.unlink(missing_ok=True)
            return None
        return str(dest)
    except Exception:
        return None

def resolve_soundfont() -> str | None:
    # 1) env
    env = os.environ.get(ENV_VAR)
    if env and Path(env).exists():
        return env
    # 2) settings file
    s = _read_user_sf2_from_settings()
    if s:
        return s
    # 3) bundled asset
    b = _bundled_sf2()
    if b:
        return b
    # 4) cached (or download)
    c = _cached_sf2()
    if c:
        return c
    return _download_sf2_if_needed()
