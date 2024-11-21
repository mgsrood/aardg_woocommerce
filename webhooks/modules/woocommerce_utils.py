import time

def get_woocommerce_order_data(order_id, wcapi):
    response = wcapi.get(f"orders/{order_id}")
    return response.json()

def get_woocommerce_subscription_data(subscription_id, wcapi):
    response = wcapi.get(f"subscriptions/{subscription_id}")
    return response.json()

def wait_for_buffer_to_clear(client, dataset_id, table_id, subscription_id, max_retries=10, wait_time=10):
    """
    Wacht totdat de streamingbuffer leeg is, maximaal `max_retries` pogingen.
    """
    retries = 0
    while retries < max_retries:
        # Controleer of de gegevens al uit de streamingbuffer zijn
        check_query = f"""
        SELECT COUNT(*) AS cnt
        FROM `{dataset_id}.{table_id}`
        WHERE subscription_id = {subscription_id}
        """
        check_job = client.query(check_query)
        results = check_job.result()

        row_count = 0
        for row in results:
            row_count = row.cnt

        if row_count > 0:
            # Als er nog gegevens in de buffer staan, wacht dan en probeer opnieuw
            print(f"De gegevens bevinden zich nog in de streamingbuffer. Poging {retries + 1} van {max_retries}.")
            time.sleep(wait_time)  # Wacht 10 seconden
            retries += 1
        else:
            # Als de gegevens niet meer in de buffer staan, kan de update worden uitgevoerd
            print(f"Gegevens voor subscription_id {subscription_id} zijn beschikbaar voor bewerking.")
            return True  # Gegevens zijn beschikbaar voor bewerking

    # Als de buffer niet leeg is na het maximale aantal pogingen
    print(f"Maximale pogingen bereikt. De gegevens voor {subscription_id} bevinden zich nog in de streamingbuffer.")
    return False  # De gegevens zijn nog steeds niet beschikbaar voor bewerking
