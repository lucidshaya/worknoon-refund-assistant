const API_BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ? JSON.stringify(body.detail) : detail;
    } catch (_) {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

export const api = {
  health: () => request("/health"),
  customers: () => request("/admin/customers"),
  submitRefund: (payload) =>
    request("/refunds", { method: "POST", body: JSON.stringify(payload) }),
  listRequests: () => request("/admin/requests"),
  getRequest: (id) => request(`/admin/requests/${id}`),
  resolveRequest: (id, decision, note) =>
    request(`/admin/requests/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ decision, note }),
    }),
  stats: () => request("/admin/stats"),
};
