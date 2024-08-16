import json
import os

def load_catalogue_from_json(file_path):
    with open(file_path, 'r') as json_file:
        return json.load(json_file)

def get_file_path():
    # Vind het absolute pad van het JSON-bestand
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, '..', 'data', 'product_catalog.json')
    return file_path

def get_category_one_dict():
    # File path
    file_path = get_file_path()

    # Catalogus laden
    product_catalogue = load_catalogue_from_json(file_path)

    # Category dictionary
    category_one_dict = {
        'Challenge': [],
        'Originals': [],
        'Starter': [],
        'Frisdrank': [],
        }

    challenge = ['CHAL']
    originals = ['P28', 'P56', 'K4', 'K8', 'W4', 'W8', 'M4', 'M8', 'P-', 'K-', 'W-', 'M-', '8719327215180', '8719326399386', '8719326399393', '8719327215135']
    frisdrank = ['F12', 'B12', 'C12', 'G12', 'F-', 'B-', 'C-', 'G-', '8719326399355', '8719326399362', '8719326399379', '8719327215128']
    starter = ['Starter', 'S-', '8719327215111']

    for sku, id in product_catalogue.items():
        if any(sub in sku for sub in challenge):
            category_one_dict['Challenge'].append(id)
        elif any(sub in sku for sub in originals):
            category_one_dict['Originals'].append(id)
        elif any(sub in sku for sub in frisdrank):
            category_one_dict['Frisdrank'].append(id)
        elif any(sub in sku for sub in starter):
            category_one_dict['Starter'].append(id)

    return category_one_dict

def get_discount_dict():
    # File path
    file_path = get_file_path()

    # Catalogus laden
    product_catalogue = load_catalogue_from_json(file_path)

    # Category dictionary
    discount_dict = {
        'Discount': [],
        }

    discount = ['ACTIE', 'X2', 'XL', 'korting', '-A', '-B', 'K8', 'M8', 'W8', '56', 'halfjaar', 'jaar', 'X2']

    for sku, id in product_catalogue.items():
        if any(sub in sku for sub in discount):
            discount_dict['Discount'].append(id)
        else:
            None

    return discount_dict

def get_base_unit_values():
    # File path
    file_path = get_file_path()

    # Catalogus laden
    product_catalogue = load_catalogue_from_json(file_path)

    # Value dictionary
    base_unit_values_dict= {
        '1': [],
        '2': [],
        '3': [],
        '4': [],
        '5': [],
        '6': [],
        '12': [],
    }

    one = ['K4', 'K-', 'W4', 'W-', 'M4', 'M-', 'P28', 'S', 'F12', 'B12', 'C12', 'G12', 'Starter', '8719327215111', '8719327215180', '8719326399386', '8719326399393', '8719327215135', '8719326399355', '8719326399362', '8719326399379', '8719327215128'   ]
    two = ['W8', 'K8','M8', 'P56', 'M-XL', 'X2', 'C2', 'S-XL']
    three = ['MP-XL', 'F-XL']
    six = ['halfjaar']
    twelve = ['jaar']

    for sku, id in product_catalogue.items():
        if any(sub in sku for sub in twelve):
            base_unit_values_dict['12'].append(id)
        elif any(sub in sku for sub in six):
            base_unit_values_dict['6'].append(id)
        elif any(sub in sku for sub in three):
            base_unit_values_dict['3'].append(id)
        elif any(sub in sku for sub in two):
            base_unit_values_dict['2'].append(id)
        elif any(sub in sku for sub in one):
            base_unit_values_dict['1'].append(id)

    return base_unit_values_dict

def get_sku_dict():
    # File path
    file_path = get_file_path()

    # Catalogus laden
    product_catalogue = load_catalogue_from_json(file_path)

    # SKU dictionary
    sku_dict = {
        'K4': [],
        'W4': [],
        'M4': [],
        'P28': [],
        'S': [],
        'F12': [],
        'B12': [],
        'C12': [],
        'G12': [],
        }

    k4 = ['K4', 'K8', 'K-', '8719326399386']
    w4 = ['W4', 'W8','W-', '8719326399393']
    m4 = ['M4', 'M8', 'M-', '8719327215135', 'MP-XL']
    p28 = ['P28', 'P56', 'P-', '8719327215180', 'X2', 'C2']
    s = ['Starter', 'S-', '8719327215111', 'S-XL']
    f12 = ['F12', 'F-', '8719327215128', 'F-X2', 'F-XL']
    b12 = ['B12', 'B-', '8719326399362']
    c12 = ['C12', 'C-', '8719326399355']
    g12 = ['G12', 'G-', '8719326399379']

    for sku, id in product_catalogue.items():
        if any(sub in sku for sub in k4):
            sku_dict['K4'].append(id)
        elif any(sub in sku for sub in w4):
            sku_dict['W4'].append(id)
        elif any(sub in sku for sub in m4):
            sku_dict['M4'].append(id)
        elif any(sub in sku for sub in p28):
            sku_dict['P28'].append(id)
        elif any(sub in sku for sub in s):
            sku_dict['S'].append(id)
        elif any(sub in sku for sub in f12):
            sku_dict['F12'].append(id)
        elif any(sub in sku for sub in b12):
            sku_dict['B12'].append(id)
        elif any(sub in sku for sub in c12):
            sku_dict['C12'].append(id)
        elif any(sub in sku for sub in g12):
            sku_dict['G12'].append(id)

    return sku_dict

def get_key_from_product_id(product_id, dict):
    for key, product_ids in dict.items():
        if product_id in product_ids:
            return key
    return None

def determine_base_product(sku):
    # Base product op basis van SKU
    if any(substring in sku for substring in ['Starter', 'S-', '8719327215111', 'S-XL']):
        return 'Starter'
    elif any(substring in sku for substring in ['P28', 'P56', 'P-', '8719327215180', 'X2', 'C2']):
        return 'Probiotica'
    elif any(substring in sku for substring in ['W4', 'W8','W-', '8719326399393']):
        return 'Waterkefir'
    elif any(substring in sku for substring in ['K4', 'K8', 'K-', '8719326399386']):
        return 'Kombucha'
    elif any(substring in sku for substring in ['M4', 'M8', 'M-', '8719327215135', 'MP-XL']):
        return 'Mix Originals'
    elif any(substring in sku for substring in ['G12', 'G-', '8719326399379']):
        return 'Gember'
    elif any(substring in sku for substring in ['C12', 'C-', '8719326399355']):
        return 'Citroen'
    elif any(substring in sku for substring in ['B12', 'B-', '8719326399362']):
        return 'Bloem'
    elif any(substring in sku for substring in ['F12', 'F-', '8719327215128', 'F-X2', 'F-XL']):
        return 'Frisdrank Mix'
    else:
        return 'Onbekend' 