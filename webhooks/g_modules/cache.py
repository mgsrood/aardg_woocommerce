from redis import Redis
import os
import json
from functools import wraps
import logging

# Redis client setup
try:
    redis_client = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
    REDIS_AVAILABLE = redis_client.ping()
    logging.info("Redis verbinding succesvol opgezet")
except Exception as e:
    REDIS_AVAILABLE = False
    redis_client = None
    logging.warning(f"Redis niet beschikbaar: {str(e)}")

def cache_decorator(timeout=300):
    """
    Decorator voor het cachen van functie resultaten.
    
    Args:
        timeout (int): Cache timeout in seconden (default: 300 seconden / 5 minuten)
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not REDIS_AVAILABLE:
                return f(*args, **kwargs)
            
            # Cache key genereren
            cache_key = f"aardg:webhook:{f.__name__}:{str(args)}:{str(kwargs)}"
            
            try:
                # Probeer uit cache te halen
                cached_result = redis_client.get(cache_key)
                if cached_result:
                    logging.info(f"Cache hit voor {cache_key}")
                    return json.loads(cached_result)
                    
            except Exception as e:
                logging.warning(f"Fout bij cache ophalen: {str(e)}")
                return f(*args, **kwargs)
                
            # Functie uitvoeren als niet in cache
            result = f(*args, **kwargs)
            
            try:
                # Resultaat cachen
                redis_client.setex(
                    cache_key,
                    timeout,
                    json.dumps(result)
                )
                logging.info(f"Resultaat gecached voor {cache_key}")
            except Exception as e:
                logging.warning(f"Fout bij cachen: {str(e)}")
                
            return result
            
        return decorated_function
    return decorator

def clear_cache(pattern="aardg:webhook:*"):
    """
    Verwijder alle cache entries die matchen met het gegeven pattern.
    
    Args:
        pattern (str): Redis key pattern om te verwijderen
    """
    if not REDIS_AVAILABLE:
        return
        
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
            logging.info(f"{len(keys)} cache entries verwijderd")
    except Exception as e:
        logging.error(f"Fout bij cache opschonen: {str(e)}")

def get_cache_status():
    """
    Verkrijg de status van de Redis cache.
    
    Returns:
        dict: Status informatie
    """
    if not REDIS_AVAILABLE:
        return {"status": "unavailable"}
        
    try:
        info = redis_client.info()
        return {
            "status": "available",
            "used_memory": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_days": info.get("uptime_in_days", 0)
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        } 