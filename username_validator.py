#!/usr/bin/env python3
"""Public username availability validator with deterministic generation."""

from __future__ import annotations

import argparse
import asyncio
import itertools
import string
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable, Optional

import aiohttp


@dataclass
class Config:
    length: int
    public_url_template: str
    fallback_url_template: str
    output_file: str = "validated_identifiers.txt"
    charset: str = string.ascii_lowercase + string.digits
    concurrency: int = 10
    base_delay: float = 0.2
    timeout: float = 15.0
    max_retries: int = 6
    limit: Optional[int] = None


def parse_retry_after(value: Optional[str]) -> Optional[float]:
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    try:
        retry_at = parsedate_to_datetime(value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
    except Exception:
        return None


def identifiers(length: int, charset: str) -> Iterable[str]:
    for chars in itertools.product(charset, repeat=length):
        yield "".join(chars)


class Validator:
    def __init__(self, config: Config) -> None:
        self.config = config
        self._iterator = identifiers(config.length, config.charset)
        self._next_lock = asyncio.Lock()
        self._file_lock = asyncio.Lock()
        self._count = 0

    async def _next_identifier(self) -> Optional[str]:
        async with self._next_lock:
            if self.config.limit is not None and self._count >= self.config.limit:
                return None
            try:
                candidate = next(self._iterator)
                self._count += 1
                return candidate
            except StopIteration:
                return None

    async def _write_available(self, identifier: str) -> None:
        async with self._file_lock:
            with open(self.config.output_file, "a", encoding="utf-8") as f:
                f.write(identifier + "\n")

    async def _request(self, session: aiohttp.ClientSession, url: str):
        for attempt in range(self.config.max_retries + 1):
            try:
                async with session.get(url, allow_redirects=True) as response:
                    body = await response.text(errors="ignore")
                    if response.status in (429, 503):
                        retry_after = parse_retry_after(response.headers.get("Retry-After"))
                        delay = retry_after if retry_after is not None else min(60.0, 2**attempt)
                        await asyncio.sleep(delay)
                        continue
                    return response.status, response.headers, body
            except (aiohttp.ClientError, asyncio.TimeoutError):
                await asyncio.sleep(min(60.0, 2**attempt))
        return None, None, None

    async def _stage1(self, session: aiohttp.ClientSession, identifier: str) -> bool:
        url = self.config.public_url_template.format(identifier=identifier)
        status, _headers, _body = await self._request(session, url)
        return status == 404

    async def _stage2(self, session: aiohttp.ClientSession, identifier: str) -> bool:
        url = self.config.fallback_url_template.format(identifier=identifier)
        status, headers, body = await self._request(session, url)
        if status == 404:
            return True
        if status == 200:
            header_hint = (headers or {}).get("X-User-Exists", "").lower()
            if header_hint in {"false", "0", "no"}:
                return True
            normalized = (body or "").lower()
            if "available" in normalized or "not found" in normalized:
                return True
        return False

    async def _worker(self, worker_id: int, session: aiohttp.ClientSession) -> None:
        while True:
            identifier = await self._next_identifier()
            if identifier is None:
                return
            try:
                if await self._stage1(session, identifier) and await self._stage2(session, identifier):
                    await self._write_available(identifier)
                    print(f"[worker-{worker_id}] AVAILABLE {identifier}")
            except Exception as exc:
                print(f"[worker-{worker_id}] ERROR {identifier}: {exc}")
            await asyncio.sleep(self.config.base_delay)

    async def run(self) -> None:
        open(self.config.output_file, "w", encoding="utf-8").close()
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        connector = aiohttp.TCPConnector(limit_per_host=max(1, self.config.concurrency))
        async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
            tasks = [asyncio.create_task(self._worker(i + 1, session)) for i in range(self.config.concurrency)]
            await asyncio.gather(*tasks)


def prompt_config() -> Config:
    length = int(input("Identifier length (X): ").strip())
    public_url = input("Public URL template with {identifier}: ").strip()
    fallback_url = input("Fallback URL template with {identifier}: ").strip()
    return Config(length=length, public_url_template=public_url, fallback_url_template=fallback_url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate username availability via public endpoints.")
    parser.add_argument("--length", type=int)
    parser.add_argument("--public-url")
    parser.add_argument("--fallback-url")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.2)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--first-only", action="store_true", help="Print the first generated identifier and exit.")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> Config:
    if args.length and args.public_url and args.fallback_url:
        return Config(
            length=args.length,
            public_url_template=args.public_url,
            fallback_url_template=args.fallback_url,
            concurrency=max(1, args.concurrency),
            base_delay=max(0.0, args.delay),
            limit=args.limit,
        )
    return prompt_config()


def main() -> None:
    args = parse_args()
    if args.first_only:
        length = args.length if args.length else int(input("Identifier length (X): ").strip())
        print(next(identifiers(length, string.ascii_lowercase + string.digits)))
        return

    config = build_config(args)
    asyncio.run(Validator(config).run())


if __name__ == "__main__":
    main()
