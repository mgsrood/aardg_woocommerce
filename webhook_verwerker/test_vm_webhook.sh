#!/bin/bash

# VM Webhook Test Script
# Test webhook endpoints op je VM

# Configuratie - PAS DIT AAN VOOR JOUW VM
VM_HOST="your-vm-ip-or-domain"  # Vervang met jouw VM IP of domein
PORT="8443"
SECRET_KEY="your-secret-key"    # Vervang met jouw WooCommerce webhook secret

# Kleuren voor output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🧪 VM Webhook Test Suite"
echo "========================"
echo "VM Host: $VM_HOST:$PORT"
echo ""

# Test payload - WooCommerce Order
PAYLOAD='{
  "id": 12345,
  "number": "12345",
  "order_key": "wc_order_abc123",
  "created_via": "checkout",
  "status": "completed",
  "currency": "EUR",
  "date_created": "2025-01-08T10:00:00",
  "date_modified": "2025-01-08T10:30:00",
  "discount_total": "0.00",
  "discount_tax": "0.00",
  "shipping_total": "5.00",
  "shipping_tax": "1.05",
  "cart_tax": "4.20",
  "total": "29.25",
  "total_tax": "5.25",
  "customer_id": 67890,
  "billing": {
    "first_name": "Jan",
    "last_name": "Jansen",
    "company": "",
    "address_1": "Teststraat 123",
    "address_2": "",
    "city": "Amsterdam",
    "state": "NH",
    "postcode": "1000 AA",
    "country": "NL",
    "email": "jan.jansen@test.nl",
    "phone": "0612345678"
  },
  "shipping": {
    "first_name": "Jan",
    "last_name": "Jansen",
    "company": "",
    "address_1": "Teststraat 123",
    "address_2": "",
    "city": "Amsterdam",
    "state": "NH",
    "postcode": "1000 AA",
    "country": "NL"
  },
  "payment_method": "ideal",
  "payment_method_title": "iDEAL",
  "transaction_id": "tr_abc123def456",
  "line_items": [
    {
      "id": 1,
      "name": "Aardg W4 Supplement",
      "product_id": 100,
      "variation_id": 0,
      "quantity": 2,
      "tax_class": "",
      "subtotal": "20.00",
      "subtotal_tax": "4.20",
      "total": "24.20",
      "total_tax": "4.20"
    }
  ]
}'

# Functie om signature te genereren (vereist openssl)
generate_signature() {
    local payload="$1"
    local secret="$2"
    echo -n "$payload" | openssl dgst -sha256 -hmac "$secret" -binary | base64
}

# Test functie
test_endpoint() {
    local endpoint="$1"
    local needs_signature="$2"
    local description="$3"
    
    echo -e "${BLUE}🚀 Testing:${NC} $description"
    echo -e "${YELLOW}Endpoint:${NC} $endpoint"
    
    # Basis headers
    local headers=(
        -H "Content-Type: application/json"
        -H "User-Agent: WooCommerce/Test"
    )
    
    # Voeg signature toe indien nodig
    if [ "$needs_signature" = "true" ]; then
        signature=$(generate_signature "$PAYLOAD" "$SECRET_KEY")
        headers+=(-H "X-WC-Webhook-Signature: $signature")
        echo -e "${YELLOW}Signature:${NC} $signature"
    fi
    
    echo ""
    
    # Verstuur request
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        "http://$VM_HOST:$PORT$endpoint" \
        "${headers[@]}" \
        -d "$PAYLOAD" \
        --connect-timeout 10 \
        --max-time 30)
    
    # Parse response
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    # Toon resultaat
    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✅ SUCCESS${NC} (HTTP $http_code)"
    else
        echo -e "${RED}❌ FAILED${NC} (HTTP $http_code)"
    fi
    
    if [ -n "$response_body" ]; then
        echo -e "${YELLOW}Response:${NC} $response_body"
    fi
    
    echo ""
    echo "----------------------------------------"
    echo ""
}

# Check of openssl beschikbaar is
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}❌ OpenSSL is vereist voor signature generatie${NC}"
    echo "Installeer met: sudo apt install openssl (Ubuntu) of brew install openssl (macOS)"
    exit 1
fi

# Test verschillende endpoints
echo "🧪 Testing webhook endpoints..."
echo ""

# Test 1: Health check (geen signature)
test_endpoint "/" false "Health Check"

# Test 2: WooCommerce Order (met signature)
test_endpoint "/woocommerce/order" true "WooCommerce Order Webhook"

# Test 3: WooCommerce Subscription (met signature)  
test_endpoint "/woocommerce/subscription" true "WooCommerce Subscription Webhook"

# Test 4: ActiveCampaign (geen signature meestal)
test_endpoint "/activecampaign/deal" false "ActiveCampaign Deal Webhook"

echo -e "${GREEN}🎉 Test suite voltooid!${NC}"
echo ""
echo -e "${YELLOW}💡 Tips:${NC}"
echo "• Controleer VM logs met: sudo journalctl -u webhook.service -f"
echo "• Vervang VM_HOST en SECRET_KEY in dit script met jouw waarden"
echo "• Voeg meer endpoints toe als je die wilt testen"