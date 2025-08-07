#!/bin/bash

# Webhook Verwerker Test Runner
# Dit script start de applicatie en voert de webhook tests uit

set -e

echo "🧪 WooCommerce Webhook Verwerker Test Suite"
echo "============================================="

# Kleuren voor output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functies
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check of Python en pip beschikbaar zijn
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 is niet geïnstalleerd"
    exit 1
fi

# Check of de applicatie bestanden bestaan
if [ ! -f "app.py" ]; then
    log_error "app.py niet gevonden. Voer dit script uit vanuit de project root."
    exit 1
fi

# Laad environment variabelen (gebruik bestaande .env)
if [ -f ".env" ]; then
    log_info "Laden van environment variabelen uit .env..."
    export $(cat .env | grep -v '^#' | xargs)
elif [ -f ".env.test" ]; then
    log_info "Laden van test environment variabelen uit .env.test..."
    export $(cat .env.test | grep -v '^#' | xargs)
else
    log_warning "Geen .env bestand gevonden. Gebruik default test waardes."
fi

# Installeer dependencies als requirements.txt bestaat
if [ -f "requirements.txt" ]; then
    log_info "Installeren van Python dependencies..."
    pip3 install -r requirements.txt > /dev/null 2>&1 || {
        log_error "Fout bij installeren van dependencies"
        exit 1
    }
fi

# Stop eventuele bestaande processen op poort 8443
log_info "Stoppen van bestaande processen op poort 8443..."
existing_pids=$(lsof -ti :8443 2>/dev/null || true)
if [ ! -z "$existing_pids" ]; then
    echo "$existing_pids" | xargs kill -9 2>/dev/null || true
    log_info "Bestaande processen gestopt: $existing_pids"
    sleep 2
fi

# Start de applicatie op de achtergrond
log_info "Starten van de webhook applicatie..."
python3 app.py &
APP_PID=$!

# Wacht tot de applicatie gestart is
log_info "Wachten tot applicatie beschikbaar is..."
sleep 3

# Check of de applicatie draait
if ! curl -s http://localhost:8443 > /dev/null 2>&1; then
    # Probeer nog een keer na 5 seconden
    sleep 5
    if ! curl -s http://localhost:8443 > /dev/null 2>&1; then
        log_error "Applicatie is niet bereikbaar op http://localhost:8443"
        kill $APP_PID 2>/dev/null || true
        exit 1
    fi
fi

log_success "Applicatie is gestart (PID: $APP_PID)"

# Cleanup functie
cleanup() {
    log_info "Stoppen van de applicatie..."
    kill $APP_PID 2>/dev/null || true
    wait $APP_PID 2>/dev/null || true
    log_success "Cleanup voltooid"
}

# Zorg ervoor dat cleanup wordt uitgevoerd bij exit
trap cleanup EXIT INT TERM

# Voer de webhook tests uit
log_info "Uitvoeren van webhook tests..."
echo ""

# Test alle endpoints
python3 test_webhooks.py "$@"

echo ""
log_success "Test suite voltooid!"