#!/bin/bash

# ============================================
# VPACK - Unified Build Script
# ============================================
# This script builds all components of VPACK:
# - Frontend (Next.js)
# - Backend (Python dependencies)
# - Database initialization
#
# Usage:
#   ./scripts/build_all.sh [--skip-frontend] [--skip-backend] [--skip-db]
#
# Options:
#   --skip-frontend    Skip frontend build
#   --skip-backend     Skip backend dependency installation
#   --skip-db          Skip database initialization
#   --production       Use production build settings
#   --clean            Clean build artifacts before building
#   -h, --help         Show this help message

set -e  # Exit on error

# ============================================
# COLOR CODES FOR OUTPUT
# ============================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================
# UTILITY FUNCTIONS
# ============================================

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}  $1"
    echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
}

print_step() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed. Please install it first."
        return 1
    fi
    return 0
}

# ============================================
# PARSE ARGUMENTS
# ============================================

SKIP_FRONTEND=false
SKIP_BACKEND=false
SKIP_DB=false
PRODUCTION=false
CLEAN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --skip-backend)
            SKIP_BACKEND=true
            shift
            ;;
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --production)
            PRODUCTION=true
            shift
            ;;
        --clean)
            CLEAN=true
            shift
            ;;
        -h|--help)
            grep '^#' "$0" | grep -v '#!/bin/bash' | sed 's/^# //'
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================
# SCRIPT INITIALIZATION
# ============================================

# Get the root directory (parent of scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

print_header "VPACK Build Script"
print_info "Root directory: $ROOT_DIR"
print_info "Build mode: $([ "$PRODUCTION" = true ] && echo "PRODUCTION" || echo "DEVELOPMENT")"
echo ""

# Track build time
START_TIME=$(date +%s)

# ============================================
# CLEAN BUILD ARTIFACTS
# ============================================

if [ "$CLEAN" = true ]; then
    print_header "Cleaning Build Artifacts"

    if [ -d "$ROOT_DIR/frontend/.next" ]; then
        print_step "Removing frontend/.next"
        rm -rf "$ROOT_DIR/frontend/.next"
    fi

    if [ -d "$ROOT_DIR/frontend/node_modules" ]; then
        print_warning "Removing frontend/node_modules"
        rm -rf "$ROOT_DIR/frontend/node_modules"
    fi

    if [ -d "$ROOT_DIR/backend/__pycache__" ]; then
        print_step "Removing Python cache"
        find "$ROOT_DIR/backend" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$ROOT_DIR/backend" -type f -name "*.pyc" -delete 2>/dev/null || true
    fi

    echo ""
fi

# ============================================
# BUILD FRONTEND
# ============================================

if [ "$SKIP_FRONTEND" = false ]; then
    print_header "Building Frontend (Next.js)"

    # Check if Node.js is installed
    if ! check_command "node"; then
        print_error "Node.js is required but not installed"
        exit 1
    fi

    # Check if npm is installed
    if ! check_command "npm"; then
        print_error "npm is required but not installed"
        exit 1
    fi

    print_info "Node version: $(node --version)"
    print_info "npm version: $(npm --version)"

    # Navigate to frontend directory
    cd "$ROOT_DIR/frontend"

    # Check if package.json exists
    if [ ! -f "package.json" ]; then
        print_error "package.json not found in frontend directory"
        exit 1
    fi

    # Install dependencies
    print_step "Installing frontend dependencies..."
    if [ "$PRODUCTION" = true ]; then
        npm ci --production
    else
        npm ci
    fi

    # Build frontend
    print_step "Building frontend application..."
    if [ "$PRODUCTION" = true ]; then
        NODE_ENV=production npm run build
    else
        npm run build
    fi

    print_step "Frontend build completed successfully"
    echo ""
else
    print_warning "Skipping frontend build"
    echo ""
fi

# ============================================
# SETUP BACKEND
# ============================================

if [ "$SKIP_BACKEND" = false ]; then
    print_header "Setting Up Backend (Python)"

    # Check if Python is installed
    if ! check_command "python3" && ! check_command "python"; then
        print_error "Python is required but not installed"
        exit 1
    fi

    # Determine Python command
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        PYTHON_CMD="python"
    fi

    print_info "Python version: $($PYTHON_CMD --version)"

    # Navigate to backend directory
    cd "$ROOT_DIR/backend"

    # Check if requirements.txt exists
    if [ ! -f "requirements.txt" ]; then
        print_error "requirements.txt not found in backend directory"
        exit 1
    fi

    # Check if virtual environment exists
    if [ -d "venv" ] || [ -d "../venv" ]; then
        print_info "Virtual environment detected"

        # Activate virtual environment
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            print_step "Activated virtual environment: venv/"
        elif [ -f "../venv/bin/activate" ]; then
            source ../venv/bin/activate
            print_step "Activated virtual environment: ../venv/"
        fi
    else
        print_warning "No virtual environment found. Consider creating one:"
        print_info "  python3 -m venv venv"
        print_info "  source venv/bin/activate"
        echo ""
    fi

    # Install Python dependencies
    print_step "Installing backend dependencies..."
    $PYTHON_CMD -m pip install --upgrade pip -q
    $PYTHON_CMD -m pip install -r requirements.txt -q

    print_step "Backend setup completed successfully"
    echo ""
else
    print_warning "Skipping backend setup"
    echo ""
fi

# ============================================
# INITIALIZE DATABASE
# ============================================

if [ "$SKIP_DB" = false ]; then
    print_header "Initializing Database"

    cd "$ROOT_DIR/backend"

    # Check if database.py exists
    if [ ! -f "database.py" ]; then
        print_warning "database.py not found, skipping database initialization"
    else
        print_step "Running database initialization..."
        $PYTHON_CMD database.py
        print_step "Database initialized successfully"
    fi

    echo ""
else
    print_warning "Skipping database initialization"
    echo ""
fi

# ============================================
# BUILD SUMMARY
# ============================================

END_TIME=$(date +%s)
BUILD_TIME=$((END_TIME - START_TIME))

print_header "Build Summary"

echo -e "${GREEN}✓ Build completed successfully${NC}"
echo ""
echo "Build Details:"
echo "  • Frontend:  $([ "$SKIP_FRONTEND" = false ] && echo "✓ Built" || echo "⊗ Skipped")"
echo "  • Backend:   $([ "$SKIP_BACKEND" = false ] && echo "✓ Set up" || echo "⊗ Skipped")"
echo "  • Database:  $([ "$SKIP_DB" = false ] && echo "✓ Initialized" || echo "⊗ Skipped")"
echo "  • Build time: ${BUILD_TIME}s"
echo ""

if [ "$PRODUCTION" = true ]; then
    print_info "Production build artifacts:"
    echo "  • Frontend: $ROOT_DIR/frontend/.next/"
    echo "  • Backend:  $ROOT_DIR/backend/"
    echo ""
fi

print_info "Next steps:"
if [ "$PRODUCTION" = true ]; then
    echo "  1. Configure environment variables (copy .env.example to .env)"
    echo "  2. Deploy frontend: cd frontend && npm run start"
    echo "  3. Deploy backend: cd backend && python app.py"
else
    echo "  1. Start development servers:"
    echo "     • Frontend: cd frontend && npm run dev"
    echo "     • Backend:  cd backend && python app.py"
    echo "  2. Or use: make start-dev (if Makefile is available)"
fi

echo ""
print_step "All done! 🎉"
