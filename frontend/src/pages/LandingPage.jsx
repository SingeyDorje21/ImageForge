import React, { useCallback, useEffect, useState } from 'react';
import axios from 'axios';
import { AnimatePresence, motion } from 'motion/react';
import { toast } from 'sonner';
import { ArrowRight, Loader2 } from 'lucide-react';
import { API_BASE } from '../config';
import ImageDrop from '../components/ImageDrop';
import JobResult from '../components/JobResult';
import OperationBuilder from '../components/OperationBuilder';
import ThemeToggle from '../components/ThemeToggle';
import { PRESETS, newStep, presetSteps, toPayload } from '../lib/operations';
import { useJobPolling } from '../lib/jobs';

const fade = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.2 },
};

const LandingPage = () => {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [steps, setSteps] = useState(() => [newStep('resize')]);
  const [uploading, setUploading] = useState(false);
  const [submittedJob, setSubmittedJob] = useState(null);
  const job = useJobPolling(submittedJob);

  useEffect(() => {
    if (!file) return undefined;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const chooseFile = useCallback((f) => {
    setFile(f);
    setSubmittedJob(null);
  }, []);

  const clearFile = () => {
    setFile(null);
    setPreviewUrl(null);
  };

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

  const showResult = Boolean(job);

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex items-center justify-between max-w-2xl w-full mx-auto px-5 pt-6">
        <a href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <img src="/favicon.svg" alt="" className="h-6 w-6" />
          ImageForge
        </a>
        <ThemeToggle />
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-5 pt-14 pb-16">
        <div className="mb-10">
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">Edit images in a few clicks.</h1>
          <p className="text-muted mt-3">
            Resize, crop, convert, watermark and more. Chain steps together, then download the result. No account needed.
          </p>
        </div>

        <AnimatePresence mode="wait">
          {showResult ? (
            <motion.div key="result" {...fade}>
              <JobResult
                job={job}
                file={file}
                previewUrl={previewUrl}
                onReset={() => {
                  setSubmittedJob(null);
                  if (job.status === 'completed') clearFile();
                }}
              />
            </motion.div>
          ) : (
            <motion.form key="form" {...fade} onSubmit={handleSubmit} className="space-y-8">
              <ImageDrop file={file} previewUrl={previewUrl} onFile={chooseFile} onClear={clearFile} onReject={toast.error} />

              <section className="space-y-3">
                <div className="flex items-baseline justify-between gap-4">
                  <h2 className="text-sm font-medium">Steps</h2>
                  <span className="text-xs text-muted">Run top to bottom · drag to reorder</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {PRESETS.map((preset) => (
                    <button
                      key={preset.name}
                      type="button"
                      onClick={() => setSteps(presetSteps(preset))}
                      className="px-3 py-1 rounded-full text-xs border border-line text-muted hover:text-fg hover:border-muted transition-colors"
                    >
                      {preset.name}
                    </button>
                  ))}
                </div>
                <OperationBuilder steps={steps} onChange={setSteps} />
              </section>

              <button type="submit" disabled={uploading || !file || steps.length === 0} className="btn-primary w-full py-3">
                {uploading ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
                {uploading ? 'Uploading…' : 'Process image'}
              </button>
            </motion.form>
          )}
        </AnimatePresence>
      </main>

      <footer className="max-w-2xl w-full mx-auto px-5 py-8 text-xs text-muted">
        ImageForge · JPG, PNG and WebP up to 10 MB
      </footer>
    </div>
  );
};

export default LandingPage;
