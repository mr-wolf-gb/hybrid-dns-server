@echo off
REM Development Environment Setup Script for Windows
REM Creates .env file from template for local development

echo 🚀 Setting up Hybrid DNS Server development environment...

REM Check if .env already exists
if exist ".env" (
    echo ⚠️  .env file already exists. Backing up to .env.backup
    copy .env .env.backup >nul
)

REM Copy from example
echo 📝 Creating .env file from template...
copy .env.example .env >nul

echo 🔐 Please manually update the following in .env file:
echo    - SECRET_KEY: Generate a secure random string
echo    - JWT_SECRET_KEY: Generate a secure random string  
echo    - REDIS_PASSWORD: Set a secure password

REM Create backend directory if it doesn't exist
if not exist "backend" mkdir backend

REM Set up Python virtual environment
if not exist "venv" (
    echo 🐍 Creating Python virtual environment...
    python -m venv venv
)

echo 📦 Installing Python dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r backend\requirements.txt

REM Initialize database
echo 🗄️  Initializing development database...
cd backend
python init_db.py
cd ..

echo ✅ Development environment setup complete!
echo.
echo 📋 Next steps:
echo 1. Activate virtual environment: venv\Scripts\activate.bat
echo 2. Start backend: cd backend ^&^& python main.py
echo 3. Start frontend: cd frontend ^&^& npm install ^&^& npm run dev
echo.
echo 🌐 Access the application:
echo    Frontend: http://localhost:3000
echo    Backend API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo ⚠️  Remember: Never commit the .env file to git!
pause