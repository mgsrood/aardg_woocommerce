import requests
from requests.auth import HTTPBasicAuth
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class MontaAPI:
    def __init__(self):
        if not current_app:
            raise RuntimeError("Deze class moet binnen een Flask applicatie context worden gebruikt")
            
        self.api_url = current_app.config.get('MONTA_API_URL')
        if not self.api_url:
            raise ValueError("MONTA_API_URL niet geconfigureerd in Flask config")
            
        self.username = current_app.config.get('MONTA_USERNAME')
        if not self.username:
            raise ValueError("MONTA_USERNAME niet geconfigureerd in Flask config")
            
        self.password = current_app.config.get('MONTA_PASSWORD')
        if not self.password:
            raise ValueError("MONTA_PASSWORD niet geconfigureerd in Flask config")
            
        # Basic auth en content type headers
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.headers = {
            'Content-Type': 'application/json'
        }
        
        logger.info(f"MontaAPI geïnitialiseerd met URL: {self.api_url}")

    def create_order(self, order_data):
        """
        Maak een nieuwe order aan in het distributiecentrum
        
        Args:
            order_data (dict): Order gegevens volgens Monta API specificatie
            
        Returns:
            dict: Response van de Monta API
        """
        try:
            logger.info(f"Order aanmaken bij Monta: {order_data}")
            response = requests.post(
                f"{self.api_url}/order",
                auth=self.auth,
                headers=self.headers,
                json=order_data
            )
            
            # Log de volledige response voor debugging
            logger.info(f"Monta API response status: {response.status_code}")
            logger.info(f"Monta API response headers: {response.headers}")
            logger.info(f"Monta API response body: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Fout bij aanmaken Monta order: {str(e)}")
            return {"error": str(e)}

    def get_order_status(self, order_id):
        """
        Haal de status op van een order
        
        Args:
            order_id (str): Monta order ID
            
        Returns:
            dict: Order status informatie
        """
        try:
            response = requests.get(
                f"{self.api_url}/order/{order_id}",
                auth=self.auth,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Fout bij ophalen Monta order status: {str(e)}")
            return {"error": str(e)} 