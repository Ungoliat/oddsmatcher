## Endpoints Principales
- `POST /admin/sync-all` — sincroniza The Odds API + Betfair + Winamax
- `POST /admin/sync-betfair` — solo Betfair
- `POST /admin/sync-the-odds-api` — solo The Odds API
- `POST /admin/sync-winamax` — solo Winamax ← NUEVO
- `GET /odds/matching?comision=0.02` — oportunidades de matched betting
- `GET /odds/dutcher3` — oportunidades de dutching 3 bandas
- Swagger: `http://localhost:8000/docs` (local) / `http://116.203.119.10:8000/docs` (servidor)

## Ligas Configuradas (The Odds API)
LaLiga, Segunda División, Premier League, Bundesliga, Serie A, Ligue 1, Champions League, Europa League, Conference League, NBA, ATP French Open, WTA French Open, Euroleague

## Ligas Configuradas (Winamax scraper)
Ligue 1, Ligue 2, LaLiga, Segunda División, Premier League, Bundesliga, Serie A, Serie B, Jupiler Pro League, Eredivisie, Liga Portugal, Süper Lig, Champions League, Europa League, Conference League, NBA, Euroleague, ATP Roland Garros, WTA Roland Garros

## Bookies Filtradas (españolas/disponibles)
betsson, williamhill, marathonbet, leovegas_se, onexbet, betfair_ex_eu, winamax_fr, 888sport, casumo, pokerstars, interwetten, tonybet, betway, bwin, bet365

## Lógica de Matching
1. The Odds API provee cuotas back de bookies
2. Betfair provee cuotas lay del exchange
3. Winamax scraper provee cuotas back adicionales
4. `emparejar_partido()` usa fuzzy matching para cruzar partidos entre fuentes
5. Los outcomes de Betfair se mapean al nombre completo usando `partial_ratio` + `startswith`
6. Se calcula rating = (back_stake + resultado_neto) / back_stake * 100
7. Solo se muestran oportunidades con rating entre 85% y 102%

## Filtros Activos en Betfair Provider
- `size >= 10` para back y lay (filtra mercados sin liquidez)
- Ignorar mercados donde todas las cuotas < 1.5 (partidos ya jugados)
- Ignorar mercados sin ninguna cuota lay real

## Normalizer (normalizer.py)
- Usa `thefuzz.token_sort_ratio` para emparejar partidos
- Umbral de 75% para considerar un match válido
- Usa `partial_ratio` adicional para mejorar matching de nombres cortos
- Elimina sufijos: FC, CF, SC, AC, BC, SD, UD, CD
- Normaliza "v" → "vs"

## Scraper Winamax (sync_service_winamax.py)
- Usa Playwright en modo headless (funciona en Linux/VPS)
- Captura datos via WebSocket de Winamax
- Sistema de reintentos (hasta 3 intentos con espera aleatoria)
- Filtra solo partidos de torneos configurados en TORNEOS_INTERES
- Solo guarda cuotas 1X2
- En Windows requiere headless=False (modo visible)
- En Linux/VPS funciona en headless=True

## Sync de Betfair (sync_service_betfair.py)
- Empareja partido de Betfair con partido en DB via fuzzy matching
- Extrae home_team/away_team del partido matcheado
- Mapea nombres cortos de Betfair al nombre completo
- Solo guarda cuotas lay (no back) en DB para Betfair

## Bugs Conocidos / Pendientes
1. **Fuzzy matching nombres español** — Winamax usa nombres en español, otras bookies en inglés — pendiente mejorar
2. **Uvicorn no arranca automáticamente** — pendiente configurar como servicio systemd
3. **Winamax headless inconsistente** — a veces falla el primer intento, el sistema de reintentos lo resuelve
4. **Betfair sync error** — "Expecting value: line 1 column 1" — token expirado, pendiente investigar
5. **Scheduler** — sync automático comentado, se hace manual por ahora

## Arranque en PC Nuevo
```bash
git clone https://github.com/Ungoliat/oddsmatcher.git
cd oddsmatcher/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install rapidfuzz thefuzz playwright
playwright install chromium
# Crear .env con credenciales
uvicorn app.main:app --reload

# Nueva terminal
cd frontend
npm install
npm run dev
```

## Arranque en VPS
```bash
ssh root@116.203.119.10
cd oddsmatcher/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Funcionalidades del Frontend
- **Matching:** tabla de oportunidades ordenadas por rating
- **Eventos:** lista de todos los eventos con cuotas por bookie
- **Mis apuestas (Ledger):** registro de apuestas con P&L
- **Dutcher 3B:** calculadora de dutching a 3 bandas
- **Calculadora:** modal al clicar una oportunidad para calcular stakes
- **Sync API:** botón que llama a `/admin/sync-all`
- Filtros por liga y bookie
- Ajuste de comisión Betfair

## Plan de Scrapers (Tier 1)
1. ✅ Winamax ES — funcionando
2. ⬜ Bwin
3. ⬜ Bet365
4. ⬜ Codere
5. ⬜ William Hill ES
6. ⬜ Sportium
7. ⬜ Retabet
8. ⬜ Marcaapuestas
9. ⬜ Paston
10. ⬜ Enracha
11. ⬜ Yosports