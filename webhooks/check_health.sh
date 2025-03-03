#!/bin/bash

# Health check uitvoeren
curl -s http://localhost:8443/health > /dev/null

# Log resultaat
if [ $? -eq 0 ]; then
    echo "$(date): Health check succesvol uitgevoerd"
else
    echo "$(date): Health check mislukt" >&2
fi 