#!/bin/bash
# scripts/fix_nginx.sh
# Automates fixing common Nginx issues with Dash/Plotly dashboards

CONF_FILE="/etc/nginx/sites-enabled/scapper.conf"

if [ ! -f "$CONF_FILE" ]; then
    echo "Error: Configuration file $CONF_FILE not found."
    exit 1
fi

echo "Injecting Nginx fixes for Dash performance..."

# 1. Increase client_max_body_size if it's not set high enough
if grep -q "client_max_body_size" "$CONF_FILE"; then
    sed -i 's/client_max_body_size [0-9]\+[MmGg];/client_max_body_size 128M;/g' "$CONF_FILE"
else
    # Insert client_max_body_size after server_name
    sed -i '/server_name/a \    client_max_body_size 128M;' "$CONF_FILE"
fi

# 2. Force IPv4 (127.0.0.1) instead of localhost to prevent "Connection refused" loop
sed -i 's/proxy_pass http:\/\/localhost/proxy_pass http:\/\/127.0.0.1/g' "$CONF_FILE"

# 3. Ensure proxy_buffering is off
if ! grep -q "proxy_buffering off" "$CONF_FILE"; then
    sed -i '/proxy_pass/a \        proxy_buffering off;' "$CONF_FILE"
fi

# 4. Test and restart
nginx -t
if [ $? -eq 0 ]; then
    systemctl restart nginx
    echo "Nginx successfully optimized. Dashboard 'Deep-Dive' should now work correctly."
else
    echo "Nginx config test failed! Please check your configuration."
    exit 1
fi
