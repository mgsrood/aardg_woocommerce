from typing import Dict, List, Optional
from datetime import datetime, timedelta
from gptm.api.openf1_client import OpenF1Client

class PerformanceAnalyzer:
    """Service voor het analyseren van F1 prestatie data."""
    
    def __init__(self):
        self.client = OpenF1Client()
        
    def analyze_driver_performance(self, driver_number: int, 
                                 start_date: Optional[str] = None,
                                 end_date: Optional[str] = None) -> Dict:
        """Analyseer de prestaties van een coureur over een bepaalde periode."""
        if not start_date:
            # Standaard laatste 3 maanden
            end = datetime.now()
            start = end - timedelta(days=90)
            start_date = start.strftime("%Y-%m-%d")
            end_date = end.strftime("%Y-%m-%d")
            
        # Haal alle sessies op voor de periode
        sessions = self.client.get_session_data(date_start=start_date, date_end=end_date)
        
        performance_summary = {
            "average_finish_position": 0,
            "average_qualifying_position": 0,
            "dnf_rate": 0,
            "points_scored": 0,
            "top_speeds": [],
            "circuit_performance": {}
        }
        
        race_sessions = [s for s in sessions if s.get("type") == "Race"]
        quali_sessions = [s for s in sessions if "Qualifying" in s.get("type", "")]
        
        # Analyseer race prestaties
        if race_sessions:
            race_positions = []
            dnf_count = 0
            
            for session in race_sessions:
                session_key = session.get("session_key")
                if not session_key:
                    continue
                    
                driver_perf = self.client.get_driver_performance_data(session_key, driver_number)
                
                # Voeg circuit specifieke prestatie toe
                circuit = session.get("circuit_short_name", "unknown")
                if circuit not in performance_summary["circuit_performance"]:
                    performance_summary["circuit_performance"][circuit] = []
                
                if driver_perf["lap_times"]:
                    performance_summary["circuit_performance"][circuit].append({
                        "date": session.get("date"),
                        "average_lap_time": sum(driver_perf["lap_times"]) / len(driver_perf["lap_times"]),
                        "top_speed": driver_perf["top_speed"]
                    })
                    
                performance_summary["top_speeds"].append(driver_perf["top_speed"])
                
        # Bereken gemiddelden
        if performance_summary["top_speeds"]:
            performance_summary["average_top_speed"] = sum(performance_summary["top_speeds"]) / len(performance_summary["top_speeds"])
            
        # Bereken circuit specifieke trends
        for circuit in performance_summary["circuit_performance"]:
            performances = performance_summary["circuit_performance"][circuit]
            if performances:
                avg_lap_times = [p["average_lap_time"] for p in performances if p["average_lap_time"]]
                if avg_lap_times:
                    performance_summary["circuit_performance"][circuit] = {
                        "average_lap_time": sum(avg_lap_times) / len(avg_lap_times),
                        "performance_trend": "improving" if avg_lap_times[-1] < avg_lap_times[0] else "declining"
                    }
                    
        return performance_summary
    
    def get_circuit_characteristics(self, circuit_name: str) -> Dict:
        """Haal karakteristieken op van een specifiek circuit."""
        # Haal laatste race sessie op voor dit circuit
        sessions = self.client.get_session_data()
        circuit_sessions = [s for s in sessions if s.get("circuit_short_name") == circuit_name]
        
        if not circuit_sessions:
            return {}
            
        latest_session = circuit_sessions[-1]
        session_key = latest_session.get("session_key")
        
        characteristics = {
            "average_speed": 0,
            "top_speed_section": 0,
            "weather_sensitivity": 0,
            "overtaking_opportunities": 0
        }
        
        # Analyseer weer impact
        weather_data = self.client.get_weather_data(session_key)
        if weather_data:
            # Analyseer impact van weer op prestaties
            pass
            
        return characteristics 