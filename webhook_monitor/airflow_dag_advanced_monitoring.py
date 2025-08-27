"""
Geavanceerde Airflow DAG voor Multi-Interval Monitoring
- Webhook monitoring: elke 5 minuten
- System monitoring: elke 15 minuten  
- Health reports: dagelijks om 09:00
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.email_operator import EmailOperator
from airflow.operators.python import ShortCircuitOperator
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
import json
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
    'email': ['max@aardg.nl'],
}

# =================================
# DAG 3: Daily Health Report (09:00)
# =================================
daily_dag = DAG(
    'daily_health_report',
    default_args=default_args,
    description='Dagelijkse health report om 09:00',
    schedule_interval='0 9 * * *',
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['monitoring', 'daily', 'report']
)


def generate_daily_report():
    """Genereer dagelijks rapport uit Azure SQL."""
    os.chdir(WEBHOOK_MONITOR_PATH)
    from m_modules.azure_sql_monitor import get_config_from_env, connect_azuresql

    try:
        cfg = get_config_from_env()
        with connect_azuresql(cfg) as conn, conn.cursor() as cursor:
            # Query webhook stats
            cursor.execute("""
                SELECT WebhookName, COUNT(*) AS CheckCount,
                       SUM(CASE WHEN StatusChanged=1 THEN 1 ELSE 0 END) AS StatusChanges,
                       SUM(CASE WHEN ActionTaken='reactivated' THEN 1 ELSE 0 END) AS Reactivations,
                       SUM(CASE WHEN CurrentStatus='error' THEN 1 ELSE 0 END) AS Errors
                FROM WebhookMonitoring
                WHERE CheckedAt >= DATEADD(hour, -24, GETDATE())
                GROUP BY WebhookName
            """)
            cols = [c[0] for c in cursor.description]
            webhook_stats = [dict(zip(cols, r)) for r in cursor.fetchall()]

            # Query system stats
            cursor.execute("""
                SELECT MonitorType,
                       AVG(CPUUsagePercent) AS AvgCPU,
                       AVG(MemoryUsagePercent) AS AvgMemory,
                       AVG(AppResponseTime) AS AvgResponseTime,
                       SUM(CASE WHEN Status='critical' THEN 1 ELSE 0 END) AS CriticalCount
                FROM SystemMonitoring
                WHERE MonitoredAt >= DATEADD(hour, -24, GETDATE())
                GROUP BY MonitorType
            """)
            cols = [c[0] for c in cursor.description]
            system_stats = [dict(zip(cols, r)) for r in cursor.fetchall()]

            # Query active alerts
            cursor.execute("""
                SELECT AlertType, Severity, COUNT(*) AS Count
                FROM MonitoringAlerts
                WHERE IsResolved = 0
                GROUP BY AlertType, Severity
            """)
            cols = [c[0] for c in cursor.description]
            active_alerts = [dict(zip(cols, r)) for r in cursor.fetchall()]

        report = {
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "environment": ENVIRONMENT,
            "webhook_stats": webhook_stats,
            "system_stats": system_stats,
            "active_alerts": active_alerts,
        }
        return json.dumps(report, indent=2)
    except Exception as e:
        # Altijd JSON teruggeven, ook bij errors
        return json.dumps({
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "environment": ENVIRONMENT,
            "error": f"Report generation failed: {str(e)}",
            "webhook_stats": [],
            "system_stats": [],
            "active_alerts": []
        }, indent=2)


def decide_and_prepare_email(ti, **context):
    """Beslis of er een e-mail gestuurd moet worden."""
    report_data = ti.xcom_pull(task_ids='generate_report')
    report = json.loads(report_data)

    issues = []

    # Active alerts
    if report.get('active_alerts'):
        issues.append(f"{sum(a.get('Count', 0) for a in report['active_alerts'])} active alerts")

    # Webhook reactivations
    total_reactivations = sum(ws.get("Reactivations", 0) for ws in report.get("webhook_stats", []))
    if total_reactivations > 0:
        issues.append(f"{total_reactivations} webhook reactivations")

    # Critical system events
    total_critical = sum(ss.get("CriticalCount", 0) for ss in report.get("system_stats", []))
    if total_critical > 0:
        issues.append(f"{total_critical} critical system events")

    if issues:
        # Zet data klaar voor EmailOperator
        ti.xcom_push(key="email_subject", value=f"AARDG Health Report - Issues Detected ({ENVIRONMENT})")
        ti.xcom_push(key="email_content",
                     value="Issues found:\n- " + "\n- ".join(issues) +
                           f"\n\nFull report:\n{json.dumps(report, indent=2)}")
        return True  # Doorgaan -> EmailOperator wordt uitgevoerd
    else:
        # Geen problemen, e-mail wordt geskipt
        return False


# Taken
generate_report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_daily_report,
    dag=daily_dag
)

check_issues_task = ShortCircuitOperator(
    task_id='check_issues',
    python_callable=decide_and_prepare_email,
    provide_context=True,
    dag=daily_dag
)

send_alert_email = EmailOperator(
    task_id='send_alert_email',
    to=['max@aardg.nl'],
    subject="{{ ti.xcom_pull(task_ids='check_issues', key='email_subject') }}",
    html_content="{{ ti.xcom_pull(task_ids='check_issues', key='email_content') }}",
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    dag=daily_dag
)

# Dependencies
generate_report_task >> check_issues_task >> send_alert_email
