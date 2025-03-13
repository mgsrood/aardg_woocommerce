from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime

from .models import Coureur, Team, RaceResultaat
from config.config import GPTMConfig

class TeamOptimizer:
    def __init__(self, beschikbare_coureurs: List[Coureur], historische_data: List[RaceResultaat]):
        self.beschikbare_coureurs = beschikbare_coureurs
        self.historische_data = historische_data
        self.config = GPTMConfig()
    
    def bereken_coureur_score(self, coureur: Coureur, circuit_type: str) -> float:
        """Berekent een score voor een coureur gebaseerd op verschillende factoren"""
        # Basis score op recente resultaten
        recent_score = np.mean(coureur.laatste_resultaten) if coureur.laatste_resultaten else 0
        
        # Circuit-specifieke prestatie
        circuit_score = coureur.circuit_prestaties.get(circuit_type, 0)
        
        # Betrouwbaarheid factor
        betrouwbaarheid = coureur.betrouwbaarheid_score
        
        # Gewogen gemiddelde van alle factoren
        totaal_score = (
            self.config.GEWICHT_RECENT_RESULTAAT * recent_score +
            self.config.GEWICHT_HISTORISCH * circuit_score +
            self.config.GEWICHT_KWALIFICATIE * coureur.gemiddelde_kwalificatie_positie
        ) * betrouwbaarheid
        
        return totaal_score
    
    def optimaliseer_team(self, circuit_type: str) -> Team:
        """Stelt het optimale team samen binnen de budgetbeperkingen"""
        # Bereken scores voor alle coureurs
        coureur_scores: List[Tuple[Coureur, float]] = [
            (coureur, self.bereken_coureur_score(coureur, circuit_type))
            for coureur in self.beschikbare_coureurs
        ]
        
        # Sorteer coureurs op score/prijs ratio (value for money)
        coureur_scores.sort(key=lambda x: x[1] / x[0].prijs, reverse=True)
        
        # Stel team samen binnen budget
        team = Team(
            coureurs=[],
            totale_waarde=0.0,
            verwachte_punten=0.0,
            laatste_update=datetime.now()
        )
        
        # Voeg coureurs toe tot we het budget bereiken
        for coureur, score in coureur_scores:
            if team.voeg_coureur_toe(coureur):
                continue
        
        team.bereken_verwachte_punten()
        return team
    
    def suggereer_transfers(self, huidig_team: Team, circuit_type: str) -> List[Dict]:
        """Suggereert mogelijke transfers om het team te verbeteren"""
        suggesties = []
        
        # Voor elke coureur in het huidige team
        for huidige_coureur in huidig_team.coureurs:
            huidige_score = self.bereken_coureur_score(huidige_coureur, circuit_type)
            
            # Zoek betere alternatieven binnen budget
            beschikbaar_budget = self.config.TOTAAL_BUDGET - huidig_team.totale_waarde + huidige_coureur.prijs
            
            for potentiele_coureur in self.beschikbare_coureurs:
                if potentiele_coureur.id == huidige_coureur.id:
                    continue
                    
                if potentiele_coureur.prijs <= beschikbaar_budget:
                    nieuwe_score = self.bereken_coureur_score(potentiele_coureur, circuit_type)
                    
                    if nieuwe_score > huidige_score:
                        suggesties.append({
                            "verwijder": huidige_coureur,
                            "toevoegen": potentiele_coureur,
                            "score_verbetering": nieuwe_score - huidige_score,
                            "kosten_verschil": potentiele_coureur.prijs - huidige_coureur.prijs
                        })
        
        # Sorteer suggesties op score verbetering
        suggesties.sort(key=lambda x: x["score_verbetering"], reverse=True)
        return suggesties 