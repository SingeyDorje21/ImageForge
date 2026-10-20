import { useCallback, useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { API_BASE } from '../config';
import { isActive } from './jobs';

// The API allows 10 uploads per client IP per clock minute. Staying at or under 10 in any rolling
// 60 seconds keeps every clock minute under the limit too.
const UPLOADS_PER_WINDOW = 10;
const WINDOW_MS = 60_000;
const POLL_MS = 1500;

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

// Time until the API's per-minute counter resets, plus a second of slack for clock skew.
const untilNextMinute = () => WINDOW_MS - (Date.now() % WINDOW_MS) + 1000;

let nextId = 1;

/**
 * A list of images that are uploaded one at a time at a pace the API's rate limit accepts, then
 * polled until each job finishes.
 *
 * Item status: ready → waiting → uploading → pending → processing → completed | failed.
 */
export const useImageQueue = () => {
  const [items, setItems] = useState([]);
  const itemsRef = useRef(items);
  const uploadQueue = useRef([]);
  const sentAt = useRef([]);
  const uploading = useRef(false);
  const alive = useRef(true);

  itemsRef.current = items;

  const patch = useCallback((id, changes) => {
    setItems((list) => list.map((item) => (item.id === id ? { ...item, ...changes } : item)));
  }, []);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  // Revoke preview URLs when the page goes away.
  useEffect(() => () => itemsRef.current.forEach((item) => URL.revokeObjectURL(item.previewUrl)), []);

  const add = useCallback((files) => {
    const added = files.map((file) => ({
      id: nextId++,
      file,
      previewUrl: URL.createObjectURL(file),
      status: 'ready',
      job: null,
      error: null,
      note: null,
    }));
    setItems((list) => [...list, ...added]);
    return added;
  }, []);

  const remove = useCallback((id) => {
    uploadQueue.current = uploadQueue.current.filter((entry) => entry.id !== id);
    setItems((list) => {
      const item = list.find((i) => i.id === id);
      if (item) URL.revokeObjectURL(item.previewUrl);
      return list.filter((i) => i.id !== id);
    });
  }, []);

  const clearFinished = useCallback(() => {
    setItems((list) => {
      list.filter((i) => i.status === 'completed').forEach((i) => URL.revokeObjectURL(i.previewUrl));
      return list.filter((i) => i.status !== 'completed');
    });
  }, []);

  const waitForSlot = async () => {
    for (;;) {
      const now = Date.now();
      sentAt.current = sentAt.current.filter((t) => now - t < WINDOW_MS);
      if (sentAt.current.length < UPLOADS_PER_WINDOW) return;
      await sleep(sentAt.current[0] + WINDOW_MS - now + 50);
    }
  };

  const runUploads = async () => {
    if (uploading.current) return;
    uploading.current = true;
    try {
      while (uploadQueue.current.length && alive.current) {
        const { id, file, operations } = uploadQueue.current[0];
        await waitForSlot();
        if (!uploadQueue.current.some((entry) => entry.id === id)) continue; // removed while waiting
        patch(id, { status: 'uploading', note: null });
        sentAt.current.push(Date.now());

        const formData = new FormData();
        formData.append('file', file);
        formData.append('operations', JSON.stringify(operations));

        try {
          const res = await axios.post(`${API_BASE}/jobs`, formData);
          uploadQueue.current.shift();
          patch(id, { status: 'pending', job: { job_id: res.data.job_id, status: 'pending' } });
        } catch (err) {
          if (err.response?.status === 429) {
            // Someone else on this IP used up the minute. Wait for the reset and try the same image again.
            const wait = untilNextMinute();
            patch(id, { status: 'waiting', note: `Upload limit reached, retrying in ${Math.ceil(wait / 1000)} s` });
            await sleep(wait);
            continue;
          }
          uploadQueue.current.shift();
          const detail = err.response?.data?.detail;
          patch(id, { status: 'failed', error: typeof detail === 'string' ? detail : 'Upload failed. Please try again.' });
        }
      }
    } finally {
      uploading.current = false;
    }
  };

  // Queue the given items for processing with `operations` (the API payload).
  const submit = useCallback((ids, operations) => {
    const files = new Map(itemsRef.current.filter((i) => ids.includes(i.id)).map((i) => [i.id, i.file]));
    if (!files.size) return;
    setItems((list) =>
      list.map((item) => (ids.includes(item.id) ? { ...item, status: 'waiting', job: null, error: null, note: null } : item))
    );
    uploadQueue.current.push(...[...files].map(([id, file]) => ({ id, file, operations })));
    runUploads();
    // runUploads only touches refs and stable callbacks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const hasActiveJobs = items.some((item) => item.job && isActive(item.job.status));

  useEffect(() => {
    if (!hasActiveJobs) return undefined;
    const interval = setInterval(() => {
      itemsRef.current
        .filter((item) => item.job && isActive(item.job.status))
        .forEach(async (item) => {
          try {
            const res = await axios.get(`${API_BASE}/jobs/${item.job.job_id}`);
            if (!alive.current) return;
            setItems((list) =>
              list.map((i) =>
                i.id === item.id && i.job?.job_id === res.data.job_id
                  ? { ...i, job: res.data, status: res.data.status, error: res.data.error_message || null }
                  : i
              )
            );
          } catch (err) {
            console.error(err);
          }
        });
    }, POLL_MS);
    return () => clearInterval(interval);
  }, [hasActiveJobs]);

  return { items, add, remove, clearFinished, submit };
};
