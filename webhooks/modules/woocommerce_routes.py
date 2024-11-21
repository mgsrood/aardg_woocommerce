from datetime import datetime, timedelta
import logging
from google.cloud import bigquery
from modules.log import log
from modules.woocommerce_utils import wait_for_buffer_to_clear

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
    except Exception as e:
        print(f"An error occurred during the insert operation: {e}")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: {e}", "Abonnement toevoegen aan BigQuery", script_id, tabel=None)

def update_abo_in_bigquery(customer_data, credentials_path, greit_connection_string, klant, script_id):
    log(greit_connection_string, klant, "WooCommerce | BigQuery", "Initialiseren van BigQuery", "Abonnement updaten in BigQuery", script_id, tabel=None)

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
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"Tabel {table_id} in dataset {dataset_id} gevonden.", "Abonnement updaten in BigQuery", script_id, tabel=None)
    except Exception as e:
        print(f"Error accessing table: {e}")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: {e}", "Abonnement updaten in BigQuery", script_id, tabel=None)
        return

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

    # Bouw de update statement
    try:
        # Controleer of de subscription_id al bestaat in de tabel
        subscription_id = tabel_input["subscription_id"]
        check_query = f"""
        SELECT COUNT(*) AS cnt
        FROM {dataset_id}.{table_id}
        WHERE subscription_id = {subscription_id}
        """

        check_job = client.query(check_query)
        results = check_job.result()

        # Extract het aantal rijen met de gegeven subscription_id
        row_count = 0
        for row in results:
            row_count = row.cnt

        # Als de subscription_id niet bestaat, geef een foutmelding
        if row_count == 0:
            log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: Subscription_id {subscription_id} niet gevonden in BigQuery", "Abonnement updaten in BigQuery", script_id, tabel=None)

        # Als de subscription_id bestaat, voer dan de MERGE (UPDATE) uit
        query = f"""
        MERGE {dataset_id}.{table_id} T
        USING (
            SELECT {subscription_id} AS subscription_id
        ) S
        ON T.subscription_id = S.subscription_id
        WHEN MATCHED THEN
            UPDATE SET
            parent_id = {tabel_input["parent_id"]},
            status = '{tabel_input["status"]}',
            number = {tabel_input["number"]},
            currency = '{tabel_input["currency"]}',
            date_created = '{tabel_input["date_created"]}',
            date_modified = '{tabel_input["date_modified"]}',
            customer_id = {tabel_input["customer_id"]},
            discount_total = {tabel_input["discount_total"]},
            total = {tabel_input["total"]},
            billing_company = '{tabel_input["billing_company"]}',
            billing_city = '{tabel_input["billing_city"]}',
            billing_state = '{tabel_input["billing_state"]}',
            billing_postcode = '{tabel_input["billing_postcode"]}',
            billing_country = '{tabel_input["billing_country"]}',
            billing_email = '{tabel_input["billing_email"]}',
            billing_first_name = '{tabel_input["billing_first_name"]}',
            billing_last_name = '{tabel_input["billing_last_name"]}',
            billing_address_1 = '{tabel_input["billing_address_1"]}',
            billing_address_2 = '{tabel_input["billing_address_2"]}',
            shipping_company = '{tabel_input["shipping_company"]}',
            shipping_city = '{tabel_input["shipping_city"]}',
            shipping_state = '{tabel_input["shipping_state"]}',
            shipping_postcode = '{tabel_input["shipping_postcode"]}',
            shipping_country = '{tabel_input["shipping_country"]}',
            shipping_first_name = '{tabel_input["shipping_first_name"]}',
            shipping_last_name = '{tabel_input["shipping_last_name"]}',
            shipping_address_1 = '{tabel_input["shipping_address_1"]}',
            shipping_address_2 = '{tabel_input["shipping_address_2"]}',
            payment_method = '{tabel_input["payment_method"]}',
            payment_method_title = '{tabel_input["payment_method_title"]}',
            transaction_id = {tabel_input["transaction_id"] if tabel_input["transaction_id"] is not None else 'NULL'},
            customer_ip_address = '{tabel_input["customer_ip_address"]}',
            customer_user_agent = '{tabel_input["customer_user_agent"]}',
            created_via = '{tabel_input["created_via"]}',
            customer_note = '{tabel_input["customer_note"]}',
            date_completed = '{tabel_input["date_completed"]}',
            date_paid = '{tabel_input["date_paid"]}',
            cart_hash = '{tabel_input["cart_hash"]}',
            lineitems_quantity = {tabel_input["lineitems_quantity"]},
            lineitems_subtotal = [{', '.join(map(str, [float(x) for x in tabel_input["lineitems_subtotal"]]))}],
            lineitems_total = [{', '.join(map(str, [float(x) for x in tabel_input["lineitems_total"]]))}],
            lineitems_price = [{', '.join(map(str, [float(x) for x in tabel_input["lineitems_price"]]))}],
            lineitems_product_id = [{', '.join(map(str, [int(x) for x in tabel_input["lineitems_product_id"]]))}],
            billing_period = '{tabel_input["billing_period"]}',
            billing_interval = {tabel_input["billing_interval"]},
            start_date = '{tabel_input["start_date"]}',
            next_payment_date = '{tabel_input["next_payment_date"]}',
            end_date = '{tabel_input["end_date"]}',
            shipping_total = {tabel_input["shipping_total"]}
        """

        query_job = client.query(query)
        query_job.result()  # Wacht tot de query is voltooid
        print("Update succesvol uitgevoerd.")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", "Update succesvol uitgevoerd.", "Abonnement updaten in BigQuery", script_id, tabel=None)
    except Exception as e:
        print(f"An error occurred during the update operation: {e}")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: {e}", "Abonnement updaten in BigQuery", script_id, tabel=None)