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

GRUPOS = {
    "A": ["México", "África do Sul", "Coreia do Sul", "Europa D"],
    "B": ["Canadá", "Catar", "Suíça", "Europa A"],
    "C": ["Brasil", "Marrocos", "Haiti", "Escócia"],
    "D": ["Estados Unidos", "Paraguai", "Austrália", "Europa C"],
    "E": ["Alemanha", "Curaçao", "Costa do Marfim", "Equador"],
    "F": ["Holanda", "Japão", "Tunísia", "Europa B"],
    "G": ["Bélgica", "Egito", "Irã", "Nova Zelândia"],
    "H": ["Espanha", "Cabo Verde", "Arábia Saudita", "Uruguai"],
    "I": ["França", "Senegal", "Noruega", "Repescagem 2"],
    "J": ["Argentina", "Argélia", "Áustria", "Jordânia"],
    "K": ["Portugal", "Uzbequistão", "Colômbia", "Repescagem 1"],
    "L": ["Inglaterra", "Croácia", "Gana", "Panamá"],
}

BANDEIRAS = {
    "Brasil": "🇧🇷", "Argentina": "🇦🇷", "França": "🇫🇷", "Alemanha": "🇩🇪",
    "Espanha": "🇪🇸", "Portugal": "🇵🇹", "Inglaterra": "🇬🇧", "Holanda": "🇳🇱",
    "Bélgica": "🇧🇪", "Uruguai": "🇺🇾", "México": "🇲🇽", "Canadá": "🇨🇦",
    "Estados Unidos": "🇺🇸", "Japão": "🇯🇵", "Coreia do Sul": "🇰🇷",
    "Marrocos": "🇲🇦", "Senegal": "🇸🇳", "Egito": "🇪🇬", "Catar": "🇶🇦",
    "Arábia Saudita": "🇸🇦", "Irã": "🇮🇷", "Austrália": "🇦🇺",
    "Noruega": "🇳🇴", "Suíça": "🇨🇭", "Croácia": "🇭🇷", "Colômbia": "🇨🇴",
    "Equador": "🇪🇨", "Paraguai": "🇵🇾", "África do Sul": "🇿🇦",
    "Tunísia": "🇹🇳", "Gana": "🇬🇭", "Escócia": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "Panamá": "🇵🇦",
    "Cabo Verde": "🇨🇻", "Nova Zelândia": "🇳🇿", "Argélia": "🇩🇿",
    "Áustria": "🇦🇹", "Jordânia": "🇯🇴", "Costa do Marfim": "🇨🇮",
    "Haiti": "🇭🇹", "Curaçao": "🇨🇼", "Uzbequistão": "🇺🇿",
}

STATUS_PT = {
    "scheduled": "🕐 Agendado",
    "in_progress": "🔴 AO VIVO",
    "live": "🔴 AO VIVO",
    "finished": "✅ Encerrado",
    "halftime": "⏸️ Intervalo",
}

FASES = {
    "group": "Fase de Grupos",
    "round_of_32": "Oitavas de Final",
    "round_of_16": "Oitavas de Final",
    "quarter_finals": "Quartas de Final",
    "semi_finals": "Semifinais",
    "third_place": "3º Lugar",
    "final": "🏆 Final",
}

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  .match-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border: 1px solid #e94560;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 12px;
    color: white;
  }
  .match-live {
    border-color: #ff4444;
    box-shadow: 0 0 12px rgba(255,68,68,0.4);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 12px rgba(255,68,68,0.4); }
    50% { box-shadow: 0 0 24px rgba(255,68,68,0.8); }
  }
  .score-box {
    font-size: 2em;
    font-weight: bold;
    text-align: center;
    color: #f5a623;
  }
  .team-name {
    font-size: 1.1em;
    font-weight: 600;
    text-align: center;
  }
  .match-info {
    font-size: 0.8em;
    color: #aaa;
    text-align: center;
    margin-top: 4px;
  }
  .group-header {
    background: #e94560;
    color: white;
    padding: 8px 16px;
    border-radius: 8px;
    font-weight: bold;
    font-size: 1.1em;
    margin-bottom: 8px;
    text-align: center;
  }
  .brasil-highlight {
    border: 2px solid #009c3b !important;
    box-shadow: 0 0 10px rgba(0,156,59,0.4) !important;
  }
  .status-live {
    background: #ff4444;
    color: white;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.8em;
    font-weight: bold;
  }
  .status-done {
    background: #333;
    color: #aaa;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.8em;
  }
</style>
""", unsafe_allow_html=True)


# ─── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_games():
    try:
        r = requests.get(f"{API_BASE}/games", timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else data.get("games", [])
    except Exception:
        pass
    return []

@st.cache_data(ttl=120)
def fetch_groups():
    try:
        r = requests.get(f"{API_BASE}/groups", timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else data.get("groups", [])
    except Exception:
        pass
    return []

@st.cache_data(ttl=120)
def fetch_teams():
    try:
        r = requests.get(f"{API_BASE}/teams", timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data if isinstance(data, list) else data.get("teams", [])
    except Exception:
        pass
    return []


def parse_date(dt_str):
    if not dt_str:
        return None
    try:
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
            try:
                dt = datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc)
                return dt.astimezone()
            except ValueError:
                continue
    except Exception:
        pass
    return None


def flag(team_name):
    if not team_name:
        return "🏳️"
    for k, v in BANDEIRAS.items():
        if k.lower() in team_name.lower() or team_name.lower() in k.lower():
            return v
    return "🏳️"


def is_brasil(home, away):
    return "brasil" in str(home).lower() or "brazil" in str(home).lower() or \
           "brasil" in str(away).lower() or "brazil" in str(away).lower()


def render_match_card(m):
    home = m.get("home_team") or m.get("home_team_name", "?")
    away = m.get("away_team") or m.get("away_team_name", "?")
    if isinstance(home, dict):
        home = home.get("name", home.get("en_name", "?"))
    if isinstance(away, dict):
        away = away.get("name", away.get("en_name", "?"))

    home_score = m.get("home_score", m.get("home_goals"))
    away_score = m.get("away_score", m.get("away_goals"))
    status = m.get("status", "scheduled")
    stadium = m.get("stadium") or m.get("location", "")
    if isinstance(stadium, dict):
        stadium = stadium.get("name", "")

    dt = parse_date(m.get("datetime") or m.get("kickoff_utc") or m.get("date"))
    phase = FASES.get(m.get("stage_name") or m.get("round", "group"), "Fase de Grupos")
    group = m.get("group", "")

    live = status in ("in_progress", "live", "halftime")
    finished = status == "finished"
    brasil = is_brasil(home, away)

    card_class = "match-card"
    if live:
        card_class += " match-live"
    if brasil:
        card_class += " brasil-highlight"

    score_html = "vs"
    if home_score is not None and away_score is not None:
        score_html = f"<span class='score-box'>{home_score} — {away_score}</span>"
    elif live:
        score_html = "<span class='score-box' style='color:#ff4444'>AO VIVO</span>"

    status_html = STATUS_PT.get(status, status)
    time_str = dt.strftime("%d/%m %H:%M") if dt else ""

    minute = ""
    if live and m.get("time"):
        minute = f" · {m['time']}'"

    st.markdown(f"""
    <div class="{card_class}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <small style="color:#aaa">{phase}{' · Grupo ' + group if group else ''}</small>
        <small>{status_html}{minute}</small>
      </div>
      <div style="display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:8px">
        <div>
          <div class="team-name">{flag(home)} {home}</div>
        </div>
        <div style="min-width:80px">{score_html}</div>
        <div>
          <div class="team-name">{away} {flag(away)}</div>
        </div>
      </div>
      <div class="match-info">{stadium} {'· ' + time_str if time_str else ''}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Copa 2026")
    st.markdown("🇧🇷 **Grupo C** · Brasil, Marrocos, Haiti, Escócia")
    st.markdown("---")

    pagina = st.radio("Navegação", [
        "🔴 Ao Vivo & Hoje",
        "📅 Jogos do Brasil",
        "🗓️ Todos os Jogos",
        "🏅 Classificação",
        "📊 Grupos",
    ])

    st.markdown("---")
    auto_refresh = st.toggle("Auto-refresh (60s)", value=False)
    if st.button("🔄 Atualizar agora"):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.caption("Dados: worldcup26.ir  \nCopa: 11 Jun – 19 Jul 2026")

# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 🏆 Copa do Mundo FIFA 2026")
st.markdown(f"*Atualizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}*")

# Auto refresh
if auto_refresh:
    time.sleep(1)
    st.rerun()

# ─── Pages ────────────────────────────────────────────────────────────────────
games = fetch_games()
today = datetime.now().date()


if pagina == "🔴 Ao Vivo & Hoje":
    st.subheader("🔴 Jogos Ao Vivo")

    live_games = [g for g in games if g.get("status") in ("in_progress", "live", "halftime")]
    if live_games:
        for g in live_games:
            render_match_card(g)
    else:
        st.info("Nenhum jogo ao vivo no momento.")

    st.subheader("📅 Jogos de Hoje")
    today_games = []
    for g in games:
        dt = parse_date(g.get("datetime") or g.get("kickoff_utc") or g.get("date"))
        if dt and dt.date() == today:
            today_games.append(g)

    if today_games:
        for g in sorted(today_games, key=lambda x: x.get("datetime", x.get("kickoff_utc", ""))):
            render_match_card(g)
    else:
        st.info("Nenhum jogo encontrado para hoje.")


elif pagina == "📅 Jogos do Brasil":
    st.subheader("🇧🇷 Jogos do Brasil")

    brasil_games = []
    for g in games:
        home = g.get("home_team") or g.get("home_team_name", "")
        away = g.get("away_team") or g.get("away_team_name", "")
        if isinstance(home, dict): home = home.get("name", "")
        if isinstance(away, dict): away = away.get("name", "")
        if is_brasil(home, away):
            brasil_games.append(g)

    if brasil_games:
        for g in sorted(brasil_games, key=lambda x: x.get("datetime", x.get("kickoff_utc", ""))):
            render_match_card(g)
    else:
        # Fallback: mostrar tabela estática de jogos do Brasil
        st.info("Dados da API não disponíveis. Jogos confirmados do Brasil:")
        jogos_brasil = [
            {"Data": "13/06 (Sex)", "Horário": "16h (BRT)", "Adversário": "🇲🇦 Marrocos", "Fase": "Grupo C", "Local": "Atlanta"},
            {"Data": "19/06 (Qui)", "Horário": "16h (BRT)", "Adversário": "🇭🇹 Haiti", "Fase": "Grupo C", "Local": "Los Angeles"},
            {"Data": "24/06 (Ter)", "Horário": "16h (BRT)", "Adversário": "🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escócia", "Fase": "Grupo C", "Local": "Dallas"},
        ]
        df = pd.DataFrame(jogos_brasil)
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown("""
        **Grupo C — Brasil** 🇧🇷
        - 🇧🇷 Brasil (cabeça de chave)
        - 🇲🇦 Marrocos
        - 🇭🇹 Haiti
        - 🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escócia

        Se avançar como 1º ou 2º → enfrenta adversário do **Grupo F**
        (Holanda, Japão, Tunísia + classificado da Europa)
        """)


elif pagina == "🗓️ Todos os Jogos":
    st.subheader("🗓️ Calendário Completo")

    if not games:
        st.warning("API fora do ar. Tente novamente em instantes.")
    else:
        # Filtros
        col1, col2, col3 = st.columns(3)
        with col1:
            grupo_filtro = st.selectbox("Grupo", ["Todos"] + list("ABCDEFGHIJKL"))
        with col2:
            status_filtro = st.selectbox("Status", ["Todos", "Agendado", "Ao Vivo", "Encerrado"])
        with col3:
            fase_filtro = st.selectbox("Fase", ["Todas", "Fase de Grupos", "Mata-mata"])

        filtered = games
        if grupo_filtro != "Todos":
            filtered = [g for g in filtered if str(g.get("group", "")).upper() == grupo_filtro]
        if status_filtro == "Ao Vivo":
            filtered = [g for g in filtered if g.get("status") in ("in_progress", "live", "halftime")]
        elif status_filtro == "Encerrado":
            filtered = [g for g in filtered if g.get("status") == "finished"]
        elif status_filtro == "Agendado":
            filtered = [g for g in filtered if g.get("status") == "scheduled"]
        if fase_filtro == "Fase de Grupos":
            filtered = [g for g in filtered if g.get("stage_name", g.get("round", "group")) == "group"]
        elif fase_filtro == "Mata-mata":
            filtered = [g for g in filtered if g.get("stage_name", g.get("round", "group")) != "group"]

        st.caption(f"{len(filtered)} jogos encontrados")

        for g in sorted(filtered, key=lambda x: x.get("datetime", x.get("kickoff_utc", ""))):
            render_match_card(g)


elif pagina == "🏅 Classificação":
    st.subheader("🏅 Classificação por Grupo")

    groups_data = fetch_groups()

    if groups_data:
        for grp in groups_data:
            grp_name = grp.get("name") or grp.get("group", "?")
            standings = grp.get("standings") or grp.get("teams", [])

            if not standings:
                continue

            st.markdown(f"<div class='group-header'>Grupo {grp_name}</div>", unsafe_allow_html=True)
            rows = []
            for i, t in enumerate(standings):
                team_name = t.get("team") or t.get("name") or t.get("team_name", "?")
                if isinstance(team_name, dict):
                    team_name = team_name.get("en_name") or team_name.get("name", "?")
                rows.append({
                    "Pos": i + 1,
                    "Seleção": f"{flag(team_name)} {team_name}",
                    "J": t.get("played", t.get("games_played", 0)),
                    "V": t.get("w", t.get("wins", 0)),
                    "E": t.get("d", t.get("draws", 0)),
                    "D": t.get("l", t.get("losses", 0)),
                    "GP": t.get("gf", t.get("goals_for", 0)),
                    "GC": t.get("ga", t.get("goals_against", 0)),
                    "SG": t.get("gd", t.get("goal_difference", 0)),
                    "Pts": t.get("points", 0),
                })

            df = pd.DataFrame(rows)
            # Highlight Brasil
            def highlight_brasil(row):
                if "rasil" in str(row["Seleção"]) or "razil" in str(row["Seleção"]):
                    return ["background-color: rgba(0,156,59,0.2)"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df.style.apply(highlight_brasil, axis=1),
                use_container_width=True,
                hide_index=True,
            )
    else:
        # Fallback: mostrar grupos estáticos
        st.info("Classificação ainda não disponível. Grupos da Copa 2026:")
        for grp, teams in GRUPOS.items():
            st.markdown(f"<div class='group-header'>Grupo {grp}</div>", unsafe_allow_html=True)
            df = pd.DataFrame({
                "Seleção": [f"{flag(t)} {t}" for t in teams],
                "J": [0] * 4, "V": [0] * 4, "E": [0] * 4,
                "D": [0] * 4, "Pts": [0] * 4,
            })
            st.dataframe(df, use_container_width=True, hide_index=True)


elif pagina == "📊 Grupos":
    st.subheader("📊 Grupos da Copa do Mundo 2026")
    st.caption("48 seleções · 12 grupos de 4 · Os 2 primeiros + 8 melhores 3ºs avançam")

    cols = st.columns(3)
    for i, (grp, teams) in enumerate(GRUPOS.items()):
        with cols[i % 3]:
            st.markdown(f"<div class='group-header'>Grupo {grp}</div>", unsafe_allow_html=True)
            for t in teams:
                brasil_style = " style='background:rgba(0,156,59,0.15);padding:2px 6px;border-radius:4px;'" if "Brasil" in t else ""
                st.markdown(f"<div{brasil_style}>{flag(t)} {t}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
  
