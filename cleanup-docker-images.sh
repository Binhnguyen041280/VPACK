#!/bin/bash
# ============================================================================
# ePACK Docker - Image Cleanup Script
# Removes old/duplicate Docker images, keeps production images
# ============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🧹 ePACK Docker - Image Cleanup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Show current disk usage
echo -e "${CYAN}📊 Current Docker Disk Usage:${NC}"
docker system df
echo ""

# Show current images
echo -e "${CYAN}📦 Current VTrack Images:${NC}"
docker images | grep -E "REPOSITORY|vtrack"
echo ""

# Parse command line arguments
DRY_RUN=false
AUTO_CONFIRM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run|-d)
            DRY_RUN=true
            shift
            ;;
        --yes|-y)
            AUTO_CONFIRM=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./cleanup-docker-images.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --dry-run, -d    Show what would be removed without removing"
            echo "  --yes, -y        Auto-confirm removal (skip prompts)"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Images to be removed:"
            echo "  - epack-backend:v2 (duplicate of phase2)"
            echo "  - epack-backend:fixed (old version)"
            echo "  - epack-frontend:production (old version)"
            echo "  - epack-frontend-deps:latest (build artifact)"
            echo ""
            echo "Images to be kept:"
            echo "  ✅ epack-backend:phase2 (production)"
            echo "  ✅ epack-frontend:phase3 (production)"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run './cleanup-docker-images.sh --help' for usage"
            exit 1
            ;;
    esac
done

# Define images to remove
IMAGES_TO_REMOVE=(
    "epack-backend:v2"
    "epack-backend:fixed"
    "epack-frontend:production"
    "epack-frontend-deps:latest"
)

# Define production images (must keep)
PRODUCTION_IMAGES=(
    "epack-backend:phase2"
    "epack-frontend:phase3"
)

echo -e "${YELLOW}⚠️  Images to be removed:${NC}"
for img in "${IMAGES_TO_REMOVE[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$img$"; then
        SIZE=$(docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "^$img" | awk '{print $2}')
        echo "  ❌ $img ($SIZE)"
    else
        echo "  ⚠️  $img (not found, skip)"
    fi
done
echo ""

echo -e "${GREEN}✅ Production images (will be kept):${NC}"
for img in "${PRODUCTION_IMAGES[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$img$"; then
        SIZE=$(docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}" | grep "^$img" | awk '{print $2}')
        echo "  ✅ $img ($SIZE)"
    else
        echo -e "  ${RED}⚠️  $img (NOT FOUND - needs rebuild!)${NC}"
    fi
done
echo ""

# Calculate space to be freed
TOTAL_SIZE=0
for img in "${IMAGES_TO_REMOVE[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$img$"; then
        SIZE_BYTES=$(docker image inspect "$img" --format='{{.Size}}' 2>/dev/null || echo "0")
        TOTAL_SIZE=$((TOTAL_SIZE + SIZE_BYTES))
    fi
done

# Convert to human readable
if [ $TOTAL_SIZE -gt 1073741824 ]; then
    TOTAL_SIZE_HUMAN=$(echo "scale=2; $TOTAL_SIZE / 1073741824" | bc)"GB"
elif [ $TOTAL_SIZE -gt 1048576 ]; then
    TOTAL_SIZE_HUMAN=$(echo "scale=2; $TOTAL_SIZE / 1048576" | bc)"MB"
else
    TOTAL_SIZE_HUMAN="${TOTAL_SIZE} bytes"
fi

echo -e "${CYAN}💾 Estimated space to be freed: $TOTAL_SIZE_HUMAN${NC}"
echo ""

# Dry run mode
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}🔍 DRY RUN MODE - No images will be removed${NC}"
    echo ""
    echo -e "${GREEN}✅ Dry run complete. Run without --dry-run to actually remove images.${NC}"
    exit 0
fi

# Confirmation prompt
if [ "$AUTO_CONFIRM" = false ]; then
    echo -e "${YELLOW}⚠️  WARNING: This will permanently remove the images listed above.${NC}"
    echo -e "${YELLOW}   Production images (phase2, phase3) will NOT be removed.${NC}"
    echo ""
    read -p "Continue with cleanup? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo -e "${YELLOW}❌ Cleanup cancelled${NC}"
        exit 0
    fi
    echo ""
fi

# Perform cleanup
echo -e "${BLUE}🗑️  Removing old images...${NC}"
echo ""

REMOVED_COUNT=0
SKIPPED_COUNT=0

for img in "${IMAGES_TO_REMOVE[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$img$"; then
        echo -n "Removing $img... "
        if docker rmi "$img" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Removed${NC}"
            REMOVED_COUNT=$((REMOVED_COUNT + 1))
        else
            echo -e "${RED}❌ Failed (may be in use)${NC}"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        fi
    else
        echo -e "$img... ${YELLOW}⚠️  Not found, skipped${NC}"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    fi
done

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
echo -e "   Removed: $REMOVED_COUNT images"
echo -e "   Skipped: $SKIPPED_COUNT images"
echo ""

# Show final disk usage
echo -e "${CYAN}📊 Final Docker Disk Usage:${NC}"
docker system df
echo ""

# Show remaining images
echo -e "${CYAN}📦 Remaining VTrack Images:${NC}"
if docker images | grep -q vtrack; then
    docker images | grep -E "REPOSITORY|vtrack"
else
    echo -e "${YELLOW}⚠️  No vtrack images found${NC}"
fi
echo ""

# Verify production images still exist
echo -e "${CYAN}🔍 Verifying Production Images:${NC}"
ALL_GOOD=true
for img in "${PRODUCTION_IMAGES[@]}"; do
    if docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$img$"; then
        echo -e "  ✅ $img"
    else
        echo -e "  ${RED}❌ $img (MISSING!)${NC}"
        ALL_GOOD=false
    fi
done

if [ "$ALL_GOOD" = true ]; then
    echo ""
    echo -e "${GREEN}🎉 All production images are intact!${NC}"
else
    echo ""
    echo -e "${RED}⚠️  WARNING: Some production images are missing!${NC}"
    echo -e "${YELLOW}   Rebuild with:${NC}"
    echo "   docker build --platform linux/arm64 -t epack-backend:phase2 ./backend"
    echo "   docker build --platform linux/arm64 -t epack-frontend:phase3 ./frontend"
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Cleanup script finished${NC}"
