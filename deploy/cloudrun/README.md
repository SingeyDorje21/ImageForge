# Deploying to Google Cloud Run (scale to zero)

Everything here runs only when it's used. With no traffic, nothing is billed
except storage.

| Piece | Service | Idle cost |
| --- | --- | --- |
| API | Cloud Run `imageforge-api` (public, min instances 0) | $0 |
| Worker | Cloud Run `imageforge-worker` (private, min instances 0) | $0 |
| Queue | Cloud Tasks queue `image-jobs`, pushes jobs to the worker over HTTP | $0 (first 1M tasks/month free) |
| Database | [Neon](https://neon.tech) serverless Postgres, suspends when idle | $0 on the free plan |
| Redis | [Upstash](https://upstash.com), billed per request | $0 on the free plan |
| Images | [Cloudflare R2](https://developers.cloudflare.com/r2/), no download (egress) fees | $0 up to 10 GB |
| Frontend | [Cloudflare Pages](https://pages.cloudflare.com) | $0 |

Cloud Run's free tier also covers 2M requests and 180k vCPU-seconds per month.
Expect a cold start of a second or two on the first request after a quiet period.

## How jobs flow

1. `POST /jobs` uploads the original to R2, writes the job to Postgres and creates
   a Cloud Task (`QUEUE_BACKEND=cloudtasks`).
2. Cloud Tasks POSTs `{"job_id": ...}` to the worker's `/tasks/process`, signed
   with an OIDC token for `imageforge-tasks@`; Cloud Run rejects anyone else.
3. The worker processes the image and returns 200. On a transient error it returns
   503 and Cloud Tasks retries with backoff, up to `MAX_RETRIES`. After that the job
   is marked `failed`, which replaces RabbitMQ's dead-letter queue.

Local development and `docker compose` still use RabbitMQ (`QUEUE_BACKEND=rabbitmq`,
the default) so everything runs offline.

## One-time setup

1. **Google Cloud**: create a project with billing enabled. Install the
   [gcloud CLI](https://cloud.google.com/sdk/docs/install) and run `gcloud auth login`,
   or use Cloud Shell (it has gcloud and bash ready).
2. **Neon**: create a project and database. Copy the *direct* connection string
   (not the `-pooler` host; asyncpg's prepared statements don't work through PgBouncer).
   Change `postgresql://` to `postgresql+asyncpg://` and `sslmode=require` to `ssl=require`.
3. **Upstash**: create a Redis database in the region closest to your Cloud Run region
   and copy its `rediss://` URL.
4. **Cloudflare R2**: create a bucket, then an R2 API token with Object Read & Write
   for it. Note the account ID, access key ID and secret.
5. Copy `deploy/cloudrun/config.example.env` to `deploy/cloudrun/config.env`
   (git-ignored) and fill it in.

## Deploy

```bash
./deploy/cloudrun/deploy.sh
```

The script enables the APIs, creates the service accounts, Secret Manager secrets,
the Cloud Tasks queue and both Cloud Run services, then prints the API URL. Re-run
it to ship a new version. The API applies database migrations on startup.

## Frontend on Cloudflare Pages

Connect the repo in Cloudflare Pages with:

- Root directory: `frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL` = the API URL the deploy script printed

Then make sure `CORS_ORIGINS` in `config.env` is the Pages URL (for example
`https://imageforge.pages.dev`) and re-run the deploy script if you changed it.
