#!/bin/bash

# 🚀 Face Recognition System - Quick Deployment Script
# Author: AI Assistant
# Version: 1.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Face Recognition System - Deployment Script${NC}"
echo "=========================================="

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check dependencies
print_status "Checking dependencies..."

if ! command_exists python3; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

if ! command_exists pip; then
    print_error "pip is required but not installed"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_warning "Virtual environment not found. Creating one..."
    python3 -m venv venv
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt

# Create wsgi.py if it doesn't exist
if [ ! -f "wsgi.py" ]; then
    print_status "Creating WSGI entry point..."
    cat > wsgi.py << 'EOF'
from app import app

if __name__ == "__main__":
    app.run()
EOF
fi

# Get deployment choice
echo ""
echo "Select deployment method:"
echo "1) 🏠 Local Production Server (Gunicorn)"
echo "2) 🐳 Docker Deployment"
echo "3) ☁️ Heroku Cloud"
echo "4) 🚂 Railway Cloud"
echo "5) 📱 PythonAnywhere"
echo "6) 🔧 Development Mode (Current Setup)"

while true; do
    read -p "Enter your choice (1-6): " choice
    case $choice in
        1|2|3|4|5|6)
            break
        *)
            print_warning "Please enter a number between 1 and 6"
            ;;
    esac
done

# Get port for local deployment
get_port() {
    while true; do
        read -p "Enter port number (default 5000): " port
        port=${port:-5000}
        if [[ $port =~ ^[0-9]+$ ]] && [ $port -ge 1024 ] && [ $port -le 65535 ]; then
            echo $port
            break
        else
            print_error "Please enter a valid port number (1024-65535)"
        fi
    done
}

# Get domain for cloud deployment
get_domain() {
    read -p "Enter your domain (optional): " domain
    echo ${domain:-localhost}
}

# Execute deployment
case $choice in
    1)
        echo -e "${GREEN}🏠 Starting Local Production Server...${NC}"
        port=$(get_port)
        print_status "Installing Gunicorn..."
        pip install gunicorn
        
        print_status "Starting server on port $port..."
        print_success "Server will be accessible at: http://localhost:$port"
        print_warning "Press Ctrl+C to stop the server"
        
        # Create systemd service file (optional)
        if command_exists systemctl; then
            print_status "Creating systemd service..."
            sudo tee /etc/systemd/system/face-recognition.service > /dev/null << EOF
[Unit]
Description=Face Recognition System
After=network.target

[Service]
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/gunicorn --workers 4 --bind 0.0.0.0:$port wsgi:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF
            
            print_status "Enabling service..."
            sudo systemctl daemon-reload
            sudo systemctl enable face-recognition.service
            sudo systemctl start face-recognition.service
            print_success "Service started! Check status with: systemctl status face-recognition"
        else
            # Run directly
            gunicorn --workers 4 --bind 0.0.0.0:$port wsgi:app
        fi
        ;;
        
    2)
        echo -e "${GREEN}🐳 Docker Deployment${NC}"
        
        if ! command_exists docker; then
            print_error "Docker is required but not installed"
            exit 1
        fi
        
        print_status "Building Docker image..."
        docker build -t face-recognition-app .
        
        port=$(get_port)
        print_status "Running Docker container..."
        docker run -d --name face-recognition -p $port:5000 face-recognition-app
        
        print_success "Container running! Access at: http://localhost:$port"
        print_warning "View logs with: docker logs face-recognition"
        print_warning "Stop with: docker stop face-recognition"
        ;;
        
    3)
        echo -e "${GREEN}☁️ Heroku Deployment${NC}"
        
        if ! command_exists git; then
            print_error "Git is required for Heroku deployment"
            exit 1
        fi
        
        if ! command_exists heroku; then
            print_error "Heroku CLI is required"
            print_status "Installing Heroku CLI..."
            npm install -g heroku
        fi
        
        domain=$(get_domain)
        print_status "Preparing for Heroku deployment..."
        
        # Create Procfile
        echo "web: gunicorn --workers 4 --bind 0.0.0.0:\$PORT wsgi:app" > Procfile
        
        # Initialize git if needed
        if [ ! -d ".git" ]; then
            git init
            git add .
            git commit -m "Initial commit"
        fi
        
        print_status "Deploying to Heroku..."
        heroku create $domain 2>/dev/null || true
        heroku git:remote -a heroku https://git.heroku.com/$domain.git
        
        git push heroku main
        
        print_success "Deployed! Check status with: heroku open"
        ;;
        
    4)
        echo -e "${GREEN}🚂 Railway Deployment${NC}"
        
        if ! command_exists railway; then
            print_error "Railway CLI is required"
            print_status "Installing Railway CLI..."
            npm install -g @railway/cli
        fi
        
        print_status "Deploying to Railway..."
        railway login
        railway up
        
        print_success "Deployed! Check Railway dashboard for URL"
        ;;
        
    5)
        echo -e "${GREEN}📱 PythonAnywhere Deployment${NC}"
        
        if ! command_exists pa_uploader; then
            print_error "PythonAnywhere is required"
            print_status "Installing PythonAnywhere..."
            pip install pythonanywhere
        fi
        
        domain=$(get_domain)
        print_status "Deploying to PythonAnywhere..."
        pa_uploader --domain "$domain" --project "FaceRecognitionProject"
        
        print_success "Deployed! Access at: https://$domain.pythonanywhere.com"
        ;;
        
    6)
        echo -e "${GREEN}🔧 Development Mode${NC}"
        print_status "Starting development server..."
        python app.py
        ;;
        
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Deployment process completed!${NC}"
echo "=========================================="
print_status "Check the logs above for any issues or next steps"
