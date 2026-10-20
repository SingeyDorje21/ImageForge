# IMAGEFLOW ⚡

![Architecture Banner](https://img.shields.io/badge/Architecture-Distributed_System-blue?style=for-the-badge) ![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi) ![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB) ![RabbitMQ](https://img.shields.io/badge/Rabbitmq-FF6600?style=for-the-badge&logo=rabbitmq&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)

**ImageFlow** (formerly ImageForge) is a high-performance, asynchronous, distributed image processing pipeline. Built with a neo-brutalist dark aesthetic, the system is designed to offload heavy image manipulations (resizing, format conversion) to a fleet of backend workers without blocking the main API thread.

---

## 🏗️ Architecture & Workflow

At its core, ImageFlow embraces a highly decoupled microservices architecture:

1. **The Client (React SPA)**: End-users upload images and processing instructions (e.g., "convert to WebP", "resize to 800x600") via a stunning, responsive landing page.
2. **API Hub (FastAPI)**: The central gateway. It intercepts uploads, enforces rate-limiting via **Redis**, saves the original file to S3-compatible object storage, logs a `pending` job in **PostgreSQL**, and publishes the `job_id` to a message queue.
3. **Message Queue (RabbitMQ locally, Google Cloud Tasks in production)**: Acts as the robust buffer. It guarantees delivery and retries failed jobs with backoff; RabbitMQ also keeps a Dead Letter Queue (DLQ).
4. **Worker Nodes (Python Async)**: Dedicated headless processors subscribe to the RabbitMQ queue. They pull the original image, perform the heavy CPU-bound image operations using **Pillow**, upload the result to object storage, and update the PostgreSQL database state to `completed`.
5. **Real-time Sync**: The frontend continuously polls the API to visually represent the processing timeline and dynamically unlocks a short-lived signed download link the moment the worker node finishes the job.

### System Diagram

![alt text](<Screenshot 2026-08-09 140220.png>)

---

## 🛠️ Technology Stack

### Frontend (Client Tier)
- **Vite + React**: Blazing fast modern frontend build tool and UI library.
- **Tailwind CSS**: Utility-first CSS framework used to build the responsive, neo-brutalist UI.
- **Chart.js**: For visualizing system metrics and queue health in the Admin Portal.
- **Lucide React**: Crisp, modern SVG icon library.

### Backend (API Tier)
- **FastAPI**: Modern, fast (high-performance) web framework for building APIs with Python 3.7+ based on standard Python type hints.
- **Uvicorn**: Lightning-fast ASGI server implementation.
- **SQLAlchemy (Async)**: Python SQL toolkit and Object Relational Mapper for database interactions.

### Infrastructure & Data Tier
- **RabbitMQ**: AMQP-based message broker for reliable task distribution.
- **PostgreSQL**: Relational database for persistent job tracking and state management.
- **Redis**: In-memory data structure store used for API rate-limiting (10 uploads/min) and global system metrics caching.
- **Docker Compose**: Container orchestration to instantly spin up the infrastructure layer.

---

## 🎛️ Image Operations

`POST /jobs` takes a JSON array of operations in the `operations` form field. They run in order, so you can chain them (e.g. crop, then resize, then watermark, then convert to WebP).

| `type` | Parameters |
|---|---|
| `resize` | `width`, `height` (1-10000) |
| `crop` | `left`, `top` (0-10000), `width`, `height` (1-10000). Fails the job if the box is outside the image. |
| `rotate` | `degrees` (-360 to 360, counter-clockwise), `expand` (default `true`, grows the canvas to fit) |
| `flip` | `direction`: `horizontal` or `vertical` |
| `grayscale` | none |
| `blur` | `radius` (default 2) |
| `sharpen` | `radius` (default 2), `percent` (strength, default 150) |
| `watermark` | `text`, `position` (`top_left`, `top_right`, `bottom_left`, `bottom_right`, `center`), `opacity` (0-1, default 0.5), `font_size` (default 24) |
| `quality` | `quality` (1-100) for JPEG/WebP output. PNG output is always lossless and optimized. |
| `strip_exif` | none. Without it, the original EXIF metadata is kept. |
| `format_convert` | `target_format`: `jpg`, `png` or `webp` |

Example:

```json
[
  {"type": "crop", "left": 0, "top": 0, "width": 800, "height": 800},
  {"type": "resize", "width": 400, "height": 400},
  {"type": "watermark", "text": "© Me", "position": "bottom_right"},
  {"type": "strip_exif"},
  {"type": "quality", "quality": 80},
  {"type": "format_convert", "target_format": "webp"}
]
```

Operation unit tests run without any services: `pip install pytest pillow pydantic pydantic-settings && pytest tests/test_operations.py`.

## 🚀 How to Run Locally

### Option A: everything in Docker
```bash
docker compose up -d --build
```
This starts Postgres, Redis, RabbitMQ, a local S3-compatible store (SeaweedFS), the API, the worker and the frontend. The API applies Alembic migrations on startup and creates the bucket.

- Frontend: `http://localhost:5173/` (admin at `/login`; set `ADMIN_PASSWORD` and `JWT_SECRET` in your shell or a root `.env` before `docker compose up`, or login stays disabled)
- API docs: `http://localhost:8000/docs`

### Option B: infra in Docker, app on your machine
```bash
docker compose up -d postgres redis rabbitmq s3

cd backend
python -m venv venv && source venv/bin/activate   # .\venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env   # then set ADMIN_PASSWORD and JWT_SECRET, see "Security configuration"
alembic upgrade head
uvicorn api.main:app --reload --port 8000        # terminal 1
python -m worker.main                            # terminal 2

cd ../frontend && npm install && npm run dev     # terminal 3
```

## ☁️ Configuration for deployment

To deploy to Google Cloud Run with everything scaled to zero when idle (Cloud Tasks, Neon, Upstash and Cloudflare R2, with the frontend on Vercel), follow [deploy/cloudrun/README.md](deploy/cloudrun/README.md).

There are two worker entrypoints: `python -m worker.main` consumes RabbitMQ (local and compose), and `uvicorn worker.server:app` is the HTTP worker Cloud Tasks pushes to.

Files live in any S3-compatible bucket (AWS S3, Cloudflare R2, Google Cloud Storage, DigitalOcean Spaces, MinIO, SeaweedFS). Results are served through signed URLs; `GET /jobs/{id}` returns `result_url`, and `GET /jobs/{id}/download` redirects to it.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `DATABASE_URL`, `REDIS_URL` | API, worker | Backing services |
| `QUEUE_BACKEND` | API | `rabbitmq` (default, local) or `cloudtasks` (Cloud Run) |
| `RABBITMQ_URL` | API, worker | Broker for `QUEUE_BACKEND=rabbitmq` |
| `GCP_PROJECT`, `GCP_LOCATION`, `CLOUD_TASKS_QUEUE` | API | Cloud Tasks queue for `QUEUE_BACKEND=cloudtasks` |
| `WORKER_URL`, `TASKS_SERVICE_ACCOUNT` | API | HTTP worker that Cloud Tasks calls, and the account that signs its OIDC token |
| `S3_BUCKET`, `S3_REGION` | API, worker | Bucket to store originals and results |
| `S3_ENDPOINT_URL` | API, worker | Leave unset for AWS S3; set for R2, GCS, Spaces, MinIO |
| `S3_PUBLIC_ENDPOINT_URL` | API | Host put in signed URLs when browsers reach storage on a different host |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | API, worker | Storage credentials (omit to use the cloud's IAM role) |
| `S3_FORCE_PATH_STYLE` | API, worker | `true` for MinIO/SeaweedFS |
| `S3_URL_EXPIRY_SECONDS` | API | Lifetime of signed download URLs (default 3600) |
| `S3_CREATE_BUCKET` | API | Create the bucket on startup (local dev) |
| `RATE_LIMIT_PER_MINUTE` | API | Uploads per client IP per minute (default 10) |
| `RUN_MIGRATIONS` | API image | `false` to skip `alembic upgrade head` on startup |
| `VITE_API_URL` | frontend build | Public URL of the API, baked in at build time |

### Security configuration
| Variable | Purpose |
| --- | --- |
| `ADMIN_PASSWORD` | Admin portal password. Login is disabled (HTTP 503) until it is set. |
| `JWT_SECRET` | Key that signs admin tokens. If unset, a random key is used and tokens stop working on restart. |
| `TOKEN_TTL_MINUTES` | How long an admin token stays valid (default 60). |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_WINDOW_SECONDS` | Failed logins allowed per client IP within the window (default 5 per 15 minutes); further attempts get HTTP 429 until it expires. |
| `TRUST_PROXY_HEADERS` | Set to `true` on Cloud Run or behind another proxy so rate limits use the client IP from `X-Forwarded-For` (default `false`). |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to call the API (default `http://localhost:5173`). |

`GET /jobs` and `GET /metrics` require an `Authorization: Bearer <token>` header obtained from `POST /login`.

---
*Developed as a showcase for high-performance, asynchronous system design.*
