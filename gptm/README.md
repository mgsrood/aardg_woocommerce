# GP TeamManager AI Assistant

Een AI-powered assistent voor het optimaliseren van je GP TeamManager team. Dit systeem helpt je bij het maken van de beste keuzes voor je team, gebaseerd op verschillende factoren zoals:

- Historische prestaties
- Circuit-specifieke prestaties
- Betrouwbaarheid
- Prijs/prestatie verhouding
- Kwalificatie prestaties

## Installatie

1. Zorg dat Python 3.8+ is geïnstalleerd
2. Installeer de benodigde packages:
```bash
pip install -r requirements.txt
```

## Configuratie

In `config/config.py` kun je verschillende instellingen aanpassen:
- Totaal beschikbaar budget
- Maximum aantal coureurs
- Scoring systeem
- Gewichten voor verschillende prestatie-factoren

## Gebruik

Start het programma:
```bash
python -m src.main
```

Het programma biedt de volgende functionaliteiten:

1. **Genereer optimaal team**
   - Analyseert alle beschikbare coureurs
   - Houdt rekening met budget beperkingen
   - Optimaliseert voor verwachte punten

2. **Voeg nieuwe coureur toe**
   - Voeg handmatig nieuwe coureurs toe aan het systeem
   - Vereiste informatie: ID, naam, team, prijs

3. **Update coureur data**
   - Werk bestaande coureur informatie bij
   - Update prijzen, punten, en andere statistieken

## Data Structuur

Coureur data wordt opgeslagen in JSON formaat in de `data` directory. Het systeem houdt bij:
- Basis informatie (naam, team, prijs)
- Historische prestaties
- Circuit-specifieke prestaties
- Betrouwbaarheidsscores
- Kwalificatie prestaties

## Optimalisatie Strategie

Het systeem gebruikt verschillende factoren om coureurs te evalueren:
1. Recente resultaten (60% gewicht)
2. Historische prestaties op specifieke circuits (30% gewicht)
3. Kwalificatie prestaties (10% gewicht)

Deze scores worden vermenigvuldigd met een betrouwbaarheidsfactor om risico's mee te wegen.

## Toekomstige Verbeteringen

- Automatische data updates van race resultaten
- Machine learning model voor prestatie voorspellingen
- Web interface voor makkelijker gebruik
- Integratie met externe F1 data bronnen
- Ondersteuning voor team constructeurs
- Analyse van weer impact op prestaties

## Bijdragen

Voel je vrij om bij te dragen aan dit project door:
1. Issues te melden
2. Feature requests in te dienen
3. Pull requests te maken met verbeteringen

## Licentie

MIT License - Zie LICENSE bestand voor details 