# Bearmony MIDI Chord & Progression Tool
# Author: Jeremy Lesniewski

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import tkinter.font as tkfont
import threading
import time
import random
import mido

try:
    import fluidsynth
    HAVE_FLUID = True
except Exception:
    HAVE_FLUID = False

from importlib import resources

def _find_sf2():
    # 1) env override
    env = os.environ.get("BEARMONY_SF2")
    if env and os.path.isfile(env):
        return env

    here = os.path.dirname(__file__)                               # bearmony/gui
    project_root = os.path.abspath(os.path.join(here, "..", "..")) # repo root
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else None
    meipass = getattr(sys, "_MEIPASS", None)                       # PyInstaller data dir

    candidates = [project_root, here, os.getcwd(), exe_dir, meipass]
    names = ["FluidR3_GM.sf2"]  # try exact first

    for d in [p for p in candidates if p and os.path.isdir(p)]:
        for name in names:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
        for f in os.listdir(d):
            if f.lower().endswith(".sf2"):
                return os.path.join(d, f)
    return None

def load_json(fname):
    try:
        with resources.files("bearmony.data").joinpath(fname).open("r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                raise json.JSONDecodeError("Empty JSON", fname, 0)
            return data
    except FileNotFoundError:
        messagebox.showerror("Error", f"'{fname}' not found inside package data.")
        sys.exit(1)
    except json.JSONDecodeError:
        messagebox.showerror("Error", f"'{fname}' is empty or contains invalid JSON")
        sys.exit(1)

CHORD_FORMULAS = load_json("chord_formulas.json")
PROGRESSIONS   = load_json("progressions.json")

ALL_NOTES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
INSTRUMENTS = {
    "Acoustic Piano": 0, "Electric Piano": 4, "Organ": 100, "Hammond Organ": 19,
    "Acoustic Grand": 1, "Bright Acoustic": 2, "Electric Grand": 3, "Honky Tonk": 5,
    "Acoustic Guitar": 24, "Electric Guitar": 27, "Bass": 32,
    "Violin": 40, "Cello": 42, "Trumpet": 56, "Sax": 64
}
OFFSET_MAP = {"I":0,"II":2,"III":4,"IV":5,"V":7,"VI":9,"VII":11}

CHORD_DEFINITIONS = {}
for name, intervals in CHORD_FORMULAS.items():
    CHORD_DEFINITIONS.setdefault(len(intervals), {})[name] = intervals

def roman_to_offset(r):
    r = r.replace('♭','b').replace('♯','#')
    accidental = 0
    if r.startswith('b'):
        accidental = -1; r = r[1:]
    elif r.startswith('#'):
        accidental = 1; r = r[1:]
    roman = r.upper()
    if roman not in OFFSET_MAP:
        raise ValueError(f"Invalid Roman numeral: {r}")
    return (OFFSET_MAP[roman] + accidental) % 12

class MidiApp:
    def __init__(self, root):
        self.root = root
        self.pitch_octave_var = tk.IntVar(value=0)
        self.root.title("Bearmony")  # Program title
        self.root.tk.call('tk', 'scaling', 1.0)
        for fn in ["TkDefaultFont","TkMenuFont","TkHeadingFont","TkTooltipFont"]:
            try:
                tkfont.nametofont(fn).configure(size=10)
            except Exception:
                pass

        # ---- SoundFont handling ----
        self.fs = None
        if HAVE_FLUID:
            sf = _find_sf2()   # <<< use the top-level helper (handles _MEIPASS)
            if sf:
                self.fs = fluidsynth.Synth(samplerate=44100)
                self.fs.start()
                self.sf_id = self.fs.sfload(sf)
                self.fs.program_select(0, self.sf_id, 0, 0)
            else:
                messagebox.showwarning(
                    "SoundFont not found",
                    "No .sf2 SoundFont found. Live playback disabled.\n"
                    "Export to MIDI still works. Put a .sf2 next to the app/EXE or set BEARMONY_SF2."
                )
        else:
            messagebox.showwarning(
                "Fluidsynth not available",
                "pyfluidsynth/fluidsynth not installed. Live playback disabled.\n"
                "Export to MIDI still works."
            )

        self.playing = False
        self.stop_event = None

        # Variables
        self.root_note_var = tk.StringVar(value=ALL_NOTES[0])
        self.chord_size_var = tk.IntVar(value=3)
        self.chord_type_var = tk.StringVar()
        self.note_value_var = tk.IntVar(value=4)
        self.swing_var = tk.DoubleVar(value=0.0)
        self.instrument_var = tk.StringVar(value=list(INSTRUMENTS.keys())[0])
        self.playback_mode_var = tk.StringVar(value="Chord")
        self.progression_var = tk.StringVar(value=list(PROGRESSIONS.keys())[0])
        self.tempo_var = tk.IntVar(value=120)
        self.velocity_mode_var = tk.StringVar(value="Dynamic")
        self.volume_var = tk.IntVar(value=100)
        self.loop_var = tk.BooleanVar(value=False)
        self.reverb_room_var = tk.DoubleVar(value=0.5)
        self.reverb_damp_var = tk.DoubleVar(value=0.5)
        self.reverb_level_var = tk.DoubleVar(value=0.2)
        self.loop_count_var = tk.IntVar(value=4)
        self.duration_seconds_var = tk.IntVar(value=0)
        self.current_notes_var = tk.StringVar(value="")

        self.loop_count_var.trace_add('write', self.update_duration)
        self.tempo_var.trace_add('write', self.update_duration)
        self.note_value_var.trace_add('write', self.update_duration)
        self.playback_mode_var.trace_add('write', self.update_duration)
        self.chord_size_var.trace_add('write', self.update_duration)

        self.build_ui()
        self.update_chord_types()
        self.update_duration()

    # -------- UI --------
    def build_ui(self):
        main = ttk.Frame(self.root, padding=5)
        main.pack(fill='both', expand=True)

        chord_frame = ttk.LabelFrame(main, text="Chord", padding=5)
        chord_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)

        ttk.Label(chord_frame, text="Root Note:").grid(row=0, column=0, sticky='w')
        ttk.Combobox(chord_frame, textvariable=self.root_note_var, values=ALL_NOTES, state='readonly', width=6).grid(row=0, column=1)

        ttk.Label(chord_frame, text="Chord Size:").grid(row=1, column=0, sticky='w')
        size_cb = ttk.Combobox(chord_frame, textvariable=self.chord_size_var, values=sorted(CHORD_DEFINITIONS.keys()), state='readonly', width=6)
        size_cb.grid(row=1, column=1)
        size_cb.bind('<<ComboboxSelected>>', lambda e: self.update_chord_types())

        ttk.Label(chord_frame, text="Chord Type:").grid(row=2, column=0, sticky='w')
        self.chord_cb = ttk.Combobox(chord_frame, textvariable=self.chord_type_var, state='readonly', width=8)
        self.chord_cb.grid(row=2, column=1)

        ttk.Label(chord_frame, text="Pitch Octave:").grid(row=5, column=0, sticky='w')
        ttk.Spinbox(chord_frame, from_=-4, to=4, textvariable=self.pitch_octave_var, width=6, state='readonly').grid(row=5, column=1, sticky='w')

        values_frame = ttk.LabelFrame(main, text="Values", padding=5)
        values_frame.grid(row=0, column=1, sticky='nsew', padx=5, pady=5)

        ttk.Label(values_frame, text="Mode:").grid(row=0, column=0, sticky='w')
        ttk.Combobox(values_frame, textvariable=self.playback_mode_var, values=["Chord","Arpeggio Asc","Arpeggio Desc","Up-Down","Random Arp"], state='readonly', width=12).grid(row=0, column=1)

        ttk.Label(values_frame, text="Progression:").grid(row=1, column=0, sticky='w')
        ttk.Combobox(values_frame, textvariable=self.progression_var, values=list(PROGRESSIONS.keys()), state='readonly', width=12).grid(row=1, column=1)

        ttk.Label(values_frame, text="Tempo (BPM):").grid(row=2, column=0, sticky='w')
        ttk.Entry(values_frame, textvariable=self.tempo_var, width=6).grid(row=2, column=1, sticky='w')

        ttk.Label(values_frame, text="Note Value:").grid(row=3, column=0, sticky='w')
        ttk.Combobox(values_frame, textvariable=self.note_value_var, values=[1,2,4,8,16], state='readonly', width=6).grid(row=3, column=1)

        ttk.Label(values_frame, text="Velocity:").grid(row=4, column=0, sticky='w')
        ttk.Combobox(values_frame, textvariable=self.velocity_mode_var, values=["Light","Normal","Strong","Dynamic"], state='readonly', width=10).grid(row=4, column=1)

        instrument_frame = ttk.LabelFrame(main, text="Instrument", padding=5)
        instrument_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=5, pady=5)

        ttk.Label(instrument_frame, text="Select:").grid(row=0, column=0, sticky='w')
        ttk.Combobox(instrument_frame, textvariable=self.instrument_var, values=list(INSTRUMENTS.keys()), state='readonly', width=20).grid(row=0, column=1, sticky='w')

        playback_frame = ttk.LabelFrame(main, text="Playback", padding=5)
        playback_frame.grid(row=2, column=0, columnspan=2, sticky='nsew', padx=5, pady=5)

        ttk.Button(playback_frame, text="▶ Chord", command=self.play_chord, width=10).grid(row=0, column=0, padx=5)
        ttk.Button(playback_frame, text="▶ Progression", command=self.jam_progression, width=10).grid(row=0, column=1, padx=5)
        ttk.Button(playback_frame, text="⏹ Stop", command=self.stop_play, width=10).grid(row=0, column=2, padx=5)
        ttk.Checkbutton(playback_frame, text="Loop", variable=self.loop_var).grid(row=1, column=0, sticky='w')

        ttk.Label(playback_frame, text="Volume (dB):").grid(row=1, column=1, sticky='e')
        vol_scale = ttk.Scale(playback_frame, from_=0, to=127, variable=self.volume_var, orient='horizontal', length=100)
        vol_scale.grid(row=1, column=2, sticky='w')

        def update_volume_label(*args):
            vol_db = int((self.volume_var.get()/127)*60)
            self.volume_db_label.config(text=f"-{60 - vol_db} dB")

        self.volume_var.trace_add('write', update_volume_label)
        self.volume_db_label = ttk.Label(playback_frame, text="-0 dB")
        self.volume_db_label.grid(row=1, column=3, sticky='w')

        effects_frame = ttk.LabelFrame(main, text="Effects", padding=5)
        effects_frame.grid(row=3, column=0, sticky='nsew', padx=5, pady=5)

        ttk.Label(effects_frame, text="Reverb Room:").grid(row=0, column=0, sticky='w')
        ttk.Scale(effects_frame, from_=0, to=1, variable=self.reverb_room_var, orient='horizontal', length=100).grid(row=0, column=1)

        ttk.Label(effects_frame, text="Damp:").grid(row=1, column=0, sticky='w')
        ttk.Scale(effects_frame, from_=0, to=1, variable=self.reverb_damp_var, orient='horizontal', length=100).grid(row=1, column=1)

        ttk.Label(effects_frame, text="Level:").grid(row=2, column=0, sticky='w')
        ttk.Scale(effects_frame, from_=0, to=1, variable=self.reverb_level_var, orient='horizontal', length=100).grid(row=2, column=1)

        export_frame = ttk.LabelFrame(main, text="Export", padding=5)
        export_frame.grid(row=3, column=1, sticky='nsew', padx=5, pady=5)

        ttk.Label(export_frame, text="Loops:").grid(row=0, column=0, sticky='w')
        loop_slider = ttk.Scale(export_frame, from_=1, to=20, variable=self.loop_count_var, orient='horizontal', length=100)
        loop_slider.grid(row=0, column=1, sticky='w')

        ttk.Label(export_frame, text="Duration (s):").grid(row=1, column=0, sticky='w')
        duration_label = ttk.Label(export_frame, textvariable=self.duration_seconds_var)
        duration_label.grid(row=1, column=1, sticky='w')

        ttk.Button(export_frame, text="Chord MIDI", command=self.export_chord_midi, width=12).grid(row=2, column=0, pady=2)
        ttk.Button(export_frame, text="Prog MIDI",  command=self.export_prog_midi,  width=12).grid(row=2, column=1, pady=2)

        indicator_frame = ttk.LabelFrame(main, text="Current Values", padding=5)
        indicator_frame.grid(row=4, column=0, columnspan=2, sticky='ew', padx=5, pady=5)
        ttk.Label(indicator_frame, textvariable=self.current_notes_var).grid(row=0, column=0, sticky='w')

    def midi_to_note_name(self, midi_num):
        return ALL_NOTES[midi_num % 12] + str(midi_num // 12 - 1)

    def update_duration(self, *args):
        loops = self.loop_count_var.get()
        bpm = self.tempo_var.get()
        note_value = self.note_value_var.get()
        mode = self.playback_mode_var.get()
        beat_duration = 60 / bpm
        single_event_duration = beat_duration * (4 / note_value)
        intervals = CHORD_DEFINITIONS[self.chord_size_var.get()][self.chord_type_var.get()]
        chord_length = len(intervals)
        if mode == 'Chord':
            total_duration = single_event_duration * loops
        elif mode == 'Up-Down':
            total_duration = single_event_duration * (chord_length * 2 - 1) * loops
        else:
            total_duration = single_event_duration * chord_length * loops
        self.duration_seconds_var.set(int(total_duration))

    def update_indicator(self, notes):
        mode = self.playback_mode_var.get()
        if mode == 'Chord':
            notes_str = ', '.join(self.midi_to_note_name(n) for n in notes)
        else:
            if mode == 'Arpeggio Asc':   seq_notes = notes
            elif mode == 'Arpeggio Desc':seq_notes = notes[::-1]
            elif mode == 'Up-Down':      seq_notes = notes + notes[::-1][1:]
            elif mode == 'Random Arp':   seq_notes = random.sample(notes, len(notes))
            else:                         seq_notes = notes
            notes_str = ', '.join(self.midi_to_note_name(n) for n in seq_notes)
        tempo = self.tempo_var.get()
        pitch = self.pitch_octave_var.get()
        chord_type = self.chord_type_var.get()
        chord_size = self.chord_size_var.get()
        info = f"Notes: {notes_str} | Tempo: {tempo} BPM | Pitch: {pitch} oct | Chord: {chord_type} ({chord_size})"
        self.current_notes_var.set(info)

    def update_chord_types(self):
        types = list(CHORD_DEFINITIONS[self.chord_size_var.get()].keys())
        self.chord_cb['values'] = types
        self.chord_type_var.set(types[0])

    def _get_chord_midis(self, root, intervals):
        pitch_shift = self.pitch_octave_var.get() * 12
        base = 60 + ALL_NOTES.index(root) + pitch_shift
        return [base + i for i in intervals]

    def _apply_fx(self):
        if self.fs:
            self.fs.set_reverb(self.reverb_room_var.get(), self.reverb_damp_var.get(), 0.5, self.reverb_level_var.get())

    def _get_velocity(self):
        vol = self.volume_var.get()
        mode = self.velocity_mode_var.get()
        if mode == 'Light':  return max(1, int(vol * 0.5))
        if mode == 'Normal': return max(1, int(vol * 0.75))
        if mode == 'Strong': return vol
        return random.randint(max(1, int(vol * 0.5)), vol)

    def _play_notes(self, notes, dur):
        if not self.fs:
            time.sleep(dur)  # no fluidsynth; just wait to keep timing consistent
            return
        mode = self.playback_mode_var.get()
        swing = self.swing_var.get()
        if mode == 'Chord':
            vel = self._get_velocity()
            for n in notes: self.fs.noteon(0, n, vel)
            time.sleep(dur)
            for n in notes: self.fs.noteoff(0, n)
        else:
            seq_map = {'Arpeggio Asc': notes, 'Arpeggio Desc': notes[::-1],
                       'Up-Down': notes + notes[::-1][1:], 'Random Arp': random.sample(notes, len(notes))}
            seq = seq_map.get(mode, notes)
            if seq:
                step = dur / len(seq)
                for i, n in enumerate(seq):
                    vel = self._get_velocity()
                    self.fs.noteon(0, n, vel)
                    dt = step
                    if swing and len(seq) > 1:
                        ratio = 1+swing if i%2==0 else 1-swing
                        dt = step * ratio
                    time.sleep(dt)
                    self.fs.noteoff(0, n)

    def play_loop(self, notes):
        beat = 60.0 / self.tempo_var.get()
        dur = beat * (4.0 / self.note_value_var.get())
        self._apply_fx()
        while not self.stop_event.is_set():
            self._play_notes(notes, dur)
            if not self.loop_var.get(): break
        self.playing = False

    def play_chord(self):
        if self.playing: return
        intervals = CHORD_DEFINITIONS[self.chord_size_var.get()][self.chord_type_var.get()]
        notes = self._get_chord_midis(self.root_note_var.get(), intervals)
        if self.fs:
            prog = INSTRUMENTS[self.instrument_var.get()]
            self.fs.program_select(0, self.sf_id, 0, prog)
        self.update_indicator(notes)
        self.stop_event = threading.Event()
        self.playing = True
        threading.Thread(target=self.play_loop, args=(notes,), daemon=True).start()

    def stop_play(self):
        if self.playing:
            self.stop_event.set()

    def jam_progression(self):
        if self.playing: return
        romans = PROGRESSIONS[self.progression_var.get()]
        base_idx = ALL_NOTES.index(self.root_note_var.get())
        intervals = CHORD_DEFINITIONS[self.chord_size_var.get()][self.chord_type_var.get()]
        self.stop_event = threading.Event()
        self.playing = True
        def prog():
            if self.fs:
                prog_id = INSTRUMENTS[self.instrument_var.get()]
                self.fs.program_select(0, self.sf_id, 0, prog_id)
            self._apply_fx()
            beat = 60.0 / self.tempo_var.get()
            dur = beat * (4.0 / self.note_value_var.get())
            for r in romans:
                offset = roman_to_offset(r)
                root_midi = 60 + base_idx + offset
                notes = [root_midi + i for i in intervals]
                self.update_indicator(notes)
                self._play_notes(notes, dur)
                if self.stop_event.is_set():
                    break
            self.playing = False
        threading.Thread(target=prog, daemon=True).start()

    def export_chord_midi(self):
        intervals = CHORD_DEFINITIONS[self.chord_size_var.get()][self.chord_type_var.get()]
        notes = self._get_chord_midis(self.root_note_var.get(), intervals)
        fn = filedialog.asksaveasfilename(defaultextension='.mid', filetypes=[('MIDI','*.mid')])
        if not fn: return
        mid = mido.MidiFile(); tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(self.tempo_var.get())))
        ticks = mid.ticks_per_beat
        note_ticks = int(ticks * (4.0 / self.note_value_var.get()))
        mode = self.playback_mode_var.get()
        if mode == 'Chord':
            seq_notes = [notes]
        else:
            seq_map = {'Arpeggio Asc': notes, 'Arpeggio Desc': notes[::-1],
                       'Up-Down': notes + notes[::-1][1:], 'Random Arp': random.sample(notes, len(notes))}
            seq = seq_map.get(mode, notes); seq_notes = [[n] for n in seq]
        loops = self.loop_count_var.get()
        for _ in range(loops):
            for chord_notes in seq_notes:
                vel = self._get_velocity()
                for n in chord_notes:
                    tr.append(mido.Message('note_on', note=n, velocity=vel, time=0))
                tr.append(mido.Message('note_off', note=chord_notes[0], velocity=0, time=note_ticks))
                for n in chord_notes[1:]:
                    tr.append(mido.Message('note_off', note=n, velocity=0, time=0))
        mid.save(fn)

    def export_prog_midi(self):
        romans = PROGRESSIONS[self.progression_var.get()]
        base_idx = ALL_NOTES.index(self.root_note_var.get())
        intervals = CHORD_DEFINITIONS[self.chord_size_var.get()][self.chord_type_var.get()]
        fn = filedialog.asksaveasfilename(defaultextension='.mid', filetypes=[('MIDI','*.mid')])
        if not fn: return
        mid = mido.MidiFile(); tr = mido.MidiTrack(); mid.tracks.append(tr)
        tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(self.tempo_var.get())))
        ticks = mid.ticks_per_beat
        note_ticks = int(ticks * (4.0 / self.note_value_var.get()))
        mode = self.playback_mode_var.get()
        loops = self.loop_count_var.get()
        for _ in range(loops):
            for r in romans:
                offset = roman_to_offset(r)
                root_midi = 60 + base_idx + offset
                chord = [root_midi + i for i in intervals]
                if mode == 'Chord':
                    seq_notes = [chord]
                else:
                    seq_map = {'Arpeggio Asc': chord, 'Arpeggio Desc': chord[::-1],
                               'Up-Down': chord + chord[::-1][1:], 'Random Arp': random.sample(chord, len(chord))}
                    seq = seq_map.get(mode, chord); seq_notes = [[n] for n in seq]
                for chord_notes in seq_notes:
                    vel = self._get_velocity()
                    for n in chord_notes:
                        tr.append(mido.Message('note_on', note=n, velocity=vel, time=0))
                    tr.append(mido.Message('note_off', note=chord_notes[0], velocity=0, time=note_ticks))
                    for n in chord_notes[1:]:
                        tr.append(mido.Message('note_off', note=n, velocity=0, time=0))
        mid.save(fn)

    def close(self):
        self.stop_play()
        if self.fs:
            self.fs.delete()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = MidiApp(root)
    root.protocol('WM_DELETE_WINDOW', app.close)
    root.mainloop()

if __name__ == "__main__":
    main()
