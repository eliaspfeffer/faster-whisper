#!/usr/bin/env python3
"""
Diagnose-Skript zur Erkennung von Tasteneingaben.
Drücken Sie verschiedene Tasten, um zu sehen, wie sie vom System erkannt werden.
Drücken Sie die ESC-Taste, um das Programm zu beenden.
"""

from pynput import keyboard
import time

print("=== Tasten-Diagnose-Tool ===")
print("Drücken Sie verschiedene Tasten, um zu sehen, wie sie vom System erkannt werden.")
print("Drücken Sie besonders die rechte Alt-Taste und andere Modifikatortasten.")
print("Drücken Sie ESC, um das Programm zu beenden.")
print("\nWarte auf Tasteneingaben...\n")

def on_press(key):
    """Wird aufgerufen, wenn eine Taste gedrückt wird"""
    try:
        # Versuche, den Zeichen-Wert der Taste zu bekommen
        print(f"Taste gedrückt: '{key.char}' (char)")
    except AttributeError:
        # Spezielle Tasten haben keinen char-Wert
        print(f"Spezielle Taste gedrückt: {key} (Name/Code)")
    
        # Zusätzliche Informationen für Spezialschlüssel
        if hasattr(key, 'name'):
            print(f"  - Name der Taste: {key.name}")
        if hasattr(key, 'vk'):
            print(f"  - Virtueller Tastaturcode: {key.vk}")
        
        # Erkenne Alt-Tasten spezifisch
        if key == keyboard.Key.alt:
            print("  - Das ist die LINKE Alt-Taste")
        if key == keyboard.Key.alt_l:
            print("  - Das ist die LINKE Alt-Taste (explizit)")
        if key == keyboard.Key.alt_r:
            print("  - Das ist die RECHTE Alt-Taste")
        if key == keyboard.Key.alt_gr:
            print("  - Das ist die AltGr-Taste (rechte Alt-Taste in manchen Layouts)")
    
    print("-" * 40)

def on_release(key):
    """Wird aufgerufen, wenn eine Taste losgelassen wird"""
    if key == keyboard.Key.esc:
        # Beende Listener bei ESC
        print("ESC gedrückt. Beende das Programm...")
        return False

# Starte den Tastatur-Listener
with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    try:
        while listener.running:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Programm durch Benutzer unterbrochen.")
    finally:
        print("Programm beendet.") 