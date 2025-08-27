import json
import os
from functools import lru_cache
import logging

# Constants voor product categorieën
CATEGORIES = {
    'Challenge': ['CHAL'],
    'Originals': ['P28', 'P56', 'K4', 'K8', 'W4', 'W8', 'M4', 'M8', 'P-', 'K-', 'W-', 'M-', 
                 '8719327215180', '8719326399386', '8719326399393', '8719327215135'],
    'Frisdrank': ['F12', 'B12', 'C12', 'G12', 'F-', 'B-', 'C-', 'G-', 
                 '8719326399355', '8719326399362', '8719326399379', '8719327215128'],
    'Starter': ['Starter', 'S-', '8719327215111', 'S-ACTIE_X']
}

DISCOUNT_KEYWORDS = ['ACTIE', 'X2', 'XL', 'korting', '-A', '-B', 'K8', 'M8', 'W8', 
                    '56', 'halfjaar', 'jaar', 'X2', 'S-ACTIE_X']

BASE_UNIT_VALUES = {
    '1': ['K4', 'K-', 'W4', 'W-', 'M4', 'M-', 'P28', 'S', 'F12', 'B12', 'C12', 'G12', 
          'Starter', '8719327215111', '8719327215180', '8719326399386', '8719326399393', 
          '8719327215135', '8719326399355', '8719326399362', '8719326399379', 
          '8719327215128', 'S-ACTIE_X'],
    '2': ['W8', 'K8', 'M8', 'P56', 'M-XL', 'X2', 'C2', 'S-XL'],
    '3': ['MP-XL', 'F-XL'],
    '6': ['halfjaar'],
    '12': ['jaar']
}

SKU_CATEGORIES = {
    'K4': ['K4', 'K8', 'K-', '8719326399386'],
    'W4': ['W4', 'W8', 'W-', '8719326399393'],
    'M4': ['M4', 'M8', 'M-', '8719327215135', 'MP-XL'],
    'P28': ['P28', 'P56', 'P-', '8719327215180', 'X2', 'C2'],
    'S': ['Starter', 'S-', '8719327215111', 'S-XL', 'S-ACTIE_X'],
    'F12': ['F12', 'F-', '8719327215128', 'F-X2', 'F-XL'],
    'B12': ['B12', 'B-', '8719326399362'],
    'C12': ['C12', 'C-', '8719326399355'],
    'G12': ['G12', 'G-', '8719326399379']
}

@lru_cache(maxsize=1)
def get_file_path():
    """Retourneert het pad naar het product catalogus bestand."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, '..', 'data', 'product_catalog.json')

@lru_cache(maxsize=1)
def load_catalogue():
    """Laadt de product catalogus en cached het resultaat."""
    try:
        with open(get_file_path(), 'r') as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Product catalogus niet gevonden op: {get_file_path()}")
    except json.JSONDecodeError:
        raise ValueError(f"Ongeldig JSON formaat in product catalogus: {get_file_path()}")

def _build_dict_from_categories(categories, product_catalogue):
    """Bouwt een dictionary op basis van categorieën en product catalogus."""
    result = {category: [] for category in categories}
    
    for sku, product_id in product_catalogue.items():
        for category, keywords in categories.items():
            if any(keyword in sku for keyword in keywords):
                result[category].append(product_id)
                break
    
    return result

@lru_cache(maxsize=1)
def get_category_one_dict():
    """Retourneert een dictionary met product IDs per categorie."""
    return _build_dict_from_categories(CATEGORIES, load_catalogue())

@lru_cache(maxsize=1)
def get_discount_dict():
    """Retourneert een dictionary met product IDs voor kortingen."""
    product_catalogue = load_catalogue()
    return {
        'Discount': [
            product_id for sku, product_id in product_catalogue.items()
            if any(keyword in sku for keyword in DISCOUNT_KEYWORDS)
        ]
    }

@lru_cache(maxsize=1)
def get_base_unit_values():
    """Retourneert een dictionary met product IDs per basis eenheid."""
    return _build_dict_from_categories(BASE_UNIT_VALUES, load_catalogue())

@lru_cache(maxsize=1)
def get_sku_dict():
    """Retourneert een dictionary met product IDs per SKU categorie."""
    return _build_dict_from_categories(SKU_CATEGORIES, load_catalogue())

def get_key_from_product_id(product_id, category_dict):
    """Vindt de categorie key voor een gegeven product ID."""
    try:
        product_id = int(product_id)
        logging.info(f"Zoek categorie voor product ID: {product_id}")
        logging.info(f"Beschikbare categorieën: {list(category_dict.keys())}")
        for key, product_ids in category_dict.items():
            logging.info(f"Categorie {key} bevat product IDs: {product_ids}")
            if product_id in product_ids:
                logging.info(f"Product ID {product_id} gevonden in categorie {key}")
                return key
        logging.warning(f"Product ID {product_id} niet gevonden in category_dict")
    except (ValueError, TypeError):
        logging.warning(f"Ongeldig product ID formaat: {product_id}")
    return None

def determine_base_product(sku):
    """Bepaalt het basis product op basis van SKU."""
    sku = sku.upper()
    
    if any(substring in sku for substring in SKU_CATEGORIES['S']):
        return 'Starter'
    elif any(substring in sku for substring in SKU_CATEGORIES['P28']):
        return 'Probiotica'
    elif any(substring in sku for substring in SKU_CATEGORIES['W4']):
        return 'Waterkefir'
    elif any(substring in sku for substring in SKU_CATEGORIES['K4']):
        return 'Kombucha'
    elif any(substring in sku for substring in SKU_CATEGORIES['M4']):
        return 'Mix Originals'
    elif any(substring in sku for substring in SKU_CATEGORIES['G12']):
        return 'Gember'
    elif any(substring in sku for substring in SKU_CATEGORIES['C12']):
        return 'Citroen'
    elif any(substring in sku for substring in SKU_CATEGORIES['B12']):
        return 'Bloem'
    elif any(substring in sku for substring in SKU_CATEGORIES['F12']):
        return 'Frisdrank Mix'
    return 'unknown'