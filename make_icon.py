"""Рисует иконку сервиса: профиль говорящего человека и звуковые волны.

Запуск: python make_icon.py — кладёт рядом speech.ico со всеми размерами,
которые Windows берёт для ярлыка, панели задач и трея.
"""
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
CANVAS = 256
ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
BACKGROUND = (37, 99, 175)
FACE = (255, 255, 255)
WAVE = (126, 211, 255)


def draw_face(pen: ImageDraw.ImageDraw) -> None:
    pen.ellipse((46, 34, 150, 138), fill=FACE)
    pen.polygon([(146, 88), (170, 106), (146, 116)], fill=FACE)
    pen.rounded_rectangle((84, 130, 118, 158), radius=10, fill=FACE)
    pen.pieslice((28, 138, 174, 252), start=200, end=340, fill=FACE)
    pen.ellipse((116, 72, 130, 88), fill=BACKGROUND)
    pen.chord((122, 112, 158, 138), start=180, end=360, fill=BACKGROUND)


def draw_waves(pen: ImageDraw.ImageDraw) -> None:
    for index, span in enumerate(((176, 68, 228, 148), (168, 46, 246, 170), (160, 24, 264, 192))):
        pen.arc(span, start=305, end=55, fill=WAVE, width=14 - index * 2)


def build() -> Image.Image:
    picture = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    pen = ImageDraw.Draw(picture)
    pen.ellipse((0, 0, CANVAS - 1, CANVAS - 1), fill=BACKGROUND)
    draw_face(pen)
    draw_waves(pen)
    return picture


def ensure_icon() -> Path:
    target = HERE / "speech.ico"
    if target.is_file() is False:
        build().save(target, sizes=ICON_SIZES)
    return target


def main() -> None:
    target = HERE / "speech.ico"
    picture = build()
    picture.save(target, sizes=ICON_SIZES)
    picture.resize((128, 128), Image.LANCZOS).save(HERE / "speech-preview.png")
    print(f"иконка готова: {target}")


if __name__ == "__main__":
    main()
