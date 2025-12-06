"""
Async load testing with real hardware

This test requires connection to an actual device.
Configure connection settings via environment variables:
- MOMONGA_ROUTEB_ID: Route-B ID
- MOMONGA_ROUTEB_PASSWORD: Route-B Password
- MOMONGA_DEV_PATH: Device path (e.g., COM3, /dev/ttyUSB0)
- MOMONGA_DEV_BAUDRATE: Baudrate (default: 115200)

Example usage:
    python -m pytest tests/test_async_load.py -v -s
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
class TestAsyncMomongaLoad(unittest.IsolatedAsyncioTestCase):
    """Async load testing with real hardware"""
    
    @classmethod
    def setUpClass(cls):
        """Test class setup - get connection parameters"""
        try:
            cls.conn_params = get_connection_params()
        except ValueError as e:
            raise unittest.SkipTest(str(e))
    
    async def test_full_load_scenario(self):
        """
        Execute all load tests in a single session
        This reuses the connection for all tests, simulating a long-running application
        """
        print("\n=== Starting Full Load Scenario ===")

        async with AsyncMomonga(**self.conn_params) as amo:
            with self.subTest("Sequential Requests"):
                await self._run_sequential_requests(amo)

            with self.subTest("Concurrent Requests (Same Property)"):
                await self._run_concurrent_requests_same_property(amo)

            with self.subTest("Concurrent Requests (Different Properties)"):
                await self._run_concurrent_requests_different_properties(amo)

            with self.subTest("Burst Requests"):
                await self._run_burst_requests(amo)

            with self.subTest("Error Handling"):
                await self._run_error_handling_under_load(amo)

            with self.subTest("Long Running Monitoring"):
                await self._run_long_running_monitoring(amo)

    async def _run_sequential_requests(self, amo):
        """
        Sequential request benchmark
        Measure performance when executing sequentially even with async version
        """
        print("\n=== Sequential Request Test ===")
        
        start = time.time()
        
        # Sequential requests
        results = []
        for i in range(20):
            power = await amo.get_instantaneous_power()
            results.append(power)
            print(f"  Request {i+1}: {power}W")
        
        elapsed = time.time() - start
        
        print(f"\n  Total requests: {len(results)}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Average time/request: {elapsed/len(results):.2f}s")
        
        self.assertEqual(len(results), 20)
    
    async def _run_concurrent_requests_same_property(self, amo):
        """
        Concurrent requests test for the same property
        Execute concurrently using asyncio.gather
        """
        print("\n=== Concurrent Request Test (Same Property) ===")
        
        start = time.time()
        
        # Issue concurrent requests
        tasks = [
            amo.get_instantaneous_power()
            for _ in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start
        
        print(f"\n  Total requests: {len(results)}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Average time/request: {elapsed/len(results):.2f}s")
        print(f"  Result samples: {results[:3]}")
        
        self.assertEqual(len(results), 20)
        # Verify that all results are numeric
        for power in results:
            self.assertIsInstance(power, (int, float))
    
    async def _run_concurrent_requests_different_properties(self, amo):
        """
        Concurrent requests test for different properties
        Execute multiple different methods concurrently
        """
        print("\n=== Concurrent Request Test (Different Properties) ===")
        
        start = time.time()
        
        # Base set of different property requests
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
        
        # Create a larger list of tasks by repeating the base set
        # This tests the queue's handling of heterogeneous requests under load
        tasks = []
        for _ in range(5):  # Repeat 5 times
            for task_func in base_tasks:
                tasks.append(task_func())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.time() - start
        
        print(f"\n  Total requests: {len(results)}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Average time/request: {elapsed/len(results):.2f}s")
        
        # Verify results
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        print(f"  Successes: {success_count}")
        print(f"  Failures: {len(results) - success_count}")
        
        self.assertGreater(success_count, 0, "At least one request should succeed")
        self.assertEqual(len(results), len(base_tasks) * 5)
    
    async def _run_burst_requests(self, amo):
        """
        Burst request test
        Issue a large number of requests in a short time to verify system stability
        """
        print("\n=== Burst Request Test ===")
        
        start = time.time()
        
        # Concurrent requests
        num_requests = 50
        tasks = [
            amo.get_instantaneous_power()
            for _ in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        
        # Count successes and failures
        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]
        
        print(f"\n  Total requests: {len(results)}")
        print(f"  Successes: {len(successes)}")
        print(f"  Failures: {len(failures)}")
        print(f"  Total time: {elapsed:.2f}s")
        print(f"  Throughput: {len(successes)/elapsed:.2f} req/sec")
        
        if failures:
            print(f"\n  Error sample: {failures[0]}")
        
        # Verify success rate is above 50% (not too strict)
        success_rate = len(successes) / len(results)
        self.assertGreater(success_rate, 0.5, 
                            f"Success rate too low: {success_rate*100:.1f}%")
    
    async def _run_long_running_monitoring(self, amo):
        """
        Long-running monitoring test
        Practical scenario of continuously acquiring data periodically
        """
        print("\n=== Long-Running Monitoring Test ===")
        
        duration_seconds = 120
        interval_seconds = 6
        
        start = time.time()
        results = []
        
        print(f"  Acquiring data every {interval_seconds}s for {duration_seconds}s...")
        
        while time.time() - start < duration_seconds:
            loop_start_time = time.time()
            try:
                power = await amo.get_instantaneous_power()
                current_time = time.time() - start
                results.append({
                    'time': current_time,
                    'power': power
                })
                print(f"    {current_time:.1f}s: {power}W")
                
            except Exception as e:
                print(f"    Error: {e}")
            
            # Adjust sleep time to maintain interval
            elapsed_in_loop = time.time() - loop_start_time
            sleep_time = max(0, interval_seconds - elapsed_in_loop)
            await asyncio.sleep(sleep_time)
        
        print(f"\n  Data points acquired: {len(results)}")
        if results:
            powers = [r['power'] for r in results]
            print(f"  Average power: {sum(powers)/len(powers):.2f}W")
            print(f"  Max power: {max(powers):.2f}W")
            print(f"  Min power: {min(powers):.2f}W")
        
        expected_count = duration_seconds // interval_seconds
        # Allow some deviation (±2 times)
        self.assertGreater(len(results), expected_count - 2)
    
    async def _run_error_handling_under_load(self, amo):
        """
        Error handling test under load
        Verify that partial failures during concurrent execution don't affect other requests
        """
        print("\n=== Error Handling Test ===")
        
        # Mix normal requests with requests that may fail
        tasks = [
            amo.get_instantaneous_power(),
            amo.get_instantaneous_current(),
            amo.get_measured_cumulative_energy(),
            amo.get_measured_cumulative_energy(reverse=True),
            amo.get_operation_status(),
            # Include operations that may cause errors, like setting non-existent properties
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        
        print(f"\n  Successes: {successes}")
        print(f"  Failures: {failures}")
        
        # Verify at least half succeeded
        self.assertGreater(successes, len(tasks) // 2)


if __name__ == '__main__':
    # Display usage help
    print(__doc__)
    unittest.main()
