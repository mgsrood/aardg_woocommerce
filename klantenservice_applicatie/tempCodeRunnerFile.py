from utils.woocommerce import wcapi
import json

def test_subscription_metadata(subscription_id):
    """
    Test script om de metadata van een WooCommerce subscription te controleren.
    """
    try:
        print(f"Ophalen van abonnement met ID: {subscription_id}")
        
        # Haal het abonnement op
        response = wcapi.get(f"subscriptions/{subscription_id}")
        
        if response.status_code != 200:
            print(f"Fout bij ophalen abonnement: {response.status_code}")
            print(f"Response: {response.text}")
            return
        
        subscription = response.json()
        
        # Print alle metadata
        print("\nAlle metadata van het abonnement:")
        print(json.dumps(subscription.get('meta_data', []), indent=2))
        
        # Zoek specifiek naar _last_order_id
        last_order_id = None
        for meta in subscription.get('meta_data', []):
            if meta.get('key') == '_last_order_id':
                last_order_id = meta.get('value')
                break
        
        if last_order_id:
            print(f"\nLaatste order ID gevonden: {last_order_id}")
            
            # Haal de order op
            order_response = wcapi.get(f"orders/{last_order_id}")
            if order_response.status_code == 200:
                order = order_response.json()
                print(f"\nDetails van de laatste order:")
                print(f"Order ID: {order.get('id')}")
                print(f"Besteldatum: {order.get('date_created')}")
                print(f"Status: {order.get('status')}")
            else:
                print(f"\nFout bij ophalen order: {order_response.status_code}")
                print(f"Response: {order_response.text}")
        else:
            print("\nGeen _last_order_id gevonden in de metadata")
        
    except Exception as e:
        print(f"Fout: {str(e)}")

if __name__ == "__main__":
    # Vraag om een subscription ID
    subscription_id = input("Voer een subscription ID in: ")
    test_subscription_metadata(subscription_id) 