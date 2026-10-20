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
| Frontend | [Vercel](https://vercel.com) | $0 on the Hobby plan (personal, non-commercial use) |

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
2. **Neon**: create a project and database. Copy the connection string exactly as
   Neon shows it. The pooled one (host contains `-pooler`) is recommended for Cloud Run;
   the app turns off asyncpg's prepared-statement cache for pooled hosts and converts
   the URL for asyncpg itself.
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

## Frontend on Vercel

`frontend/vercel.json` builds the Vite app and rewrites every path to `index.html`,
so routes like `/login` and `/admin` load on refresh or a direct link.

1. In Vercel, **Add New → Project** and import the repo.
2. Set **Root Directory** to `frontend`. Vercel picks up the build settings from `vercel.json`.
3. Under **Environment Variables**, add `VITE_API_URL` = the API URL the deploy script
   printed (for example `https://imageforge-api-xxxx-uc.a.run.app`), for Production and Preview.
   It's baked in at build time, so redeploy after changing it.
4. Deploy, then set `CORS_ORIGINS` in `config.env` to your Vercel domain (for example
   `https://imageforge.vercel.app`) and re-run `./deploy/cloudrun/deploy.sh`.

`CORS_ORIGINS` takes a comma-separated list, so add a custom domain alongside the
`.vercel.app` one if you use both. Preview deployments get their own URLs; they can
only call the API if you add those origins too.
