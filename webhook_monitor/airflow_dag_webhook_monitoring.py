"""
Airflow DAG voor Webhook en System Monitoring
Scheduled webhook monitoring en system health checks via Airflow
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.bash_operator import BashOperator
from airflow.utils.dates import days_ago
import sys
import os

# Voeg het project pad toe aan Python path
webhook_monitor_path = "/path/to/webhook_monitor"  # Pas aan naar jouw pad
sys.path.insert(0, webhook_monitor_path)

# Default arguments voor de DAG
default_args = {
    'owner': 'aardg',
    'depends_on_past': False,
    'start_date': days_ago(1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'email': ['your-email@domain.com'],  # Pas aan naar jouw email
}

# DAG definitie
dag = DAG(
    'webhook_monitoring',
    default_args=default_args,
    description='Webhook en System Monitoring',
    schedule_interval=timedelta(minutes=5),  # Elke 5 minuten
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['monitoring', 'webhooks', 'aardg']
)

def run_webhook_monitoring():
    """
    Voer webhook monitoring uit via Python import.
    """
    try:
        # Change working directory
        os.chdir(webhook_monitor_path)
        
        # Import required modules
        from m_modules.webhook_monitor import check_and_reactivate_webhooks
        from m_modules.env_tool import env_check
        from woocommerce import API
        import logging
        
        # Setup basic logging
        logging.basicConfig(level=logging.INFO)
        
        # Environment check
        env_check()
        
        # WooCommerce API setup
        wcapi = API(
            url=os.getenv('WOOCOMMERCE_URL'),
            consumer_key=os.getenv('WOOCOMMERCE_CONSUMER_KEY'),
            consumer_secret=os.getenv('WOOCOMMERCE_CONSUMER_SECRET'),
            version="wc/v3",
            timeout=30
        )
        
        # Required webhooks
        required_webhooks = [
            "Order Verwerking",
            "Abonnement Verwerking",
            "Facebook Audience",
            "Product Velden",
            "Product Tags",
            "Abonnements Tag",
            "Abonnements Veld Ophogen",
            "Abonnements Veld Verlagen",
            "Besteldatum"
        ]
        
        # Run webhook monitoring
        logging.info("Starting Airflow webhook monitoring task...")
        check_and_reactivate_webhooks(wcapi, required_webhooks)
        logging.info("Webhook monitoring completed successfully")
        
        return "Webhook monitoring completed"
        
    except Exception as e:
        logging.error(f"Webhook monitoring failed: {str(e)}")
        raise

def run_system_monitoring():
    """
    Voer system monitoring uit.
    """
    try:
        # Change working directory
        os.chdir(webhook_monitor_path)
        
        # Import system monitoring
        from m_modules.azure_sql_monitor import monitor_all_systems
        import logging
        
        # Setup basic logging
        logging.basicConfig(level=logging.INFO)
        
        # Run system monitoring
        logging.info("Starting Airflow system monitoring task...")
        results = monitor_all_systems()
        
        # Log results
        for monitor_type, result in results.items():
            if result.get('status') == 'healthy':
                logging.info(f"{monitor_type}: healthy")
            else:
                logging.warning(f"{monitor_type}: {result}")
        
        logging.info("System monitoring completed successfully")
        return f"System monitoring completed: {results}"
        
    except Exception as e:
        logging.error(f"System monitoring failed: {str(e)}")
        raise

def check_environment():
    """
    Controleer of alle benodigde environment variabelen aanwezig zijn.
    """
    required_vars = [
        'WOOCOMMERCE_URL',
        'WOOCOMMERCE_CONSUMER_KEY', 
        'WOOCOMMERCE_CONSUMER_SECRET',
        'AZURE_SQL_SERVER',
        'AZURE_SQL_DATABASE',
        'AZURE_SQL_USERNAME',
        'AZURE_SQL_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
    
    return "Environment check passed"

# Task definitiës
env_check_task = PythonOperator(
    task_id='check_environment',
    python_callable=check_environment,
    dag=dag
)

webhook_monitoring_task = PythonOperator(
    task_id='webhook_monitoring',
    python_callable=run_webhook_monitoring,
    dag=dag
)

# System monitoring draait alleen elke 15 minuten
# We gebruiken een sensor of conditional logic
def should_run_system_monitoring():
    """Bepaal of system monitoring moet draaien (elke 15 min)."""
    from datetime import datetime
    current_minute = datetime.now().minute
    return current_minute % 15 == 0

system_monitoring_task = PythonOperator(
    task_id='system_monitoring',
    python_callable=run_system_monitoring,
    dag=dag
)

# Alternative: gebruik BashOperator om direct het script uit te voeren
bash_webhook_monitoring = BashOperator(
    task_id='bash_webhook_monitoring',
    bash_command=f'cd {webhook_monitor_path} && python main.py',
    dag=dag
)

# Task dependencies
env_check_task >> webhook_monitoring_task
env_check_task >> system_monitoring_task

# Je kunt kiezen tussen Python tasks of Bash task:
# env_check_task >> bash_webhook_monitoring
