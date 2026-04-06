import { NavLink, Outlet } from "react-router-dom";

const nav = [
  { to: "/", label: "Home" },
  { to: "/explore", label: "Explore graph" },
  { to: "/upload", label: "Upload dataset" },
  { to: "/stats", label: "Company stats" },
  { to: "/optimize", label: "Optimize profit" },
];

export function Layout() {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <aside
        style={{
          width: 220,
          background: "#0a0e14",
          borderRight: "1px solid var(--border)",
          padding: "1.25rem 0.75rem",
        }}
      >
        <div style={{ padding: "0 0.75rem 1rem", fontWeight: 700, fontSize: "1.05rem" }}>
          Fraud Graph
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {nav.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              style={({ isActive }) => ({
                padding: "0.5rem 0.75rem",
                borderRadius: 8,
                color: isActive ? "#fff" : "#94a3b8",
                background: isActive ? "rgba(59,130,246,0.25)" : "transparent",
                fontWeight: isActive ? 600 : 400,
              })}
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, background: "#0c1017" }}>
        <Outlet />
      </main>
    </div>
  );
}
