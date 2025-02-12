
def get_woocommerce_order_data(order_id, wcapi):
    response = wcapi.get(f"orders/{order_id}")
    return response.json()

def get_woocommerce_subscription_data(subscription_id, wcapi):
    response = wcapi.get(f"subscriptions/{subscription_id}")
    return response.json()