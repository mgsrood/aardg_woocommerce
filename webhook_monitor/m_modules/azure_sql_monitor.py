import json
import logging
import os
import time
import socket
import psutil
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

import pyodbc
from dataclasses import dataclass


@dataclass
class AzureSQLConfig:
    server: str
    database: str
    username: str
    password: str
    driver: str = "ODBC Driver 18 for SQL Server"
    encrypt: str = "yes"
    trust_server_certificate: str = "no"


def get_config_from_env() -> AzureSQLConfig:
    """Haal Azure SQL configuratie op uit environment variabelen."""
    try:
        return AzureSQLConfig(
            server=os.environ["AZURE_SQL_SERVER"],
            database=os.environ["AZURE_SQL_DATABASE"],
            username=os.environ["AZURE_SQL_USERNAME"],
            password=os.environ["AZURE_SQL_PASSWORD"],
            driver=os.environ.get("AZURE_SQL_DRIVER", "ODBC Driver 18 for SQL Server"),
            encrypt=os.environ.get("AZURE_SQL_ENCRYPT", "yes"),
            trust_server_certificate=os.environ.get("AZURE_SQL_TRUST_SERVER_CERTIFICATE", "no"),
        )
    except KeyError as exc:
        raise ValueError(f"Ontbrekende Azure SQL environment variable: {exc.args[0]}")


def connect_azuresql(cfg: AzureSQLConfig) -> pyodbc.Connection:
    """Maak verbinding met Azure SQL Database."""
    conn_str = (
        f"DRIVER={{{cfg.driver}}};SERVER={cfg.server};DATABASE={cfg.database};"
        f"UID={cfg.username};PWD={cfg.password};"
        f"Encrypt={cfg.encrypt};TrustServerCertificate={cfg.trust_server_certificate};"
        f"Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)


def log_webhook_monitoring(
    webhook_id: int,
    webhook_name: str,
    webhook_url: Optional[str],
    previous_status: Optional[str],
    current_status: str,
    action_taken: Optional[str] = None,
    error_message: Optional[str] = None,
    response_time: Optional[int] = None
) -> None:
    """
    Log webhook monitoring resultaat naar Azure SQL.
    
    Args:
        webhook_id: WooCommerce webhook ID
        webhook_name: Naam van de webhook
        webhook_url: URL van de webhook
        previous_status: Vorige status van de webhook
        current_status: Huidige status van de webhook
        action_taken: Actie die ondernomen is ('reactivated', 'already_active', etc.)
        error_message: Error message bij problemen
        response_time: API response tijd in milliseconden
    """
    try:
        # Check of logging uitgeschakeld is
        if os.getenv('SKIP_AZURE_SQL_LOGGING', '').lower() in ['true', '1', 'yes']:
            return
        
        cfg = get_config_from_env()
        environment = os.getenv('ENVIRONMENT', 'development')
        status_changed = previous_status != current_status if previous_status else False
        
        with connect_azuresql(cfg) as conn:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO [dbo].[WebhookMonitoring] (
                    [WebhookID], [WebhookName], [WebhookURL], [PreviousStatus], [CurrentStatus],
                    [StatusChanged], [ActionTaken], [ErrorMessage], [ResponseTime], [Environment]
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    webhook_id,
                    webhook_name,
                    webhook_url,
                    previous_status,
                    current_status,
                    status_changed,
                    action_taken,
                    error_message,
                    response_time,
                    environment
                ))
                conn.commit()
        
        logging.debug(f"Webhook monitoring log geschreven voor {webhook_name}")
        
    except Exception as e:
        logging.error(f"Fout bij webhook monitoring logging: {str(e)}")


def get_system_metrics() -> Dict[str, Any]:
    """Verzamel system metrics van de VM."""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        # Network (simple ping test)
        network_latency = None
        try:
            start_time = time.time()
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            network_latency = int((time.time() - start_time) * 1000)
        except:
            pass
        
        return {
            'cpu_percent': round(cpu_percent, 2),
            'memory_percent': round(memory_percent, 2),
            'disk_percent': round(disk_percent, 2),
            'network_latency': network_latency,
            'hostname': socket.gethostname(),
            'process_id': os.getpid()
        }
    except Exception as e:
        logging.error(f"Fout bij ophalen system metrics: {e}")
        return {}


def test_webhook_app_health(app_url: str = "http://localhost:8443") -> Dict[str, Any]:
    """Test de gezondheid van de webhook applicatie."""
    try:
        start_time = time.time()
        
        # Test basis health endpoint (als deze bestaat)
        test_endpoints = [
            f"{app_url}/health",
            f"{app_url}/",
            f"{app_url}/woocommerce/add_ac_product_tag"  # Test endpoint
        ]
        
        for endpoint in test_endpoints:
            try:
                response = requests.get(endpoint, timeout=10)
                response_time = int((time.time() - start_time) * 1000)
                
                return {
                    'status': 'healthy' if response.status_code < 500 else 'unhealthy',
                    'response_time': response_time,
                    'status_code': response.status_code,
                    'endpoint': endpoint
                }
            except requests.exceptions.ConnectionError:
                continue
            except Exception as e:
                return {
                    'status': 'unhealthy',
                    'response_time': int((time.time() - start_time) * 1000),
                    'error': str(e),
                    'endpoint': endpoint
                }
        
        return {
            'status': 'unreachable',
            'response_time': None,
            'error': 'No endpoints responded'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e)
        }


def log_system_monitoring(
    monitor_type: str,
    status: str,
    message: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log system monitoring data naar Azure SQL.
    
    Args:
        monitor_type: Type monitoring ('webhook_app', 'vm_health', 'api_health')
        status: Status ('healthy', 'warning', 'critical', 'unknown')
        message: Optionele message
        **kwargs: Extra metrics (cpu_percent, memory_percent, etc.)
    """
    try:
        if os.getenv('SKIP_AZURE_SQL_LOGGING', '').lower() in ['true', '1', 'yes']:
            return
        
        cfg = get_config_from_env()
        environment = os.getenv('ENVIRONMENT', 'development')
        
        # Extract specific metrics from kwargs
        details = {}
        for key, value in kwargs.items():
            if key not in ['cpu_percent', 'memory_percent', 'disk_percent', 'network_latency',
                          'app_response_time', 'api_response_code', 'api_response_time',
                          'api_endpoint', 'hostname', 'process_id']:
                details[key] = value
        
        with connect_azuresql(cfg) as conn:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO [dbo].[SystemMonitoring] (
                    [MonitorType], [Status], [Message], [CPUUsagePercent], [MemoryUsagePercent],
                    [DiskUsagePercent], [NetworkLatency], [AppResponseTime], [APIEndpoint],
                    [APIResponseCode], [APIResponseTime], [Hostname], [ProcessID], [Details], [Environment]
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    monitor_type,
                    status,
                    message,
                    kwargs.get('cpu_percent'),
                    kwargs.get('memory_percent'),
                    kwargs.get('disk_percent'),
                    kwargs.get('network_latency'),
                    kwargs.get('app_response_time'),
                    kwargs.get('api_endpoint'),
                    kwargs.get('api_response_code'),
                    kwargs.get('api_response_time'),
                    kwargs.get('hostname'),
                    kwargs.get('process_id'),
                    json.dumps(details) if details else None,
                    environment
                ))
                conn.commit()
        
        logging.debug(f"System monitoring log geschreven voor {monitor_type}")
        
    except Exception as e:
        logging.error(f"Fout bij system monitoring logging: {str(e)}")


def create_alert(
    alert_type: str,
    severity: str,
    title: str,
    description: Optional[str] = None,
    source: Optional[str] = None
) -> None:
    """
    Maak een monitoring alert aan.
    
    Args:
        alert_type: Type alert ('webhook_down', 'vm_critical', 'app_error')
        severity: Severity ('low', 'medium', 'high', 'critical')
        title: Alert titel
        description: Uitgebreide beschrijving
        source: Bron van de alert (webhook naam, hostname, etc.)
    """
    try:
        if os.getenv('SKIP_AZURE_SQL_LOGGING', '').lower() in ['true', '1', 'yes']:
            return
        
        cfg = get_config_from_env()
        environment = os.getenv('ENVIRONMENT', 'development')
        
        with connect_azuresql(cfg) as conn:
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO [dbo].[MonitoringAlerts] (
                    [AlertType], [Severity], [Title], [Description], [Source], [Environment]
                ) VALUES (?, ?, ?, ?, ?, ?)
                """
                
                cursor.execute(sql, (
                    alert_type,
                    severity,
                    title,
                    description,
                    source,
                    environment
                ))
                conn.commit()
        
        logging.warning(f"Alert aangemaakt: {title}")
        
    except Exception as e:
        logging.error(f"Fout bij alert aanmaken: {str(e)}")


def monitor_all_systems() -> Dict[str, Any]:
    """Voer complete system monitoring uit."""
    results = {}
    
    # VM Health monitoring
    try:
        vm_metrics = get_system_metrics()
        vm_status = 'healthy'
        
        # Bepaal status op basis van metrics
        if vm_metrics.get('cpu_percent', 0) > 90:
            vm_status = 'critical'
        elif vm_metrics.get('cpu_percent', 0) > 75:
            vm_status = 'warning'
        
        if vm_metrics.get('memory_percent', 0) > 90:
            vm_status = 'critical'
        elif vm_metrics.get('memory_percent', 0) > 80:
            vm_status = max(vm_status, 'warning')
        
        log_system_monitoring('vm_health', vm_status, 'VM health check', **vm_metrics)
        results['vm_health'] = {'status': vm_status, 'metrics': vm_metrics}
        
        # Alert bij kritieke situaties
        if vm_status == 'critical':
            create_alert(
                'vm_critical',
                'high',
                'VM Resources Critical',
                f"CPU: {vm_metrics.get('cpu_percent')}%, Memory: {vm_metrics.get('memory_percent')}%",
                vm_metrics.get('hostname')
            )
            
    except Exception as e:
        log_system_monitoring('vm_health', 'error', f'VM monitoring failed: {e}')
        results['vm_health'] = {'status': 'error', 'error': str(e)}
    
    # Webhook App Health monitoring
    try:
        app_health = test_webhook_app_health()
        log_system_monitoring(
            'webhook_app', 
            app_health['status'], 
            'Webhook app health check',
            app_response_time=app_health.get('response_time'),
            api_response_code=app_health.get('status_code'),
            api_endpoint=app_health.get('endpoint')
        )
        results['webhook_app'] = app_health
        
        # Alert bij app problemen
        if app_health['status'] in ['unhealthy', 'unreachable', 'error']:
            create_alert(
                'app_error',
                'high',
                'Webhook App Unhealthy',
                f"App status: {app_health['status']}, Error: {app_health.get('error', 'Unknown')}",
                'webhook_verwerker'
            )
            
    except Exception as e:
        log_system_monitoring('webhook_app', 'error', f'App monitoring failed: {e}')
        results['webhook_app'] = {'status': 'error', 'error': str(e)}
    
    return results
