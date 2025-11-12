#!/bin/bash
# ============================================================================
# V_Track Docker - Start Script
# Starts the V_Track application stack using Docker Compose
# ============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 V_Track Docker - Starting Application Stack${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from template...${NC}"
    if [ -f .env.docker.example ]; then
        cp .env.docker.example .env
        echo -e "${YELLOW}⚠️  IMPORTANT: Edit .env and configure SECRET_KEY and ENCRYPTION_KEY${NC}"
        echo -e "${YELLOW}   Generate keys with:${NC}"
        echo -e "${YELLOW}   python3 -c \"import secrets; print('SECRET_KEY=' + secrets.token_hex(32))\"${NC}"
        echo -e "${YELLOW}   python3 -c \"from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())\"${NC}"
        echo ""
        read -p "Press Enter after configuring .env to continue..."
    else
        echo -e "${RED}❌ .env.docker.example not found${NC}"
        exit 1
    fi
fi

# Check if Docker images exist
echo -e "${BLUE}📦 Checking Docker images...${NC}"
if ! docker images | grep -q "vtrack-backend.*phase2"; then
    echo -e "${YELLOW}⚠️  Backend image not found. Building...${NC}"
    docker build --platform linux/arm64 -t vtrack-backend:phase2 ./backend
fi

if ! docker images | grep -q "vtrack-frontend.*phase3"; then
    echo -e "${YELLOW}⚠️  Frontend image not found. Building...${NC}"
    docker build --platform linux/arm64 -t vtrack-frontend:phase3 ./frontend
fi

echo -e "${GREEN}✅ Docker images ready${NC}"
echo ""

# Parse command line arguments
MODE="production"
DETACHED="-d"

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev|--development)
            MODE="development"
            shift
            ;;
        --attach|-a)
            DETACHED=""
            shift
            ;;
        --help|-h)
            echo "Usage: ./start.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dev, --development    Start in development mode"
            echo "  --attach, -a            Run in attached mode (show logs)"
            echo "  --help, -h              Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./start.sh                    # Start in production mode (detached)"
            echo "  ./start.sh --dev              # Start in development mode"
            echo "  ./start.sh --attach           # Start and show logs"
            echo "  ./start.sh --dev --attach     # Start dev mode with logs"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run './start.sh --help' for usage information"
            exit 1
            ;;
    esac
done

# Start the appropriate stack
if [ "$MODE" = "development" ]; then
    echo -e "${BLUE}🔧 Starting V_Track in DEVELOPMENT mode...${NC}"
    echo -e "${YELLOW}   - Live code reloading enabled${NC}"
    echo -e "${YELLOW}   - Source code mounted as volumes${NC}"
    echo ""
    docker-compose -f docker-compose.dev.yml up $DETACHED
else
    echo -e "${BLUE}🚀 Starting V_Track in PRODUCTION mode...${NC}"
    echo ""
    docker-compose up $DETACHED
fi

# If running in detached mode, show status
if [ ! -z "$DETACHED" ]; then
    echo ""
    echo -e "${GREEN}✅ V_Track stack started successfully${NC}"
    echo ""
    echo -e "${BLUE}📊 Container Status:${NC}"
    docker-compose ps
    echo ""
    echo -e "${BLUE}🌐 Access URLs:${NC}"
    echo -e "   Frontend:  ${GREEN}http://localhost:3000${NC}"
    echo -e "   Backend:   ${GREEN}http://localhost:8080${NC}"
    echo -e "   Health:    ${GREEN}http://localhost:8080/health${NC}"
    echo ""
    echo -e "${BLUE}📝 Useful Commands:${NC}"
    echo "   View logs:      ./logs.sh"
    echo "   Stop services:  ./stop.sh"
    echo "   Restart:        docker-compose restart"
    echo ""
    echo -e "${BLUE}🔍 Health Check:${NC}"
    echo "   Waiting for services to be healthy..."
    sleep 5

    # Check backend health
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        echo -e "   Backend:  ${GREEN}✅ Healthy${NC}"
    else
        echo -e "   Backend:  ${YELLOW}⚠️  Starting...${NC}"
    fi

    # Check frontend health
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "   Frontend: ${GREEN}✅ Healthy${NC}"
    else
        echo -e "   Frontend: ${YELLOW}⚠️  Starting...${NC}"
    fi

    echo ""
    echo -e "${GREEN}🎉 V_Track is ready!${NC}"
fi
