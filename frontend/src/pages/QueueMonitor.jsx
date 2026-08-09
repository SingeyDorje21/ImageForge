import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Layers, Play, RefreshCw, X, Download } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const QueueMonitor = () => {
  const [jobs, setJobs] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  
  // Upload form state
  const [file, setFile] = useState(null);
  const [opType, setOpType] = useState('resize');
  const [width, setWidth] = useState(400);
  const [height, setHeight] = useState(400);
  const [format, setFormat] = useState('webp');
  const [uploading, setUploading] = useState(false);

  const fetchJobs = async () => {
    try {
      const res = await axios.get(`${API_BASE}/jobs?limit=50`);
      setJobs(res.data);
    } catch (err) {
      console.error('Error fetching jobs', err);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    
    let ops = [];
    if (opType === 'resize') {
      ops.push({ type: 'resize', width: parseInt(width), height: parseInt(height) });
    } else {
      ops.push({ type: 'format_convert', target_format: format });
    }
    formData.append('operations', JSON.stringify(ops));

    try {
      await axios.post(`${API_BASE}/jobs`, formData);
      setShowUploadModal(false);
      setFile(null);
      fetchJobs();
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const StatusBadge = ({ status }) => {
    const map = {
      pending: { bg: 'bg-panel border-textMuted', text: 'text-textMuted', label: 'PENDING' },
      processing: { bg: 'bg-blue-500/10 border-blue-500/30', text: 'text-primary', label: 'PROCESSING' },
      completed: { bg: 'bg-green-500/10 border-green-500/30', text: 'text-success', label: 'SUCCESS' },
      failed: { bg: 'bg-red-500/10 border-red-500/30', text: 'text-danger', label: 'FAILED' }
    };
    const style = map[status] || map.pending;
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-bold border ${style.bg} ${style.text} flex items-center gap-2 w-fit`}>
        {status === 'processing' && <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>}
        {style.label}
      </span>
    );
  };

  const handleJobClick = (job) => {
    if (job.status === 'completed' && job.result_path) {
      setSelectedJob(job);
    }
  };

  return (
    <div className="h-full flex flex-col relative">
      <header className="flex justify-between items-center mb-8 border-b border-border pb-4">
        <h2 className="text-xl font-bold text-white">Queue Monitor</h2>
        <button 
          onClick={() => setShowUploadModal(true)}
          className="bg-primary hover:bg-blue-400 text-slate-900 font-bold py-2 px-6 rounded transition-colors flex items-center gap-2 shadow-[0_0_15px_rgba(56,189,248,0.3)]"
        >
          <Play size={16} /> Upload Task
        </button>
      </header>

      {/* Top Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="glass-panel p-6 flex flex-col justify-center">
          <h3 className="text-xs font-bold text-textMuted uppercase tracking-wider mb-2 flex items-center justify-between">
            Total Displayed <Layers size={16}/>
          </h3>
          <span className="text-4xl font-bold text-white">{jobs.length}</span>
        </div>
        <div className="glass-panel p-6 flex flex-col justify-center border-l-2 border-primary">
          <h3 className="text-xs font-bold text-textMuted uppercase tracking-wider mb-2">Pending Execution</h3>
          <span className="text-4xl font-bold text-white">{jobs.filter(j => j.status === 'pending').length}</span>
        </div>
        <div className="glass-panel p-6 flex flex-col justify-center border-l-2 border-success">
          <h3 className="text-xs font-bold text-textMuted uppercase tracking-wider mb-2 flex items-center justify-between">
            Actively Processing <RefreshCw size={16} className="text-success animate-spin-slow"/>
          </h3>
          <span className="text-4xl font-bold text-white">{jobs.filter(j => j.status === 'processing').length}</span>
        </div>
      </div>

      {/* Table */}
      <div className="glass-panel flex-1 overflow-hidden flex flex-col">
        <div className="p-4 border-b border-border">
          <h3 className="text-xs font-bold text-textMuted uppercase tracking-wider">Top 50 Recent Jobs</h3>
        </div>
        <div className="flex-1 overflow-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-white/5 text-textMuted sticky top-0">
              <tr>
                <th className="p-4 font-semibold uppercase tracking-wider text-xs">Job ID</th>
                <th className="p-4 font-semibold uppercase tracking-wider text-xs">Status</th>
                <th className="p-4 font-semibold uppercase tracking-wider text-xs">File Name</th>
                <th className="p-4 font-semibold uppercase tracking-wider text-xs">Operations</th>
                <th className="p-4 font-semibold uppercase tracking-wider text-xs">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {jobs.map(job => (
                <tr 
                  key={job.job_id} 
                  className={`hover:bg-white/5 transition-colors ${job.status === 'completed' ? 'cursor-pointer hover:bg-success/10' : ''}`}
                  onClick={() => handleJobClick(job)}
                >
                  <td className="p-4 font-mono text-textMuted">{job.job_id.substring(0, 8).toUpperCase()}</td>
                  <td className="p-4"><StatusBadge status={job.status} /></td>
                  <td className="p-4 text-white truncate max-w-xs">{job.original_filename}</td>
                  <td className="p-4 text-textMuted">
                    {job.operations.map((o, i) => (
                      <span key={i} className="bg-white/5 px-2 py-1 rounded text-xs mr-2">{o.type}</span>
                    ))}
                  </td>
                  <td className="p-4 text-textMuted">
                    {new Date(job.created_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-md p-6 relative">
            <button onClick={() => setShowUploadModal(false)} className="absolute top-4 right-4 text-textMuted hover:text-white">
              <X size={24} />
            </button>
            <h2 className="text-xl font-bold mb-6 text-white">Upload New Task</h2>
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-xs text-textMuted uppercase mb-1">Image File</label>
                <input type="file" onChange={(e) => setFile(e.target.files[0])} accept="image/*" required className="w-full text-sm text-textMuted file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 cursor-pointer" />
              </div>
              <div>
                <label className="block text-xs text-textMuted uppercase mb-1">Operation</label>
                <select value={opType} onChange={e => setOpType(e.target.value)} className="w-full bg-white/5 border border-border rounded px-3 py-2 text-white">
                  <option value="resize">Resize</option>
                  <option value="format_convert">Format Convert</option>
                </select>
              </div>
              {opType === 'resize' ? (
                <div className="flex gap-4">
                  <div className="flex-1">
                    <label className="block text-xs text-textMuted uppercase mb-1">Width</label>
                    <input type="number" value={width} onChange={e => setWidth(e.target.value)} className="w-full bg-white/5 border border-border rounded px-3 py-2 text-white" />
                  </div>
                  <div className="flex-1">
                    <label className="block text-xs text-textMuted uppercase mb-1">Height</label>
                    <input type="number" value={height} onChange={e => setHeight(e.target.value)} className="w-full bg-white/5 border border-border rounded px-3 py-2 text-white" />
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-xs text-textMuted uppercase mb-1">Target Format</label>
                  <select value={format} onChange={e => setFormat(e.target.value)} className="w-full bg-white/5 border border-border rounded px-3 py-2 text-white">
                    <option value="webp">WebP</option>
                    <option value="png">PNG</option>
                    <option value="jpg">JPG</option>
                  </select>
                </div>
              )}
              <div className="pt-4">
                <button type="submit" disabled={uploading || !file} className="w-full bg-primary hover:bg-blue-400 text-slate-900 font-bold py-3 rounded transition-colors disabled:opacity-50">
                  {uploading ? 'Submitting...' : 'Queue Task'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview/Download Modal */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm" onClick={() => setSelectedJob(null)}>
          <div className="glass-panel w-full max-w-lg p-6 relative text-center flex flex-col items-center" onClick={e => e.stopPropagation()}>
            <button onClick={() => setSelectedJob(null)} className="absolute top-4 right-4 text-textMuted hover:text-white">
              <X size={24} />
            </button>
            <h2 className="text-xl font-bold mb-2 text-white">Job Completed</h2>
            <p className="text-sm text-textMuted mb-6 font-mono">{selectedJob.job_id}</p>
            
            <div className="w-full aspect-video bg-black/50 rounded-lg flex items-center justify-center mb-6 overflow-hidden border border-border relative group">
              <img src={`${API_BASE}/storage/results/${selectedJob.result_path.split(/[\\/]/).pop()}`} alt="Result" className="max-w-full max-h-full object-contain" />
              <div className="absolute inset-0 bg-black/60 flex flex-col items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                 <span className="text-white text-sm font-bold mb-2">Processed Image</span>
                 <p className="text-xs font-mono text-primary break-all">{selectedJob.result_path.split(/[\\/]/).pop()}</p>
              </div>
            </div>

            <a href={`${API_BASE}/storage/results/${selectedJob.result_path.split(/[\\/]/).pop()}`} download target="_blank" rel="noreferrer" className="w-full bg-success hover:bg-green-400 text-slate-900 font-bold py-3 rounded transition-colors flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(74,222,128,0.3)]">
              <Download size={20} /> Download Image
            </a>
          </div>
        </div>
      )}
    </div>
  );
};

export default QueueMonitor;
