import asyncio
from pathlib import Path

from app.services.realtime import process_image


async def watch_pending(directory: Path, line_id: str = "line-1") -> None:
    """Watch the camera drop directory with watchdog, with a polling fallback."""
    directory.mkdir(parents=True, exist_ok=True)
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        seen: set[Path] = set()
        while True:
            for path in directory.glob("*.*"):
                if path.is_file() and path not in seen:
                    seen.add(path)
                    await process_image(path, line_id=line_id)
            await asyncio.sleep(1)
        return

    loop = asyncio.get_running_loop()
    tasks: set[asyncio.Task] = set()

    class Handler(FileSystemEventHandler):
        def on_created(self, event) -> None:
            path = Path(event.src_path)
            if not event.is_directory and path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
                task = loop.create_task(process_image(path, line_id=line_id))
                tasks.add(task)
                task.add_done_callback(tasks.discard)

    observer = Observer()
    observer.schedule(Handler(), str(directory), recursive=False)
    observer.start()
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        observer.stop()
        observer.join(timeout=5)
