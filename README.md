# Rejects Analyzer

FastAPI backend и Streamlit UI для анализа причин отказов заказчиков после интервью.

## Что реализовано

- Поиск строки в Google Sheets по проекту, сотруднику, технологии или выбранному кейсу.
- Поддержка структуры таблицы кейсов с колонками `Проект`, `Сотрудник`,
  `Технология`, `Грейд`, `Источник`/`Статус`, `Комментарий`, `Ссылка на разбор`, `Дата`.
- Извлечение ссылок на Google Doc/Sheet из найденной строки и загрузка текста
  разбора, если ссылка доступна сервисному аккаунту.
- Анализ отказа через внешний OpenAI-compatible LLM API.
- LLM orchestration через `langchain==0.3.27` и `langchain-openai`.
- Fallback-анализ без LLM API, чтобы сервис можно было проверить локально.
- RAG-слой на Qdrant через `langchain-qdrant`: сохранение кейсов и поиск
  3-5 похожих отказов.
- Локальный JSON-кэш результатов для экономии токенов.
- Streamlit-интерфейс: новый анализ, чат с агентом, история.

## Локальный запуск

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Во втором терминале:

```bash
uv run streamlit run ui/app.py
```

Healthcheck:

```bash
curl http://localhost:8000/api/v1/health
```

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

UI будет доступен на `http://localhost:8501`, backend на `http://localhost:8000`.

## Настройка Google

1. Создайте Service Account в Google Cloud.
2. Дайте этому аккаунту доступ на чтение к Google Sheet и Google Docs.
3. Сохраните JSON-ключ и укажите путь в `GOOGLE_SERVICE_ACCOUNT_FILE`.
4. Проверьте `GOOGLE_SHEET_ID`.
   Backend сам обходит все месячные листы таблицы до текущего месяца включительно.

Если Google API не настроен, можно вставлять фидбек и анализ интервью вручную в поле "Ручной контекст".

В Docker JSON-ключ нужно примонтировать в контейнер и указать контейнерный путь, например
`GOOGLE_SERVICE_ACCOUNT_FILE=/app/secrets/service-account.json`.

## Настройка LLM

Для OpenAI:

```env
LLM_API_KEY=...
LLM_MODEL=gpt-4o-mini
```

Для Qwen/Gemini через OpenAI-compatible endpoint:

```env
LLM_API_KEY=...
LLM_BASE_URL=https://example.com/v1
LLM_MODEL=qwen2.5
```
