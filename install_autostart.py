"""Ярлыки значка распознавания: рабочий стол и «Автозагрузка».

Создать: python install_autostart.py
Убрать: python install_autostart.py --remove

Ярлык ведёт на tray.py, а не на server.py: значок даёт надзор за сервисом и
способ его закрыть. Иконка — speech.ico, её рисует make_icon.py.
Ярлык создаётся через COM (pywin32), а не PowerShell: в имени кириллица,
а argv PowerShell на Windows приходит в ANSI и портит её.
"""
import argparse
from pathlib import Path

import win32com.client

from make_icon import ensure_icon

HERE = Path(__file__).resolve().parent
SHORTCUT_NAME = "Распознавание речи (трей).lnk"
FOLDERS = ("Desktop", "Startup")
OLD_NAME = "Сервис распознавания речи.lnk"


def shortcut_path(folder: str) -> Path:
    shell = win32com.client.Dispatch("WScript.Shell")
    return Path(shell.SpecialFolders(folder)) / SHORTCUT_NAME


def create(folder: str) -> None:
    target = HERE / ".venv" / "Scripts" / "pythonw.exe"
    if target.is_file() is False:
        raise SystemExit(f"нет интерпретатора {target}")
    shell = win32com.client.Dispatch("WScript.Shell")
    link = shell.CreateShortcut(str(shortcut_path(folder)))
    link.TargetPath = str(target)
    link.Arguments = "-X utf8 tray.py"
    link.WorkingDirectory = str(HERE)
    link.IconLocation = str(ensure_icon())
    link.Description = "Локальное распознавание речи: модель в памяти, ответ на 127.0.0.1:8792"
    link.Save()
    print(f"ярлык создан: {shortcut_path(folder)}")


def remove(folder: str) -> None:
    shell = win32com.client.Dispatch("WScript.Shell")
    for name in (SHORTCUT_NAME, OLD_NAME):
        path = Path(shell.SpecialFolders(folder)) / name
        if path.is_file() is True:
            path.unlink()
            print(f"ярлык удалён: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="ярлыки значка распознавания речи")
    parser.add_argument("--remove", action="store_true", help="убрать ярлыки со стола и из автозагрузки")
    args = parser.parse_args()
    for folder in FOLDERS:
        remove(folder)
        if args.remove is False:
            create(folder)


if __name__ == "__main__":
    main()
