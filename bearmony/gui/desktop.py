"""Bearmony MIDI Chord & Progression Tool"""

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
        # Set app logo, always override default Python icon
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "images", "logo.png")
            if os.path.isfile(logo_path):
                logo_img = tk.PhotoImage(file=logo_path)
                self.root.iconphoto(True, logo_img)
            else:
                # Set a blank icon if logo is missing
                blank_img = tk.PhotoImage(width=1, height=1)
                self.root.iconphoto(True, blank_img)
        except Exception as e:
            print(f"Could not set app logo: {e}")
        self.fs = None
        self.sf2_path = None
        self.sf_id = None
        self.playing = False
        self.stop_event = None
        self.played_notes_history = []
        # Tkinter variables
        self.root_note_var = tk.StringVar(value=ALL_NOTES[0])
        self.chord_size_var = tk.IntVar(value=3)
        self.chord_type_var = tk.StringVar()
        self.instrument_var = tk.StringVar(value=list(INSTRUMENTS.keys())[0])
        self.pitch_octave_var = tk.IntVar(value=0)
        self.velocity_mode_var = tk.StringVar(value="Normal")
        self.note_value_var = tk.IntVar(value=4)
        self.tempo_var = tk.IntVar(value=120)
        self.swing_var = tk.DoubleVar(value=0)
        self.loop_var = tk.BooleanVar(value=False)
        self.progression_var = tk.StringVar(value=list(PROGRESSIONS.keys())[0])
        self.reverb_room_var = tk.DoubleVar(value=0.5)
        self.reverb_damp_var = tk.DoubleVar(value=0.5)
        self.reverb_level_var = tk.DoubleVar(value=0.5)
        self.volume_var = tk.IntVar(value=100)
        self.playback_mode_var = tk.StringVar(value="Chord")
        self.loop_count_var = tk.IntVar(value=1)
        self.duration_seconds_var = tk.IntVar(value=0)
        # Build UI
        self.build_ui()
    def choose_sf2(self):
        path = filedialog.askopenfilename(title="Select SoundFont (.sf2)", filetypes=[("SoundFont Files", "*.sf2")])
        if path:
            self.sf2_path = path
            if HAVE_FLUID:
                if self.fs:
                    self.fs.delete()
                self.fs = fluidsynth.Synth()
                self.fs.start(driver='coreaudio')  # macOS default
                self.sf_id = self.fs.sfload(self.sf2_path)
                prog = INSTRUMENTS[self.instrument_var.get()]

    def build_ui(self):
        self.root.title("Bearmony MidiGen Beta")
        main = ttk.Frame(self.root, padding=4)
        main.pack(fill='both', expand=True)

        menubar = tk.Menu(self.root)
        audio_menu = tk.Menu(menubar, tearoff=0)
        audio_menu.add_command(label="Choose SoundFont…", command=self.choose_sf2)
        menubar.add_cascade(label="Audio", menu=audio_menu)
        self.root.config(menu=menubar)

        # Chord Selection and Chord Display (side by side)
        chord_sel_frame = ttk.LabelFrame(main, text="Chord Selection", padding=4)
        chord_sel_frame.grid(row=0, column=0, sticky='nsew', padx=2, pady=2)
        chord_sel_frame.columnconfigure(0, weight=1)
        chord_sel_frame.columnconfigure(1, weight=1)
        # Parameters (left)
        param_frame = ttk.Frame(chord_sel_frame)
        param_frame.grid(row=0, column=0, sticky='nsew')
        ttk.Label(param_frame, text="Root Note:").grid(row=0, column=0, sticky='w')
        ttk.Combobox(param_frame, textvariable=self.root_note_var, values=ALL_NOTES, state='readonly').grid(row=0, column=1, sticky='ew')
        ttk.Label(param_frame, text="Chord Size:").grid(row=1, column=0, sticky='w')
        size_cb = ttk.Combobox(param_frame, textvariable=self.chord_size_var, values=sorted(CHORD_DEFINITIONS.keys()), state='readonly')
        size_cb.grid(row=1, column=1, sticky='ew')
        size_cb.bind('<<ComboboxSelected>>', lambda e: self.update_chord_types())
        ttk.Label(param_frame, text="Chord Type:").grid(row=2, column=0, sticky='w')
        self.chord_cb = ttk.Combobox(param_frame, textvariable=self.chord_type_var, state='readonly')
        self.chord_cb.grid(row=2, column=1, sticky='ew')
        # Chord Display (right, locked size box)
        chord_display_frame = ttk.Frame(chord_sel_frame, relief='ridge', borderwidth=2, width=120, height=60)
        chord_display_frame.grid(row=0, column=1, sticky='nsew', padx=(10,0))
        chord_display_frame.grid_propagate(False)
        chord_display_frame.rowconfigure(0, weight=1)
        chord_display_frame.columnconfigure(0, weight=1)
        self.chord_display_var = tk.StringVar()
        self.chord_name_label = ttk.Label(
            chord_display_frame,
            textvariable=self.chord_display_var,
            font=("TkDefaultFont", 16),
            anchor='center',
            background='#f0f0f0',
            width=10
        )
        self.chord_name_label.grid(row=0, column=0, sticky='nsew', ipadx=10, ipady=20)
        def update_chord_display(*args):
            note = self.root_note_var.get()
            ctype = self.chord_type_var.get()
            self.chord_display_var.set(f"{note}{ctype}")
        self.root_note_var.trace_add('write', update_chord_display)
        self.chord_type_var.trace_add('write', update_chord_display)
        update_chord_display()

        # Mode & Progression section (above export)
        mode_prog_frame = ttk.LabelFrame(main, text="Mode & Progression", padding=4)
        mode_prog_frame.grid(row=1, column=0, sticky='ew', padx=2, pady=2)
        mode_prog_frame.columnconfigure(0, weight=1)
        mode_prog_frame.columnconfigure(1, weight=1)
        ttk.Label(mode_prog_frame, text="Mode:").grid(row=0, column=0, sticky='w')
        ttk.Combobox(mode_prog_frame, textvariable=self.playback_mode_var, values=["Chord","Arpeggio Asc","Arpeggio Desc","Up-Down","Random Arp"], state='readonly').grid(row=0, column=1, sticky='ew')
        ttk.Label(mode_prog_frame, text="Progression:").grid(row=1, column=0, sticky='w')
        ttk.Combobox(mode_prog_frame, textvariable=self.progression_var, values=list(PROGRESSIONS.keys()), state='readonly').grid(row=1, column=1, sticky='ew')
        ttk.Label(mode_prog_frame, text="Note Value:").grid(row=2, column=0, sticky='w')
        ttk.Combobox(mode_prog_frame, textvariable=self.note_value_var, values=[1,2,4,8,16], state='readonly').grid(row=2, column=1, sticky='ew')

        # Export section (bottom left)
        export_frame = ttk.LabelFrame(main, text="Export", padding=4)
        export_frame.grid(row=2, column=0, sticky='ew', padx=2, pady=2)
        export_frame.columnconfigure(0, weight=1)
        export_frame.columnconfigure(1, weight=1)
        ttk.Label(export_frame, text="Tempo (BPM):").grid(row=0, column=0, sticky='w')
        self.export_tempo_var = tk.IntVar(value=self.tempo_var.get())
        tempo_entry = ttk.Entry(export_frame, textvariable=self.export_tempo_var)
        tempo_entry.grid(row=0, column=1, sticky='ew')
        ttk.Label(export_frame, text="Length (tacts):").grid(row=1, column=0, sticky='w')
        self.export_tacts_var = tk.IntVar(value=4)
        tacts_slider = ttk.Scale(export_frame, from_=1, to=32, variable=self.export_tacts_var, orient='horizontal')
        tacts_slider.grid(row=1, column=1, sticky='ew')
        tacts_slider.config(command=lambda v: self.export_tacts_var.set(int(float(v))))
        self.tacts_label = ttk.Label(export_frame, text=f"Tacts: {self.export_tacts_var.get()}")
        self.tacts_label.grid(row=2, column=0, columnspan=2, sticky='ew')
        def update_tacts_label(*args):
            self.tacts_label.config(text=f"Tacts: {self.export_tacts_var.get()}")
        self.export_tacts_var.trace_add('write', update_tacts_label)
        ttk.Label(export_frame, text="Duration (s):").grid(row=3, column=0, sticky='w')
        self.export_duration_var = tk.StringVar(value="0")
        duration_label = ttk.Label(export_frame, textvariable=self.export_duration_var)
        duration_label.grid(row=3, column=1, sticky='ew')
        def update_export_duration(*args):
            bpm = self.export_tempo_var.get()
            tacts = self.export_tacts_var.get()
            seconds = (tacts * 4 * 60) / bpm if bpm > 0 else 0
            self.export_duration_var.set(f"{seconds:.1f}")
        self.export_tempo_var.trace_add('write', update_export_duration)
        self.export_tacts_var.trace_add('write', update_export_duration)
        update_export_duration()
        self.export_tempo_velocity = tk.BooleanVar(value=True)
        ttk.Checkbutton(export_frame, text="Include velocity info", variable=self.export_tempo_velocity).grid(row=4, column=0, columnspan=2, sticky='ew')
        ttk.Button(export_frame, text="Chord MIDI", command=self.export_chord_midi).grid(row=5, column=0, pady=2, sticky='ew')
        ttk.Button(export_frame, text="Prog MIDI",  command=self.export_prog_midi).grid(row=5, column=1, pady=2, sticky='ew')

        # Playback Section (right, split into three)
        # Instrument Settings
        instr_settings_frame = ttk.LabelFrame(main, text="Instrument Settings", padding=4)
        instr_settings_frame.grid(row=0, column=1, sticky='nsew', padx=2, pady=2)
        instr_settings_frame.columnconfigure(0, weight=1)
        instr_settings_frame.columnconfigure(1, weight=1)
        ttk.Label(instr_settings_frame, text="Pitch Octave:").grid(row=0, column=0, sticky='w')
        ttk.Spinbox(instr_settings_frame, from_=-4, to=4, textvariable=self.pitch_octave_var, state='readonly').grid(row=0, column=1, sticky='ew')
        ttk.Label(instr_settings_frame, text="Instrument:").grid(row=1, column=0, sticky='w')
        ttk.Combobox(instr_settings_frame, textvariable=self.instrument_var, values=list(INSTRUMENTS.keys()), state='readonly').grid(row=1, column=1, sticky='ew')
        ttk.Label(instr_settings_frame, text="Velocity:").grid(row=2, column=0, sticky='w')
        ttk.Combobox(instr_settings_frame, textvariable=self.velocity_mode_var, values=["Light","Normal","Strong","Dynamic"], state='readonly').grid(row=2, column=1, sticky='ew')
    # ...existing code...

        # Effects
        effects_frame = ttk.LabelFrame(main, text="Effects", padding=4)
        effects_frame.grid(row=1, column=1, sticky='nsew', padx=2, pady=2)
        effects_frame.columnconfigure(0, weight=1)
        effects_frame.columnconfigure(1, weight=1)
        ttk.Label(effects_frame, text="Reverb Room:").grid(row=0, column=0, sticky='w')
        ttk.Scale(effects_frame, from_=0, to=1, variable=self.reverb_room_var, orient='horizontal').grid(row=0, column=1, sticky='ew')
        ttk.Label(effects_frame, text="Damp:").grid(row=1, column=0, sticky='w')
            # Instrument Settings
        ttk.Label(effects_frame, text="Level:").grid(row=2, column=0, sticky='w')
        ttk.Scale(effects_frame, from_=0, to=1, variable=self.reverb_level_var, orient='horizontal').grid(row=2, column=1, sticky='ew')

        # Playback Control
        control_frame = ttk.LabelFrame(main, text="Playback Control", padding=4)
        control_frame.grid(row=2, column=1, sticky='nsew', padx=2, pady=2)
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)
        control_frame.columnconfigure(2, weight=1)
        ttk.Button(control_frame, text="▶ Chord", command=self.play_chord).grid(row=0, column=0, padx=2, pady=2, sticky='ew')
        ttk.Button(control_frame, text="▶ Progression", command=self.jam_progression).grid(row=0, column=1, padx=2, pady=2, sticky='ew')
        ttk.Button(control_frame, text="⏹ Stop", command=self.stop_play).grid(row=0, column=2, padx=2, pady=2, sticky='ew')
        ttk.Checkbutton(control_frame, text="Loop", variable=self.loop_var).grid(row=1, column=0, columnspan=3, sticky='w')

        # Notes Played Bar (bottom, spanning window)
        notes_bar_frame = ttk.Frame(main, padding=4, relief='groove')
        notes_bar_frame.grid(row=3, column=0, columnspan=2, sticky='ew', padx=2, pady=2)
        notes_bar_frame.columnconfigure(0, weight=1)
        self.notes_text = tk.Text(notes_bar_frame, height=2, wrap='none', state='disabled', font=('TkDefaultFont', 10))
        self.notes_text.grid(row=0, column=0, sticky='ew')

    # ...existing code...

    def midi_to_note_name(self, midi_num):
        return ALL_NOTES[midi_num % 12] + str(midi_num // 12 - 1)

    def update_duration(self, *args):
        loops = self.loop_count_var.get()
        bpm = self.tempo_var.get()
        note_value = self.note_value_var.get()
        mode = self.playback_mode_var.get()
        beat_duration = 60 / bpm
        single_event_duration = beat_duration * (4 / note_value)
        chord_size = self.chord_size_var.get()
        chord_type = self.chord_type_var.get()
        # Fallback: if chord_type is empty, use the first available type
        if not chord_type:
            chord_type = list(CHORD_DEFINITIONS[chord_size].keys())[0]
            self.chord_type_var.set(chord_type)
        intervals = CHORD_DEFINITIONS[chord_size][chord_type]
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
        notes_str = ', '.join(self.midi_to_note_name(n) for n in notes)
        # Keep all played notes until stop is clicked
        self.played_notes_history.append(notes_str)
        self.notes_text.config(state='normal')
        self.notes_text.delete(1.0, tk.END)
        self.notes_text.insert(tk.END, ' | '.join(self.played_notes_history))
        self.notes_text.config(state='disabled')

    def update_chord_types(self):
        types = list(CHORD_DEFINITIONS[self.chord_size_var.get()].keys())
        self.chord_cb['values'] = types
        if self.chord_type_var.get() not in types:
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
        if self.playing:
            return
        if not HAVE_FLUID:
            messagebox.showerror("Error", "FluidSynth is not available. Please install pyfluidsynth and FluidSynth.")
            return
        if not self.fs or not self.sf_id:
            messagebox.showerror("Error", "No SoundFont loaded. Please select a valid .sf2 file in Settings → Choose SoundFont…")
            return
        chord_size = self.chord_size_var.get()
        chord_type = self.chord_type_var.get()
        if not chord_type or chord_type not in CHORD_DEFINITIONS[chord_size]:
            chord_type = list(CHORD_DEFINITIONS[chord_size].keys())[0]
            self.chord_type_var.set(chord_type)
        intervals = CHORD_DEFINITIONS[chord_size][chord_type]
        notes = self._get_chord_midis(self.root_note_var.get(), intervals)
        prog = INSTRUMENTS[self.instrument_var.get()]
        self.fs.program_select(0, self.sf_id, 0, prog)
        self.update_indicator(notes)
        self.stop_event = threading.Event()
        self.playing = True
        threading.Thread(target=self.play_loop, args=(notes,), daemon=True).start()

    def stop_play(self):
        if self.playing:
            self.stop_event.set()
        # Clear played notes display
        self.played_notes_history = []
        self.notes_text.config(state='normal')
        self.notes_text.delete(1.0, tk.END)
        self.notes_text.config(state='disabled')

    def jam_progression(self):
        if self.playing:
            return
        if not HAVE_FLUID:
            messagebox.showerror("Error", "FluidSynth is not available. Please install pyfluidsynth and FluidSynth.")
            return
        if not self.fs or not self.sf_id:
            messagebox.showerror("Error", "No SoundFont loaded. Please select a valid .sf2 file in Settings → Choose SoundFont…")
            return
        romans = PROGRESSIONS[self.progression_var.get()]
        base_idx = ALL_NOTES.index(self.root_note_var.get())
        intervals = CHORD_DEFINITIONS[self.chord_size_var.get()][self.chord_type_var.get()]
        self.stop_event = threading.Event()
        self.playing = True
        self.played_notes_history = []  # Clear only when a new progression starts
        def prog():
            prog_id = INSTRUMENTS[self.instrument_var.get()]
            self.fs.program_select(0, self.sf_id, 0, prog_id)
            self._apply_fx()
            beat = 60.0 / self.tempo_var.get()
            dur = beat * (4.0 / self.note_value_var.get())
            last_notes_str = None
            for r in romans:
                offset = roman_to_offset(r)
                root_midi = 60 + base_idx + offset
                notes = [root_midi + i for i in intervals]
                notes_str = ', '.join(self.midi_to_note_name(n) for n in notes)
                if notes_str != last_notes_str:
                    self.update_indicator(notes)
                    last_notes_str = notes_str
                self._play_notes(notes, dur)
                if self.stop_event.is_set():
                    break
            self.playing = False
        threading.Thread(target=prog, daemon=True).start()

    def export_chord_midi(self):
        chord_size = self.chord_size_var.get()
        chord_type = self.chord_type_var.get()
        if not chord_type or chord_type not in CHORD_DEFINITIONS[chord_size]:
            chord_type = list(CHORD_DEFINITIONS[chord_size].keys())[0]
            self.chord_type_var.set(chord_type)
        intervals = CHORD_DEFINITIONS[chord_size][chord_type]
        notes = self._get_chord_midis(self.root_note_var.get(), intervals)
        fn = filedialog.asksaveasfilename(defaultextension='.mid', filetypes=[('MIDI','*.mid')])
        if not fn: return
        mid = mido.MidiFile(); tr = mido.MidiTrack(); mid.tracks.append(tr)
        bpm = self.export_tempo_var.get()
        if self.export_tempo_velocity.get():
            tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
        ticks = mid.ticks_per_beat
        note_ticks = int(ticks * 4)  # 1 tact = 4 beats
        mode = self.playback_mode_var.get()
        if mode == 'Chord':
            seq_notes = [notes]
        else:
            seq_map = {'Arpeggio Asc': notes, 'Arpeggio Desc': notes[::-1],
                       'Up-Down': notes + notes[::-1][1:], 'Random Arp': random.sample(notes, len(notes))}
            seq = seq_map.get(mode, notes); seq_notes = [[n] for n in seq]
        tacts = self.export_tacts_var.get()
        for _ in range(tacts):
            for chord_notes in seq_notes:
                vel = self._get_velocity() if self.export_tempo_velocity.get() else 100
                for n in chord_notes:
                    tr.append(mido.Message('note_on', note=n, velocity=vel, time=0))
                tr.append(mido.Message('note_off', note=chord_notes[0], velocity=0, time=note_ticks))
                for n in chord_notes[1:]:
                    tr.append(mido.Message('note_off', note=n, velocity=0, time=0))
        mid.save(fn)

    def export_prog_midi(self):
        romans = PROGRESSIONS[self.progression_var.get()]
        base_idx = ALL_NOTES.index(self.root_note_var.get())
        chord_size = self.chord_size_var.get()
        chord_type = self.chord_type_var.get()
        if not chord_type or chord_type not in CHORD_DEFINITIONS[chord_size]:
            chord_type = list(CHORD_DEFINITIONS[chord_size].keys())[0]
            self.chord_type_var.set(chord_type)
        intervals = CHORD_DEFINITIONS[chord_size][chord_type]
        fn = filedialog.asksaveasfilename(defaultextension='.mid', filetypes=[('MIDI','*.mid')])
        if not fn: return
        mid = mido.MidiFile(); tr = mido.MidiTrack(); mid.tracks.append(tr)
        bpm = self.export_tempo_var.get()
        if self.export_tempo_velocity.get():
            tr.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
        ticks = mid.ticks_per_beat
        note_ticks = int(ticks * 4)  # 1 tact = 4 beats
        mode = self.playback_mode_var.get()
        tacts = self.export_tacts_var.get()
        for _ in range(tacts):
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
                    vel = self._get_velocity() if self.export_tempo_velocity.get() else 100
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
