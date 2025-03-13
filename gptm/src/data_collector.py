import json
from typing import List, Dict
from datetime import datetime
import os

from .models import Coureur, RaceResultaat
from config.config import GPTMConfig

class DataCollector:
    def __init__(self):
        self.config = GPTMConfig()
        self.data_dir = self.config.DATA_DIR
        
        # Zorg dat de data directory bestaat
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def laad_coureur_data(self) -> List[Coureur]:
        """Laadt coureur data uit het JSON bestand"""
        bestand_pad = os.path.join(self.data_dir, self.config.COUREURS_BESTAND)
        
        if not os.path.exists(bestand_pad):
            return []
            
        with open(bestand_pad, 'r') as f:
            data = json.load(f)
            
        coureurs = []
        for c_data in data:
            coureur = Coureur(
                id=c_data['id'],
                naam=c_data['naam'],
                team=c_data['team'],
                prijs=c_data['prijs'],
                punten_totaal=c_data.get('punten_totaal', 0),
                laatste_resultaten=c_data.get('laatste_resultaten', []),
                gemiddelde_finish_positie=c_data.get('gemiddelde_finish_positie', 0.0),
                gemiddelde_kwalificatie_positie=c_data.get('gemiddelde_kwalificatie_positie', 0.0),
                betrouwbaarheid_score=c_data.get('betrouwbaarheid_score', 0.0),
                circuit_prestaties=c_data.get('circuit_prestaties', {})
            )
            coureurs.append(coureur)
            
        return coureurs
    
    def sla_coureur_data_op(self, coureurs: List[Coureur]):
        """Slaat coureur data op in het JSON bestand"""
        bestand_pad = os.path.join(self.data_dir, self.config.COUREURS_BESTAND)
        
        data = []
        for coureur in coureurs:
            c_data = {
                'id': coureur.id,
                'naam': coureur.naam,
                'team': coureur.team,
                'prijs': coureur.prijs,
                'punten_totaal': coureur.punten_totaal,
                'laatste_resultaten': coureur.laatste_resultaten,
                'gemiddelde_finish_positie': coureur.gemiddelde_finish_positie,
                'gemiddelde_kwalificatie_positie': coureur.gemiddelde_kwalificatie_positie,
                'betrouwbaarheid_score': coureur.betrouwbaarheid_score,
                'circuit_prestaties': coureur.circuit_prestaties
            }
            data.append(c_data)
            
        with open(bestand_pad, 'w') as f:
            json.dump(data, f, indent=2)
    
    def voeg_coureur_toe(self, coureur_data: Dict):
        """Voegt een nieuwe coureur toe aan de dataset"""
        coureurs = self.laad_coureur_data()
        
        # Controleer of coureur al bestaat
        if any(c.id == coureur_data['id'] for c in coureurs):
            return False
            
        nieuwe_coureur = Coureur(
            id=coureur_data['id'],
            naam=coureur_data['naam'],
            team=coureur_data['team'],
            prijs=coureur_data['prijs']
        )
        
        coureurs.append(nieuwe_coureur)
        self.sla_coureur_data_op(coureurs)
        return True
    
    def update_coureur(self, coureur_id: int, nieuwe_data: Dict):
        """Update de data van een bestaande coureur"""
        coureurs = self.laad_coureur_data()
        
        for coureur in coureurs:
            if coureur.id == coureur_id:
                for key, value in nieuwe_data.items():
                    if hasattr(coureur, key):
                        setattr(coureur, key, value)
                break
                
        self.sla_coureur_data_op(coureurs) 