sku_dict = {
    'C12': [5411, 20231, 33842, 25271, 49063],
    'B12': [5409, 20232, 33843, 25270, 49061],
    'G12': [5415, 20229, 33841, 25272, 49064],
    'F12': [11389, 33840, 25279, 46959, 48040, 70847],
    'P28': [47389, 75021, 49056, 47390, 49057, 71418, 74402, 47391, 49065, 85862, 95670],
    'W4': [8580, 30311, 11155, 45348, 45351, 49060, 25278, 85964],
    'M4': [11385, 75172, 49055, 11159, 45350, 45355, 33838, 25274, 85962, 27305],
    'K4': [8579, 49054, 10371, 45347, 45353, 27304, 25276, 49059, 85963, 79885],
    'S': [5416, 45344, 33864, 47504]
}
def get_sku_from_product_id(product_id, sku_dict):
    for sku, product_ids in sku_dict.items():
        if product_id in product_ids:
            return sku
    return None

category_dict = {
    "normal": [
        8579, 8580, 11385, 47389, 75021, 75172, 5409, 5411, 5415, 11389, 5416, 10371,
        11155, 11159, 47390, 20229, 20231, 20232, 20233, 45347, 45348, 45350, 45351,
        45353, 45355, 30311, 49054, 49055, 49056, 79885
    ],
    "discount": [
        27304, 27305, 33838, 45345, 49057, 66469, 71418, 74402, 48040, 33840, 33841,
        33842, 33843, 70847, 45344, 33864, 85862, 85962, 85963, 85964, 95670
    ],
    "orderbump": [
        25274, 25276, 25278, 47391, 25270, 25271, 25272, 25279, 47504, 46959, 49061,
        49063, 49064, 49058, 49059, 49060, 49065
    ]
}

def get_category_from_product_id(product_id, category_dict):
    for category, product_ids in category_dict.items():
        if product_id in product_ids:
            return category
    return None

def update_field_values(current_fields, updates):
    for update in updates:
        for current_field in current_fields:
            if current_field['field'] == update['field']:
                current_field['value'] = int(current_field['value']) + int(update['value'])
    return current_fields