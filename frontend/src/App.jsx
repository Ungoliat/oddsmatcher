import { useEffect, useRef, useState, useCallback } from "react";

const API_URL = "http://127.0.0.1:8000";

function App() {
  // =========================
  // AUTH
  // =========================
  const [token, setToken] = useState(localStorage.getItem("jwt") || "");
  const [user, setUser] = useState(null);

  // =========================
  // DATA EVENTS
  // =========================
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [limit, setLimit] = useState(200);
  const [nextOffset, setNextOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loadingEvents, setLoadingEvents] = useState(false);

  // =========================
  // FILTER OPTIONS (desde DB)
  // =========================
  const [filterOptions, setFilterOptions] = useState({
    bookies: [],
    deportes: [],
    competiciones: [],
    mercados: [],
  });
  const [loadingFilters, setLoadingFilters] = useState(false);

  // =========================
  // SELECTED FILTERS
  // =========================
  const [selectedDeporte, setSelectedDeporte] = useState("");
  const [selectedBookie, setSelectedBookie] = useState("");
  const [selectedMercado, setSelectedMercado] = useState("");

  const [competicionInput, setCompeticionInput] = useState("");
  const [partidoInput, setPartidoInput] = useState("");

  const [selectedCompeticion, setSelectedCompeticion] = useState("");
  const [selectedPartido, setSelectedPartido] = useState("");

  // =========================
  // LOGIN FORM
  // =========================
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // =========================
  // UI / STATUS
  // =========================
  const [error, setError] = useState("");
  const sentinelRef = useRef(null);
  const observerRef = useRef(null);
  const loadingEventsRef = useRef(false);

  // =========================
  // AUTH HELPERS
  // =========================
  const fetchMe = useCallback(async (jwt) => {
    try {
      const res = await fetch(`${API_URL}/me`, {
        headers: {
          Authorization: `Bearer ${jwt}`,
        },
      });

      if (!res.ok) {
        throw new Error("Token inválido o sesión expirada");
      }

      const data = await res.json();
      setUser(data);
    } catch (err) {
      console.error("Error en /me:", err);
      setUser(null);
      setToken("");
      localStorage.removeItem("jwt");
    }
  }, []);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");

    try {
      const body = new URLSearchParams();
      body.append("username", username);
      body.append("password", password);

      const res = await fetch(`${API_URL}/token`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body,
      });

      if (!res.ok) {
        throw new Error("Login incorrecto");
      }

      const data = await res.json();
      localStorage.setItem("jwt", data.access_token);
      setToken(data.access_token);
      await fetchMe(data.access_token);
    } catch (err) {
      console.error(err);
      setError(err.message || "Error de login");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("jwt");
    setToken("");
    setUser(null);
    setItems([]);
    setTotal(0);
    setNextOffset(0);
    setHasMore(true);
    setLoadingEvents(false);
    setLoadingFilters(false);
    setError("");
    loadingEventsRef.current = false;

    setSelectedDeporte("");
    setSelectedBookie("");
    setSelectedMercado("");
    setCompeticionInput("");
    setPartidoInput("");
    setSelectedCompeticion("");
    setSelectedPartido("");

    setFilterOptions({
      bookies: [],
      deportes: [],
      competiciones: [],
      mercados: [],
    });
  };

  // =========================
  // LOAD FILTERS
  // =========================
  const loadFilters = useCallback(async () => {
    if (!token) return;

    setLoadingFilters(true);
    setError("");

    try {
      const res = await fetch(`${API_URL}/events/filters`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        throw new Error("No se pudieron cargar los filtros");
      }

      const data = await res.json();

      setFilterOptions({
        bookies: data.bookies || [],
        deportes: data.deportes || [],
        competiciones: data.competiciones || [],
        mercados: data.mercados || [],
      });
    } catch (err) {
      console.error("Error cargando filtros:", err);
      setError(err.message || "Error cargando filtros");
    } finally {
      setLoadingFilters(false);
    }
  }, [token]);

  // =========================
  // BUILD URL WITH FILTERS
  // =========================
  const buildEventsUrl = useCallback(
    (offsetToUse = 0, appendLimit = limit) => {
      const params = new URLSearchParams();

      params.set("limit", appendLimit);
      params.set("offset", offsetToUse);

      if (selectedDeporte) {
        params.set("deporte", selectedDeporte);
      }

      if (selectedBookie) {
        params.set("bookie", selectedBookie);
      }
      if (selectedMercado) {
        params.set("mercado", selectedMercado);
      }
      if (selectedCompeticion.trim()) {
        params.set("competicion", selectedCompeticion.trim());
      }

      if (selectedPartido.trim()) {
        params.set("partido", selectedPartido.trim());
      }

      return `${API_URL}/events?${params.toString()}`;
    },
    [
      limit,
      selectedDeporte,
      selectedBookie,
      selectedMercado,
      selectedCompeticion,
      selectedPartido,
    ]
  );

  // =========================
  // LOAD EVENTS
  // =========================
  const loadEvents = useCallback(
    async (offsetToUse = 0, append = false) => {
      if (!token || loadingEventsRef.current) return;

      loadingEventsRef.current = true;
      setLoadingEvents(true);
      setError("");

      try {
        const url = buildEventsUrl(offsetToUse, limit);
        console.log("Cargando:", url);

        const res = await fetch(url, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const contentType = res.headers.get("content-type") || "";
        console.log("STATUS:", res.status, "CONTENT-TYPE:", contentType);

        if (!res.ok) {
          throw new Error("No se pudieron cargar los eventos");
        }

        const data = await res.json();
        console.log("DATA:", data);

        const newEvents = Array.isArray(data.events) ? data.events : [];

        setItems((prev) => (append ? [...prev, ...newEvents] : newEvents));
        setTotal(data.total || 0);

        const newOffset = offsetToUse + newEvents.length;
        setNextOffset(newOffset);

        setHasMore(newOffset < (data.total || 0));
      } catch (err) {
        console.error("Error cargando eventos:", err);
        setError(err.message || "Error cargando eventos");
      } finally {
        loadingEventsRef.current = false;
        setLoadingEvents(false);
      }
    },
    [token, limit, buildEventsUrl]
  );

  // =========================
  // RESET + RELOAD
  // =========================
  const resetAndLoad = useCallback(async () => {
    setItems([]);
    setTotal(0);
    setNextOffset(0);
    setHasMore(true);
    await loadEvents(0, false);
  }, [loadEvents]);

  const clearFilters = () => {
    setSelectedDeporte("");
    setSelectedBookie("");
    setSelectedMercado("");
    setCompeticionInput("");
    setPartidoInput("");
    setSelectedCompeticion("");
    setSelectedPartido("");
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      setSelectedCompeticion(competicionInput.trim());
    }, 400);

    return () => clearTimeout(timer);
  }, [competicionInput]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSelectedPartido(partidoInput.trim());
    }, 400);

    return () => clearTimeout(timer);
  }, [partidoInput]);

  // =========================
  // INITIAL AUTH CHECK
  // =========================
  useEffect(() => {
    if (token) {
      fetchMe(token);
    }
  }, [token, fetchMe]);

  // =========================
  // LOAD FILTERS WHEN TOKEN READY
  // =========================
  useEffect(() => {
    if (token) {
      loadFilters();
    }
  }, [token, loadFilters]);

  // =========================
  // FIRST LOAD / RELOAD WHEN FILTERS CHANGE
  // =========================
  useEffect(() => {
    if (!token) return;
    resetAndLoad();
  }, [
    token,
    limit,
    selectedDeporte,
    selectedBookie,
    selectedCompeticion,
    selectedPartido,
    resetAndLoad,
  ]);

  // =========================
  // INFINITE SCROLL
  // =========================
  useEffect(() => {
    if (!token) return;
    if (!sentinelRef.current) return;

    if (observerRef.current) {
      observerRef.current.disconnect();
    }

    observerRef.current = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (
          first.isIntersecting &&
          hasMore &&
          !loadingEvents &&
          items.length > 0
        ) {
          loadEvents(nextOffset, true);
        }
      },
      {
        root: null,
        rootMargin: "200px",
        threshold: 0.1,
      }
    );

    observerRef.current.observe(sentinelRef.current);

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [token, hasMore, loadingEvents, nextOffset, loadEvents, items.length]);

  return (
    <div style={{ padding: "24px", fontFamily: "Arial, sans-serif" }}>
      <h1>Oddsmatcher</h1>

      {!token ? (
        <form onSubmit={handleLogin} style={{ marginBottom: "24px" }}>
          <div style={{ marginBottom: "8px" }}>
            <input
              type="text"
              placeholder="Usuario"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div style={{ marginBottom: "8px" }}>
            <input
              type="password"
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button type="submit">Entrar</button>
        </form>
      ) : (
        <>
          <div style={{ marginBottom: "16px" }}>
            <strong>Sesión iniciada</strong>
            {user && (
              <span style={{ marginLeft: "12px" }}>
                Usuario: {user.username} | Rol: {user.role}
              </span>
            )}
            <button onClick={handleLogout} style={{ marginLeft: "12px" }}>
              Logout
            </button>
          </div>

          <div
            style={{
              marginBottom: "20px",
              padding: "16px",
              border: "1px solid #444",
              borderRadius: "8px",
            }}
          >
            <h3>Filtros</h3>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "12px",
                marginBottom: "12px",
              }}
            >
              <div>
                <label>Deporte</label>
                <br />
                <select
                  value={selectedDeporte}
                  onChange={(e) => setSelectedDeporte(e.target.value)}
                  style={{ width: "100%" }}
                >
                  <option value="">Todos</option>
                  {filterOptions.deportes.map((dep) => (
                    <option key={dep} value={dep}>
                      {dep}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label>Bookie</label>
                <br />
                <select
                  value={selectedBookie}
                  onChange={(e) => setSelectedBookie(e.target.value)}
                  style={{ width: "100%" }}
                >
                  <option value="">Todos</option>
                  {filterOptions.bookies.map((bookie) => (
                    <option key={bookie} value={bookie}>
                      {bookie}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label>Mercado</label>
                <br />
                <select
                  value={selectedMercado}
                  onChange={(e) => setSelectedMercado(e.target.value)}
                  style={{ width: "100%" }}
                >
                  <option value="">Todos</option>
                  {filterOptions.mercados.map((mercado) => (
                    <option key={mercado} value={mercado}>
                      {mercado}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label>Competición</label>
                <br />
                <input
                  type="text"
                  value={competicionInput}
                  onChange={(e) => setCompeticionInput(e.target.value)}
                  placeholder="Buscar competición..."
                  style={{ width: "100%" }}
                />
              </div>

              <div>
                <label>Partido</label>
                <br />
                <input
                  type="text"
                  value={partidoInput}
                  onChange={(e) => setPartidoInput(e.target.value)}
                  placeholder="Buscar partido..."
                  style={{ width: "100%" }}
                />
              </div>

              <div>
                <label>Límite</label>
                <br />
                <select
                  value={limit}
                  onChange={(e) => setLimit(Number(e.target.value))}
                  style={{ width: "100%" }}
                >
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value={500}>500</option>
                </select>
              </div>
            </div>

            <div style={{ display: "flex", gap: "8px" }}>
              <button onClick={resetAndLoad} disabled={loadingEvents}>
                Recargar desde 0
              </button>
              <button onClick={clearFilters} disabled={loadingEvents}>
                Limpiar filtros
              </button>
            </div>

            <div style={{ marginTop: "10px", fontSize: "14px" }}>
              {loadingFilters ? "Cargando filtros..." : "Filtros listos"}
            </div>
          </div>

          <div style={{ marginBottom: "16px" }}>
            <strong>Cargados:</strong> {items.length} / {total}
            <span style={{ marginLeft: "12px" }}>
              <strong>Offset siguiente:</strong> {nextOffset}
            </span>
            <span style={{ marginLeft: "12px" }}>
              <strong>Has more:</strong> {hasMore ? "Sí" : "No"}
            </span>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table
              border="1"
              cellPadding="8"
              style={{ borderCollapse: "collapse", width: "100%" }}
            >
              <thead>
                <tr>
                  <th>Bookie</th>
                  <th>Competición</th>
                  <th>Partido</th>
                  <th>Mercados</th>
                  <th>Deporte</th>
                </tr>
              </thead>
              <tbody>
                {items.map((e, idx) => (
                  <tr key={e.id || `${e.bookie}-${e.partido}-${idx}`}>
                    <td>{e.bookie}</td>
                    <td>{e.competicion}</td>
                    <td>{e.partido}</td>
                    <td>
                      {Array.isArray(e.mercados)
                        ? e.mercados.join(", ")
                        : typeof e.mercados === "string"
                          ? e.mercados
                            .split(",")
                            .map((m) => m.trim())
                            .filter(Boolean)
                            .join(", ")
                          : ""}
                    </td>
                    <td>{e.deporte}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div
            ref={sentinelRef}
            style={{
              height: "40px",
              marginTop: "16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {loadingEvents
              ? "Cargando más eventos..."
              : hasMore
                ? "Scroll para seguir cargando"
                : "No hay más resultados"}
          </div>
        </>
      )}

      {error && (
        <div style={{ marginTop: "16px", color: "red" }}>
          <strong>Error:</strong> {error}
        </div>
      )}
    </div>
  );
}

export default App;