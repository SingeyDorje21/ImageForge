# Load testing

`locustfile.py` drives the whole job lifecycle the way the web app does: upload an
image with a chain of operations (`POST /jobs`), poll `GET /jobs/{id}` until it
finishes, then download the result through its signed URL. Next to Locust's normal
per-request stats it reports one `JOB` row per job, timed from upload to
`completed`, so you get job throughput, end-to-end p50/p95 and failure rate in one
table. It never calls `/login` or any admin endpoint.

```bash
pip install -r tests/perf/requirements.txt
```

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `IMAGE_SIZE` | `1920x1080` | Source image, generated in memory as a noisy JPEG (~1.5 MB at the default) |
| `OPS_PROFILE` | `chain` | `light` (resize + WebP), `chain` (resize, rotate, sharpen, watermark, quality, JPG), `heavy` (full-size blur, sharpen, grayscale, watermark, PNG) |
| `PACING_SECONDS` | `15` | Minimum seconds between uploads per simulated user; `0` uploads back to back |
| `POLL_SECONDS` | `1` | Seconds between status polls. End-to-end times are only as precise as this |
| `JOB_TIMEOUT` | `120` | A job not finished by then counts as a failure |
| `DOWNLOAD` | `true` | Also download each result |

Locust's own flags set the load: `-u` users, `-r` spawn rate, `-t` duration, and
`--csv out/run` writes the numbers to CSV. Leave off `--headless` to watch it live in
the Locust web UI on http://localhost:8089.

The defaults are deliberately small: 2 users at one upload per 15 seconds each is
8 uploads a minute, under the API's limit of 10 uploads per minute per IP. A user
that does get a 429 counts it as a failure and pauses 10 seconds.

## Against the local stack

The API rate-limits uploads per IP, and a load test comes from one IP, so start the
API with the limit raised and run more than one worker:

```bash
RATE_LIMIT_PER_MINUTE=100000 docker compose up -d --build --scale worker=3

PACING_SECONDS=0 POLL_SECONDS=0.25 \
  locust -f tests/perf/locustfile.py --headless -H http://localhost:8000 -u 8 -r 8 -t 60s
```

## Against the deployed Cloud Run API

This sends real traffic to production. It scales Cloud Run up from zero, writes
objects to R2 and rows to Neon, and spends Upstash commands, so keep it short. Test
jobs show up in the admin dashboard as `perf-*.jpg`.

```bash
API_URL="$(gcloud run services describe imageforge-api --region us-central1 --format 'value(status.url)')"

# Safe default: 2 users, ~8 uploads/min, for 2 minutes (about 16 jobs)
locust -f tests/perf/locustfile.py --headless -H "$API_URL" -u 2 -r 1 -t 2m
```

The first job or two include cold starts of the API and worker services, so read p95
and the run as a whole rather than the max. Run it twice in a row to see warm numbers.

From one machine you cannot push past 10 uploads a minute, because `TRUST_PROXY_HEADERS`
makes the limit count your real IP. To measure actual capacity, raise the limit for
the duration of the test and put it back afterwards:

```bash
gcloud run services update imageforge-api --region us-central1 --update-env-vars RATE_LIMIT_PER_MINUTE=1000
PACING_SECONDS=0 locust -f tests/perf/locustfile.py --headless -H "$API_URL" -u 6 -r 2 -t 2m
gcloud run services update imageforge-api --region us-central1 --update-env-vars RATE_LIMIT_PER_MINUTE=10
```

Expect throughput to flatten around the worker's limits from `deploy.sh`: at most 3
worker instances with 1 vCPU each, and Cloud Tasks dispatching at most 10 jobs at
once. Image processing is CPU-bound, so 4 concurrent requests per worker instance
share one vCPU.

## Baseline (local, October 2026)

Measured on a 4-vCPU Linux VM with Postgres, Redis, RabbitMQ and SeaweedFS in Docker
and the API (one uvicorn process) and workers running on the host, with the load
generator on the same machine. `POLL_SECONDS=0.25`, `PACING_SECONDS=0`, 60 s per
row, 1920x1080 input unless noted. No row had a failure.

| Workers | Users | Profile | Jobs/s | Job p50 | Job p95 | Upload p95 | Worker time/job |
|---|---|---|---|---|---|---|---|
| 1 | 1 | chain | 3.2 | 310 ms | 330 ms | 65 ms | 0.15 s |
| 1 | 4 | chain | 6.8 | 570 ms | 830 ms | 89 ms | 0.14 s |
| 1 | 8 | chain | 6.7 | 1.1 s | 1.4 s | 110 ms | 0.15 s |
| 1 | 16 | chain | 6.6 | 2.4 s | 2.7 s | 150 ms | 0.15 s |
| 3 | 8 | chain | 14.5 | 590 ms | 730 ms | 200 ms | 0.19 s |
| 3 | 16 | chain | 13.9 | 1.2 s | 1.5 s | 260 ms | 0.21 s |
| 3 | 16 | light | 16.3 | 920 ms | 1.2 s | 290 ms | 0.18 s |
| 3 | 8 | heavy | 1.6 | 5.0 s | 5.5 s | 200 ms | 1.74 s |
| 3 | 8 | chain, 3840x2160 | 7.4 | 1.0 s | 1.6 s | 460 ms | 0.39 s |

What it shows:

- **Workers are the bottleneck.** One worker tops out at about 1 / (time per job),
  roughly 6.7 jobs/s for the chain profile, and past that extra users only lengthen
  the queue: p50 grows linearly with users while throughput stays flat. Three
  workers more than doubled throughput; on this 4-vCPU box they then competed with
  the API and load generator for CPU.
- **The API is not.** Upload p95 stayed under 300 ms and status polls under 60 ms at
  16 users; uploads slow mainly with file size (460 ms p95 for 4K).
- **Output encoding dominates heavy jobs.** Encoding a full-size 1080p image as PNG
  takes ~0.65 s and as WebP ~0.45 s, while blur, sharpen or grayscale each take
  0.03-0.11 s. Large PNG/WebP outputs are the slowest jobs you can submit.
- **The upload limit caps one client at 10 jobs a minute**, far below what the
  system can process; an unpaced test from one IP gets 429 on nearly every upload.
