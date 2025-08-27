# Webhook Monitor

Een geautomatiseerde monitoring tool voor WooCommerce webhooks en system health monitoring.

## 🎯 Functionaliteiten

### Webhook Monitoring
- **Controleert status** van belangrijke webhooks
- **Heractiveerd automatisch** inactieve webhooks
- **Detecteert ontbrekende** webhooks
- **Logt alle acties** naar Azure SQL Database

### System Monitoring  
- **VM Health**: CPU, Memory, Disk usage
- **App Health**: Webhook applicatie responsiviteit
- **Network**: Connectivity tests
- **Alerts**: Automatische alerts bij problemen

### Monitored Webhooks
- Order Verwerking
- Abonnement Verwerking  
- Facebook Audience
- Product Velden
- Product Tags
- Abonnements Tag
- Abonnements Veld Ophogen
- Abonnements Veld Verlagen
- Besteldatum

## 📊 Azure SQL Database Tabellen

### WebhookMonitoring
Logs webhook status checks en heractivering acties:
- Webhook details (ID, naam, URL)
- Status wijzigingen
- Acties ondernomen (reactivated, failed, etc.)
- Response tijden
- Error details

### SystemMonitoring  
Logs system metrics en health checks:
- VM resources (CPU, Memory, Disk)
- App performance metrics
- API health checks
- Network latency

### MonitoringAlerts
Alerts voor kritieke situaties:
- Webhook down
- VM critical resources
- App errors
- API failures

## 🔧 Installatie

1. **Dependencies installeren:**
```bash
pip install -r requirements.txt
```

2. **Database setup:**
```sql
-- Voer uit in je Azure SQL Database
-- Zie sql/create_webhook_monitoring_tables.sql
```

3. **Environment configuratie:**
```bash
cp env_example.txt .env
# Vul de juiste waarden in
```

## ⚙️ Configuratie

### Vereiste Environment Variables
```bash
# WooCommerce API
WOOCOMMERCE_CONSUMER_KEY=your_key
WOOCOMMERCE_CONSUMER_SECRET=your_secret
WOOCOMMERCE_URL=https://www.aardg.nl

# Azure SQL Database  
AZURE_SQL_SERVER=your_server.database.windows.net
AZURE_SQL_DATABASE=your_database
AZURE_SQL_USERNAME=your_username
AZURE_SQL_PASSWORD=your_password

# Environment
ENVIRONMENT=development  # of 'production'
```

## 🚀 Gebruik

### Handmatige uitvoering
```bash
python main.py
```

### Geautomatiseerd (cron)
```bash
# Elke 5 minuten webhook monitoring
*/5 * * * * cd /path/to/webhook_monitor && python main.py

# Elke 15 minuten uitgebreide monitoring  
*/15 * * * * cd /path/to/webhook_monitor && python main.py
```

## 📈 Monitoring & Alerts

### Alert Types
- **webhook_down**: Webhook inactief of ontbreekt
- **vm_critical**: VM resources kritiek (>90% CPU/Memory)
- **app_error**: Webhook app niet bereikbaar
- **api_failure**: WooCommerce API problemen

### Alert Severity
- **low**: Informatief
- **medium**: Aandacht vereist
- **high**: Actie vereist
- **critical**: Directe actie nodig

## 🔍 Queries voor Monitoring

### Recent webhook status
```sql
SELECT TOP 50 
    CheckedAt, WebhookName, CurrentStatus, ActionTaken, ErrorMessage
FROM WebhookMonitoring 
ORDER BY CheckedAt DESC;
```

### System health trends
```sql
SELECT 
    MonitoredAt, CPUUsagePercent, MemoryUsagePercent, 
    AppResponseTime, Status
FROM SystemMonitoring 
WHERE MonitorType = 'vm_health'
ORDER BY MonitoredAt DESC;
```

### Active alerts
```sql
SELECT 
    TriggeredAt, AlertType, Severity, Title, Description
FROM MonitoringAlerts 
WHERE IsResolved = 0
ORDER BY Severity DESC, TriggeredAt DESC;
```

## 🛠 Onderhoud

- Monitor regelmatig de Azure SQL Database logs
- Controleer alerts voor kritieke situaties  
- Update dependencies regelmatig
- Test webhook heractivering functionaliteit

## 📞 Troubleshooting

### Webhook monitor faalt
1. Controleer WooCommerce API credentials
2. Verificeer netwerkconnectiviteit
3. Check Azure SQL Database verbinding

### System monitoring errors
1. Controleer psutil dependencies
2. Verificeer permissions voor system metrics
3. Test netwerkconnectiviteit

### Alerts niet zichtbaar
1. Controleer Azure SQL Database verbinding
2. Verificeer environment variables
3. Check SKIP_AZURE_SQL_LOGGING setting
