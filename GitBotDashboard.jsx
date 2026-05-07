import { useState, useEffect, useRef } from "react";

const MOCK_PROJECTS = [
  {
    id: 1, name: "portfolio-site", path: "~/projects/portfolio-site",
    branch: "main", status: "watching", lastCommit: "2 min ago",
    langs: ["HTML", "CSS", "JS"], lines: 1840, files: 24,
    commits: [
      { msg: "[auto] update 3 files: index.html, style.css (+1 more) — 14:32", time: "2 min ago", pushed: true },
      { msg: "[auto] add 1 file: about.html — 13:15", time: "1 hr ago", pushed: true },
    ]
  },
  {
    id: 2, name: "expense-tracker", path: "~/projects/expense-tracker",
    branch: "main", status: "watching", lastCommit: "45 min ago",
    langs: ["TypeScript", "React/TS", "CSS"], lines: 3210, files: 38,
    commits: [
      { msg: "[auto] update 2 files: App.tsx, utils.ts — 13:47", time: "45 min ago", pushed: true },
    ]
  },
  {
    id: 3, name: "cli-tool", path: "~/projects/cli-tool",
    branch: "dev", status: "idle", lastCommit: "3 hrs ago",
    langs: ["Python"], lines: 640, files: 8,
    commits: [
      { msg: "[auto] add 1 file: parser.py — 11:05", time: "3 hrs ago", pushed: false },
    ]
  },
];

const LANG_COLORS = {
  Python: "#3b82f6", JavaScript: "#f59e0b", TypeScript: "#60a5fa",
  "React/TS": "#06b6d4", HTML: "#f97316", CSS: "#a78bfa",
  SCSS: "#ec4899", Go: "#10b981", Rust: "#ef4444", JSON: "#94a3b8",
};

function StatusDot({ status }) {
  const color = status === "watching" ? "#22c55e" : status === "committing" ? "#f59e0b" : "#475569";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
      <span style={{
        width: 8, height: 8, borderRadius: "50%", background: color,
        boxShadow: status === "watching" ? `0 0 0 3px ${color}22` : "none",
        animation: status === "watching" ? "pulse 2s infinite" : "none",
        display: "inline-block"
      }} />
      <span style={{ fontSize: 12, color: "#94a3b8", textTransform: "capitalize" }}>{status}</span>
    </span>
  );
}

function LangBadge({ lang }) {
  return (
    <span style={{
      fontSize: 11, padding: "2px 8px", borderRadius: 4,
      background: `${LANG_COLORS[lang] || "#475569"}22`,
      color: LANG_COLORS[lang] || "#94a3b8",
      border: `1px solid ${LANG_COLORS[lang] || "#475569"}44`,
      fontFamily: "monospace",
    }}>{lang}</span>
  );
}

function ProjectCard({ project, onRemove }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div style={{
      background: "#111827", border: "1px solid #1f2937",
      borderRadius: 12, overflow: "hidden",
      transition: "border-color 0.2s",
    }}
      onMouseEnter={e => e.currentTarget.style.borderColor = "#374151"}
      onMouseLeave={e => e.currentTarget.style.borderColor = "#1f2937"}
    >
      {/* Header */}
      <div style={{ padding: "16px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 8,
            background: "linear-gradient(135deg, #1e3a5f, #1a2744)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16,
          }}>📁</div>
          <div>
            <div style={{ fontWeight: 600, color: "#f1f5f9", fontFamily: "monospace", fontSize: 14 }}>
              {project.name}
            </div>
            <div style={{ fontSize: 11, color: "#475569", fontFamily: "monospace" }}>{project.path}</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <StatusDot status={project.status} />
          <button onClick={() => setExpanded(e => !e)} style={{
            background: "#1f2937", border: "1px solid #374151", color: "#94a3b8",
            borderRadius: 6, padding: "4px 10px", cursor: "pointer", fontSize: 12,
          }}>{expanded ? "▲ hide" : "▼ details"}</button>
          <button onClick={() => onRemove(project.id)} style={{
            background: "transparent", border: "none", color: "#374151",
            cursor: "pointer", fontSize: 16, padding: 4, lineHeight: 1,
          }} title="Remove">✕</button>
        </div>
      </div>

      {/* Stats row */}
      <div style={{
        padding: "10px 20px", borderTop: "1px solid #1f2937",
        display: "flex", gap: 24, flexWrap: "wrap",
      }}>
        <div>
          <div style={{ fontSize: 11, color: "#475569" }}>BRANCH</div>
          <div style={{ fontSize: 13, color: "#60a5fa", fontFamily: "monospace" }}>⎇ {project.branch}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#475569" }}>FILES</div>
          <div style={{ fontSize: 13, color: "#e2e8f0" }}>{project.files}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#475569" }}>LINES</div>
          <div style={{ fontSize: 13, color: "#e2e8f0" }}>{project.lines.toLocaleString()}</div>
        </div>
        <div>
          <div style={{ fontSize: 11, color: "#475569" }}>LAST COMMIT</div>
          <div style={{ fontSize: 13, color: "#e2e8f0" }}>{project.lastCommit}</div>
        </div>
        <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
          {project.langs.map(l => <LangBadge key={l} lang={l} />)}
        </div>
      </div>

      {/* Commit log */}
      {expanded && (
        <div style={{ borderTop: "1px solid #1f2937", padding: "12px 20px" }}>
          <div style={{ fontSize: 11, color: "#475569", marginBottom: 8 }}>RECENT COMMITS</div>
          {project.commits.map((c, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "8px 12px", background: "#0f172a", borderRadius: 6, marginBottom: 6,
              border: "1px solid #1e293b",
            }}>
              <div style={{ fontFamily: "monospace", fontSize: 12, color: "#94a3b8", flex: 1, marginRight: 12 }}>
                {c.msg}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                <span style={{ fontSize: 11, color: "#475569" }}>{c.time}</span>
                <span style={{
                  fontSize: 10, padding: "2px 6px", borderRadius: 4,
                  background: c.pushed ? "#052e1633" : "#2d1b0933",
                  color: c.pushed ? "#22c55e" : "#f59e0b",
                  border: `1px solid ${c.pushed ? "#16653444" : "#78350f44"}`,
                }}>{c.pushed ? "✓ pushed" : "⏳ pending"}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function AddProjectModal({ onAdd, onClose }) {
  const [path, setPath] = useState("");
  const [branch, setBranch] = useState("main");
  const [debounce, setDebounce] = useState("30");
  const inputRef = useRef();

  useEffect(() => { inputRef.current?.focus(); }, []);

  return (
    <div style={{
      position: "fixed", inset: 0, background: "#000000bb",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }} onClick={onClose}>
      <div style={{
        background: "#111827", border: "1px solid #1f2937", borderRadius: 16,
        padding: 28, width: 420, maxWidth: "calc(100vw - 32px)",
      }} onClick={e => e.stopPropagation()}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#f1f5f9", marginBottom: 20 }}>Add Project</div>

        {[
          { label: "Project Path", value: path, set: setPath, placeholder: "~/projects/my-app", ref: inputRef },
          { label: "Branch", value: branch, set: setBranch, placeholder: "main" },
          { label: "Debounce (seconds)", value: debounce, set: setDebounce, placeholder: "30" },
        ].map(({ label, value, set, placeholder, ref }) => (
          <div key={label} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: "#94a3b8", marginBottom: 6 }}>{label}</div>
            <input ref={ref} value={value} onChange={e => set(e.target.value)}
              placeholder={placeholder}
              style={{
                width: "100%", background: "#0f172a", border: "1px solid #1f2937",
                borderRadius: 8, padding: "10px 14px", color: "#f1f5f9",
                fontSize: 13, fontFamily: "monospace", outline: "none",
                boxSizing: "border-box",
              }}
              onFocus={e => e.target.style.borderColor = "#3b82f6"}
              onBlur={e => e.target.style.borderColor = "#1f2937"}
            />
          </div>
        ))}

        <div style={{ display: "flex", gap: 10, marginTop: 20, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{
            padding: "10px 18px", borderRadius: 8, cursor: "pointer",
            background: "transparent", border: "1px solid #374151", color: "#94a3b8", fontSize: 13,
          }}>Cancel</button>
          <button onClick={() => { if (path) { onAdd({ path, branch, debounce }); onClose(); } }} style={{
            padding: "10px 18px", borderRadius: 8, cursor: "pointer",
            background: "#3b82f6", border: "none", color: "#fff", fontSize: 13, fontWeight: 600,
          }}>Add & Watch</button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [projects, setProjects] = useState(MOCK_PROJECTS);
  const [showModal, setShowModal] = useState(false);
  const [botRunning, setBotRunning] = useState(true);
  const [log, setLog] = useState([
    { time: "14:34:12", msg: "✅ Committed in portfolio-site: [auto] update 3 files: index.html, style.css (+1 more)", level: "ok" },
    { time: "14:34:13", msg: "🚀 Pushed to GitHub (main)", level: "ok" },
    { time: "13:47:51", msg: "✅ Committed in expense-tracker: [auto] update 2 files: App.tsx, utils.ts", level: "ok" },
    { time: "13:47:52", msg: "🚀 Pushed to GitHub (main)", level: "ok" },
    { time: "11:05:00", msg: "✅ Committed in cli-tool: [auto] add 1 file: parser.py", level: "ok" },
    { time: "11:05:01", msg: "⚠️  Push failed for cli-tool — no upstream configured for branch 'dev'", level: "warn" },
    { time: "10:00:00", msg: "👀 Watching 3 projects | Debounce: 30s | Auto-push: enabled", level: "info" },
  ]);

  const logEnd = useRef();
  useEffect(() => { logEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [log]);

  const handleAdd = ({ path, branch, debounce }) => {
    const name = path.split("/").filter(Boolean).pop() || "project";
    const newProject = {
      id: Date.now(), name, path,
      branch, status: "watching", lastCommit: "never",
      langs: [], lines: 0, files: 0, commits: [],
    };
    setProjects(p => [...p, newProject]);
    setLog(l => [...l, {
      time: new Date().toLocaleTimeString("en-US", { hour12: false }),
      msg: `👀 Now watching: ${path} (branch: ${branch}, debounce: ${debounce}s)`,
      level: "info",
    }]);
  };

  const handleRemove = (id) => {
    const p = projects.find(x => x.id === id);
    setProjects(ps => ps.filter(x => x.id !== id));
    if (p) setLog(l => [...l, {
      time: new Date().toLocaleTimeString("en-US", { hour12: false }),
      msg: `🗑  Removed project: ${p.name}`,
      level: "info",
    }]);
  };

  const totalCommits = projects.reduce((a, p) => a + p.commits.length, 0);
  const totalLines = projects.reduce((a, p) => a + p.lines, 0);

  return (
    <div style={{
      minHeight: "100vh", background: "#030712",
      fontFamily: "'IBM Plex Mono', 'Fira Code', monospace",
      color: "#e2e8f0", padding: "0 0 40px",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 2px; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:none} }
      `}</style>

      {/* Header */}
      <div style={{
        background: "#030712", borderBottom: "1px solid #0f172a",
        padding: "16px 28px", display: "flex", alignItems: "center", justifyContent: "space-between",
        position: "sticky", top: 0, zIndex: 50, backdropFilter: "blur(12px)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 22 }}>🤖</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15, color: "#f1f5f9" }}>GitHub Auto-Commit Bot</div>
            <div style={{ fontSize: 11, color: "#475569" }}>Watches your VSCode projects & auto-commits</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button onClick={() => setBotRunning(r => !r)} style={{
            padding: "8px 16px", borderRadius: 8, cursor: "pointer", fontSize: 12, fontWeight: 600,
            background: botRunning ? "#052e1644" : "#1e293b",
            border: `1px solid ${botRunning ? "#16653488" : "#374151"}`,
            color: botRunning ? "#22c55e" : "#94a3b8",
            transition: "all 0.2s",
          }}>
            {botRunning ? "⏸ Pause Bot" : "▶ Start Bot"}
          </button>
          <button onClick={() => setShowModal(true)} style={{
            padding: "8px 16px", borderRadius: 8, cursor: "pointer", fontSize: 12, fontWeight: 600,
            background: "#1d4ed8", border: "1px solid #3b82f6", color: "#fff",
          }}>+ Add Project</button>
        </div>
      </div>

      <div style={{ maxWidth: 860, margin: "0 auto", padding: "28px 20px 0" }}>

        {/* Stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 28 }}>
          {[
            { label: "PROJECTS WATCHED", value: projects.length, icon: "📁" },
            { label: "AUTO-COMMITS", value: totalCommits, icon: "✅" },
            { label: "LINES OF CODE", value: totalLines.toLocaleString(), icon: "📝" },
            { label: "BOT STATUS", value: botRunning ? "Running" : "Paused", icon: botRunning ? "🟢" : "🔴" },
          ].map(s => (
            <div key={s.label} style={{
              background: "#0a0f1a", border: "1px solid #0f172a",
              borderRadius: 10, padding: "16px 18px",
            }}>
              <div style={{ fontSize: 11, color: "#475569", marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontSize: 20, fontWeight: 700, color: "#f1f5f9" }}>
                {s.icon} {s.value}
              </div>
            </div>
          ))}
        </div>

        {/* Projects */}
        <div style={{ marginBottom: 8, fontSize: 11, color: "#475569" }}>PROJECTS</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 28 }}>
          {projects.map(p => (
            <div key={p.id} style={{ animation: "fadeIn 0.3s ease" }}>
              <ProjectCard project={p} onRemove={handleRemove} />
            </div>
          ))}
          {projects.length === 0 && (
            <div style={{
              textAlign: "center", padding: 48, color: "#374151",
              border: "1px dashed #1f2937", borderRadius: 12,
            }}>
              No projects added yet. Click <strong style={{ color: "#60a5fa" }}>+ Add Project</strong> to get started.
            </div>
          )}
        </div>

        {/* Log */}
        <div style={{ marginBottom: 8, fontSize: 11, color: "#475569" }}>ACTIVITY LOG</div>
        <div style={{
          background: "#050d1a", border: "1px solid #0f172a",
          borderRadius: 12, padding: 16, maxHeight: 220, overflowY: "auto",
        }}>
          {log.map((entry, i) => (
            <div key={i} style={{
              display: "flex", gap: 12, padding: "4px 0",
              borderBottom: i < log.length - 1 ? "1px solid #0a0f1a" : "none",
            }}>
              <span style={{ color: "#1e4f6e", flexShrink: 0, fontSize: 12 }}>{entry.time}</span>
              <span style={{
                fontSize: 12,
                color: entry.level === "ok" ? "#86efac" : entry.level === "warn" ? "#fbbf24" : "#94a3b8",
              }}>{entry.msg}</span>
            </div>
          ))}
          <div ref={logEnd} />
        </div>

        {/* Setup guide */}
        <div style={{
          marginTop: 28, background: "#050d1a", border: "1px solid #0f172a",
          borderRadius: 12, padding: 20,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "#60a5fa", marginBottom: 12 }}>⚡ Quick Setup</div>
          {[
            "pip install gitpython watchdog python-dotenv",
            "cp .env.example .env   # edit with your project paths",
            "python github_bot.py ~/projects/my-app",
          ].map((cmd, i) => (
            <div key={i} style={{
              fontFamily: "monospace", fontSize: 12, color: "#94a3b8",
              background: "#0a0f1a", border: "1px solid #0f172a",
              borderRadius: 6, padding: "8px 12px", marginBottom: 6,
              display: "flex", alignItems: "center", gap: 8,
            }}>
              <span style={{ color: "#1e4f6e" }}>$</span> {cmd}
            </div>
          ))}
        </div>

      </div>

      {showModal && <AddProjectModal onAdd={handleAdd} onClose={() => setShowModal(false)} />}
    </div>
  );
}
