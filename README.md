# DocQA — AI-Powered Document & Multimedia Q&A

A full-stack web application that lets users upload PDFs, audio, and video files and interact with an AI-powered chatbot to ask questions, get summaries, and navigate multimedia content via timestamped answers.

---

## Features

| Requirement | Implementation |
|---|---|
| Upload PDFs | pdfplumber + PyMuPDF extraction |
| Upload Audio/Video | OpenAI Whisper transcription with timestamps |
| AI Chatbot | GPT-4o via OpenAI API |
| Summarization | GPT-4o summarizes document/media content on upload |
| Timestamp extraction | Whisper verbose JSON with segment-level timestamps |
| Play button | Frontend seeks media player to exact timestamp |
| Vector search | FAISS + sentence-transformers (all-MiniLM-L6-v2) |
| Streaming responses | Server-Sent Events (SSE) real-time streaming |
| Multi-user auth | JWT Bearer tokens |
| Rate limiting | slowapi (60 req/min default) |
| Caching | Redis (document lists, query results) |
| 95%+ test coverage | pytest-cov enforced in CI |
| Docker | Dockerfile for backend + frontend |
| Docker Compose | 4-service stack (db, redis, backend, frontend) |
| CI/CD | GitHub Actions — test, lint, build, push to GHCR |

---

## Architecture

```
┌─────────────┐    ┌───────────────────────────────────────┐
│   Frontend  │    │              Backend (FastAPI)         │
│  React+Vite │───▶│  /api/v1/auth   /documents  /media    │
│  Tailwind   │    │  /chat/message  /chat/message/stream  │
└─────────────┘    └──────┬──────────┬──────────┬──────────┘
                          │          │          │
                   ┌──────▼──┐  ┌────▼────┐  ┌─▼──────┐
                   │PostgreSQL│  │  Redis  │  │ FAISS  │
                   │(metadata)│  │ (cache) │  │(vector)│
                   └──────────┘  └─────────┘  └────────┘
                          │
                   ┌──────▼──────────────────────────────┐
                   │          OpenAI APIs                  │
                   │  GPT-4o (chat/summary) + Whisper      │
                   └────────────────────────────────────── ┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- An [OpenAI API key](https://platform.openai.com/api-keys)

### 1. Clone & configure

```bash
git clone <your-repo-url>
cd docqa

cp .env.example .env
# Edit .env and set your OPENAI_API_KEY and SECRET_KEY
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

The app will be available at **http://localhost**.

API docs: **http://localhost/api/v1/docs**

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=sk-your-key
export SECRET_KEY=dev-secret
export DATABASE_URL=postgresql+asyncpg://docqa:docqa@localhost:5432/docqa
export REDIS_URL=redis://localhost:6379/0

# Start local postgres and redis (or use docker)
docker run -d -p 5432:5432 -e POSTGRES_USER=docqa -e POSTGRES_PASSWORD=docqa -e POSTGRES_DB=docqa postgres:16-alpine
docker run -d -p 6379:6379 redis:7-alpine

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Testing

### Backend (95%+ coverage enforced)

```bash
cd backend
pytest
```

Or with explicit coverage report:

```bash
pytest --cov=app --cov-report=html --cov-fail-under=95
# Open htmlcov/index.html for the report
```

### Frontend

```bash
cd frontend
npm test
npm run test:coverage
```

---

## API Documentation

Interactive Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

#### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, returns JWT |
| GET | `/api/v1/auth/me` | Get current user |

#### Documents
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/documents/upload` | Upload PDF (multipart/form-data) |
| GET | `/api/v1/documents/` | List all documents |
| GET | `/api/v1/documents/{id}` | Get document details + extracted text |
| DELETE | `/api/v1/documents/{id}` | Delete document |

#### Media
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/media/upload` | Upload audio/video (auto-transcribes) |
| GET | `/api/v1/media/` | List all media files |
| GET | `/api/v1/media/{id}` | Get media + transcription + segments |
| DELETE | `/api/v1/media/{id}` | Delete media |

#### Chat
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/chat/sessions` | Create chat session |
| GET | `/api/v1/chat/sessions` | List sessions |
| GET | `/api/v1/chat/sessions/{id}` | Get session with messages |
| POST | `/api/v1/chat/message` | Send message (non-streaming) |
| POST | `/api/v1/chat/message/stream` | Send message (SSE streaming) |
| DELETE | `/api/v1/chat/sessions/{id}` | Delete session |

### Example: Upload & Chat

```bash
# Register
curl -X POST http://localhost/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","username":"you","password":"password123"}'

# Upload PDF
curl -X POST http://localhost/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"

# Create chat session
curl -X POST http://localhost/api/v1/chat/sessions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"document_id": 1, "title": "PDF Analysis"}'

# Ask a question
curl -X POST http://localhost/api/v1/chat/message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"session_id": 1, "message": "What are the main points?", "stream": false}'
```

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (auth, documents, media, chat)
│   │   ├── core/            # Security (JWT), rate limiter
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic
│   │   │   ├── pdf_service.py
│   │   │   ├── transcription_service.py   # Whisper
│   │   │   ├── llm_service.py             # GPT-4o
│   │   │   ├── vector_service.py          # FAISS
│   │   │   └── cache_service.py           # Redis
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/               # 95%+ coverage
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # FileUpload, ChatInterface, TimestampList, MediaPlayer, SummaryPanel
│   │   ├── pages/           # Login, Register, Dashboard
│   │   ├── services/        # API client
│   │   ├── store/           # Zustand state management
│   │   └── types/           # TypeScript interfaces
│   ├── Dockerfile
│   └── nginx.conf
├── .github/workflows/ci-cd.yml
├── docker-compose.yml
└── README.md
```

---

## Environment Variables

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for GPT-4o + Whisper | Yes |
| `SECRET_KEY` | JWT signing secret (use long random string) | Yes |
| `DATABASE_URL` | PostgreSQL async connection URL | Yes |
| `REDIS_URL` | Redis connection URL | Yes |
| `DEBUG` | Enable debug mode | No (default: false) |
| `MAX_FILE_SIZE_MB` | Max upload size in MB | No (default: 100) |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | No (default: 60) |

---

## Bonus Features Implemented

- **Vector search**: FAISS + sentence-transformers for semantic document search
- **Streaming**: Real-time SSE streaming of chat responses
- **Multi-user auth**: JWT-based authentication with bcrypt password hashing
- **Rate limiting**: slowapi middleware (per-IP)
- **Caching**: Redis caches document/media lists (5 min TTL)
