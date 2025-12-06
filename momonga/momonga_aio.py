import asyncio
import functools
import logging
from typing import Self, Any
from concurrent.futures import Executor

from .momonga import Momonga
from .momonga_device_enum import DeviceType
from .momonga_exception import MomongaError

logger = logging.getLogger(__name__)


class AsyncMomonga:
    def __init__(self,
                 rbid: str,
                 pwd: str,
                 dev: str,
                 baudrate: int = 115200,
                 reset_dev: bool = True,
                 executor: Executor | None = None,
                 ) -> None:
        """
        Async wrapper for Momonga client.
        
        Args:
            rbid: Route-B ID
            pwd: Route-B Password
            dev: Device path (e.g. '/dev/ttyUSB0' or 'COM3')
            baudrate: Baudrate (default: 115200)
            reset_dev: Whether to reset the device on open (default: True)
            executor: Custom executor for running blocking operations. 
                      If None, the default loop executor is used.
        """
        self._sync_client = Momonga(rbid, pwd, dev, baudrate, reset_dev)
        self._executor = executor
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self._closing: bool = False
        self._state_lock: asyncio.Lock = asyncio.Lock()

    async def __aenter__(self) -> Self:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.close()

    async def _run_in_executor(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        # Protect checking/starting worker vs close() with a small lock.
        async with self._state_lock:
            if self._closing:
                raise MomongaError("client is closing; cannot accept new tasks")

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
            while not self._queue.empty():
                item = self._queue.get_nowait()
                if item is None:
                    self._queue.task_done()
                    continue
                _, _, _, fut = item
                if not fut.done():
                    fut.set_exception(MomongaError("worker stopped unexpectedly"))
                self._queue.task_done()

    async def open(self) -> Self:
        await self._run_in_executor(self._sync_client.open)
        return self

    async def close(self) -> None:
        loop = asyncio.get_running_loop()

        async with self._state_lock:
            self._closing = True
            worker_exists = self._worker is not None

        if not worker_exists:
            await loop.run_in_executor(self._executor, functools.partial(self._sync_client.close))
            async with self._state_lock:
                self._closing = False
            return

        close_fut: asyncio.Future = loop.create_future()
        await self._queue.put((self._sync_client.close, (), {}, close_fut))
        await close_fut

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
