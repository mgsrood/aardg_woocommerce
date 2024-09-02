import json

# De input string
input_string = '''{\"id\":13238,\"date_created\":\"2024-09-02T10:48:41\",\"date_created_gmt\":\"2024-09-02T08:48:41\",\"date_modified\":\"2024-09-02T10:48:42\",\"date_modified_gmt\":\"2024-09-02T08:48:42\",\"email\":\"max@greit.nl\",\"first_name\":\"Max\",\"last_name\":\"Rood\",\"role\":\"customer\",\"username\":\"M.Greit\",\"billing\":{\"first_name\":\"\",\"last_name\":\"\",\"company\":\"\",\"address_1\":\"\",\"address_2\":\"\",\"city\":\"\",\"postcode\":\"\",\"country\":\"\",\"state\":\"\",\"email\":\"\",\"phone\":\"\"},\"shipping\":{\"first_name\":\"\",\"last_name\":\"\",\"company\":\"\",\"address_1\":\"\",\"address_2\":\"\",\"city\":\"\",\"postcode\":\"\",\"country\":\"\",\"state\":\"\",\"phone\":\"\"},\"is_paying_customer\":false,\"avatar_url\":\"https:\\/\\/secure.gravatar.com\\/avatar\\/66a6bb410d1f12e588a78f88bf033849?s=96&d=blank&r=g\",\"meta_data\":[{\"id\":891146,\"key\":\"_wcs_subscription_ids_cache\",\"value\":[]},{\"id\":891147,\"key\":\"_yoast_wpseo_profile_updated\",\"value\":\"1725266921\"},{\"id\":891148,\"key\":\"_aw_user_registered\",\"value\":\"1\"},{\"id\":891150,\"key\":\"aim\",\"value\":\"\"},{\"id\":891151,\"key\":\"yim\",\"value\":\"\"},{\"id\":891152,\"key\":\"jabber\",\"value\":\"\"}],\"_links\":{\"self\":[{\"href\":\"https:\\/\\/www.aardg.nl\\/wp-json\\/wc\\/v3\\/customers\\/13238\"}],\"collection\":[{\"href\":\"https:\\/\\/www.aardg.nl\\/wp-json\\/wc\\/v3\\/customers\"}]}}'''

# Stap 1: Escape de backslashes
escaped_string = input_string.replace(r'\/', '/').replace(r'\\u', '\\u')

# Stap 2: Omzetten naar een Python dict (JSON-parsen)
json_data = json.loads(escaped_string)

# Stap 3: Mooi geformatteerde JSON-string maken
pretty_json = json.dumps(json_data, indent=4)

# Print de geformatteerde JSON
print(pretty_json)
