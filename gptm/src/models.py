from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class Coureur:
    id: int
    naam: str
    team: str
    prijs: float
    punten_totaal: int = 0
    laatste_resultaten: List[int] = None
    gemiddelde_finish_positie: float = 0.0
    gemiddelde_kwalificatie_positie: float = 0.0
    betrouwbaarheid_score: float = 0.0  # Percentage races gefinisht
    circuit_prestaties: Dict[str, float] = None  # Prestaties per circuit type
    
    def __post_init__(self):
        if self.laatste_resultaten is None:
            self.laatste_resultaten = []
        if self.circuit_prestaties is None:
            self.circuit_prestaties = {}

@dataclass
class Team:
    coureurs: List[Coureur]
    totale_waarde: float
    verwachte_punten: float
    laatste_update: datetime
    
    def voeg_coureur_toe(self, coureur: Coureur) -> bool:
        from config.config import GPTMConfig
        
        if len(self.coureurs) >= GPTMConfig.MAX_COUREURS:
            return False
            
        nieuwe_totale_waarde = self.totale_waarde + coureur.prijs
        if nieuwe_totale_waarde > GPTMConfig.TOTAAL_BUDGET:
            return False
            
        self.coureurs.append(coureur)
        self.totale_waarde = nieuwe_totale_waarde
        return True
    
    def verwijder_coureur(self, coureur_id: int) -> bool:
        for i, coureur in enumerate(self.coureurs):
            if coureur.id == coureur_id:
                self.totale_waarde -= coureur.prijs
                self.coureurs.pop(i)
                return True
        return False
    
    def bereken_verwachte_punten(self) -> float:
        # Dit is een simpele berekening die later verfijnd kan worden
        self.verwachte_punten = sum(c.gemiddelde_finish_positie * c.betrouwbaarheid_score 
                                   for c in self.coureurs)
        return self.verwachte_punten

@dataclass
class RaceResultaat:
    race_id: int
    circuit: str
    circuit_type: str
    datum: datetime
    weer: str
    resultaten: Dict[int, Dict[str, any]]  # Coureur ID -> resultaat details 