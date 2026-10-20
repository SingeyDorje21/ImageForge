"""Unit tests for the admin analytics. No services needed: run with `pytest tests/test_stats.py`."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from api.stats import JobRow, compute_stats  # noqa: E402

NOW = datetime(2026, 10, 20, 12, 30, tzinfo=timezone.utc)


def row(status="completed", ops=("resize",), name="a.png", error=None, retries=0, ago=timedelta(hours=1), took=2.0):
    created = NOW - ago
    return JobRow(
        status=status,
        operations=[{"type": t} for t in ops],
        original_filename=name,
        error_message=error,
        retry_count=retries,
        created_at=created,
        updated_at=created + timedelta(seconds=took),
    )


def test_empty_window():
    stats = compute_stats([], NOW, 7)
    assert stats["totals"]["jobs"] == 0
    assert stats["totals"]["success_rate"] is None
    assert stats["turnaround_sec"] == {"avg": None, "p50": None, "p95": None}
    assert len(stats["timeline"]) == 7
    assert stats["granularity"] == "day"


def test_totals_and_rates():
    rows = [
        row(took=1), row(took=3), row(took=5),
        row(status="failed", error="Bad image", retries=3),
        row(status="pending"),
    ]
    stats = compute_stats(rows, NOW, 7)
    totals = stats["totals"]
    assert totals["jobs"] == 5
    assert totals["completed"] == 3
    assert totals["failed"] == 1
    assert totals["pending"] == 1
    assert totals["success_rate"] == 0.75
    assert totals["retries"] == 3
    assert stats["turnaround_sec"]["avg"] == 3.0
    assert stats["turnaround_sec"]["p50"] == 3.0
    assert stats["turnaround_sec"]["p95"] == 5.0
    assert stats["top_errors"] == [{"message": "Bad image", "count": 1}]


def test_operations_and_formats_counted():
    rows = [
        row(ops=("resize", "format_convert"), name="x.JPEG"),
        row(ops=("resize",), name="y.jpg"),
        row(ops=("grayscale",), name="z.webp"),
    ]
    stats = compute_stats(rows, NOW, 7)
    assert stats["operations"][0] == {"type": "resize", "count": 2}
    assert {"format": "jpg", "count": 2} in stats["formats"]
    assert {"format": "webp", "count": 1} in stats["formats"]
    assert stats["totals"]["avg_steps_per_job"] == round(4 / 3, 2)


def test_hourly_timeline_places_jobs_in_their_hour():
    rows = [
        row(ago=timedelta(minutes=10)),
        row(status="failed", ago=timedelta(minutes=20)),
        row(status="processing", ago=timedelta(hours=3)),
    ]
    stats = compute_stats(rows, NOW, 1)
    assert stats["granularity"] == "hour"
    timeline = {point["bucket"]: point for point in stats["timeline"]}
    current = timeline[NOW.replace(minute=0).isoformat()]
    assert current["completed"] == 1 and current["failed"] == 1
    earlier = timeline[(NOW - timedelta(hours=3)).replace(minute=0).isoformat()]
    assert earlier["in_progress"] == 1
    assert sum(p["completed"] + p["failed"] + p["in_progress"] for p in stats["timeline"]) == 3
