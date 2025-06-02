from datetime import datetime, timedelta
from google.cloud import bigquery
from woocommerce import API
import logging
import os

# Helper functie voor BigQuery client en tabel
def _get_bigquery_client_and_table(dataset_id, table_id):
    """Initialiseert BigQuery client en retourneert client en table reference."""
    credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
    if not credentials_path:
        raise ValueError("AARDG_GOOGLE_CREDENTIALS environment variable is not set")
    
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    client = bigquery.Client()
    table_ref = client.dataset(dataset_id).table(table_id)
    try:
        client.get_table(table_ref)  # Controleer of tabel bestaat
        logging.info(f"Tabel {table_id} in dataset {dataset_id} gevonden.")
    except Exception as e:
        logging.error(f"Fout bij het verkrijgen van de tabel {dataset_id}.{table_id}: {e}")
        raise
    return client, table_ref

def move_next_payment_date(data):
    """Verplaatst de volgende betaaldatum als de betaalmethode iDEAL of Bancontact is."""
    payment_method = data.get('payment_method_title')
    subscription_id = data.get('id') # Haal vroeg op voor logging en return
    next_payment_date_str = data.get('next_payment_date_gmt')

    logging.info(f"Start verwerking verplaatsing betaaldatum voor abonnement: {subscription_id}, betaalmethode: {payment_method}")

    if payment_method not in ['iDEAL', 'Bancontact']:
        msg = f'Betaalmethode ({payment_method}) vereist geen aanpassing van de betaaldatum voor abonnement {subscription_id}.'
        logging.info(msg)
        return {
            'status': 'geen_actie_nodig',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method
        }

    if not next_payment_date_str:
        msg = f"Volgende betaaldatum (next_payment_date_gmt) niet gevonden in data voor abonnement {subscription_id}."
        logging.warning(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method,
            'details': 'next_payment_date_gmt ontbreekt'
        }

    logging.info(f"Originele volgende betaaldatum voor abonnement {subscription_id}: {next_payment_date_str}")

    try:
        consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
        consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
        woocommerce_url = os.getenv('WOOCOMMERCE_URL')

        if not all([consumer_secret, consumer_key, woocommerce_url]):
            msg = f"Ontbrekende WooCommerce API configuratie (URL, Key of Secret) voor abonnement {subscription_id}."
            logging.error(msg)
            # Deze ValueError wordt hieronder opgevangen
            raise ValueError(msg) 

        wcapi = API(
            url=woocommerce_url,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            version="wc/v3",
            timeout=60
        )

        next_payment_date = datetime.strptime(next_payment_date_str, '%Y-%m-%dT%H:%M:%S')
        new_next_payment_date = next_payment_date - timedelta(days=7)
        
        # Gebruik 'next_payment_date' als key en formatteer de datum als YYYY-MM-DD HH:MM:SS
        update_data = {"next_payment_date": new_next_payment_date.strftime('%Y-%m-%d %H:%M:%S')}
        
        if not subscription_id:
            # Deze check is enigszins redundant geworden door de vroege fetch, maar behouden voor robuustheid.
            msg = f"Abonnements ID niet gevonden in data voor het bijwerken van de betaaldatum."
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg,
                'abonnements_id': None, # Expliciet None omdat het hier faalt
                'betaalmethode': payment_method,
                'details': 'subscription_id ontbreekt bij update poging'
            }

        response = wcapi.put(f"subscriptions/{subscription_id}", update_data)
        
        if response.status_code != 200:
            error_body_text = ""
            try:
                json_response = response.json()
                if isinstance(json_response, dict) and 'message' in json_response:
                    # Gebruik het bericht van de API als dat er is
                    error_body_text = f"API Bericht: {json_response.get('message')}"
                    if 'data' in json_response and json_response.get('data') is not None:
                        error_body_text += f", API Data: {json_response.get('data')}" 
                else:
                    error_body_text = f"Volledige API response: {response.text}"
            except ValueError: # response.json() faalt als het geen JSON is
                error_body_text = f"Volledige API response (geen JSON): {response.text}"

            msg = f"Fout bij verplaatsen van de betaaldatum voor abonnement {subscription_id}: {response.status_code}"
            # Log de volledige foutdetails
            logging.error(f"{msg} - Details: {error_body_text}")
            return {
                'status': 'fout',
                'bericht': msg,
                'abonnements_id': subscription_id,
                'betaalmethode': payment_method,
                # Geef de gedetailleerde foutmelding ook terug in de response
                'details': f"HTTP status: {response.status_code}. {error_body_text}"
            }
        else:
            # Gebruik het correcte datumformaat in het succesbericht
            formatted_new_date = new_next_payment_date.strftime('%Y-%m-%d %H:%M:%S')
            msg = f"Betaaldatum voor abonnement {subscription_id} succesvol verplaatst met 7 dagen naar {formatted_new_date}"
            logging.info(msg)
            return {
                'status': 'succes',
                'bericht': msg,
                'abonnements_id': subscription_id,
                'originele_betaaldatum': next_payment_date_str,
                'nieuwe_betaaldatum': formatted_new_date,
                'betaalmethode': payment_method
            }

    except ValueError as ve:
        # Vangt o.a. de strptime error en de handmatig gegooide ValueError voor API config
        msg = f"Fout bij verwerken betaaldatum voor abonnement {subscription_id}: {str(ve)}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method,
            'details': str(ve)
        }
    except Exception as e:
        msg = f"Algemene fout bij het verplaatsen van de betaaldatum voor abonnement {subscription_id}: {str(e)}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'abonnements_id': subscription_id,
            'betaalmethode': payment_method,
            'details': str(e)
        }

def _prepare_subscription_data_for_bq(sub_data):
    """Bereidt subscription data voor om naar BigQuery te schrijven."""
    billing_info = sub_data.get("billing", {})
    shipping_info = sub_data.get("shipping", {})
    line_items = sub_data.get("line_items", [])

    return {
        "subscription_id": sub_data.get("id"),
        "parent_id": sub_data.get("parent_id"),
        "status": sub_data.get("status"),
        "number": sub_data.get("number"),
        "currency": sub_data.get("currency"),
        "date_created": sub_data.get("date_created"),
        "date_modified": sub_data.get("date_modified"),
        "customer_id": sub_data.get("customer_id"),
        "discount_total": float(sub_data.get("discount_total", 0.0)),
        "total": float(sub_data.get("total", 0.0)),
        "billing_company": billing_info.get("company"),
        "billing_city": billing_info.get("city"),
        "billing_state": billing_info.get("state"),
        "billing_postcode": billing_info.get("postcode"),
        "billing_country": billing_info.get("country"),
        "billing_email": billing_info.get("email"),
        "billing_first_name": billing_info.get("first_name"),
        "billing_last_name": billing_info.get("last_name"),
        "billing_address_1": billing_info.get("address_1"),
        "billing_address_2": billing_info.get("address_2"),
        "shipping_company": shipping_info.get("company"),
        "shipping_city": shipping_info.get("city"),
        "shipping_state": shipping_info.get("state"),
        "shipping_postcode": shipping_info.get("postcode"),
        "shipping_country": shipping_info.get("country"),
        "shipping_first_name": shipping_info.get("first_name"),
        "shipping_last_name": shipping_info.get("last_name"),
        "shipping_address_1": shipping_info.get("address_1"),
        "shipping_address_2": shipping_info.get("address_2"),
        "payment_method": sub_data.get("payment_method"),
        "payment_method_title": sub_data.get("payment_method_title"),
        "transaction_id": None,
        "customer_ip_address": sub_data.get("customer_ip_address"),
        "customer_user_agent": sub_data.get("customer_user_agent"),
        "created_via": sub_data.get("created_via"),
        "customer_note": sub_data.get("customer_note"),
        "date_completed": sub_data.get("date_completed"),
        "date_paid": sub_data.get("date_paid"),
        "cart_hash": "",
        "lineitems_quantity": [item.get("quantity", 0) for item in line_items],
        "lineitems_subtotal": [float(item.get("subtotal", 0.0)) for item in line_items],
        "lineitems_total": [float(item.get("total", 0.0)) for item in line_items],
        "lineitems_price": [float(item.get("price", 0.0)) for item in line_items],
        "lineitems_product_id": [item.get("product_id", 0) for item in line_items],
        "billing_period": sub_data.get("billing_period"),
        "billing_interval": sub_data.get("billing_interval"),
        "start_date": sub_data.get("start_date_gmt"),
        "next_payment_date": sub_data.get("next_payment_date_gmt"),
        "end_date": sub_data.get("end_date_gmt"),
        "shipping_total": float(sub_data.get("shipping_total", 0.0))
    }

def update_or_insert_sub_to_bigquery(customer_data):
    """Update of insert subscription data in BigQuery."""
    logging.info(f"Abonnement verwerken in BigQuery")
    dataset_id = "woocommerce"
    table_id = "subscriptions"
    action_taken = "geen"
    
    # Haal billing info vroeg op voor return message, zelfs bij een fout
    billing_info_early = customer_data.get("billing", {})
    email_early = billing_info_early.get("email", "onbekend")
    first_name_early = billing_info_early.get("first_name", "onbekend")
    last_name_early = billing_info_early.get("last_name", "onbekend")
    subscription_id_param = customer_data.get("id")

    try:
        client, table_ref = _get_bigquery_client_and_table(dataset_id, table_id)
        tabel_input = _prepare_subscription_data_for_bq(customer_data)
        subscription_id = tabel_input.get("subscription_id")
        
        # Gebruik de waarden uit tabel_input (voorbereide data) voor de rest van de logica
        email = tabel_input.get("billing_email", email_early)
        first_name = tabel_input.get("billing_first_name", first_name_early)
        last_name = tabel_input.get("billing_last_name", last_name_early)

        if not subscription_id:
            msg = "Abonnement ID ontbreekt in voorbereide data."
            logging.error(msg)
            return {
                'status': 'fout', 
                'bericht': msg, 
                'actie_genomen': 'fout', 
                'abonnements_id': subscription_id_param,
                'email': email,
                'voornaam': first_name,
                'achternaam': last_name
            }

        check_query = f"SELECT COUNT(1) FROM `{table_ref}` WHERE subscription_id = {subscription_id}"
        exists = next(client.query(check_query).result()).f0_ > 0

        fields_to_set = [
            "parent_id = @parent_id", "status = @status", "number = @number", "currency = @currency",
            "date_created = @date_created", "date_modified = @date_modified", "customer_id = @customer_id",
            "discount_total = @discount_total", "total = @total", "billing_company = @billing_company",
            "billing_city = @billing_city", "billing_state = @billing_state", "billing_postcode = @billing_postcode",
            "billing_country = @billing_country", "billing_email = @billing_email",
            "billing_first_name = @billing_first_name", "billing_last_name = @billing_last_name",
            "billing_address_1 = @billing_address_1", "billing_address_2 = @billing_address_2",
            "shipping_company = @shipping_company", "shipping_city = @shipping_city",
            "shipping_state = @shipping_state", "shipping_postcode = @shipping_postcode",
            "shipping_country = @shipping_country", "shipping_first_name = @shipping_first_name",
            "shipping_last_name = @shipping_last_name", "shipping_address_1 = @shipping_address_1",
            "shipping_address_2 = @shipping_address_2", "payment_method = @payment_method",
            "payment_method_title = @payment_method_title", "transaction_id = @transaction_id",
            "customer_ip_address = @customer_ip_address", "customer_user_agent = @customer_user_agent",
            "created_via = @created_via", "customer_note = @customer_note", "date_completed = @date_completed",
            "date_paid = @date_paid", "cart_hash = @cart_hash", "lineitems_quantity = @lineitems_quantity",
            "lineitems_subtotal = @lineitems_subtotal", "lineitems_total = @lineitems_total",
            "lineitems_price = @lineitems_price", "lineitems_product_id = @lineitems_product_id",
            "billing_period = @billing_period", "billing_interval = @billing_interval",
            "start_date = @start_date", "next_payment_date = @next_payment_date", "end_date = @end_date",
            "shipping_total = @shipping_total"
        ]
        columns = ["subscription_id"] + [f.split(" = ")[0] for f in fields_to_set]
        placeholders = ["@subscription_id"] + [f.split(" = ")[1] for f in fields_to_set]

        query = f"""
        MERGE `{table_ref}` T
        USING (SELECT @subscription_id AS subscription_id_source) S
        ON T.subscription_id = S.subscription_id_source
        WHEN MATCHED THEN
            UPDATE SET {", ".join(fields_to_set)}
        WHEN NOT MATCHED THEN
            INSERT ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
        """
        
        final_params = []
        for key, value in tabel_input.items():
            param_name = key
            if "lineitems" in key: 
                if "quantity" in key or "id" in key or "product_id" in key:
                    # Specifiek voor quantity, id en product_id: gebruik INT64
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "INT64", [int(x) for x in value]))
                elif "product_name" in key:
                    # Voor product names: gebruik STRING array
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "STRING", value))
                else:
                    # Voor andere numerieke waarden: gebruik FLOAT64
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "FLOAT64", value))
            elif "discount" in key:
                if "code" in key:
                    # Voor discount codes: gebruik STRING array
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "STRING", value))
                elif "per_code" in key:
                    # Voor discount bedragen per code: gebruik FLOAT64 array
                    # Zorg ervoor dat alle waarden float zijn
                    float_values = [float(x) if isinstance(x, (int, float)) else float(str(x)) for x in value]
                    logging.info(f"Discount per code waarden voor BigQuery: {float_values}, Types: {[type(x) for x in float_values]}")
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "FLOAT64", float_values))
                else:
                    # Voor totaal discount: gebruik FLOAT64 scalar
                    final_params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", value))
            elif key == "transaction_id":
                 # Converteer transaction_id naar STRING, gebruik lege string als het leeg is
                 transaction_value = str(value) if value and str(value).strip() else ""
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "STRING", transaction_value))
            elif key in ["subscription_id", "parent_id", "customer_id", "number"]:
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", value))
            elif key in ["discount_total", "total", "shipping_total"]:
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", value))
            elif key in ["billing_interval"]:
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", value))
            else:
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "STRING", str(value) if value is not None else None))
        job_config = bigquery.QueryJobConfig(query_parameters=final_params)

        query_job = client.query(query, job_config=job_config)
        query_job.result()

        action_taken = "update" if exists else "insert"
        actie_nl = "geüpdatet" if exists else "ingevoegd"
        msg = f"Abonnement {subscription_id} ({first_name} {last_name}, {email}) succesvol {actie_nl} in BigQuery."
        logging.info(msg)
        return {
            'status': 'succes',
            'bericht': msg,
            'actie_genomen': action_taken,
            'abonnements_id': subscription_id,
            'email': email,
            'voornaam': first_name,
            'achternaam': last_name
        }

    except Exception as e:
        msg = f"Fout bij het verwerken van abonnement {subscription_id_param} ({first_name_early} {last_name_early}, {email_early}) in BigQuery: {e}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'actie_genomen': 'fout',
            'abonnements_id': subscription_id_param,
            'email': email_early,
            'voornaam': first_name_early,
            'achternaam': last_name_early
        }

def _prepare_order_data_for_bq(order_data):
    """Bereidt order data voor om naar BigQuery te schrijven."""
    billing_info = order_data.get("billing", {})
    shipping_info = order_data.get("shipping", {})
    line_items = order_data.get("line_items", [])
    coupon_lines = order_data.get("coupon_lines", [])

    # Bereid discount_per_code voor
    discount_per_code = []
    for item in coupon_lines:
        discount = item.get("discount", 0.0)
        try:
            float_discount = float(discount)
            discount_per_code.append(float_discount)
        except Exception as e:
            discount_per_code.append(0.0)

    return {
        "order_id": order_data.get("id"),
        "status": order_data.get("status"),
        "currency": order_data.get("currency"),
        "total": float(order_data.get("total", 0.0)),
        "billing_company": billing_info.get("company"),
        "billing_city": billing_info.get("city"),
        "billing_state": billing_info.get("state"),
        "billing_postcode": billing_info.get("postcode"),
        "billing_country": billing_info.get("country"),
        "billing_email": billing_info.get("email"),
        "billing_first_name": billing_info.get("first_name"),
        "billing_last_name": billing_info.get("last_name"),
        "billing_address_1": billing_info.get("address_1"),
        "billing_address_2": billing_info.get("address_2"),
        "shipping_company": shipping_info.get("company"),
        "shipping_city": shipping_info.get("city"),
        "shipping_state": shipping_info.get("state"),
        "shipping_postcode": shipping_info.get("postcode"),
        "shipping_country": shipping_info.get("country"),
        "shipping_first_name": shipping_info.get("first_name"),
        "shipping_last_name": shipping_info.get("last_name"),
        "shipping_address_1": shipping_info.get("address_1"),
        "shipping_address_2": shipping_info.get("address_2"),
        "order_number": order_data.get("number"),
        "date_created": order_data.get("date_created"),
        "date_modified": order_data.get("date_modified"),
        "discount_total": float(order_data.get("discount_total", 0.0)),
        "customer_id": order_data.get("customer_id"),
        "order_key": order_data.get("order_key"),
        "payment_method": order_data.get("payment_method"),
        "payment_method_title": order_data.get("payment_method_title"),
        "transaction_id": None,
        "customer_ip_address": order_data.get("customer_ip_address"),
        "customer_user_agent": order_data.get("customer_user_agent"),
        "created_via": order_data.get("created_via"),
        "customer_note": order_data.get("customer_note"),
        "date_completed": order_data.get("date_completed"),
        "date_paid": order_data.get("date_paid"),
        "cart_hash": "",
        "lineitems_id": [item.get("id", 0) for item in line_items],
        "lineitems_product_name": [item.get("name", "") for item in line_items],
        "lineitems_quantity": [item.get("quantity", 0) for item in line_items],
        "lineitems_subtotal": [float(item.get("subtotal", 0.0)) for item in line_items],
        "lineitems_total": [float(item.get("total", 0.0)) for item in line_items],
        "lineitems_product_id": [item.get("product_id", 0) for item in line_items],
        "discount_code": [item.get("code", "") for item in coupon_lines],
        "discount_per_code": discount_per_code,
        "payment_url": order_data.get("payment_url"),
        "currency_symbol": order_data.get("currency_symbol"),
        "shipping_total": float(order_data.get("shipping_total", 0.0))
    }

def update_or_insert_order_to_bigquery(customer_data):
    """Update of insert order data in BigQuery."""
    logging.info(f"Order verwerken in BigQuery")
    dataset_id = "woocommerce"
    table_id = "orders"
    action_taken = "geen"

    billing_info_early = customer_data.get("billing", {})
    email_early = billing_info_early.get("email", "onbekend")
    first_name_early = billing_info_early.get("first_name", "onbekend")
    last_name_early = billing_info_early.get("last_name", "onbekend")
    order_id_param = customer_data.get("id")

    try:
        client, table_ref = _get_bigquery_client_and_table(dataset_id, table_id)
        tabel_input = _prepare_order_data_for_bq(customer_data)
        order_id = tabel_input.get("order_id")

        email = tabel_input.get("billing_email", email_early)
        first_name = tabel_input.get("billing_first_name", first_name_early)
        last_name = tabel_input.get("billing_last_name", last_name_early)

        if not order_id:
            msg = "Order ID ontbreekt in voorbereide data."
            logging.error(msg)
            return {
                'status': 'fout',
                'bericht': msg,
                'actie_genomen': 'fout',
                'order_id': order_id_param,
                'email': email,
                'voornaam': first_name,
                'achternaam': last_name
            }

        check_query = f"SELECT COUNT(1) FROM `{table_ref}` WHERE order_id = {order_id}"
        exists = next(client.query(check_query).result()).f0_ > 0
        
        fields_to_set = [
            "status = @status", "currency = @currency", "total = @total", "billing_company = @billing_company",
            "billing_city = @billing_city", "billing_state = @billing_state", "billing_postcode = @billing_postcode",
            "billing_country = @billing_country", "billing_email = @billing_email",
            "billing_first_name = @billing_first_name", "billing_last_name = @billing_last_name",
            "billing_address_1 = @billing_address_1", "billing_address_2 = @billing_address_2",
            "shipping_company = @shipping_company", "shipping_city = @shipping_city",
            "shipping_state = @shipping_state", "shipping_postcode = @shipping_postcode",
            "shipping_country = @shipping_country", "shipping_first_name = @shipping_first_name",
            "shipping_last_name = @shipping_last_name", "shipping_address_1 = @shipping_address_1",
            "shipping_address_2 = @shipping_address_2", "order_number = @order_number",
            "date_created = @date_created", "date_modified = @date_modified", "discount_total = @discount_total",
            "customer_id = @customer_id", "order_key = @order_key", "payment_method = @payment_method",
            "payment_method_title = @payment_method_title", "transaction_id = NULL",
            "customer_ip_address = @customer_ip_address", "customer_user_agent = @customer_user_agent",
            "created_via = @created_via", "customer_note = @customer_note", "date_completed = @date_completed",
            "date_paid = @date_paid", "cart_hash = @cart_hash", "lineitems_id = @lineitems_id",
            "lineitems_product_name = @lineitems_product_name", "lineitems_quantity = @lineitems_quantity",
            "lineitems_subtotal = @lineitems_subtotal", "lineitems_total = @lineitems_total",
            "lineitems_product_id = @lineitems_product_id", "discount_code = @discount_code",
            f"discount_per_code = [{', '.join(map(str, [float(x) for x in tabel_input['discount_per_code']]))}]",
            "payment_url = @payment_url", "currency_symbol = @currency_symbol", "shipping_total = @shipping_total"
        ]
        columns = ["order_id"] + [f.split(" = ")[0] for f in fields_to_set]
        placeholders = ["@order_id"] + [f.split(" = ")[1] for f in fields_to_set]
        
        query = f"""
        MERGE `{table_ref}` T
        USING (SELECT @order_id AS order_id_source) S
        ON T.order_id = S.order_id_source
        WHEN MATCHED THEN
            UPDATE SET {", ".join(fields_to_set)}
        WHEN NOT MATCHED THEN
            INSERT ({", ".join(columns)})
            VALUES ({", ".join(placeholders)})
        """

        final_params = []
        for key, value in tabel_input.items():
            param_name = key
            if key == "transaction_id" or key == "discount_per_code":
                continue  # Sla deze over omdat we ze direct in de query verwerken
            if "lineitems" in key: 
                if "quantity" in key or "id" in key or "product_id" in key:
                    # Specifiek voor quantity, id en product_id: gebruik INT64
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "INT64", [int(x) for x in value]))
                elif "product_name" in key:
                    # Voor product names: gebruik STRING array
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "STRING", value))
                else:
                    # Voor andere numerieke waarden: gebruik FLOAT64
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "FLOAT64", value))
            elif "discount" in key:
                if "code" in key:
                    # Voor discount codes: gebruik STRING array
                    final_params.append(bigquery.ArrayQueryParameter(param_name, "STRING", value))
                else:
                    # Voor totaal discount: gebruik FLOAT64 scalar
                    final_params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", value))
            elif key in ["order_id", "customer_id", "order_number"]:
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "INT64", value))
            elif key in ["total", "shipping_total"]:
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "FLOAT64", value))
            else:
                 final_params.append(bigquery.ScalarQueryParameter(param_name, "STRING", str(value) if value is not None else None))
        job_config = bigquery.QueryJobConfig(query_parameters=final_params)

        query_job = client.query(query, job_config=job_config)
        query_job.result()

        action_taken = "update" if exists else "insert"
        actie_nl = "geüpdatet" if exists else "ingevoegd"
        msg = f"Order {order_id} ({first_name} {last_name}, {email}) succesvol {actie_nl} in BigQuery."
        logging.info(msg)
        return {
            'status': 'succes',
            'bericht': msg,
            'actie_genomen': action_taken,
            'order_id': order_id,
            'email': email,
            'voornaam': first_name,
            'achternaam': last_name
        }

    except Exception as e:
        msg = f"Fout bij het verwerken van order {order_id_param} ({first_name_early} {last_name_early}, {email_early}) in BigQuery: {e}"
        logging.error(msg)
        return {
            'status': 'fout',
            'bericht': msg,
            'actie_genomen': 'fout',
            'order_id': order_id_param,
            'email': email_early,
            'voornaam': first_name_early,
            'achternaam': last_name_early
        }