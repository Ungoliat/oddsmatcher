import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export default function App() {
  // ---- auth ----
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState(localStorage.getItem("jwt") || "");
  const [authMsg, setAuthMsg] = useState("");

  // ---- data ----
  const [items, setItems] = useState([]); // acumulado (infinite)
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  // ---- paging ----
  const [limit, setLimit] = useState(200);
  const [total, setTotal] = useState(0);
  const [nextOffset, setNextOffset] = useState(0); // siguiente offset a pedir

  // ---- sentinel ----
  const sentinelRef = useRef(null);
  const inFlightRef = useRef(false);
  const abortRef = useRef(null);

  const hasMore = nextOffset < total;

  const authHeaders = useMemo(() => {
    const t = (token || "").trim();
    return t
      ? { Authorization: `Bearer ${t}`, Accept: "application/json" }
      : { Accept: "application/json" };
  }, [token]);

  async function login() {
    setErr("");
    setAuthMsg("");
    try {
      if (!username.trim() || !password.trim()) {
        setAuthMsg("Mete usuario y contraseña.");
        return;
      }

      const body = new URLSearchParams();
      body.set("username", username.trim());
      body.set("password", password);

      const res = await fetch(`${API_URL}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          Accept: "application/json",
        },
        body,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Login falló (HTTP ${res.status}). ${text.slice(0, 160)}`);
      }

      const data = await res.json();
      const jwt = data.access_token;
      setToken(jwt);
      localStorage.setItem("jwt", jwt);
      setAuthMsg("Login OK ✅");
    } catch (e) {
      setErr(e.message || String(e));
    }
  }

  function logout() {
    // abort request in-flight
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = null;

    setToken("");
    localStorage.removeItem("jwt");
    setItems([]);
    setTotal(0);
    setNextOffset(0);
    setAuthMsg("Logout ✅");
    setErr("");
  }

  const normalizeEvents = (rawEvents) => {
    return (rawEvents || []).map((e) => {
      const raw = e.mercados ?? "";
      const arr = Array.isArray(raw)
        ? raw
        : String(raw)
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
      return { ...e, mercados: arr };
    });
  };

  const loadEvents = useCallback(
    async (offsetToLoad = nextOffset, append = true) => {
      if (!token) return;
      if (inFlightRef.current) return;

      // si no hay más y estás intentando append, no hagas nada
      if (append && total > 0 && offsetToLoad >= total) return;

      inFlightRef.current = true;
      setLoading(true);
      setErr("");

      // abort previous request (si existiera)
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const url = `${API_URL}/events?limit=${limit}&offset=${offsetToLoad}`;
        const res = await fetch(url, { headers: authHeaders, signal: controller.signal });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Events HTTP ${res.status}. ${text.slice(0, 200)}`);
        }

        const ct = res.headers.get("content-type") || "";
        if (!ct.includes("application/json")) {
          const text = await res.text();
          throw new Error(`No JSON (${ct}). ${text.slice(0, 200)}`);
        }

        const data = await res.json();
        const normalized = normalizeEvents(data.events);

        const newTotal = Number(data.total ?? 0);
        const receivedOffset = Number(data.offset ?? offsetToLoad);

        setTotal(newTotal);

        // “siguiente offset” = lo ya cargado (offset actual + nº items recibidos)
        const computedNext = receivedOffset + normalized.length;
        setNextOffset(computedNext);

        if (append) {
          setItems((prev) => (receivedOffset === 0 ? normalized : [...prev, ...normalized]));
        } else {
          setItems(normalized);
        }
      } catch (e) {
        if (e?.name !== "AbortError") {
          setErr(e.message || String(e));
        }
      } finally {
        setLoading(false);
        inFlightRef.current = false;
      }
    },
    [API_URL, authHeaders, limit, nextOffset, token, total]
  );

  const resetAndLoad = useCallback(() => {
    setItems([]);
    setTotal(0);
    setNextOffset(0);
    // importante: pedir offset 0 explícito
    loadEvents(0, false);
  }, [loadEvents]);

  // Auto-cargar al entrar si ya hay token
  useEffect(() => {
    if (token) resetAndLoad();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  // Infinite scroll (IntersectionObserver)
  useEffect(() => {
    if (!token) return;
    const el = sentinelRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (!first?.isIntersecting) return;
        if (loading) return;
        if (!hasMore) return;
        loadEvents(nextOffset, true);
      },
      { root: null, rootMargin: "600px 0px", threshold: 0.01 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [token, loadEvents, nextOffset, hasMore, loading]);

  return (
    <div style={{ maxWidth: 980, margin: "40px auto", padding: 16 }}>
      <h1 style={{ marginBottom: 18 }}>Oddsmatcher – Events</h1>

      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <input
          style={{ padding: 10, width: 160 }}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="usuario"
        />
        <input
          style={{ padding: 10, width: 200 }}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="contraseña"
          type="password"
        />
        <button onClick={login} disabled={loading}>
          Login
        </button>
        <button onClick={logout} disabled={!token}>
          Logout
        </button>

        <span style={{ opacity: 0.8 }}>
          API: <code>{API_URL}</code>
        </span>
      </div>

      <div style={{ marginTop: 10, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
        <button onClick={resetAndLoad} disabled={!token || loading}>
          {loading ? "Cargando..." : "Recargar desde 0"}
        </button>

        <label style={{ opacity: 0.9 }}>
          Limit:&nbsp;
          <select
            value={limit}
            onChange={(e) => {
              const v = Number(e.target.value);
              setLimit(v);
              setItems([]);
              setTotal(0);
              setNextOffset(0);

              // 🔥 auto-recarga automática
              if (token) {
                loadEvents(0, false);
              }
            }}
            style={{ padding: 8 }}
            disabled={!token || loading}
          >
            <option value={50}>50</option>
            <option value={100}>100</option>
            <option value={200}>200</option>
            <option value={500}>500</option>
          </select>
        </label>

        <span style={{ opacity: 0.8 }}>
          Cargados: <strong>{items.length}</strong> / {total || 0}
          {total > 0 && (
            <>
              {" "}
              — Página:{" "}
              <strong>{Math.floor(Math.max(0, items.length - 1) / limit) + 1}</strong> /{" "}
              {Math.max(1, Math.ceil(total / limit))}
            </>
          )}
        </span>

        {authMsg && <span style={{ color: "#7CFC00" }}>{authMsg}</span>}
      </div>

      {err && <p style={{ color: "tomato", marginTop: 14, whiteSpace: "pre-wrap" }}>{err}</p>}

      {token && (
        <div style={{ marginTop: 14, opacity: 0.85, fontSize: 12 }}>
          Token guardado: <code>{token.slice(0, 24)}…</code>
        </div>
      )}

      <div style={{ marginTop: 18, overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>Bookie</th>
              <th style={th}>Competición</th>
              <th style={th}>Partido</th>
              <th style={th}>Mercados</th>
              <th style={th}>Deporte</th>
            </tr>
          </thead>
          <tbody>
            {items.map((e, i) => (
              <tr key={i}>
                <td style={td}>{e.bookie}</td>
                <td style={td}>{e.competicion}</td>
                <td style={td}>{e.partido}</td>
                <td style={td}>{Array.isArray(e.mercados) ? e.mercados.join(", ") : e.mercados}</td>
                <td style={td}>{e.deporte}</td>
              </tr>
            ))}

            {items.length === 0 && (
              <tr>
                <td style={td} colSpan={5}>
                  {token ? "Sin eventos aún. Pulsa “Recargar desde 0”." : "Haz login para empezar."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Sentinel + estado */}
      {token && (
        <div style={{ marginTop: 14 }}>
          <div ref={sentinelRef} style={{ height: 1 }} />
          <div style={{ opacity: 0.8, fontSize: 12, marginTop: 10 }}>
            {loading && "Cargando…"}
            {!loading && total > 0 && hasMore && "Scroll para cargar más…"}
            {!loading && total > 0 && !hasMore && "Fin ✅"}
          </div>
        </div>
      )}
    </div>
  );
}

const th = { textAlign: "left", padding: 10, borderBottom: "1px solid #444" };
const td = { padding: 10, borderBottom: "1px solid #333" };
