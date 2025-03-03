#!/bin/bash

# Check en start Redis als het niet draait
if ! systemctl is-active --quiet redis-server; then
    echo "Starting Redis server..."
    sudo systemctl start redis-server
fi

# Bestaande herstart procedure
sudo systemctl daemon-reload
sudo systemctl restart flaskapp
sudo systemctl status flaskapp 