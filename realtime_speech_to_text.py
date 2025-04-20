#!/usr/bin/env python3
import os
import tempfile
import threading
import time
import wave
import pyaudio
import numpy as np
from pynput import keyboard, mouse
from pynput.keyboard import Controller as KeyboardController, Key, Listener
from pynput.mouse import Controller as MouseController
from faster_whisper import WhisperModel

class RealtimeSpeechToText:
    def __init__(self, model_size="base", language="de", device="cpu", compute_type="int8"):
        """
        Initialisierung der Echtzeit-Spracherkennung mit Faster-Whisper
        
        Args:
            model_size: Größe des Whisper-Modells ('tiny', 'base', 'small', 'medium', 'large-v3')
            language: Sprachcode (z.B. 'de' für Deutsch, 'en' für Englisch)
            device: 'cpu' oder 'cuda' für GPU-Unterstützung
            compute_type: Berechnungstyp ('int8', 'float16', 'float32')
        """
        print(f"Lade Whisper-Modell '{model_size}'...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.language = language
        
        # Audio-Parameter
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        
        # Controller für Eingabegeräte
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
        
        # Flags für Status und Steuerung
        self.is_recording = False
        self.stop_event = threading.Event()
        
        # Speicherung der Cursor-Position beim Start der Aufnahme
        self.recording_start_position = None
        self.current_position = None
        
        # Initialisieren von PyAudio
        self.p = pyaudio.PyAudio()
        
        # Audio-Stream einmalig öffnen
        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            start=False  # Stream nicht sofort starten
        )
        
        # Audio-Frames
        self.frames = []
        
        # Steuerungstasten (mehrere Tasten können verwendet werden)
        self.control_keys = [Key.ctrl_r, Key.shift_r]
        self.pressed_key = None  # Speichert, welche Steuertaste aktuell gedrückt ist
        
        print("System bereit. Halten Sie die rechte Strg-Taste ODER die linke Alt-Taste gedrückt, während Sie sprechen.")
        print("Der Text wird an der Position eingefügt, wo sich der Cursor beim Start der Aufnahme befand.")
        print("Drücken Sie ESC zum Beenden.")

    def on_press(self, key):
        """Wird aufgerufen, wenn eine Taste gedrückt wird"""
        if key in self.control_keys and not self.is_recording:
            # Speichere die gedrückte Steuertaste
            self.pressed_key = key
            
            # Speichere die aktuelle Cursor-Position
            self.recording_start_position = self.mouse.position
            self.start_recording()
            
            # Bestimme den Namen der Taste für die Ausgabe
            key_name = self.get_key_name(key)
            print(f"Aufnahme gestartet... (Sprechen Sie, solange Sie die {key_name} gedrückt halten)")
            print(f"Cursor-Position gespeichert: {self.recording_start_position}")

    def get_key_name(self, key):
        """Gibt den benutzerfreundlichen Namen einer Taste zurück"""
        key_names = {
            Key.ctrl_r: "rechte Strg-Taste",
            Key.alt: "linke Alt-Taste",
            Key.alt_gr: "AltGr-Taste",
            Key.alt_r: "rechte Alt-Taste",
            Key.alt_l: "linke Alt-Taste",
            Key.ctrl: "Strg-Taste",
            Key.shift_r: "rechte Umschalttaste",
            Key.shift_l: "linke Umschalttaste",
            Key.f12: "F12-Taste"
        }
        return key_names.get(key, str(key))

    def on_release(self, key):
        """Wird aufgerufen, wenn eine Taste losgelassen wird"""
        if key == self.pressed_key and self.is_recording:
            self.stop_recording()
            
            key_name = self.get_key_name(key)
            print(f"{key_name} losgelassen. Aufnahme gestoppt.")
            
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join()
            
            self.transcribe_audio()
            self.pressed_key = None
        elif key == Key.esc:
            # ESC beendet das Programm
            return False

    def start_recording(self):
        """Startet die Audioaufnahme"""
        self.frames = []  # Leere die Frames
        self.is_recording = True
        
        try:
            # Starte den Stream (oder starte ihn neu, falls nötig)
            if not self.stream.is_active():
                self.stream.start_stream()
            
            # Starte Aufnahme-Thread
            self.recording_thread = threading.Thread(target=self.record_audio)
            self.recording_thread.daemon = True
            self.recording_thread.start()
        except Exception as e:
            print(f"Fehler beim Starten der Aufnahme: {str(e)}")
            self.is_recording = False

    def record_audio(self):
        """Nimmt Audio auf, solange is_recording True ist"""
        while self.is_recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.append(data)
            except Exception as e:
                print(f"Fehler bei der Aufnahme: {str(e)}")
                # Kurze Pause, um CPU-Last zu reduzieren
                time.sleep(0.1)

    def stop_recording(self):
        """Stoppt die Audioaufnahme"""
        self.is_recording = False
        
        # Warte, bis der Aufnahme-Thread beendet ist
        if hasattr(self, 'recording_thread') and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=1)
        
        print("Aufnahme beendet. Transkribiere...")

    def transcribe_audio(self):
        """Transkribiert die aufgenommene Audiodatei"""
        if not self.frames:
            print("Keine Audiodaten zum Transkribieren.")
            return
        
        try:
            # Erstelle temporäre WAV-Datei
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name
            
            wf = wave.open(temp_filename, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            
            # Transkribiere die Audiodatei
            segments, _ = self.model.transcribe(
                temp_filename, 
                language=self.language,
                beam_size=5,
                vad_filter=True
            )
            
            # Sammle den transkribierten Text
            text = ""
            for segment in segments:
                text += segment.text
            
            # Lösche die temporäre Datei
            os.unlink(temp_filename)
            
            # Wenn Text erkannt wurde, gebe ihn aus
            text = text.strip()
            if text:
                print(f"Erkannter Text: {text}")
                
                # Speichere die aktuelle Mausposition
                current_position = self.mouse.position
                
                # Bewege den Cursor zur gespeicherten Position vom Start der Aufnahme
                if self.recording_start_position:
                    print(f"Bewege Cursor zur gespeicherten Position: {self.recording_start_position}")
                    self.mouse.position = self.recording_start_position
                    # Kurze Pause, um sicherzustellen, dass der Cursor angekommen ist
                    time.sleep(0.1)
                    # Klicke an dieser Position (zum Setzen des Cursors)
                    self.mouse.click(mouse.Button.left)
                    time.sleep(0.1)
                
                # Füge den Text ein
                self.keyboard.type(text + " ")  # Füge Leerzeichen nach dem Text ein
                
                # Optional: Cursor zur vorherigen Position zurücksetzen
                if current_position:
                    time.sleep(0.1)
                    self.mouse.position = current_position
        except Exception as e:
            print(f"Fehler bei der Transkription: {str(e)}")

    def run(self):
        """Startet die Echtzeit-Spracherkennung mit Tastatürsteuerung"""
        try:
            # Starte den Tastatur-Listener
            with Listener(on_press=self.on_press, on_release=self.on_release) as listener:
                listener.join()
                
        except Exception as e:
            print(f"Fehler: {str(e)}")
        finally:
            # Aufräumen
            if self.stream:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()
            print("\nProgramm beendet.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Echtzeit-Spracherkennung mit Cursor-Eingabe")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"], 
                        help="Modellgröße (tiny, base, small, medium, large-v3)")
    parser.add_argument("--language", default="de", help="Sprachcode (z.B. 'de' für Deutsch)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], 
                        help="Gerät für die Berechnung (cpu oder cuda)")
    parser.add_argument("--compute_type", default="int8", choices=["int8", "float16", "float32"], 
                        help="Berechnungstyp (int8, float16, float32)")
    parser.add_argument("--key", default="both", choices=["alt", "ctrl_r", "alt_gr", "alt_r", "alt_l", "ctrl", "shift_r", "shift_l", "f12", "both"], 
                        help="Taste(n) für die Aufnahmesteuerung (Standard: 'both' = rechte Strg-Taste UND linke Alt-Taste)")
    parser.add_argument("--restore-cursor", action="store_true", 
                        help="Nach dem Einfügen den Cursor wieder an seine ursprüngliche Position zurücksetzen")
    
    args = parser.parse_args()
    
    stt = RealtimeSpeechToText(
        model_size=args.model,
        language=args.language,
        device=args.device,
        compute_type=args.compute_type
    )
    
    # Optional: Anpassung der Steuerungstaste über Kommandozeilenparameter
    if args.key != "both":
        if args.key == "alt":
            stt.control_keys = [Key.alt]
        elif args.key == "ctrl_r":
            stt.control_keys = [Key.ctrl_r]
        elif args.key == "alt_gr":
            stt.control_keys = [Key.alt_gr]
        elif args.key == "alt_r":
            stt.control_keys = [Key.alt_r]
        elif args.key == "alt_l":
            stt.control_keys = [Key.alt_l]
        elif args.key == "ctrl":
            stt.control_keys = [Key.ctrl]
        elif args.key == "shift_r":
            stt.control_keys = [Key.shift_r]
        elif args.key == "shift_l":
            stt.control_keys = [Key.shift_l]
        elif args.key == "f12":
            stt.control_keys = [Key.f12]
        print(f"Steuerungstaste geändert auf: {args.key}")
    else:
        print("Steuerungstasten: Rechte Strg-Taste UND linke Alt-Taste verfügbar")
    
    stt.run() 