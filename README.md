# AI Fake News Detection

Detect fake news from any news website. Paste a URL, and the system scrapes the
page's headlines, classifies each one as **Real** or **Fake** with a trained
neural network, and streams the live progress to your browser over WebSockets.

Built around an async pipeline: FastAPI enqueues Celery tasks, a worker scrapes
with headless Chrome and scores headlines with a BiLSTM classifier trained on the
WELFake dataset (~91% test accuracy), and Redis pub/sub streams progress events
to the client.

---

## Features

- **Async analysis pipeline** — `POST /api/analyze` returns immediately with a
  `task_id`; the heavy work (scraping + inference) runs in a Celery worker.
- **7-minute result cache** — every completed analysis is stored in Redis keyed
  by the submitted URL (`url_cache:{url}`, TTL 420 s), so re-pasting the same
  link returns instantly without re-scraping or re-running the model.
- **Live progress streaming** — WebSocket endpoint pushes stage updates
  (`scraping` → `analyzing` → `done`) plus the final per-headline verdicts.
- **Real browser scraping** — headless Chrome (Selenium) renders JS-heavy sites
  before extracting `h1`–`h6` headlines.
- **Deep-learning classifier** — Embedding + Bidirectional LSTM, retrained on
  WELFake (72K+ labeled articles), ~91% balanced accuracy.
- **Optional cyber-security filtering** — restrict analysis to security-related
  headlines via `ENABLE_KEYWORD_FILTER=true`.
- **Animated landing page** — Next.js landing page (Framer Motion: staggered
  hero, floating gradient orbs, scroll reveals, animated counters) at `/`, with
  the analyzer at `/analyze`.
- **Dockerized** — full stack (Redis + API + worker + frontend) runs with one
  command; heavy dependencies install at container startup, not at build time.
- **Single-browser worker** — one reused Chrome driver (thread-safe, auto-healed)
  and one in-memory model, so a worker stays memory-lean.
- **Cross-platform** — Windows (solo pool) and Linux (Docker) both supported.

---

## Architecture

```
┌────────────┐   POST /api/analyze ──────┐
│   Browser  │                          │
│  (Next.js) │   WS /ws/analyze/{id}     ▼
└─────┬──────┘                    ┌──────────────┐      Redis
      │                           │  FastAPI API  │◄─────── broker /0
      │  streaming events         │  (uvicorn)    │───────► result db /1
      │                           └──────────────┘      pub/sub analyze:{id}
      │                                  │ enqueue (Celery task)
      │                                  ▼
      │                           ┌──────────────┐
      └──────────────────────────►│ Celery worker│
                  Redis pub/sub    │              │
                                   └──────┬───────┘
                                          │
                          ┌───────────────┼───────────────┐
                          ▼               ▼               ▼
                  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
                  │  Scraper    │  │  NLP pre-   │  │  BiLSTM     │
                  │ (Selenium,  │  │  processing │  │ classifier  │
                  │  headless   │  │  (NLTK)     │  │  (TF/Keras) │
                  │  Chrome)    │  │             │  │             │
                  └─────────────┘  └─────────────┘  └─────────────┘
```

Flow:

1. The client submits a URL.
2. FastAPI validates it and enqueues a Celery task, returning
   `202 {task_id, status: "queued", url}`.
3. The worker first checks the URL-keyed Redis cache; on a hit it replays the
   stored result instantly. On a miss it publishes stage events to Redis
   pub/sub (`analyze:{task_id}`) and scrapes the page with headless Chrome.
4. Headlines are extracted, preprocessed, and classified by the BiLSTM model.
5. The result is stored in the cache (7-minute TTL) and the client receives
   the events over WebSocket and renders the result.

> The API process never touches Chrome or the model — it only enqueues tasks
> and relays Redis events. That keeps it fast and horizontally scalable.

---

## Tech Stack

| Layer      | Technologies |
|------------|--------------|
| Backend    | Python 3.12, FastAPI, Uvicorn, Celery 5.6, Redis 8 |
| ML         | TensorFlow / Keras (Embedding + BiLSTM), NLTK, scikit-learn |
| Scraping   | Selenium 4, headless Chrome, BeautifulSoup4 |
| Frontend   | Next.js 16 (App Router), React 19, Tailwind CSS 4, Framer Motion |
| Tooling    | Docker + Docker Compose, pytest, pnpm-free npm |

---

## Repository Layout

```
├── backend/            # FastAPI app + Celery worker
│   ├── app/
│   │   ├── main.py         # FastAPI entrypoint, CORS, lifespan (NLTK download)
│   │   ├── config.py       # pydantic-settings configuration
│   │   ├── celery_app.py   # Celery instance (broker/result wiring)
│   │   ├── tasks.py        # analyze_url task (cache → scrape → classify → publish)
│   │   ├── routers/        # REST + WebSocket endpoints
│   │   └── services/       # scraper, preprocess, classifier, cache, events, stream
│   ├── tests/              # pytest suite (API + task event flow)
│   ├── requirements.txt
│   ├── Dockerfile          # lean image; deps installed by entry_point.sh
│   └── entry_point.sh      # runtime install (Chromium, NLTK data) + server start
├── frontend/            # Next.js 16 UI
│   ├── app/               # app/page.tsx landing page, app/analyze/ analyzer
│   ├── lib/api.ts         # API client + WebSocket helper
│   ├── Dockerfile
│   └── entry_point.sh
├── ml/                  # training pipeline (WELFake)
│   ├── download_data.py
│   ├── train.py
│   └── evaluate.py
├── models/              # trained artifacts (committed)
│   ├── CS_model.keras      # ~24 MB, Embedding + BiLSTM
│   └── tokenizer.pkl       # Keras tokenizer vocabulary
├── scripts/dev.ps1      # one-command local dev on Windows
├── docker-compose.yml   # redis + backend + worker + frontend
└── .env.example         # documented configuration template
```

---

## Getting Started

### Prerequisites

- **Docker Desktop** (Docker + Compose) — recommended path
- **Windows local path** — Python 3.12, Node.js 22+, npm, and a running Redis
  on `localhost:6379` (Docker `redis:7` is fine)
- ~4 GB free disk and a working internet connection on first start

### Option A — Docker (recommended)

```bash
docker compose up -d --build
```

| Service  | URL |
|----------|-----|
| Frontend (landing page) | http://localhost:3000 |
| Analyzer | http://localhost:3000/analyze |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

**How it works**

- Images are deliberately lean: the app code is baked in, but **dependencies
  (Chromium, TensorFlow, npm packages) install at container startup** via
  `entry_point.sh`. `docker compose build` is near-instant.
- Install caches live in named volumes (`pip-cache`, `selenium-cache`,
  `npm-cache`), so the first start pays the download cost and subsequent
  restarts are fast.
- Redis is internal-only (not published to the host) — it won't clash with a
  local Redis on port 6379.
- The Celery worker runs `--pool=solo`: one process, one model, one browser.
- The backend `entry_point.sh` also downloads the NLTK corpora (punkt,
  punkt_tab, stopwords, wordnet) for both the API and the worker, so the
  worker can tokenize and lemmatize without NLTK lookups failing.

**Overrides** — create a `.env` next to `docker-compose.yml`:

```dotenv
# Host port for the backend API (default 8000; change if taken)
BACKEND_PORT=8001
# URL the browser uses to reach the API (must match BACKEND_PORT)
NEXT_PUBLIC_API_URL=http://localhost:8001
```

Then recreate: `docker compose up -d`.

> The frontend bakes `NEXT_PUBLIC_API_URL` into the client bundle during its
> first `next build` (which happens at container startup). Change it before the
> first start, or wipe the frontend container afterwards.

**Useful commands**

```bash
docker compose logs -f backend      # follow the API logs
docker compose logs -f worker       # follow the Celery worker logs
docker compose ps                   # container status
docker compose down                 # stop everything (keeps volumes)
```

### Option B — Local development (Windows)

One command:

```powershell
.\scripts\dev.ps1
```

This ensures Redis (Docker), creates `.venv`, installs backend + frontend
dependencies, and starts the worker, API, and frontend.

Or manually:

```powershell
# 1. Redis (Celery broker/result backend)
docker run -d --name ai-fakenews-redis -p 6379:6379 redis:7

# 2. Python environment
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# 3. Celery worker — solo pool is REQUIRED on Windows
.\.venv\Scripts\python.exe -m celery -A app.celery_app worker --pool=solo --loglevel=info

# 4. Backend API (from backend/)
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# 5. Frontend
npm --prefix frontend install
npm --prefix frontend run dev          # http://localhost:3000
```

> Requires a locally installed Chrome/Chromium — Selenium Manager downloads the
> matching driver automatically.

---

## Configuration

All settings are read from environment variables (see `backend/app/config.py`
and `.env.example`).

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `models/CS_model.keras` | Trained Keras model |
| `TOKENIZER_PATH` | `models/tokenizer.pkl` | Keras tokenizer |
| `MAX_LEN` | `50` | Max tokens per headline |
| `ENABLE_KEYWORD_FILTER` | `false` | Only analyze cyber-security headlines |
| `CS_KEYWORDS` | list of security terms | Keywords used by the filter |
| `CORS_ORIGINS` | `localhost:3000/5173` | Allowed browser origins |
| `PAGE_LOAD_TIMEOUT` | `30` | Max seconds to load a page |
| `PAGE_WAIT_TIMEOUT` | `10` | Max seconds to wait for `<body>` |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker |
| `REDIS_RESULT_URL` | `redis://localhost:6379/1` | Celery result backend |
| `WS_IDLE_TIMEOUT` | `30` | WebSocket heartbeat idle seconds |
| `CACHE_ENABLED` | `true` | Enable the URL-keyed Redis result cache |
| `CACHE_TTL_SECONDS` | `420` | How long a cached analysis lives (7 minutes) |
| `REDIS_HEALTH_CHECK_INTERVAL` | `25` | Redis client health pings (stale-connection guard) |
| `REDIS_SOCKET_TIMEOUT` | `10` | Redis socket timeout |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | `5` | Redis connect timeout |
| `REDIS_SOCKET_KEEPALIVE` | `true` | TCP keepalive on Redis sockets |

> The Redis hardening options (health checks, timeouts, keepalive) exist because
> Redis is often reached through relays (WSL2, port-forwarders) that silently
> drop idle connections. Without them, idle clients can stall for minutes.

---

## API Reference

Interactive docs: `http://localhost:8000/docs`

### `GET /test` — health check

```bash
curl http://localhost:8000/test
# {"message":"Server is running!"}
```

### `POST /api/analyze` — enqueue an analysis

```bash
curl -X POST http://localhost:8000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"url": "https://thehackernews.com"}'
```

Response `202 Accepted`:

```json
{
  "task_id": "6f9c3a2e-8d2b-4f1e-9a1c-3b2e1f0a9c8d",
  "status": "queued",
  "url": "https://thehackernews.com"
}
```

### `GET /api/analyze/{task_id}` — poll status / result

```bash
curl http://localhost:8000/api/analyze/6f9c3a2e-8d2b-4f1e-9a1c-3b2e1f0a9c8d
```

While running:

```json
{ "task_id": "6f9c3a2e-...", "status": "PENDING" }
```

On success:

```json
{
  "task_id": "6f9c3a2e-...",
  "status": "SUCCESS",
  "result": {
    "url": "https://thehackernews.com",
    "total": 14,
    "real": 11,
    "fake": 3,
    "headlines": [
      { "headline": "Ransomware group hits hospital network", "trusted": "Fake", "confidence": 0.93 }
    ]
  }
}
```

On failure:

```json
{ "task_id": "6f9c3a2e-...", "status": "FAILURE", "error": "..." }
```

### `WS /ws/analyze/{task_id}` — stream progress

Connect with any WebSocket client (browser, websocat, Postman). Events are
JSON, one per message:

```json
{"type": "status", "stage": "scraping"}
{"type": "status", "stage": "analyzing", "total": 14}
{"type": "status", "stage": "done", "total": 14, "real": 11, "fake": 3}
{"type": "result", "result": { "url": "...", "total": 14, "real": 11, "fake": 3, "headlines": [...] }}
{"type": "error", "detail": "..."}
```

Behavior notes:

- Safe to connect at any time: if the task already finished, the terminal
  event is sent immediately and the socket closes.
- If no event arrives within `WS_IDLE_TIMEOUT`, the server re-checks the task
  state (heartbeat) so reconnects and long scrapes stay consistent.
- The socket closes after the terminal event (`result` or `error`).

### Errors

Validation failures return `4xx` with `{"detail": "..."}` (e.g. malformed URLs).
Scraping/inference failures are reported through the task status and the
`error` WebSocket event — the API never returns `500` for them.

---

## ML Pipeline

The classifier is an Embedding + Bidirectional LSTM trained on the
[WELFake](https://huggingface.co/datasets/davanstrien/WELFake) dataset
(72,960 labeled articles).

```powershell
.\.venv\Scripts\python.exe ml\download_data.py   # fetch WELFake (~145 MB) -> ml/data/
.\.venv\Scripts\python.exe ml\train.py           # train + save to models/
.\.venv\Scripts\python.exe ml\evaluate.py        # metrics on held-out test set
```

`ml/train.py` supports `--epochs` and `--batch-size` flags. A 10-epoch CPU
training run takes a few minutes.

**Current model**: test accuracy **~91%**, balanced Real/Fake F1 **~0.91**
(evaluated on 20% held-out WELFake test split).

---

## Testing

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

The suite (~22 tests) covers:

- API contract: enqueue `202`, status polling, validation errors.
- WebSocket streaming: stage/result/error events, terminal-event replay.
- Task logic: event publication sequence, keyword-filter behavior, and the
  URL-keyed cache (hit → no scraping; miss → result stored with TTL).
- Preprocessing and classifier unit tests.

---

## Observability & Operations

- **Health**: `GET /test` on the API.
- **Worker logs**: `docker compose logs -f worker` (Celery logs every task
  receive/succeed/fail with duration).
- **First request latency**: the model and Chrome driver load lazily in the
  worker on the first analysis; expect 60–120 s for the first run, then a few
  seconds per subsequent request. Re-analyzing the same URL within 7 minutes
  is served straight from the Redis cache (near-instant).
- **Memory**: the worker holds one Keras model and one Chrome process
  (`--pool=solo`). Restart the worker if Chrome processes accumulate.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Bind for 0.0.0.0:8000 failed: port is already allocated` | Another service owns 8000. Set `BACKEND_PORT=8001` in `.env` (and matching `NEXT_PUBLIC_API_URL`), then `docker compose up -d`. |
| Worker task fails with `Timeout reading from socket` | Stale Redis connection through a relay (WSL2/port-forwarder). The app now health-checks Redis connections; restart the worker after upgrading. |
| Celery `Task 'analyze_url' ... KeyError` in logs | Wrong module registration — run with `-A app.celery_app` (the app includes `app.tasks` automatically). |
| Empty results for a URL | The page has no `h1`–`h6` headlines, or they don't match keywords with `ENABLE_KEYWORD_FILTER=true`. Disable the filter or use another URL. |
| First analysis very slow | Model + browser warm-up in the worker (lazy loading). Expected; subsequent runs are fast. |
| `chromium` missing inside container | The backend `entry_point.sh` installs it on first start; check `docker compose logs backend` if it fails (apt may need retrying on flaky networks). |
| Task fails with NLTK `Resource punkt_tab not found` | NLTK data is downloaded by `entry_point.sh` in both containers. Recreate the containers (`docker compose up -d --build backend worker`); if the zip was downloaded but not extracted, delete `/root/nltk_data` inside the container and restart. |
| Frontend can't reach the API | `NEXT_PUBLIC_API_URL` was baked with the wrong host/port — it must be set before the frontend's first build (see Docker overrides above). |

---

## Security Notes

- No secrets are committed; configuration is via environment variables
  (`.env` is gitignored, `.env.example` is a template).
- CORS is restricted to the documented origins; tighten
  `CORS_ORIGINS` for production deployments.
- The API performs no client-side credentials/state beyond task IDs; results
  live in Redis with default TTL semantics (see Celery result expiry).
- The web scraper runs only inside the worker container/process — the API
  never fetches remote pages itself.

---

## License

Internal/prototype project. Contact the maintainers before reuse.
