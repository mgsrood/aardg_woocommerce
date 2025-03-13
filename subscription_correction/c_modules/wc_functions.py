from c_modules.woocommerce_utils import get_woocommerce_subscription_data
from google.cloud import bigquery
from concurrent.futures import ThreadPoolExecutor
import logging

def process_subscription_batch(subscriptions_batch, wcapi, client, dataset_id, table_id):
    processed_count = 0
    success_count = 0
    update_count = 0
    insert_count = 0
    
    for subscription_id in subscriptions_batch:
        try:
            customer_data = get_woocommerce_subscription_data(subscription_id, wcapi)
            
            def escape_string(s):
                if s is None:
                    return None
                return str(s).replace("'", "\\'")

            # Controleer of de subscription al bestaat
            check_query = f"SELECT COUNT(*) FROM `{dataset_id}.{table_id}` WHERE subscription_id = {subscription_id}"
            check_job = client.query(check_query)
            exists = next(check_job.result()).f0_ > 0

            # Bereid de data voor
            row = {
                "subscription_id": customer_data["id"],
                "parent_id": customer_data["parent_id"],
                "status": escape_string(customer_data["status"]),
                "number": customer_data["number"],
                "currency": escape_string(customer_data["currency"]),
                "date_created": escape_string(customer_data["date_created"]),
                "date_modified": escape_string(customer_data["date_modified"]),
                "customer_id": customer_data["customer_id"],
                "discount_total": float(customer_data["discount_total"]),
                "total": float(customer_data["total"]),
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
                "shipping_address_2": escape_string(customer_data["shipping"].get("address_2")),
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
                "lineitems_quantity": [item.get("quantity", 0) for item in customer_data.get("line_items", [])],
                "lineitems_subtotal": [float(item.get("subtotal", 0.0)) for item in customer_data.get("line_items", [])],
                "lineitems_total": [float(item.get("total", 0.0)) for item in customer_data.get("line_items", [])],
                "lineitems_price": [float(item.get("price", 0.0)) for item in customer_data.get("line_items", [])],
                "lineitems_product_id": [int(item.get("product_id", 0)) for item in customer_data.get("line_items", [])],
                "billing_period": escape_string(customer_data["billing_period"]),
                "billing_interval": customer_data["billing_interval"],
                "start_date": escape_string(customer_data["start_date_gmt"]),
                "next_payment_date": escape_string(customer_data["next_payment_date_gmt"]),
                "end_date": escape_string(customer_data["end_date_gmt"]),
                "shipping_total": float(customer_data["shipping_total"])
            }

            # Bouw de MERGE query
            merge_query = f"""
            MERGE `{dataset_id}.{table_id}` T
            USING (SELECT {subscription_id} as subscription_id) S
            ON T.subscription_id = S.subscription_id
            WHEN MATCHED THEN
                UPDATE SET
                    parent_id = {row["parent_id"]},
                    status = '{row["status"]}',
                    number = {row["number"]},
                    currency = '{row["currency"]}',
                    date_created = '{row["date_created"]}',
                    date_modified = '{row["date_modified"]}',
                    customer_id = {row["customer_id"]},
                    discount_total = {row["discount_total"]},
                    total = {row["total"]},
                    billing_company = '{row["billing_company"]}',
                    billing_city = '{row["billing_city"]}',
                    billing_state = '{row["billing_state"]}',
                    billing_postcode = '{row["billing_postcode"]}',
                    billing_country = '{row["billing_country"]}',
                    billing_email = '{row["billing_email"]}',
                    billing_first_name = '{row["billing_first_name"]}',
                    billing_last_name = '{row["billing_last_name"]}',
                    billing_address_1 = '{row["billing_address_1"]}',
                    billing_address_2 = '{row["billing_address_2"]}',
                    shipping_company = '{row["shipping_company"]}',
                    shipping_city = '{row["shipping_city"]}',
                    shipping_state = '{row["shipping_state"]}',
                    shipping_postcode = '{row["shipping_postcode"]}',
                    shipping_country = '{row["shipping_country"]}',
                    shipping_first_name = '{row["shipping_first_name"]}',
                    shipping_last_name = '{row["shipping_last_name"]}',
                    shipping_address_1 = '{row["shipping_address_1"]}',
                    shipping_address_2 = '{row["shipping_address_2"]}',
                    payment_method = '{row["payment_method"]}',
                    payment_method_title = '{row["payment_method_title"]}',
                    transaction_id = NULL,
                    customer_ip_address = '{row["customer_ip_address"]}',
                    customer_user_agent = '{row["customer_user_agent"]}',
                    created_via = '{row["created_via"]}',
                    customer_note = '{row["customer_note"]}',
                    date_completed = '{row["date_completed"]}',
                    date_paid = '{row["date_paid"]}',
                    cart_hash = '{row["cart_hash"]}',
                    lineitems_quantity = {row["lineitems_quantity"]},
                    lineitems_subtotal = {row["lineitems_subtotal"]},
                    lineitems_total = {row["lineitems_total"]},
                    lineitems_price = {row["lineitems_price"]},
                    lineitems_product_id = {row["lineitems_product_id"]},
                    billing_period = '{row["billing_period"]}',
                    billing_interval = {row["billing_interval"]},
                    start_date = '{row["start_date"]}',
                    next_payment_date = '{row["next_payment_date"]}',
                    end_date = '{row["end_date"]}',
                    shipping_total = {row["shipping_total"]}
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
                    {subscription_id}, {row["parent_id"]}, '{row["status"]}', {row["number"]},
                    '{row["currency"]}', '{row["date_created"]}', '{row["date_modified"]}',
                    {row["customer_id"]}, {row["discount_total"]}, {row["total"]},
                    '{row["billing_company"]}', '{row["billing_city"]}', '{row["billing_state"]}',
                    '{row["billing_postcode"]}', '{row["billing_country"]}', '{row["billing_email"]}',
                    '{row["billing_first_name"]}', '{row["billing_last_name"]}', '{row["billing_address_1"]}',
                    '{row["billing_address_2"]}', '{row["shipping_company"]}', '{row["shipping_city"]}',
                    '{row["shipping_state"]}', '{row["shipping_postcode"]}', '{row["shipping_country"]}',
                    '{row["shipping_first_name"]}', '{row["shipping_last_name"]}', '{row["shipping_address_1"]}',
                    '{row["shipping_address_2"]}', '{row["payment_method"]}', '{row["payment_method_title"]}',
                    NULL, '{row["customer_ip_address"]}', '{row["customer_user_agent"]}',
                    '{row["created_via"]}', '{row["customer_note"]}', '{row["date_completed"]}',
                    '{row["date_paid"]}', '{row["cart_hash"]}', {row["lineitems_quantity"]},
                    {row["lineitems_subtotal"]}, {row["lineitems_total"]}, {row["lineitems_price"]},
                    {row["lineitems_product_id"]}, '{row["billing_period"]}', {row["billing_interval"]},
                    '{row["start_date"]}', '{row["next_payment_date"]}', '{row["end_date"]}',
                    {row["shipping_total"]}
                )
            """

            try:
                query_job = client.query(merge_query)
                query_job.result()  # Wacht tot de query klaar is
                action = "Update" if exists else "Insert"
                if exists:
                    update_count += 1
                else:
                    insert_count += 1
                success_count += 1
                logging.info(f"{action} succesvol uitgevoerd voor subscription {subscription_id}")
            except Exception as e:
                logging.error(f"Fout bij {action} van subscription {subscription_id}: {str(e)}")
                continue
            
        except Exception as e:
            logging.error(f"Fout bij verwerken van subscription {subscription_id}: {str(e)}")
            continue
        
        processed_count += 1
    
    batch_summary = f"Batch verwerkt: {processed_count} totaal, {success_count} succesvol ({update_count} updates, {insert_count} inserts)"
    logging.info(batch_summary)
    return {"processed": processed_count, "success": success_count, "updates": update_count, "inserts": insert_count}

def update_or_insert_sub_to_bigquery(subscription_ids, wcapi):
    if not isinstance(subscription_ids, list):
        subscription_ids = [subscription_ids]

    total_count = len(subscription_ids)
    logging.info(f"Start verwerking van {total_count} abonnementen naar BigQuery")

    # Initialiseer de BigQuery client
    client = bigquery.Client()
    dataset_id = "woocommerce"
    table_id = "subscriptions"

    # Verdeel de subscriptions in batches van 100
    batch_size = 100
    subscription_batches = [
        subscription_ids[i:i + batch_size] 
        for i in range(0, len(subscription_ids), batch_size)
    ]

    # Statistieken bijhouden
    total_processed = 0
    total_success = 0
    total_updates = 0
    total_inserts = 0

    # Verwerk batches parallel met maximaal 4 threads
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(
                process_subscription_batch, 
                batch, 
                wcapi, 
                client, 
                dataset_id, 
                table_id
            )
            for batch in subscription_batches
        ]
        
        # Wacht tot alle batches klaar zijn en verzamel statistieken
        for future in futures:
            result = future.result()
            total_processed += result["processed"]
            total_success += result["success"]
            total_updates += result["updates"]
            total_inserts += result["inserts"]

    final_summary = f"""
    Verwerking voltooid:
    - Totaal verwerkt: {total_processed}/{total_count}
    - Succesvol: {total_success}
    - Updates: {total_updates}
    - Nieuwe inserts: {total_inserts}
    - Fouten: {total_count - total_success}
    """
    logging.info(final_summary)