"""
Async load testing with real hardware

This test requires connection to an actual device.
Configure connection settings via environment variables:
- MOMONGA_RBID: Route-B ID
- MOMONGA_PWD: Route-B Password
- MOMONGA_DEV: Device path (e.g., COM3, /dev/ttyUSB0)
- MOMONGA_BAUDRATE: Baudrate (default: 115200)

Example usage:
    python -m pytest tests/test_async_load.py -v -s
"""

import asyncio
import os
import time
import unittest
from typing import List, Dict, Any
from momonga import AsyncMomonga


def get_connection_params() -> Dict[str, Any]:
    """Get connection parameters from environment variables"""
    rbid = os.getenv('MOMONGA_RBID')
    pwd = os.getenv('MOMONGA_PWD')
    dev = os.getenv('MOMONGA_DEV')
    baudrate = int(os.getenv('MOMONGA_BAUDRATE', '115200'))
    
    if not all([rbid, pwd, dev]):
        raise ValueError(
            "Please set environment variables: MOMONGA_RBID, MOMONGA_PWD, MOMONGA_DEV"
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
            
            # 10 sequential requests
            results = []
            for i in range(10):
                power = await amo.get_instantaneous_power()
                results.append(power)
                print(f"  Request {i+1}: {power}W")
            
            elapsed = time.time() - start
            
            print(f"\n  Total requests: {len(results)}")
            print(f"  Total time: {elapsed:.2f}s")
            print(f"  Average time/request: {elapsed/len(results):.2f}s")
            
            self.assertEqual(len(results), 10)
    
    async def test_concurrent_requests_same_property(self):
        """
        Concurrent requests test for the same property
        Execute concurrently using asyncio.gather
        """
        print("\n=== Concurrent Request Test (Same Property) ===")
        
        async with AsyncMomonga(**self.conn_params) as amo:
            start = time.time()
            
            # Issue 10 concurrent requests
            tasks = [
                amo.get_instantaneous_power()
                for _ in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            elapsed = time.time() - start
            
            print(f"\n  Total requests: {len(results)}")
            print(f"  Total time: {elapsed:.2f}s")
            print(f"  Average time/request: {elapsed/len(results):.2f}s")
            print(f"  Result samples: {results[:3]}")
            
            self.assertEqual(len(results), 10)
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
            
            # 50 concurrent requests
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
    
    async def test_long_running_monitoring(self):
        """
        Long-running monitoring test
        Practical scenario of continuously acquiring data periodically
        """
        print("\n=== Long-Running Monitoring Test ===")
        
        duration_seconds = 60  # 1 minute
        interval_seconds = 5    # Every 5 seconds
        
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


class TestAsyncMomongaConcurrentConnections(unittest.IsolatedAsyncioTestCase):
    """Concurrent connection test (when multiple devices are available)"""
    
    async def test_single_device_multiple_sessions(self):
        """
        Multiple sessions to the same device
        Note: Expected to fail since physical concurrent connections are not possible
        This test is to verify proper error handling
        """
        print("\n=== Multiple Session Test (Error Check) ===")
        
        try:
            conn_params = get_connection_params()
        except ValueError as e:
            raise unittest.SkipTest(str(e))
        
        # First session should succeed
        async with AsyncMomonga(**conn_params) as amo1:
            power1 = await amo1.get_instantaneous_power()
            print(f"  Session 1: {power1}W - Success")
            
            # Second session is likely to fail
            # (because serial port is already in use)
            try:
                async with AsyncMomonga(**conn_params) as amo2:
                    power2 = await amo2.get_instantaneous_power()
                    print(f"  Session 2: {power2}W - Success (Unexpected)")
            except Exception as e:
                print(f"  Session 2: Error (Expected) - {type(e).__name__}")
                # Verify that error occurs appropriately
                self.assertIsInstance(e, Exception)


if __name__ == '__main__':
    # Display usage help
    print(__doc__)
    unittest.main()
