import asyncio
import logging

import aiohttp

timeout = aiohttp.ClientTimeout(total=30, sock_connect=10, sock_read=20)
logging.basicConfig(level=logging.DEBUG)
headers = {
    'User-Agent': 'Mozilla/5.0'
}

async def mini():
    connector = aiohttp.TCPConnector(
        limit_per_host=1,
        happy_eyeballs_delay=2.5,
    )
    async with aiohttp.ClientSession(timeout=timeout, headers=headers, connector=connector) as session:
        async with session.get('https://olegmakarenko.ru/data/rss/') as resp:
            content = await resp.read()
            print(content)


if __name__ == '__main__':
    asyncio.run(mini())
