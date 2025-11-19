# ePACK Docker Compose - Quick Start

Fast setup guide for ePACK deployment using Docker Compose.

---

## Prerequisites

- Docker Desktop installed and running
- Pre-built images: `epack-backend:phase2` and `epack-frontend:phase3`
- Mac M1/M2/M3 (ARM64)

---

## 1. Setup Environment (First Time Only)

```bash
# Copy environment template
cp .env.docker.example .env

# Generate security keys
python3 -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32))"
python3 -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Edit .env and add the generated keys
nano .env
```

**Required in .env:**
```bash
SECRET_KEY=<YOUR_GENERATED_SECRET_KEY>
ENCRYPTION_KEY=<YOUR_GENERATED_ENCRYPTION_KEY>
NEXT_PUBLIC_API_URL=http://localhost:8080
```

---

## 2. Start Production Services

```bash
# Start services
docker-compose up -d

# Check status (wait for "healthy" status)
docker-compose ps

# View logs
docker-compose logs -f
```

---

## 3. Access Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8080
- **Health Check**: http://localhost:8080/health

---

## Common Commands

```bash
# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Check service status
docker-compose ps

# Update and restart
docker-compose up -d --force-recreate

# Remove everything (including data)
docker-compose down -v
```

---

## Development Mode

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up

# With live code reloading:
# - Backend: ./backend mounted to /app
# - Frontend: ./frontend mounted to /app

# Stop development
docker-compose -f docker-compose.dev.yml down
```

---

## Troubleshooting

### Services not starting?
```bash
# Check logs
docker-compose logs backend
docker-compose logs frontend

# Check ports not in use
lsof -i :8080
lsof -i :3000
```

### Frontend can't connect to backend?
```bash
# Verify backend health
curl http://localhost:8080/health

# Check NEXT_PUBLIC_API_URL in .env
cat .env | grep NEXT_PUBLIC_API_URL
```

### Permission errors?
```bash
# Reset volumes
docker-compose down -v
docker-compose up -d
```

---

## Backup Data

```bash
# Backup database
docker run --rm \
  -v epack-db:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/epack-db.tar.gz -C /data .

# Restore database
docker run --rm \
  -v epack-db:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/epack-db.tar.gz -C /data
```

---

## Need More Help?

See full documentation: [DOCKER_COMPOSE_GUIDE.md](./DOCKER_COMPOSE_GUIDE.md)
