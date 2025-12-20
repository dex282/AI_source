# Импортируем FastAPI и типы для работы с файлами и ошибками HTTP
from fastapi import FastAPI, UploadFile, File, HTTPException
# Pydantic-модели для строгого описания входных/выходных JSON-схем
from pydantic import BaseModel
# Типы для аннотаций (словарь и кортеж)
from typing import Dict, Tuple
# Для измерения времени работы (latency)
import time
# Для чтения CSV в DataFrame
import pandas as pd

# Импортируем функции EDA-ядра из твоего HW03
from eda_cli.core import summarize_dataset, missing_table, compute_quality_flags

# Создаём объект приложения FastAPI.
# Его потом использует uvicorn: `uv run uvicorn eda_cli.api:app --reload --port 8000`
app = FastAPI(title="EDA-CLI API", version="0.1")


# Pydantic-модели 

# Модель входного JSON для эндпоинта /quality.
# Описывает агрегированные признаки набора данных.
class QualityRequest(BaseModel):
    n_rows: int              # количество строк в датасете
    n_cols: int              # количество колонок
    max_missing_share: float # максимальная доля пропусков среди колонок (0..1)
    numeric_cols: int        # количество числовых колонок
    categorical_cols: int    # количество категориальных колонок


# Модель выходного JSON для /quality.
class QualityResponse(BaseModel):
    ok_for_model: bool               # можно ли использовать датасет для модели
    quality_score: float             # числовой скор качества (0..1)
    message: str                     # текстовое сообщение ("ok"/"low quality")
    latency_ms: float                # время обработки запроса в миллисекундах
    flags: Dict[str, bool]          # словарь флагов качества (true/false)
    dataset_shape: Tuple[int, int]   # форма датасета (n_rows, n_cols)


#  Эндпоинт health-check

# Простейший GET-эндпоинт для проверки, что сервис жив).
# 
@app.get("/health")
def health():
    # Просто возвращаем небольшой JSON с информацией о сервисе
    return {"status": "ok", "service": "eda-cli", "version": "0.1"}


#  Эндпоинт /quality (по агрегированным признакам) 

# POST /quality принимает JSON по схеме QualityRequest
# и возвращает JSON по схеме QualityResponse.
@app.post("/quality", response_model=QualityResponse)
def quality(req: QualityRequest):
    # Засекаем время начала обработки, чтобы потом посчитать latency
    start = time.perf_counter()

    # Простая валидация: количество строк и колонок должно быть > 0
    if req.n_rows <= 0 or req.n_cols <= 0:
        # Если условие не выполняется — сразу отдаём ошибку 400
        raise HTTPException(status_code=400, detail="n_rows and n_cols must be > 0")

    # Простейшая эвристика качества:
    # чем меньше пропусков и чем больше доля числовых колонок, тем лучше.
    score = (1 - req.max_missing_share) * (req.numeric_cols / req.n_cols)
    # Ограничиваем скор в диапазоне [0, 1]
    score = max(0.0, min(1.0, score))

    # Примеры флагов качества:
    # мало строк и слишком много пропусков.
    flags = {
        "too_few_rows": req.n_rows < 50,
        "too_many_missing": req.max_missing_share > 0.3,
    }

    # Считаем latency в миллисекундах
    latency_ms = (time.perf_counter() - start) * 1000
    # Считаем, что датасет «годится для модели», если score >= 0.5
    ok = score >= 0.5

    # Возвращаем объект QualityResponse (FastAPI сам превратит его в JSON)
    return QualityResponse(
        ok_for_model=ok,
        quality_score=round(score, 3),
        message="ok" if ok else "low quality",
        latency_ms=round(latency_ms, 1),
        flags=flags,
        dataset_shape=(req.n_rows, req.n_cols),
    )


# Эндпоинт /quality-from-csv (по самому CSV-файлу) 

#POST /quality-from-csv принимает файл (формат multipart/form-data).
# Здесь вместо агрегированных чисел ты отдаёшь сам CSV,
# а все признаки вычисляются внутри через функции ядра.
@app.post("/quality-from-csv")
async def quality_from_csv(file: UploadFile = File(...)):
    # Засекаем время начала обработки
    start = time.perf_counter()

    # Пробуем прочитать CSV в DataFrame pandas
    try:
        df = pd.read_csv(file.file)
    except Exception:
        # Если не удалось прочитать — возвращаем 400
        raise HTTPException(status_code=400, detail="Cannot read CSV")

    # Если DataFrame пустой — тоже ошибка 400
    if df.empty:
        raise HTTPException(status_code=400, detail="Empty CSV")

    # Вызываем функции ядра eda_cli (из HW03):
    # summary — агрегированная статистика по колонкам
    summary = summarize_dataset(df)
    # missing_df — таблица пропусков по колонкам
    missing_df = missing_table(df)
    # flags — словарь флагов качества на основе summary и missing_df
    flags = compute_quality_flags(summary, missing_df)

    # Простая схема вычисления score:
    # считаем, какая доля флагов == False (то есть нет проблем).
    score = sum(1 for v in flags.values() if not v) / max(len(flags), 1)

    # Считаем latency
    latency_ms = (time.perf_counter() - start) * 1000

    # Возвращаем обычный dict, FastAPI превратит его в JSON.
    # Здесь можно было бы тоже завести отдельную Pydantic-модель, но не обязательно.
    return {
        "ok_for_model": score >= 0.5,
        "quality_score": round(score, 3),
        "message": "ok" if score >= 0.5 else "low quality",
        "latency_ms": round(latency_ms, 1),
        "flags": flags,                # словарь флагов из compute_quality_flags
        "dataset_shape": list(df.shape),  # например [100, 10]
    }
@app.post("/quality-flags-from-csv")
async def quality_flags_from_csv(file: UploadFile = File(...)):
    """
    Принимает CSV-файл, прогоняет его через EDA-ядро
    и возвращает полный набор флагов качества из compute_quality_flags.
    """
    start = time.perf_counter()

    # 1. Чтение CSV
    try:
        df = pd.read_csv(file.file)
    except Exception:
        raise HTTPException(status_code=400, detail="Cannot read CSV")

    if df.empty:
        raise HTTPException(status_code=400, detail="Empty CSV")

    # 2. EDA-ядро из HW03
    summary = summarize_dataset(df)
    missing_df = missing_table(df)
    flags = compute_quality_flags(summary, missing_df)  # здесь все твои эвристики HW03

    # 3. Latency и форма датасета (для удобства)
    latency_ms = (time.perf_counter() - start) * 1000

    # 4. Ответ – только флаги + немного тех. инфы
    return {
        "flags": dict(flags),                  # полный словарь флагов качества
        "latency_ms": round(latency_ms, 1), 
        "n_rows": int(df.shape[0]),
        "n_cols": int(df.shape[1]),
    }
