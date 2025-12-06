#!/bin/bash
#
# Async load test runner for Momonga
# 
# Usage:
#   ./run_async_load_test.sh
#
# Make sure to set environment variables before running:
#   export MOMONGA_ROUTEB_ID="your_route_b_id"
#   export MOMONGA_ROUTEB_PASSWORD="your_password"
#   export MOMONGA_DEV_PATH="COM3"  # or /dev/ttyUSB0
#   export MOMONGA_DEV_BAUDRATE="115200"  # optional, defaults to 115200

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Momonga Async Load Test Runner ===${NC}\n"

# Check required environment variables
if [ -z "$MOMONGA_ROUTEB_ID" ] || [ -z "$MOMONGA_ROUTEB_PASSWORD" ] || [ -z "$MOMONGA_DEV_PATH" ]; then
    echo -e "${RED}Error: Missing required environment variables${NC}"
    echo "Please set:"
    echo "  MOMONGA_ROUTEB_ID"
    echo "  MOMONGA_ROUTEB_PASSWORD"
    echo "  MOMONGA_DEV_PATH"
    echo ""
    echo "Example:"
    echo "  export MOMONGA_ROUTEB_ID=\"your_route_b_id\""
    echo "  export MOMONGA_ROUTEB_PASSWORD=\"your_password\""
    echo "  export MOMONGA_DEV_PATH=\"COM3\""
    exit 1
fi

# Display configuration
echo -e "${YELLOW}Configuration:${NC}"
echo "  RBID: ${MOMONGA_ROUTEB_ID}"
echo "  Device: ${MOMONGA_DEV_PATH}"
echo "  Baudrate: ${MOMONGA_DEV_BAUDRATE:-115200}"
echo ""

# Run the tests
echo -e "${GREEN}Running async load tests...${NC}\n"

python -m pytest tests/test_async_load.py -v -s

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
else
    echo -e "\n${RED}✗ Some tests failed${NC}"
    exit 1
fi
