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

# Add new imports for window management
import subprocess
import re
import platform

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
        self.space_pressed_during_transcription = False
        
        # Speicherung des aktiven Fensters beim Start der Aufnahme
        self.active_window_id = None
        self.active_window_name = None
        
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
        
        # Bestimme das Betriebssystem für fenster-spezifische Funktionen
        self.system = platform.system()
        
        # Starte den Tastatur-Listener für Leertaste
        self.space_listener = keyboard.Listener(on_press=self.on_key_press)
        self.space_listener.daemon = True
        self.space_listener.start()
        
        print("System bereit. Halten Sie die rechte Strg-Taste ODER die rechte Umschalttaste gedrückt, während Sie sprechen.")
        print("Der Text wird in das aktive Textfeld eingefügt, auch wenn Sie während der Aufnahme woanders hinklicken.")
        print("Bei Eingabe in Cursor wird automatisch Enter gedrückt, wenn keine Leertaste gedrückt wurde.")
        print("Drücken Sie Strg+C im Terminal zum Beenden.")

    def on_key_press(self, key):
        """Überwacht Tastendrücke, insbesondere die Leertaste"""
        try:
            if key == Key.space and not self.is_recording:
                self.space_pressed_during_transcription = True
                print("Leertaste erkannt - kein automatischer Enter")
        except:
            pass  # Ignoriere Fehler bei der Tastenerkennung

    def get_active_window_id(self):
        """Ermittelt die ID des aktiven Fensters abhängig vom Betriebssystem"""
        if self.system == "Linux":
            try:
                # In Linux (X11) verwenden wir xdotool
                result = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except (FileNotFoundError, subprocess.SubprocessError):
                print("Warnung: xdotool nicht gefunden oder Fehler bei der Ausführung.")
                
        elif self.system == "Windows":
            try:
                # In Windows können wir GetForegroundWindow aus user32.dll nutzen
                import ctypes
                return ctypes.windll.user32.GetForegroundWindow()
            except (ImportError, AttributeError):
                print("Warnung: Windows-API konnte nicht genutzt werden.")
                
        elif self.system == "Darwin":  # macOS
            try:
                # In macOS verwenden wir AppleScript
                cmd = "osascript -e 'tell application \"System Events\" to get id of first application process whose frontmost is true'"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except subprocess.SubprocessError:
                print("Warnung: AppleScript konnte nicht ausgeführt werden.")
        
        return None

    def get_active_window_name(self):
        """Ermittelt den Namen der aktiven Anwendung"""
        if self.system == "Linux":
            try:
                # Für Linux verwenden wir xdotool, um den Fensternamen zu erhalten
                result = subprocess.run(["xdotool", "getactivewindow", "getwindowname"], 
                                        capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except (FileNotFoundError, subprocess.SubprocessError):
                pass
                
        elif self.system == "Windows":
            try:
                # Für Windows
                import ctypes
                from ctypes import windll, wintypes, create_unicode_buffer
                
                hwnd = windll.user32.GetForegroundWindow()
                length = windll.user32.GetWindowTextLengthW(hwnd)
                buf = create_unicode_buffer(length + 1)
                windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return buf.value
            except (ImportError, AttributeError):
                pass
                
        elif self.system == "Darwin":  # macOS
            try:
                # Für macOS
                cmd = """osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true'"""
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    return result.stdout.strip()
            except subprocess.SubprocessError:
                pass
        
        return None

    def is_cursor_app(self):
        """Überprüft, ob die aktive Anwendung Cursor ist"""
        window_name = self.active_window_name
        if window_name:
            return "Cursor" in window_name
        return False

    def focus_window(self, window_id):
        """Fokussiert ein Fenster basierend auf seiner ID"""
        if not window_id:
            return False
            
        if self.system == "Linux":
            try:
                subprocess.run(["xdotool", "windowactivate", window_id], check=False)
                return True
            except (FileNotFoundError, subprocess.SubprocessError):
                print("Fenster konnte nicht fokussiert werden.")
                
        elif self.system == "Windows":
            try:
                import ctypes
                ctypes.windll.user32.SetForegroundWindow(window_id)
                return True
            except (ImportError, AttributeError):
                print("Windows-API konnte nicht genutzt werden.")
                
        elif self.system == "Darwin":  # macOS
            try:
                # Dies ist eine vereinfachte Version, die möglicherweise nicht für alle Anwendungen funktioniert
                cmd = f"osascript -e 'tell application \"System Events\" to set frontmost of first application process whose id is {window_id} to true'"
                subprocess.run(cmd, shell=True, check=False)
                return True
            except subprocess.SubprocessError:
                print("AppleScript konnte nicht ausgeführt werden.")
        
        return False

    def on_press(self, key):
        """Wird aufgerufen, wenn eine Taste gedrückt wird"""
        if key in self.control_keys and not self.is_recording:
            # Speichere die gedrückte Steuertaste
            self.pressed_key = key
            
            # Speichere das aktive Fenster und seinen Namen
            self.active_window_id = self.get_active_window_id()
            self.active_window_name = self.get_active_window_name()
            
            if self.active_window_id:
                print(f"Aktives Fenster-ID gespeichert: {self.active_window_id}")
                if self.active_window_name:
                    print(f"Aktive Anwendung: {self.active_window_name}")
            else:
                print("Konnte aktives Fenster nicht ermitteln.")
            
            # Setze die Leertasten-Erkennung zurück
            self.space_pressed_during_transcription = False
            
            self.start_recording()
            
            # Bestimme den Namen der Taste für die Ausgabe
            key_name = self.get_key_name(key)
            print(f"Aufnahme gestartet... (Sprechen Sie, solange Sie die {key_name} gedrückt halten)")

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
                
                # Speichere die aktuelle Fenster-ID
                current_window = self.get_active_window_id()
                
                # Fokussiere das ursprüngliche Fenster, falls nötig
                if self.active_window_id and current_window != self.active_window_id:
                    print(f"Wechsle zurück zum ursprünglichen Fenster...")
                    if self.focus_window(self.active_window_id):
                        # Kurze Pause, um sicherzustellen, dass der Fensterwechsel abgeschlossen ist
                        time.sleep(0.3)
                    else:
                        print("Konnte nicht zum ursprünglichen Fenster zurückkehren.")
                
                # Füge den Text ein
                self.keyboard.type(text + " ")  # Füge Leerzeichen nach dem Text ein
                
                # Prüfe, ob es sich um Cursor handelt und keine Leertaste gedrückt wurde
                if self.is_cursor_app() and not self.space_pressed_during_transcription:
                    print("Cursor erkannt - drücke automatisch Enter")
                    time.sleep(0.1)  # Kurze Pause vor dem Enter-Druck
                    self.keyboard.press(Key.enter)
                    self.keyboard.release(Key.enter)
                
                # Optional: Zurück zum vorherigen Fenster wechseln
                if current_window and current_window != self.active_window_id:
                    time.sleep(0.1)
                    self.focus_window(current_window)
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
            if self.space_listener.running:
                self.space_listener.stop()
            print("\nProgramm beendet.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Echtzeit-Spracherkennung mit Cursor-Eingabe")
    parser.add_argument("--model", default="base", choices=["tiny", "base", "small", "medium", "large-v3"], 
                        help="Modellgröße (tiny, base, small, medium, large-v3)")
    parser.add_argument("--language", default="de", choices=["de", "en", "auto"], 
                        help="Sprachcode (z.B. 'de' für Deutsch, 'en' für Englisch, 'auto' für automatische Erkennung)")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], 
                        help="Gerät für die Berechnung (cpu oder cuda)")
    parser.add_argument("--compute_type", default="int8", choices=["int8", "float16", "float32"], 
                        help="Berechnungstyp (int8, float16, float32)")
    parser.add_argument("--key", default="both", choices=["alt", "ctrl_r", "alt_gr", "alt_r", "alt_l", "ctrl", "shift_r", "shift_l", "f12", "both"], 
                        help="Taste(n) für die Aufnahmesteuerung (Standard: 'both' = rechte Strg-Taste UND rechte Umschalttaste)")
    
    args = parser.parse_args()
    
    # Initialisiere das Objekt
    stt = RealtimeSpeechToText(
        model_size=args.model,
        language="auto" if args.language == "auto" else args.language,  # Setze auf None für auto
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
        print("Steuerungstasten: Rechte Strg-Taste UND rechte Umschalttaste verfügbar")
    
    stt.run() 