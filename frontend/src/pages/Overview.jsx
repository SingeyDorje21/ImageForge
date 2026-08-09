import React, { useEffect, useState } from 'react';
import axios from 'axios';
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
import { Bell, History, User } from 'lucide-react';

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend);
ChartJS.defaults.color = '#94a3b8';
ChartJS.defaults.font.family = 'Inter';

const API_BASE = 'http://localhost:8000';

const StatCard = ({ title, value, subtext, colorClass }) => (
  <div className="glass-panel p-6 border-t-2" style={{ borderTopColor: colorClass }}>
    <h3 className="text-xs font-bold text-textMuted uppercase tracking-wider mb-2">{title}</h3>
    <div className="flex items-baseline gap-4">
      <span className="text-3xl font-bold" style={{ color: colorClass }}>{value}</span>
      {subtext && <span className="text-sm font-medium" style={{ color: colorClass }}>{subtext}</span>}
    </div>
  </div>
);

const Overview = () => {
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
        const res = await axios.get(`${API_BASE}/metrics`);
        setMetrics(res.data);
      } catch (err) {
        console.error('Error fetching metrics', err);
      }
    };
    
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 2000);
    return () => clearInterval(interval);
  }, []);

  const chartData = {
    labels: ['Queued', 'Completed', 'Failed', 'Rate Limited'],
    datasets: [
      {
        label: 'Tasks',
        data: [metrics.jobs_queued, metrics.jobs_completed, metrics.jobs_failed, metrics.rate_limit_hits],
        backgroundColor: ['rgba(56, 189, 248, 0.8)', 'rgba(74, 222, 128, 0.8)', 'rgba(248, 113, 113, 0.8)', 'rgba(251, 191, 36, 0.8)'],
        borderRadius: 4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' } },
      x: { grid: { display: false } },
    },
    plugins: { legend: { display: false } },
  };

  return (
    <div className="h-full flex flex-col">
      {/* Top Header */}
      <header className="flex justify-between items-center mb-8 border-b border-border pb-4">
        <h2 className="text-xl font-bold text-white">Distributed Image Processor</h2>
        <div className="flex items-center gap-4 text-textMuted">
          <Bell size={20} className="hover:text-white cursor-pointer" />
          <History size={20} className="hover:text-white cursor-pointer" />
          <User size={20} className="hover:text-white cursor-pointer" />
        </div>
      </header>

      {/* Title */}
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-2xl font-bold text-white mb-1">System Overview</h1>
          <p className="text-sm text-textMuted">Real-time health and throughput metrics across all distributed nodes.</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <StatCard title="Total Queued" value={metrics.jobs_queued} colorClass="#38bdf8" />
        <StatCard title="Avg Processing Time" value={`${metrics.avg_processing_time_sec}s`} colorClass="#fbbf24" />
        <StatCard title="Completed Jobs" value={metrics.jobs_completed} colorClass="#4ade80" />
        <StatCard title="Failed Jobs" value={metrics.jobs_failed} colorClass="#f87171" />
      </div>

      {/* Chart Area */}
      <div className="glass-panel flex-1 min-h-[300px] p-6 flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xs font-bold text-textMuted uppercase tracking-wider">Real-time Throughput</h3>
        </div>
        <div className="flex-1 relative">
          <Bar data={chartData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
};

export default Overview;
