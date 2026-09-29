import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api.js";
import CustomerChat from "./pages/CustomerChat.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";

export default function App() {
  const [aiOnline, setAiOnline] = useState(null);

  useEffect(() => {
    api
      .health()
      .then((h) => setAiOnline(h.ai_available))
      .catch(() => setAiOnline(false));
  }, []);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">WORKNOON &middot; Refund Assistant</div>
        <nav className="nav">
          <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
            Customer Chat
          </NavLink>
          <NavLink to="/admin" className={({ isActive }) => (isActive ? "active" : "")}>
            Support Dashboard
          </NavLink>
          {aiOnline !== null && (
            <div className={`ai-status ${aiOnline ? "online" : "offline"}`}>
              <span className="ai-dot" />
              {aiOnline ? "AI Online" : "AI Offline"}
            </div>
          )}
        </nav>
      </header>
      <main className="content">
        <Routes>
          <Route path="/" element={<CustomerChat />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </main>
    </div>
  );
}
