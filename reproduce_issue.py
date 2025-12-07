
import asyncio
import unittest
import logging
from concurrent.futures import ThreadPoolExecutor
from momonga.momonga_aio import AsyncMomonga
from momonga.momonga_exception import MomongaNeedToReopen

# Mock Momonga synchronous client
class MockMomonga:
    def __init__(self, *args, **kwargs):
        pass
    def open(self):
        pass
    def close(self):
        pass
    def get_instantaneous_power(self):
        return 123.45

# Patch AsyncMomonga to use MockMomonga
import momonga.momonga_aio
momonga.momonga_aio.Momonga = MockMomonga

class TestAsyncMomongaRepro(unittest.IsolatedAsyncioTestCase):
    async def test_error_handling(self):
        print("=== Starting Repro Test ===")
        amo = AsyncMomonga("rbid", "pwd", "dev")
        await amo.open()

        def failing_sync():
            raise MomongaNeedToReopen("Simulated connection failure")

        print("  [Step 1] Submitting failing task...")
        with self.assertRaises(MomongaNeedToReopen):
            await amo._run_in_executor(failing_sync)
        print("  [Pass] Exception propagated correctly")

        # Check if worker is alive
        if amo._worker.done():
            print("DEBUG: Worker is DONE after exception!")
            try:
                await amo._worker
            except BaseException as e:
                print(f"DEBUG: Worker exception: {type(e).__name__}: {e}")
        else:
            print("DEBUG: Worker is still running.")

        print("  [Step 2] Verifying worker recovery...")
        try:
            res = await amo.get_instantaneous_power()
            print(f"  [Pass] Worker recovered, result: {res}")
        except Exception as e:
            print(f"FAIL: {e}")
            import traceback
            traceback.print_exc()
            raise

        await amo.close()

if __name__ == '__main__':
    unittest.main()
