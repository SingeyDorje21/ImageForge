import { useEffect, useState } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';

// Prefer the API's signed result URL; fall back to the local storage route.
export const resultUrl = (job) => {
  if (job.result_url) return job.result_url;
  if (!job.result_path) return null;
  return `${API_BASE}/storage/results/${job.result_path.split(/[\\/]/).pop()}`;
};

export const formatBytes = (bytes) => {
  if (bytes == null) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
};

export const isActive = (status) => status === 'pending' || status === 'processing';

// Polls a job until it finishes. Returns the latest job record (null before one is set).
export const useJobPolling = (initialJob) => {
  const [job, setJob] = useState(initialJob);

  useEffect(() => setJob(initialJob), [initialJob]);

  const jobId = job?.job_id;
  const active = job && isActive(job.status);

  useEffect(() => {
    if (!active) return undefined;
    let cancelled = false;
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/jobs/${jobId}`);
        if (!cancelled) setJob(res.data);
      } catch (err) {
        console.error(err);
      }
    }, 1000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [jobId, active]);

  return job;
};
