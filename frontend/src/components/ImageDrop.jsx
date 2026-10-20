import React, { useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { ImagePlus, X } from 'lucide-react';
import clsx from 'clsx';
import { formatBytes } from '../lib/jobs';

export const MAX_FILE_MB = 10;
const ACCEPT = { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'], 'image/webp': ['.webp'] };

// Drop, browse or paste an image. Shows a preview with dimensions and size once chosen.
const ImageDrop = ({ file, previewUrl, onFile, onClear, onReject, className = 'h-64' }) => {
  const [dimensions, setDimensions] = useState(null);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: ACCEPT,
    maxFiles: 1,
    maxSize: MAX_FILE_MB * 1024 * 1024,
    onDropAccepted: ([accepted]) => onFile(accepted),
    onDropRejected: ([rejection]) => {
      const code = rejection?.errors[0]?.code;
      onReject(code === 'file-too-large'
        ? `That file is over ${MAX_FILE_MB} MB.`
        : 'Please choose a JPG, PNG or WebP image.');
    },
  });

  useEffect(() => {
    const onPaste = (e) => {
      const item = [...(e.clipboardData?.files || [])].find((f) => Object.keys(ACCEPT).includes(f.type));
      if (item) onFile(item);
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  }, [onFile]);

  useEffect(() => setDimensions(null), [previewUrl]);

  if (file && previewUrl) {
    return (
      <div className="card overflow-hidden">
        <div className="relative bg-subtle flex items-center justify-center h-64">
          <img
            src={previewUrl}
            alt="Selected"
            className="max-h-full max-w-full object-contain"
            onLoad={(e) => setDimensions([e.currentTarget.naturalWidth, e.currentTarget.naturalHeight])}
          />
          <button
            type="button"
            onClick={onClear}
            aria-label="Remove image"
            className="absolute top-3 right-3 h-8 w-8 flex items-center justify-center rounded-full bg-surface/90 border border-line text-muted hover:text-fg backdrop-blur"
          >
            <X size={14} />
          </button>
        </div>
        <div className="flex items-center justify-between gap-4 px-4 py-3 text-sm">
          <span className="truncate font-medium">{file.name}</span>
          <span className="shrink-0 text-muted tabular-nums">
            {dimensions && `${dimensions[0]} × ${dimensions[1]} · `}{formatBytes(file.size)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      {...getRootProps()}
      className={clsx(
        'flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed cursor-pointer transition-colors text-center px-6',
        className,
        isDragActive ? 'border-accent bg-accent/5' : 'border-line hover:border-muted bg-surface'
      )}
    >
      <input {...getInputProps()} />
      <div className="h-11 w-11 rounded-full bg-subtle flex items-center justify-center text-muted">
        <ImagePlus size={20} />
      </div>
      <div>
        <p className="text-sm font-medium">{isDragActive ? 'Drop it here' : 'Drop an image, or click to browse'}</p>
        <p className="text-xs text-muted mt-1">You can also paste. JPG, PNG or WebP up to {MAX_FILE_MB} MB.</p>
      </div>
    </div>
  );
};

export default ImageDrop;
