# FitLog – Der Trainingsplantracker 🏋️‍♂️

**FitLog** ist eine webbasierte Anwendung zum Erstellen und Verwalten von Trainingsplänen.  
Das Projekt wurde im Rahmen des Moduls *Skriptsprachen / Python* an der FH Südwestfalen entwickelt.

---

## 🔧 Projektüberblick

FitLog soll es ermöglichen, eigene Trainingspläne anzulegen, Übungen zu verwalten und Fortschritte über Zeit zu visualisieren.  
Die Anwendung läuft lokal über Flask und speichert Daten in einer SQLite-Datenbank.

### Hauptfunktionen

* Trainingspläne anlegen, bearbeiten und löschen
* Übungen einem Plan hinzufügen (mit Sätzen, Wiederholungen und Gewicht)
* Trainingseinheiten erfassen und speichern
* Automatische Aktualisierung des Standardgewichts nach dem Training
* Visualisierung des Trainingsfortschritts (Matplotlib-Diagramme)
* Optionale Berechnung des Energieverbrauchs auf Basis von MET-Werten

---

## ⚙️ Installation \& Setup

### Voraussetzungen

* Python 3.10 oder neuer
* Git
* Eine IDE wie PyCharm (empfohlen)

### Lokale Einrichtung

```bash
# Repository klonen
git clone https://github.com/lp-coding/FitLog.git
cd FitLog

# Virtuelle Umgebung erstellen und aktivieren
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# macOS / Linux:
source .venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Beispiel-Umgebungsdatei kopieren
cp .env.example .env
```

### Starten der Anwendung

```bash
python app.py
```

oder (alternativ, wenn du FLASK\_APP gesetzt hast):

```bash
flask run
```

Danach öffnet sich die Anwendung unter:  
👉 [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 🗂️ Projektstruktur

```text
FitLog/
│
├── app.py              # Flask-App mit Routen
├── models.py           # Datenbank-Modelle (SQLAlchemy)
├── static/             # CSS, Bilder, JS
├── templates/          # HTML-Templates (Jinja2)
├── database/           # SQLite-Datenbank
├── instance/           # Laufzeitkonfiguration
├── .env.example        # Beispiel für Umgebungsvariablen
└── README.md
```

---

## 🧩 Verwendete Technologien

| Bereich           | Technologie         | Version (Beispiel) |
|-------------------|--------------------|--------------------|
| Backend Framework | Flask              | 3.0.0              |
| Datenbank         | SQLite / SQLAlchemy| 2.0.x              |
| Visualisierung    | Matplotlib         | 3.9.x              |
| Sonstiges         | python-dotenv      | 1.0.x              |

---

## 💡 Hinweise für Entwickler:innen

* Achte darauf, `.env` nicht zu committen (enthält Secrets).
* Diagramme und Kalorienberechnung sind optionale Erweiterungen.
* Für Tests kann die Datenbank jederzeit gelöscht werden (`database/fitlog.db`).

---

## 📸 Screenshots (Platzhalter)

> \*(Hier später Screenshots deiner Startseite, Planbearbeitung oder Fortschrittsdiagramme einfügen.)\*

---

## ✍️ Autor

**Lucas Piepenbrock**  
Fachhochschule Südwestfalen  
Modul: Skriptsprachen / Python  
Betreuung: Prof. Gogolin

---

