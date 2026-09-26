#!/usr/bin/python3

# Загрузка html. Один результат на источник, ошибка не роняет весь запуск.
# Про конфиги почти ничего не знает: url для скачивания может отличаться
# от url статьи (t.me отдаёт текст только в embed-режиме).

import asyncio
import time

import aiohttp
import requests

from article_to_md import TAG_TIMEOUT, get_fetch_url_for

RETRIES = 2
RETRY_PAUSE = 2


def is_retryable(status: int) -> bool:
    """403/404 — это «не пустили» и «нет такого», повтор не поможет.
    429 и 5xx — временно, стоит подождать."""
    return status == 429 or status >= 500


class RateLimiter:
    """Пауза между стартами запросов, общая на всю сессию."""

    def __init__(self, interval: float = 0):
        self.interval = interval
        self._lock = asyncio.Lock()
        self._last = 0.0

    async def wait(self) -> None:
        if not self.interval:
            return
        async with self._lock:
            delay = self._last + self.interval - time.monotonic()
            if delay > 0:
                await asyncio.sleep(delay)
            self._last = time.monotonic()


def _fetch_sync(url: str) -> tuple[str | None, str]:
    """Возвращает (html, причина_ошибки). Причина пустая при успехе."""
    for attempt in range(1, RETRIES + 1):
        try:
            response = requests.get(url, timeout=TAG_TIMEOUT)
        except requests.RequestException as e:
            if attempt == RETRIES:
                return None, f'{type(e).__name__}: {e}'
            time.sleep(RETRY_PAUSE * attempt)
            continue
        status = response.status_code
        if status < 400:
            return response.text, ''
        if not is_retryable(status) or attempt == RETRIES:
            return None, f'HTTP {status}'
        print(f'  HTTP {status}, повтор')
        time.sleep(RETRY_PAUSE * attempt)
    return None, 'неизвестно'


async def _fetch_async(session, url: str, semaphore, limiter) -> tuple[str | None, str]:
    async with semaphore:
        for attempt in range(1, RETRIES + 1):
            await limiter.wait()
            try:
                async with session.get(url) as response:
                    status = response.status
                    if status < 400:
                        return await response.text(), ''
                    if not is_retryable(status) or attempt == RETRIES:
                        return None, f'HTTP {status}'
                    print(f'  HTTP {status}, повтор')
            except aiohttp.ClientError as e:
                if attempt == RETRIES:
                    return None, f'{type(e).__name__}: {e}'
            await asyncio.sleep(RETRY_PAUSE * attempt)
    return None, 'неизвестно'


async def _fetch_all(urls: list[str], concurrency: int, interval: int) -> list[tuple]:
    semaphore = asyncio.Semaphore(concurrency)
    limiter = RateLimiter(interval)
    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(_fetch_async(session, url, semaphore, limiter))
            for url in urls
        ]
        return await asyncio.gather(*tasks)


def fetch_html(urls: list[str], *, sync: bool = False,
               concurrency: int = 5, interval: int = 0) -> list[tuple]:
    if not urls:
        return []
    if sync:
        htmls = []
        for url in urls:
            print(url, end=' ... ', flush=True)
            html, reason = _fetch_sync(url)
            print('success' if html else 'fail')
            htmls.append((html, reason))
            if interval:
                time.sleep(interval)
        return htmls
    print(f'качаю {len(urls)} шт, concurrency={concurrency}, interval={interval}')
    return asyncio.run(_fetch_all(urls, concurrency, interval))


def fetch_sources(sources: list, *, sync: bool = False,
                  concurrency: int = 5, interval: int = 0) -> list:
    """Результат в том же порядке, что и sources. Source с kind != 'url'
    (локальный .html или .md) возвращается как есть — сеть не нужна.
    На месте провалившейся загрузки — None."""
    todo = [(i, s) for i, s in enumerate(sources) if s.kind == 'url']
    urls = [get_fetch_url_for(s.url) for _, s in todo]
    results = fetch_html(urls, sync=sync, concurrency=concurrency, interval=interval)

    fetched = {}
    for (i, source), (html, reason) in zip(todo, results):
        if html is None:
            print(f'SKIP {source.url}: {reason}')
        else:
            source.html = html
        fetched[i] = source if html else None

    return [s if s.kind != 'url' else fetched.get(i) for i, s in enumerate(sources)]
