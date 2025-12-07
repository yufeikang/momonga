import asyncio
import functools
import logging
from typing import Any
from concurrent.futures import Executor

from .momonga import Momonga
from .momonga_exception import MomongaSkScanFailure, MomongaDeviceBusyError, MomongaNeedToReopen

logger = logging.getLogger(__name__)

__all__ = ["AsyncMomonga"]


class AsyncMomonga:
    """
    Asynchronous wrapper for the Momonga client.

    This class provides an asyncio-compatible interface to the synchronous Momonga client.
    It uses a background worker task and an executor to run blocking operations without
    blocking the asyncio event loop.
    """
    _active_devices: set[str] = set()

    def __init__(self,
                 rbid: str,
                 pwd: str,
                 dev: str,
                 baudrate: int = 115200,
                 reset_dev: bool = True,
                 executor: Executor | None = None,
                 ) -> None:
        self._dev = dev
        self._sync_client = Momonga(rbid, pwd, dev, baudrate, reset_dev)
        self._executor = executor
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._closing: bool = False
        self._state_lock: asyncio.Lock = asyncio.Lock()

    def __repr__(self) -> str:
        return f"<AsyncMomonga dev={self._dev}>"

    async def __aenter__(self) -> "AsyncMomonga":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _run_in_executor(self, func, *args, **kwargs) -> Any:
        loop = asyncio.get_running_loop()
        # Protect checking/starting worker vs close() with a small lock.
        async with self._state_lock:
            if self._closing:
                raise MomongaNeedToReopen("Client is closing; cannot accept new tasks")

            # Ensure worker is running
            if self._worker is None:
                self._start_worker()

        fut: asyncio.Future = loop.create_future()
        await self._queue.put((func, args, kwargs, fut))
        return await fut

    def _start_worker(self) -> None:
        if self._worker is None:
            loop = asyncio.get_running_loop()
            self._worker = loop.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        loop = asyncio.get_running_loop()
        try:
            while True:
                item = await self._queue.get()
                if item is None:
                    self._queue.task_done()
                    break

                func, args, kwargs, fut = item

                # If the future is already done (cancelled or completed),
                # skip executing the blocking call to avoid wasted work.
                if fut.done():
                    self._queue.task_done()
                    continue

                try:
                    res = await loop.run_in_executor(self._executor, functools.partial(func, *args, **kwargs))
                except Exception as e:
                    if not fut.done():
                        fut.set_exception(e)
                else:
                    if not fut.done():
                        fut.set_result(res)
                finally:
                    self._queue.task_done()
        finally:
            # Drain the queue and cancel pending futures if the worker stops unexpectedly
            while not self._queue.empty():
                item = self._queue.get_nowait()
                if item is None:
                    self._queue.task_done()
                    continue
                _, _, _, fut = item
                if not fut.done():
                    fut.set_exception(MomongaNeedToReopen("Worker stopped unexpectedly"))
                self._queue.task_done()

    async def open(self, retry_count: int = 3, retry_interval: float = 2.0) -> "AsyncMomonga":
        if self._dev in AsyncMomonga._active_devices:
            raise MomongaDeviceBusyError(f"Device {self._dev} is already in use by another AsyncMomonga instance")

        last_error = None
        for i in range(retry_count + 1):
            try:
                await self._run_in_executor(self._sync_client.open)
                AsyncMomonga._active_devices.add(self._dev)
                return self
            except MomongaSkScanFailure as e:
                last_error = e
                if i < retry_count:
                    logger.warning(f"Scan failed, retrying ({i+1}/{retry_count})...")
                    await asyncio.sleep(retry_interval)

        if last_error:
            raise last_error
        return self

    async def close(self) -> None:
        loop = asyncio.get_running_loop()

        async with self._state_lock:
            self._closing = True
            worker_exists = self._worker is not None

        if not worker_exists:
            await loop.run_in_executor(self._executor, functools.partial(self._sync_client.close))
            if self._dev in AsyncMomonga._active_devices:
                AsyncMomonga._active_devices.remove(self._dev)
            async with self._state_lock:
                self._closing = False
            return

        close_fut: asyncio.Future = loop.create_future()
        await self._queue.put((self._sync_client.close, (), {}, close_fut))
        await close_fut

        if self._dev in AsyncMomonga._active_devices:
            AsyncMomonga._active_devices.remove(self._dev)

        await self._queue.join()

        await self._queue.put(None)
        if self._worker:
            await self._worker
            self._worker = None

        async with self._state_lock:
            self._closing = False

    # --- Wrapped Methods ---

    async def get_operation_status(self) -> bool | None:
        return await self._run_in_executor(self._sync_client.get_operation_status)

    async def get_installation_location(self) -> str:
        return await self._run_in_executor(self._sync_client.get_installation_location)

    async def get_standard_version(self) -> str:
        return await self._run_in_executor(self._sync_client.get_standard_version)

    async def get_fault_status(self) -> bool | None:
        return await self._run_in_executor(self._sync_client.get_fault_status)

    async def get_manufacturer_code(self) -> bytes:
        return await self._run_in_executor(self._sync_client.get_manufacturer_code)

    async def get_serial_number(self) -> str:
        return await self._run_in_executor(self._sync_client.get_serial_number)

    async def get_current_time_setting(self) -> Any:
        return await self._run_in_executor(self._sync_client.get_current_time_setting)

    async def get_current_date_setting(self) -> Any:
        return await self._run_in_executor(self._sync_client.get_current_date_setting)

    async def get_properties_for_status_notification(self) -> set:
        return await self._run_in_executor(self._sync_client.get_properties_for_status_notification)

    async def get_properties_to_set_values(self) -> set:
        return await self._run_in_executor(self._sync_client.get_properties_to_set_values)

    async def get_properties_to_get_values(self) -> set:
        return await self._run_in_executor(self._sync_client.get_properties_to_get_values)

    async def get_route_b_id(self) -> dict:
        return await self._run_in_executor(self._sync_client.get_route_b_id)

    async def get_one_minute_measured_cumulative_energy(self) -> dict:
        return await self._run_in_executor(self._sync_client.get_one_minute_measured_cumulative_energy)

    async def get_coefficient_for_cumulative_energy(self) -> int:
        return await self._run_in_executor(self._sync_client.get_coefficient_for_cumulative_energy)

    async def get_number_of_effective_digits_for_cumulative_energy(self) -> int:
        return await self._run_in_executor(self._sync_client.get_number_of_effective_digits_for_cumulative_energy)

    async def get_measured_cumulative_energy(self, reverse: bool = False) -> int | float:
        return await self._run_in_executor(self._sync_client.get_measured_cumulative_energy, reverse)

    async def get_unit_for_cumulative_energy(self) -> int | float:
        return await self._run_in_executor(self._sync_client.get_unit_for_cumulative_energy)

    async def get_historical_cumulative_energy_1(self, reverse: bool = False) -> list:
        return await self._run_in_executor(self._sync_client.get_historical_cumulative_energy_1, reverse)

    async def get_day_for_historical_data_1(self) -> int:
        return await self._run_in_executor(self._sync_client.get_day_for_historical_data_1)

    async def get_instantaneous_power(self) -> float:
        return await self._run_in_executor(self._sync_client.get_instantaneous_power)

    async def get_instantaneous_current(self) -> dict:
        return await self._run_in_executor(self._sync_client.get_instantaneous_current)

    async def get_cumulative_energy_measured_at_fixed_time(self, reverse: bool = False) -> dict:
        return await self._run_in_executor(self._sync_client.get_cumulative_energy_measured_at_fixed_time, reverse)

    async def get_historical_cumulative_energy_2(self) -> list:
        return await self._run_in_executor(self._sync_client.get_historical_cumulative_energy_2)

    async def get_time_for_historical_data_2(self) -> dict:
        return await self._run_in_executor(self._sync_client.get_time_for_historical_data_2)

    async def get_historical_cumulative_energy_3(self) -> list:
        return await self._run_in_executor(self._sync_client.get_historical_cumulative_energy_3)

    async def get_time_for_historical_data_3(self) -> dict:
        return await self._run_in_executor(self._sync_client.get_time_for_historical_data_3)

    async def request_to_set(self, **kwargs) -> None:
        return await self._run_in_executor(self._sync_client.request_to_set, **kwargs)

    async def request_to_get(self, properties: set) -> dict:
        return await self._run_in_executor(self._sync_client.request_to_get, properties)
