import React, { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { ReactCompareSlider, ReactCompareSliderImage } from 'react-compare-slider';
import { AlertCircle, Download, RotateCcw } from 'lucide-react';
import { formatBytes, resultUrl } from '../lib/jobs';

const STAGES = { pending: 'Waiting in queue…', processing: 'Processing…' };

const Progress = ({ status }) => (
  <div className="card p-6 space-y-4">
    <p className="text-sm font-medium">{STAGES[status] || 'Starting…'}</p>
    <div className="h-1 rounded-full bg-subtle overflow-hidden">
      <motion.div
        className="h-full bg-accent rounded-full"
        initial={{ width: '5%' }}
        animate={{ width: status === 'processing' ? '70%' : '30%' }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      />
    </div>
  </div>
);

// Shows progress while a job runs, then a before/after slider and a download link.
const JobResult = ({ job, file, previewUrl, onReset }) => {
  const [resultSize, setResultSize] = useState(null);
  const url = job.status === 'completed' ? resultUrl(job) : null;

  useEffect(() => {
    if (!url) return undefined;
    let cancelled = false;
    // Best effort: the size is a nice-to-have, so a blocked request just hides it.
    fetch(url)
      .then((res) => (res.ok ? res.blob() : null))
      .then((blob) => !cancelled && blob && setResultSize(blob.size))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [url]);

  if (job.status === 'failed') {
    return (
      <div className="card p-6 space-y-4">
        <div className="flex items-start gap-3">
          <AlertCircle size={18} className="text-danger mt-0.5 shrink-0" />
          <div>
            <p className="text-sm font-medium">That didn't work</p>
            <p className="text-sm text-muted mt-1">{job.error_message || 'Something went wrong while processing the image.'}</p>
          </div>
        </div>
        <button type="button" onClick={onReset} className="btn-outline">
          <RotateCcw size={14} /> Try again
        </button>
      </div>
    );
  }

  if (!url) return <Progress status={job.status} />;

  const name = job.result_path?.split(/[\\/]/).pop() || 'imageforge-result';
  const saved = resultSize != null && file ? Math.round((1 - resultSize / file.size) * 100) : null;

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <div className="card overflow-hidden">
        <ReactCompareSlider
          className="h-80 bg-subtle"
          itemOne={<ReactCompareSliderImage src={previewUrl} alt="Original" style={{ objectFit: 'contain' }} />}
          itemTwo={<ReactCompareSliderImage src={url} alt="Result" style={{ objectFit: 'contain' }} />}
        />
        <div className="grid grid-cols-2 divide-x divide-line border-t border-line text-sm">
          <div className="px-4 py-3">
            <p className="label">Before</p>
            <p className="tabular-nums mt-0.5">{formatBytes(file?.size)}</p>
          </div>
          <div className="px-4 py-3">
            <p className="label">After</p>
            <p className="tabular-nums mt-0.5">
              {resultSize != null ? formatBytes(resultSize) : '—'}
              {saved != null && saved > 0 && <span className="text-success ml-2">−{saved}%</span>}
            </p>
          </div>
        </div>
      </div>
      <div className="flex flex-col sm:flex-row gap-2">
        <a href={url} download={name} target="_blank" rel="noreferrer" className="btn-primary flex-1 py-2.5">
          <Download size={16} /> Download
        </a>
        <button type="button" onClick={onReset} className="btn-outline flex-1 py-2.5">
          <RotateCcw size={14} /> Process another
        </button>
      </div>
    </motion.div>
  );
};

export default JobResult;
