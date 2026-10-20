import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { toast } from 'sonner';
import clsx from 'clsx';
import { ReactCompareSlider, ReactCompareSliderImage } from 'react-compare-slider';
import { AlertCircle, ArrowRight, CheckCircle2, Download, ImagePlus, Loader2, RotateCcw, X } from 'lucide-react';
import ImageDrop, { AddImagesButton, MAX_FILE_MB } from '../components/ImageDrop';
import { usePasteImages } from '../lib/images';
import OperationBuilder from '../components/OperationBuilder';
import ThemeToggle from '../components/ThemeToggle';
import { PRESETS, newStep, presetSteps, toPayload } from '../lib/operations';
import { formatBytes, resultUrl } from '../lib/jobs';
import { useImageQueue } from '../lib/queue';

const CANVAS_HEIGHT = 'h-[340px] sm:h-[460px]';

const STATUS = {
  ready: { label: 'Ready', tone: 'text-muted' },
  waiting: { label: 'Queued', tone: 'text-muted' },
  uploading: { label: 'Uploading…', tone: 'text-accent' },
  pending: { label: 'Waiting for a worker…', tone: 'text-accent' },
  processing: { label: 'Processing…', tone: 'text-accent' },
  completed: { label: 'Done', tone: 'text-success' },
  failed: { label: 'Failed', tone: 'text-danger' },
};

// Above this many images, uploads are paced by the API's per-minute limit.
const UPLOAD_HINT_AT = 10;

const isBusy = (status) => ['waiting', 'uploading', 'pending', 'processing'].includes(status);

const downloadName = (item) => item.job?.result_path?.split(/[\\/]/).pop() || `edited-${item.file.name}`;

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

// The left-hand canvas: preview, progress, before/after or error for the selected image.
const Canvas = ({ item, onRemove }) => {
  const [dimensions, setDimensions] = useState(null);
  const url = item.status === 'completed' && item.job ? resultUrl(item.job) : null;
  const resultSize = useRemoteSize(url);
  const busy = isBusy(item.status);
  const saved = resultSize != null ? Math.round((1 - resultSize / item.file.size) * 100) : null;

  useEffect(() => setDimensions(null), [item.id]);

  return (
    <div className="card overflow-hidden">
      <div className={clsx('relative bg-subtle', CANVAS_HEIGHT)}>
        {url ? (
          <ReactCompareSlider
            className="h-full"
            itemOne={<ReactCompareSliderImage src={item.previewUrl} alt="Original" style={{ objectFit: 'contain' }} />}
            itemTwo={<ReactCompareSliderImage src={url} alt="Result" style={{ objectFit: 'contain' }} />}
          />
        ) : (
          <div className="h-full flex items-center justify-center p-4">
            <img
              src={item.previewUrl}
              alt={item.file.name}
              className={clsx('max-h-full max-w-full object-contain transition-opacity', busy && 'opacity-40')}
              onLoad={(e) => setDimensions([e.currentTarget.naturalWidth, e.currentTarget.naturalHeight])}
            />
          </div>
        )}

        {url && (
          <>
            <span className="absolute z-10 top-3 left-3 px-2 py-0.5 rounded-md bg-black/50 text-white text-[11px] backdrop-blur">Before</span>
            <span className="absolute z-10 top-3 right-3 px-2 py-0.5 rounded-md bg-black/50 text-white text-[11px] backdrop-blur">After</span>
          </>
        )}

        {!url && !busy && (
          <button
            type="button"
            onClick={onRemove}
            aria-label="Remove image"
            className="absolute top-3 right-3 h-8 w-8 flex items-center justify-center rounded-full bg-surface/90 border border-line text-muted hover:text-fg backdrop-blur"
          >
            <X size={14} />
          </button>
        )}

        <AnimatePresence>
          {busy && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 flex items-center justify-center">
              <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-surface border border-line shadow-sm text-sm">
                <Loader2 size={14} className="animate-spin text-accent" />
                {item.note || STATUS[item.status].label}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {item.status === 'failed' && (
        <div className="flex items-start gap-2 px-4 py-3 border-t border-line bg-danger/5 text-sm">
          <AlertCircle size={16} className="text-danger mt-0.5 shrink-0" />
          <span>{item.error || 'Something went wrong while processing the image.'}</span>
        </div>
      )}

      <MetaBar>
        {url ? (
          <>
            <span className="text-muted tabular-nums truncate">
              {formatBytes(item.file.size)} → <span className="text-fg">{resultSize != null ? formatBytes(resultSize) : '…'}</span>
              {saved != null && saved > 0 && <span className="text-success ml-2">−{saved}%</span>}
            </span>
            <a href={url} download={downloadName(item)} target="_blank" rel="noreferrer" className="btn-primary py-1.5 shrink-0">
              <Download size={14} /> Download
            </a>
          </>
        ) : (
          <>
            <span className="truncate font-medium">{item.file.name}</span>
            <span className="shrink-0 text-muted tabular-nums">
              {dimensions && `${dimensions[0]} × ${dimensions[1]} · `}{formatBytes(item.file.size)}
            </span>
          </>
        )}
      </MetaBar>
    </div>
  );
};

const QueueRow = ({ item, selected, onSelect, onRemove }) => {
  const url = item.status === 'completed' && item.job ? resultUrl(item.job) : null;
  const busy = isBusy(item.status);
  const status = STATUS[item.status];

  return (
    <li
      className={clsx(
        'flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors',
        selected ? 'bg-subtle' : 'hover:bg-subtle/60'
      )}
      onClick={onSelect}
    >
      <img src={url || item.previewUrl} alt="" className="h-10 w-10 rounded-md object-cover bg-subtle shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="text-sm truncate">{item.file.name}</p>
        <p className={clsx('text-xs truncate flex items-center gap-1', status.tone)}>
          {busy && <Loader2 size={10} className="animate-spin shrink-0" />}
          {item.status === 'completed' && <CheckCircle2 size={10} className="shrink-0" />}
          {item.status === 'failed' ? item.error || status.label : item.note || status.label}
        </p>
      </div>
      {url && (
        <a
          href={url}
          download={downloadName(item)}
          target="_blank"
          rel="noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="btn-ghost h-8 w-8 p-0 shrink-0"
          aria-label={`Download ${item.file.name}`}
        >
          <Download size={14} />
        </a>
      )}
      {!busy && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="btn-ghost h-8 w-8 p-0 shrink-0"
          aria-label={`Remove ${item.file.name}`}
        >
          <X size={14} />
        </button>
      )}
    </li>
  );
};

const LandingPage = () => {
  const { items, add, remove, clearFinished, submit } = useImageQueue();
  const [selectedId, setSelectedId] = useState(null);
  const [steps, setSteps] = useState(() => [newStep('resize')]);

  const addFiles = useCallback(
    (files) => {
      const added = add(files);
      if (added.length) setSelectedId(added[0].id);
    },
    [add]
  );
  usePasteImages(addFiles);

  const selected = items.find((i) => i.id === selectedId) || items[0];

  const removeItem = (id) => {
    remove(id);
    if (id === selectedId) setSelectedId(null);
  };

  const ready = items.filter((i) => i.status === 'ready');
  const finished = items.filter((i) => i.status === 'completed' || i.status === 'failed');
  const busyCount = items.filter((i) => isBusy(i.status)).length;
  const doneCount = items.filter((i) => i.status === 'completed').length;

  // New images go first; with none waiting, the button re-runs everything finished with the current steps.
  const targets = ready.length ? ready : busyCount ? [] : finished;
  const rerun = !ready.length && targets.length > 0;
  const plural = (n) => (n === 1 ? '1 image' : `${n} images`);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!targets.length || steps.length === 0) return;
    submit(targets.map((i) => i.id), toPayload(steps));
  };

  let buttonLabel = 'Process image';
  if (targets.length) buttonLabel = rerun ? `Run again on ${plural(targets.length)}` : `Process ${plural(targets.length)}`;
  else if (busyCount) buttonLabel = `Processing ${plural(busyCount)}…`;

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
        <div className="space-y-4 min-w-0">
          {selected ? (
            <Canvas key={selected.id} item={selected} onRemove={() => removeItem(selected.id)} />
          ) : (
            <ImageDrop multiple paste={false} onFiles={addFiles} onReject={toast.error} className={CANVAS_HEIGHT} />
          )}

          {items.length > 0 && (
            <section className="card overflow-hidden">
              <div className="flex items-center justify-between gap-3 px-3 py-2 border-b border-line">
                <h2 className="text-xs font-medium text-muted">
                  {plural(items.length)}
                  {doneCount > 0 && ` · ${doneCount} done`}
                  {busyCount > 0 && ` · ${busyCount} in progress`}
                </h2>
                <div className="flex items-center gap-1">
                  {doneCount > 0 && (
                    <button type="button" onClick={clearFinished} className="btn-ghost py-1 px-2 text-xs">
                      Clear done
                    </button>
                  )}
                  <AddImagesButton onFiles={addFiles} onReject={toast.error} className="btn-outline py-1 px-2.5 text-xs">
                    <ImagePlus size={14} /> Add images
                  </AddImagesButton>
                </div>
              </div>
              <ul className="divide-y divide-line max-h-80 overflow-y-auto">
                {items.map((item) => (
                  <QueueRow
                    key={item.id}
                    item={item}
                    selected={item.id === selected?.id}
                    onSelect={() => setSelectedId(item.id)}
                    onRemove={() => removeItem(item.id)}
                  />
                ))}
              </ul>
            </section>
          )}
        </div>

        <aside className="card lg:sticky lg:top-20 flex flex-col">
          <div className="p-4 border-b border-line">
            <h1 className="text-sm font-semibold">Steps</h1>
            <p className="text-xs text-muted mt-0.5">Applied top to bottom to every image. Drag to reorder, click to edit.</p>
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
            <button type="submit" disabled={!targets.length || steps.length === 0} className="btn-primary w-full py-2.5">
              {!targets.length && busyCount ? <Loader2 size={16} className="animate-spin" /> : rerun ? <RotateCcw size={16} /> : <ArrowRight size={16} />}
              {buttonLabel}
            </button>
            <p className="text-[11px] text-muted text-center">
              {!items.length
                ? `Add one or more images to start. JPG, PNG or WebP up to ${MAX_FILE_MB} MB each.`
                : items.length > UPLOAD_HINT_AT
                  ? 'Large batches upload at about 10 images a minute.'
                  : 'Add more images any time; they queue up behind the current ones.'}
            </p>
          </div>
        </aside>
      </form>
    </div>
  );
};

export default LandingPage;
