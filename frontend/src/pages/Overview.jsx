import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { authHeaders, handleAuthError } from '../auth';
import { API_BASE } from '../config';
import { useTheme } from '../lib/theme';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);
ChartJS.defaults.font.family = 'Inter';

// Reads a theme color token from index.css so the chart follows light and dark mode.
const cssColor = (name, alpha = 1) => {
  const rgb = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim().split(/\s+/).join(', ');
  return `rgba(${rgb}, ${alpha})`;
};

const StatCard = ({ title, value, tone }) => (
  <div className="card p-5">
    <p className="label">{title}</p>
    <p className={`text-2xl font-semibold tabular-nums mt-2 ${tone || ''}`}>{value}</p>
  </div>
);

const Overview = () => {
  const theme = useTheme();
  const [metrics, setMetrics] = useState({
    jobs_queued: 0,
    jobs_completed: 0,
    jobs_failed: 0,
    rate_limit_hits: 0,
    avg_processing_time_sec: 0,
  });

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const res = await axios.get(`${API_BASE}/metrics`, { headers: authHeaders() });
        setMetrics(res.data);
      } catch (err) {
        if (handleAuthError(err)) return;
        console.error('Error fetching metrics', err);
      }
    };
    
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 2000);
    return () => clearInterval(interval);
  }, []);

  const chartData = {
    labels: ['Queued', 'Completed', 'Failed', 'Rate limited'],
    datasets: [
      {
        label: 'Jobs',
        data: [metrics.jobs_queued, metrics.jobs_completed, metrics.jobs_failed, metrics.rate_limit_hits],
        backgroundColor: [cssColor('accent', 0.85), cssColor('success', 0.85), cssColor('danger', 0.85), cssColor('warning', 0.85)],
        borderRadius: 6,
        maxBarThickness: 56,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    color: cssColor('muted'),
    scales: {
      y: { beginAtZero: true, grid: { color: cssColor('line') }, border: { display: false }, ticks: { color: cssColor('muted'), precision: 0 } },
      x: { grid: { display: false }, border: { display: false }, ticks: { color: cssColor('muted') } },
    },
    plugins: { legend: { display: false } },
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Overview</h1>
        <p className="text-sm text-muted mt-1">Live job throughput and health.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Queued" value={metrics.jobs_queued} />
        <StatCard title="Avg processing time" value={`${metrics.avg_processing_time_sec}s`} />
        <StatCard title="Completed" value={metrics.jobs_completed} tone="text-success" />
        <StatCard title="Failed" value={metrics.jobs_failed} tone="text-danger" />
      </div>

      <div className="card p-5">
        <p className="label mb-4">Jobs by status</p>
        <div className="h-72">
          <Bar key={theme} data={chartData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
};

export default Overview;
