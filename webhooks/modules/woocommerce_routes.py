from datetime import datetime, timedelta
import logging
from google.cloud import bigquery
from modules.log import log

def move_next_payment_date(data, wcapi, greit_connection_string, klant, script_id):
    log(greit_connection_string, klant, "WooCommerce | WooCommerce", f"Verkoopmethode bepalen", "Volgende betaaldatum verplaatsen", script_id, tabel=None)
    payment_method = data.get('payment_method_title')
    if payment_method in ['iDEAL', 'Bancontact']:
        next_payment_date_str = data.get('next_payment_date_gmt')
        log(greit_connection_string, klant, "WooCommerce | WooCommerce", f"Betaaldatum verplaatsen naar {next_payment_date_str}", "Volgende betaaldatum verplaatsen", script_id, tabel=None)
        if next_payment_date_str:
            # Converteer de datum string naar een datetime object
            next_payment_date = datetime.strptime(next_payment_date_str, '%Y-%m-%dT%H:%M:%S')
            new_next_payment_date = next_payment_date - timedelta(days=7)

            # Update WooCommerce subscription
            update_data = {
                "next_payment_date": f"{new_next_payment_date}"
            }

            # Voer de PUT request uit naar WooCommerce API
            try:
                wcapi.put(f"subscriptions/{data['id']}", update_data)
            except Exception as e:
                log(greit_connection_string, klant, "WooCommerce | WooCommerce", f"FOUTMELDING: {e}", "Volgende betaaldatum verplaatsen", script_id, tabel=None)

def add_abo_to_bigquery(customer_data, credentials_path, greit_connection_string, klant, script_id):
    log(greit_connection_string, klant, "WooCommerce | BigQuery", "Initialiseren van BigQuery", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)

    # Initialiseer de BigQuery client
    client = bigquery.Client()

    # Verwijs naar de dataset en tabel waarin je de gegevens wilt invoegen
    dataset_id = "woocommerce_data"
    table_id = "subscriptions"

    # Bouw de volledige tabelreferentie
    table_ref = client.dataset(dataset_id).table(table_id)

    # Verkrijg de tabel om ervoor te zorgen dat deze bestaat en dat je schema correct is
    try:
        table = client.get_table(table_ref)
        print(f"Table {table_id} in dataset {dataset_id} accessed successfully.")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"Tabel {table_id} in dataset {dataset_id} gevonden.", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)
    except Exception as e:
        print(f"Error accessing table: {e}")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: {e}", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)

    tabel_input = {
        "subscription_id": customer_data["id"],
        "parent_id": customer_data["parent_id"],
        "status": customer_data["status"],
        "number": customer_data["number"],
        "currency": customer_data["currency"],
        "date_created": customer_data["date_created"],
        "date_modified": customer_data["date_modified"],
        "customer_id": customer_data["customer_id"],
        "discount_total": customer_data["discount_total"],
        "total": customer_data["total"],
        "billing_company": customer_data["billing"]["company"],
        "billing_city": customer_data["billing"]["city"],
        "billing_state": customer_data["billing"]["state"],
        "billing_postcode": customer_data["billing"]["postcode"],
        "billing_country": customer_data["billing"]["country"],
        "billing_email": customer_data["billing"]["email"],
        "billing_first_name": customer_data["billing"]["first_name"],
        "billing_last_name": customer_data["billing"]["last_name"],
        "billing_address_1": customer_data["billing"]["address_1"],
        "billing_address_2": customer_data["billing"]["address_2"],
        "shipping_company": customer_data["shipping"]["company"],
        "shipping_city": customer_data["shipping"]["city"],
        "shipping_state": customer_data["shipping"]["state"],
        "shipping_postcode": customer_data["shipping"]["postcode"],
        "shipping_country": customer_data["shipping"]["country"],
        "shipping_first_name": customer_data["shipping"]["first_name"],
        "shipping_last_name": customer_data["shipping"]["last_name"],
        "shipping_address_1": customer_data["shipping"]["address_1"],
        "shipping_address_2": customer_data["shipping"]["address_2"],
        "payment_method": customer_data["payment_method"],
        "payment_method_title": customer_data["payment_method_title"],
        "transaction_id": None,
        "customer_ip_address": customer_data["customer_ip_address"],
        "customer_user_agent": customer_data["customer_user_agent"],
        "created_via": customer_data["created_via"],
        "customer_note": customer_data["customer_note"],
        "date_completed": customer_data["date_completed"],
        "date_paid": customer_data["date_paid"],
        "cart_hash": "",
        "lineitems_quantity": [item["quantity"] for item in customer_data["line_items"]],
        "lineitems_subtotal": [item["subtotal"] for item in customer_data["line_items"]],
        "lineitems_total": [item["total"] for item in customer_data["line_items"]],
        "lineitems_price": [item["price"] for item in customer_data["line_items"]],
        "lineitems_product_id": [item["product_id"] for item in customer_data["line_items"]],
        "billing_period": customer_data["billing_period"],
        "billing_interval": customer_data["billing_interval"],
        "start_date": customer_data["start_date_gmt"],
        "next_payment_date": customer_data["next_payment_date_gmt"],
        "end_date": customer_data["end_date_gmt"],
        "shipping_total": customer_data["shipping_total"]
    }

    rows_to_insert = [tabel_input]

    try:
        errors = client.insert_rows_json(table, rows_to_insert)
        if errors:
            print(f"Errors occurred while inserting: {errors}")
            log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: {errors}", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)
        else:
            print("Insert successful")
            log(greit_connection_string, klant, "WooCommerce | BigQuery", "Geen foutmeldingen", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)
    except Exception as e:
        print(f"An error occurred during the insert operation: {e}")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: {e}", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)