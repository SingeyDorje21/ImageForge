const TOKEN_KEY = 'imageforge_token';

export const getToken = () => localStorage.getItem(TOKEN_KEY);

export const authHeaders = () => {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};

// Drop an expired or rejected token and send the admin back to the login page.
export const handleAuthError = (err) => {
  if (err?.response?.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    window.location.href = '/login';
    return true;
  }
  return false;
};
