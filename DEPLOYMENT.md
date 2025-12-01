# Deployment Guide

## Docker Compose Deployment (Recommended)

### Prerequisites

On your Proxmox container:
```bash
sudo apt update
sudo apt install docker.io docker-compose git -y
sudo systemctl enable docker
sudo systemctl start docker
```

### Deployment Steps

1. **Clone the repository**:
   ```bash
   cd /opt
   sudo git clone <your-repo-url> meshtastic-mqtt-bot
   cd meshtastic-mqtt-bot
   ```

2. **Create your environment file**:
   ```bash
   sudo nano .env.heltec
   ```
   
   Paste your configuration (see `.env.heltec.example` for reference).

3. **Create necessary directories**:
   ```bash
   sudo mkdir -p logs
   sudo touch meshtastic_stats.db
   ```

4. **Build and start the container**:
   ```bash
   sudo docker-compose up -d
   ```

5. **View logs**:
   ```bash
   sudo docker-compose logs -f
   ```

6. **Check status**:
   ```bash
   sudo docker-compose ps
   ```

### Updating the Bot

```bash
cd /opt/meshtastic-mqtt-bot
sudo git pull
sudo docker-compose up -d --build
```

### Stopping the Bot

```bash
sudo docker-compose down
```

### Accessing the Dashboard

Open your browser to: `http://<proxmox-container-ip>:8000`

---

## Systemd Service Deployment (Alternative)

### Prerequisites

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv git -y
```

### Installation

1. **Clone and setup**:
   ```bash
   cd /opt
   sudo git clone <your-repo-url> meshtastic-mqtt-bot
   cd meshtastic-mqtt-bot
   sudo python3 -m venv venv
   sudo venv/bin/pip install -r requirements.txt
   ```

2. **Create environment file**:
   ```bash
   sudo nano .env.heltec
   ```

3. **Create systemd service**:
   ```bash
   sudo nano /etc/systemd/system/meshtastic-bot.service
   ```
   
   Paste:
   ```ini
   [Unit]
   Description=Meshtastic MQTT Bot
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/opt/meshtastic-mqtt-bot
   Environment="MESHTASTIC_ENV_FILE=/opt/meshtastic-mqtt-bot/.env.heltec"
   ExecStart=/opt/meshtastic-mqtt-bot/venv/bin/python main.py
   Restart=always
   RestartSec=10
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable and start**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable meshtastic-bot
   sudo systemctl start meshtastic-bot
   ```

5. **Check status**:
   ```bash
   sudo systemctl status meshtastic-bot
   ```

6. **View logs**:
   ```bash
   sudo journalctl -u meshtastic-bot -f
   ```

### Updating the Bot

```bash
cd /opt/meshtastic-mqtt-bot
sudo git pull
sudo venv/bin/pip install -r requirements.txt
sudo systemctl restart meshtastic-bot
```

---

## Nginx Reverse Proxy (Optional)

If you want to access the dashboard via a domain name with HTTPS:

1. **Install Nginx**:
   ```bash
   sudo apt install nginx certbot python3-certbot-nginx -y
   ```

2. **Create Nginx config**:
   ```bash
   sudo nano /etc/nginx/sites-available/meshtastic-bot
   ```
   
   Paste:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection 'upgrade';
           proxy_set_header Host $host;
           proxy_cache_bypass $http_upgrade;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Enable the site**:
   ```bash
   sudo ln -s /etc/nginx/sites-available/meshtastic-bot /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

4. **Get SSL certificate**:
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

---

## Troubleshooting

### Check if the bot is running
```bash
# Docker
sudo docker-compose ps

# Systemd
sudo systemctl status meshtastic-bot
```

### View logs
```bash
# Docker
sudo docker-compose logs -f

# Systemd
sudo journalctl -u meshtastic-bot -f

# Log files (both methods)
tail -f logs/meshtastic_bot.log
```

### Check if port 8000 is listening
```bash
sudo netstat -tlnp | grep 8000
# or
sudo ss -tlnp | grep 8000
```

### Restart the bot
```bash
# Docker
sudo docker-compose restart

# Systemd
sudo systemctl restart meshtastic-bot
```

### Database issues
If you need to wipe and restart:
```bash
# Docker
sudo docker-compose down
sudo rm meshtastic_stats.db
sudo touch meshtastic_stats.db
sudo docker-compose up -d

# Systemd
sudo systemctl stop meshtastic-bot
sudo rm /opt/meshtastic-mqtt-bot/meshtastic_stats.db
sudo systemctl start meshtastic-bot
```

---

## Monitoring

### Check bot health
```bash
curl http://localhost:8000/health
```

### Check recent messages
```bash
curl http://localhost:8000/messages/detailed?limit=10 | jq
```

### Check bot stats
```bash
curl http://localhost:8000/bot/stats | jq
```

---

## Firewall Configuration

If you have a firewall enabled:

```bash
# UFW
sudo ufw allow 8000/tcp

# iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

