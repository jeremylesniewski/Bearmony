## **Bearmony MidiGen (Beta)** — MIDI Chord, Arpeggio & Progression Tool

**Bearmony MidiGen (Beta)** – a simple program with a library of all musical chord and scale combinations, featuring real-time playback on various instruments and the ability to create MIDI files for songwriting.

Use the GUI to choose notes/chords/progressions, set arpeggio/tempo/velocity for playbacn, pick an instrument, and export MIDI.

## Features
- Chords and full progressions
- Arpeggios (Asc/Desc/Up-Down/Random)
- Tempo, note value, velocity, loop count, basic FX
- General MIDI instrument selection
- Live playback (FluidSynth + SoundFont)
- MIDI export (chord or progression)


## Requirements
- Python **3.11** recommended (3.8+ supported).  
- Install deps:
````
pip install -r requirements.txt
````


* For playback you need:
  * **FluidSynth**
    * macOS: `brew install fluid-synth`
    * Windows: install a FluidSynth runtime or place `fluidsynth.dll` next to the EXE
  * **SoundFont (`.sf2`) — Bearmony now ships with a redistributable General MIDI SoundFont (MIT-licensed, MuseScore General or FluidR3_GM).**

Bearmony will automatically find and use the bundled SoundFont. Advanced users can override the SoundFont by setting:

```bash
export BEARMONY_SF2=/absolute/path/to/Your.sf2      # macOS/Linux
# PowerShell:
# $Env:BEARMONY_SF2 = "C:\path\to\Your.sf2"
```
Or via Settings → "Choose SoundFont…" in the app.

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

## Build

### macOS (.app)

```bash
source .venv/bin/activate
pip install pyinstaller
pyinstaller --windowed --name Bearmony bearmony/__main__.py \
  --add-data "bearmony/data/chord_formulas.json:bearmony/data" \
  --add-data "bearmony/data/progressions.json:bearmony/data" \
  --add-data "bearmony/data/scales.json:bearmony/data" \
  --add-data "bearmony/assets/soundfonts/FluidR3_GM.sf2:bearmony/assets/soundfonts" \
  --add-data "bearmony/assets/LICENSE_SOUNDFONT.txt:bearmony/assets"
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

Bearmony will use the bundled SoundFont automatically. You can override it by placing your own `.sf2` next to the EXE or setting `BEARMONY_SF2`.

---

## Troubleshooting

* `No module named '_tkinter'`: use Python 3.11 from python.org and recreate the venv.
* “No SoundFont found”: This should not occur unless you override the default and the file is missing. By default, Bearmony ships with a working SoundFont. If you override, set `BEARMONY_SF2` or use Settings → "Choose SoundFont…".
* “No module named bearmony”: run from the project root with `python -m bearmony`.

---

## License

MIT — DIY / IW / GL
