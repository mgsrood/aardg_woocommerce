#!/bin/bash

# Bestaande herstart procedure
sudo systemctl daemon-reload
sudo systemctl restart webhook
sudo systemctl status webhook 