# S03 – eda_cli: мини-EDA для CSV

Небольшое CLI-приложение для базового анализа CSV-файлов.
Используется в рамках Семинара 03 курса «Инженерия ИИ».

## Требования

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) установлен в систему

## Инициализация проекта

В корне проекта (S03):

```bash
uv sync
```

Эта команда:

- создаст виртуальное окружение `.venv`;
- установит зависимости из `pyproject.toml`;
- установит сам проект `eda-cli` в окружение.

## Запуск CLI

### Краткий обзор

```bash
uv run eda-cli overview data/example.csv
```

Параметры:

- `--sep` – разделитель (по умолчанию `,`);
- `--encoding` – кодировка (по умолчанию `utf-8`).

### Полный EDA-отчёт

```bash
uv run eda-cli report data/example.csv --out-dir reports
```

В результате в каталоге `reports/` появятся:

- `report.md` – основной отчёт в Markdown;
- `summary.csv` – таблица по колонкам;
- `missing.csv` – пропуски по колонкам;
- `correlation.csv` – корреляционная матрица (если есть числовые признаки);
- `top_categories/*.csv` – top-k категорий по строковым признакам;
- `hist_*.png` – гистограммы числовых колонок;
- `missing_matrix.png` – визуализация пропусков;
- `correlation_heatmap.png` – тепловая карта корреляций.



В результате в каталоге `reports/` появятся:

- `report.md` – основной отчёт в Markdown;
- `summary.csv` – таблица по колонкам;
- `missing.csv` – пропуски по колонкам;
- `correlation.csv` – корреляционная матрица (если есть числовые признаки);
- `top_categories/*.csv` – top-k категорий по строковым признакам;
- `hist_*.png` – гистограммы числовых колонок;
- `missing_matrix.png` – визуализация пропусков;
- `correlation_heatmap.png` – тепловая карта корреляций.

## Расширенные параметры команды `report`

Команда `report` поддерживает дополнительные настройки, которые влияют на содержимое отчёта:
```bash
uv run eda-cli report data/example.csv
--out-dir reports_example
--max-hist-columns 2
--top-k-categories 3
--title "EDA по example.csv"
--min-missing-share 0.05
```

Параметры:

- `--max-hist-columns` — максимальное число числовых колонок, для которых строятся гистограммы.
- `--top-k-categories` — сколько наиболее частых значений показывать для категориальных признаков.
- `--title` — заголовок отчёта, первая строка в `report.md`.
- `--min-missing-share` — порог доли пропусков; колонки с большей долей пропусков попадают в отдельную таблицу «проблемных» колонок в отчёте.

## Команда `head`

Для быстрого просмотра начала датасета есть отдельная команда:

```bash
uv run eda-cli head data/example.csv --n 5
```


Она загружает CSV‑файл и выводит в терминал первые `n` строк (по умолчанию 5). Это удобно, чтобы проверить структуру и содержимое файла перед запуском полного отчёта.

## Тесты

```bash
uv run pytest -q
```

# eda-cli — HW04

HTTP‑сервис качества датасетов поверх проекта `eda-cli` (FastAPI + REST API).  
Проект основан на решении HW03 и добавляет HTTP‑слой к существующему EDA‑ядру и CLI.

## Установка и окружение

Из корня проекта HW04:

```
uv sync
```

## Запуск HTTP‑сервиса

```
uv run uvicorn eda_cli.api:app --reload --port 8000
```

## HTTP‑эндпоинты

Базовый URL: `http://localhost:8000`

### `GET /health`
Проверка доступности сервиса.

### `POST /quality`
Оценивает качество датасета по агрегированным признакам, переданным в JSON.

Вход: JSON по схеме `QualityRequest` (n_rows, n_cols, max_missing_share, numeric_cols, categorical_cols).  

Выход: JSON `QualityResponse` (ok_for_model, quality_score, message, latency_ms, flags, dataset_shape).  
Пример curl‑запроса.

### `POST /quality-from-csv`
Оценивает качество датасета по самому CSV‑файлу: внутри считаются summary, пропуски и флаги качества.

Вход: `multipart/form-data` с полем `file` (CSV).  
Что делает и какие поля возвращает (как в коде).

### `POST /quality-flags-from-csv`
Дополнительный эндпоинт, который возвращает полный набор флагов качества для CSV‑файла.

Вход: ```multipart/form-data``` с полем ```file``` (CSV файл).

Выход: JSON с полями:

```flags```: полный список флагов качества (например: ["has_numeric", "has_categorical", "low_missing_rate", "has_datetime"])

```latency_ms```: время обработки в миллисекундах

```n_rows```: количество строк в датасете

```n_cols```: количество столбцов в датасете

```column_details```: подробная информация по каждой колонке

```missing_per_column```: доля пропусков по каждой колонке

```data_types```: типы данных каждой колонки

Особенности эндпоинта:

* Возвращает более детальную информацию, чем /quality-from-csv

 * Фокусируется на диагностических флагах, а не на итоговой оценке

 * Полезен для глубокого анализа качества данных

 * Включает метрики по каждой колонке отдельно
  

## Тестирование API

Для тестирования API можно использовать:

Swagger UI: ```http://localhost:8000/docs```

ReDoc: ```http://localhost:8000/redoc```

Пример curl‑запроса
```
curl -X 'POST' \
  'http://127.0.0.1:8000/quality-flags-from-csv' \
  -H 'accept: application/json' \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@example.csv;type=text/csv'
  ```
  Пример реального ответа
```json
{
  "flags": {
    "too_few_rows": true,
    "too_many_columns": false,
    "max_missing_share": 0.05555555555555555,
    "too_many_missing": false,
    "has_constant_columns": false,
    "constant_columns_count": 0,
    "constant_column_names": [],
    "has_many_zero_values": true,
    "high_zero_columns": 4,
    "high_zero_column_names": [
      "purchases_last_30d",
      "revenue_last_30d",
      "churned",
      "n_support_tickets"
    ],
    "quality_score": 0.5944444444444444
  },
  "latency_ms": 20.3,
  "n_rows": 36,
  "n_cols": 14
}
```