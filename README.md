# Antifrode Backend

A modern fraud detection API service built with FastAPI and Clean Architecture principles. Provides secure authentication, user management, and comprehensive audit logging for fraud detection systems.

## Quick Start

### Admin Login
```json
{
  "email": "admin@example.com",
  "password": "AdminPassword123"
}
```

### Prerequisites
- Docker & Docker Compose
- Python 3.13+ (for local development)

### Run Locally with Docker

```bash
# 1. Setup environment variables
make env-setup

# 2. Start services (PostgreSQL + API)
make docker-up

# 3. Access the API
# - API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
# - Database: postgres://postgres:postgres@localhost:5432/antifrode_backend_db
```

### Run Locally without Docker

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup environment
cp .env.example .env
# Edit .env with your database credentials

# 4. Run database migrations
alembic upgrade head

# 5. Start API server
python main.py
```

## Project Structure

```
app/
├── domain/              # Business logic & entities
│   ├── user/           # User entity, rules, repository interface
│   ├── auth/           # Authentication policies
│   ├── audit/          # Audit log entity
│   └── ...
├── application/        # Use cases & business workflows
│   ├── auth/           # Registration, login, refresh tokens
│   ├── user/           # User CRUD operations
│   ├── audit/          # Audit log queries
│   └── services/       # Service implementations
├── infrastructure/     # Technical implementation
│   ├── db/            # Database models & repositories
│   ├── di/            # Dependency injection setup
│   ├── auth.py        # JWT & password handling
│   └── config.py      # Configuration loader
└── presentation/      # FastAPI API layer
    └── api/          # Endpoints (auth, users, audit, health)
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Framework** | FastAPI 0.135.3+ (async Python web framework) |
| **Language** | Python 3.13+ |
| **Database** | PostgreSQL 16 with SQLAlchemy ORM |
| **Authentication** | JWT tokens (access + refresh) with python-jose |
| **Dependency Injection** | Dishka 1.9.1+ |
| **Validation** | Pydantic 2.13+ |
| **Migration** | Alembic 1.18+ |
| **Deployment** | Docker & Docker Compose |
| **Server** | Uvicorn 0.44+ |
| **Observability** | OpenTelemetry + optional Sentry |

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user (admin token required by default)
- `POST /auth/login` - Login with email/password
- `POST /auth/refresh` - Refresh access token using refresh token
- `POST /auth/logout` - Logout and invalidate refresh token

### Users
- `GET /users/me` - Get current user profile
- `GET /users` - List all users (admin only)
- `GET /users/{user_id}` - Get user details (admin or self)
- `PUT /users/{user_id}` - Update user (admin only)
- `DELETE /users/{user_id}` - Delete user (admin only, prevents last admin deletion)

### Audit Logs
- `GET /audit-logs` - List audit logs with filters (admin only)
- `GET /audit-logs/{log_id}` - Get audit log details (admin only)

### Health
- `GET /health/` - Service health check

**API Documentation:** Open `http://localhost:8000/docs` (interactive Swagger UI)

## Configuration

### Environment Variables (`.env`)
```bash
# Database
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=antifrode_backend_db
DB_PORT=5432

# API
APP_PORT=8000
CONFIG_PATH=./config.yaml

# Initial Admin (created on first run)
INITIAL_ADMIN_PASSWORD=AdminPassword123
```

### Config File (`config.yaml`)
```yaml
postgres:
  host: localhost
  port: 5432
  pool_size: 30
  pool_recycle: 3600

auth:
  secret_key: "your-super-secret-key-minimum-32-characters"
  algorithm: "HS256"
  access_token_expire_minutes: 30
  refresh_token_expire_days: 7
  admin_emails: [admin@example.com]

telemetry:
  export_metrics: true
  export_traces: true
  sentry_dsn: null
```

## Development Commands

```bash
make help              # Show all available commands
make env-setup        # Initialize .env file
make docker-up        # Start containers
make docker-down      # Stop containers
make docker-logs      # View container logs
make rebuild          # Rebuild and restart containers
make db-shell         # Access PostgreSQL shell
make docker-test      # Run tests in Docker
make docker-lint      # Run linting checks
```

## Architecture

### Clean Architecture Pattern
The codebase follows **Clean/Hexagonal Architecture** with clear separation of concerns:

1. **Domain Layer** (`app/domain/`) - Pure business logic, no framework dependencies
   - Entities and business rules
   - Repository interfaces (contracts)

2. **Application Layer** (`app/application/`) - Use cases and workflows
   - Interactors (business workflows)
   - Service implementations
   - Transaction management

3. **Infrastructure Layer** (`app/infrastructure/`) - Technical implementation
   - Database models and repositories
   - External services (Auth, Config)
   - Dependency injection container

4. **Presentation Layer** (`app/presentation/`) - HTTP API
   - FastAPI endpoints
   - Request/response DTOs
   - Middleware and error handling

### Key Features

**Authentication Flow:**
- User registers → password hashed with bcrypt
- Login → receives JWT access token (30 min) + refresh token (7 days, stored in HTTP-only cookie)
- Middleware extracts JWT and validates on each request
- Expired token → use refresh endpoint to get new access token
- Logout → invalidates refresh token

**Authorization:**
- Role-based access control (admin/regular user)
- Middleware validates permissions
- Users can view own profile; admins can view all
- Special protection for last admin user (cannot be deleted)

**Audit Trail:**
- Every significant action logged (user creation, login, logout, updates, deletions)
- Queryable by administrators with filtering
- Includes action type, entity info, user, and timestamp

## Database

### Migrations
Migrations are automatically applied on startup using Alembic.

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Upgrade to latest
alembic upgrade head

# View migration status
alembic current
```

### Initial Setup
- PostgreSQL container starts automatically with Docker Compose
- Initial admin user created on first run if `INITIAL_ADMIN_PASSWORD` env var is set
- All migrations run automatically on startup

## Testing

```bash
# Run all tests in Docker
make docker-test

# Run specific test file
docker-compose exec app pytest tests/test_auth.py -v

# Run with coverage
docker-compose exec app pytest --cov=app tests/
```

## Deployment

### Docker Production Build
```bash
docker build -t antifrode-backend:latest .
docker run -e CONFIG_PATH=/app/config.docker.yaml \
           -e DB_USER=postgres \
           -e DB_PASSWORD=secure_password \
           -e DB_NAME=antifrode_backend_db \
           -p 8000:8000 \
           antifrode-backend:latest
```

### Environment-Specific Configs
- `config.yaml` - Local development
- `config.docker.yaml` - Docker development
- Create `config.prod.yaml` for production deployment

## Common Tasks

### Reset Database
```bash
make docker-down
docker volume rm antifrode_backend_db_data
make docker-up
```

### View Logs
```bash
# API logs
make docker-logs

# Follow logs in real-time
docker-compose logs -f app
```

### Access Database
```bash
# Interactive psql shell
make db-shell

# Or directly
docker-compose exec postgres psql -U postgres -d antifrode_backend_db
```

### Create Admin User Manually
```bash
docker-compose exec app python -c "
from app.infrastructure.db.repos.user import UserRepository
from app.infrastructure.db.models import AsyncSessionLocal
# Create user with admin=True
"
```

## Troubleshooting

**Port Already in Use:**
```bash
# Change port in .env: APP_PORT=8001
```

**Database Connection Error:**
```bash
# Ensure DATABASE_URL is correct in .env
# Check PostgreSQL container is running: docker ps
```

**Migrations Failed:**
```bash
# View migration status
alembic current
# Try to upgrade
alembic upgrade head
```

**Permission Denied Errors:**
```bash
# Rebuild containers
make rebuild
```

## Contributing

1. **Create a branch** for your feature: `git checkout -b feature/your-feature`
2. **Write tests** for new functionality
3. **Follow the architecture** - keep domain logic separate from infrastructure
4. **Run linting** before committing: `make docker-lint`
5. **Test locally** - ensure tests pass: `make docker-test`
6. **Create a pull request** with clear description
