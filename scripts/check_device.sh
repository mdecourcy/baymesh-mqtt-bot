#!/bin/bash

# Diagnostic script to check Meshtastic device connectivity

DEVICE_IP="192.168.8.182"
DEVICE_PORT="4403"

echo "=== Meshtastic Device Connectivity Check ==="
echo ""

echo "1. Checking if device IP is reachable..."
if ping -c 2 -W 2 $DEVICE_IP > /dev/null 2>&1; then
    echo "   ✓ Device responds to ping"
else
    echo "   ✗ Device does not respond to ping (may be normal if ICMP is blocked)"
fi
echo ""

echo "2. Checking if TCP port $DEVICE_PORT is open..."
if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$DEVICE_IP/$DEVICE_PORT" 2>/dev/null; then
    echo "   ✓ Port $DEVICE_PORT is open"
else
    echo "   ✗ Port $DEVICE_PORT is not responding"
    echo "   → Device may be offline, rebooting, or TCP server not running"
fi
echo ""

echo "3. Checking ARP table for device..."
arp -a | grep $DEVICE_IP
echo ""

echo "4. Attempting to connect with Meshtastic CLI..."
echo "   (This may take up to 10 seconds...)"
if timeout 10 meshtastic --host $DEVICE_IP --info > /dev/null 2>&1; then
    echo "   ✓ Meshtastic CLI can connect"
    echo ""
    echo "   Device info:"
    timeout 10 meshtastic --host $DEVICE_IP --info 2>&1 | head -20
else
    echo "   ✗ Meshtastic CLI cannot connect or timed out"
    echo "   → Check device power, WiFi connection, and TCP server status"
fi
echo ""

echo "=== Troubleshooting Steps ==="
echo "If the device is not reachable:"
echo "1. Check if the device is powered on"
echo "2. Verify WiFi connection (check device screen/LEDs)"
echo "3. Try rebooting the device"
echo "4. Check if the IP address has changed (use 'arp -a' or router DHCP table)"
echo "5. Verify TCP server is enabled in device settings"
echo "6. Try connecting via USB instead: MESHTASTIC_CONNECTION_URL=/dev/ttyUSB0"
echo ""

