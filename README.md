
````
# Bearmony — MIDI Chord & Progression Tool

Bearmony turns chords and progressions into MIDI. Pick root notes, chord types/sizes, roman-numeral progressions, and arpeggio modes (Asc / Desc / Up-Down / Random). Control tempo, note value, velocity, loops, basic FX, and General MIDI instrument. Playback uses FluidSynth with a SoundFont you provide.

---

## Features
- Chords and full progressions
- Arpeggios (Asc/Desc/Up-Down/Random)
- Tempo, note value, velocity, loop count, basic FX
- General MIDI instrument selection (0–127)
- Live playback (FluidSynth + SoundFont)
- MIDI export (chord or progression)

---

## Requirements
- Python **3.11** recommended (3.8+ supported).  
  macOS: use the Python.org installer (includes Tkinter).
- Install deps:
  ```bash
  pip install -r requirements.txt
````

* For playback you need:

  * **FluidSynth**

    * macOS: `brew install fluid-synth`
    * Windows: install a FluidSynth runtime or place `fluidsynth.dll` next to the EXE
  * **SoundFont (`.sf2`) — not included. You must provide your own.**

Provide your SoundFont by placing it in the project root (e.g. `FluidR3_GM.sf2`) **or** set:

```bash
export BEARMONY_SF2=/absolute/path/to/Your.sf2      # macOS/Linux
# PowerShell:
# $Env:BEARMONY_SF2 = "C:\path\to\Your.sf2"
```

---

## Quick start

```bash
python3 -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
# .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
python -m bearmony
```

Use the GUI to choose notes/chords/progressions, set arpeggio/tempo/velocity, pick an instrument, and export MIDI.

---

## Build

### macOS (.app)

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --windowed --name Bearmony bearmony/__main__.py \
  --add-data "bearmony/data/chord_formulas.json:bearmony/data" \
  --add-data "bearmony/data/progressions.json:bearmony/data" \
  --add-data "bearmony/data/scales.json:bearmony/data"
# Optional zip:
ditto -c -k --sequesterRsrc --keepParent dist/Bearmony.app dist/Bearmony-mac.zip
```

If macOS reports a missing `libfluidsynth`, run `brew install fluid-synth`.

### Windows (.exe)

```powershell
.\.venv\Scripts\activate
pip install pyinstaller
pyinstaller -F -w -n bearmony bearmony\__main__.py `
  --add-data "bearmony\data\chord_formulas.json;bearmony\data" `
  --add-data "bearmony\data\progressions.json;bearmony\data" `
  --add-data "bearmony\data\scales.json;bearmony\data"
```

Provide your `.sf2` at runtime (next to the EXE or via `BEARMONY_SF2`).

---

## Troubleshooting

* `No module named '_tkinter'`: use Python 3.11 from python.org and recreate the venv.
* “No SoundFont found”: place your `.sf2` in the project root or set `BEARMONY_SF2`.
* “No module named bearmony”: run from the project root with `python -m bearmony`.

---

## License

MIT — DIY / IW / GL
