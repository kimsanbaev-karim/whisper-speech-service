"""Значок в трее для сервиса распознавания речи: держит server.py живым и показывает состояние.

Запуск без консоли: .venv/Scripts/pythonw.exe tray.py

Ярлык на столе и в автозагрузке указывает сюда, а не на server.py: сервису нужен
надзор (перезапуск после падения) и способ его закрыть, а голый процесс не даёт ни того, ни другого.
"""
import os
import subprocess
import threading
import time
from pathlib import Path

import pystray
import win32api
import win32event
import winerror
from PIL import Image

from make_icon import ensure_icon

HERE = Path(__file__).resolve().parent
LOG_PATH = HERE / "service.log"
MUTEX_NAME = "Global\\whisper-speech-service-tray"
RESTART_DELAY_SECONDS = 5
POLL_SECONDS = 1.0


def ensure_single_instance() -> None:
    win32event.CreateMutex(None, False, MUTEX_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        raise SystemExit("значок сервиса распознавания уже в трее")


def write_log(message: str) -> None:
    with LOG_PATH.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(f"[трей {time.strftime('%H:%M:%S')}] {message}\n")


class ServiceSupervisor:
    def __init__(self) -> None:
        self.stopping = threading.Event()
        self.process = self.spawn()
        threading.Thread(target=self.watch, daemon=True).start()

    def spawn(self) -> subprocess.Popen:
        write_log("запускаю сервис распознавания")
        python = HERE / ".venv" / "Scripts" / "python.exe"
        command = [str(python), "-X", "utf8", str(HERE / "server.py")]
        log = LOG_PATH.open("a", encoding="utf-8", buffering=1)
        return subprocess.Popen(command, cwd=HERE, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)

    def watch(self) -> None:
        while self.stopping.is_set() is False:
            try:
                code = self.process.wait(timeout=POLL_SECONDS)
            except subprocess.TimeoutExpired:
                continue
            if self.stopping.is_set() is True:
                return
            write_log(f"сервис завершился с кодом {code}, перезапуск через {RESTART_DELAY_SECONDS} с")
            time.sleep(RESTART_DELAY_SECONDS)
            self.process = self.spawn()

    def restart(self) -> None:
        write_log("перезапуск по команде из меню")
        self.process.terminate()

    def stop(self) -> None:
        write_log("выход по команде из меню")
        self.stopping.set()
        self.process.terminate()


def main() -> None:
    ensure_single_instance()
    supervisor = ServiceSupervisor()

    def on_open_log(icon, item) -> None:
        os.startfile(LOG_PATH)

    def on_restart(icon, item) -> None:
        supervisor.restart()

    def on_quit(icon, item) -> None:
        supervisor.stop()
        icon.stop()

    items = (
        pystray.MenuItem("Открыть лог", on_open_log),
        pystray.MenuItem("Перезапустить", on_restart),
        pystray.MenuItem("Выход", on_quit),
    )
    icon = pystray.Icon("whisper-speech", Image.open(ensure_icon()), "Распознавание речи (127.0.0.1:8792)", pystray.Menu(*items))
    icon.run()


if __name__ == "__main__":
    main()
