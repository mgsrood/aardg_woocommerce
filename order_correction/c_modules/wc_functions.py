from c_modules.woocommerce_utils import get_woocommerce_order_data
from google.cloud import bigquery
import logging

def update_or_insert_order_to_bigquery(order_id, wcapi):

    logging.info("Order verwerken in BigQuery")

    # Initialiseer de BigQuery client
    client = bigquery.Client()

    # Verwijs naar de dataset en tabel waarin je de gegevens wilt invoegen
    dataset_id = "woocommerce"
    table_id = "orders"

    # Bouw de volledige tabelreferentie
    table_ref = client.dataset(dataset_id).table(table_id)

    # Verkrijg de tabel om ervoor te zorgen dat deze bestaat en dat je schema correct is
    try:
        table = client.get_table(table_ref)
        logging.info("Table " + table_id + " in dataset " + dataset_id + " gevonden.")
    except Exception as e:
        logging.error("Fout bij het verkrijgen van de tabel: " + str(e))
        return

    # Controleer of de order al bestaat
    check_query = f"SELECT COUNT(*) FROM `{dataset_id}.{table_id}` WHERE order_id = {order_id}"
    check_job = client.query(check_query)
    exists = next(check_job.result()).f0_ > 0
    
    # Verkrijg de order data van WooCommerce
    customer_data = get_woocommerce_order_data(order_id, wcapi)

    def escape_string(s):
        if s is None:
            return None
        return str(s).replace("'", "\\'")

    tabel_input = {
        "order_id": customer_data["id"],
        "status": escape_string(customer_data["status"]),
        "currency": escape_string(customer_data["currency"]),
        "total": customer_data["total"],
        "billing_company": escape_string(customer_data["billing"]["company"]),
        "billing_city": escape_string(customer_data["billing"]["city"]),
        "billing_state": escape_string(customer_data["billing"]["state"]),
        "billing_postcode": escape_string(customer_data["billing"]["postcode"]),
        "billing_country": escape_string(customer_data["billing"]["country"]),
        "billing_email": escape_string(customer_data["billing"]["email"]),
        "billing_first_name": escape_string(customer_data["billing"]["first_name"]),
        "billing_last_name": escape_string(customer_data["billing"]["last_name"]),
        "billing_address_1": escape_string(customer_data["billing"]["address_1"]),
        "billing_address_2": escape_string(customer_data["billing"]["address_2"]),
        "shipping_company": escape_string(customer_data["shipping"]["company"]),
        "shipping_city": escape_string(customer_data["shipping"]["city"]),
        "shipping_state": escape_string(customer_data["shipping"]["state"]),
        "shipping_postcode": escape_string(customer_data["shipping"]["postcode"]),
        "shipping_country": escape_string(customer_data["shipping"]["country"]),
        "shipping_first_name": escape_string(customer_data["shipping"]["first_name"]),
        "shipping_last_name": escape_string(customer_data["shipping"]["last_name"]),
        "shipping_address_1": escape_string(customer_data["shipping"]["address_1"]),
        "shipping_address_2": escape_string(customer_data["shipping"]["address_2"]) if "shipping" in customer_data and "address_2" in customer_data["shipping"] else None,
        "order_number": customer_data["number"],
        "date_created": escape_string(customer_data["date_created"]),
        "date_modified": escape_string(customer_data["date_modified"]),
        "discount_total": customer_data["discount_total"],
        "customer_id": customer_data["customer_id"],
        "order_key": escape_string(customer_data["order_key"]),                
        "payment_method": escape_string(customer_data["payment_method"]),
        "payment_method_title": escape_string(customer_data["payment_method_title"]),
        "transaction_id": None,
        "customer_ip_address": escape_string(customer_data["customer_ip_address"]),
        "customer_user_agent": escape_string(customer_data["customer_user_agent"]),
        "created_via": escape_string(customer_data["created_via"]),
        "customer_note": escape_string(customer_data["customer_note"]),
        "date_completed": escape_string(customer_data["date_completed"]),
        "date_paid": escape_string(customer_data["date_paid"]),
        "cart_hash": "",
        "lineitems_id": [item["id"] for item in customer_data["line_items"]],
        "lineitems_product_name": [escape_string(item["name"]) for item in customer_data["line_items"]],   
        "lineitems_quantity": [item["quantity"] for item in customer_data["line_items"]],
        "lineitems_subtotal": [item["subtotal"] for item in customer_data["line_items"]],
        "lineitems_total": [item["total"] for item in customer_data["line_items"]],
        "lineitems_product_id": [item["product_id"] for item in customer_data["line_items"]],
        "discount_code": [escape_string(item["code"]) for item in customer_data["coupon_lines"]],
        "discount_per_code": [item["discount"] for item in customer_data["coupon_lines"]],
        "payment_url": escape_string(customer_data["payment_url"]),
        "currency_symbol": escape_string(customer_data["currency_symbol"]),
        "shipping_total": customer_data["shipping_total"]
    }

    # Format arrays voor BigQuery
    def format_array(arr, type_cast=None):
        if not arr:
            return "[]"
        if type_cast:
            return f"[{', '.join(type_cast(str(x)) for x in arr)}]"
        return f"[{', '.join(str(x) for x in arr)}]"

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
            lineitems_id = {format_array(tabel_input["lineitems_id"])},
            lineitems_product_name = {format_array(tabel_input["lineitems_product_name"], lambda x: f"'{x}'")},
            lineitems_quantity = {format_array(tabel_input["lineitems_quantity"])},
            lineitems_subtotal = {format_array(tabel_input["lineitems_subtotal"])},
            lineitems_total = {format_array(tabel_input["lineitems_total"])},
            lineitems_product_id = {format_array(tabel_input["lineitems_product_id"])},
            discount_code = {format_array(tabel_input["discount_code"], lambda x: f"'{x}'")},
            discount_per_code = {format_array(tabel_input["discount_per_code"])},
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
            '{tabel_input["cart_hash"]}', {format_array(tabel_input["lineitems_id"])},
            {format_array(tabel_input["lineitems_product_name"], lambda x: f"'{x}'")},
            {format_array(tabel_input["lineitems_quantity"])},
            {format_array(tabel_input["lineitems_subtotal"])},
            {format_array(tabel_input["lineitems_total"])},
            {format_array(tabel_input["lineitems_product_id"])},
            {format_array(tabel_input["discount_code"], lambda x: f"'{x}'")},
            {format_array(tabel_input["discount_per_code"])},
            '{tabel_input["payment_url"]}', '{tabel_input["currency_symbol"]}', {tabel_input["shipping_total"]}
        )
    """

    # Voer de MERGE-query uit
    try:
        query_job = client.query(query)
        logging.info("Query uitgevoerd")
    except Exception as e:
        logging.error("Fout bij het uitvoeren van de query: " + str(e))

    query_job.result()  # Wacht tot de query is voltooid
    
    # Bepaal actie op basis van controle
    action = "Update uitgevoerd voor order ID" if exists else "Insert uitgevoerd voor order ID"
    result_message = f"{action} {order_id}"
    logging.info(result_message)