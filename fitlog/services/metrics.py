def calculate_energy_expenditure(weight_kg: float, met_value: float, duration_min: int) -> float:
    """Berechnet den Energieverbrauch (vereinfachte MET-Formel)."""
    # 1 MET ≈ 1 kcal/kg/h → kcal = MET * Gewicht (kg) * Dauer (h)
    hours = max(duration_min, 0) / 60.0
    return round(met_value * weight_kg * hours, 1)
