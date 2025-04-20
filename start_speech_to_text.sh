#!/bin/bash

# Pfad zu Ihrem Projektverzeichnis
PROJECT_DIR="/home/loskud-3neufi-barem/Documents/Github/faster-whisper"

# In das Projektverzeichnis wechseln
cd "$PROJECT_DIR"

# Aktivieren der virtuellen Umgebung
source venv/bin/activate

# Exportieren der LD_LIBRARY_PATH-Variable für den Fall, dass später GPU-Unterstützung benötigt wird
export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib 2>/dev/null; import nvidia.cudnn.lib 2>/dev/null; paths = []; p1 = os.path.dirname(nvidia.cublas.lib.__file__) if "nvidia.cublas.lib" in sys.modules else ""; p2 = os.path.dirname(nvidia.cudnn.lib.__file__) if "nvidia.cudnn.lib" in sys.modules else ""; if p1: paths.append(p1); if p2: paths.append(p2); print(":".join(paths))' 2>/dev/null` || true

# Starten des Programms
python3 realtime_speech_to_text.py --model small --device cpu --compute_type int8

# Warten auf Beendigung (sollte normalerweise nicht erreicht werden, da das Programm im Vordergrund läuft)
wait 