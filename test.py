from src.core.audio_processing import AudioProcessor
import sys
import numpy as np
from pathlib import Path


def main():
    audio_path = Path(sys.argv[1])

    print(f"📁 Тестируем файл: {audio_path}")
    print(f"📊 Размер файла: {audio_path.stat().st_size / 1024 / 1024:.2f} MB")

    audio_processor = AudioProcessor(n_mfcc=20)

    with open(audio_path, "rb") as f:
        print("🔍 Извлекаем признаки...")
        embedding = audio_processor.create_embedding(f)

        print("✅ Эмбеддинг успешно создан!")
        print(f"📐 Размерность вектора: {len(embedding)}")
        print("📈 Статистика вектора:")
        print(f"   - Min: {np.min(embedding):.6f}")
        print(f"   - Max: {np.max(embedding):.6f}")
        print(f"   - Mean: {np.mean(embedding):.6f}")
        print(f"   - Std: {np.std(embedding):.6f}")
        print(f"   - Sum: {np.sum(embedding):.6f}")

        if np.any(np.isnan(embedding)):
            print("❌ Обнаружены NaN значения!")
        if np.any(np.isinf(embedding)):
            print("❌ Обнаружены Inf значения!")


if __name__ == "__main__":
    main()
