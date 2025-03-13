import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import logging
import random
import time

logger = logging.getLogger(__name__)

class OpenF1Client:
    """Client voor het ophalen van F1 data via de OpenF1 API."""
    
    BASE_URL = "https://api.openf1.org/v1"
    
    def __init__(self):
        self.session = requests.Session()
        self.use_mock = False  # Gebruik echte data
        self.retry_count = 3
        self.retry_delay = 1  # seconden
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Basis methode voor het maken van API requests met retry mechanisme."""
        if self.use_mock:
            return self._get_mock_data(endpoint, params)
            
        url = f"{self.BASE_URL}/{endpoint}"
        attempts = 0
        
        while attempts < self.retry_count:
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                attempts += 1
                if attempts == self.retry_count:
                    logger.error(f"Fout bij ophalen data van {url} na {self.retry_count} pogingen: {str(e)}")
                    if self.use_mock:
                        logger.info("Terugvallen op mock data...")
                        return self._get_mock_data(endpoint, params)
                    return []
                logger.warning(f"Poging {attempts} mislukt, nieuwe poging over {self.retry_delay} seconden...")
                time.sleep(self.retry_delay)

    def _get_mock_data(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Genereer mock data voor testing en development."""
        if endpoint == "sessions":
            return self._mock_sessions()
        elif endpoint == "car_data":
            return self._mock_car_data(params)
        elif endpoint == "laps":
            return self._mock_lap_data(params)
        elif endpoint == "weather":
            return self._mock_weather_data()
        return []

    def _mock_sessions(self) -> List[Dict]:
        """Genereer mock sessie data."""
        sessions = []
        base_date = datetime.now() - timedelta(days=30)
        
        for i in range(5):
            session_date = base_date + timedelta(days=i*7)
            sessions.append({
                "session_key": 1000 + i,
                "meeting_key": 100 + i,
                "session_name": f"Race {i+1}",
                "session_type": "Race",
                "date": session_date.isoformat(),
                "circuit_short_name": f"Circuit_{i+1}",
                "circuit_key": i+1
            })
        return sessions

    def _mock_car_data(self, params: Optional[Dict]) -> List[Dict]:
        """Genereer mock car telemetrie data."""
        data = []
        base_time = datetime.now()
        
        for i in range(10):
            data.append({
                "date": (base_time + timedelta(seconds=i)).isoformat(),
                "speed": random.randint(280, 340),
                "rpm": random.randint(10000, 15000),
                "gear": random.randint(1, 8),
                "throttle": random.randint(0, 100),
                "brake": random.randint(0, 100),
                "drs": random.choice([0, 1, 8, 10, 12, 14])
            })
        return data

    def _mock_lap_data(self, params: Optional[Dict]) -> List[Dict]:
        """Genereer mock rondetijd data."""
        data = []
        base_time = datetime.now()
        
        for i in range(5):
            data.append({
                "date": (base_time + timedelta(minutes=i*2)).isoformat(),
                "lap_number": i + 1,
                "lap_duration": random.uniform(80.0, 85.0),
                "sector_1_time": random.uniform(25.0, 27.0),
                "sector_2_time": random.uniform(27.0, 29.0),
                "sector_3_time": random.uniform(26.0, 28.0),
                "is_pit_out_lap": False,
                "is_pit_in_lap": False
            })
        return data

    def _mock_weather_data(self) -> List[Dict]:
        """Genereer mock weer data."""
        return [{
            "air_temperature": random.uniform(20.0, 30.0),
            "track_temperature": random.uniform(30.0, 45.0),
            "humidity": random.uniform(40.0, 60.0),
            "pressure": random.uniform(1000.0, 1020.0),
            "wind_speed": random.uniform(2.0, 8.0),
            "wind_direction": random.uniform(0, 360),
            "rainfall": random.choice([0, 0, 0, 1])
        }]

    def get_driver_data(self, session_key: Union[int, str], driver_number: Optional[int] = None) -> List[Dict]:
        """Haal coureur data op voor een specifieke sessie."""
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._make_request("drivers", params)

    def get_car_data(self, session_key: Union[int, str], driver_number: Optional[int] = None) -> List[Dict]:
        """Haal telemetrie data op van een auto."""
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._make_request("car_data", params)

    def get_lap_data(self, session_key: Union[int, str], driver_number: Optional[int] = None) -> List[Dict]:
        """Haal rondetijden data op."""
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._make_request("laps", params)

    def get_session_data(self, year: Optional[int] = None, date_start: Optional[str] = None, date_end: Optional[str] = None) -> List[Dict]:
        """Haal sessie informatie op."""
        params = {}
        if year:
            params["year"] = year
        if date_start:
            params["date_start"] = date_start
        if date_end:
            params["date_end"] = date_end
        return self._make_request("sessions", params)

    def get_weather_data(self, session_key: Union[int, str]) -> List[Dict]:
        """Haal weer data op voor een specifieke sessie."""
        params = {"session_key": session_key}
        return self._make_request("weather", params)

    def get_driver_performance_data(self, session_key: Union[int, str], driver_number: int) -> Dict:
        """Verzamel prestatie data voor een coureur in een specifieke sessie."""
        performance_data = {
            "lap_times": [],
            "top_speed": 0,
            "average_speed": 0,
            "sector_times": [],
            "track_position_changes": 0,
            "raw_data": {}
        }
        
        # Haal basis coureur informatie op
        driver_info = self.get_driver_data(session_key, driver_number)
        if driver_info:
            performance_data["raw_data"]["driver_info"] = driver_info[0]
        
        # Haal lap data op
        lap_data = self.get_lap_data(session_key, driver_number)
        if lap_data:
            performance_data["lap_times"] = [lap.get("lap_duration") for lap in lap_data if lap.get("lap_duration")]
            performance_data["raw_data"]["lap_data"] = lap_data
            
            # Bereken sector tijden statistieken
            sector_times = []
            for lap in lap_data:
                if all(lap.get(f"sector_{i}_time") for i in range(1, 4)):
                    sector_times.append({
                        "s1": lap["sector_1_time"],
                        "s2": lap["sector_2_time"],
                        "s3": lap["sector_3_time"]
                    })
            performance_data["sector_times"] = sector_times
        
        # Haal car data op voor snelheid analyse
        car_data = self.get_car_data(session_key, driver_number)
        if car_data:
            speeds = [data.get("speed", 0) for data in car_data]
            if speeds:
                performance_data["top_speed"] = max(speeds)
                performance_data["average_speed"] = sum(speeds) / len(speeds)
            performance_data["raw_data"]["car_data"] = car_data
        
        # Voeg weer data toe
        weather_data = self.get_weather_data(session_key)
        if weather_data:
            performance_data["raw_data"]["weather_data"] = weather_data
        
        return performance_data

    def analyze_driver_performance(self, performance_data: Dict) -> Dict:
        """Analyseer de prestatie data van een coureur en bereken scores."""
        analysis = {
            "consistency_score": 0.0,
            "speed_score": 0.0,
            "weather_adaptation": 0.0,
            "overall_score": 0.0
        }
        
        # Bereken consistency score op basis van lap tijden
        if performance_data["lap_times"]:
            valid_times = [t for t in performance_data["lap_times"] if 60 < t < 120]  # Filter onrealistische tijden
            if valid_times:
                mean_time = sum(valid_times) / len(valid_times)
                variance = sum((t - mean_time) ** 2 for t in valid_times) / len(valid_times)
                analysis["consistency_score"] = max(0, 100 - (variance * 10))
        
        # Bereken speed score
        if performance_data["top_speed"] > 0:
            # Normaliseer top snelheid (300-350 km/h is normaal bereik)
            speed_score = (performance_data["top_speed"] - 300) / 50 * 100
            analysis["speed_score"] = max(0, min(100, speed_score))
        
        # Bereken weather adaptation score als er weer data beschikbaar is
        weather_data = performance_data["raw_data"].get("weather_data", [])
        if weather_data and performance_data["lap_times"]:
            # Simpele analyse van prestaties onder verschillende weersomstandigheden
            # Dit kan verder uitgebreid worden met meer complexe analyses
            analysis["weather_adaptation"] = 75.0  # Basis score
        
        # Bereken overall score (gewogen gemiddelde)
        weights = {
            "consistency_score": 0.4,
            "speed_score": 0.4,
            "weather_adaptation": 0.2
        }
        
        analysis["overall_score"] = sum(
            score * weights[metric] 
            for metric, score in analysis.items() 
            if metric != "overall_score"
        )
        
        return analysis 