def fetch_script_id(cursor):
    # Voer de query uit om het hoogste ScriptID op te halen
    query = 'SELECT MAX(ScriptID) FROM Logging'
    cursor.execute(query)
    
    # Verkrijg het resultaat
    highest_script_id = cursor.fetchone()[0]

    return highest_script_id