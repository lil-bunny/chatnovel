const TOKEN_KEY = "chatnovel.token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setTokens(data) {
  localStorage.setItem(TOKEN_KEY, data.access_token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function req(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth && getToken()) headers.Authorization = `Bearer ${getToken()}`;
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401) {
    clearToken();
    throw new Error("unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "request failed");
  }
  return res.json();
}

export const api = {
  register: (email, password) => req("/v1/auth/register", { method: "POST", body: { email, password }, auth: false }),
  login: (email, password) => req("/v1/auth/login", { method: "POST", body: { email, password }, auth: false }),
  stories: () => req("/v1/stories"),
  story: (id) => req(`/v1/stories/${id}`),
  chapters: (id) => req(`/v1/stories/${id}/chapters`),
  state: (id) => req(`/v1/reading/${id}/state`),
  start: (id) => req(`/v1/reading/${id}/start`, { method: "POST" }),
  next: (id, chapterId, after) => {
    const q = new URLSearchParams();
    if (chapterId) q.set("chapter_id", chapterId);
    if (after) q.set("after", after);
    const s = q.toString();
    return req(`/v1/reading/${id}/next${s ? `?${s}` : ""}`);
  },
  ack: (id, lastMessageId) => req(`/v1/reading/${id}/ack?last_message_id=${lastMessageId}`, { method: "POST" }),
  billing: () => req("/v1/billing/me"),
  checkout: () => req("/v1/billing/checkout", { method: "POST" }),
  track: (name, payload) => req("/v1/analytics/events", { method: "POST", body: { name, payload } }),
};
