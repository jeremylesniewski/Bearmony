import os

def resolve_soundfont():
    """
    Returns the path to the SoundFont file (.sf2) for FluidSynth playback.
    Checks the BEARMONY_SF2 environment variable, then common filenames in the project root.
    Raises FileNotFoundError if not found.
    """
    # Check environment variable
    sf2_env = os.environ.get("BEARMONY_SF2")
    if sf2_env and os.path.isfile(sf2_env):
        return sf2_env
    # Check common locations in project root
    candidates = [
        "FluidR3_GM.sf2",
        "GeneralUser.sf2",
        "soundfont.sf2"
    ]
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for fname in candidates:
        path = os.path.join(root, fname)
        if os.path.isfile(path):
            return path
    raise FileNotFoundError("No SoundFont (.sf2) found. Place one in the project root or set BEARMONY_SF2.")
