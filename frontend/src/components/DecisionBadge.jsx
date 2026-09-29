const STYLES = {
  approved: { label: "Approved", cls: "badge badge-approved" },
  denied: { label: "Denied", cls: "badge badge-denied" },
  escalated: { label: "Escalated", cls: "badge badge-escalated" },
};

export default function DecisionBadge({ decision }) {
  const s = STYLES[decision] || { label: decision, cls: "badge" };
  return <span className={s.cls}>{s.label}</span>;
}
