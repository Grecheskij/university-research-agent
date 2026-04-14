# University Research Agent

## Описание проекта

University Research Agent — это двуязычный (RU/EN) ассистент для академических исследований. Проект умеет:

- искать статьи по нескольким открытым научным источникам;
- собирать обзор литературы;
- формировать библиографию в форматах APA 7, MLA 9 и ГОСТ 7.0.5;
- показывать простую аналитику по найденному корпусу статей.

Архитектура разделена на:

- `agent_core/` — ИИ-логика, инструменты и цепочки;
- `backend/` — FastAPI API для фронтенда;
- `frontend/` — Gradio UI;
- `devops/` — зависимости, env-конфиг и инструкция по запуску.

## Требования

- Python 3.11+
- Доступ в интернет для внешних научных API и LLM-провайдеров
- Git (для работы с репозиторием)

## Установка зависимостей

### Linux / macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r devops/requirements.txt
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r devops/requirements.txt
```

## Настройка окружения

1. Скопируйте `devops/.env.example` в `.env`.
2. Заполните секреты и параметры:
   - `GEMINI_API_KEY`
   - `GROQ_API_KEY`
   - `UNPAYWALL_EMAIL`
   - `SEMANTIC_SCHOLAR_KEY` при необходимости
   - `API_KEY`/`BACKEND_API_KEY`, если хотите защитить analytics-endpoint

Переменные `.env` автоматически подгружаются в backend и frontend через `python-dotenv`.

## Локальный запуск

### Вариант 1. Раздельный запуск backend и frontend

Запуск backend:

```bash
python -m uvicorn backend.api.main:create_app --factory --host 0.0.0.0 --port 8000
```

Запуск frontend:

```bash
python -m frontend.app
```

Доступные адреса:

- FastAPI health: `http://localhost:8000/health`
- FastAPI docs: `http://localhost:8000/docs`
- Gradio UI: `http://localhost:7860`

### Вариант 2. Только фронтенд, backend стартует автоматически

Если `BACKEND_BASE_URL` указывает на `http://localhost:8000` или `http://127.0.0.1:8000` и `AUTO_START_BACKEND=1`, Gradio поднимет локальный backend в фоне при старте интерфейса.

```bash
python -m frontend.app
```

Этот режим удобен для локальной демонстрации и для Hugging Face Spaces с единым Gradio-entrypoint.

## Запуск тестов

```bash
python -m pytest -p no:cacheprovider
```

## Деплой на Hugging Face Spaces

### Рекомендуемый вариант

Для текущей структуры проекта удобнее использовать **Gradio Space**:

- в корне репозитория уже добавлен `app.py`, который экспортирует `demo` из `frontend.app`;
- в корне также есть `requirements.txt`, который подключает `devops/requirements.txt`;
- frontend при необходимости может автоматически поднять локальный FastAPI backend внутри того же окружения.

### Что сделать в Settings Space

Добавьте Secrets / Variables:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`
- `UNPAYWALL_EMAIL`
- `SEMANTIC_SCHOLAR_KEY` (если нужен)
- `API_KEY` или `BACKEND_API_KEY` (если защищаете analytics)
- `HF_SPACE_URL` — URL Space для CORS
- `BACKEND_BASE_URL=http://127.0.0.1:8000`
- `AUTO_START_BACKEND=1`

### Поведение Space

Если Space создан как **Gradio**, Hugging Face ожидает корневой `app.py` и автоматически запускает интерфейс. Дополнительная команда запуска обычно не нужна.

Если вы захотите перейти на отдельный backend-процесс или Docker-сборку, можно перенести проект в **Docker Space** и запускать backend/frontend через собственный entrypoint.

### Полезные ссылки

- Hugging Face Spaces overview: https://huggingface.co/docs/hub/spaces-overview
- Hugging Face Gradio Spaces: https://huggingface.co/docs/hub/spaces-sdks-gradio
- Hugging Face Spaces dependencies: https://huggingface.co/docs/hub/spaces-dependencies

## Безопасность

- Никогда не храните API-ключи в коде или в git.
- Используйте `.env` только локально.
- Для Hugging Face Spaces и GitHub Actions используйте Secrets.
- Если включён `API_KEY`/`BACKEND_API_KEY`, frontend отправляет его как `X-API-Key`, а backend проверяет его на защищённых маршрутах.

## GitHub и Hugging Face

- Код развивается в GitHub-репозитории: `Grecheskij/university-research-agent`
- Для публикации на Hugging Face можно:
  - вручную push-ить код в Space-репозиторий;
  - или настроить синхронизацию из GitHub через workflow / Hub sync.
