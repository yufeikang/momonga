import asyncio
import os
import sys
import logging
from momonga import AsyncMomonga
from momonga.momonga_exception import (
    MomongaSkScanFailure,
    MomongaSkJoinFailure,
    MomongaNeedToReopen
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    rbid = os.environ.get('MOMONGA_ROUTEB_ID')
    pwd = os.environ.get('MOMONGA_ROUTEB_PASSWORD')
    dev = os.environ.get('MOMONGA_DEV_PATH')

    if not all([rbid, pwd, dev]):
        print("Please set environment variables: MOMONGA_ROUTEB_ID, MOMONGA_ROUTEB_PASSWORD, MOMONGA_DEV_PATH", file=sys.stderr)
        return

    print(f"Starting async monitoring loop on {dev}...")

    while True:
        try:
            print("Connecting...")
            async with AsyncMomonga(rbid, pwd, dev) as amo:
                print("Connected. Starting measurement loop.")
                
                while True:
                    val = await amo.get_instantaneous_power()
                    print(f"Instantaneous Power: {val}W")
                    await asyncio.sleep(60)

        except (MomongaSkScanFailure, MomongaSkJoinFailure, MomongaNeedToReopen) as e:
            print(f"Connection lost or reset required: {e}", file=sys.stderr)
            print("Retrying in 300 seconds...", file=sys.stderr)
            await asyncio.sleep(300)

        except Exception as e:
            print(f"Unexpected error: {e}", file=sys.stderr)
            print("Retrying in 600 seconds...", file=sys.stderr)
            await asyncio.sleep(600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user.")
