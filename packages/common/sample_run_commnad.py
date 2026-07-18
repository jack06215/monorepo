import asyncio
import time

from common.execute import run_command_stream
from common.execute_async import run_command_stream_gen


async def stream(label: str, cmd: list[str]) -> None:
    async for source, line in run_command_stream_gen(cmd):
        print(f"[{label}][{source}] {line}", flush=True)


def run_one() -> None:
    run_command_stream(
        ["ping", "-c", "4", "google.com"],
        stdout_handler=lambda line: print(f"[google] {line}", flush=True),
    )
    run_command_stream(
        ["ping", "-c", "4", "github.com"],
        stdout_handler=lambda line: print(f"[github] {line}", flush=True),
    )
    run_command_stream(
        ["ping", "-c", "4", "cloudflare.com"],
        stdout_handler=lambda line: print(f"[cloudflare] {line}", flush=True),
    )


async def run_many() -> None:
    await asyncio.gather(
        stream("google", ["ping", "-c", "4", "google.com"]),
        stream("github", ["ping", "-c", "4", "github.com"]),
        stream("cloudflare", ["ping", "-c", "4", "cloudflare.com"]),
    )


print("\n=== Sequential (sync) ===")
start = time.perf_counter()
run_one()
sync_elapsed = time.perf_counter() - start
print(f"\nSYNC elapsed: {sync_elapsed:.2f}s")

print("\n=== Concurrent (async) ===")
start = time.perf_counter()
asyncio.run(run_many())
async_elapsed = time.perf_counter() - start
print(f"\nASYNC elapsed: {async_elapsed:.2f}s")

print("\n=== Result ===")
print(f"Speedup: {sync_elapsed / async_elapsed:.2f}x")
