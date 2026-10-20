import { useSyncExternalStore } from 'react';

const KEY = 'imageforge_theme';
const listeners = new Set();
const media = window.matchMedia('(prefers-color-scheme: dark)');

// index.html applies the saved or system theme before first paint; this module keeps it in sync after.
const current = () => (document.documentElement.classList.contains('dark') ? 'dark' : 'light');

const apply = (theme) => {
  document.documentElement.classList.toggle('dark', theme === 'dark');
  listeners.forEach((fn) => fn());
};

const savedTheme = () => {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
};

// Follow the system setting until the user picks a theme themselves.
media.addEventListener('change', () => {
  if (!savedTheme()) apply(media.matches ? 'dark' : 'light');
});

const subscribe = (fn) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};

export const toggleTheme = () => {
  const next = current() === 'dark' ? 'light' : 'dark';
  try {
    localStorage.setItem(KEY, next);
  } catch {
    // Storage can be unavailable (private mode); the toggle still works for this visit.
  }
  apply(next);
};

export const useTheme = () => useSyncExternalStore(subscribe, current);
