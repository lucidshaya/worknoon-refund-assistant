import { useEffect, useState } from "react";
import { api } from "../api.js";
import DecisionBadge from "../components/DecisionBadge.jsx";

export default function AdminDashboard() {
  const [stats, setStats] = useState(null);
  const [requests, setRequests] = useState([]);
  const [selected, setSelected] = useState(null);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");
  const [resolving, setResolving] = useState(false);

  async function refresh() {
    try {
      const [s, r] = await Promise.all([api.stats(), api.listRequests()]);
      setStats(s);
      setRequests(r);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 5000);
    return () => clearInterval(interval);
  }, []);

  async function openDetail(id) {
    try {
      const detail = await api.getRequest(id);
      setSelected(detail);
      setNote("");
    } catch (e) {
      setError(e.message);
    }
  }

  async function resolve(decision) {
    if (!selected || resolving) return;
    setResolving(true);
    try {
      const updated = await api.resolveRequest(selected.id, decision, note);
      setSelected(updated);
      refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setResolving(false);
    }
  }

  let auditTrail = null;
  if (selected?.audit_trail) {
    try {
      auditTrail = JSON.parse(selected.audit_trail);
    } catch (_) {
      auditTrail = null;
    }
  }

  return (
    <div className="admin-layout">
      <section className="admin-main">
        <h2>Support Dashboard</h2>

        {stats && (
          <div className="stat-row">
            <StatCard label="Total requests" value={stats.total} icon="📊" />
            <StatCard label="Approved" value={stats.approved} tone="approved" icon="✅" />
            <StatCard label="Denied" value={stats.denied} tone="denied" icon="❌" />
            <StatCard label="Escalated" value={stats.escalated} tone="escalated" icon="⚠️" />
            <StatCard label="Injection blocked" value={stats.injection_attempts} tone="warn" icon="🛡️" />
          </div>
        )}

        {error && <div className="error-banner">{error}</div>}

        <table className="requests-table" id="requests-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Time</th>
              <th>Customer</th>
              <th>Order</th>
              <th>Decision</th>
              <th>Rule</th>
              <th>Source</th>
              <th>Security</th>
            </tr>
          </thead>
          <tbody>
            {requests.map((r) => (
              <tr
                key={r.id}
                className={selected?.id === r.id ? "selected-row" : ""}
                onClick={() => openDetail(r.id)}
              >
                <td style={{ fontWeight: 600 }}>#{r.id}</td>
                <td>{new Date(r.created_at).toLocaleString()}</td>
                <td>{r.customer_id}</td>
                <td>{r.order_id}</td>
                <td>
                  <DecisionBadge decision={r.decision} />
                  {r.resolved_by_human && <span className="badge badge-human">Human</span>}
                </td>
                <td className="muted" style={{ fontSize: '0.78rem' }}>{r.policy_rule_hit}</td>
                <td>
                  <span className="badge" style={{
                    background: r.decision_source === 'ai_assisted' ? 'rgba(99,102,241,0.12)' : 'rgba(255,255,255,0.06)',
                    color: r.decision_source === 'ai_assisted' ? '#818cf8' : 'var(--text-muted)',
                  }}>
                    {r.decision_source === 'ai_assisted' ? '🤖 AI' : '⚙️ Engine'}
                  </span>
                </td>
                <td>{r.injection_flag ? <span className="badge badge-warn">🛡️ Flagged</span> : "—"}</td>
              </tr>
            ))}
            {requests.length === 0 && (
              <tr>
                <td colSpan={8} className="muted" style={{ textAlign: 'center', padding: '32px' }}>
                  No refund requests yet. Submit one from the Customer Chat tab.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <aside className="admin-detail">
        {!selected && (
          <div className="chat-empty" style={{ padding: '40px 0' }}>
            <div style={{ fontSize: '2rem', marginBottom: '12px' }}>📋</div>
            <div>Select a request to see full reasoning and the audit log.</div>
          </div>
        )}
        {selected && (
          <>
            <h3>
              Request #{selected.id} <DecisionBadge decision={selected.decision} />
            </h3>
            <p className="muted" style={{ fontSize: '0.8rem', marginBottom: '14px' }}>
              {new Date(selected.created_at).toLocaleString()}
            </p>

            <DetailRow label="Customer" value={selected.customer_id} />
            <DetailRow label="Order" value={selected.order_id} />
            <DetailRow label="Claimed reason" value={selected.claimed_reason} />
            <DetailRow label="Policy rule" value={selected.policy_rule_hit} />
            <DetailRow label="Decision source" value={selected.decision_source} />

            <h4>Customer message</h4>
            <p className="quote">{selected.customer_message}</p>

            {selected.injection_flag && (
              <div className="warn-box">
                <strong>🛡️ Security note:</strong> {selected.injection_detail}
              </div>
            )}

            <h4>AI reasoning</h4>
            <p className="quote">{selected.ai_summary || "—"}</p>

            <h4>Customer-facing reply</h4>
            <p className="quote">{selected.customer_reply}</p>

            {auditTrail && (
              <>
                <h4>Policy trace</h4>
                <ol className="trace-list">
                  {auditTrail.policy_trace?.map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ol>

                {auditTrail.classification && (
                  <>
                    <h4>AI Classification</h4>
                    <DetailRow label="Source" value={auditTrail.classification.source} />
                    <DetailRow label="Claimed reason" value={auditTrail.classification.claimed_reason} />
                    <DetailRow label="Conflicts" value={auditTrail.classification.conflicts_with_status ? "Yes" : "No"} />
                    <DetailRow label="Suspicious" value={auditTrail.classification.suspicious ? "Yes" : "No"} />
                    {auditTrail.classification.stated_amount !== null && (
                      <DetailRow label="Stated amount" value={`$${auditTrail.classification.stated_amount}`} />
                    )}
                  </>
                )}

                {auditTrail.guard && auditTrail.guard.flagged && (
                  <>
                    <h4>Guard Details</h4>
                    <div className="warn-box" style={{ marginTop: '4px' }}>
                      Matched patterns: {auditTrail.guard.matched_patterns.join(", ")}
                    </div>
                  </>
                )}
              </>
            )}

            {selected.decision === "escalated" && !selected.resolved_by_human && (
              <div className="resolve-box">
                <h4>🔍 Human Review Required</h4>
                <textarea
                  id="resolve-note"
                  placeholder="Reviewer note (optional)"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  rows={2}
                />
                <div className="resolve-buttons">
                  <button
                    id="resolve-approve-btn"
                    className="btn-approve"
                    onClick={() => resolve("approved")}
                    disabled={resolving}
                  >
                    {resolving ? "…" : "✓ Approve"}
                  </button>
                  <button
                    id="resolve-deny-btn"
                    className="btn-deny"
                    onClick={() => resolve("denied")}
                    disabled={resolving}
                  >
                    {resolving ? "…" : "✗ Deny"}
                  </button>
                </div>
              </div>
            )}

            {selected.resolved_by_human && (
              <div className="resolve-box">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge badge-human">Human Resolved</span>
                  <DecisionBadge decision={selected.decision} />
                </div>
                {selected.human_note && (
                  <p className="quote" style={{ marginTop: '10px' }}>{selected.human_note}</p>
                )}
              </div>
            )}
          </>
        )}
      </aside>
    </div>
  );
}

function StatCard({ label, value, tone, icon }) {
  return (
    <div className={`stat-card ${tone ? `tone-${tone}` : ""}`}>
      <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>{icon}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

function DetailRow({ label, value }) {
  return (
    <div className="detail-row">
      <span className="detail-label">{label}</span>
      <span className="detail-value">{value || "—"}</span>
    </div>
  );
}
