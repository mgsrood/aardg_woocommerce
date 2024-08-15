import hmac
import hashlib
import base64
import os
from dotenv import load_dotenv

load_dotenv()

def generate_wc_signature(secret, payload):
    # Genereer de HMAC-SHA256 hash van de payload
    hmac_hash = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).digest()
    # Codeer de hash naar Base64
    return base64.b64encode(hmac_hash).decode()

secret = os.getenv('SECRET_KEY')  
payload = '''{
    "id": 100580,
    "parent_id": 100578,
    "status": "active",
    "currency": "EUR",
    "version": "9.1.2",
    "prices_include_tax": false,
    "date_created": "2024-08-14T10:27:32",
    "date_modified": "2024-08-14T10:30:18",
    "discount_total": "0.00",
    "discount_tax": "0.00",
    "shipping_total": "4.99",
    "shipping_tax": "0.00",
    "cart_tax": "0.00",
    "total": "34.98",
    "total_tax": "0.00",
    "customer_id": 13194,
    "order_key": "wc_order_Eg3EnKh9z9ztS",
    "billing": {
        "first_name": "Eugénie",
        "last_name": "de Meijer",
        "company": "",
        "address_1": "Reimersbeek 25",
        "address_2": "",
        "city": "Amsterdam",
        "state": "",
        "postcode": "1082 AE",
        "country": "NL",
        "email": "efdemeijer@gmail.com",
        "phone": "0612791059"
    },
    "shipping": {
        "first_name": "Eugénie",
        "last_name": "de Meijer",
        "company": "",
        "address_1": "Reimersbeek 25",
        "address_2": "",
        "city": "Amsterdam",
        "state": "",
        "postcode": "1082 AE",
        "country": "NL",
        "phone": "0612791059"
    },
    "payment_method": "mollie_wc_gateway_ideal",
    "payment_method_title": "iDEAL",
    "customer_ip_address": "62.195.194.238",
    "customer_user_agent": "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) GSA/328.0.658461140 Mobile/15E148 Safari/604.1",
    "created_via": "checkout",
    "customer_note": "",
    "date_completed": null,
    "date_paid": "2024-08-14T10:30:17",
    "number": "100580",
    "meta_data": [
        {
            "id": 4617702,
            "key": "affwp_submission_forms_hashes",
            "value": []
        },
        {
            "id": 4617753,
            "key": "_billing_street_name",
            "value": "Reimersbeek"
        },
        {
            "id": 4617754,
            "key": "_billing_house_number",
            "value": "25"
        },
        {
            "id": 4617755,
            "key": "_shipping_calculator",
            "value": ""
        },
        {
            "id": 4617756,
            "key": "_billing_house_number_suffix",
            "value": ""
        },
        {
            "id": 4617757,
            "key": "_wfob_report_data",
            "value": {
                "76870": {
                    "converted": 0,
                    "bid": 76870,
                    "total": 0,
                    "iid": "{}",
                    "fid": "1"
                }
            }
        },
        {
            "id": 4617758,
            "key": "_wfacp_report_data",
            "value": {
                "wfacp_total": 34.98,
                "funnel_id": "1"
            }
        },
        {
            "id": 4617759,
            "key": "_wffn_tracking_data",
            "value": {
                "utm_source": "",
                "utm_medium": "",
                "utm_campaign": "",
                "utm_term": "",
                "utm_content": "",
                "first_landing_url": "/winkel/",
                "browser": "Safari",
                "first_click": "2024-8-14 09:58:32",
                "device": "mobile",
                "click_id": "Cj0KCQjwq_G1BhCSARIsACc7NxoUhKEuOpX35Kz3166Cj0CgjT2xvt5KG4OsebUdksL7JKW715-2hNMaAsmQEALw_wcB",
                "referrer": "www.google.com",
                "journey": ""
            }
        },
        {
            "id": 4617760,
            "key": "es_wc_activecampaign_opt_in",
            "value": "no"
        },
        {
            "id": 4617761,
            "key": "_shipping_street_name",
            "value": "Reimersbeek"
        },
        {
            "id": 4617762,
            "key": "_shipping_house_number",
            "value": "25"
        },
        {
            "id": 4617763,
            "key": "_shipping_house_number_suffix",
            "value": ""
        },
        {
            "id": 4617764,
            "key": "_wc_order_attribution_source_type",
            "value": "organic"
        },
        {
            "id": 4617765,
            "key": "_wc_order_attribution_referrer",
            "value": "https://www.google.com/"
        },
        {
            "id": 4617766,
            "key": "_wc_order_attribution_utm_source",
            "value": "google"
        },
        {
            "id": 4617767,
            "key": "_wc_order_attribution_utm_medium",
            "value": "organic"
        },
        {
            "id": 4617768,
            "key": "_wc_order_attribution_session_entry",
            "value": "https://www.aardg.nl/winkel/"
        },
        {
            "id": 4617769,
            "key": "_wc_order_attribution_session_start_time",
            "value": "2024-08-14 08:27:53"
        },
        {
            "id": 4617770,
            "key": "_wc_order_attribution_session_pages",
            "value": "25"
        },
        {
            "id": 4617771,
            "key": "_wc_order_attribution_session_count",
            "value": "1"
        },
        {
            "id": 4617772,
            "key": "_wc_order_attribution_user_agent",
            "value": "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) GSA/328.0.658461140 Mobile/15E148 Safari/604.1"
        },
        {
            "id": 4617773,
            "key": "_wc_order_attribution_device_type",
            "value": "Mobile"
        },
        {
            "id": 4617774,
            "key": "_woofunnel_cid",
            "value": "14045"
        },
        {
            "id": 4617775,
            "key": "_wfacp_post_id",
            "value": "66240"
        },
        {
            "id": 4617776,
            "key": "_wfacp_source",
            "value": "https://www.aardg.nl/afrekenen/"
        },
        {
            "id": 4617777,
            "key": "_wfacp_timezone",
            "value": "Europe/Amsterdam"
        },
        {
            "id": 4617778,
            "key": "billing_house_number",
            "value": "25"
        },
        {
            "id": 4617779,
            "key": "billing_house_number_suffix",
            "value": ""
        },
        {
            "id": 4617780,
            "key": "billing_street_name",
            "value": "Reimersbeek"
        },
        {
            "id": 4617781,
            "key": "_mollie_order_id",
            "value": "ord_1.pkphx8"
        },
        {
            "id": 4617784,
            "key": "_mollie_customer_id",
            "value": "cst_b6qTxVzv4Z"
        },
        {
            "id": 4617785,
            "key": "_automatewoo_order_created",
            "value": "1"
        },
        {
            "id": 4617786,
            "key": "is_vat_exempt",
            "value": "no"
        },
        {
            "id": 4617787,
            "key": "automatewoo_cart_id",
            "value": "21617"
        }
    ],
    "line_items": [
        {
            "id": 148590,
            "name": "Probiotica Ampullen Abonnement (28x 9ml)",
            "product_id": 47390,
            "variation_id": 0,
            "quantity": 1,
            "tax_class": "",
            "subtotal": "29.99",
            "subtotal_tax": "0.00",
            "total": "29.99",
            "total_tax": "0.00",
            "taxes": [],
            "meta_data": [],
            "sku": "aP28",
            "price": 29.99,
            "image": {
                "id": "57549",
                "src": "https://www.aardg.nl/wp-content/uploads/2022/01/4.-Probiotica-Ampullen-Abonnement.jpg"
            },
            "parent_name": null
        }
    ],
    "tax_lines": [],
    "shipping_lines": [
        {
            "id": 148589,
            "method_title": "Vast tarief",
            "method_id": "flat_rate",
            "instance_id": "25",
            "total": "4.99",
            "total_tax": "0.00",
            "taxes": [],
            "meta_data": [
                {
                    "id": 1117639,
                    "key": "Artikelen",
                    "value": "Probiotica Ampullen Abonnement (28x 9ml) × 1",
                    "display_key": "Artikelen",
                    "display_value": "Probiotica Ampullen Abonnement (28x 9ml) × 1"
                }
            ]
        }
    ],
    "fee_lines": [],
    "coupon_lines": [],
    "payment_url": "https://www.aardg.nl/afrekenen/order-pay/100580/?pay_for_order=true&key=wc_order_Eg3EnKh9z9ztS",
    "is_editable": true,
    "needs_payment": false,
    "needs_processing": true,
    "date_created_gmt": "2024-08-14T08:27:32",
    "date_modified_gmt": "2024-08-14T08:30:18",
    "date_completed_gmt": null,
    "date_paid_gmt": "2024-08-14T08:30:17",
    "billing_period": "week",
    "billing_interval": "4",
    "trial_period": "",
    "suspension_count": 0,
    "requires_manual_renewal": false,
    "start_date_gmt": "2024-08-14T08:29:33",
    "trial_end_date_gmt": "",
    "next_payment_date_gmt": "2024-09-11T08:29:33",
    "payment_retry_date_gmt": "",
    "last_payment_date_gmt": "2024-08-14T08:27:32",
    "cancelled_date_gmt": "",
    "end_date_gmt": "",
    "resubscribed_from": "",
    "resubscribed_subscription": "",
    "removed_line_items": [],
    "_links": {
        "self": [
            {
                "href": "https://www.aardg.nl/wp-json/wc/v3/subscriptions/100580"
            }
        ],
        "collection": [
            {
                "href": "https://www.aardg.nl/wp-json/wc/v3/subscriptions"
            }
        ],
        "customer": [
            {
                "href": "https://www.aardg.nl/wp-json/wc/v3/customers/13194"
            }
        ],
        "up": [
            {
                "href": "https://www.aardg.nl/wp-json/wc/v3/orders/100578"
            }
        ]
    }
}
'''

signature = generate_wc_signature(secret, payload)
print(signature)