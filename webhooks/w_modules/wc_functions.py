from w_modules.woocommerce_utils import get_woocommerce_order_data, get_woocommerce_subscription_data
from datetime import datetime, timedelta
from google.cloud import bigquery
import logging
import json

def move_next_payment_date(data, wcapi):
    payment_method = data.get('payment_method_title')
    logging.info(f"Verkoopmethode: {payment_method}")
    
    if payment_method in ['iDEAL', 'Bancontact']:
        next_payment_date_str = data.get('next_payment_date_gmt')
        logging.info(f"Huidige betaaldatum: {next_payment_date_str}")
        
        if next_payment_date_str:
            next_payment_date = datetime.strptime(next_payment_date_str, '%Y-%m-%dT%H:%M:%S')
            new_next_payment_date = next_payment_date - timedelta(days=7)

            update_data = {"next_payment_date": new_next_payment_date.isoformat()}
            try:
                wcapi.put(f"subscriptions/{data['id']}", update_data)
                logging.info("Betaaldatum verplaatst met 7 dagen")
            except Exception as e:
                logging.error(f"Fout bij het verplaatsen van de betaaldatum: {e}")

def update_or_insert_to_bigquery(table_id, dataset_id, primary_key, data):
    """
    Algemene functie voor het verwerken van orders en abonnementen naar BigQuery.
    """
    logging.info(f"Verwerken van {table_id} in BigQuery")
    client = bigquery.Client()
    
    table_ref = client.dataset(dataset_id).table(table_id)
    
    # Controleer of de tabel bestaat
    try:
        table = client.get_table(table_ref)
        logging.info(f"Table {table_id} in dataset {dataset_id} gevonden.")
    except Exception as e:
        logging.error(f"Fout bij het verkrijgen van de tabel: {e}")
        return
    
    # JSON-velden correct serialiseren
    def format_json(value):
        return json.dumps(value) if isinstance(value, list) else value
    
    # Zet lijstvelden om in geldige BigQuery-ARRAY's
    def format_array(value, data_type="STRING"):
        if isinstance(value, list):
            return f"ARRAY<{data_type}>[{', '.join(map(str, value))}]"
        return "NULL"
    
    primary_key_value = data[primary_key]
    
    query = f"""
    MERGE `{dataset_id}.{table_id}` T
    USING (SELECT {primary_key_value} AS {primary_key}) S
    ON T.{primary_key} = S.{primary_key}
    WHEN MATCHED THEN
        UPDATE SET
            status = '{data['status']}',
            currency = '{data['currency']}',
            total = {data['total']},
            billing_first_name = '{data['billing_first_name']}',
            billing_last_name = '{data['billing_last_name']}',
            billing_email = '{data['billing_email']}',
            payment_method = '{data['payment_method']}',
            payment_method_title = '{data['payment_method_title']}',
            customer_ip_address = '{data['customer_ip_address']}',
            customer_user_agent = '{data['customer_user_agent']}',
            created_via = '{data['created_via']}',
            customer_note = '{data['customer_note']}',
            date_created = '{data['date_created']}',
            date_modified = '{data['date_modified']}',
            date_paid = '{data['date_paid']}',
            lineitems_quantity = {format_array(data['lineitems_quantity'], 'INT64')},
            lineitems_total = {format_array(data['lineitems_total'], 'FLOAT64')},
            lineitems_product_id = {format_array(data['lineitems_product_id'], 'INT64')}
    WHEN NOT MATCHED THEN
        INSERT (
            {primary_key}, status, currency, total, billing_first_name, billing_last_name, billing_email,
            payment_method, payment_method_title, customer_ip_address, customer_user_agent, created_via,
            customer_note, date_created, date_modified, date_paid, lineitems_quantity, lineitems_total,
            lineitems_product_id
        )
        VALUES (
            {primary_key_value}, '{data['status']}', '{data['currency']}', {data['total']}, '{data['billing_first_name']}',
            '{data['billing_last_name']}', '{data['billing_email']}', '{data['payment_method']}', '{data['payment_method_title']}',
            '{data['customer_ip_address']}', '{data['customer_user_agent']}', '{data['created_via']}', '{data['customer_note']}',
            '{data['date_created']}', '{data['date_modified']}', '{data['date_paid']}',
            {format_array(data['lineitems_quantity'], 'INT64')}, {format_array(data['lineitems_total'], 'FLOAT64')},
            {format_array(data['lineitems_product_id'], 'INT64')}
        )
    """
    
    try:
        query_job = client.query(query)
        logging.info(f"Uitgevoerde BigQuery-query: {query}")
    except Exception as e:
        logging.error(f"Fout bij het uitvoeren van de query: {e}")
    
    query_job.result()
    logging.info(f"Succesvolle verwerking voor {primary_key} {primary_key_value}")

def update_or_insert_order_to_bigquery(order_id, wcapi):
    """ Verwerk een order in BigQuery """
    data = get_woocommerce_order_data(order_id, wcapi)
    update_or_insert_to_bigquery("orders", "woocommerce_data", "order_id", data)

def update_or_insert_sub_to_bigquery(subscription_id, wcapi):
    """ Verwerk een abonnement in BigQuery """
    data = get_woocommerce_subscription_data(subscription_id, wcapi)
    update_or_insert_to_bigquery("subscriptions", "woocommerce", "subscription_id", data)

