## **BEARMONY MidiGen (Demo)** — MIDI Chord, Arpeggio & Progression Tool

**Bearmony** MidiGen (Demo) – a simple program with a library of all musical chord and scale combinations, featuring real-time playback on various instruments and the ability to create MIDI files for songwriting.

Use the GUI to choose notes/chords/progressions, set arpeggio/tempo/velocity/note value for playback, pick an instrument, and export MIDI.

## Features
- Chords and full progressions
- Arpeggios (Asc/Desc/Up-Down/Random)
- Tempo, note value, velocity, loop count, basic FX
- General MIDI instrument selection
- Live playback (FluidSynth + SoundFont)
- MIDI export (chord or progression)
- Modern UI: Mode, Progression, and Note Value selection grouped together for workflow
- Chord display always shows as "Cmaj7" in a fixed-size box

## Requirements
- Python **3.11** recommended (3.8+ supported).  
- Install deps:
```
pip install -r requirements.txt
```

* For playback you need:

  * **FluidSynth**

    * macOS: `brew install fluid-synth`
    * Windows: install a FluidSynth runtime or place `fluidsynth.dll` next to the EXE
  * **SoundFont (`.sf2`) — not included. You must provide your own.**

SoundFont resolution:
- Place your SoundFont in the project root (e.g. `FluidR3_GM.sf2`, `GeneralUser.sf2`, or `soundfont.sf2`)
- Or set the environment variable:

```bash
export BEARMONY_SF2=/absolute/path/to/Your.sf2      # macOS/Linux
# PowerShell:
# $Env:BEARMONY_SF2 = "C:\path\to\Your.sf2"
```

The app will automatically detect the SoundFont using the above logic.

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

---

## UI Overview
- Chord Selection: Choose root note, chord size, and chord type
- Chord Display: Shows the current chord as "Cmaj7" in a fixed-size box
- Mode & Progression: Select playback mode, progression, and note value (all grouped together)
- Instrument Settings: Pick instrument, pitch octave, and velocity
- Effects: Reverb controls
- Export: Set tempo, tacts, and export MIDI
- Playback Control: Play chord/progression, stop, and loop

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
