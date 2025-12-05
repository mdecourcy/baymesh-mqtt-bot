#!/bin/bash
# Diagnose and recover the Meshtastic stats bot

set -e

BOT_HOST="root@192.168.8.114"
BOT_DIR="/opt/baymesh-mqtt-bot"

echo "=== Checking service status ==="
ssh $BOT_HOST "systemctl status meshtastic-stats-bot.service --no-pager" || true

echo ""
echo "=== Checking CPU and memory usage ==="
ssh $BOT_HOST "top -bn1 | grep -E 'python|uvicorn' | head -5" || true

echo ""
echo "=== Checking process details ==="
ssh $BOT_HOST "ps aux | grep -E 'python|uvicorn' | grep -v grep" || true

echo ""
echo "=== Last 50 lines of application logs ==="
ssh $BOT_HOST "tail -50 $BOT_DIR/logs/meshtastic_stats.log"

echo ""
echo "=== Last 50 lines of systemd logs ==="
ssh $BOT_HOST "journalctl -u meshtastic-stats-bot.service -n 50 --no-pager"

echo ""
echo "=== Recent errors in application logs ==="
ssh $BOT_HOST "grep -i 'error\|exception\|traceback' $BOT_DIR/logs/meshtastic_stats.log | tail -20" || echo "No recent errors found"

echo ""
read -p "Do you want to restart the service? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "=== Restarting service ==="
    ssh $BOT_HOST "systemctl restart meshtastic-stats-bot.service"
    sleep 3
    ssh $BOT_HOST "systemctl status meshtastic-stats-bot.service --no-pager"
    echo "Service restarted!"
fi

