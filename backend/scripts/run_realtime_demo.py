"""Run the local camera -> inference -> decision -> DB -> WS demo."""
# ruff: noqa: I001 -- direct script execution requires the backend root on sys.path
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.watcher import watch_pending


PNG_1X1 = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360f8cf00000004000101f9a3d6da0000000049454e44ae426082")


async def generate_images(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    index = 0
    while True:
        index += 1
        suffix = "-ng" if index % 4 == 0 else "-pass"
        (directory / f"mock-{index:05d}{suffix}.png").write_bytes(PNG_1X1)
        await asyncio.sleep(float(os.getenv("MOCK_IMAGE_INTERVAL_SECONDS", "3")))


async def main() -> None:
    directory = Path(os.getenv("IMAGE_PENDING_DIR", "/data/images/pending"))
    await asyncio.gather(watch_pending(directory), generate_images(directory))


if __name__ == "__main__":
    asyncio.run(main())
