"""Резидентный сервис распознавания речи: модель живёт в памяти, ответ по HTTP на localhost.

Запуск: python -X utf8 server.py
Проверка: curl http://127.0.0.1:8792/healthz
Распознать: curl -X POST --data-binary @body.json http://127.0.0.1:8792/transcribe

После простоя модель выгружается: на этой машине Rider и Unity занимают память,
и держать три гигабайта ради сообщения раз в час дороже, чем прогреться заново.
"""
import gc
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from transcribe import MODELS_DIR, load_model, register_cuda_libraries

HOST = "127.0.0.1"
PORT = 8792  # config-ok: 8791 занят telegram-mcp, дефолтные порты заняты чужими проектами
MAX_BODY_BYTES = 64 * 1024
DEFAULT_LANGUAGE = "ru"
IDLE_UNLOAD_SECONDS = 900  # config-ok: прогрев раз в 15 минут дешевле, чем постоянные три гигабайта
IDLE_CHECK_SECONDS = 60

loaded: dict[str, object] = {}
speech_lock = threading.Lock()


def ensure_model():
    if len(loaded) == 0:
        model, device, compute = load_model(str(MODELS_DIR / "large-v3"), ["cuda", "cpu"])
        loaded["model"] = model
        loaded["device"] = device
        loaded["used_at"] = time.monotonic()
        print(f"[модель загружена: {device}, {compute}]", file=sys.stderr, flush=True)
    return loaded["model"]


def unload_when_idle() -> None:
    while True:
        time.sleep(IDLE_CHECK_SECONDS)
        with speech_lock:
            idle_for = time.monotonic() - float(loaded.get("used_at", time.monotonic()))
            if len(loaded) > 0 and idle_for > IDLE_UNLOAD_SECONDS:
                loaded.clear()
                gc.collect()
                print(f"[модель выгружена после {idle_for / 60:.0f} мин простоя]", file=sys.stderr, flush=True)


def recognize(audio: str, language: str) -> dict:
    path = Path(audio)
    if not path.is_file():
        raise FileNotFoundError(path)
    with speech_lock:
        model = ensure_model()
        segments, info = model.transcribe(str(path), language=language, vad_filter=True)
        lines = [segment.text.strip() for segment in segments]
        loaded["used_at"] = time.monotonic()
    text = "\n".join(line for line in lines if len(line) > 0)
    return {
        "text": text,
        "language": info.language,
        "probability": round(info.language_probability, 2),
        "duration": round(info.duration, 1),
        "device": loaded.get("device", ""),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        print(f"{self.address_string()} {format % args}", file=sys.stderr, flush=True)

    def answer(self, code: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != "/healthz":
            self.answer(404, {"error": f"нет такого адреса: {self.path}"})
            return
        self.answer(200, {"status": "ready", "model_loaded": len(loaded) > 0, "device": loaded.get("device", "")})

    def do_POST(self):
        if self.path != "/transcribe":
            self.answer(404, {"error": f"нет такого адреса: {self.path}"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY_BYTES:
            self.answer(400, {"error": f"тело запроса пустое или больше {MAX_BODY_BYTES} байт"})
            return
        try:
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            audio = request["audio"]
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError, TypeError) as error:
            self.answer(400, {"error": f"жду JSON вида {{\"audio\": \"путь\"}}: {error}"})
            return
        try:
            self.answer(200, recognize(audio, request.get("language", DEFAULT_LANGUAGE)))
        except FileNotFoundError as error:
            self.answer(400, {"error": f"файл не найден: {error}"})
        except Exception as error:
            self.answer(500, {"error": f"{type(error).__name__}: {error}"})


def main() -> None:
    cuda_libs = register_cuda_libraries()
    print(f"[CUDA-библиотеки: {cuda_libs}]", file=sys.stderr, flush=True)
    threading.Thread(target=unload_when_idle, daemon=True).start()
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError as error:
        raise SystemExit(f"порт {PORT} уже занят — сервис распознавания где-то запущен: {error}") from error
    print(f"[слушаю http://{HOST}:{PORT}, модель грузится по первому запросу]", file=sys.stderr, flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
