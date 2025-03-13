from typing import List, Dict
import json
import os
from datetime import datetime

from .data_collector import DataCollector
from .optimizer import TeamOptimizer
from .models import Coureur, Team, RaceResultaat
from config.config import GPTMConfig

def main():
    # Initialiseer de componenten
    data_collector = DataCollector()
    config = GPTMConfig()
    
    # Laad de coureur data
    coureurs = data_collector.laad_coureur_data()
    
    if not coureurs:
        print("Geen coureur data gevonden. Voeg eerst coureurs toe.")
        return
    
    # Laad historische data (als die er is)
    historische_data = []  # Dit zou je kunnen uitbreiden met echte historische data
    
    # Maak de optimizer
    optimizer = TeamOptimizer(coureurs, historische_data)
    
    # Bepaal het circuit type voor de eerste race
    eerste_circuit_type = "permanent_circuit"  # Dit zou je kunnen aanpassen
    
    # Genereer het optimale team
    optimaal_team = optimizer.optimaliseer_team(eerste_circuit_type)
    
    # Toon het resultaat
    print("\nOptimaal team samenstelling:")
    print("-" * 50)
    print(f"Totale waarde: {optimaal_team.totale_waarde}")
    print(f"Verwachte punten: {optimaal_team.verwachte_punten}")
    print("\nCoureurs:")
    for coureur in optimaal_team.coureurs:
        print(f"- {coureur.naam} (€{coureur.prijs}M)")
        print(f"  Team: {coureur.team}")
        print(f"  Gemiddelde finish positie: {coureur.gemiddelde_finish_positie}")
        print(f"  Betrouwbaarheid: {coureur.betrouwbaarheid_score * 100}%")
        print()

def voeg_nieuwe_coureur_toe():
    data_collector = DataCollector()
    
    coureur_data = {
        'id': int(input("Coureur ID: ")),
        'naam': input("Naam: "),
        'team': input("Team: "),
        'prijs': float(input("Prijs (in miljoenen): "))
    }
    
    if data_collector.voeg_coureur_toe(coureur_data):
        print(f"Coureur {coureur_data['naam']} toegevoegd!")
    else:
        print("Coureur met dit ID bestaat al!")

def update_coureur_data():
    data_collector = DataCollector()
    coureurs = data_collector.laad_coureur_data()
    
    print("\nBeschikbare coureurs:")
    for coureur in coureurs:
        print(f"{coureur.id}: {coureur.naam}")
    
    coureur_id = int(input("\nKies een coureur ID om te updaten: "))
    
    nieuwe_data = {}
    print("\nVul nieuwe waardes in (laat leeg om ongewijzigd te laten):")
    
    prijs = input("Nieuwe prijs (in miljoenen): ")
    if prijs:
        nieuwe_data['prijs'] = float(prijs)
    
    punten = input("Nieuwe punten totaal: ")
    if punten:
        nieuwe_data['punten_totaal'] = int(punten)
    
    if nieuwe_data:
        data_collector.update_coureur(coureur_id, nieuwe_data)
        print("Coureur data geüpdatet!")

if __name__ == "__main__":
    while True:
        print("\nGP TeamManager AI Assistant")
        print("1. Genereer optimaal team")
        print("2. Voeg nieuwe coureur toe")
        print("3. Update coureur data")
        print("4. Afsluiten")
        
        keuze = input("\nMaak je keuze (1-4): ")
        
        if keuze == "1":
            main()
        elif keuze == "2":
            voeg_nieuwe_coureur_toe()
        elif keuze == "3":
            update_coureur_data()
        elif keuze == "4":
            break
        else:
            print("Ongeldige keuze, probeer opnieuw.") 