def get_woocommerce_order_data(order_id, wcapi):
    response = wcapi.get(f"orders/{order_id}")
    return response.json()

def get_woocommerce_subscription_data(subscription_id, wcapi):
    response = wcapi.get(f"subscriptions/{subscription_id}")
    return response.json()

def retrieve_all_products(wcapi, per_page=100):
    products = []
    page = 1
    
    while True:
        # Verkrijg de producten van de huidige pagina
        response = wcapi.get("products", params={"page": page, "per_page": per_page})
        page_products = response.json()
        
        # Als er geen producten zijn, stoppen we
        if not page_products:
            break
        
        # Voeg de producten van deze pagina toe aan de lijst
        products.extend(page_products)
        
        # Ga naar de volgende pagina
        page += 1
    
    product_catalogue = {
    }
    for product in products:
        product_id = product['id']
        product_sku = product['sku']
        product_catalogue[product_sku] = product_id

    return product_catalogue