import sqlite3
from pathlib import Path


def seed_database() -> None:
    db_path = Path("instance/fitlog.db")
    if not db_path.exists():
        print("Datenbank nicht gefunden. Bitte zuerst init_db.py ausführen.")
        return

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Beispiel-Datensätze
    exercises = [
        ("Bankdrücken", "Brust"),
        ("Kniebeugen", "Beine"),
        ("Klimmzüge", "Rücken"),
    ]
    cur.executemany("INSERT INTO exercises (name, muscle_group) VALUES (?, ?)", exercises)

    plans = [("Oberkörper",), ("Ganzkörper",)]
    cur.executemany("INSERT INTO training_plans (name) VALUES (?)", plans)

    con.commit()
    con.close()
    print("Seed-Daten erfolgreich eingetragen.")


if __name__ == "__main__":
    seed_database()
