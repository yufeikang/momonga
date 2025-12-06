#!/bin/bash
#
# Async load test runner for Momonga
# 
# Usage:
#   ./run_async_load_test.sh
#
# Make sure to set environment variables before running:
#   export MOMONGA_RBID="your_route_b_id"
#   export MOMONGA_PWD="your_password"
#   export MOMONGA_DEV="COM3"  # or /dev/ttyUSB0
#   export MOMONGA_BAUDRATE="115200"  # optional, defaults to 115200

set -e  # Exit on error

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Momonga Async Load Test Runner ===${NC}\n"

# Check required environment variables
if [ -z "$MOMONGA_RBID" ] || [ -z "$MOMONGA_PWD" ] || [ -z "$MOMONGA_DEV" ]; then
    echo -e "${RED}Error: Missing required environment variables${NC}"
    echo "Please set:"
    echo "  MOMONGA_RBID"
    echo "  MOMONGA_PWD"
    echo "  MOMONGA_DEV"
    echo ""
    echo "Example:"
    echo "  export MOMONGA_RBID=\"your_route_b_id\""
    echo "  export MOMONGA_PWD=\"your_password\""
    echo "  export MOMONGA_DEV=\"COM3\""
    exit 1
fi

# Display configuration
echo -e "${YELLOW}Configuration:${NC}"
echo "  RBID: ${MOMONGA_RBID}"
echo "  Device: ${MOMONGA_DEV}"
echo "  Baudrate: ${MOMONGA_BAUDRATE:-115200}"
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
