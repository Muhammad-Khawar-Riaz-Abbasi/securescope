from app.services import ImpactProvider

def test_impact_provider_is_deterministic():
    assert ImpactProvider().calculate(100) == {"meals_rescued": 100, "co2_saved_kg": 80.0, "water_saved_l": 20000}
