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
    
    async def test_sequential_requests(self):
        """
        Sequential request benchmark
        Measure performance when executing sequentially even with async version
        """
        print("\n=== Sequential Request Test ===")
        
        async with AsyncMomonga(**self.conn_params) as amo:
            start = time.time()
            
            # 5 sequential requests
            results = []
            for i in range(5):
                power = await amo.get_instantaneous_power()
                results.append(power)
                print(f"  Request {i+1}: {power}W")
            
            elapsed = time.time() - start
            
            print(f"\n  Total requests: {len(results)}")
            print(f"  Total time: {elapsed:.2f}s")
            print(f"  Average time/request: {elapsed/len(results):.2f}s")
            
            self.assertEqual(len(results), 5)
    
    async def test_concurrent_requests_same_property(self):
        """
        Concurrent requests test for the same property
        Execute concurrently using asyncio.gather
        """
        print("\n=== Concurrent Request Test (Same Property) ===")
        
        async with AsyncMomonga(**self.conn_params) as amo:
            start = time.time()
            
            # Issue 5 concurrent requests
            tasks = [
                amo.get_instantaneous_power()
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            elapsed = time.time() - start
            
            print(f"\n  Total requests: {len(results)}")
            print(f"  Total time: {elapsed:.2f}s")
            print(f"  Average time/request: {elapsed/len(results):.2f}s")
            print(f"  Result samples: {results[:3]}")
            
            self.assertEqual(len(results), 5)
            # Verify that all results are numeric
            for power in results:
                self.assertIsInstance(power, (int, float))
    
    async def test_concurrent_requests_different_properties(self):
        """
        Concurrent requests test for different properties
        Execute multiple different methods concurrently
        """
        print("\n=== Concurrent Request Test (Different Properties) ===")
        
        async with AsyncMomonga(**self.conn_params) as amo:
            start = time.time()
            
            # Get different properties concurrently
            results = await asyncio.gather(
                amo.get_instantaneous_power(),
                amo.get_instantaneous_current(),
                amo.get_measured_cumulative_energy(),
                amo.get_operation_status(),
                amo.get_coefficient_for_cumulative_energy(),
                amo.get_unit_for_cumulative_energy(),
                return_exceptions=True  # Get other results even if there are errors
            )
            
            elapsed = time.time() - start
            
            print(f"\n  Total requests: {len(results)}")
            print(f"  Total time: {elapsed:.2f}s")
            print(f"  Average time/request: {elapsed/len(results):.2f}s")
            
            # Display results
            labels = [
                "Instantaneous Power",
                "Instantaneous Current",
                "Cumulative Energy",
                "Operation Status",
                "Coefficient",
                "Unit"
            ]
            
            for label, result in zip(labels, results):
                if isinstance(result, Exception):
                    print(f"  {label}: Error - {result}")
                else:
                    print(f"  {label}: {result}")
            
            # Verify that at least one succeeded
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            self.assertGreater(success_count, 0, "At least one request should succeed")
    
    async def test_burst_requests(self):
        """
        Burst request test
        Issue a large number of requests in a short time to verify system stability
        """
        print("\n=== Burst Request Test ===")
        
        async with AsyncMomonga(**self.conn_params) as amo:
            start = time.time()
            
            # 10 concurrent requests
            num_requests = 10
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
    
    async def test_long_running_monitoring(self):
        """
        Long-running monitoring test
        Practical scenario of continuously acquiring data periodically
        """
        print("\n=== Long-Running Monitoring Test ===")
        
        duration_seconds = 30
        interval_seconds = 5
        
        async with AsyncMomonga(**self.conn_params) as amo:
            start = time.time()
            results = []
            
            print(f"  Acquiring data every {interval_seconds}s for {duration_seconds}s...")
            
            while time.time() - start < duration_seconds:
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
                
                await asyncio.sleep(interval_seconds)
            
            print(f"\n  Data points acquired: {len(results)}")
            if results:
                powers = [r['power'] for r in results]
                print(f"  Average power: {sum(powers)/len(powers):.2f}W")
                print(f"  Max power: {max(powers):.2f}W")
                print(f"  Min power: {min(powers):.2f}W")
            
            expected_count = duration_seconds // interval_seconds
            # Allow some deviation (±2 times)
            self.assertGreater(len(results), expected_count - 2)
    
    async def test_error_handling_under_load(self):
        """
        Error handling test under load
        Verify that partial failures during concurrent execution don't affect other requests
        """
        print("\n=== Error Handling Test ===")
        
        async with AsyncMomonga(**self.conn_params) as amo:
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
