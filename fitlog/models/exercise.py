from typing import List, Dict, Any, Optional
from ..db import get_db

def get_exercise(exercise_id: int) -> Optional[Dict[str, Any]]:
    db = get_db()
    row = db.execute("SELECT id, name, met FROM exercises WHERE id=?;", (exercise_id,)).fetchone()
    return dict(row) if row else None
