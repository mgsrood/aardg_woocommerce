#!/usr/bin/env python3
import os
import sys
import logging

# Voeg de root directory toe aan Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gptm.services.team_optimizer import TeamOptimizer

# Configureer logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def format_currency(amount: float) -> str:
    """Format een bedrag als valuta string."""
    return f"€{amount:.1f}M"

def print_team_recommendation(team: dict, index: int = 1, upcoming_races: list = None):
    """Print een team aanbeveling op een geformatteerde manier met motivatie."""
    print(f"\nTeam Optie {index}")
    print("=" * 50)
    
    # Coureurs
    print("\nCoureurs:")
    for i, driver in enumerate(team['drivers'], 1):
        print(f"{i}. {driver['naam']} ({format_currency(driver['prijs'])})")
        
        # Toon coureur specifieke motivatie
        if i == 1:
            print("   Eerste coureur - Extra punten bonus van 25%")
        print(f"   - Betrouwbaarheidsscore: {driver.get('betrouwbaarheid_score', 0):.1f}")
        print(f"   - Gemiddelde kwalificatie positie: {driver.get('gemiddelde_kwalificatie_positie', 0):.1f}")
        print(f"   - Gemiddelde finish positie: {driver.get('gemiddelde_finish_positie', 0):.1f}")
        
        # Circuit specifieke prestaties
        if upcoming_races and driver.get('circuit_prestaties'):
            print("   Circuit prestaties voor komende races:")
            for race in upcoming_races[:3]:  # Toon eerste 3 races
                circuit = race['race']['circuit']
                if circuit in driver['circuit_prestaties']:
                    perf = driver['circuit_prestaties'][circuit]
                    print(f"   - {race['race']['naam']}: {perf.get('performance_rating', 'Geen data')}")
    
    # Chassis & Motor
    print(f"\nChassis: {team['chassis']['naam']} ({format_currency(team['chassis']['prijs'])})")
    print(f"Motor: {team['engine']['naam']} ({format_currency(team['engine']['prijs'])})")
    
    # Team synergie
    if team['chassis']['team'] == team['engine']['team']:
        print("\nTeam Synergie Bonus: +10% (matching chassis/motor combinatie)")
    
    # Budget informatie
    print(f"\nTotale kosten: {format_currency(team['total_cost'])}")
    print(f"Resterend budget: {format_currency(team['remaining_budget'])}")
    
    # Strategie motivatie
    print("\nStrategie Motivatie:")
    print(f"- Prijs/prestatie verhouding: {team.get('value_score', 0):.2f}")
    print("- Komende races overwegingen:")
    if upcoming_races:
        for race in upcoming_races[:3]:
            print(f"  * {race['race']['naam']} ({race['race']['circuit_type']})")
            if race['race'].get('sprint_race'):
                print("    + Sprint race weekend - extra punten mogelijkheid")
    
    # Team score
    print(f"\nTeam Score: {team['team_score']:.2f}")
    print("=" * 50)

def main():
    """Hoofdfunctie van de applicatie."""
    try:
        logger.info("GP TeamManager Optimizer wordt gestart...")
        
        # Initialiseer de optimizer
        optimizer = TeamOptimizer()
        
        # Haal team aanbevelingen op
        logger.info("Bezig met analyseren van optimale team samenstellingen...")
        results = optimizer.get_optimal_team_composition()
        
        # Print de top 3 aanbevelingen
        print("\nTop 3 Aanbevolen Teams")
        print("=" * 50)
        
        for i, team in enumerate(results['recommended_teams'], 1):
            print_team_recommendation(team, i, results.get('upcoming_races'))
        
        # Print informatie over komende races
        print("\nKomende Races")
        print("=" * 50)
        
        for race in results['upcoming_races']:
            race_info = race['race']
            print(f"\n{race_info['naam']} - {race_info['datum']}")
            print(f"Circuit: {race_info['circuit']}")
            print(f"Type: {race_info['circuit_type']}")
            if race_info.get('sprint_race'):
                print("* Sprint race weekend")
            
            # Toon circuit karakteristieken
            if race.get('characteristics'):
                chars = race['characteristics']
                print("\nCircuit karakteristieken:")
                print(f"- Gemiddelde snelheid: {chars.get('average_speed', 0):.0f} km/h")
                print(f"- Inhaal mogelijkheden: {chars.get('overtaking_opportunities', 0)}")
                print(f"- Weer gevoeligheid: {chars.get('weather_sensitivity', 0)}")
        
        logger.info("Analyse succesvol afgerond!")
        
    except Exception as e:
        logger.error(f"Er is een fout opgetreden: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 