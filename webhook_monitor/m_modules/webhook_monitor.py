import logging

def check_and_reactivate_webhooks(wcapi, required_webhooks) -> None:
    """
    Controleer en heractiveer inactieve webhooks
    """

    # Alle webhooks ophalen
    response = wcapi.get("webhooks", params={"per_page": 100})
    if response.status_code != 200:
        logging.error(f"Fout bij ophalen webhooks: {response.text}")
        return
    
    webhooks = response.json()
    
    # Controleer elke webhook
    for webhook in webhooks:
        webhook_name = webhook.get('name', '')
        
        if webhook_name in required_webhooks:
            if webhook['status'] != 'active':
                logging.info(f"Heractiveren webhook: {webhook_name}")
                
                try:
                    update_response = wcapi.put(f"webhooks/{webhook['id']}", {
                        "status": "active"
                    })
                    
                    if update_response.status_code == 200:
                        logging.info(f"Webhook {webhook_name} succesvol geheractiveerd")
                    else:
                        logging.error(f"Fout bij heractiveren {webhook_name}: {update_response.text}")
                        
                except Exception as e:
                    logging.error(f"Fout bij updaten webhook {webhook_name}: {str(e)}")
            else:
                logging.info(f"Webhook {webhook_name} is al actief")
