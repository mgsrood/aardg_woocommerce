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

def update_or_insert_to_bigquery(table_id, dataset_id, record_id, get_data_func, wcapi, id_field):
    logging.info(f"Verwerken van {table_id} in BigQuery")
    client = bigquery.Client()
    table_ref = client.dataset(dataset_id).table(table_id)
    
    try:
        table = client.get_table(table_ref)
        logging.info(f"Table {table_id} in dataset {dataset_id} gevonden.")
    except Exception as e:
        logging.error(f"Fout bij het verkrijgen van de tabel: {e}")
        return

    check_query = f"SELECT COUNT(*) FROM `{dataset_id}.{table_id}` WHERE {id_field} = {record_id}"
    check_job = client.query(check_query)
    exists = next(check_job.result()).f0_ > 0
    
    data = get_data_func(record_id, wcapi)
    tabel_input = {
        id_field: data["id"],
        "status": data["status"],
        "currency": data["currency"],
        "total": data["total"],
        "billing_first_name": data["billing"]["first_name"],
        "billing_last_name": data["billing"]["last_name"],
        "billing_email": data["billing"]["email"],
        "payment_method": data["payment_method"],
        "payment_method_title": data["payment_method_title"],
        "customer_ip_address": data["customer_ip_address"],
        "customer_user_agent": data["customer_user_agent"],
        "created_via": data["created_via"],
        "customer_note": data["customer_note"],
        "date_created": data["date_created"],
        "date_modified": data["date_modified"],
        "date_paid": data["date_paid"],
        "lineitems_quantity": json.dumps([item["quantity"] for item in data["line_items"]]),
        "lineitems_total": json.dumps([item["total"] for item in data["line_items"]]),
        "lineitems_product_id": json.dumps([item["product_id"] for item in data["line_items"]])
    }

    query = f"""
    MERGE `{dataset_id}.{table_id}` T
    USING (SELECT {record_id} AS {id_field}) S
    ON T.{id_field} = S.{id_field}
    WHEN MATCHED THEN
        UPDATE SET status = '{tabel_input["status"]}',
                   currency = '{tabel_input["currency"]}',
                   total = {tabel_input["total"]},
                   billing_first_name = '{tabel_input["billing_first_name"]}',
                   billing_last_name = '{tabel_input["billing_last_name"]}',
                   billing_email = '{tabel_input["billing_email"]}',
                   payment_method = '{tabel_input["payment_method"]}',
                   payment_method_title = '{tabel_input["payment_method_title"]}',
                   customer_ip_address = '{tabel_input["customer_ip_address"]}',
                   customer_user_agent = '{tabel_input["customer_user_agent"]}',
                   created_via = '{tabel_input["created_via"]}',
                   customer_note = '{tabel_input["customer_note"]}',
                   date_created = '{tabel_input["date_created"]}',
                   date_modified = '{tabel_input["date_modified"]}',
                   date_paid = '{tabel_input["date_paid"]}',
                   lineitems_quantity = '{tabel_input["lineitems_quantity"]}',
                   lineitems_total = '{tabel_input["lineitems_total"]}',
                   lineitems_product_id = '{tabel_input["lineitems_product_id"]}'
    WHEN NOT MATCHED THEN
        INSERT ({', '.join(tabel_input.keys())})
        VALUES ({', '.join(f'"{v}"' if isinstance(v, str) else str(v) for v in tabel_input.values())})
    """

    try:
        query_job = client.query(query)
        logging.info(f"Uitgevoerde BigQuery-query: {query}")
        query_job.result()
    except Exception as e:
        logging.error(f"Fout bij het uitvoeren van de query: {e}")
    
    action = "Update uitgevoerd" if exists else "Insert uitgevoerd"
    logging.info(f"{action} voor {id_field} {record_id}")

def update_or_insert_sub_to_bigquery(subscription_id, wcapi):
    update_or_insert_to_bigquery(
        table_id="subscriptions", 
        dataset_id="woocommerce", 
        record_id=subscription_id, 
        get_data_func=get_woocommerce_subscription_data, 
        wcapi=wcapi, 
        id_field="subscription_id"
    )

def update_or_insert_order_to_bigquery(order_id, wcapi):
    update_or_insert_to_bigquery(
        table_id="orders", 
        dataset_id="woocommerce_data", 
        record_id=order_id, 
        get_data_func=get_woocommerce_order_data, 
        wcapi=wcapi, 
        id_field="order_id"
    )
