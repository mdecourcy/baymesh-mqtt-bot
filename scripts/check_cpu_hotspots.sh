#!/bin/bash
# Check for CPU hotspots in the running bot

BOT_HOST="root@192.168.8.114"

echo "=== Python processes and their CPU usage ==="
ssh $BOT_HOST "ps aux | grep python | grep -v grep | awk '{print \$2, \$3, \$11}' | column -t"

echo ""
echo "=== Top 10 threads by CPU ==="
ssh $BOT_HOST "ps -eLo pid,tid,class,rtprio,ni,pri,psr,pcpu,stat,wchan:14,comm | grep -E 'python|uvicorn' | sort -k8 -r | head -10"

echo ""
echo "=== Database connections ==="
ssh $BOT_HOST "lsof -p \$(pgrep -f 'python.*main.py' | head -1) 2>/dev/null | grep -c 'meshtastic_stats.db'" || echo "Could not check"

echo ""
echo "=== Network connections ==="
ssh $BOT_HOST "netstat -anp 2>/dev/null | grep -E 'python|uvicorn' | wc -l"

echo ""
echo "=== Memory usage ==="
ssh $BOT_HOST "ps aux | grep 'python.*main.py' | grep -v grep | awk '{print \"RSS:\", \$6/1024, \"MB\", \"VSZ:\", \$5/1024, \"MB\"}'"

