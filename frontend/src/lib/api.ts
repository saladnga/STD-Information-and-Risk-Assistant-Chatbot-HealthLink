import { getToken, saveSession } from "./storage";

export const API_URL = import.meta.env.VITE_API_URL;

export function apiFetch(path: string, options: RequestInit = {}) {
  const token = getToken();
  return fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...options.headers,
      ...(token
        ? {
            Authorization: `Bearer ${token}`,
          }
        : {}),
    },
  });
}

async function postJson(path: string, payload: object) {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await res.json();
  return { ok: res.ok, data };
}

export async function authRequest(path: string, payload: object) {
  const { ok, data } = await postJson(path, payload);
  if (ok) {
    saveSession(data.access_token, data.user);
  }
  return { ok, data };
}

export async function forgotPassword(email: string) {
  return postJson("/auth/forgot-password", { email });
}

export async function resetPassword(token: string, newPassword: string) {
  return postJson("/auth/reset-password", { token, new_password: newPassword });
}

// Set a key (+ model), or omit apiKey to change just the model when a key already exists. Never returns the raw key back.
export async function setOpenaiKey(apiKey: string | undefined, model: string) {
  const res = await apiFetch("/auth/openai-key", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey, model }),
  });
  const data = await res.json();
  return { ok: res.ok, data };
}

export async function clearOpenaiKey() {
  const res = await apiFetch("/auth/openai-key", { method: "DELETE" });
  const data = await res.json();
  return { ok: res.ok, data };
}
