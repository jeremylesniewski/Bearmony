import os
from pathlib import Path
from bearmony.audio import resolve_soundfont, ENV_VAR

def test_bundled_sf2():
    sf2 = resolve_soundfont()
    assert sf2 and Path(sf2).exists(), f"Bundled SoundFont not found: {sf2}"

def test_env_override(tmp_path, monkeypatch):
    fake_sf2 = tmp_path / "fake.sf2"
    fake_sf2.write_bytes(b"FAKE")
    monkeypatch.setenv(ENV_VAR, str(fake_sf2))
    assert resolve_soundfont() == str(fake_sf2)
