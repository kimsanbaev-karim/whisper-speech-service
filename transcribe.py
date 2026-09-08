import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NVIDIA_LIBS = ROOT / ".venv" / "Lib" / "site-packages" / "nvidia"
MODELS_DIR = ROOT / "models"


def register_cuda_libraries():
    if not NVIDIA_LIBS.is_dir():
        return False
    found = [entry for entry in NVIDIA_LIBS.rglob("bin") if entry.is_dir()]
    for entry in found:
        os.add_dll_directory(str(entry))
    os.environ["PATH"] = os.pathsep.join([str(entry) for entry in found] + [os.environ["PATH"]])
    return len(found) > 0


def load_model(model_name, devices):
    from faster_whisper import WhisperModel

    failures = []
    for device in devices:
        compute_type = "float16" if device == "cuda" else "int8"
        try:
            model = WhisperModel(model_name, device=device, compute_type=compute_type, download_root=str(MODELS_DIR))
            return model, device, compute_type
        except Exception as error:
            failures.append(f"{device}: {error}")
    raise RuntimeError("Не удалось загрузить модель:\n" + "\n".join(failures))


def main():
    parser = argparse.ArgumentParser(description="Локальное распознавание речи через faster-whisper")
    parser.add_argument("audio", help="путь к аудиофайлу")
    parser.add_argument("--language", default="ru", help="код языка, например ru или en")
    parser.add_argument("--model", default=str(MODELS_DIR / "large-v3"), help="имя модели faster-whisper или путь к каталогу")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--timestamps", action="store_true", help="печатать тайминги сегментов")
    args = parser.parse_args()

    audio_path = Path(args.audio)
    if not audio_path.is_file():
        sys.exit(f"Файл не найден: {audio_path}")

    cuda_libs = register_cuda_libraries()
    devices = ["cuda", "cpu"] if args.device == "auto" else [args.device]
    model, device, compute_type = load_model(args.model, devices)
    print(f"[устройство: {device}, точность: {compute_type}, CUDA: {cuda_libs}]", file=sys.stderr)

    segments, info = model.transcribe(str(audio_path), language=args.language, vad_filter=True)
    print(f"[язык: {info.language}, уверенность: {info.language_probability:.2f}, длительность: {info.duration:.1f} с]", file=sys.stderr)

    for segment in segments:
        if args.timestamps:
            print(f"[{segment.start:6.1f} → {segment.end:6.1f}] {segment.text.strip()}")
        else:
            print(segment.text.strip())


if __name__ == "__main__":
    main()
