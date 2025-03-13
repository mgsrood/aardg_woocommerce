from dataclasses import dataclass
from typing import Dict, List

@dataclass
class GPTMConfig:
    # Budget configuratie
    TOTAAL_BUDGET: float = 100.0  # Startbudget in miljoenen
    MAX_COUREURS: int = 2  # Exact 2 coureurs verplicht
    EERSTE_COUREUR_BONUS: float = 1.25  # 25% meer punten voor eerste coureur
    
    # Scoring configuratie race
    RACE_PUNTEN: Dict[str, Dict[int, int]] = {
        "coureur": {
            1: 100, 2: 90, 3: 80, 4: 70, 5: 60,
            6: 50, 7: 45, 8: 40, 9: 35, 10: 30,
            11: 25, 12: 20, 13: 18, 14: 15, 15: 13,
            16: 10, 17: 8, 18: 6, 19: 4, 20: 2
        },
        "chassis": {
            1: 50, 2: 45, 3: 40, 4: 35, 5: 30,
            6: 25, 7: 22, 8: 20, 9: 17, 10: 15,
            11: 12, 12: 11, 13: 10, 14: 9, 15: 8,
            16: 7, 17: 5, 18: 3, 19: 2, 20: 1
        },
        "motor": {
            1: 40, 2: 36, 3: 32, 4: 28, 5: 24,
            6: 20, 7: 18, 8: 16, 9: 14, 10: 12,
            11: 10, 12: 9, 13: 8, 14: 7, 15: 6,
            16: 5, 17: 4, 18: 3, 19: 2, 20: 1
        }
    }
    
    # Kwalificatie punten
    KWALIFICATIE_PUNTEN: Dict[str, Dict[int, int]] = {
        "coureur": {
            1: 20, 2: 18, 3: 16, 4: 14, 5: 12,
            6: 10, 7: 9, 8: 9, 9: 8, 10: 7,
            11: 6, 12: 5, 13: 4, 14: 3, 15: 3,
            16: 2, 17: 2, 18: 1, 19: 0, 20: 0
        },
        "chassis": {
            1: 13, 2: 12, 3: 11, 4: 10, 5: 9,
            6: 8, 7: 7, 8: 6, 9: 5, 10: 5,
            11: 4, 12: 4, 13: 3, 14: 3, 15: 2,
            16: 2, 17: 1, 18: 1, 19: 0, 20: 0
        },
        "motor": {
            1: 11, 2: 10, 3: 9, 4: 8, 5: 7,
            6: 6, 7: 5, 8: 4, 9: 3, 10: 3,
            11: 2, 12: 2, 13: 1, 14: 1, 15: 0,
            16: 0, 17: 0, 18: 0, 19: 0, 20: 0
        }
    }
    
    # Bonus punten
    SNELSTE_RONDE_PUNTEN: Dict[str, int] = {
        "coureur": 10,
        "chassis": 5,
        "motor": 5
    }
    
    # Waarde aanpassingen (in miljoenen)
    WAARDE_AANPASSINGEN: Dict[str, Dict[str, float]] = {
        "coureur": {
            "0-7": -2.0,
            "8-15": -1.0,
            "16-30": 0.0,
            "31-50": 1.0,
            "51-65": 2.0,
            "66-80": 2.5,
            "81-99": 3.0,
            "100+": 4.0
        },
        "chassis": {
            "0-7": -1.5,
            "8-15": -0.7,
            "16-30": 0.0,
            "31-50": 0.7,
            "51-65": 1.5,
            "66-80": 2.0,
            "81-99": 2.5,
            "100+": 3.0
        },
        "motor": {
            "0-7": -1.0,
            "8-15": -0.5,
            "16-30": 0.0,
            "31-50": 0.5,
            "51-65": 1.0,
            "66-80": 1.5,
            "81-99": 2.0,
            "100+": 2.5
        }
    }
    
    # Salaris berekening (in miljoenen)
    SALARIS_PER_PUNT: Dict[str, float] = {
        "0-100": 0.07,
        "101-200": 0.025,
        "201-300": 0.01,
        "301+": 0.005
    }
    
    # Waarde limieten
    MIN_WAARDE: float = 10.0
    MAX_WAARDE: float = 120.0
    
    # Data bronnen
    DATA_DIR: str = "data"
    COUREURS_BESTAND: str = "coureurs.json"
    HISTORISCHE_DATA_BESTAND: str = "historische_data.json"
    
    # Model parameters
    GEWICHT_RECENT_RESULTAAT: float = 0.6
    GEWICHT_HISTORISCH: float = 0.3
    GEWICHT_KWALIFICATIE: float = 0.1
    
    # Circuit factoren
    CIRCUIT_TYPES: List[str] = [
        "street_circuit",
        "permanent_circuit",
        "high_speed",
        "technical"
    ] 