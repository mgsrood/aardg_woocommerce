from modules.woocommerce_utils import get_woocommerce_order_data, get_woocommerce_subscription_data
from datetime import datetime, timedelta
from google.cloud import bigquery
from modules.log import log

def move_next_payment_date(data, wcapi, greit_connection_string, klant, script_id, route_naam):
    
    # Verkoopmethode bepalen
    payment_method = data.get('payment_method_title')
    log(greit_connection_string, klant, "WooCommerce", f"Verkoopmethode bepalen", route_naam, script_id, tabel=None)
    
    # Als betaalmethode iDEAL of Bancontact is, verplaats de volgende betaaldatum met 7 dagen
    if payment_method in ['iDEAL', 'Bancontact']:
        next_payment_date_str = data.get('next_payment_date_gmt')
        log(greit_connection_string, klant, "WooCommerce", f"Betaaldatum verplaatsen naar {next_payment_date_str}", route_naam, script_id, tabel=None)
        
        # Converteer de datum string naar een datetime object
        if next_payment_date_str:
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
                log(greit_connection_string, klant, "WooCommerce", f"FOUTMELDING: {e}", route_naam, script_id, tabel=None)

def update_or_insert_sub_to_bigquery(greit_connection_string, klant, script_id, route_naam, subscription_id, wcapi):

    # Log de start van de verwerking
    log(greit_connection_string, klant, "WooCommerce | BigQuery", "Initialiseren van BigQuery", "Abonnement verwerken in BigQuery", script_id, tabel=None)

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
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"Tabel {table_id} in dataset {dataset_id} gevonden.", "Abonnement verwerken in BigQuery", script_id, tabel=None)
    except Exception as e:
        print(f"Error accessing table: {e}")
        log(greit_connection_string, klant, "WooCommerce | BigQuery", f"FOUTMELDING: {e}", "Abonnement verwerken in BigQuery", script_id, tabel=None)
        return
    
    # Controleer of de order al bestaat
    check_query = f"SELECT COUNT(*) FROM `{dataset_id}.{table_id}` WHERE subscription_id = {subscription_id}"
    check_job = client.query(check_query)
    exists = next(check_job.result()).f0_ > 0


    customer_data = get_woocommerce_subscription_data(subscription_id, wcapi)
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
        "shipping_address_2": customer_data["shipping"]["address_2"] if "shipping" in customer_data and "address_2" in customer_data["shipping"] else None,
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

    # Bouw de MERGE-query voor invoegen of updaten
    subscription_id = tabel_input["subscription_id"]

    query = f"""
    MERGE `{dataset_id}.{table_id}` T
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
    WHEN NOT MATCHED THEN
        INSERT (
            subscription_id, parent_id, status, number, currency, date_created, date_modified, 
            customer_id, discount_total, total, billing_company, billing_city, billing_state, 
            billing_postcode, billing_country, billing_email, billing_first_name, billing_last_name,
            billing_address_1, billing_address_2, shipping_company, shipping_city, shipping_state, 
            shipping_postcode, shipping_country, shipping_first_name, shipping_last_name, shipping_address_1, 
            shipping_address_2, payment_method, payment_method_title, transaction_id, customer_ip_address,
            customer_user_agent, created_via, customer_note, date_completed, date_paid, cart_hash, 
            lineitems_quantity, lineitems_subtotal, lineitems_total, lineitems_price, lineitems_product_id, 
            billing_period, billing_interval, start_date, next_payment_date, end_date, shipping_total
        )
        VALUES (
            {tabel_input["subscription_id"]}, {tabel_input["parent_id"]}, '{tabel_input["status"]}', {tabel_input["number"]}, 
            '{tabel_input["currency"]}', '{tabel_input["date_created"]}', '{tabel_input["date_modified"]}', 
            {tabel_input["customer_id"]}, {tabel_input["discount_total"]}, {tabel_input["total"]}, 
            '{tabel_input["billing_company"]}', '{tabel_input["billing_city"]}', '{tabel_input["billing_state"]}', 
            '{tabel_input["billing_postcode"]}', '{tabel_input["billing_country"]}', '{tabel_input["billing_email"]}', 
            '{tabel_input["billing_first_name"]}', '{tabel_input["billing_last_name"]}', '{tabel_input["billing_address_1"]}', 
            '{tabel_input["billing_address_2"]}', '{tabel_input["shipping_company"]}', '{tabel_input["shipping_city"]}', 
            '{tabel_input["shipping_state"]}', '{tabel_input["shipping_postcode"]}', '{tabel_input["shipping_country"]}', 
            '{tabel_input["shipping_first_name"]}', '{tabel_input["shipping_last_name"]}', '{tabel_input["shipping_address_1"]}', 
            '{tabel_input["shipping_address_2"]}', '{tabel_input["payment_method"]}', '{tabel_input["payment_method_title"]}', 
            {tabel_input["transaction_id"] if tabel_input["transaction_id"] is not None else 'NULL'}, 
            '{tabel_input["customer_ip_address"]}', '{tabel_input["customer_user_agent"]}', '{tabel_input["created_via"]}', 
            '{tabel_input["customer_note"]}', '{tabel_input["date_completed"]}', '{tabel_input["date_paid"]}', 
            '{tabel_input["cart_hash"]}', [{', '.join(map(str, tabel_input["lineitems_quantity"]))}], 
            [{', '.join(map(str, tabel_input["lineitems_subtotal"]))}], 
            [{', '.join(map(str, tabel_input["lineitems_total"]))}], 
            [{', '.join(map(str, tabel_input["lineitems_price"]))}], 
            [{', '.join(map(str, tabel_input["lineitems_product_id"]))}], 
            '{tabel_input["billing_period"]}', {tabel_input["billing_interval"]}, '{tabel_input["start_date"]}', 
            '{tabel_input["next_payment_date"]}', '{tabel_input["end_date"]}', {tabel_input["shipping_total"]}
        )
    """

    # Voer de MERGE-query uit
    try:
        query_job = client.query(query)
    except Exception as e:
        log(greit_connection_string, klant, "WooCommerce", f"FOUTMELDING: {e}", route_naam, script_id, tabel=None)

    query_job.result()  # Wacht tot de query is voltooid
    
    # Bepaal actie op basis van controle
    action = "Update uitgevoerd voor subscription ID" if exists else "Insert uitgevoerd voor subscription ID"
    result_message = f"{action} {subscription_id}"
    log(greit_connection_string, klant, "WooCommerce", result_message, route_naam, script_id, tabel=None)

def update_or_insert_order_to_bigquery(greit_connection_string, klant, script_id, route_naam, order_id, wcapi):

    # Initialiseer de BigQuery client
    client = bigquery.Client()

    # Verwijs naar de dataset en tabel waarin je de gegevens wilt invoegen
    dataset_id = "woocommerce_data"
    table_id = "orders"

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

    # Controleer of de order al bestaat
    check_query = f"SELECT COUNT(*) FROM `{dataset_id}.{table_id}` WHERE order_id = {order_id}"
    check_job = client.query(check_query)
    exists = next(check_job.result()).f0_ > 0
    
    # Verkrijg de order data van WooCommerce
    customer_data = get_woocommerce_order_data(order_id, wcapi)
    tabel_input = {
        "order_id": customer_data["id"],
        "status": customer_data["status"],
        "currency": customer_data["currency"],
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
        "shipping_address_2": customer_data["shipping"]["address_2"] if "shipping" in customer_data and "address_2" in customer_data["shipping"] else None,
        "order_number": customer_data["number"],
        "date_created": customer_data["date_created"],
        "date_modified": customer_data["date_modified"],
        "discount_total": customer_data["discount_total"],
        "customer_id": customer_data["customer_id"],
        "order_key": customer_data["order_key"],                
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
        "lineitems_id": [item["id"] for item in customer_data["line_items"]],
        "lineitems_product_name": [item["name"] for item in customer_data["line_items"]],   
        "lineitems_quantity": [item["quantity"] for item in customer_data["line_items"]],
        "lineitems_subtotal": [item["subtotal"] for item in customer_data["line_items"]],
        "lineitems_total": [item["total"] for item in customer_data["line_items"]],
        "lineitems_product_id": [item["product_id"] for item in customer_data["line_items"]],
        "discount_code": [item["code"] for item in customer_data["coupon_lines"]],
        "discount_per_code": [item["discount"] for item in customer_data["coupon_lines"]],
        "payment_url": customer_data["payment_url"],
        "currency_symbol": customer_data["currency_symbol"],
        "shipping_total": customer_data["shipping_total"]
    }

    # Bouw de MERGE-query voor invoegen of updaten
    query = f"""
    MERGE `{dataset_id}.{table_id}` T
    USING (
        SELECT {order_id} AS order_id
    ) O
    ON T.order_id = O.order_id
    WHEN MATCHED THEN
        UPDATE SET
            status = '{tabel_input["status"]}',
            currency = '{tabel_input["currency"]}',
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
            order_number = {tabel_input["order_number"]},
            date_created = '{tabel_input["date_created"]}',
            date_modified = '{tabel_input["date_modified"]}',
            discount_total = {tabel_input["discount_total"]},
            customer_id = {tabel_input["customer_id"]},
            order_key = '{tabel_input["order_key"]}',
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
            lineitems_id = [{', '.join(map(str, tabel_input["lineitems_id"]))}],
            lineitems_product_name = [{', '.join(f"'{name}'" for name in tabel_input["lineitems_product_name"])}],
            lineitems_quantity = [{', '.join(map(str, tabel_input["lineitems_quantity"]))}],
            lineitems_subtotal = [{', '.join(map(str, [float(x) for x in tabel_input["lineitems_subtotal"]]))}],
            lineitems_total = [{', '.join(map(str, [float(x) for x in tabel_input["lineitems_total"]]))}],
            lineitems_product_id = [{', '.join(map(str, [int(x) for x in tabel_input["lineitems_product_id"]]))}],
            discount_code = [{', '.join(f"'{code}'" for code in tabel_input["discount_code"])}],
            discount_per_code = [{', '.join(map(str, [float(x) for x in tabel_input["discount_per_code"]]))}],
            payment_url = '{tabel_input["payment_url"]}',
            currency_symbol = '{tabel_input["currency_symbol"]}',
            shipping_total = {tabel_input["shipping_total"]}
    WHEN NOT MATCHED THEN
        INSERT (
            order_id, status, currency, total, billing_company, billing_city,
            billing_state, billing_postcode, billing_country, billing_email,
            billing_first_name, billing_last_name, billing_address_1, billing_address_2,
            shipping_company, shipping_city, shipping_state, shipping_postcode,
            shipping_country, shipping_first_name, shipping_last_name, shipping_address_1,
            shipping_address_2, order_number, date_created, date_modified, discount_total,
            customer_id, order_key, payment_method, payment_method_title, transaction_id,
            customer_ip_address, customer_user_agent, created_via, customer_note,
            date_completed, date_paid, cart_hash, lineitems_id, lineitems_product_name,
            lineitems_quantity, lineitems_subtotal, lineitems_total, lineitems_product_id,
            discount_code, discount_per_code, payment_url, currency_symbol, shipping_total
        )
        VALUES (
            {tabel_input["order_id"]}, '{tabel_input["status"]}', '{tabel_input["currency"]}', {tabel_input["total"]},
            '{tabel_input["billing_company"]}', '{tabel_input["billing_city"]}', '{tabel_input["billing_state"]}',
            '{tabel_input["billing_postcode"]}', '{tabel_input["billing_country"]}', '{tabel_input["billing_email"]}',
            '{tabel_input["billing_first_name"]}', '{tabel_input["billing_last_name"]}', '{tabel_input["billing_address_1"]}',
            '{tabel_input["billing_address_2"]}', '{tabel_input["shipping_company"]}', '{tabel_input["shipping_city"]}',
            '{tabel_input["shipping_state"]}', '{tabel_input["shipping_postcode"]}', '{tabel_input["shipping_country"]}',
            '{tabel_input["shipping_first_name"]}', '{tabel_input["shipping_last_name"]}', '{tabel_input["shipping_address_1"]}',
            '{tabel_input["shipping_address_2"]}', {tabel_input["order_number"]}, '{tabel_input["date_created"]}',
            '{tabel_input["date_modified"]}', {tabel_input["discount_total"]}, {tabel_input["customer_id"]},
            '{tabel_input["order_key"]}', '{tabel_input["payment_method"]}', '{tabel_input["payment_method_title"]}',
            {tabel_input["transaction_id"] if tabel_input["transaction_id"] is not None else 'NULL'},
            '{tabel_input["customer_ip_address"]}', '{tabel_input["customer_user_agent"]}', '{tabel_input["created_via"]}',
            '{tabel_input["customer_note"]}', '{tabel_input["date_completed"]}', '{tabel_input["date_paid"]}',
            '{tabel_input["cart_hash"]}', [{', '.join(map(str, tabel_input["lineitems_id"]))}],
            [{', '.join(f"'{name}'" for name in tabel_input["lineitems_product_name"])}],
            [{', '.join(map(str, tabel_input["lineitems_quantity"]))}],
            [{', '.join(map(str, [float(x) for x in tabel_input["lineitems_subtotal"]]))}],
            [{', '.join(map(str, [float(x) for x in tabel_input["lineitems_total"]]))}],
            [{', '.join(map(str, [int(x) for x in tabel_input["lineitems_product_id"]]))}],
            [{', '.join(f"'{code}'" for code in tabel_input["discount_code"])}],
            [{', '.join(map(str, [float(x) for x in tabel_input["discount_per_code"]]))}],
            '{tabel_input["payment_url"]}', '{tabel_input["currency_symbol"]}', {tabel_input["shipping_total"]}
        )
    """

    # Voer de MERGE-query uit
    try:
        query_job = client.query(query)
    except Exception as e:
        log(greit_connection_string, klant, "WooCommerce", f"FOUTMELDING: {e}", route_naam, script_id, tabel=None)

    query_job.result()  # Wacht tot de query is voltooid
    
    # Bepaal actie op basis van controle
    action = "Update uitgevoerd voor order ID" if exists else "Insert uitgevoerd voor order ID"
    result_message = f"{action} {order_id}"
    log(greit_connection_string, klant, "WooCommerce", result_message, route_naam, script_id, tabel=None)