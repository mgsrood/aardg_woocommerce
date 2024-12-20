from modules.bigquery_transfer import insert_order_into_bigquery
from modules.config import set_script_id
from modules.env_tool import env_check
from modules.log import log, end_log
from woocommerce import API
import os

def main():

    # Check uitvoering: lokaal of productie
    env_check()

    # WooCommerce variabelen
    consumer_secret = os.getenv('WOOCOMMERCE_CONSUMER_SECRET')
    consumer_key = os.getenv('WOOCOMMERCE_CONSUMER_KEY')
    woocommerce_url = os.getenv('WOOCOMMERCE_URL')
    
    # Google variabelen
    credentials_path = os.getenv('AARDG_GOOGLE_CREDENTIALS')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
    
    # Database variabelen
    driver = '{ODBC Driver 18 for SQL Server}'
    username = os.getenv('GEBRUIKERSNAAM')
    database = os.getenv('DATABASE')
    password = os.getenv('PASSWORD')
    server = os.getenv('SERVER')
    greit_connection_string = f'DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;'

    # Algemene configuratie
    script = "Bulk order toevoegen in BigQuery"
    klant = "Aard'g"
    bron = "python"
    script_id = 1
    
    # WooCommerce API configuratie
    wcapi = API(
        url=woocommerce_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        version="wc/v3",
        timeout=60
    )
    
    # Script ID bepalen
    start_time, script_id = set_script_id(greit_connection_string, klant, bron, "Script ID bepalen", script)
    print("Script ID:", script_id)
    
    # Jaar loop vanaf 2019
    for jaar in range(2020, 2025):
        
        # Periode bepalen
        periode_begin = f"{jaar}-01-01T00:00:00Z"
        periode_eind = f"{jaar}-12-31T23:59:59Z"
        page = 1  # Start met de eerste pagina
        total_orders = 0  # Row count voor dit jaar
        
        print(f"Script gestart voor jaar {jaar}")
        
        while True:
            # Orders ophalen met paginering
            response = wcapi.get("orders", params={
                "after": periode_begin,
                "before": periode_eind,
                "per_page": 100, # Maximaal 100 resultaten per pagina
                "page": page # Huidige pagina
            })
            
            print(f"Eerste {page * 100} orders opgehaald")
            
            if response.status_code != 200:
                log(greit_connection_string, klant, bron, f"FOUTMELDING: API response {response.status_code}", script, script_id, tabel=None)
                break
            orders = response.json()
            
            # Stop als er geen orders meer zijn
            if not orders:
                print(f"Geen orders meer gevonden voor jaar {jaar}")
                break

            # Data verwerken
            for order in orders:
                try:
                    insert_order_into_bigquery(
                        greit_connection_string,
                        klant,
                        script_id,
                        script,
                        order  
                    )
                    total_orders += 1  # Verhoog de row count bij succesvolle verwerking
                    print("Totaal aantal verwerkte orders:", total_orders)
                except Exception as e:
                    log(greit_connection_string, klant, bron, f"FOUTMELDING: {e}", script, script_id, tabel=None)
                    continue

            # Naar de volgende pagina
            page += 1

        # Print het totaal aantal orders voor dit jaar
        print(f"Totaal aantal verwerkte orders voor {jaar}: {total_orders}")

    # Script beëindigen
    end_log(start_time, greit_connection_string, klant, bron, script, script_id)

if __name__ == "__main__":
    main()