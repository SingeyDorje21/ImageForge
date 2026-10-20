#!/usr/bin/env bash
# Deploys ImageForge to Google Cloud Run with Cloud Tasks, scaled to zero when idle.
# Prereqs: gcloud CLI logged in, billing enabled on the project, and
# deploy/cloudrun/config.env filled in from config.example.env.
# Safe to re-run: existing resources are reused and services get a new revision.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck disable=SC1091
set -a; source "$HERE/config.env"; set +a

PROJECT="$GCP_PROJECT"
REGION="${GCP_REGION:-us-central1}"
REPO=imageforge
QUEUE=image-jobs
MAX_RETRIES="${MAX_RETRIES:-3}"
IMAGE_BASE="$REGION-docker.pkg.dev/$PROJECT/$REPO"
RUN_SA="imageforge-run@$PROJECT.iam.gserviceaccount.com"
TASKS_SA="imageforge-tasks@$PROJECT.iam.gserviceaccount.com"

gcloud config set project "$PROJECT" >/dev/null

echo "==> Enabling APIs"
gcloud services enable run.googleapis.com cloudtasks.googleapis.com \
  artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com

echo "==> Artifact Registry repo"
gcloud artifacts repositories describe "$REPO" --location "$REGION" >/dev/null 2>&1 ||
  gcloud artifacts repositories create "$REPO" --repository-format docker --location "$REGION"

echo "==> Service accounts"
for sa in imageforge-run imageforge-tasks; do
  gcloud iam service-accounts describe "$sa@$PROJECT.iam.gserviceaccount.com" >/dev/null 2>&1 ||
    gcloud iam service-accounts create "$sa"
done
# The API creates tasks that carry an OIDC token for the tasks service account
gcloud projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$RUN_SA" \
  --role roles/cloudtasks.enqueuer --condition None >/dev/null
gcloud iam service-accounts add-iam-policy-binding "$TASKS_SA" --member "serviceAccount:$RUN_SA" \
  --role roles/iam.serviceAccountUser >/dev/null

# DATABASE_URL -> imageforge-database-url
secret_name() {
  echo "imageforge-$1" | tr '[:upper:]_' '[:lower:]-'
}

echo "==> Secrets"
SECRETS=(DATABASE_URL REDIS_URL S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY ADMIN_PASSWORD JWT_SECRET)
for name in "${SECRETS[@]}"; do
  secret="$(secret_name "$name")"
  gcloud secrets describe "$secret" >/dev/null 2>&1 ||
    gcloud secrets create "$secret" --replication-policy automatic >/dev/null
  printf '%s' "${!name}" | gcloud secrets versions add "$secret" --data-file - >/dev/null
  gcloud secrets add-iam-policy-binding "$secret" --member "serviceAccount:$RUN_SA" \
    --role roles/secretmanager.secretAccessor >/dev/null
done
secret_flags() {
  local flags="" name
  for name in "$@"; do
    flags+="$name=$(secret_name "$name"):latest,"
  done
  echo "${flags%,}"
}

echo "==> Building images"
gcloud builds submit "$ROOT" --config "$HERE/cloudbuild.yaml" \
  --substitutions "_REGION=$REGION,_REPO=$REPO"

# "^@^" switches gcloud's env-var separator to "@" so values may contain commas
COMMON_ENV="S3_BUCKET=$S3_BUCKET@S3_ENDPOINT_URL=$S3_ENDPOINT_URL@S3_REGION=$S3_REGION@MAX_RETRIES=$MAX_RETRIES"

echo "==> Worker service (private, invoked only by Cloud Tasks)"
gcloud run deploy imageforge-worker --image "$IMAGE_BASE/worker:latest" --region "$REGION" \
  --service-account "$RUN_SA" --no-allow-unauthenticated \
  --command uvicorn --args "worker.server:app,--host,0.0.0.0,--port,8080" --port 8080 \
  --min-instances 0 --max-instances 3 --concurrency 4 --cpu 1 --memory 1Gi --timeout 300 \
  --set-env-vars "^@^$COMMON_ENV" \
  --set-secrets "$(secret_flags DATABASE_URL REDIS_URL S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY)"
WORKER_URL="$(gcloud run services describe imageforge-worker --region "$REGION" --format 'value(status.url)')"
gcloud run services add-iam-policy-binding imageforge-worker --region "$REGION" \
  --member "serviceAccount:$TASKS_SA" --role roles/run.invoker >/dev/null

echo "==> Cloud Tasks queue"
QUEUE_FLAGS=(--location "$REGION" --max-attempts "$((MAX_RETRIES + 1))"
  --min-backoff 5s --max-backoff 60s --max-concurrent-dispatches 10)
if gcloud tasks queues describe "$QUEUE" --location "$REGION" >/dev/null 2>&1; then
  gcloud tasks queues update "$QUEUE" "${QUEUE_FLAGS[@]}"
else
  gcloud tasks queues create "$QUEUE" "${QUEUE_FLAGS[@]}"
fi

echo "==> API service (public)"
gcloud run deploy imageforge-api --image "$IMAGE_BASE/api:latest" --region "$REGION" \
  --service-account "$RUN_SA" --allow-unauthenticated --port 8000 \
  --min-instances 0 --max-instances 3 --cpu 1 --memory 512Mi \
  --set-env-vars "^@^$COMMON_ENV@QUEUE_BACKEND=cloudtasks@GCP_PROJECT=$PROJECT@GCP_LOCATION=$REGION@CLOUD_TASKS_QUEUE=$QUEUE@WORKER_URL=$WORKER_URL@TASKS_SERVICE_ACCOUNT=$TASKS_SA@CORS_ORIGINS=$CORS_ORIGINS@TRUST_PROXY_HEADERS=true" \
  --set-secrets "$(secret_flags DATABASE_URL REDIS_URL S3_ACCESS_KEY_ID S3_SECRET_ACCESS_KEY ADMIN_PASSWORD JWT_SECRET)"
API_URL="$(gcloud run services describe imageforge-api --region "$REGION" --format 'value(status.url)')"

echo
echo "Done."
echo "  API:    $API_URL"
echo "  Worker: $WORKER_URL (private)"
echo "Set VITE_API_URL=$API_URL in your Vercel project and redeploy the frontend"
