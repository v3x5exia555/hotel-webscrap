# Post-Mortem & Troubleshooting Guide

## Issue: "Individual Property Intelligence Deep-Dive" Tab Fails on Remote Domain

### Symptom

- Dashboard works perfectly on `localhost` or via Cloudflare Tunnel.
- On the Nginx-proxied domain (`scapper.abai.my`), the "Deep-Dive" tab shows "Callback Error", infinite loading, or "No Data".
- Browser Console (F12) shows `413 Request Entity Too Large`.
- Nginx Error Log (`/var/log/nginx/error.log`) shows:
  - `client intended to send too large body: XXXXX bytes`
  - `connect() failed (111: Connection refused) while connecting to upstream`

### Root Causes

1. **Nginx Payload Limit**: The "Deep-Dive" request sends large data structures (Fact Tables + Multiple Plotly Graphs). Nginx's default `client_max_body_size` is too small (1MB).
2. **IPv6 Loopback Mismatch**: Nginx often resolves `localhost` to `[::1]` (IPv6), but Python/Dash often listens only on `127.0.0.1` (IPv4).

### Resolution

The proxy configuration must be updated to allow large payloads and a specific IP address.

#### One-Click Fix

Run the provided fix script on the server:

```bash
bash scripts/fix_nginx.sh
```

#### Manual Configuration Fix

In your Nginx config (`/etc/nginx/sites-enabled/scapper.conf`), update the `location /` block:

```nginx
server {
    ...
    # ALLOW LARGE PAYLOADS
    client_max_body_size 128M;

    location / {
        # USE 127.0.0.1 INSTEAD OF LOCALHOST
        proxy_pass http://127.0.0.1:8050;

        # ENSURE BUFFERING IS OFF
        proxy_buffering off;
        ...
    }
}
```

---

## Performance Optimization Checklist

- [ ] **Database Indexes**: Ensure `snapshots` and `pickup_trends` have indexes on `hotel_name`.
- [ ] **Python Path**: Always run with `export PYTHONPATH=$PYTHONPATH:.` to ensure `utils` module is found.
- [ ] **Cache Flush**: Use the "Full Refresh" button on the dashboard to clear stale server-side cache.
