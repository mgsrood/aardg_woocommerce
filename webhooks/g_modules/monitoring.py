from functools import wraps
from redis import Redis
import time
import os
import psutil
import traceback
from flask import request
from datetime import datetime

class Monitoring:
    def __init__(self):
        self.redis_client = Redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.metrics_prefix = "metrics:"
        self.cache_prefix = "cache:"
        self.error_prefix = "errors:"
    
    def track_endpoint_timing(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                response = f(*args, **kwargs)
                duration = round((time.time() - start_time) * 1000, 2)
                
                # Sla response tijd op
                endpoint = request.endpoint
                self.redis_client.lpush(
                    f"{self.metrics_prefix}response_times:{endpoint}",
                    duration
                )
                # Houd alleen laatste 100 metingen
                self.redis_client.ltrim(f"{self.metrics_prefix}response_times:{endpoint}", 0, 99)
                
                return response
            except Exception as e:
                # Track error
                self.track_error(request.endpoint, e)
                raise
        return decorated_function
    
    def track_cache_stats(self, key, hit):
        """Houdt cache hits/misses bij, zowel globaal als per functie"""
        function_name = key.split(':')[0]  # Eerste deel van de key is functienaam
        
        # Globale statistieken
        if hit:
            self.redis_client.incr(f"{self.metrics_prefix}cache:hits")
            self.redis_client.incr(f"{self.metrics_prefix}cache:func:{function_name}:hits")
        else:
            self.redis_client.incr(f"{self.metrics_prefix}cache:misses")
            self.redis_client.incr(f"{self.metrics_prefix}cache:func:{function_name}:misses")
    
    def track_error(self, endpoint, error):
        """Track errors met stack trace en timestamp"""
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "message": str(error),
            "stack_trace": traceback.format_exc()
        }
        # Sla error op in lijst, maximum 100 errors per endpoint
        self.redis_client.lpush(
            f"{self.error_prefix}{endpoint}",
            str(error_data)
        )
        self.redis_client.ltrim(f"{self.error_prefix}{endpoint}", 0, 99)
    
    def get_cache_stats(self):
        """Haalt cache statistieken op, inclusief per-functie statistieken"""
        # Globale stats
        hits = int(self.redis_client.get(f"{self.metrics_prefix}cache:hits") or 0)
        misses = int(self.redis_client.get(f"{self.metrics_prefix}cache:misses") or 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        
        # Per-functie stats
        function_stats = {}
        for key in self.redis_client.scan_iter(f"{self.metrics_prefix}cache:func:*"):
            func_name = key.decode().split(':')[3]  # Haal functienaam uit key
            if func_name not in function_stats:
                function_stats[func_name] = {"hits": 0, "misses": 0}
            
            if key.decode().endswith(":hits"):
                function_stats[func_name]["hits"] = int(self.redis_client.get(key) or 0)
            elif key.decode().endswith(":misses"):
                function_stats[func_name]["misses"] = int(self.redis_client.get(key) or 0)
        
        # Bereken hit rates per functie
        for func_stats in function_stats.values():
            func_total = func_stats["hits"] + func_stats["misses"]
            func_stats["hit_rate"] = round((func_stats["hits"] / func_total * 100), 2) if func_total > 0 else 0
        
        return {
            "global": {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_rate": round(hit_rate, 2)
            },
            "per_function": function_stats
        }
    
    def get_endpoint_stats(self):
        """Haalt endpoint statistieken op"""
        stats = {}
        for key in self.redis_client.scan_iter(f"{self.metrics_prefix}response_times:*"):
            endpoint = key.decode().split(':')[-1]
            times = [float(x) for x in self.redis_client.lrange(key, 0, -1)]
            if times:
                stats[endpoint] = {
                    "avg_ms": round(sum(times) / len(times), 2),
                    "min_ms": round(min(times), 2),
                    "max_ms": round(max(times), 2),
                    "count": len(times)
                }
        return stats
    
    def get_error_stats(self):
        """Haalt error statistieken op per endpoint"""
        error_stats = {}
        for key in self.redis_client.scan_iter(f"{self.error_prefix}*"):
            endpoint = key.decode().replace(self.error_prefix, '')
            errors = self.redis_client.lrange(key, 0, -1)
            error_stats[endpoint] = {
                "total_errors": len(errors),
                "recent_errors": [eval(error.decode()) for error in errors[:5]]  # Laatste 5 errors
            }
        return error_stats
    
    def get_system_stats(self):
        """Haalt systeem statistieken op"""
        process = psutil.Process()
        return {
            "cpu": {
                "process_percent": process.cpu_percent(),
                "system_percent": psutil.cpu_percent()
            },
            "memory": {
                "process": {
                    "used_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                    "percent": process.memory_percent()
                },
                "system": {
                    "total_gb": round(psutil.virtual_memory().total / 1024 / 1024 / 1024, 2),
                    "available_gb": round(psutil.virtual_memory().available / 1024 / 1024 / 1024, 2),
                    "percent": psutil.virtual_memory().percent
                }
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / 1024 / 1024 / 1024, 2),
                "free_gb": round(psutil.disk_usage('/').free / 1024 / 1024 / 1024, 2),
                "percent": psutil.disk_usage('/').percent
            }
        }
    
    def get_redis_memory_stats(self):
        """Haalt Redis geheugen statistieken op"""
        try:
            info = self.redis_client.info(section="memory")
            return {
                "used_memory_human": info.get("used_memory_human", "unknown"),
                "used_memory_peak_human": info.get("used_memory_peak_human", "unknown"),
                "used_memory_lua_human": info.get("used_memory_lua_human", "unknown"),
                "maxmemory_human": info.get("maxmemory_human", "unlimited")
            }
        except Exception as e:
            return {"error": str(e)} 