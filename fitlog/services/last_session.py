# -*- coding: utf-8 -*-
"""
Service: Last Session
Zeigt die zuletzt GESPEICHERTE/beendete Session (höchste ID mit ended_at != NULL).
Das vermeidet Probleme, wenn ended_at bewusst rückdatiert wird (z. B. per Dauer).
Gibt die Keys zurück, die index.html erwartet:
  - date (YYYY-MM-DD)
  - plan_name
  - duration_min
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, Optional


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    if not val:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt)
        except ValueError:
            continue
    return None


def get_last_session(db) -> Dict[str, Any]:
    """
    Nimmt die letzte BEENDTE Session per höchster s.id.
    Hintergrund: ended_at kann bewusst auf „früher“ gesetzt sein (Dauer-Input),
    wir möchten aber die zuletzt gespeicherte Einheit zeigen.
    """
    row = db.execute(
        """
        SELECT s.started_at, s.ended_at, tp.name AS plan_name
        FROM sessions s
        JOIN training_plans tp ON tp.id = s.plan_id
        WHERE s.ended_at IS NOT NULL
        ORDER BY s.id DESC
        LIMIT 1
        """
    ).fetchone()

    if not row:
        return {"date": "—", "plan_name": "—", "duration_min": "—"}

    start_dt = _parse_dt(row["started_at"])
    end_dt   = _parse_dt(row["ended_at"])

    duration_min = "—"
    if start_dt and end_dt:
        duration_min = max(0, int((end_dt - start_dt).total_seconds() // 60))

    return {
        "date": (end_dt or start_dt).date().isoformat() if (end_dt or start_dt) else "—",
        "plan_name": row["plan_name"] or "—",
        "duration_min": duration_min,
    }
