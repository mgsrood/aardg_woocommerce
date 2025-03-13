from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os
import json
import logging
from gptm.api.openf1_client import OpenF1Client
from gptm.services.performance_analyzer import PerformanceAnalyzer
from statistics import mean, stdev

logger = logging.getLogger(__name__)

class TeamOptimizer:
    """Service voor het optimaliseren van F1 team samenstellingen."""
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
        self.f1_client = OpenF1Client()
        self.analyzer = PerformanceAnalyzer()
        
    def _load_json_data(self, filename: str) -> Dict:
        """Laad data uit een JSON bestand."""
        file_path = os.path.join(self.data_dir, filename)
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                # Zorg ervoor dat we de juiste data structuur hebben
                if filename == "coureurs.json":
                    return data.get("coureurs", [])
                elif filename == "motoren.json":
                    return data.get("motoren", [])
                elif filename == "chassis.json":
                    return data.get("chassis", [])
                elif filename == "kalender.json":
                    return data.get("races", [])
                return data
        except FileNotFoundError:
            logger.error(f"Bestand niet gevonden: {file_path}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Ongeldig JSON bestand: {file_path}")
            return []

    def analyze_upcoming_circuits(self) -> List[Dict]:
        """Analyseer de komende circuits en hun karakteristieken."""
        calendar = self._load_json_data("kalender.json")
        if not calendar:
            return []
        
        # Filter op toekomstige races
        today = datetime.now()
        upcoming_races = []
        
        for race in calendar:
            try:
                race_date = datetime.fromisoformat(race.get("datum", ""))
                if race_date > today:
                    # Voeg circuit analyse toe
                    race_analysis = {
                        "race": race,
                        "characteristics": self._analyze_circuit(race.get("circuit", ""))
                    }
                    upcoming_races.append(race_analysis)
            except (ValueError, TypeError) as e:
                logger.warning(f"Ongeldige datum voor race: {race.get('naam', 'Onbekend')}")
                continue
        
        return upcoming_races[:5]  # Return alleen de eerst volgende 5 races

    def _analyze_circuit(self, circuit: str) -> Dict:
        """Analyseer een circuit op basis van historische data."""
        # Haal historische sessie data op voor dit circuit
        sessions = self.f1_client.get_session_data()
        circuit_sessions = [s for s in sessions if s.get("circuit_key") == circuit]
        
        if not circuit_sessions:
            return {
                "average_speed": 0,
                "overtaking_opportunities": 0,
                "weather_sensitivity": 0
            }
        
        # Analyseer de meest recente sessie
        latest_session = circuit_sessions[-1]
        session_key = latest_session.get("session_key")
        
        # Verzamel lap data
        lap_data = self.f1_client.get_lap_data(session_key)
        
        # Bereken gemiddelde snelheid
        car_data = self.f1_client.get_car_data(session_key)
        speeds = [d.get("speed", 0) for d in car_data if d.get("speed")]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0
        
        # Schat inhaal mogelijkheden (simpele heuristiek)
        position_changes = len([l for l in lap_data if l.get("position_change", 0) != 0])
        overtaking_score = min(100, (position_changes / len(lap_data)) * 100) if lap_data else 0
        
        # Analyseer weer gevoeligheid
        weather_data = self.f1_client.get_weather_data(session_key)
        weather_changes = len([w for w in weather_data if w.get("rainfall", 0) > 0])
        weather_sensitivity = min(100, (weather_changes / len(weather_data)) * 100) if weather_data else 0
        
        return {
            "average_speed": avg_speed,
            "overtaking_opportunities": overtaking_score,
            "weather_sensitivity": weather_sensitivity
        }

    def analyze_driver_potential(self, driver_number: int, upcoming_races: List[Dict]) -> Dict:
        """Analyseer het potentieel van een coureur voor de komende races."""
        # Haal historische prestaties op
        performance = self.analyzer.analyze_driver_performance(driver_number)
        
        # Analyseer geschiktheid voor komende circuits
        circuit_suitability = {}
        for race in upcoming_races:
            circuit = race['race']['circuit']
            if circuit in performance['circuit_performance']:
                circuit_data = performance['circuit_performance'][circuit]
                circuit_suitability[circuit] = {
                    'historical_performance': circuit_data,
                    'expected_performance': self._calculate_expected_performance(
                        circuit_data,
                        race['characteristics']
                    )
                }
                
        return {
            'historical_performance': performance,
            'circuit_suitability': circuit_suitability
        }
        
    def _calculate_expected_performance(self, historical_data: Dict, circuit_chars: Dict) -> float:
        """Bereken verwachte prestatie op basis van historische data en circuit karakteristieken."""
        # Basis score
        base_score = 0.0
        
        if historical_data.get('performance_trend') == 'improving':
            base_score += 0.2
            
        # Voeg hier meer complexe berekeningen toe op basis van:
        # - Weer gevoeligheid
        # - Circuit type (street vs permanent)
        # - Inhaal mogelijkheden
        # - etc.
            
        return base_score
        
    def get_optimal_team_composition(self) -> Dict:
        """Bepaal de optimale team samenstelling."""
        budget = 100.0  # Budget in miljoenen
        
        # Laad basis data
        drivers = self._load_json_data("coureurs.json")
        engines = self._load_json_data("motoren.json")
        chassis = self._load_json_data("chassis.json")
        
        if not all([drivers, engines, chassis]):
            logger.error("Kon niet alle benodigde data laden")
            return {"error": "Missende data bestanden"}
        
        # Analyseer komende races
        upcoming_races = self.analyze_upcoming_circuits()
        
        # Update coureur prestaties met echte data
        self._update_driver_performances(drivers, upcoming_races)
        
        # Genereer alle mogelijke team combinaties
        teams = self._generate_team_combinations(drivers, engines, chassis, budget)
        
        # Sorteer teams op score
        teams.sort(key=lambda x: x.get("team_score", 0), reverse=True)
        
        return {
            "recommended_teams": teams[:3],  # Top 3 teams
            "upcoming_races": upcoming_races
        }

    def _get_historical_sessions(self, days: int = 365) -> List[Dict]:
        """Haal historische sessie data op van het afgelopen jaar."""
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        return self.f1_client.get_session_data(date_start=start_date)
    
    def _analyze_historical_performance(self, driver_number: int, sessions: List[Dict]) -> Dict:
        """Analyseer historische prestaties van een coureur."""
        performance_history = {
            "races_completed": 0,
            "average_finish_position": 0,
            "podium_percentage": 0,
            "dnf_percentage": 0,
            "qualifying_performance": 0,
            "wet_race_performance": 0,
            "consistency_trend": 0,
            "improvement_rate": 0
        }
        
        if not sessions:
            return performance_history
            
        # Verzamel race resultaten
        race_positions = []
        podiums = 0
        dnfs = 0
        wet_race_scores = []
        qualifying_positions = []
        
        for session in sessions:
            session_key = session.get("session_key")
            if not session_key:
                continue
                
            # Haal prestatie data op
            perf_data = self.f1_client.get_driver_performance_data(session_key, driver_number)
            
            # Race analyse
            if session.get("session_type") == "Race":
                if lap_data := perf_data.get("raw_data", {}).get("lap_data", []):
                    # Check finish positie
                    final_position = lap_data[-1].get("position")
                    if final_position:
                        race_positions.append(final_position)
                        if final_position <= 3:
                            podiums += 1
                    
                    # Check DNF
                    if len(lap_data) < session.get("total_laps", 0):
                        dnfs += 1
                    
                    # Weer prestatie
                    if weather := perf_data.get("raw_data", {}).get("weather_data"):
                        if any(w.get("rainfall", 0) > 0 for w in weather):
                            wet_score = self._calculate_wet_performance(perf_data)
                            wet_race_scores.append(wet_score)
            
            # Kwalificatie analyse
            elif session.get("session_type") in ["Qualifying", "Sprint Qualifying"]:
                if qual_data := perf_data.get("raw_data", {}).get("lap_data", []):
                    best_position = min((lap.get("position", float("inf")) for lap in qual_data), default=None)
                    if best_position:
                        qualifying_positions.append(best_position)
        
        # Bereken statistieken
        if race_positions:
            performance_history["races_completed"] = len(race_positions)
            performance_history["average_finish_position"] = mean(race_positions)
            performance_history["podium_percentage"] = (podiums / len(race_positions)) * 100
            performance_history["dnf_percentage"] = (dnfs / len(race_positions)) * 100
        
        if qualifying_positions:
            performance_history["qualifying_performance"] = mean(qualifying_positions)
        
        if wet_race_scores:
            performance_history["wet_race_performance"] = mean(wet_race_scores)
        
        # Bereken trends
        if len(race_positions) > 1:
            try:
                consistency = stdev(race_positions)
                performance_history["consistency_trend"] = 100 - (consistency * 10)  # Hoger is consistenter
                
                # Bereken verbetering over tijd
                first_half = mean(race_positions[:len(race_positions)//2])
                second_half = mean(race_positions[len(race_positions)//2:])
                performance_history["improvement_rate"] = ((first_half - second_half) / first_half) * 100
            except:
                logger.warning(f"Kon geen trends berekenen voor coureur {driver_number}")
        
        return performance_history

    def _calculate_wet_performance(self, performance_data: Dict) -> float:
        """Bereken prestatie score voor natte condities."""
        score = 0.0
        
        # Gebruik lap times voor consistentie in natte condities
        if lap_times := performance_data.get("lap_times", []):
            valid_times = [t for t in lap_times if 60 < t < 120]  # Filter onrealistische tijden
            if valid_times:
                # Lagere variatie = betere prestatie in regen
                try:
                    variation = stdev(valid_times) / mean(valid_times)
                    score += max(0, 100 - (variation * 1000))
                except:
                    pass
        
        # Gebruik car data voor controle in natte condities
        if car_data := performance_data.get("raw_data", {}).get("car_data", []):
            # Analyseer throttle/brake patronen
            smooth_inputs = 0
            total_inputs = 0
            
            for i in range(1, len(car_data)):
                prev = car_data[i-1]
                curr = car_data[i]
                
                # Tel grote veranderingen in gas/rem gebruik
                throttle_change = abs(curr.get("throttle", 0) - prev.get("throttle", 0))
                brake_change = abs(curr.get("brake", 0) - prev.get("brake", 0))
                
                if throttle_change > 0 or brake_change > 0:
                    total_inputs += 1
                    if throttle_change < 20 and brake_change < 20:  # Soepele inputs
                        smooth_inputs += 1
            
            if total_inputs > 0:
                smoothness_score = (smooth_inputs / total_inputs) * 100
                score = (score + smoothness_score) / 2
        
        return score

    def _update_driver_performances(self, drivers: List[Dict], upcoming_races: List[Dict]) -> None:
        """Update coureur prestaties met recente en historische data."""
        # Haal historische data op
        historical_sessions = self._get_historical_sessions()
        
        # Haal recente sessies op voor real-time prestaties
        recent_sessions = self.f1_client.get_session_data(
            date_start=(datetime.now() - timedelta(days=30)).isoformat()
        )
        
        if not recent_sessions and not historical_sessions:
            logger.warning("Geen sessie data beschikbaar")
            return
        
        # Update elke coureur
        for driver in drivers:
            driver_number = driver.get("nummer")
            if not driver_number:
                continue
            
            # Analyseer historische prestaties
            historical_perf = self._analyze_historical_performance(driver_number, historical_sessions)
            
            # Verzamel recente prestatie data
            recent_performance = {}
            for session in recent_sessions[-3:]:
                session_key = session.get("session_key")
                if session_key:
                    perf = self.f1_client.get_driver_performance_data(session_key, driver_number)
                    analysis = self.f1_client.analyze_driver_performance(perf)
                    recent_performance[session.get("circuit_key", "")] = {
                        "performance_rating": analysis.get("overall_score", 0),
                        "consistency": analysis.get("consistency_score", 0),
                        "speed": analysis.get("speed_score", 0),
                        "weather_adaptation": analysis.get("weather_adaptation", 0)
                    }
            
            # Combineer historische en recente data voor een totaalscore
            if recent_performance:
                recent_rating = mean(d.get("performance_rating", 0) for d in recent_performance.values())
                historical_rating = (
                    (100 - historical_perf["average_finish_position"] * 5) +  # Positie naar score
                    historical_perf["podium_percentage"] * 0.5 +              # Podium bonus
                    historical_perf["consistency_trend"] * 0.3 +              # Consistentie bonus
                    max(0, historical_perf["improvement_rate"]) * 0.2         # Verbetering bonus
                ) / 2  # Schaal naar 0-100
                
                # Gewogen gemiddelde: recente prestaties tellen zwaarder mee
                driver["betrouwbaarheid_score"] = (recent_rating * 0.7 + historical_rating * 0.3)
            else:
                # Alleen historische data beschikbaar
                driver["betrouwbaarheid_score"] = (
                    (100 - historical_perf["average_finish_position"] * 5) +
                    historical_perf["podium_percentage"] * 0.5 +
                    historical_perf["consistency_trend"] * 0.3
                ) / 2
            
            # Update prestatie data
            driver["circuit_prestaties"] = recent_performance
            driver["historische_prestaties"] = historical_perf

    def _generate_team_combinations(self, drivers: List[Dict], engines: List[Dict], chassis: List[Dict], budget: float) -> List[Dict]:
        """Genereer alle mogelijke team combinaties binnen het budget."""
        valid_teams = []
        
        for engine in engines:
            engine_price = engine.get("prijs", 0)
            for chass in chassis:
                chassis_price = chass.get("prijs", 0)
                # Check chassis/motor combinatie budget
                if engine_price + chassis_price >= budget:
                    continue
                    
                remaining_budget = budget - engine_price - chassis_price
                
                # Zoek coureur combinaties
                for i, driver1 in enumerate(drivers):
                    driver1_price = driver1.get("prijs", 0)
                    if driver1_price > remaining_budget:
                        continue
                        
                    for driver2 in drivers[i+1:]:
                        driver2_price = driver2.get("prijs", 0)
                        total_cost = engine_price + chassis_price + driver1_price + driver2_price
                        
                        if total_cost <= budget:
                            # Bereken team score
                            team = {
                                "drivers": [driver1, driver2],
                                "engine": engine,
                                "chassis": chass,
                                "total_cost": total_cost,
                                "remaining_budget": budget - total_cost
                            }
                            
                            team_score = self._calculate_team_score(team)
                            team["team_score"] = team_score
                            team["value_score"] = team_score / total_cost if total_cost > 0 else 0
                            
                            valid_teams.append(team)
        
        return valid_teams

    def _calculate_team_score(self, team: Dict) -> float:
        """Bereken een totaal score voor een team samenstelling."""
        score = 0.0
        
        # Coureur scores met historische context
        driver_weights = [1.25, 1.0]  # Eerste coureur krijgt 25% bonus
        for driver, weight in zip(team.get("drivers", []), driver_weights):
            # Basis score van betrouwbaarheid
            driver_score = driver.get("betrouwbaarheid_score", 0) * weight
            
            # Voeg historische prestatie bonus toe
            if hist_perf := driver.get("historische_prestaties", {}):
                # Bonus voor consistentie en verbetering
                consistency_bonus = hist_perf.get("consistency_trend", 0) * 0.2
                improvement_bonus = max(0, hist_perf.get("improvement_rate", 0)) * 0.1
                
                # Bonus voor prestatie in verschillende condities
                wet_bonus = hist_perf.get("wet_race_performance", 0) * 0.15
                qualifying_bonus = (20 - hist_perf.get("qualifying_performance", 20)) * 0.15
                
                driver_score += (consistency_bonus + improvement_bonus + wet_bonus + qualifying_bonus) * weight
            
            score += driver_score
        
        # Chassis/motor synergie bonus
        if team.get("chassis", {}).get("team") == team.get("engine", {}).get("team"):
            score *= 1.1  # 10% bonus voor matching combinatie
        
        # Normaliseer score naar 0-100 schaal
        score = min(100, max(0, score))
        
        return score 