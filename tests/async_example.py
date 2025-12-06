import asyncio
import os
from momonga import AsyncMomonga


async def main():
    rbid = os.environ.get('MOMONGA_ROUTEB_ID')
    pwd = os.environ.get('MOMONGA_ROUTEB_PASSWORD')
    dev = os.environ.get('MOMONGA_DEV_PATH')

    async with AsyncMomonga(rbid, pwd, dev) as amo:
        while True:
            res = await amo.get_instantaneous_power()
            print('%0.1fW' % res)
            await asyncio.sleep(60)


if __name__ == '__main__':
    asyncio.run(main())
