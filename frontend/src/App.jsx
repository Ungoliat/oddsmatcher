import { useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL;

export default function App() {
  const [token, setToken] = useState("");
  const [events, setEvents] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const loadEvents = async () => {
    if (!token) {
      setError("Pega un token JWT primero");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_URL}/events`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data = await res.json();
      setEvents(data.events || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24, fontFamily: "Arial" }}>
      <h1>Oddsmatcher – Events</h1>

      <div style={{ marginBottom: 16 }}>
        <input
          type="text"
          placeholder="Pega aquí tu token JWT"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          style={{ width: "70%", padding: 8 }}
        />
        <button onClick={loadEvents} style={{ marginLeft: 8 }}>
          Cargar eventos
        </button>
      </div>

      {loading && <p>Cargando…</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <table border="1" cellPadding="6">
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
          {events.map((e, i) => (
            <tr key={i}>
              <td>{e.bookie}</td>
              <td>{e.competicion}</td>
              <td>{e.partido}</td>
              <td>
                {Array.isArray(e.mercados)
                  ? e.mercados.join(", ")
                  : e.mercados}
              </td>
              <td>{e.deporte}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
