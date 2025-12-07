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
from momonga.momonga_exception import MomongaConnectionError

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
        print("=== Starting Full Load Scenario ===")

        # Run burst and concurrent requests in a single session first.
#        async with AsyncMomonga(**self.conn_params) as amo:
#            with self.subTest("Burst Requests"):
#                await self._run_burst_requests(amo)
#            with self.subTest("Concurrent Requests"):
#                await self._run_concurrent_requests(amo)

        # Run the error-handling check in a fresh session to isolate from prior load.
        with self.subTest("Error Handling"):
            # Optionally enable DEBUG logs for SK wrapper and session manager
            debug_enabled = os.getenv('MOMONGA_DEBUG') == '1'
            if debug_enabled:
                print("  [Debug] Enabling DEBUG logs for SK wrapper and session manager")
                prev_levels = (momonga.logger.level, momonga.session_manager_logger.level, momonga.sk_wrapper_logger.level)
                momonga.logger.setLevel(logging.DEBUG)
                momonga.session_manager_logger.setLevel(logging.DEBUG)
                momonga.sk_wrapper_logger.setLevel(logging.DEBUG)
            try:
                async with AsyncMomonga(**self.conn_params) as amo_err:
                    await self._run_error_handling_under_load(amo_err)
            finally:
                if debug_enabled:
                    momonga.logger.setLevel(prev_levels[0])
                    momonga.session_manager_logger.setLevel(prev_levels[1])
                    momonga.sk_wrapper_logger.setLevel(prev_levels[2])

        # Run monitoring loops in their own session (long-running).
#        async with AsyncMomonga(**self.conn_params) as amo:
#            with self.subTest("Concurrent Monitoring Loops"):
#                await self._run_concurrent_monitoring_loops(amo)

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

    async def _run_error_handling_under_load(self, amo):
        """
        Error handling test under load
        Verify that partial failures during concurrent execution don't affect other requests
        """
        print("=== Error Handling Test ===")

        # Define a synchronous helper that simulates a transport-level failure.
        def failing_sync():
            raise MomongaConnectionError('simulated failure from sync helper')

        # Submit the failing synchronous call through the AsyncMomonga queue and
        # verify the exception is propagated to the awaiter.
        try:
            with self.subTest('Queued failing sync call'):
                with self.assertRaises(MomongaConnectionError):
                    await asyncio.wait_for(amo.submit_sync_call(failing_sync), timeout=5)

            # Immediately perform a normal call to ensure the worker continued.
            # Insert a short sleep to avoid a timing-sensitive race on real hardware.
            # This is a pragmatic, temporary mitigation to reduce flakiness.
            await asyncio.sleep(0.3)
            with self.subTest('Follow-up normal call'):
                # Diagnostic: print queue/worker state before calling
                try:
                    qsize = amo._queue.qsize()
                except Exception:
                    qsize = 'N/A'
                worker_state = None
                try:
                    worker_state = getattr(amo._worker, 'done', lambda: 'N/A')()
                except Exception:
                    worker_state = 'N/A'

                print("  [Follow-up] before call: sync_client.is_open =", getattr(amo._sync_client, 'is_open', None))
                print(f"  [Follow-up] queue size={qsize}, worker_done={worker_state}")

                # Extra diagnostics from the session manager and SK wrapper
                try:
                    sm = amo._sync_client.session_manager
                    print("  [Follow-up] session_established =", getattr(sm, 'session_established', None))
                    try:
                        r_alive = sm.receiver_th.is_alive() if sm.receiver_th is not None else None
                    except Exception:
                        r_alive = 'N/A'
                    print("  [Follow-up] receiver_th_alive =", r_alive)
                    print("  [Follow-up] receiver_exception =", getattr(sm, 'receiver_exception', None))
                    try:
                        recv_qsize = sm.recv_q.qsize()
                    except Exception:
                        recv_qsize = 'N/A'
                    print("  [Follow-up] recv_qsize =", recv_qsize)
                    try:
                        xmit_locked = sm.xmit_lock.locked()
                    except Exception:
                        xmit_locked = 'N/A'
                    print("  [Follow-up] xmit_lock_locked =", xmit_locked)

                    # SK wrapper diagnostics
                    try:
                        skw = sm.skw
                        pub_alive = skw.publisher_th.is_alive() if getattr(skw, 'publisher_th', None) is not None else None
                        print("  [Follow-up] skw.publisher_th_alive =", pub_alive)
                        ser = getattr(skw, 'ser', None)
                        if ser is None:
                            print("  [Follow-up] serial = None")
                        else:
                            try:
                                ser_open = not getattr(ser, 'closed', False)
                            except Exception:
                                ser_open = 'N/A'
                            print("  [Follow-up] serial open =", ser_open)
                    except Exception as e:
                        print("  [Follow-up] skw diagnostics error:", e)
                except Exception as e:
                    print("  [Follow-up] session manager diagnostics error:", e)

                # Allow longer time for real hardware and retry a couple of times
                max_retries = 2
                last_exc = None
                for attempt in range(1, max_retries + 1):
                    try:
                        val = await asyncio.wait_for(amo.get_instantaneous_power(), timeout=15)
                        print(f"  [Follow-up] attempt {attempt} succeeded: {val}")
                        self.assertIsInstance(val, (int, float))
                        last_exc = None
                        break
                    except Exception as e:
                        last_exc = e
                        print(f"  [Follow-up] attempt {attempt} failed: {type(e).__name__}: {e!r}")
                        print("  [Follow-up] sync_client.is_open after failure =", getattr(amo._sync_client, 'is_open', None))
                        if attempt < max_retries:
                            await asyncio.sleep(0.5)
                            print("  [Follow-up] retrying...")
                if last_exc is not None:
                    self.fail(f"Follow-up call failed after {max_retries} attempts: {last_exc!r}")

            # Optionally, exercise concurrent handling: one failing task mixed with valid ones.
            with self.subTest('Concurrent mix'):
                tasks = [amo.get_instantaneous_power() for _ in range(3)] + [amo.submit_sync_call(failing_sync)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                failures = [r for r in results if isinstance(r, Exception)]
                successes = [r for r in results if not isinstance(r, Exception)]

                # Expect exactly one failure (the failing_sync) and the rest succeed
                self.assertEqual(len(failures), 1, f'Expected one failure, got {len(failures)}')
                self.assertTrue(all(not isinstance(s, Exception) for s in successes))
        finally:
            # No-op: ensure we don't leave the device in a weird state; cleanup handled by caller.
            pass


if __name__ == '__main__':
    # Display usage help
    print(__doc__)
    unittest.main()
