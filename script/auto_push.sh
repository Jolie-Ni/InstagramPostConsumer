#! /bin/bash

# Date in format Day-Month-Year
date=$(date +"%Y-%m-%d %T")

# Commit message
message="Commit for $date"
cd ~/Development/InstagramPostConsumer
git add .
git commit --allow-empty -m"${message}"
git push -u origin main
