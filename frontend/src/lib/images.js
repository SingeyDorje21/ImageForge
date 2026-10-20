import { useEffect } from 'react';

// Image types the API accepts, in react-dropzone's format.
export const ACCEPT = { 'image/jpeg': ['.jpg', '.jpeg'], 'image/png': ['.png'], 'image/webp': ['.webp'] };

// Adds images pasted anywhere on the page (Ctrl/Cmd+V).
export const usePasteImages = (onFiles, enabled = true) => {
  useEffect(() => {
    if (!enabled) return undefined;
    const onPaste = (e) => {
      const files = [...(e.clipboardData?.files || [])].filter((f) => Object.keys(ACCEPT).includes(f.type));
      if (files.length) onFiles(files);
    };
    window.addEventListener('paste', onPaste);
    return () => window.removeEventListener('paste', onPaste);
  }, [onFiles, enabled]);
};

