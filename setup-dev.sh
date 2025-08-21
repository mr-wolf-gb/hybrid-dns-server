#!/bin/bash

# Development Environment Setup Script
# Creates .env file from template for local development

set -e

echo "🚀 Setting up Hybrid DNS Server development environment..."

# Check if .env already exists
if [[ -f ".env" ]]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp .env .env.backup
fi

# Copy from example
echo "📝 Creating .env file from template..."
cp .env.example .env

# Generate secure random keys for development
echo "🔐 Generating secure development keys..."

# Generate random secret keys
SECRET_KEY="dev-secret-$(openssl rand -hex 32)"
JWT_SECRET_KEY="dev-jwt-$(openssl rand -hex 32)"
REDIS_PASSWORD="dev-redis-$(openssl rand -hex 16)"

# Update the .env file with generated keys
if command -v sed >/dev/null 2>&1; then
    sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    sed -i.bak "s/JWT_SECRET_KEY=.*/JWT_SECRET_KEY=$JWT_SECRET_KEY/" .env
    sed -i.bak "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASSWORD/" .env
    rm -f .env.bak
else
    echo "⚠️  sed not available. Please manually update SECRET_KEY and JWT_SECRET_KEY in .env"
fi

# Set development-friendly defaults
echo "🛠️  Configuring development settings..."

# Create backend directory if it doesn't exist
mkdir -p backend

# Set up Python virtual environment
if [[ ! -d "venv" ]]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

# Initialize database
echo "🗄️  Initializing development database..."
cd backend
python init_db.py
cd ..

echo "✅ Development environment setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start backend: cd backend && python main.py"
echo "3. Start frontend: cd frontend && npm install && npm run dev"
echo ""
echo "🌐 Access the application:"
echo "   Frontend: http://localhost:3000"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "⚠️  Remember: Never commit the .env file to git!"