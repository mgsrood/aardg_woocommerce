from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def move_next_payment_date(data, wcapi):
    logging.debug(f"Starting move_next_payment_date for: {data['billing']['email']}")
    logging.debug(f"Determining payment method")
    payment_method = data.get('payment_method_title')
    if payment_method in ['iDEAL', 'Bancontact']:
        next_payment_date_str = data.get('next_payment_date_gmt')
        logging.debug(f"Moving payment date to: {next_payment_date_str}")
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
                logging.error(f"Failed to update subscription: {e}")