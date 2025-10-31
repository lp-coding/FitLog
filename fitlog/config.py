import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Lädt Basis-Konfiguration. Für die Abgabe bewusst simpel gehalten."""
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY", "dev"),
        # SQLite-Datei liegt in instance/
        "DATABASE": os.getenv("DATABASE", "fitlog.db"),
    }
