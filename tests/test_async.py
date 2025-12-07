"""
Async integration testing with real hardware

This test suite verifies the stability, concurrency, and error handling of the AsyncMomonga client.
It requires connection to an actual device.
Configure connection settings via environment variables:
- MOMONGA_ROUTEB_ID: Route-B ID
- MOMONGA_ROUTEB_PASSWORD: Route-B Password
- MOMONGA_DEV_PATH: Device path (e.g., COM3, /dev/ttyUSB0)
- MOMONGA_DEV_BAUDRATE: Baudrate (default: 115200)

Example usage:
    python -m pytest tests/test_async.py -v -s
"""

import asyncio
import logging
import os
import time
import unittest
from typing import List, Dict, Any
from momonga import AsyncMomonga
import momonga

# Configure logging to display warnings and errors
log_fmt = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s - %(message)s')
log_hnd = logging.StreamHandler()
log_hnd.setFormatter(log_fmt)
momonga.logger.addHandler(log_hnd)
momonga.logger.setLevel(logging.WARNING)
momonga.session_manager_logger.addHandler(log_hnd)
momonga.session_manager_logger.setLevel(logging.WARNING)
momonga.sk_wrapper_logger.addHandler(log_hnd)
momonga.sk_wrapper_logger.setLevel(logging.WARNING)


def get_connection_params() -> Dict[str, Any]:
    """Get connection parameters from environment variables"""
    rbid = os.getenv('MOMONGA_ROUTEB_ID')
    pwd = os.getenv('MOMONGA_ROUTEB_PASSWORD')
    dev = os.getenv('MOMONGA_DEV_PATH')
    baudrate = int(os.getenv('MOMONGA_DEV_BAUDRATE', '115200'))

    if not all([rbid, pwd, dev]):
        raise ValueError(
            "Please set environment variables: MOMONGA_ROUTEB_ID, MOMONGA_ROUTEB_PASSWORD, MOMONGA_DEV_PATH"
        )

    return {
        'rbid': rbid,
        'pwd': pwd,
        'dev': dev,
        'baudrate': baudrate,
    }

class TestAsyncMomonga(unittest.IsolatedAsyncioTestCase):
    """Async integration testing with real hardware"""

    @classmethod
    def setUpClass(cls):
        """Test class setup - get connection parameters"""
        try:
            cls.conn_params = get_connection_params()
        except ValueError as e:
            raise unittest.SkipTest(str(e))

    async def test_full_load_scenario(self):
        """
        Execute all integration tests in a single session
        This reuses the connection for all tests, simulating a long-running application
        """
        print("=== Starting Full Async Integration Scenario ===")

        async with AsyncMomonga(**self.conn_params) as amo:
            with self.subTest("Burst Requests"):
                await self._run_burst_requests(amo)
            
            with self.subTest("Concurrent Requests"):
                await self._run_concurrent_requests(amo)

            with self.subTest("Error Handling"):
                await self._run_error_handling(amo)

            with self.subTest("Cancellation Tolerance"):
                await self._run_cancellation_test(amo)

            with self.subTest("Concurrent Monitoring Loops"):
                await self._run_concurrent_monitoring_loops(amo)

    async def _run_concurrent_monitoring_loops(self, amo):
        """
        Practical concurrent monitoring test
        Simulate a real application with multiple independent monitoring loops.
        
        This test verifies that multiple monitoring loops can coexist without
        crashing or deadlocking, even if the device is slow.
        We are not testing throughput here, but stability.
        """
        print("=== Concurrent Monitoring Loops Test ===")
        
        duration = 120
        results = {'power': [], 'energy': []}
        
        async def monitor_power():
            interval = 10.0
            end_time = time.time() + duration
            while time.time() < end_time:
                loop_start = time.time()
                try:
                    val = await amo.get_instantaneous_power()
                    results['power'].append((time.time(), val))
                    print(f"    [Power] {val}W")
                except Exception as e:
                    print(f"    [Power] Error: {e}")
                
                elapsed = time.time() - loop_start
                await asyncio.sleep(max(0, interval - elapsed))

        async def monitor_energy():
            interval = 30.0
            end_time = time.time() + duration
            while time.time() < end_time:
                loop_start = time.time()
                try:
                    val = await amo.get_measured_cumulative_energy()
                    results['energy'].append((time.time(), val))
                    print(f"    [Energy] {val}kWh")
                except Exception as e:
                    print(f"    [Energy] Error: {e}")
                
                elapsed = time.time() - loop_start
                await asyncio.sleep(max(0, interval - elapsed))

        print(f"  Starting concurrent monitoring for {duration}s...")
        await asyncio.gather(monitor_power(), monitor_energy())
        print(f"  Power samples: {len(results['power'])}")
        print(f"  Energy samples: {len(results['energy'])}")

        self.assertGreater(len(results['power']), 0, "Should have received at least one power sample")
        self.assertGreater(len(results['energy']), 0, "Should have received at least one energy sample")

    async def _run_concurrent_requests(self, amo):
        """
        Concurrent requests test
        Execute multiple different methods concurrently
        """
        print("=== Concurrent Request Test ===")
        start = time.time()

        base_tasks = [
            amo.get_instantaneous_power,
            amo.get_instantaneous_current,
            amo.get_measured_cumulative_energy,
            amo.get_operation_status,
            amo.get_coefficient_for_cumulative_energy,
            amo.get_unit_for_cumulative_energy,
            amo.get_number_of_effective_digits_for_cumulative_energy,
            amo.get_cumulative_energy_measured_at_fixed_time,
        ]

        tasks = []
        for _ in range(5):
            for task_func in base_tasks:
                tasks.append(task_func())

        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        print(f"  Total requests: {len(results)}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Average time/request: {elapsed/len(results):.2f}s")

        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"  Successes: {success_count}")
        print(f"  Failures: {len(results) - success_count}")

        self.assertEqual(success_count, len(base_tasks) * 5, "All requests should succeed")

    async def _run_burst_requests(self, amo):
        """
        Burst request test
        Issue a large number of requests in a short time to verify system stability
        """
        print("=== Burst Request Test ===")
        start = time.time()

        num_requests = 50
        tasks = [
            amo.get_instantaneous_power()
            for _ in range(num_requests)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start

        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]

        print(f"  Total requests: {len(results)}")
        print(f"  Successes: {len(successes)}")
        print(f"  Failures: {len(failures)}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Throughput: {len(successes)/elapsed:.2f} req/sec")

        if failures:
            print(f"  Error sample: {failures[0]}")

        self.assertEqual(len(successes), len(results), "All burst requests should succeed")

    async def _run_error_handling(self, amo):
        print("\n  --- Testing Error Handling ---")

        def failing_sync():
            raise ValueError("Simulated connection failure")

        # 1. Verify exception propagation
        print("  [Step 1] Submitting failing task...")
        with self.assertRaises(ValueError):
            await amo._run_in_executor(failing_sync)
        print("  [Pass] Exception propagated correctly")

        # 2. Verify worker recovery
        print("  [Step 2] Verifying worker recovery...")

        try:
            # Use a simple read command
            res = await amo.get_instantaneous_power()
            print(f"  [Pass] Worker recovered, result: {res}")
        except Exception as e:
            self.fail(f"Worker failed to recover: {e}")

    async def _run_cancellation_test(self, amo):
        print("\n  --- Testing Cancellation Tolerance ---")
        
        # 1. Start a task and cancel it immediately
        print("  [Step 1] Starting and cancelling a task...")
        task = asyncio.create_task(amo.get_instantaneous_power())
        await asyncio.sleep(0.01) # Give it a tiny moment to start
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            print("  [Pass] Task cancelled successfully")
        except Exception as e:
            self.fail(f"Task failed with unexpected exception: {e}")

        # 2. Verify worker is still alive and can process new requests
        print("  [Step 2] Verifying worker survival...")
        try:
            res = await amo.get_instantaneous_power()
            print(f"  [Pass] Worker survived cancellation, result: {res}")
        except Exception as e:
            self.fail(f"Worker died after cancellation: {e}")

if __name__ == '__main__':
    # Display usage help
    print(__doc__)
    unittest.main()
