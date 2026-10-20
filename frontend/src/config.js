// Base URL of the ImageForge API. Set VITE_API_URL at build time for deployments.
export const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
