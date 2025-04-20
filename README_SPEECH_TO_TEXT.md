# Echtzeit-Spracherkennung mit Cursor-Eingabe

Dieses Skript ermöglicht die Echtzeit-Transkription von Sprache zu Text. Es verwendet das Faster-Whisper-Modell, um gesprochene Sprache zu erkennen und gibt den erkannten Text an der aktuellen Cursor-Position aus, als ob Sie ihn getippt hätten.

## Voraussetzungen

- Python 3.9 oder höher
- Virtuelle Umgebung mit den benötigten Paketen (siehe Installation)

## Installation

1. Erstellen Sie eine virtuelle Umgebung und aktivieren Sie sie:

```bash
python3 -m venv venv
source venv/bin/activate  # Unter Windows: venv\Scripts\activate
```

2. Installieren Sie die benötigten Pakete:

```bash
pip install faster-whisper PyAudio pynput
```

## Verwendung

Aktivieren Sie die virtuelle Umgebung und führen Sie das Skript aus:

```bash
source venv/bin/activate  # Unter Windows: venv\Scripts\activate
python3 realtime_speech_to_text.py
```

### Bedienung:

1. **Positionieren Sie den Cursor** an der Stelle, wo der Text eingefügt werden soll
2. **Halten Sie die rechte Strg-Taste gedrückt**, während Sie sprechen
3. **Lassen Sie die Taste los**, um die Transkription zu starten
4. Der erkannte Text wird an der Stelle eingefügt, wo sich der Cursor beim Start der Aufnahme befand, auch wenn Sie während der Aufnahme woanders hingeklickt haben
5. Drücken Sie **ESC**, um das Programm zu beenden

### Befehlszeilenoptionen

Das Skript unterstützt verschiedene Optionen:

- `--model`: Modellgröße (tiny, base, small, medium, large-v3) [Standard: base]
- `--language`: Sprachcode (z.B. 'de' für Deutsch, 'en' für Englisch) [Standard: de]
- `--device`: Gerät für die Berechnung (cpu oder cuda) [Standard: cpu]
- `--compute_type`: Berechnungstyp (int8, float16, float32) [Standard: int8]
- `--key`: Taste für die Aufnahmesteuerung [Standard: ctrl_r]
  - Verfügbare Optionen: ctrl_r, alt_gr, alt_r, alt_l, ctrl, shift_r, shift_l, f12
- `--restore-cursor`: Nach dem Einfügen des Textes den Cursor wieder an seine aktuelle Position zurücksetzen

Beispiel für ein größeres Modell mit Englisch als Sprache:

```bash
python3 realtime_speech_to_text.py --model medium --language en
```

Beispiel für GPU-Nutzung (falls verfügbar):

```bash
python3 realtime_speech_to_text.py --device cuda --compute_type float16
```

Beispiel für Änderung der Steuerungstaste auf F12:

```bash
python3 realtime_speech_to_text.py --key f12
```

## Hinweise

- Für bessere Ergebnisse verwenden Sie ein gutes Mikrofon und sprechen Sie in einer ruhigen Umgebung.
- Größere Modelle (medium, large-v3) bieten eine bessere Erkennung, benötigen aber mehr Arbeitsspeicher und Rechenleistung.
- Die Aufnahme erfolgt nur, solange die Steuerungstaste gedrückt gehalten wird.
- Die Transkription startet automatisch, sobald die Taste losgelassen wird.
- Das Programm kann kontinuierlich genutzt werden, ohne es neu zu starten. Sie können beliebig oft die Taste drücken und loslassen, um neue Texte zu transkribieren.
- Das Skript unterstützt primär Transkription in einer Sprache. Ein Mix aus Deutsch und Englisch kann zu Ungenauigkeiten führen, funktioniert aber in begrenztem Umfang, besonders bei größeren Modellen.
