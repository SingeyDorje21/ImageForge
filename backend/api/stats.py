"""Job analytics for the admin dashboard, computed from the jobs table over a time window."""
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models import Job

# Caps the rows one request aggregates so a busy window can't stall the API.
MAX_ROWS = 50_000


@dataclass
class JobRow:
    status: str
    operations: list[dict]
    original_filename: str
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime


async def fetch_rows(db: AsyncSession, since: datetime) -> list[JobRow]:
    query = (
        select(
            Job.status, Job.operations, Job.original_filename, Job.error_message,
            Job.retry_count, Job.created_at, Job.updated_at,
        )
        .where(Job.created_at >= since)
        .order_by(Job.created_at.desc())
        .limit(MAX_ROWS)
    )
    result = await db.execute(query)
    return [JobRow(*row) for row in result.all()]


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, max(0, round(pct / 100 * (len(sorted_values) - 1))))
    return sorted_values[index]


def _bucket_start(ts: datetime, hourly: bool) -> datetime:
    if hourly:
        return ts.replace(minute=0, second=0, microsecond=0)
    return ts.replace(hour=0, minute=0, second=0, microsecond=0)


def compute_stats(rows: list[JobRow], now: datetime, days: int) -> dict:
    """Aggregate job rows created in the last `days` days (ending at `now`, timezone-aware)."""
    hourly = days <= 2
    step = timedelta(hours=1) if hourly else timedelta(days=1)
    start = _bucket_start(now - timedelta(days=days), hourly) + step

    buckets: dict[datetime, Counter] = {}
    cursor = start
    while cursor <= now:
        buckets[cursor] = Counter()
        cursor += step

    statuses = Counter()
    operations = Counter()
    formats = Counter()
    errors = Counter()
    turnaround: list[float] = []
    total_steps = 0
    retries = 0

    for row in rows:
        statuses[row.status] += 1
        retries += row.retry_count
        total_steps += len(row.operations)
        operations.update(op.get("type", "unknown") for op in row.operations)
        ext = os.path.splitext(row.original_filename)[1].lower().lstrip(".")
        formats["jpg" if ext == "jpeg" else ext or "unknown"] += 1

        bucket = buckets.get(_bucket_start(row.created_at, hourly))
        if bucket is not None:
            bucket[row.status if row.status in ("completed", "failed") else "in_progress"] += 1

        if row.status == "completed":
            turnaround.append(max(0.0, (row.updated_at - row.created_at).total_seconds()))
        elif row.status == "failed" and row.error_message:
            errors[row.error_message.strip()[:200]] += 1

    total = len(rows)
    finished = statuses["completed"] + statuses["failed"]
    turnaround.sort()

    return {
        "window_days": days,
        "granularity": "hour" if hourly else "day",
        "generated_at": now.isoformat(),
        "truncated": total >= MAX_ROWS,
        "totals": {
            "jobs": total,
            "completed": statuses["completed"],
            "failed": statuses["failed"],
            "pending": statuses["pending"],
            "processing": statuses["processing"],
            "success_rate": round(statuses["completed"] / finished, 4) if finished else None,
            "retries": retries,
            "avg_steps_per_job": round(total_steps / total, 2) if total else 0,
        },
        "turnaround_sec": {
            "avg": round(sum(turnaround) / len(turnaround), 3) if turnaround else None,
            "p50": round(_percentile(turnaround, 50), 3) if turnaround else None,
            "p95": round(_percentile(turnaround, 95), 3) if turnaround else None,
        },
        "timeline": [
            {
                "bucket": ts.isoformat(),
                "completed": counts["completed"],
                "failed": counts["failed"],
                "in_progress": counts["in_progress"],
            }
            for ts, counts in buckets.items()
        ],
        "operations": [{"type": t, "count": c} for t, c in operations.most_common()],
        "formats": [{"format": f, "count": c} for f, c in formats.most_common()],
        "top_errors": [{"message": m, "count": c} for m, c in errors.most_common(5)],
    }
