#!/bin/bash

# Function to print colored output
print_green() { echo -e "\033[32m$1\033[0m"; }
print_red() { echo -e "\033[31m$1\033[0m"; }
print_yellow() { echo -e "\033[33m$1\033[0m"; }

echo "--- WiFi Network Scanner (Radio Activation Fix) ---"

# Enable WiFi radio via NetworkManager
print_yellow "Enabling WiFi radio..."
sudo nmcli radio wifi on
sleep 2

# Ensure interface is up
sudo ip link set wlan0 up 2>/dev/null
sleep 1

# Force a fresh scan
print_yellow "Initiating deep scan... please wait."
sudo nmcli device wifi rescan 2>/dev/null || true
sleep 8

# List networks
networks=$(nmcli -t -f SSID,SIGNAL,SECURITY device wifi list 2>/dev/null | grep -v "^$" | grep -v "^SSID")

if [ -z "$networks" ]; then
    print_red "No WiFi networks found."
    print_yellow "Check: sudo nmcli device wifi"
    exit 1
fi

# Display networks with numbers
echo "Available Networks:"
echo "-------------------"

declare -a ssid_list
count=1

while IFS=':' read -r ssid signal security; do
    if [ -z "$ssid" ]; then continue; fi
    ssid_list+=("$ssid")
    printf "%2d. %-30s Signal: %s%%  [%s]\n" "$count" "$ssid" "$signal" "$security"
    ((count++))
done <<< "$networks"

total_networks=$((count - 1))

# Prompt for selection
echo ""
while true; do
    read -p "Enter the number of the network you want to connect to (1-$total_networks): " choice
    
    if ! [[ "$choice" =~ ^[0-9]+$ ]]; then
        print_red "Invalid input. Please enter a number."
        continue
    fi

    if [ "$choice" -lt 1 ] || [ "$choice" -gt "$total_networks" ]; then
        print_red "Number out of range."
        continue
    fi
    
    selected_ssid="${ssid_list[$((choice - 1))]}"
    break
done

# Prompt for password
echo ""
print_yellow "Connecting to: $selected_ssid"
read -sp "Enter WiFi password: " wifi_password
echo ""

# MANUAL CONNECTION SETUP
print_yellow "Deleting old profile if exists..."
sudo nmcli connection delete "$selected_ssid" 2>/dev/null || true

print_yellow "Creating new profile with explicit security settings..."

# Determine security type
security_type="wpa-psk"
if [[ "$security" == *"WPA3"* ]] && [[ "$security" != *"WPA2"* ]]; then
    security_type="sae"
fi

# Create the connection profile explicitly
sudo nmcli connection add type wifi con-name "$selected_ssid" ifname wlan0 ssid "$selected_ssid" \
    802-11-wireless-security.key-mgmt "$security_type" \
    802-11-wireless-security.psk "$wifi_password"

if [ $? -ne 0 ]; then
    print_red "Failed to create connection profile."
    exit 1
fi

print_yellow "Waiting for radio to be ready..."
sleep 3

print_yellow "Activating connection..."

# Activate the connection
sudo nmcli connection up "$selected_ssid"

if [ $? -eq 0 ]; then
    print_green "Success! Connected to $selected_ssid"
    
    sleep 3
    ip_addr=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    if [ -n "$ip_addr" ]; then
        print_green "Your IP address is: $ip_addr"
    else
        print_yellow "Connected, but IP not detected yet. Check 'ip addr' in a moment."
    fi
else
    print_red "Failed to activate connection."
    print_yellow "Debug info:"
    sudo nmcli device wifi show-status
    echo ""
    print_yellow "Try: sudo nmcli device wifi connect '$selected_ssid' password '$wifi_password'"
    exit 1
fi