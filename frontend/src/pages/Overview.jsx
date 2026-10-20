import React, { useEffect, useState } from 'react';
import axios from 'axios';
import clsx from 'clsx';
import {
  Chart as ChartJS,
  ArcElement,
  BarElement,
  CategoryScale,
  Legend,
  LinearScale,
  Tooltip,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { authHeaders, handleAuthError } from '../auth';
import { API_BASE } from '../config';
import { OPERATIONS } from '../lib/operations';
import { useTheme } from '../lib/theme';

ChartJS.register(ArcElement, BarElement, CategoryScale, Legend, LinearScale, Tooltip);
ChartJS.defaults.font.family = "Inter, ui-sans-serif, system-ui, sans-serif";

const RANGES = [
  { days: 1, label: '24h' },
  { days: 7, label: '7d' },
  { days: 30, label: '30d' },
];

// Reads a theme color token from index.css so charts follow light and dark mode.
const cssColor = (name, alpha = 1) => {
  const rgb = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim().split(/\s+/).join(', ');
  return `rgba(${rgb}, ${alpha})`;
};

const formatDuration = (sec) => {
  if (sec == null) return '—';
  if (sec < 1) return `${Math.round(sec * 1000)} ms`;
  if (sec < 60) return `${sec.toFixed(1)} s`;
  return `${(sec / 60).toFixed(1)} min`;
};

const formatPercent = (rate) => (rate == null ? '—' : `${(rate * 100).toFixed(1)}%`);

const Stat = ({ label, value, hint, tone }) => (
  <div className="card p-4">
    <p className="label">{label}</p>
    <p className={clsx('text-2xl font-semibold tabular-nums mt-1.5', tone)}>{value}</p>
    {hint && <p className="text-xs text-muted mt-1">{hint}</p>}
  </div>
);

const Panel = ({ title, className, children, aside }) => (
  <section className={clsx('card p-5 flex flex-col', className)}>
    <div className="flex items-center justify-between mb-4">
      <h2 className="label">{title}</h2>
      {aside}
    </div>
    {children}
  </section>
);

const Empty = ({ children = 'No jobs in this period.' }) => (
  <div className="flex-1 flex items-center justify-center text-sm text-muted py-10">{children}</div>
);

const bucketLabel = (iso, granularity) => {
  const d = new Date(iso);
  return granularity === 'hour'
    ? d.toLocaleTimeString([], { hour: 'numeric' })
    : d.toLocaleDateString([], { month: 'short', day: 'numeric' });
};

const Overview = () => {
  const theme = useTheme();
  const [days, setDays] = useState(7);
  const [stats, setStats] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const headers = authHeaders();
        const [statsRes, metricsRes] = await Promise.all([
          axios.get(`${API_BASE}/stats`, { params: { days }, headers }),
          axios.get(`${API_BASE}/metrics`, { headers }),
        ]);
        if (cancelled) return;
        setStats(statsRes.data);
        setMetrics(metricsRes.data);
        setError(false);
      } catch (err) {
        if (handleAuthError(err)) return;
        console.error('Error fetching stats', err);
        if (!cancelled) setError(true);
      }
    };
    load();
    const interval = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [days]);

  const muted = cssColor('muted');
  const grid = cssColor('line');
  const palette = ['accent', 'success', 'warning', 'danger', 'muted'].map((c) => cssColor(c, 0.85));

  const totals = stats?.totals;
  const timeline = stats?.timeline || [];
  const hasJobs = totals?.jobs > 0;

  const axis = {
    x: { stacked: true, grid: { display: false }, border: { display: false }, ticks: { color: muted, maxRotation: 0, autoSkipPadding: 12 } },
    y: { stacked: true, beginAtZero: true, grid: { color: grid }, border: { display: false }, ticks: { color: muted, precision: 0 } },
  };

  const timelineData = {
    labels: timeline.map((p) => bucketLabel(p.bucket, stats.granularity)),
    datasets: [
      { label: 'Completed', data: timeline.map((p) => p.completed), backgroundColor: cssColor('success', 0.8), borderRadius: 3 },
      { label: 'Failed', data: timeline.map((p) => p.failed), backgroundColor: cssColor('danger', 0.8), borderRadius: 3 },
      { label: 'In progress', data: timeline.map((p) => p.in_progress), backgroundColor: cssColor('accent', 0.6), borderRadius: 3 },
    ],
  };

  const operations = stats?.operations || [];
  const operationsData = {
    labels: operations.map((o) => OPERATIONS[o.type]?.label || o.type),
    datasets: [{ data: operations.map((o) => o.count), backgroundColor: cssColor('accent', 0.75), borderRadius: 4, maxBarThickness: 18 }],
  };

  const formats = stats?.formats || [];
  const formatsData = {
    labels: formats.map((f) => f.format.toUpperCase()),
    datasets: [{ data: formats.map((f) => f.count), backgroundColor: palette, borderColor: cssColor('surface'), borderWidth: 2 }],
  };

  const legend = { position: 'bottom', labels: { color: muted, boxWidth: 8, boxHeight: 8, usePointStyle: true } };
  const queueNow = totals ? totals.pending + totals.processing : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Overview</h1>
          <p className="text-sm text-muted mt-1">
            {error ? 'Could not load stats. Retrying…' : 'Job volume, reliability and speed. Refreshes every 10 seconds.'}
          </p>
        </div>
        <div className="inline-flex p-0.5 rounded-lg bg-subtle border border-line" role="tablist" aria-label="Time range">
          {RANGES.map((r) => (
            <button
              key={r.days}
              role="tab"
              aria-selected={days === r.days}
              onClick={() => setDays(r.days)}
              className={clsx(
                'px-3 py-1 text-xs font-medium rounded-md transition-colors',
                days === r.days ? 'bg-surface text-fg shadow-sm' : 'text-muted hover:text-fg'
              )}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <Stat label="Jobs" value={totals?.jobs ?? '—'} hint={totals && `${totals.avg_steps_per_job} steps on average`} />
        <Stat
          label="Success rate"
          value={formatPercent(totals?.success_rate)}
          hint={totals && `${totals.completed} done · ${totals.failed} failed`}
          tone={totals?.success_rate != null && totals.success_rate < 0.95 ? 'text-warning' : undefined}
        />
        <Stat label="Median turnaround" value={formatDuration(stats?.turnaround_sec.p50)} hint="Upload to result" />
        <Stat label="p95 turnaround" value={formatDuration(stats?.turnaround_sec.p95)} hint={`Average ${formatDuration(stats?.turnaround_sec.avg)}`} />
        <Stat label="In queue now" value={queueNow ?? '—'} hint={totals && `${totals.processing} processing`} />
        <Stat
          label="Retries"
          value={totals?.retries ?? '—'}
          hint={metrics && `${metrics.rate_limit_hits} rate-limited uploads all time`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Panel title={`Jobs per ${stats?.granularity || 'day'}`} className="lg:col-span-2">
          <div className="h-64">
            {stats && <Bar key={`t-${theme}`} data={timelineData} options={{ responsive: true, maintainAspectRatio: false, scales: axis, plugins: { legend } }} />}
          </div>
        </Panel>

        <Panel title="Most used steps">
          {operations.length ? (
            <div className="h-64">
              <Bar
                key={`o-${theme}`}
                data={operationsData}
                options={{
                  indexAxis: 'y',
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: { legend: { display: false } },
                  scales: {
                    x: { beginAtZero: true, grid: { color: grid }, border: { display: false }, ticks: { color: muted, precision: 0 } },
                    y: { grid: { display: false }, border: { display: false }, ticks: { color: muted } },
                  },
                }}
              />
            </div>
          ) : <Empty />}
        </Panel>

        <Panel title="Input formats">
          {hasJobs ? (
            <div className="h-56">
              <Doughnut key={`f-${theme}`} data={formatsData} options={{ responsive: true, maintainAspectRatio: false, cutout: '68%', plugins: { legend } }} />
            </div>
          ) : <Empty />}
        </Panel>

        <Panel title="Top failure reasons" className="lg:col-span-2" aside={totals?.failed ? <span className="text-xs text-danger">{totals.failed} failed</span> : null}>
          {stats?.top_errors.length ? (
            <ul className="divide-y divide-line -my-2">
              {stats.top_errors.map((e) => (
                <li key={e.message} className="flex items-start justify-between gap-4 py-2.5 text-sm">
                  <span className="font-mono text-xs text-fg/80 break-all">{e.message}</span>
                  <span className="shrink-0 tabular-nums text-muted">{e.count}×</span>
                </li>
              ))}
            </ul>
          ) : <Empty>{hasJobs ? 'No failures in this period.' : undefined}</Empty>}
        </Panel>
      </div>

      {stats?.truncated && (
        <p className="text-xs text-muted">Showing the most recent 50,000 jobs in this period.</p>
      )}
    </div>
  );
};

export default Overview;
