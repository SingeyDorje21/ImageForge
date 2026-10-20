import React, { useCallback, useEffect, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { ImagePlus, X } from 'lucide-react';
import clsx from 'clsx';
import { formatBytes } from '../lib/jobs';
import { ACCEPT, usePasteImages } from '../lib/images';

export const MAX_FILE_MB = 10;

const rejectionMessage = (rejections) => {
  if (rejections.some((r) => r.errors.some((e) => e.code === 'too-many-files'))) return 'Please choose one image.';
  const tooLarge = rejections.filter((r) => r.errors.some((e) => e.code === 'file-too-large')).length;
  const wrongType = rejections.length - tooLarge;
  const parts = [];
  if (tooLarge) parts.push(tooLarge === 1 ? `1 file is over ${MAX_FILE_MB} MB` : `${tooLarge} files are over ${MAX_FILE_MB} MB`);
  if (wrongType) parts.push(wrongType === 1 ? '1 file is not a JPG, PNG or WebP image' : `${wrongType} files are not JPG, PNG or WebP images`);
  return `Skipped: ${parts.join(' and ')}.`;
};

// File picking shared by the drop area and the "Add images" button.
const useImagePicker = ({ multiple, onFiles, onReject, noDrag = false }) =>
  useDropzone({
    accept: ACCEPT,
    multiple,
    maxFiles: multiple ? 0 : 1,
    maxSize: MAX_FILE_MB * 1024 * 1024,
    noDrag,
    onDropAccepted: (accepted) => onFiles(multiple ? accepted : accepted.slice(0, 1)),
    onDropRejected: (rejections) => onReject?.(rejectionMessage(rejections)),
  });

export const AddImagesButton = ({ onFiles, onReject, className = '', children }) => {
  const { getRootProps, getInputProps } = useImagePicker({ multiple: true, onFiles, onReject, noDrag: true });
  return (
    <button type="button" {...getRootProps({ className })}>
      <input {...getInputProps()} />
      {children}
    </button>
  );
};

// Drop, browse or paste images. With a single file chosen it shows a preview with dimensions and size.
// Pass onFiles with multiple to accept several at once, or onFile for one.
const ImageDrop = ({ file, previewUrl, onFile, onFiles, multiple = false, paste = true, onClear, onReject, className = 'h-64' }) => {
  const [dimensions, setDimensions] = useState(null);
  const handleFiles = useCallback((files) => (multiple ? onFiles(files) : onFile(files[0])), [multiple, onFiles, onFile]);
  const { getRootProps, getInputProps, isDragActive } = useImagePicker({ multiple, onFiles: handleFiles, onReject });
  usePasteImages(handleFiles, paste);

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
        <p className="text-sm font-medium">
          {isDragActive ? 'Drop to add' : multiple ? 'Drop images, or click to browse' : 'Drop an image, or click to browse'}
        </p>
        <p className="text-xs text-muted mt-1">
          {multiple && 'Pick as many as you like. '}You can also paste. JPG, PNG or WebP up to {MAX_FILE_MB} MB{multiple && ' each'}.
        </p>
      </div>
    </div>
  );
};

export default ImageDrop;
