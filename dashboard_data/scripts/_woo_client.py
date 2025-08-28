from __future__ import annotations

import os
import time
import logging
from typing import Dict, Iterator, List, Optional

import requests
from requests import Response


class WooClient:
    def __init__(
        self,
        base_url: str,
        consumer_key: str,
        consumer_secret: str,
        api_version: str = "wc/v3",
        timeout_seconds: float = 60.0,
        rate_limit_sleep_seconds: float = 0.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.api_version = api_version.strip("/")
        self.timeout_seconds = timeout_seconds
        self.rate_limit_sleep_seconds = rate_limit_sleep_seconds

    def _make_url(self, resource_path: str, api_version: Optional[str] = None) -> str:
        resource = resource_path.strip("/")
        version = api_version or self.api_version
        return f"{self.base_url}/wp-json/{version}/{resource}"

    def get(self, resource_path: str, params: Optional[Dict[str, str]] = None, max_retries: int = 3, api_version: Optional[str] = None) -> Response:
        params = params.copy() if params else {}
        params.update({
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
        })
        url = self._make_url(resource_path, api_version)
        
        for attempt in range(max_retries):
            try:
                resp = requests.get(url, params=params, timeout=self.timeout_seconds)
                if self.rate_limit_sleep_seconds > 0:
                    time.sleep(self.rate_limit_sleep_seconds)
                resp.raise_for_status()
                return resp
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    continue
                raise e
            except Exception as e:
                raise e

    def paginate(self, resource_path: str, params: Optional[Dict[str, str]] = None, per_page: int = 100, api_version: Optional[str] = None) -> Iterator[List[dict]]:
        page = 1
        total_items = 0
        logging.info(f"Start pagineren van {resource_path} (per_page={per_page})")
        
        while True:
            page_params: Dict[str, str] = {"per_page": str(per_page), "page": str(page)}
            if params:
                page_params.update({k: str(v) for k, v in params.items()})
            
            logging.info(f"Ophalen pagina {page} van {resource_path}...")
            resp = self.get(resource_path, page_params, api_version=api_version)
            data = resp.json()
            
            if not isinstance(data, list):
                logging.warning(f"Onverwacht response type voor {resource_path} pagina {page}: {type(data)}")
                break
            if len(data) == 0:
                logging.info(f"Geen data meer gevonden op pagina {page}, stoppen met pagineren")
                break
            
            total_items += len(data)
            logging.info(f"Pagina {page}: {len(data)} items ontvangen (totaal: {total_items})")
            yield data
            page += 1
