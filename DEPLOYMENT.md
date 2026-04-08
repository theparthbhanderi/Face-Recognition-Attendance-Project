# 🚀 Face Recognition System - Deployment Guide

## 📋 Table of Contents
1. [Local Development Setup](#local-development)
2. [Production Deployment Options](#production-deployment)
3. [Cloud Deployment Platforms](#cloud-platforms)
4. [Domain & SSL Setup](#domain-ssl)
5. [Security Considerations](#security)

---

## 🏠 Local Development Setup

### Current Setup (Already Running)
```bash
# Activate virtual environment
venv\Scripts\activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Run development server
python app.py
```
- **Access:** `http://localhost:5000` or `http://127.0.0.1:5000`
- **Debug Mode:** Currently enabled
- **For development only**

---

## 🌐 Production Deployment Options

### Option 1: Gunicorn (Recommended for Production)

#### Install Gunicorn
```bash
pip install gunicorn
```

#### Create Production Config File
Create `wsgi.py`:
```python
from app import app

if __name__ == "__main__":
    app.run()
```

#### Deploy with Gunicorn
```bash
# Basic deployment
gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app

# Production deployment with SSL
gunicorn --workers 4 --bind 0.0.0.0:8000 --certfile cert.pem --keyfile key.pem wsgi:app
```

### Option 2: Docker Deployment

#### Create Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Run the application
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "wsgi:app"]
```

#### Build and Run Docker
```bash
# Build image
docker build -t face-recognition-app .

# Run container
docker run -p 5000:5000 face-recognition-app
```

### Option 3: Waitress (Lightweight Alternative)

```bash
pip install waitress

# Run with Waitress
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

---

## ☁️ Cloud Deployment Platforms

### 1. Heroku (Free Tier Available)

#### Create Procfile
```
web: gunicorn --workers 4 --bind 0.0.0.0:$PORT wsgi:app
```

#### Deploy to Heroku
```bash
# Install Heroku CLI
npm install -g heroku

# Login and create app
heroku login
heroku create your-app-name

# Deploy
git init
git add .
git commit -m "Initial deployment"
heroku git:remote -a heroku git+https://git.heroku.com/your-app-name.git
git push heroku main
```

### 2. PythonAnywhere (Free Python Hosting)

```bash
pip install pythonanywhere

# Configure and deploy
pa_uploader --domain "your-domain.pythonanywhere.com" --project "FaceRecognitionProject"
```

### 3. Railway (Modern Cloud Platform)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### 4. Vercel (Serverless)

#### Create vercel.json
```json
{
    "version": 2,
    "builds": [
        {
            "src": "app.py",
            "use": "@vercel/python"
        }
    ],
    "routes": [
        {
            "src": "app.py",
            "dest": "/"
        }
    ]
}
```

#### Deploy to Vercel
```bash
npm install -g vercel
vercel --prod
```

---

## 🌐 Domain & SSL Setup

### Option 1: Free SSL with Let's Encrypt

```bash
# Install Certbot
pip install certbot

# Generate SSL certificate
certbot certonly --standalone -d yourdomain.com

# Use with Gunicorn
gunicorn --workers 4 --certfile /etc/letsencrypt/live/yourdomain.com/fullchain.pem --keyfile /etc/letsencrypt/live/yourdomain.com/privkey.pem --bind 0.0.0.0:443 wsgi:app
```

### Option 2: Cloudflare SSL (Recommended)

1. **Sign up for Cloudflare** (free tier)
2. **Add your domain** to Cloudflare
3. **Point nameservers** to Cloudflare
4. **Enable SSL/TLS** in Cloudflare dashboard
5. **Deploy** your app behind Cloudflare proxy

---

## 🔧 Production Configuration

### Create Production Config
Create `config.py`:
```python
import os

class ProductionConfig:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    DEBUG = False
    TESTING = False
    
    # Database settings (if using database)
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///face_recognition.db')
    
    # Camera settings
    CAMERA_INDEX = int(os.environ.get('CAMERA_INDEX', '0'))
    MAX_FACES = int(os.environ.get('MAX_FACES', '100'))
    
    # Security settings
    CORS_ORIGINS = ['https://yourdomain.com', 'https://www.yourdomain.com']
```

### Update app.py for Production
```python
# Replace at top of app.py
import os
from config import ProductionConfig

# Use production config
app.config.from_object(ProductionConfig)

# Disable debug mode in production
if not app.config.get('DEBUG', False):
    app.run(debug=False)
```

---

## 🛡️ Security Considerations

### 1. Environment Variables
```bash
# Set secure environment variables
export SECRET_KEY="your-very-secure-secret-key"
export FLASK_ENV="production"
export CAMERA_INDEX="0"
```

### 2. Firewall Configuration
```bash
# Allow port 5000 (or your chosen port)
sudo ufw allow 5000
sudo ufw allow 443  # for HTTPS
```

### 3. Reverse Proxy (Nginx)
Create `/etc/nginx/sites-available/face-recognition`:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 📱 Quick Start Scripts

### Create deploy.sh
```bash
#!/bin/bash
echo "🚀 Deploying Face Recognition System..."

# Choose deployment method
echo "Select deployment method:"
echo "1) Local Production"
echo "2) Docker"
echo "3) Cloud (Heroku/Railway)"

read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "🏠 Starting local production server..."
        gunicorn --workers 4 --bind 0.0.0.0:8000 wsgi:app
        ;;
    2)
        echo "🐳 Building Docker image..."
        docker build -t face-recognition-app .
        docker run -p 8000:5000 face-recognition-app
        ;;
    3)
        echo "☁️ Deploying to cloud..."
        echo "Choose platform:"
        echo "1) Heroku"
        echo "2) Railway"
        read -p "Enter choice (1-2): " cloud_choice
        
        case $cloud_choice in
            1)
                git add .
                git commit -m "Deploy to Heroku"
                git push heroku main
                ;;
            2)
                railway up
                ;;
        ;;
esac
```

---

## 🌍 Access Your Live Application

### Once deployed, your app will be accessible at:
- **Local:** `http://YOUR_IP:5000`
- **With Domain:** `https://yourdomain.com`
- **Docker:** `http://YOUR_SERVER_IP:8000`

### Public IP Detection
```bash
# Find your public IP
curl ifconfig.me
# Or
ip addr show eth0 | grep inet | awk '{ print $2 }'
```

---

## 📊 Monitoring & Maintenance

### Health Check Endpoint
Add to `app.py`:
```python
@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })
```

### Log Monitoring
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler('app.log', maxBytes=1000000, backupCount=3)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
```

---

## 🎯 Next Steps

1. **Choose deployment method** (Local/Docker/Cloud)
2. **Set up domain name** (optional but recommended)
3. **Configure SSL** (required for production)
4. **Test thoroughly** before going live
5. **Set up monitoring** for production health

---

## 🆘 Troubleshooting

### Common Issues & Solutions

**Camera Not Working:**
```bash
# Check camera permissions
ls -l /dev/video*

# Test with different camera indices
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

**Port Already in Use:**
```bash
# Find what's using the port
sudo netstat -tulpn | grep :5000

# Kill the process
sudo kill -9 PID
```

**Memory Issues:**
```bash
# Increase swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📞 Support

For deployment issues:
1. **Check logs:** `tail -f app.log`
2. **Verify dependencies:** `pip list`
3. **Test locally first:** Always test before deploying
4. **Community support:** GitHub Issues, Stack Overflow

---

**🎉 Congratulations!** Your Face Recognition System is now ready for production deployment!
