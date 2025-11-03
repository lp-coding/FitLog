"""
FitLog – Instanzkonfiguration
-----------------------------
Diese Datei enthält lokale bzw. sensible Einstellungen,
die nicht im öffentlichen Repository landen sollten.

Sie wird automatisch von Flask beim Start eingelesen,
wenn `app.config.from_pyfile("config.py", silent=True)` aktiviert ist.
"""

# ⚙️ Flask-Grundeinstellungen
SECRET_KEY = "my-very-secret-key"   # Bitte ändern für Produktivbetrieb!
DEBUG = True                        # Debugmodus für lokale Entwicklung
TESTING = False                     # False lassen, außer beim Unit-Testing

# 💾 Datenbankpfad (kann angepasst werden)
DATABASE = "instance/fitlog.db"

# 🌍 Optionale Konfigurationen für spätere Features
# (können später ergänzt werden)
# UPLOAD_FOLDER = "instance/uploads"
# LOG_LEVEL = "INFO"
# ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# 📈 Falls du später Diagramme oder APIs nutzt:
# MATPLOTLIB_BACKEND = "Agg"
# API_RATE_LIMIT = "100/hour"

