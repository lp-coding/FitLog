# FitLog – Trainingsplantracker (Finale Struktur)

Web-App mit Flask, SQLite und Matplotlib zur Erstellung/Verwaltung von Trainingsplänen inkl. Fortschrittsdiagrammen.

## Setup
```bash
python -m venv .venv
.venv/Scripts/activate  # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
flask --app app run
```

## Hinweise
- SQLite liegt in `instance/fitlog.db` (wird automatisch angelegt).
- Erste Standard-Übungen werden beim Start gesät (INSERT OR IGNORE).
- Diagramme werden serverseitig per Matplotlib als PNG generiert.
