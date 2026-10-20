import React, { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { AnimatePresence, motion } from 'motion/react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { ReactCompareSlider, ReactCompareSliderImage } from 'react-compare-slider';
import { AlertCircle, ArrowRight, Download, History, Loader2, RotateCcw, X } from 'lucide-react';
import { API_BASE } from '../config';
import ImageDrop, { MAX_FILE_MB } from '../components/ImageDrop';
import OperationBuilder from '../components/OperationBuilder';
import ThemeToggle from '../components/ThemeToggle';
import { OPERATIONS, PRESETS, newStep, presetSteps, toPayload } from '../lib/operations';
import { formatBytes, isActive, resultUrl, useJobPolling } from '../lib/jobs';

const CANVAS_HEIGHT = 'h-[340px] sm:h-[460px]';

// Best effort: the result size is a nice-to-have, so a blocked request just hides it.
const useRemoteSize = (url) => {
  const [size, setSize] = useState(null);
  useEffect(() => {
    setSize(null);
    if (!url) return undefined;
    let cancelled = false;
    fetch(url)
      .then((res) => (res.ok ? res.blob() : null))
      .then((blob) => !cancelled && blob && setSize(blob.size))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [url]);
  return size;
};

const MetaBar = ({ children }) => (
  <div className="flex items-center justify-between gap-4 px-4 py-2.5 border-t border-line text-sm min-h-[44px]">{children}</div>
);

// The left-hand canvas: preview, progress, before/after or error for the current image.
const Canvas = ({ file, previewUrl, job, dimensions, onDimensions, onClear }) => {
  const url = job?.status === 'completed' ? resultUrl(job) : null;
  const resultSize = useRemoteSize(url);
  const running = job && isActive(job.status);
  const saved = resultSize != null ? Math.round((1 - resultSize / file.size) * 100) : null;
  const name = job?.result_path?.split(/[\\/]/).pop() || 'imageforge-result';

  return (
    <div className="card overflow-hidden">
      <div className={clsx('relative bg-subtle', CANVAS_HEIGHT)}>
        {url ? (
          <ReactCompareSlider
            className="h-full"
            itemOne={<ReactCompareSliderImage src={previewUrl} alt="Original" style={{ objectFit: 'contain' }} />}
            itemTwo={<ReactCompareSliderImage src={url} alt="Result" style={{ objectFit: 'contain' }} />}
          />
        ) : (
          <div className="h-full flex items-center justify-center p-4">
            <img
              src={previewUrl}
              alt="Selected"
              className={clsx('max-h-full max-w-full object-contain transition-opacity', running && 'opacity-40')}
              onLoad={(e) => onDimensions([e.currentTarget.naturalWidth, e.currentTarget.naturalHeight])}
            />
          </div>
        )}

        {url && (
          <>
            <span className="absolute z-10 top-3 left-3 px-2 py-0.5 rounded-md bg-black/50 text-white text-[11px] backdrop-blur">Before</span>
            <span className="absolute z-10 top-3 right-3 px-2 py-0.5 rounded-md bg-black/50 text-white text-[11px] backdrop-blur">After</span>
          </>
        )}

        {!url && !running && (
          <button
            type="button"
            onClick={onClear}
            aria-label="Remove image"
            className="absolute top-3 right-3 h-8 w-8 flex items-center justify-center rounded-full bg-surface/90 border border-line text-muted hover:text-fg backdrop-blur"
          >
            <X size={14} />
          </button>
        )}

        <AnimatePresence>
          {running && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 flex items-center justify-center"
            >
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-surface border border-line shadow-sm text-sm">
                <Loader2 size={14} className="animate-spin text-accent" />
                {job.status === 'processing' ? 'Processing…' : 'Waiting in queue…'}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {job?.status === 'failed' && (
        <div className="flex items-start gap-2 px-4 py-3 border-t border-line bg-danger/5 text-sm">
          <AlertCircle size={16} className="text-danger mt-0.5 shrink-0" />
          <span>{job.error_message || 'Something went wrong while processing the image.'}</span>
        </div>
      )}

      <MetaBar>
        {url ? (
          <>
            <span className="text-muted tabular-nums truncate">
              {formatBytes(file.size)} → <span className="text-fg">{resultSize != null ? formatBytes(resultSize) : '…'}</span>
              {saved != null && saved > 0 && <span className="text-success ml-2">−{saved}%</span>}
            </span>
            <a href={url} download={name} target="_blank" rel="noreferrer" className="btn-primary py-1.5 shrink-0">
              <Download size={14} /> Download
            </a>
          </>
        ) : (
          <>
            <span className="truncate font-medium">{file.name}</span>
            <span className="shrink-0 text-muted tabular-nums">
              {dimensions && `${dimensions[0]} × ${dimensions[1]} · `}{formatBytes(file.size)}
            </span>
          </>
        )}
      </MetaBar>
    </div>
  );
};

const SessionHistory = ({ items }) => (
  <section className="space-y-2">
    <h2 className="flex items-center gap-1.5 text-xs font-medium text-muted">
      <History size={12} /> This session
    </h2>
    <ul className="card divide-y divide-line overflow-hidden">
      {items.map((item) => (
        <li key={item.id} className="flex items-center gap-3 px-3 py-2">
          <img src={item.url} alt="" className="h-10 w-10 rounded-md object-cover bg-subtle shrink-0" />
          <div className="min-w-0 flex-1">
            <p className="text-sm truncate">{item.name}</p>
            <p className="text-xs text-muted truncate">{item.steps}</p>
          </div>
          <span className="text-xs text-muted tabular-nums hidden sm:block">{item.time}</span>
          <a href={item.url} download target="_blank" rel="noreferrer" className="btn-ghost h-8 w-8 p-0 shrink-0" aria-label={`Download ${item.name}`}>
            <Download size={14} />
          </a>
        </li>
      ))}
    </ul>
  </section>
);

const LandingPage = () => {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [dimensions, setDimensions] = useState(null);
  const [steps, setSteps] = useState(() => [newStep('resize')]);
  const [uploading, setUploading] = useState(false);
  const [submittedJob, setSubmittedJob] = useState(null);
  const [history, setHistory] = useState([]);
  const job = useJobPolling(submittedJob);
  const recorded = useRef(new Set());

  useEffect(() => {
    if (!file) return undefined;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    setDimensions(null);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  // Remember each finished result for this visit so earlier versions stay downloadable.
  useEffect(() => {
    if (job?.status !== 'completed' || recorded.current.has(job.job_id)) return;
    recorded.current.add(job.job_id);
    setHistory((h) => [
      {
        id: job.job_id,
        name: file.name,
        url: resultUrl(job),
        steps: (job.operations || []).map((o) => OPERATIONS[o.type]?.label || o.type).join(' → '),
        time: new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
      },
      ...h,
    ]);
  }, [job, file]);

  const chooseFile = useCallback((f) => {
    setFile(f);
    setSubmittedJob(null);
  }, []);

  const clearFile = () => {
    setFile(null);
    setPreviewUrl(null);
    setSubmittedJob(null);
  };

  const running = Boolean(job && isActive(job.status));
  const finished = job && !running;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || steps.length === 0) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('operations', JSON.stringify(toPayload(steps)));

    try {
      const res = await axios.post(`${API_BASE}/jobs`, formData);
      setSubmittedJob({ job_id: res.data.job_id, status: 'pending' });
    } catch (err) {
      const detail = err.response?.data?.detail;
      toast.error(typeof detail === 'string' ? detail : 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-20 border-b border-line bg-background/80 backdrop-blur">
        <div className="max-w-6xl mx-auto px-5 h-14 flex items-center justify-between gap-4">
          <a href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <img src="/favicon.svg" alt="" className="h-6 w-6" />
            ImageForge
          </a>
          <div className="flex items-center gap-4">
            <span className="hidden sm:block text-xs text-muted">Free image editing · no account needed</span>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <form onSubmit={handleSubmit} className="flex-1 max-w-6xl w-full mx-auto px-5 py-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px] items-start">
        <div className="space-y-6 min-w-0">
          {file && previewUrl ? (
            <Canvas
              file={file}
              previewUrl={previewUrl}
              job={job}
              dimensions={dimensions}
              onDimensions={setDimensions}
              onClear={clearFile}
            />
          ) : (
            <ImageDrop file={null} onFile={chooseFile} onReject={toast.error} className={CANVAS_HEIGHT} />
          )}
          {history.length > 0 && <SessionHistory items={history} />}
        </div>

        <aside className="card lg:sticky lg:top-20 flex flex-col">
          <div className="p-4 border-b border-line">
            <h1 className="text-sm font-semibold">Steps</h1>
            <p className="text-xs text-muted mt-0.5">Applied top to bottom. Drag to reorder, click to edit.</p>
          </div>

          <div className="p-4 space-y-4">
            <div>
              <p className="label mb-2">Presets</p>
              <div className="flex flex-wrap gap-1.5">
                {PRESETS.map((preset) => (
                  <button
                    key={preset.name}
                    type="button"
                    onClick={() => setSteps(presetSteps(preset))}
                    className="px-2.5 py-1 rounded-md text-xs bg-subtle text-fg hover:bg-accent hover:text-accent-fg transition-colors"
                  >
                    {preset.name}
                  </button>
                ))}
              </div>
            </div>
            <OperationBuilder steps={steps} onChange={setSteps} />
          </div>

          <div className="p-4 border-t border-line space-y-2 mt-auto">
            <button type="submit" disabled={uploading || running || !file || steps.length === 0} className="btn-primary w-full py-2.5">
              {uploading || running ? <Loader2 size={16} className="animate-spin" /> : finished ? <RotateCcw size={16} /> : <ArrowRight size={16} />}
              {uploading ? 'Uploading…' : running ? 'Processing…' : finished ? 'Run again with these steps' : 'Process image'}
            </button>
            <p className="text-[11px] text-muted text-center">
              {file ? 'Tweak the steps and run again as often as you like.' : `Add an image to start. JPG, PNG or WebP up to ${MAX_FILE_MB} MB.`}
            </p>
          </div>
        </aside>
      </form>
    </div>
  );
};

export default LandingPage;
