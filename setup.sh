#!/bin/bash

# =================================================================
# AUTO SETUP SCRIPT FOR DEBIAN SERVER (TELEGRAM BOT)
# =================================================================

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (use sudo ./setup.sh)"
  exit
fi

# Configuration
APP_NAME="bottele"
PROJECT_DIR=$(pwd)
PYTHON_EXEC="/usr/bin/python3"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
USER_NAME=$(logname || echo $USER)

echo "--- Starting Setup for $APP_NAME ---"

# 1. Update and Install System Dependencies
echo "1. Updating system and installing dependencies..."
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git

# 2. Setup Virtual Environment
echo "2. Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON_EXEC -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# 3. Install Python Requirements
echo "3. Installing requirements from requirements.txt..."
if [ -f "requirements.txt" ]; then
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
else
    echo "WARNING: requirements.txt not found!"
fi

# 4. Create Systemd Service File
echo "4. Creating Systemd service file..."
cat <<EOF > $SERVICE_FILE
[Unit]
Description=Telegram Bot Service ($APP_NAME)
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=$APP_NAME

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created at $SERVICE_FILE"

# 5. Start and Enable Service
echo "5. Starting and enabling the service..."
systemctl daemon-reload
systemctl enable $APP_NAME
systemctl restart $APP_NAME

echo "--- Setup Complete! ---"
echo "You can check the status using: systemctl status $APP_NAME"
echo "To view logs, use: journalctl -u $APP_NAME -f"

# Initial Status Check
systemctl status $APP_NAME --no-pager
