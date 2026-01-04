# Resume Parser - Production Deployment Guide

## Security Checklist

- [x] Debug mode disabled (only in development)
- [x] Security headers added (CSP, X-Frame-Options, X-XSS-Protection, etc.)
- [x] Input validation on all file uploads
- [x] Path traversal protection on all file serving
- [x] API key sanitization and truncation
- [x] Model validation to prevent injection attacks
- [x] File size limits enforced
- [x] File type validation (whitelist only: PDF, DOCX, DOC, TXT)
- [x] Error messages don't leak sensitive information in production
- [x] Session cookies secure (HTTPONLY, SECURE, SAMESITE)
- [x] HTTPS/SSL enforced in production (via reverse proxy headers)
- [x] API key storage encrypted (optional via secrets_store.py)

## Deployment Architecture

### Recommended Production Setup

```
┌─────────────┐
│   Users     │
└──────┬──────┘
       │ HTTPS/TLS
       ↓
┌─────────────────────────────────────┐
│  Nginx/Apache Reverse Proxy         │
│  - TLS Termination                  │
│  - Request Rate Limiting            │
│  - Gzip Compression                 │
│  - Static File Serving              │
└────────────┬────────────────────────┘
             │ HTTP (localhost only)
             ↓
┌─────────────────────────────────────┐
│  Flask App (resume_parser)          │
│  - Gunicorn/uWSGI (4+ workers)      │
│  - Running on localhost:5050        │
│  - Environment: production          │
└─────────────────────────────────────┘
```

## Step-by-Step Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-pip python3-venv nginx supervisor
```

### 2. Application Setup

```bash
cd /opt/resume-parser
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create application user
sudo useradd -m -s /bin/bash resumeparser
sudo chown -R resumeparser:resumeparser /opt/resume-parser
```

### 3. Configuration

```bash
# Copy environment configuration
cp .env.production .env

# Edit .env with your settings
nano .env

# Generate secure ADMIN_TOKEN
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# If using encrypted API key storage, generate MASTER_KEY
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 4. Create Supervisor Configuration

```bash
sudo cat > /etc/supervisor/conf.d/resume-parser.conf << 'EOF'
[program:resume-parser]
directory=/opt/resume-parser
command=/opt/resume-parser/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:5050 --timeout 120 app:app
user=resumeparser
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/resume-parser.log
environment=FLASK_ENV=production,PATH="/opt/resume-parser/venv/bin"
EOF

sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start resume-parser
```

### 5. Configure Nginx

```bash
sudo cat > /etc/nginx/sites-available/resume-parser << 'EOF'
upstream resume_parser {
    server 127.0.0.1:5050;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=upload:10m rate=5r/s;

    # Logging
    access_log /var/log/nginx/resume-parser-access.log;
    error_log /var/log/nginx/resume-parser-error.log warn;

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;

    # Upload size limit
    client_max_body_size 50M;

    # Parse endpoint with stricter rate limiting
    location /parse {
        limit_req zone=upload burst=10 nodelay;
        proxy_pass http://resume_parser;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    # Other endpoints with normal rate limiting
    location / {
        limit_req zone=api burst=30 nodelay;
        proxy_pass http://resume_parser;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 10s;
        proxy_read_timeout 60s;
    }

    # Admin endpoints - require authentication at nginx level
    location /admin {
        auth_basic "Admin Only";
        auth_basic_user_file /etc/nginx/.htpasswd;
        proxy_pass http://resume_parser;
    }

    # Static/uploaded files - cached
    location /uploads {
        proxy_pass http://resume_parser;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }

    location /originals {
        proxy_pass http://resume_parser;
        expires 1h;
        add_header Cache-Control "public, max-age=3600";
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/resume-parser /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Set Up HTTPS with Let's Encrypt

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot certonly --nginx -d your-domain.com
```

### 7. Enable Firewall

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 8. Monitoring & Logs

```bash
# View application logs
sudo tail -f /var/log/resume-parser.log

# View Nginx logs
sudo tail -f /var/log/nginx/resume-parser-access.log
sudo tail -f /var/log/nginx/resume-parser-error.log

# Check supervisor status
sudo supervisorctl status resume-parser
```

## Security Best Practices

1. **Keep System Updated**: Run `apt update && apt upgrade` regularly
2. **Database/Storage**: Keep `/uploads` and `/originals` directories outside web root if possible
3. **Backups**: Regular backups of parsed data and configuration
4. **Access Control**: Use strong `ADMIN_TOKEN` and nginx basic auth
5. **Monitoring**: Set up alerts for error rates, failed parses, and server health
6. **API Keys**: Rotate LLM API keys regularly, store securely in `.env`
7. **Logs**: Rotate logs daily, keep for 30+ days for audit trails
8. **Performance**: Monitor CPU/Memory, scale workers based on load

## Troubleshooting

### Application won't start
```bash
sudo supervisorctl restart resume-parser
# Check logs:
sudo tail -f /var/log/resume-parser.log
```

### Out of memory
```bash
# Reduce workers
# Edit /etc/supervisor/conf.d/resume-parser.conf
# Change --workers 4 to --workers 2
sudo supervisorctl restart resume-parser
```

### Uploads not saving
```bash
# Check permissions
ls -la /opt/resume-parser/uploads
sudo chown -R resumeparser:resumeparser /opt/resume-parser/uploads

# Check disk space
df -h
```

### Nginx 502 Bad Gateway
```bash
# Check if Flask app is running
sudo supervisorctl status resume-parser

# Check Flask logs
sudo tail -f /var/log/resume-parser.log

# Verify Flask is listening
netstat -tlnp | grep 5050
```

## Performance Tuning

```bash
# Increase open file descriptors
ulimit -n 65536

# Optimize Nginx worker processes
# Edit /etc/nginx/nginx.conf
# Set: worker_processes auto;
```

## Security Audit Checklist

- [ ] HTTPS/TLS enabled with valid certificate
- [ ] Debug mode disabled
- [ ] Strong ADMIN_TOKEN set
- [ ] File upload limits configured
- [ ] Rate limiting enabled
- [ ] Security headers verified
- [ ] Access logs monitored
- [ ] Error logs reviewed
- [ ] Firewall configured
- [ ] Regular backups scheduled

## Support

For security issues, do NOT open public issues. Contact: [security contact]
