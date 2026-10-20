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
