from g_modules.cache import cache_decorator
import logging

@cache_decorator(timeout=300)  # Cache voor 5 minuten
def get_woocommerce_order_data(order_id, wcapi):
    """
    Haalt order data op van WooCommerce API met caching.
    Cache verloopt na 5 minuten.
    """
    logging.info(f"WooCommerce order data ophalen voor order {order_id}")
    response = wcapi.get(f"orders/{order_id}")
    return response.json()

@cache_decorator(timeout=300)  # Cache voor 5 minuten
def get_woocommerce_subscription_data(subscription_id, wcapi):
    """
    Haalt abonnement data op van WooCommerce API met caching.
    Cache verloopt na 5 minuten.
    """
    logging.info(f"WooCommerce subscription data ophalen voor abonnement {subscription_id}")
    response = wcapi.get(f"subscriptions/{subscription_id}")
    return response.json()