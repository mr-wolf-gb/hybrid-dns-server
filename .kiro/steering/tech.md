# Technology Stack & Build System

## Core Technologies

### Backend
- **FastAPI**: Python web framework for REST API
- **Python 3.10+**: Primary backend language
- **SQLAlchemy**: Database ORM
- **SQLite/PostgreSQL**: Database for configuration and logs (SQLite for development, PostgreSQL for production)
- **Redis**: Caching and session storage (optional)
- **Uvicorn**: ASGI server for FastAPI
- **Alembic**: Database migration tool
- **Celery**: Background task processing
- **Jinja2**: Template engine for configuration file generation

### Frontend
- **React 18**: UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **Chart.js & Recharts**: Data visualization
- **TanStack Query (React Query)**: Server state management
- **React Hook Form**: Form handling
- **React Router**: Client-side routing
- **Headless UI**: Accessible UI components
- **Heroicons**: Icon library
- **React Toastify**: Toast notifications
- **Axios**: HTTP client

### DNS & Infrastructure
- **BIND9**: Core DNS server (version 9.16+)
- **Nginx**: Reverse proxy and static file serving
- **Docker & Docker Compose**: Containerization
- **systemd**: Service management on Linux

### Development Tools
- **pytest**: Python testing framework
- **pytest-asyncio**: Async testing support
- **Black**: Python code formatting
- **Flake8**: Python linting
- **mypy**: Python type checking
- **Prettier**: Frontend code formatting (via .prettierrc)
- **TypeScript**: Type checking for frontend

## Build Commands

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install
npm run dev          # Development server
npm run build        # Production build
npm run preview      # Preview production build
npm run type-check   # TypeScript checking
```

### Docker Development
```bash
# Full stack development
docker-compose up -d

# Individual services
docker-compose up -d postgres redis
docker-compose up backend  # With logs
docker-compose up frontend

# Rebuild after changes
docker-compose build backend frontend
docker-compose up -d
```

### Testing
```bash
# Backend tests
cd backend
pytest
pytest --cov=app tests/  # With coverage

# Frontend tests (if configured)
cd frontend
npm test
```

### Production Deployment
```bash
# Automated installation
sudo ./install.sh

# Manual systemd services
sudo systemctl start hybrid-dns-backend
sudo systemctl start hybrid-dns-monitoring
sudo systemctl restart bind9

# Docker production
docker-compose -f docker-compose.prod.yml up -d
```

## Configuration Management

### Environment Files
- `.env`: Main environment configuration
- `.env.example`: Example environment configuration
- `frontend/.env.local.example`: Frontend environment example
- `frontend/.env.production`: Frontend production settings

### Key Configuration Locations
- `/etc/bind/`: BIND9 DNS configuration (production)
- `bind9/`: BIND9 configuration (development)
- `/opt/hybrid-dns-server/`: Application installation directory (production)
- `/var/log/hybrid-dns/`: Application logs (production)
- `/var/log/bind/`: DNS server logs (production)
- `.env`: Environment configuration
- `backend/.env`: Backend-specific settings (if exists)
- `frontend/.env.local`: Frontend environment variables (if exists)

### Database Migrations
```bash
# Backend database setup
cd backend
alembic upgrade head  # Apply migrations
alembic revision --autogenerate -m "Description"  # Create migration
```

## Development Workflow

1. **Local Development**: Use Docker Compose for full stack or run services individually
2. **Code Style**: Follow Black formatting for Python, Prettier for TypeScript
3. **Testing**: Write tests for new features, maintain coverage above 80%
4. **Configuration**: Use environment variables for all configurable values
5. **Logging**: Use structured logging with appropriate log levels
6. **Security**: Never commit secrets, use environment variables or secret management