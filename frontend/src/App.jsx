import { useState, useEffect } from "react";

const API = "http://localhost:8000";

function formatFecha(isoString) {
  if (!isoString) return "—";
  const d = new Date(isoString);
  return d.toLocaleDateString("es-ES", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

function Calculadora({ op, comision, token, onClose, onGuardado }) {
  const [stake, setStake] = useState(100);
  const [backOdds, setBackOdds] = useState(op.back_odds);
  const [layOdds, setLayOdds] = useState(op.lay_odds);
  const [com, setCom] = useState(comision);
  const [notas, setNotas] = useState("");
  const [guardando, setGuardando] = useState(false);
  const [guardado, setGuardado] = useState(false);

  const layStake = (stake * backOdds) / (layOdds - com / 100);
  const gananciaBack = stake * (backOdds - 1);
  const perdidaLay = layStake * (layOdds - 1);
  const neto = gananciaBack - perdidaLay;
  const rating = ((stake + neto) / stake) * 100;

  function getRatingColor(r) {
    if (r >= 100) return "#2ecc71";
    if (r >= 90) return "#f39c12";
    return "#e74c3c";
  }

  async function guardarApuesta() {
    setGuardando(true);
    try {
      const res = await fetch(`${API}/bets`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          partido: op.partido,
          competicion: op.competicion,
          fecha_evento: op.commence_time,
          outcome: op.outcome,
          mercado: op.mercado,
          bookie: op.bookie,
          back_odds: backOdds,
          lay_odds: layOdds,
          stake_back: stake,
          stake_lay: parseFloat(layStake.toFixed(2)),
          resultado_estimado: parseFloat(neto.toFixed(2)),
          notas: notas,
          estado: "pendiente",
        }),
      });
      if (res.ok) {
        setGuardado(true);
        onGuardado();
        setTimeout(() => onClose(), 1200);
      }
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div style={{ ...styles.modalOverlay, padding: "1rem" }} onClick={onClose}>
      <div style={styles.modalBox} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <div>
            <div style={{ color: "#aaa", fontSize: "0.85rem" }}>{op.competicion}</div>
            <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>{op.partido}</div>
            <div style={{ color: "#646cff", marginTop: "0.2rem" }}>
              {op.outcome} — {op.mercado}
            </div>
          </div>
          <button onClick={onClose} style={styles.btnCerrar}>✕</button>
        </div>

        <div style={styles.modalGrid}>
          <div style={styles.modalField}>
            <label style={styles.modalLabel}>💶 Stake back (€)</label>
            <input type="number" value={stake} min="1"
              onChange={e => setStake(parseFloat(e.target.value) || 0)}
              style={styles.modalInput} />
          </div>
          <div style={styles.modalField}>
            <label style={styles.modalLabel}>📈 Cuota back ({op.bookie})</label>
            <input type="number" value={backOdds} min="1" step="0.01"
              onChange={e => setBackOdds(parseFloat(e.target.value) || 0)}
              style={{ ...styles.modalInput, borderColor: "#2ecc71" }} />
          </div>
          <div style={styles.modalField}>
            <label style={styles.modalLabel}>📉 Cuota lay (Betfair)</label>
            <input type="number" value={layOdds} min="1" step="0.01"
              onChange={e => setLayOdds(parseFloat(e.target.value) || 0)}
              style={{ ...styles.modalInput, borderColor: "#e74c3c" }} />
          </div>
          <div style={styles.modalField}>
            <label style={styles.modalLabel}>💸 Comisión Betfair (%)</label>
            <input type="number" value={com} min="0" max="10" step="0.1"
              onChange={e => setCom(parseFloat(e.target.value) || 0)}
              style={styles.modalInput} />
          </div>
        </div>

        <div style={styles.resultadosGrid}>
          <div style={styles.resultadoBox}>
            <span style={styles.resultadoLabel}>Lay stake</span>
            <span style={styles.resultadoValor}>{isFinite(layStake) ? layStake.toFixed(2) : "—"}€</span>
          </div>
          <div style={styles.resultadoBox}>
            <span style={styles.resultadoLabel}>Resultado neto</span>
            <span style={{ ...styles.resultadoValor, color: neto >= 0 ? "#2ecc71" : "#e74c3c" }}>
              {isFinite(neto) ? (neto >= 0 ? "+" : "") + neto.toFixed(2) : "—"}€
            </span>
          </div>
          <div style={{ ...styles.resultadoBox, background: "rgba(100,108,255,0.1)", border: "1px solid #646cff" }}>
            <span style={styles.resultadoLabel}>Rating</span>
            <span style={{ ...styles.resultadoValor, color: getRatingColor(rating), fontSize: "1.5rem" }}>
              {isFinite(rating) ? rating.toFixed(2) : "—"}%
            </span>
          </div>
        </div>

        <div style={{ marginTop: "1rem" }}>
          <label style={styles.modalLabel}>📝 Notas (opcional)</label>
          <input
            type="text"
            value={notas}
            onChange={e => setNotas(e.target.value)}
            placeholder="Ej: apuesta calificante, 10 FB..."
            style={{ ...styles.modalInput, width: "100%", marginTop: "0.4rem", boxSizing: "border-box" }}
          />
        </div>

        <button
          onClick={guardarApuesta}
          disabled={guardando || guardado}
          style={{
            ...styles.btnPrimary,
            width: "100%",
            marginTop: "1rem",
            background: guardado ? "#2ecc71" : "#646cff",
            fontSize: "1rem",
            padding: "0.75rem",
          }}>
          {guardado ? "✅ Guardado" : guardando ? "Guardando..." : "💾 Guardar apuesta"}
        </button>
      </div>
    </div>
  );
}

function FilaLedger({ bet, onUpdate, onDelete }) {
  const [editando, setEditando] = useState(false);
  const [notas, setNotas] = useState(bet.notas || "");
  const [resultadoReal, setResultadoReal] = useState(bet.resultado_real ?? bet.resultado_estimado ?? "");
  const [estado, setEstado] = useState(bet.estado);
  const [tipo, setTipo] = useState(bet.tipo || "MB");

  async function guardar() {
    await onUpdate(bet.id, { notas, resultado_real: parseFloat(resultadoReal) || null, estado, tipo });
    setEditando(false);
  }

  const resultado = bet.resultado_real ?? bet.resultado_estimado;
  const esPositivo = resultado >= 0;

  return (
    <tr style={{ borderBottom: "1px solid #2a2a2a" }}>
      <td style={styles.td}>{formatFecha(bet.fecha_registro)}</td>
      <td style={styles.td}>
        {editando ? (
          <select value={tipo} onChange={e => setTipo(e.target.value)}
            style={{ ...styles.select, padding: "0.3rem" }}>
            <option value="MB">MB</option>
            <option value="ARB">ARB</option>
            <option value="DUTCH">Dutch</option>
            <option value="DUTCH3">Dutch 3B</option>
          </select>
        ) : (
          <span style={{
            padding: "0.2rem 0.5rem", borderRadius: "4px", fontSize: "0.8rem",
            background: tipo === "MB" ? "rgba(100,108,255,0.2)" :
              tipo === "ARB" ? "rgba(46,204,113,0.2)" :
              tipo === "DUTCH" ? "rgba(243,156,18,0.2)" : "rgba(231,76,60,0.2)",
            color: tipo === "MB" ? "#646cff" :
              tipo === "ARB" ? "#2ecc71" :
              tipo === "DUTCH" ? "#f39c12" : "#e74c3c",
          }}>{tipo}</span>
        )}
      </td>
      <td style={styles.td}>
        {editando ? (
          <input value={notas} onChange={e => setNotas(e.target.value)}
            style={{ ...styles.modalInput, padding: "0.3rem", fontSize: "0.85rem", width: "120px" }} />
        ) : (
          <span style={{ color: "#aaa" }}>{bet.notas || "—"}</span>
        )}
      </td>
      <td style={styles.td}>
        <div style={{ fontSize: "0.8rem", color: "#aaa" }}>{bet.competicion}</div>
        <div>{bet.partido}</div>
        <div style={{ fontSize: "0.8rem", color: "#646cff" }}>{bet.outcome}</div>
      </td>
      <td style={styles.td}>{formatFecha(bet.fecha_evento)}</td>
      <td style={styles.td}>{bet.bookie}</td>
      <td style={{ ...styles.td, color: "#2ecc71" }}>{bet.back_odds}</td>
      <td style={{ ...styles.td, color: "#e74c3c" }}>{bet.lay_odds}</td>
      <td style={styles.td}>{bet.stake_back}€</td>
      <td style={styles.td}>{bet.stake_lay}€</td>
      <td style={styles.td}>
        {editando ? (
          <input type="number" value={resultadoReal}
            onChange={e => setResultadoReal(e.target.value)}
            style={{ ...styles.modalInput, padding: "0.3rem", fontSize: "0.85rem", width: "80px" }} />
        ) : (
          <span style={{ color: esPositivo ? "#2ecc71" : "#e74c3c", fontWeight: "bold" }}>
            {resultado != null ? (esPositivo ? "+" : "") + parseFloat(resultado).toFixed(2) + "€" : "—"}
          </span>
        )}
      </td>
      <td style={styles.td}>
        {editando ? (
          <select value={estado} onChange={e => setEstado(e.target.value)}
            style={{ ...styles.select, padding: "0.3rem" }}>
            <option value="pendiente">Pendiente</option>
            <option value="ganada">Ganada</option>
            <option value="perdida">Perdida</option>
            <option value="completada">Completada</option>
          </select>
        ) : (
          <span style={{
            padding: "0.3rem 0.7rem", borderRadius: "4px", fontSize: "0.85rem",
            display: "inline-flex", alignItems: "center", gap: "0.4rem",
            fontWeight: "bold",
            background: estado === "ganada" ? "rgba(46,204,113,0.2)" :
              estado === "perdida" ? "rgba(231,76,60,0.2)" :
              estado === "completada" ? "rgba(46,204,113,0.2)" : "rgba(255,165,0,0.2)",
            color: estado === "ganada" ? "#2ecc71" :
              estado === "perdida" ? "#e74c3c" :
              estado === "completada" ? "#2ecc71" : "#f39c12",
            border: `1px solid ${estado === "ganada" ? "#2ecc71" :
              estado === "perdida" ? "#e74c3c" :
              estado === "completada" ? "#2ecc71" : "#f39c12"}`,
          }}>
            {estado === "completada" ? "✅" :
             estado === "ganada" ? "🏆" :
             estado === "perdida" ? "❌" : "⏳"}
            {estado}
          </span>
        )}
      </td>
      <td style={styles.td}>
        {editando ? (
          <div style={{ display: "flex", gap: "0.4rem" }}>
            <button onClick={guardar} style={{ ...styles.btnPrimary, padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}>✓</button>
            <button onClick={() => setEditando(false)} style={{ ...styles.btnLogout, padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}>✕</button>
          </div>
        ) : (
          <div style={{ display: "flex", gap: "0.4rem" }}>
            <button onClick={() => setEditando(true)} style={{ ...styles.btnVista, background: "#333", padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}>✏️</button>
            <button onClick={() => onDelete(bet.id)} style={{ ...styles.btnVista, background: "rgba(231,76,60,0.3)", padding: "0.3rem 0.6rem", fontSize: "0.8rem" }}>🗑</button>
          </div>
        )}
      </td>
    </tr>
  );
}
function CalculadoraDutcher3({ op, onClose }) {
  const [stakeTotal, setStakeTotal] = useState(100);
  const [cuota1, setCuota1] = useState(op.outcome_1.cuota);
  const [cuotaX, setCuotaX] = useState(op.outcome_x.cuota);
  const [cuota2, setCuota2] = useState(op.outcome_2.cuota);
  const [com1, setCom1] = useState(0);
  const [comX, setComX] = useState(0);
  const [com2, setCom2] = useState(0);

  const cuota1Net = cuota1 * (1 - com1 / 100);
  const cuotaXNet = cuotaX * (1 - comX / 100);
  const cuota2Net = cuota2 * (1 - com2 / 100);

  const margen = (1 / cuota1Net) + (1 / cuotaXNet) + (1 / cuota2Net);
  const stake1 = isFinite(margen) ? round2((stakeTotal / cuota1Net) / margen) : 0;
  const stakeX = isFinite(margen) ? round2((stakeTotal / cuotaXNet) / margen) : 0;
  const stake2 = isFinite(margen) ? round2((stakeTotal / cuota2Net) / margen) : 0;
  const retorno = isFinite(margen) ? round2(stakeTotal / margen) : 0;
  const beneficio = round2(retorno - stakeTotal);
  const beneficioPct = isFinite(margen) ? round2((1 - margen) * 100) : 0;

  function round2(n) { return Math.round(n * 100) / 100; }

  function getColor(n) {
    if (n > 0) return "#2ecc71";
    if (n > -5) return "#f39c12";
    return "#e74c3c";
  }

  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div style={{ ...styles.modalBox, maxWidth: "650px", width: "calc(100% - 2rem)", boxSizing: "border-box" }} onClick={e => e.stopPropagation()}>
        <div style={styles.modalHeader}>
          <div>
            <div style={{ color: "#aaa", fontSize: "0.85rem" }}>{op.competicion}</div>
            <div style={{ fontWeight: "bold", fontSize: "1.1rem" }}>{op.partido}</div>
            <div style={{ color: "#646cff", marginTop: "0.2rem" }}>Dutcher 3 Bandas</div>
          </div>
          <button onClick={onClose} style={styles.btnCerrar}>✕</button>
        </div>

        {/* Stake total */}
        <div style={{ marginBottom: "1.5rem" }}>
          <label style={styles.modalLabel}>💶 Stake total (€)</label>
          <input type="number" value={stakeTotal} min="1"
            onChange={e => setStakeTotal(parseFloat(e.target.value) || 0)}
            style={{ ...styles.modalInput, width: "150px", marginTop: "0.4rem" }} />
        </div>

        {/* Grid de 3 outcomes */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: "0.75rem", marginBottom: "1.5rem" }}>
          {[
            { label: "1 (Local)", bookie: op.outcome_1.bookie, cuota: cuota1, setCuota: setCuota1, com: com1, setCom: setCom1, stake: stake1 },
            { label: "X (Empate)", bookie: op.outcome_x.bookie, cuota: cuotaX, setCuota: setCuotaX, com: comX, setCom: setComX, stake: stakeX },
            { label: "2 (Visitante)", bookie: op.outcome_2.bookie, cuota: cuota2, setCuota: setCuota2, com: com2, setCom: setCom2, stake: stake2 },
          ].map((o, i) => (
            <div key={i} style={{ background: "#1a1a1a", border: "1px solid #333", borderRadius: "8px", padding: "1rem" }}>
              <div style={{ fontWeight: "bold", color: "#646cff", marginBottom: "0.5rem" }}>{o.label}</div>
              <div style={{ color: "#aaa", fontSize: "0.8rem", marginBottom: "0.75rem" }}>{o.bookie}</div>
              <div style={styles.modalField}>
                <label style={styles.modalLabel}>Cuota</label>
                <input type="number" value={o.cuota} min="1" step="0.01"
                  onChange={e => o.setCuota(parseFloat(e.target.value) || 0)}
                  style={{ ...styles.modalInput, borderColor: "#2ecc71", fontSize: "1rem" }} />
              </div>
              <div style={{ ...styles.modalField, marginTop: "0.5rem" }}>
                <label style={styles.modalLabel}>Comisión (%)</label>
                <input type="number" value={o.com} min="0" max="10" step="0.1"
                  onChange={e => o.setCom(parseFloat(e.target.value) || 0)}
                  style={{ ...styles.modalInput, fontSize: "1rem" }} />
              </div>
              <div style={{ marginTop: "0.75rem", textAlign: "center" }}>
                <div style={{ color: "#aaa", fontSize: "0.75rem" }}>Stake</div>
                <div style={{ fontWeight: "bold", color: "#646cff", fontSize: "1.1rem" }}>{o.stake}€</div>
              </div>
            </div>
          ))}
        </div>

        {/* Resultados */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" }}>
          <div style={styles.resultadoBox}>
            <span style={styles.resultadoLabel}>Retorno garantizado</span>
            <span style={{ ...styles.resultadoValor, color: "#2ecc71" }}>{retorno}€</span>
          </div>
          <div style={styles.resultadoBox}>
            <span style={styles.resultadoLabel}>Beneficio neto</span>
            <span style={{ ...styles.resultadoValor, color: getColor(beneficio) }}>
              {beneficio >= 0 ? "+" : ""}{beneficio}€
            </span>
          </div>
          <div style={{ ...styles.resultadoBox, background: "rgba(100,108,255,0.1)", border: "1px solid #646cff" }}>
            <span style={styles.resultadoLabel}>% Beneficio</span>
            <span style={{ ...styles.resultadoValor, color: getColor(beneficioPct), fontSize: "1.5rem" }}>
              {beneficioPct >= 0 ? "+" : ""}{beneficioPct}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [token, setToken] = useState(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pestana, setPestana] = useState("matching");
  const [groups, setGroups] = useState([]);
  const [oportunidades, setOportunidades] = useState([]);
  const [bets, setBets] = useState([]);
  const [dutcher3, setDutcher3] = useState([]);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [filtroLiga, setFiltroLiga] = useState("");
  const [filtroBookie, setFiltroBookie] = useState("");
  const [expandido, setExpandido] = useState({});
  const [vistaExpandida, setVistaExpandida] = useState(false);
  const [comision, setComision] = useState(2);
  const [opSeleccionada, setOpSeleccionada] = useState(null);
  const [dutcher3Seleccionada, setDutcher3Seleccionada] = useState(null);

  async function login() {
    setError("");
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const res = await fetch(`${API}/token`, { method: "POST", body: form });
    if (!res.ok) { setError("Usuario o contraseña incorrectos"); return; }
    const data = await res.json();
    setToken(data.access_token);
  }

  async function fetchGroups(tok) {
    try {
      const res = await fetch(`${API}/events/grouped`, { headers: { Authorization: `Bearer ${tok}` } });
      const data = await res.json();
      setGroups(data.groups || []);
    } catch { }
  }

  async function fetchMatching(tok, com) {
    setLoading(true);
    try {
      const res = await fetch(`${API}/odds/matching?comision=${com / 100}`, { headers: { Authorization: `Bearer ${tok}` } });
      const data = await res.json();
      setOportunidades(data.oportunidades || []);
    } catch { }
    finally { setLoading(false); }
  }

  async function fetchBets(tok) {
    try {
      const res = await fetch(`${API}/bets`, { headers: { Authorization: `Bearer ${tok}` } });
      const data = await res.json();
      setBets(data.bets || []);
    } catch { }
  }

async function fetchDutcher3(tok) {
  setLoading(true);
  try {
    const res = await fetch(`${API}/odds/dutcher3`, {
      headers: { Authorization: `Bearer ${tok}` },
    });
    const data = await res.json();
    setDutcher3(data.oportunidades || []);
  } catch { }
  finally { setLoading(false); }
}

 async function syncReal() {
    setSyncing(true); setSyncMsg("");
    try {
      const res = await fetch(`${API}/admin/sync-oddspapi`, {
        method: "POST", headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      setSyncMsg(`✅ Sync OK — ${data.inserted} eventos insertados`);
      fetchGroups(token);
      fetchMatching(token, comision);
    } catch { setSyncMsg("❌ Error en el sync"); }
    finally { setSyncing(false); }
  }

  async function updateBet(id, data) {
    await fetch(`${API}/bets/${id}`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    fetchBets(token);
  }

  async function deleteBet(id) {
    if (!confirm("¿Eliminar esta apuesta?")) return;
    await fetch(`${API}/bets/${id}`, {
      method: "DELETE", headers: { Authorization: `Bearer ${token}` },
    });
    fetchBets(token);
  }

  useEffect(() => {
    if (token) {
      fetchGroups(token);
      fetchMatching(token, comision);
      fetchBets(token);
    }
  }, [token]);

  function getRatingColor(rating) {
    if (rating >= 100) return "#2ecc71";
    if (rating >= 90) return "#f39c12";
    return "#e74c3c";
  }

  function getRatingBg(rating) {
    if (rating >= 100) return "rgba(46,204,113,0.05)";
    if (rating >= 90) return "rgba(243,156,18,0.05)";
    return "rgba(231,76,60,0.05)";
  }

  function getMargenColor(pct) {
  if (pct > 0) return "#2ecc71";
  if (pct > -5) return "#f39c12";
  return "#e74c3c";
}

  const ligas = [...new Set(groups.map(g => g.competicion))].sort();
  const bookies = [...new Set(groups.flatMap(g => g.bookies.map(b => b.bookie)))].sort();
  const groupsFiltrados = groups.filter(g => (!filtroLiga || g.competicion === filtroLiga) && (!filtroBookie || g.bookies.some(b => b.bookie === filtroBookie)));
  const opsFiltradas = oportunidades.filter(o => (!filtroLiga || o.competicion === filtroLiga) && (!filtroBookie || o.bookie === filtroBookie));

  const dutcher3Filtradas = dutcher3.filter(o => !filtroLiga || o.competicion === filtroLiga);
  const totalNeto = bets.reduce((acc, b) => acc + (b.resultado_real ?? b.resultado_estimado ?? 0), 0);

  if (!token) {
    return (
      <div style={styles.loginPage}>
        <div style={styles.loginBox}>
          <h1 style={styles.title}>Oddsmatcher</h1>
          <input placeholder="Usuario" value={username}
            onChange={e => setUsername(e.target.value)}
            onKeyDown={e => e.key === "Enter" && login()} style={styles.input} />
          <input type="password" placeholder="Contraseña" value={password}
            onChange={e => setPassword(e.target.value)}
            onKeyDown={e => e.key === "Enter" && login()} style={styles.input} />
          <button onClick={login} style={styles.btnPrimary}>Entrar</button>
          {error && <p style={{ color: "#ff6b6b", marginTop: "0.5rem" }}>{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      {opSeleccionada && (
        <Calculadora
          op={opSeleccionada}
          comision={comision}
          token={token}
          onClose={() => setOpSeleccionada(null)}
          onGuardado={() => fetchBets(token)}
        />
      )}
      {dutcher3Seleccionada && (
  <CalculadoraDutcher3
    op={dutcher3Seleccionada}
    onClose={() => setDutcher3Seleccionada(null)}
  />
)}

      <div style={styles.header}>
        <div style={{ display: "flex", alignItems: "center", gap: "1.5rem" }}>
          <h2 style={{ margin: 0 }}>⚽ Oddsmatcher</h2>
          <div style={styles.tabs}>
            <button onClick={() => setPestana("matching")} style={{ ...styles.tab, ...(pestana === "matching" ? styles.tabActive : {}) }}>🎯 Matching</button>
            <button onClick={() => setPestana("eventos")} style={{ ...styles.tab, ...(pestana === "eventos" ? styles.tabActive : {}) }}>📋 Eventos</button>
            <button onClick={() => { setPestana("ledger"); fetchBets(token); }} style={{ ...styles.tab, ...(pestana === "ledger" ? styles.tabActive : {}) }}>
              📒 Mis apuestas {bets.length > 0 && <span style={{ marginLeft: "0.3rem", background: "#646cff", borderRadius: "10px", padding: "0 0.4rem", fontSize: "0.75rem" }}>{bets.length}</span>}
            </button>
            <button onClick={() => { setPestana("dutcher3"); fetchDutcher3(token); }} style={{ ...styles.tab, ...(pestana === "dutcher3" ? styles.tabActive : {}) }}>
             🎲 Dutcher 3B
            </button>
          </div>
        </div>
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <button onClick={syncReal} disabled={syncing} style={styles.btnSync}>
            {syncing ? "Sincronizando..." : "🔄 Sync API"}
          </button>
          <button onClick={() => setToken(null)} style={styles.btnLogout}>Salir</button>
        </div>
      </div>

      {syncMsg && <p style={styles.syncMsg}>{syncMsg}</p>}

      {pestana !== "ledger" && (
        <div style={styles.filtros}>
          <select value={filtroLiga} onChange={e => setFiltroLiga(e.target.value)} style={styles.select}>
            <option value="">Todas las ligas</option>
            {ligas.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
          <select value={filtroBookie} onChange={e => setFiltroBookie(e.target.value)} style={styles.select}>
            <option value="">Todos los bookies</option>
            {bookies.filter(b => b !== "betfair").map(b => <option key={b} value={b}>{b}</option>)}
          </select>
          {pestana === "matching" && (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginLeft: "auto" }}>
              <label style={{ color: "#aaa", fontSize: "0.9rem" }}>Comisión Betfair:</label>
              <input type="number" value={comision} min="0" max="10" step="0.1"
                onChange={e => setComision(parseFloat(e.target.value))}
                style={{ ...styles.input, width: "60px", padding: "0.3rem 0.5rem", textAlign: "center" }} />
              <span style={{ color: "#aaa" }}>%</span>
              <button onClick={() => fetchMatching(token, comision)}
                style={{ ...styles.btnPrimary, padding: "0.3rem 0.8rem", fontSize: "0.85rem" }}>Aplicar</button>
            </div>
          )}
          {pestana === "eventos" && (
            <div style={{ marginLeft: "auto", display: "flex", gap: "0.5rem" }}>
              <button onClick={() => setVistaExpandida(false)} style={{ ...styles.btnVista, background: !vistaExpandida ? "#646cff" : "#333" }}>🖱 Click para expandir</button>
              <button onClick={() => setVistaExpandida(true)} style={{ ...styles.btnVista, background: vistaExpandida ? "#646cff" : "#333" }}>📋 Todo expandido</button>
            </div>
          )}
        </div>
      )}

      {loading ? (
        <p style={{ color: "#aaa", textAlign: "center", marginTop: "3rem" }}>Cargando...</p>
      ) : pestana === "matching" ? (
        <div style={styles.tableWrapper}>
          <p style={{ color: "#aaa", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            {opsFiltradas.length} oportunidades — haz clic en una fila para calcular
          </p>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Rating</th>
                <th style={styles.th}>Fecha</th>
                <th style={styles.th}>Partido</th>
                <th style={styles.th}>Outcome</th>
                <th style={styles.th}>Mercado</th>
                <th style={styles.th}>Bookie</th>
                <th style={styles.th}>Back</th>
                <th style={styles.th}>Lay</th>
                <th style={styles.th}>Resultado neto</th>
              </tr>
            </thead>
            <tbody>
              {opsFiltradas.map((o, i) => (
                <tr key={i} style={{ background: getRatingBg(o.rating), cursor: "pointer" }}
                  onClick={() => setOpSeleccionada(o)}>
                  <td style={{ ...styles.td, textAlign: "center" }}>
                    <span style={{ color: getRatingColor(o.rating), fontWeight: "bold", fontSize: "1rem" }}>{o.rating}%</span>
                  </td>
                  <td style={{ ...styles.td, fontSize: "0.85rem", color: "#aaa", whiteSpace: "nowrap" }}>{formatFecha(o.commence_time)}</td>
                  <td style={styles.td}>
                    <div style={{ fontSize: "0.8rem", color: "#aaa" }}>{o.competicion}</div>
                    <div>{o.partido}</div>
                  </td>
                  <td style={{ ...styles.td, fontWeight: "bold" }}>{o.outcome}</td>
                  <td style={styles.td}><span style={styles.mercadoBadge}>{o.mercado}</span></td>
                  <td style={styles.td}>{o.bookie}</td>
                  <td style={{ ...styles.td, color: "#2ecc71", fontWeight: "bold" }}>{o.back_odds}</td>
                  <td style={{ ...styles.td, color: "#e74c3c", fontWeight: "bold" }}>{o.lay_odds}</td>
                  <td style={{ ...styles.td, color: o.resultado_neto >= 0 ? "#2ecc71" : "#e74c3c", fontWeight: "bold" }}>
                    {o.resultado_neto >= 0 ? "+" : ""}{o.resultado_neto}€
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : pestana === "eventos" ? (
        <div style={styles.tableWrapper}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Liga</th>
                <th style={styles.th}>Partido</th>
                <th style={styles.th}>Bookies y cuotas</th>
              </tr>
            </thead>
            <tbody>
              {groupsFiltrados.map((g, i) => {
                const key = `${g.competicion}||${g.partido}`;
                const abierto = vistaExpandida || !!expandido[key];
                return (
                  <tr key={i} style={i % 2 === 0 ? styles.trEven : styles.trOdd}>
                    <td style={styles.td}>{g.competicion}</td>
                    <td style={{ ...styles.td, cursor: !vistaExpandida ? "pointer" : "default" }}
                      onClick={() => !vistaExpandida && setExpandido(prev => ({ ...prev, [key]: !prev[key] }))}>
                      {g.partido}
                      {!vistaExpandida && <span style={{ marginLeft: "0.5rem", color: "#646cff", fontSize: "0.8rem" }}>{abierto ? "▲" : "▼"}</span>}
                    </td>
                    <td style={styles.td}>
                      {!abierto ? (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                          {g.bookies.map((b, j) => (
                            <span key={j} style={styles.bookieBadge}><strong>{b.bookie}</strong>: {b.mercados.join(", ")}</span>
                          ))}
                        </div>
                      ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                          {g.bookies.map((b, j) => (
                            <div key={j} style={styles.bookieCard}>
                              <strong style={{ color: "#646cff" }}>{b.bookie}</strong>
                              {Object.entries(b.cuotas).map(([mercado, outcomes]) => (
                                <div key={mercado} style={{ marginTop: "0.4rem" }}>
                                  <span style={styles.mercadoLabel}>{mercado}</span>
                                  <div style={styles.outcomesRow}>
                                    {Object.entries(outcomes).map(([equipo, cuota]) => (
                                      <div key={equipo} style={styles.outcomeBox}>
                                        <span style={styles.outcomeEquipo}>
  {equipo === "home" ? "1" : equipo === "away" ? "2" : equipo === "draw" ? "X" : equipo}
</span>
                                        <span style={styles.outcomeCuota}>{cuota}</span>
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              ))}
                            </div>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : pestana === "dutcher3" ? (
        <div style={styles.tableWrapper}>
          <p style={{ color: "#aaa", fontSize: "0.85rem", marginBottom: "0.5rem" }}>
            {dutcher3Filtradas.length} partidos — stake total de referencia: 100€
          </p>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Beneficio</th>
                <th style={styles.th}>Fecha</th>
                <th style={styles.th}>Partido</th>
                <th style={styles.th}>1 (local)</th>
                <th style={styles.th}>X (empate)</th>
                <th style={styles.th}>2 (visitante)</th>
                <th style={styles.th}>Retorno</th>
              </tr>
            </thead>
            <tbody>
              {dutcher3Filtradas.map((o, i) => (
                <tr key={i} style={{ background: o.beneficio_pct > 0 ? "rgba(46,204,113,0.05)" : "rgba(231,76,60,0.03)", cursor: "pointer" }}
                  onClick={() => setDutcher3Seleccionada(o)}>
                  <td style={{ ...styles.td, textAlign: "center" }}>
                    <span style={{ color: getMargenColor(o.beneficio_pct), fontWeight: "bold", fontSize: "1rem" }}>
                      {o.beneficio_pct > 0 ? "+" : ""}{o.beneficio_pct}%
                    </span>
                    <div style={{ fontSize: "0.8rem", color: getMargenColor(o.beneficio_pct) }}>
                      {o.beneficio_neto > 0 ? "+" : ""}{o.beneficio_neto}€
                    </div>
                  </td>
                  <td style={{ ...styles.td, fontSize: "0.85rem", color: "#aaa", whiteSpace: "nowrap" }}>{formatFecha(o.commence_time)}</td>
                  <td style={styles.td}>
                    <div style={{ fontSize: "0.8rem", color: "#aaa" }}>{o.competicion}</div>
                    <div>{o.partido}</div>
                  </td>
                  <td style={styles.td}>
                    <div style={{ fontWeight: "bold", color: "#2ecc71" }}>{o.outcome_1.cuota}</div>
                    <div style={{ fontSize: "0.8rem", color: "#aaa" }}>{o.outcome_1.bookie}</div>
                    <div style={{ fontSize: "0.8rem", color: "#646cff" }}>{o.outcome_1.stake}€</div>
                  </td>
                  <td style={styles.td}>
                    <div style={{ fontWeight: "bold", color: "#2ecc71" }}>{o.outcome_x.cuota}</div>
                    <div style={{ fontSize: "0.8rem", color: "#aaa" }}>{o.outcome_x.bookie}</div>
                    <div style={{ fontSize: "0.8rem", color: "#646cff" }}>{o.outcome_x.stake}€</div>
                  </td>
                  <td style={styles.td}>
                    <div style={{ fontWeight: "bold", color: "#2ecc71" }}>{o.outcome_2.cuota}</div>
                    <div style={{ fontSize: "0.8rem", color: "#aaa" }}>{o.outcome_2.bookie}</div>
                    <div style={{ fontSize: "0.8rem", color: "#646cff" }}>{o.outcome_2.stake}€</div>
                  </td>
                  <td style={{ ...styles.td, fontWeight: "bold", color: o.beneficio_neto > 0 ? "#2ecc71" : "#aaa" }}>
                    {o.retorno}€
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* LEDGER */
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <p style={{ color: "#aaa", margin: 0 }}>{bets.length} apuestas registradas</p>
            <div style={{
              background: totalNeto >= 0 ? "rgba(46,204,113,0.1)" : "rgba(231,76,60,0.1)",
              border: `1px solid ${totalNeto >= 0 ? "#2ecc71" : "#e74c3c"}`,
              borderRadius: "8px", padding: "0.5rem 1rem",
            }}>
              <span style={{ color: "#aaa", fontSize: "0.85rem" }}>P&L Total: </span>
              <span style={{ color: totalNeto >= 0 ? "#2ecc71" : "#e74c3c", fontWeight: "bold", fontSize: "1.1rem" }}>
                {totalNeto >= 0 ? "+" : ""}{totalNeto.toFixed(2)}€
              </span>
            </div>
          </div>
          {bets.length === 0 ? (
            <p style={{ color: "#aaa", textAlign: "center", marginTop: "3rem" }}>
              No tienes apuestas registradas. Ve a 🎯 Matching y guarda una apuesta.
            </p>
          ) : (
            <div style={styles.tableWrapper}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>Fecha registro</th>
                    <th style={styles.th}>Tipo</th>
                    <th style={styles.th}>Notas</th>
                    <th style={styles.th}>Partido / Outcome</th>
                    <th style={styles.th}>Fecha evento</th>
                    <th style={styles.th}>Bookie</th>
                    <th style={styles.th}>Back</th>
                    <th style={styles.th}>Lay</th>
                    <th style={styles.th}>Stake</th>
                    <th style={styles.th}>Lay stake</th>
                    <th style={styles.th}>Resultado</th>
                    <th style={styles.th}>Estado</th>
                    <th style={styles.th}>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {bets.map(bet => (
                    <FilaLedger key={bet.id} bet={bet} onUpdate={updateBet} onDelete={deleteBet} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  loginPage: { background: "#1a1a1a", minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" },
  loginBox: { display: "flex", flexDirection: "column", gap: "0.75rem", background: "#2a2a2a", padding: "2rem", borderRadius: "12px", minWidth: "300px" },
  title: { margin: 0, color: "white", fontSize: "1.8rem" },
  input: { padding: "0.6rem", borderRadius: "6px", border: "1px solid #444", background: "#1a1a1a", color: "white", fontSize: "1rem" },
  btnPrimary: { padding: "0.6rem", background: "#646cff", color: "white", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: "bold" },
  page: { background: "#1a1a1a", minHeight: "100vh", color: "white", padding: "1rem 2rem" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", borderBottom: "1px solid #333", paddingBottom: "1rem" },
  tabs: { display: "flex", gap: "0.5rem" },
  tab: { background: "transparent", color: "#aaa", border: "1px solid #333", borderRadius: "6px", padding: "0.4rem 1rem", cursor: "pointer", fontSize: "0.9rem" },
  tabActive: { background: "#2a2a2a", color: "white", borderColor: "#646cff" },
  btnSync: { background: "#2ecc71", color: "white", border: "none", borderRadius: "6px", padding: "0.5rem 1rem", cursor: "pointer", fontWeight: "bold" },
  btnLogout: { background: "#444", color: "white", border: "none", borderRadius: "6px", padding: "0.5rem 1rem", cursor: "pointer" },
  btnVista: { color: "white", border: "none", borderRadius: "6px", padding: "0.4rem 0.8rem", cursor: "pointer", fontSize: "0.85rem" },
  btnCerrar: { background: "transparent", color: "#aaa", border: "none", fontSize: "1.2rem", cursor: "pointer", padding: "0.2rem 0.5rem" },
  syncMsg: { background: "#2a2a2a", padding: "0.5rem 1rem", borderRadius: "6px", marginBottom: "1rem" },
  filtros: { display: "flex", gap: "1rem", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap" },
  select: { padding: "0.5rem", borderRadius: "6px", border: "1px solid #444", background: "#2a2a2a", color: "white", fontSize: "0.9rem" },
  tableWrapper: { overflowX: "auto" },
  table: { width: "100%", borderCollapse: "collapse" },
  th: { background: "#2a2a2a", padding: "0.75rem 1rem", textAlign: "left", borderBottom: "2px solid #444", color: "#aaa", fontSize: "0.85rem", textTransform: "uppercase" },
  td: { padding: "0.75rem 1rem", verticalAlign: "top", borderBottom: "1px solid #2a2a2a" },
  trEven: { background: "#1e1e1e" },
  trOdd: { background: "#222" },
  mercadoBadge: { background: "#2a2a2a", border: "1px solid #444", borderRadius: "4px", padding: "0.2rem 0.5rem", fontSize: "0.8rem" },
  bookieBadge: { background: "#2a2a2a", border: "1px solid #444", borderRadius: "4px", padding: "0.2rem 0.5rem", fontSize: "0.8rem", whiteSpace: "nowrap" },
  bookieCard: { background: "#2a2a2a", border: "1px solid #333", borderRadius: "8px", padding: "0.6rem 0.8rem" },
  mercadoLabel: { fontSize: "0.75rem", color: "#aaa", textTransform: "uppercase", letterSpacing: "0.05em", display: "block", marginBottom: "0.3rem" },
  outcomesRow: { display: "flex", gap: "0.5rem", flexWrap: "wrap" },
  outcomeBox: { background: "#1a1a1a", border: "1px solid #444", borderRadius: "6px", padding: "0.3rem 0.6rem", display: "flex", flexDirection: "column", alignItems: "center", minWidth: "80px" },
  outcomeEquipo: { fontSize: "0.75rem", color: "#aaa", marginBottom: "0.1rem" },
  outcomeCuota: { fontSize: "1rem", fontWeight: "bold", color: "#2ecc71" },
  modalOverlay: { position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 },
  modalBox: { background: "#2a2a2a", borderRadius: "12px", padding: "1.5rem", width: "100%", maxWidth: "600px", border: "1px solid #444" },
  modalHeader: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.5rem", borderBottom: "1px solid #333", paddingBottom: "1rem" },
  modalGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" },
  modalField: { display: "flex", flexDirection: "column", gap: "0.4rem" },
  modalLabel: { color: "#aaa", fontSize: "0.85rem" },
  modalInput: { padding: "0.6rem", borderRadius: "6px", border: "1px solid #444", background: "#1a1a1a", color: "white", fontSize: "1.1rem", fontWeight: "bold" },
  resultadosGrid: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.75rem" },
  resultadoBox: { background: "#1a1a1a", border: "1px solid #333", borderRadius: "8px", padding: "0.75rem", display: "flex", flexDirection: "column", alignItems: "center", gap: "0.3rem" },
  resultadoLabel: { color: "#aaa", fontSize: "0.75rem", textAlign: "center" },
  resultadoValor: { fontWeight: "bold", fontSize: "1.1rem", color: "white" },
};