import logging

def check_webhooks(wcapi):
    try:
        response = wcapi.get("webhooks", params={"per_page": 100, "page": 1})
        if not response or response.status_code != 200:
            logging.error(f"WooCommerce API-fout: {response.status_code if response else 'Geen response'} - {response.text if response else 'Geen inhoud'}")
            return

        webhooks = response.json()
        
        for webhook in webhooks:
            if "ActiveCampaign" not in webhook["name"]:
                if webhook["status"] in ["disabled", "trash"]:
                    logging.error(f"Webhook '{webhook['name']}' (ID: {webhook['id']}) is uitgeschakeld.")

    except Exception as e:
        logging.error(f"Fout bij ophalen WooCommerce webhooks: {e}")
