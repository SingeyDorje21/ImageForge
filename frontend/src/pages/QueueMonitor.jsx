import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { AnimatePresence, motion } from 'motion/react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { Download, Plus, X } from 'lucide-react';
import { authHeaders, handleAuthError } from '../auth';
import { API_BASE } from '../config';
import ImageDrop from '../components/ImageDrop';
import OperationBuilder from '../components/OperationBuilder';
import { OPERATIONS, newStep, toPayload } from '../lib/operations';
import { resultUrl } from '../lib/jobs';

const STATUS = {
  pending: { label: 'Pending', dot: 'bg-muted', text: 'text-muted' },
  processing: { label: 'Processing', dot: 'bg-accent animate-pulse', text: 'text-accent' },
  completed: { label: 'Done', dot: 'bg-success', text: 'text-success' },
  failed: { label: 'Failed', dot: 'bg-danger', text: 'text-danger' },
};

const StatusBadge = ({ status }) => {
  const style = STATUS[status] || STATUS.pending;
  return (
    <span className={clsx('inline-flex items-center gap-1.5 text-xs font-medium', style.text)}>
      <span className={clsx('h-1.5 w-1.5 rounded-full', style.dot)} />
      {style.label}
    </span>
  );
};

const Modal = ({ onClose, children, title }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm"
    onClick={onClose}
  >
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      className="card w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto shadow-xl"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-semibold">{title}</h2>
        <button onClick={onClose} aria-label="Close" className="btn-ghost h-8 w-8 p-0 rounded-full">
          <X size={16} />
        </button>
      </div>
      {children}
    </motion.div>
  </motion.div>
);

const QueueMonitor = () => {
  const [jobs, setJobs] = useState([]);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  
  // Upload form state
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [steps, setSteps] = useState(() => [newStep('resize')]);
  const [uploading, setUploading] = useState(false);

  const fetchJobs = async () => {
    try {
      const res = await axios.get(`${API_BASE}/jobs?limit=50`, { headers: authHeaders() });
      setJobs(res.data);
    } catch (err) {
      if (handleAuthError(err)) return;
      console.error('Error fetching jobs', err);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (!file) return undefined;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || steps.length === 0) return;
    
    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('operations', JSON.stringify(toPayload(steps)));

    try {
      await axios.post(`${API_BASE}/jobs`, formData);
      setShowUploadModal(false);
      setFile(null);
      toast.success('Job queued');
      fetchJobs();
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const counts = {
    pending: jobs.filter((j) => j.status === 'pending').length,
    processing: jobs.filter((j) => j.status === 'processing').length,
  };

  return (
    <div className="space-y-8">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Jobs</h1>
          <p className="text-sm text-muted mt-1">
            {jobs.length} recent · {counts.pending} pending · {counts.processing} processing
          </p>
        </div>
        <button onClick={() => setShowUploadModal(true)} className="btn-primary">
          <Plus size={16} /> New job
        </button>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-muted border-b border-line">
              <tr>
                <th className="px-5 py-3 font-medium text-xs">Job</th>
                <th className="px-5 py-3 font-medium text-xs">Status</th>
                <th className="px-5 py-3 font-medium text-xs">File</th>
                <th className="px-5 py-3 font-medium text-xs">Steps</th>
                <th className="px-5 py-3 font-medium text-xs text-right">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {jobs.length === 0 && (
                <tr><td colSpan={5} className="px-5 py-12 text-center text-muted">No jobs yet.</td></tr>
              )}
              {jobs.map((job) => {
                const clickable = job.status === 'completed' && resultUrl(job);
                return (
                  <tr
                    key={job.job_id}
                    className={clsx('transition-colors', clickable && 'cursor-pointer hover:bg-subtle')}
                    onClick={() => clickable && setSelectedJob(job)}
                  >
                    <td className="px-5 py-3 font-mono text-xs text-muted">{job.job_id.substring(0, 8)}</td>
                    <td className="px-5 py-3"><StatusBadge status={job.status} /></td>
                    <td className="px-5 py-3 truncate max-w-xs">{job.original_filename}</td>
                    <td className="px-5 py-3">
                      <div className="flex flex-wrap gap-1">
                        {job.operations.map((o, i) => (
                          <span key={i} className="bg-subtle px-2 py-0.5 rounded-md text-xs text-muted">
                            {OPERATIONS[o.type]?.label || o.type}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-5 py-3 text-right text-muted tabular-nums">
                      {new Date(job.created_at).toLocaleTimeString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {showUploadModal && (
          <Modal title="New job" onClose={() => setShowUploadModal(false)}>
            <form onSubmit={handleUpload} className="space-y-5">
              <ImageDrop
                file={file}
                previewUrl={previewUrl}
                onFile={setFile}
                onClear={() => { setFile(null); setPreviewUrl(null); }}
                onReject={toast.error}
              />
              <OperationBuilder steps={steps} onChange={setSteps} />
              <button type="submit" disabled={uploading || !file || steps.length === 0} className="btn-primary w-full py-2.5">
                {uploading ? 'Submitting…' : 'Queue job'}
              </button>
            </form>
          </Modal>
        )}

        {selectedJob && (
          <Modal title={selectedJob.original_filename} onClose={() => setSelectedJob(null)}>
            <div className="rounded-xl bg-subtle flex items-center justify-center aspect-video overflow-hidden mb-4">
              <img src={resultUrl(selectedJob)} alt="Result" className="max-w-full max-h-full object-contain" />
            </div>
            <p className="text-xs font-mono text-muted mb-4 break-all">{selectedJob.job_id}</p>
            <a href={resultUrl(selectedJob)} download target="_blank" rel="noreferrer" className="btn-primary w-full py-2.5">
              <Download size={16} /> Download
            </a>
          </Modal>
        )}
      </AnimatePresence>
    </div>
  );
};

export default QueueMonitor;
