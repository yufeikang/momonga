import asyncio
import os
from momonga import AsyncMomonga


async def main():
    rbid = os.environ.get('MOMONGA_ROUTEB_ID')
    pwd = os.environ.get('MOMONGA_ROUTEB_PASSWORD')
    dev = os.environ.get('MOMONGA_DEV_PATH')

    async with AsyncMomonga(rbid, pwd, dev) as amo:
        async def loop_power():
            while True:
                res = await amo.get_instantaneous_power()
                print('Power: %0.1fW' % res)
                await asyncio.sleep(20)

        async def loop_energy():
            while True:
                res = await amo.get_measured_cumulative_energy()
                print('Energy: %0.1fkWh' % res)
                await asyncio.sleep(60)

        await asyncio.gather(loop_power(), loop_energy())


if __name__ == '__main__':
    asyncio.run(main())
