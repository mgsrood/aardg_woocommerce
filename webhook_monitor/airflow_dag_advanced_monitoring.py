"""
Geavanceerde Airflow DAG voor Multi-Interval Monitoring
- Webhook monitoring: elke 5 minuten
- System monitoring: elke 15 minuten  
- Health reports: dagelijks om 09:00
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.operators.email_operator import EmailOperator
from airflow.sensors.filesystem import FileSensor
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
import sys
import os

# Configuratie
WEBHOOK_MONITOR_PATH = "/home/maxrood/aardg/projecten/woocommerce/webhook_monitor"
ENVIRONMENT = 'production'

# Voeg pad toe
sys.path.insert(0, WEBHOOK_MONITOR_PATH)

# Default args
default_args = {
    'owner': 'aardg-monitoring',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
    'email': ['max@aardg.nl'],  # Pas aan
}

# =================================
# DAG 1: Webhook Monitoring (5 min)
# =================================
webhook_dag = DAG(
    'webhook_monitoring_5min',
    default_args=default_args,
    description='Webhook monitoring elke 5 minuten',
    schedule_interval=timedelta(minutes=5),
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['monitoring', 'webhooks', 'frequent']
)



def webhook_check():
    """Alleen webhook monitoring."""
    os.chdir(WEBHOOK_MONITOR_PATH)
    
    from m_modules.webhook_monitor import check_and_reactivate_webhooks
    from m_modules.env_tool import env_check
    from woocommerce import API
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    env_check()
    
    # API setup
    wcapi = API(
        url=os.getenv('WOOCOMMERCE_URL'),
        consumer_key=os.getenv('WOOCOMMERCE_CONSUMER_KEY'),
        consumer_secret=os.getenv('WOOCOMMERCE_CONSUMER_SECRET'),
        version="wc/v3",
        timeout=30
    )
    
    required_webhooks = [
        "Facebook Audience",
        "Product Velden", "Product Tags", "Abonnements Tag",
        "Abonnements Veld Ophogen", "Abonnements Veld Verlagen", "Besteldatum"
    ]
    
    check_and_reactivate_webhooks(wcapi, required_webhooks)
    return "Webhook check completed"

webhook_task = PythonOperator(
    task_id='webhook_monitoring',
    python_callable=webhook_check,
    dag=webhook_dag
)

# =================================
# DAG 2: System Monitoring (15 min)
# =================================
system_dag = DAG(
    'system_monitoring_15min',
    default_args=default_args,
    description='System monitoring elke 15 minuten',
    schedule_interval=timedelta(minutes=15),
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['monitoring', 'system', 'performance']
)

def system_health_check():
    """System monitoring met alerts."""
    os.chdir(WEBHOOK_MONITOR_PATH)
    
    from m_modules.azure_sql_monitor import monitor_all_systems, create_alert
    from m_modules.env_tool import env_check
    import logging
    
    env_check()
    
    logging.basicConfig(level=logging.INFO)
    
    results = monitor_all_systems()
    
    # Check voor kritieke situaties
    alerts_created = []
    for monitor_type, result in results.items():
        status = result.get('status', 'unknown')
        
        if status in ['critical', 'unhealthy', 'error']:
            alerts_created.append(f"{monitor_type}: {status}")
    
    if alerts_created:
        return f"System issues detected: {', '.join(alerts_created)}"
    else:
        return "All systems healthy"

system_task = PythonOperator(
    task_id='system_monitoring',
    python_callable=system_health_check,
    dag=system_dag
)

# =================================
# DAG 3: Daily Health Report (09:00)
# =================================
daily_dag = DAG(
    'daily_health_report',
    default_args=default_args,
    description='Dagelijkse health report om 09:00',
    schedule_interval='0 9 * * *',  # Cron: 09:00 elke dag
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['monitoring', 'daily', 'report']
)

def generate_daily_report():
    """Genereer dagelijks rapport."""
    os.chdir(WEBHOOK_MONITOR_PATH)
    
    from m_modules.azure_sql_monitor import get_config_from_env, connect_azuresql
    from m_modules.env_tool import env_check
    import json
    
    env_check()
    
    try:
        cfg = get_config_from_env()
        
        with connect_azuresql(cfg) as conn:
            with conn.cursor() as cursor:
                # Query voor laatste 24 uur webhook data
                cursor.execute("""
                    SELECT 
                        WebhookName, 
                        COUNT(*) as CheckCount,
                        SUM(CASE WHEN StatusChanged = 1 THEN 1 ELSE 0 END) as StatusChanges,
                        COUNT(CASE WHEN ActionTaken = 'reactivated' THEN 1 END) as Reactivations,
                        COUNT(CASE WHEN CurrentStatus = 'error' THEN 1 END) as Errors
                    FROM WebhookMonitoring 
                    WHERE CheckedAt >= DATEADD(hour, -24, GETDATE())
                    GROUP BY WebhookName
                """)
                
                webhook_stats = cursor.fetchall()
                
                # Query voor system health trends
                cursor.execute("""
                    SELECT 
                        MonitorType,
                        AVG(CPUUsagePercent) as AvgCPU,
                        AVG(MemoryUsagePercent) as AvgMemory,
                        AVG(AppResponseTime) as AvgResponseTime,
                        COUNT(CASE WHEN Status = 'critical' THEN 1 END) as CriticalCount
                    FROM SystemMonitoring 
                    WHERE MonitoredAt >= DATEADD(hour, -24, GETDATE())
                    GROUP BY MonitorType
                """)
                
                system_stats = cursor.fetchall()
                
                # Query voor active alerts
                cursor.execute("""
                    SELECT AlertType, Severity, COUNT(*) as Count
                    FROM MonitoringAlerts 
                    WHERE IsResolved = 0
                    GROUP BY AlertType, Severity
                """)
                
                active_alerts = cursor.fetchall()
        
        # Format rapport
        report = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'environment': ENVIRONMENT,
            'webhook_stats': [dict(zip([col[0] for col in cursor.description], row)) for row in webhook_stats],
            'system_stats': [dict(zip([col[0] for col in cursor.description], row)) for row in system_stats],
            'active_alerts': [dict(zip([col[0] for col in cursor.description], row)) for row in active_alerts]
        }
        
        return json.dumps(report, indent=2)
        
    except Exception as e:
        return f"Report generation failed: {str(e)}"

def send_report_if_issues(**context):
    """Verstuur email alleen bij problemen."""
    report_data = context['task_instance'].xcom_pull(task_ids='generate_report')
    
    import json
    report = json.loads(report_data)
    
    # Check voor problemen
    has_issues = False
    issues = []
    
    # Check active alerts
    if report['active_alerts']:
        has_issues = True
        alert_count = sum(alert['Count'] for alert in report['active_alerts'])
        issues.append(f"{alert_count} active alerts")
    
    # Check webhook reactivations
    total_reactivations = sum(ws.get('Reactivations', 0) for ws in report['webhook_stats'])
    if total_reactivations > 0:
        has_issues = True
        issues.append(f"{total_reactivations} webhook reactivations")
    
    # Check system critical events
    total_critical = sum(ss.get('CriticalCount', 0) for ss in report['system_stats'])
    if total_critical > 0:
        has_issues = True
        issues.append(f"{total_critical} critical system events")
    
    if has_issues:
        return {
            'send_email': True,
            'subject': f'AARDG Health Report - Issues Detected ({ENVIRONMENT})',
            'content': f"Issues found:\n- {chr(10).join(issues)}\n\nFull report:\n{report_data}"
        }
    else:
        return {
            'send_email': False,
            'content': f"All systems healthy ({ENVIRONMENT})"
        }

# Daily tasks
generate_report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_daily_report,
    dag=daily_dag
)

check_issues_task = PythonOperator(
    task_id='check_issues',
    python_callable=send_report_if_issues,
    provide_context=True,
    dag=daily_dag
)

# Conditionele email
send_alert_email = EmailOperator(
    task_id='send_alert_email',
    to=['max@aardg.nl'],  # Pas aan
    subject='AARDG Health Report - Issues Detected',
    html_content="{{ task_instance.xcom_pull(task_ids='check_issues')['content'] }}",
    trigger_rule=TriggerRule.NONE_FAILED,
    dag=daily_dag
)

# Dependencies
generate_report_task >> check_issues_task >> send_alert_email
