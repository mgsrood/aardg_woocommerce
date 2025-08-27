import logging
import time
from .azure_sql_monitor import log_webhook_monitoring, create_alert, monitor_all_systems

def check_and_reactivate_webhooks(wcapi, required_webhooks) -> None:
    """
    Controleer en heractiveer inactieve webhooks met Azure SQL logging
    """
    
    start_time = time.time()
    
    try:
        # Alle webhooks ophalen
        response = wcapi.get("webhooks", params={"per_page": 100})
        api_response_time = int((time.time() - start_time) * 1000)
        
        if response.status_code != 200:
            error_msg = f"Fout bij ophalen webhooks: {response.text}"
            logging.error(error_msg)
            
            # Log de fout naar Azure SQL
            log_webhook_monitoring(
                webhook_id=0,
                webhook_name="API_ERROR",
                webhook_url=None,
                previous_status=None,
                current_status="error",
                action_taken=None,
                error_message=error_msg,
                response_time=api_response_time
            )
            
            # Maak alert aan
            create_alert(
                'api_failure',
                'high',
                'WooCommerce API Error',
                f"Failed to fetch webhooks: {response.status_code}",
                'WooCommerce API'
            )
            return
        
        webhooks = response.json()
        logging.info(f"Ophalen van {len(webhooks)} webhooks gelukt in {api_response_time}ms")
        
        # Houd bij welke required webhooks we hebben gevonden
        found_webhooks = set()
        
        # Controleer elke webhook
        for webhook in webhooks:
            webhook_id = webhook.get('id')
            webhook_name = webhook.get('name', '')
            webhook_url = webhook.get('delivery_url', '')
            current_status = webhook.get('status', 'unknown')
            
            if webhook_name in required_webhooks:
                found_webhooks.add(webhook_name)
                
                if current_status != 'active':
                    logging.warning(f"Webhook {webhook_name} is {current_status}, heractiveren...")
                    
                    try:
                        update_start = time.time()
                        update_response = wcapi.put(f"webhooks/{webhook_id}", {
                            "status": "active"
                        })
                        update_time = int((time.time() - update_start) * 1000)
                        
                        if update_response.status_code == 200:
                            logging.info(f"Webhook {webhook_name} succesvol geheractiveerd")
                            
                            # Log succesvolle heractivering
                            log_webhook_monitoring(
                                webhook_id=webhook_id,
                                webhook_name=webhook_name,
                                webhook_url=webhook_url,
                                previous_status=current_status,
                                current_status="active",
                                action_taken="reactivated",
                                error_message=None,
                                response_time=update_time
                            )
                            
                        else:
                            error_msg = f"Fout bij heractiveren {webhook_name}: {update_response.text}"
                            logging.error(error_msg)
                            
                            # Log gefaalde heractivering
                            log_webhook_monitoring(
                                webhook_id=webhook_id,
                                webhook_name=webhook_name,
                                webhook_url=webhook_url,
                                previous_status=current_status,
                                current_status=current_status,  # Status blijft hetzelfde
                                action_taken="failed_to_reactivate",
                                error_message=error_msg,
                                response_time=update_time
                            )
                            
                            # Maak alert aan
                            create_alert(
                                'webhook_down',
                                'medium',
                                f'Failed to Reactivate Webhook: {webhook_name}',
                                error_msg,
                                webhook_name
                            )
                            
                    except Exception as e:
                        error_msg = f"Fout bij updaten webhook {webhook_name}: {str(e)}"
                        logging.error(error_msg)
                        
                        # Log exception
                        log_webhook_monitoring(
                            webhook_id=webhook_id,
                            webhook_name=webhook_name,
                            webhook_url=webhook_url,
                            previous_status=current_status,
                            current_status="error",
                            action_taken="failed_to_reactivate",
                            error_message=error_msg,
                            response_time=None
                        )
                        
                        # Maak alert aan
                        create_alert(
                            'webhook_down',
                            'high',
                            f'Webhook Update Failed: {webhook_name}',
                            error_msg,
                            webhook_name
                        )
                        
                else:
                    logging.info(f"Webhook {webhook_name} is al actief")
                    
                    # Log dat webhook al actief is
                    log_webhook_monitoring(
                        webhook_id=webhook_id,
                        webhook_name=webhook_name,
                        webhook_url=webhook_url,
                        previous_status=None,  # We weten de vorige status niet
                        current_status=current_status,
                        action_taken="already_active",
                        error_message=None,
                        response_time=None
                    )
        
        # Controleer of alle required webhooks gevonden zijn
        missing_webhooks = set(required_webhooks) - found_webhooks
        if missing_webhooks:
            missing_list = ", ".join(missing_webhooks)
            error_msg = f"Ontbrekende webhooks: {missing_list}"
            logging.error(error_msg)
            
            # Log ontbrekende webhooks
            for missing_webhook in missing_webhooks:
                log_webhook_monitoring(
                    webhook_id=0,
                    webhook_name=missing_webhook,
                    webhook_url=None,
                    previous_status=None,
                    current_status="missing",
                    action_taken=None,
                    error_message="Webhook not found in WooCommerce",
                    response_time=None
                )
            
            # Maak alert aan
            create_alert(
                'webhook_down',
                'high',
                'Missing Required Webhooks',
                error_msg,
                'Webhook Monitor'
            )
    
    except Exception as e:
        error_msg = f"Algemene fout in webhook monitoring: {str(e)}"
        logging.error(error_msg)
        
        # Log algemene fout
        log_webhook_monitoring(
            webhook_id=0,
            webhook_name="MONITOR_ERROR",
            webhook_url=None,
            previous_status=None,
            current_status="error",
            action_taken=None,
            error_message=error_msg,
            response_time=None
        )
        
        # Maak alert aan
        create_alert(
            'webhook_down',
            'critical',
            'Webhook Monitor Failed',
            error_msg,
            'Webhook Monitor'
        )
