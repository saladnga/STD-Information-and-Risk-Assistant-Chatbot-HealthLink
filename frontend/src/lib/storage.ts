const SESSION_ID_KEY = "current_session_id";

export interface User {
  id: string;
  first_name: string;
  last_name: string;
  email?: string;
  has_custom_openai_key?: boolean;
  openai_model?: string | null;
  [key: string]: unknown;
}

export const getToken = () => localStorage.getItem("access_token");

export const getUser = () => {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
};

export const saveUser = (user: User) =>
  localStorage.setItem("user", JSON.stringify(user));

export const saveSession = (token: string, user: User) => {
  localStorage.setItem("access_token", token);
  saveUser(user);
  // A fresh login should never auto-resume whatever chat was last active - especially not another user's, on a shared browser that never logged out.
  clearCurrentSessionId();
};

export const getCurrentSessionId = () => localStorage.getItem(SESSION_ID_KEY);

export const setCurrentSessionId = (id: string) =>
  localStorage.setItem(SESSION_ID_KEY, id);

export const clearCurrentSessionId = () =>
  localStorage.removeItem(SESSION_ID_KEY);

export const clearAuth = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
  clearCurrentSessionId();
};
