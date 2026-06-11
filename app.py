import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone
import time

# ─── Config ───────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Copa do Mundo 2026 🏆",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "https://worldcup26.ir/get"

# ─── Mapeamento completo por código ISO ───────────────────────────────────────
# Bandeira via unicode regional indicators (funciona em qualquer OS moderno)
def code_to_flag(code: str) -> str:
    """Converte código ISO 3166-1 alpha-2 em emoji de bandeira."""
    if not code or len(code) < 2:
        return "🏳️"
    c = code.upper()[:2]
    # Casos especiais
    special = {
        "SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
        "WAL": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
        "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    }
    if code.upper() in special:
        return special[code.upper()]
    try:
        return chr(0x1F1E6 + ord(c[0]) - ord('A')) + chr(0x1F1E6 + ord(c[1]) - ord('A'))
    except Exception:
        return "🏳️"

# Nome EN → código ISO + nome PT
TEAM_MAP = {
    # Grupo A
    "Mexico": ("MX", "México"), "South Africa": ("ZA", "África do Sul"),
    "South Korea": ("KR", "Coreia do Sul"), "Korea Republic": ("KR", "Coreia do Sul"),
    "Czech Republic": ("CZ", "Rep. Tcheca"), "Czechia": ("CZ", "Rep. Tcheca"),
    # Grupo B
    "Canada": ("CA", "Canadá"), "Qatar": ("QA", "Catar"),
    "Switzerland": ("CH", "Suíça"), "Italy": ("IT", "Itália"),
    # Grupo C
    "Brazil": ("BR", "Brasil"), "Morocco": ("MA", "Marrocos"),
    "Haiti": ("HT", "Haiti"), "Scotland": ("SCO", "Escócia"),
    # Grupo D
    "USA": ("US", "Estados Unidos"), "United States": ("US", "Estados Unidos"),
    "Paraguay": ("PY", "Paraguai"), "Australia": ("AU", "Austrália"),
    "Turkey": ("TR", "Turquia"),
    # Grupo E
    "Germany": ("DE", "Alemanha"), "Curacao": ("CW", "Curaçao"),
    "Ivory Coast": ("CI", "Costa do Marfim"), "Côte d'Ivoire": ("CI", "Costa do Marfim"),
    "Ecuador": ("EC", "Equador"),
    # Grupo F
    "Netherlands": ("NL", "Holanda"), "Japan": ("JP", "Japão"),
    "Tunisia": ("TN", "Tunísia"), "Ukraine": ("UA", "Ucrânia"),
    "Sweden": ("SE", "Suécia"), "Poland": ("PL", "Polônia"),
    "Albania": ("AL", "Albânia"),
    # Grupo G
    "Belgium": ("BE", "Bélgica"), "Egypt": ("EG", "Egito"),
    "Iran": ("IR", "Irã"), "New Zealand": ("NZ", "Nova Zelândia"),
    # Grupo H
    "Spain": ("ES", "Espanha"), "Cape Verde": ("CV", "Cabo Verde"),
    "Saudi Arabia": ("SA", "Arábia Saudita"), "Uruguay": ("UY", "Uruguai"),
    # Grupo I
    "France": ("FR", "França"), "Senegal": ("SN", "Senegal"),
    "Norway": ("NO", "Noruega"), "Iraq": ("IQ", "Iraque"),
    "Bolivia": ("BO", "Bolívia"), "Suriname": ("SR", "Suriname"),
    # Grupo J
    "Argentina": ("AR", "Argentina"), "Algeria": ("DZ", "Argélia"),
    "Austria": ("AT", "Áustria"), "Jordan": ("JO", "Jordânia"),
    # Grupo K
    "Portugal": ("PT", "Portugal"), "Uzbekistan": ("UZ", "Uzbequistão"),
    "Colombia": ("CO", "Colômbia"),
    "DR Congo": ("CD", "RD Congo"), "Jamaica": ("JM", "Jamaica"),
    "New Caledonia": ("NC", "Nova Caledônia"),
    # Grupo L
    "England": ("ENG", "Inglaterra"), "Croatia": ("HR", "Croácia"),
    "Ghana": ("GH", "Gana"), "Panama": ("PA", "Panamá"),
    # Outros
    "Denmark": ("DK", "Dinamarca"), "Ireland": ("IE", "Irlanda"),
    "Wales": ("WAL", "País de Gales"), "Bosnia": ("BA", "Bósnia"),
    "Bosnia and Herzegovina": ("BA", "Bósnia e Herzegovina"),
    "Romania": ("RO", "Romênia"), "Slovakia": ("SK", "Eslováquia"),
    "Kosovo": ("XK", "Kosovo"), "Northern Ireland": ("GB", "Irlanda do Norte"),
    "North Macedonia": ("MK", "Macedônia do Norte"),
}

def resolve_team(raw) -> tuple[str, str]:
    """Retorna (bandeira_emoji, nome_pt) a partir de qualquer formato da API."""
    if isinstance(raw, dict):
        # Tentar pegar pelo code primeiro
        code = raw.get("code") or raw.get("country_code") or ""
        name_en = raw.get("en_name") or raw.get("name") or raw.get("country", "")
    else:
        code = ""
        name_en = str(raw) if raw else ""

    name_en = name_en.strip()

    # 1) Lookup pelo nome EN
    if name_en in TEAM_MAP:
        iso, name_pt = TEAM_MAP[name_en]
        return code_to_flag(iso), name_pt

    # 2) Lookup parcial
    for k, (iso, name_pt) in TEAM_MAP.items():
        if k.lower() in name_en.lower() or name_en.lower() in k.lower():
            return code_to_flag(iso), name_pt

    # 3) Fallback pelo code
    if code and len(code) == 2:
        return code_to_flag(code), name_en

    return "🏳️", name_en or "?"

GRUPOS_PT = {
    "A": [("MX","México"),("ZA","África do Sul"),("KR","Coreia do Sul"),("CZ","Rep. Tcheca")],
    "B": [("CA","Canadá"),("QA","Catar"),("CH","Suíça"),("IT","Europa A")],
    "C": [("BR","Brasil"),("MA","Marrocos"),("HT","Haiti"),("SCO","Escócia")],
    "D": [("US","Estados Unidos"),("PY","Paraguai"),("AU","Austrália"),("TR","Europa C")],
    "E": [("DE","Alemanha"),("CW","Curaçao"),("CI","Costa do Marfim"),("EC","Equador")],
    "F": [("NL","Holanda"),("JP","Japão"),("TN","Tunísia"),("UA","Europa B")],
    "G": [("BE","Bélgica"),("EG","Egito"),("IR","Irã"),("NZ","Nova Zelândia")],
    "H": [("ES","Espanha"),("CV","Cabo Verde"),("SA","Arábia Saudita"),("UY","Uruguai")],
    "I": [("FR","França"),("SN","Senegal"),("NO","Noruega"),("IQ","Repescagem 2")],
    "J": [("AR","Argentina"),("DZ","Argélia"),("AT","Áustria"),("JO","Jordânia")],
    "K": [("PT","Portugal"),("UZ","Uzbequistão"),("CO","Colômbia"),("CD","Repescagem 1")],
    "L": [("ENG","Inglaterra"),("HR","Croácia"),("GH","Gana"),("PA","Panamá")],
}

FASES = {
    "group": "Fase de Grupos", "Group Stage": "Fase de Grupos",
    "round_of_32": "Oitavas (R32)", "Round of 32": "Oitavas (R32)",
    "round_of_16": "Oitavas de Final", "Round of 16": "Oitavas de Final",
    "quarter_finals": "Quartas de Final", "Quarter-finals": "Quartas de Final",
    "semi_finals": "Semifinais", "Semi-finals": "Semifinais",
    "third_place": "3º Lugar",
    "final": "🏆 Final", "Final": "🏆 Final",
}

STATUS_PT = {
    "scheduled": "🕐 Agendado",
    "in_progress": "🔴 AO VIVO",
    "live": "🔴 AO VIVO",
    "finished": "✅ Encerrado",
    "halftime": "⏸️ Intervalo",
    "FT": "✅ Encerrado",
    "NS": "🕐 Agendado",
    "1H": "🔴 AO VIVO", "2H": "🔴 AO VIVO",
    "HT": "⏸️ Intervalo",
}

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .match-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border: 1px solid #e94560;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    color: white;
  }
  .match-live {
    border-color: #ff4444 !important;
    box-shadow: 0 0 14px rgba(255,68,68,0.5);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%,100% { box-shadow: 0 0 14px rgba(255,68,68,0.4); }
    50%      { box-shadow: 0 0 28px rgba(255,68,68,0.9); }
  }
  .brasil-card { border-color: #009c3b !important; box-shadow: 0 0 10px rgba(0,156,59,0.3); }
  .score-num   { font-size: 2.2em; font-weight: 900; color: #f5a623; }
  .vs-text     { font-size: 1em; color: #888; }
  .team-flag   { font-size: 2em; }
  .team-name   { font-size: 0.95em; font-weight: 600; margin-top: 4px; }
  .match-meta  { font-size: 0.78em; color: #aaa; text-align: center; margin-top: 8px; }
  .grp-header  { background:#e94560; color:white; padding:6px 14px; border-radius:8px;
                  font-weight:bold; text-align:center; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

# ─── API helpers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_games():
    try:
        r = requests.get(f"{API_BASE}/games", timeout=10,
                         headers={"User-Agent": "Mozilla/5.0 Copa2026App/1.0"})
        if r.status_code == 200:
            d = r.json()
            return d if isinstance(d, list) else d.get("games", [])
    except Exception:
        pass
    return []

@st.cache_data(ttl=120)
def fetch_groups():
    try:
        r = requests.get(f"{API_BASE}/groups", timeout=10,
                         headers={"User-Agent": "Mozilla/5.0 Copa2026App/1.0"})
        if r.status_code == 200:
            d = r.json()
            return d if isinstance(d, list) else d.get("groups", [])
    except Exception:
        pass
    return []

def parse_dt(s):
    if not s:
        return None
    for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc).astimezone()
        except ValueError:
            continue
    return None

def is_brasil_game(home_raw, away_raw):
    def check(raw):
        s = str(raw).lower()
        return "brazil" in s or "brasil" in s or '"br"' in s
    return check(home_raw) or check(away_raw)

def render_card(m):
    home_raw = m.get("home_team") or m.get("home_team_name", "?")
    away_raw = m.get("away_team") or m.get("away_team_name", "?")

    hflag, hname = resolve_team(home_raw)
    aflag, aname = resolve_team(away_raw)

    hs = m.get("home_score", m.get("home_goals"))
    as_ = m.get("away_score", m.get("away_goals"))
    status = str(m.get("status", "scheduled"))
    stadium = m.get("stadium") or m.get("location", "")
    if isinstance(stadium, dict):
        stadium = stadium.get("name", stadium.get("city", ""))
    dt = parse_dt(m.get("datetime") or m.get("kickoff_utc") or m.get("date"))
    phase_raw = m.get("stage_name") or m.get("round") or m.get("stage") or "group"
    phase = FASES.get(phase_raw, phase_raw)
    group = m.get("group", "")
    minute = m.get("time") or m.get("minute") or ""

    live     = status in ("in_progress", "live", "halftime", "1H", "2H", "HT")
    finished = status in ("finished", "FT")
    brasil   = is_brasil_game(home_raw, away_raw)

    css = "match-card"
    if live:   css += " match-live"
    if brasil: css += " brasil-card"

    # Score
    if hs is not None and as_ is not None:
        score_html = f"<span class='score-num'>{hs} — {as_}</span>"
    elif live:
        score_html = "<span class='score-num' style='color:#ff4444'>⚽ ⚽</span>"
    else:
        score_html = "<span class='vs-text'>vs</span>"

    status_label = STATUS_PT.get(status, status)
    min_str = f" {minute}'" if minute and live else ""
    time_str = dt.strftime("%d/%m %H:%M") if dt else ""
    meta = " · ".join(filter(None, [stadium, time_str]))

    st.markdown(f"""
    <div class="{css}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <small style="color:#aaa">{phase}{' · Grupo '+group if group else ''}</small>
        <small>{status_label}{min_str}</small>
      </div>
      <div style="display:grid;grid-template-columns:1fr 90px 1fr;align-items:center;gap:6px;text-align:center">
        <div>
          <div class="team-flag">{hflag}</div>
          <div class="team-name">{hname}</div>
        </div>
        <div style="text-align:center">{score_html}</div>
        <div>
          <div class="team-flag">{aflag}</div>
          <div class="team-name">{aname}</div>
        </div>
      </div>
      <div class="match-meta">{meta}</div>
    </div>
    """, unsafe_allow_html=True)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Copa 2026")
    st.markdown("🇧🇷 **Grupo C** — Brasil, Marrocos, Haiti, Escócia")
    st.divider()
    pagina = st.radio("Página", [
        "🔴 Ao Vivo & Hoje",
        "🇧🇷 Jogos do Brasil",
        "🗓️ Todos os Jogos",
        "🏅 Classificação",
        "📊 Grupos",
    ])
    st.divider()
    auto = st.toggle("Auto-refresh 60s", value=False)
    if st.button("🔄 Atualizar agora"):
        st.cache_data.clear()
        st.rerun()
    st.caption("API: worldcup26.ir  \n11 Jun – 19 Jul 2026")

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 🏆 Copa do Mundo FIFA 2026")
st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if auto:
    time.sleep(60)
    st.rerun()

games  = fetch_games()
today  = datetime.now().date()

def sort_key(g):
    return g.get("datetime") or g.get("kickoff_utc") or g.get("date") or ""

# ══════════════════════════════════════════════════════════════════════════════
if pagina == "🔴 Ao Vivo & Hoje":
    live_games = [g for g in games if str(g.get("status","")) in
                  ("in_progress","live","halftime","1H","2H","HT")]
    st.subheader("🔴 Ao Vivo")
    if live_games:
        for g in live_games: render_card(g)
    else:
        st.info("Nenhum jogo ao vivo agora.")

    st.subheader("📅 Jogos de Hoje")
    today_games = [g for g in games if (dt := parse_dt(
        g.get("datetime") or g.get("kickoff_utc") or g.get("date"))) and dt.date() == today]
    if today_games:
        for g in sorted(today_games, key=sort_key): render_card(g)
    else:
        st.info("Nenhum jogo encontrado para hoje." if games else "API indisponível — tente atualizar.")

# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🇧🇷 Jogos do Brasil":
    st.subheader("🇧🇷 Jogos do Brasil — Grupo C")
    br = [g for g in games if is_brasil_game(
        g.get("home_team") or g.get("home_team_name",""),
        g.get("away_team") or g.get("away_team_name",""))]
    if br:
        for g in sorted(br, key=sort_key): render_card(g)
    else:
        st.info("Dados ainda não disponíveis na API. Jogos confirmados:")
        df = pd.DataFrame([
            {"Data":"13/06 Sex","Hora (BRT)":"16h","Adversário":"🇲🇦 Marrocos","Grupo":"C","Cidade":"Atlanta"},
            {"Data":"19/06 Qui","Hora (BRT)":"16h","Adversário":"🇭🇹 Haiti",  "Grupo":"C","Cidade":"Los Angeles"},
            {"Data":"24/06 Ter","Hora (BRT)":"16h","Adversário":"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escócia","Grupo":"C","Cidade":"Dallas"},
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🗓️ Todos os Jogos":
    st.subheader("🗓️ Calendário Completo")
    if not games:
        st.warning("API fora do ar. Tente atualizar.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            grp_f = st.selectbox("Grupo", ["Todos"] + list("ABCDEFGHIJKL"))
        with c2:
            sta_f = st.selectbox("Status", ["Todos","Agendado","Ao Vivo","Encerrado"])
        with c3:
            fas_f = st.selectbox("Fase", ["Todas","Fase de Grupos","Mata-mata"])

        fil = games[:]
        if grp_f != "Todos":
            fil = [g for g in fil if str(g.get("group","")).upper() == grp_f]
        if sta_f == "Ao Vivo":
            fil = [g for g in fil if str(g.get("status","")) in ("in_progress","live","halftime","1H","2H","HT")]
        elif sta_f == "Encerrado":
            fil = [g for g in fil if str(g.get("status","")) in ("finished","FT")]
        elif sta_f == "Agendado":
            fil = [g for g in fil if str(g.get("status","")) in ("scheduled","NS")]
        if fas_f == "Fase de Grupos":
            fil = [g for g in fil if (g.get("stage_name") or g.get("round","group")) in ("group","Group Stage")]
        elif fas_f == "Mata-mata":
            fil = [g for g in fil if (g.get("stage_name") or g.get("round","group")) not in ("group","Group Stage")]

        st.caption(f"{len(fil)} jogos encontrados")
        for g in sorted(fil, key=sort_key): render_card(g)

# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏅 Classificação":
    st.subheader("🏅 Classificação por Grupo")
    gdata = fetch_groups()
    if gdata:
        for grp in gdata:
            gname = grp.get("name") or grp.get("group","?")
            standings = grp.get("standings") or grp.get("teams",[])
            if not standings: continue
            st.markdown(f"<div class='grp-header'>Grupo {gname}</div>", unsafe_allow_html=True)
            rows = []
            for i, t in enumerate(standings):
                flag_e, name_pt = resolve_team(t.get("team") or t.get("name") or t)
                rows.append({
                    "#": i+1, "Seleção": f"{flag_e} {name_pt}",
                    "J": t.get("played",0), "V": t.get("w",0),
                    "E": t.get("d",0),      "D": t.get("l",0),
                    "GP": t.get("gf",0),    "GC": t.get("ga",0),
                    "SG": t.get("gd",0),    "Pts": t.get("points",0),
                })
            df = pd.DataFrame(rows)
            def hl(row):
                return ["background:rgba(0,156,59,.18)"]*len(row) if "Brasil" in str(row["Seleção"]) else [""]*len(row)
            st.dataframe(df.style.apply(hl,axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("Classificação ainda não disponível.")
        for grp, teams in GRUPOS_PT.items():
            st.markdown(f"<div class='grp-header'>Grupo {grp}</div>", unsafe_allow_html=True)
            df = pd.DataFrame({
                "Seleção":[f"{code_to_flag(iso)} {name}" for iso,name in teams],
                "J":[0]*4,"V":[0]*4,"E":[0]*4,"D":[0]*4,"Pts":[0]*4
            })
            st.dataframe(df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
elif pagina == "📊 Grupos":
    st.subheader("📊 Grupos da Copa do Mundo 2026")
    st.caption("48 seleções · 12 grupos de 4 · Os 2 primeiros + 8 melhores 3ºs avançam")
    cols = st.columns(3)
    for i, (grp, teams) in enumerate(GRUPOS_PT.items()):
        with cols[i % 3]:
            st.markdown(f"<div class='grp-header'>Grupo {grp}</div>", unsafe_allow_html=True)
            for iso, name in teams:
                em = code_to_flag(iso)
                style = " style='background:rgba(0,156,59,.15);padding:2px 6px;border-radius:4px'" if name == "Brasil" else ""
                st.markdown(f"<div{style}>{em} {name}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
