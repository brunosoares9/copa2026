import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from sportscore import SportScoreClient

st.set_page_config(
    page_title="Copa do Mundo 2026 🏆",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRT = timezone(timedelta(hours=-3))

# ──────────────────────────────────────────────────────────────────────────────
# Bandeiras e tradução de times (mantido igual ao original)
# ──────────────────────────────────────────────────────────────────────────────
def code_to_flag(code: str) -> str:
    special = {"SCO":"🏴󠁧󠁢󠁳󠁣󠁴󠁿","WAL":"🏴󠁧󠁢󠁷󠁬󠁳󠁿","ENG":"🏴󠁧󠁢󠁥󠁮󠁧󠁿"}
    if not code: return "🏳️"
    if code.upper() in special: return special[code.upper()]
    c = code.upper()[:2]
    try: return chr(0x1F1E6+ord(c[0])-ord('A'))+chr(0x1F1E6+ord(c[1])-ord('A'))
    except: return "🏳️"

TEAM_MAP = {
    "Mexico":("MX","México"),"South Africa":("ZA","África do Sul"),
    "South Korea":("KR","Coreia do Sul"),"Korea Republic":("KR","Coreia do Sul"),
    "Czech Republic":("CZ","Rep. Tcheca"),"Czechia":("CZ","Rep. Tcheca"),
    "Denmark":("DK","Dinamarca"),"North Macedonia":("MK","Macedônia do Norte"),
    "Ireland":("IE","Irlanda"),"Canada":("CA","Canadá"),"Qatar":("QA","Catar"),
    "Switzerland":("CH","Suíça"),"Italy":("IT","Itália"),
    "Northern Ireland":("GB","Irlanda do Norte"),
    "Wales":("WAL","País de Gales"),"Bosnia and Herzegovina":("BA","Bósnia"),
    "Brazil":("BR","Brasil"),"Morocco":("MA","Marrocos"),
    "Haiti":("HT","Haiti"),"Scotland":("SCO","Escócia"),
    "USA":("US","Estados Unidos"),"United States":("US","Estados Unidos"),
    "Paraguay":("PY","Paraguai"),"Australia":("AU","Austrália"),
    "Turkey":("TR","Turquia"),"Romania":("RO","Romênia"),
    "Slovakia":("SK","Eslováquia"),"Kosovo":("XK","Kosovo"),
    "Germany":("DE","Alemanha"),"Curacao":("CW","Curaçao"),
    "Ivory Coast":("CI","Costa do Marfim"),"Côte d'Ivoire":("CI","Costa do Marfim"),
    "Ecuador":("EC","Equador"),"Netherlands":("NL","Holanda"),
    "Japan":("JP","Japão"),"Tunisia":("TN","Tunísia"),"Ukraine":("UA","Ucrânia"),
    "Sweden":("SE","Suécia"),"Poland":("PL","Polônia"),"Albania":("AL","Albânia"),
    "Belgium":("BE","Bélgica"),"Egypt":("EG","Egito"),
    "Iran":("IR","Irã"),"New Zealand":("NZ","Nova Zelândia"),
    "Spain":("ES","Espanha"),"Cape Verde":("CV","Cabo Verde"),
    "Saudi Arabia":("SA","Arábia Saudita"),"Uruguay":("UY","Uruguai"),
    "France":("FR","França"),"Senegal":("SN","Senegal"),
    "Norway":("NO","Noruega"),"Iraq":("IQ","Iraque"),
    "Bolivia":("BO","Bolívia"),"Suriname":("SR","Suriname"),
    "Argentina":("AR","Argentina"),"Algeria":("DZ","Argélia"),
    "Austria":("AT","Áustria"),"Jordan":("JO","Jordânia"),
    "Portugal":("PT","Portugal"),"Uzbekistan":("UZ","Uzbequistão"),
    "Colombia":("CO","Colômbia"),"DR Congo":("CD","RD Congo"),
    "Jamaica":("JM","Jamaica"),"New Caledonia":("NC","Nova Caledônia"),
    "England":("ENG","Inglaterra"),"Croatia":("HR","Croácia"),
    "Ghana":("GH","Gana"),"Panama":("PA","Panamá"),
}

def resolve(name_en: str) -> tuple:
    if not name_en or name_en in ("null","None","?"): return "🏳️","?"
    n = name_en.strip()
    if n in TEAM_MAP:
        iso,pt = TEAM_MAP[n]; return code_to_flag(iso),pt
    for k,(iso,pt) in TEAM_MAP.items():
        if k.lower() in n.lower() or n.lower() in k.lower():
            return code_to_flag(iso),pt
    return "🏳️", n

# ──────────────────────────────────────────────────────────────────────────────
# Configuração de grupos (para a página "Grupos")
# ──────────────────────────────────────────────────────────────────────────────
GRUPOS_PT = {
    "A":[("MX","México"),("ZA","África do Sul"),("KR","Coreia do Sul"),("CZ","Rep. Tcheca")],
    "B":[("CA","Canadá"),("QA","Catar"),("CH","Suíça"),("IT","Itália")],
    "C":[("BR","Brasil"),("MA","Marrocos"),("HT","Haiti"),("SCO","Escócia")],
    "D":[("US","Estados Unidos"),("PY","Paraguai"),("AU","Austrália"),("TR","Turquia")],
    "E":[("DE","Alemanha"),("CW","Curaçao"),("CI","Costa do Marfim"),("EC","Equador")],
    "F":[("NL","Holanda"),("JP","Japão"),("TN","Tunísia"),("UA","Ucrânia")],
    "G":[("BE","Bélgica"),("EG","Egito"),("IR","Irã"),("NZ","Nova Zelândia")],
    "H":[("ES","Espanha"),("CV","Cabo Verde"),("SA","Arábia Saudita"),("UY","Uruguai")],
    "I":[("FR","França"),("SN","Senegal"),("NO","Noruega"),("IQ","Iraque")],
    "J":[("AR","Argentina"),("DZ","Argélia"),("AT","Áustria"),("JO","Jordânia")],
    "K":[("PT","Portugal"),("UZ","Uzbequistão"),("CO","Colômbia"),("CD","RD Congo")],
    "L":[("ENG","Inglaterra"),("HR","Croácia"),("GH","Gana"),("PA","Panamá")],
}

# ──────────────────────────────────────────────────────────────────────────────
# Busca de dados com SportScore (sem chave)
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_world_cup_data():
    """Retorna lista de jogos da Copa 2026 com placares e status ao vivo."""
    try:
        with SportScoreClient() as client:
            # Busca partidas de futebol (limite 100 para ter todas da Copa)
            matches_data = client.get_matches("football", limit=100)
            all_matches = []
            for m in matches_data.get('data', []):
                comp_name = m.get('competition', {}).get('name', '')
                # Filtra pela Copa do Mundo (ajuste se necessário)
                if 'world cup' in comp_name.lower() or 'worldcup' in comp_name.lower():
                    # Mapeia status
                    status_raw = m.get('status', 'NS')
                    if status_raw == 'FT':
                        status = 'finished'
                    elif status_raw in ('1H', '2H', 'HT'):
                        status = 'live'
                    else:
                        status = 'scheduled'

                    game = {
                        "team1": m.get('home_team', {}).get('name'),
                        "team2": m.get('away_team', {}).get('name'),
                        "home_score": m.get('home_score'),
                        "away_score": m.get('away_score'),
                        "status": status,
                        "datetime": parse_iso_date(m.get('starting_at')),
                        "group": m.get('group', ''),   # pode vir vazio
                        "ground": m.get('venue', {}).get('name', ''),
                    }
                    # Se não tiver grupo, tenta inferir pelo time (usando GRUPOS_PT)
                    if not game['group']:
                        for grp, times in GRUPOS_PT.items():
                            nomes_pt = [nome for _, nome in times]
                            if any(nome in resolve(game['team1'])[1] or nome in resolve(game['team2'])[1] for nome in nomes_pt):
                                game['group'] = grp
                                break
                    all_matches.append(game)
            return all_matches
    except Exception as e:
        st.error(f"Erro ao conectar com a SportScore: {e}")
        return []

def parse_iso_date(date_str):
    if not date_str:
        return None
    try:
        dt_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt_utc.astimezone(BRT)
    except:
        return None

# ──────────────────────────────────────────────────────────────────────────────
# Cálculo da classificação a partir dos jogos (apenas partidas finished)
# ──────────────────────────────────────────────────────────────────────────────
def calc_standings_from_games(games):
    groups = defaultdict(lambda: defaultdict(lambda: {"J":0,"V":0,"E":0,"D":0,"GP":0,"GC":0,"Pts":0}))
    for g in games:
        if g["status"] != "finished" or g["home_score"] is None:
            continue
        t1, t2 = g["team1"], g["team2"]
        g1, g2 = g["home_score"], g["away_score"]
        grp = g.get("group", "")
        if not grp:
            continue
        # Atualiza estatísticas
        groups[grp][t1]["J"] += 1
        groups[grp][t2]["J"] += 1
        groups[grp][t1]["GP"] += g1
        groups[grp][t1]["GC"] += g2
        groups[grp][t2]["GP"] += g2
        groups[grp][t2]["GC"] += g1
        if g1 > g2:
            groups[grp][t1]["V"] += 1
            groups[grp][t1]["Pts"] += 3
            groups[grp][t2]["D"] += 1
        elif g2 > g1:
            groups[grp][t2]["V"] += 1
            groups[grp][t2]["Pts"] += 3
            groups[grp][t1]["D"] += 1
        else:
            groups[grp][t1]["E"] += 1
            groups[grp][t1]["Pts"] += 1
            groups[grp][t2]["E"] += 1
            groups[grp][t2]["Pts"] += 1
    # Ordenar cada grupo
    result = {}
    for grp, times in groups.items():
        result[grp] = sorted(times.items(), key=lambda x: (-x[1]["Pts"], -(x[1]["GP"]-x[1]["GC"]), -x[1]["GP"]))
    return result

# ──────────────────────────────────────────────────────────────────────────────
# CSS e Card (mesmo visual original)
# ──────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.match-card {
  background:linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);
  border:1px solid #e94560; border-radius:12px;
  padding:14px 18px; margin-bottom:10px; color:white;
}
.match-live  { border-color:#ff4444!important;
               box-shadow:0 0 14px rgba(255,68,68,.5);
               animation:pulse 2s infinite; }
.brasil-card { border-color:#009c3b!important;
               box-shadow:0 0 10px rgba(0,156,59,.3); }
@keyframes pulse {
  0%,100%{box-shadow:0 0 14px rgba(255,68,68,.4);}
  50%{box-shadow:0 0 28px rgba(255,68,68,.9);}
}
.score-num{font-size:2.2em;font-weight:900;color:#f5a623;}
.vs-text{font-size:1em;color:#888;}
.flag-big{font-size:2em;}
.tname{font-size:.9em;font-weight:600;margin-top:4px;}
.meta{font-size:.76em;color:#aaa;text-align:center;margin-top:8px;}
.brt-time{color:#f5a623;font-weight:bold;}
.grp-hdr{background:#e94560;color:white;padding:6px 14px;
          border-radius:8px;font-weight:bold;text-align:center;margin-bottom:8px;}
</style>
""", unsafe_allow_html=True)

def render_card(g: dict):
    hflag, hname = resolve(g["team1"])
    aflag, aname = resolve(g["team2"])
    status   = g["status"]
    live     = status == "live"
    finished = status == "finished"
    brasil   = "Brasil" in (hname, aname)

    hs, as_ = g.get("home_score"), g.get("away_score")
    if (live or finished) and hs is not None:
        score_html = f"<span class='score-num'>{hs} — {as_}</span>"
    elif live:
        score_html = "<span class='score-num' style='color:#ff4444'>⚽</span>"
    else:
        score_html = "<span class='vs-text'>vs</span>"

    status_label = {"scheduled":"🕐 Agendado", "live":"🔴 AO VIVO", "halftime":"⏸️ Intervalo", "finished":"✅ Encerrado"}.get(status, "🕐 Agendado")
    group  = g.get("group","")
    ground = g.get("ground","")
    dt_brt = g.get("datetime")

    time_str = ""
    if dt_brt:
        time_str = f"<span class='brt-time'>{dt_brt.strftime('%d/%m às %H:%M')} BRT</span>"

    meta_parts = list(filter(None,[ground, time_str]))
    meta = " &nbsp;·&nbsp; ".join(meta_parts)

    css = "match-card"
    if live:   css += " match-live"
    if brasil: css += " brasil-card"

    st.markdown(f"""
    <div class="{css}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <small style="color:#aaa">{"Fase de Grupos" if len(group)==1 else group}{' · Grupo '+group if len(group)==1 else ''}</small>
        <small>{status_label}</small>
      </div>
      <div style="display:grid;grid-template-columns:1fr 90px 1fr;align-items:center;gap:6px;text-align:center">
        <div><div class="flag-big">{hflag}</div><div class="tname">{hname}</div></div>
        <div>{score_html}</div>
        <div><div class="flag-big">{aflag}</div><div class="tname">{aname}</div></div>
      </div>
      <div class="meta">{meta}</div>
    </div>
    """, unsafe_allow_html=True)

def sort_key(g): return g.get("datetime") or datetime.min.replace(tzinfo=BRT)

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar e páginas
# ──────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚽ Copa 2026")
    st.markdown("🇧🇷 **Grupo C** — Brasil, Marrocos, Haiti, Escócia")
    st.divider()
    pagina = st.radio("Página",[
        "🔴 Ao Vivo & Hoje",
        "🇧🇷 Jogos do Brasil",
        "🗓️ Todos os Jogos",
        "🏅 Classificação",
        "📊 Grupos",
    ])
    st.divider()
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Horários em BRT (UTC-3)  \n11 Jun – 19 Jul 2026")
    st.caption("Dados: SportScore · Atribuição obrigatória")

st.markdown("# 🏆 Copa do Mundo FIFA 2026")
st.caption(f"⏰ Horários em **Brasília (BRT)** · Atualizado: {datetime.now(BRT).strftime('%d/%m/%Y %H:%M')}")

games = fetch_world_cup_data()
now_brt = datetime.now(BRT)
today = now_brt.date()

if pagina == "🔴 Ao Vivo & Hoje":
    live_games = [g for g in games if g["status"] in ("live","halftime")]
    st.subheader("🔴 Ao Vivo")
    if live_games:
        for g in live_games: render_card(g)
    else:
        st.info("Nenhum jogo ao vivo agora.")

    st.subheader("📅 Jogos de Hoje")
    today_games = [g for g in games if g.get("datetime") and g["datetime"].date() == today]
    if today_games:
        for g in sorted(today_games, key=sort_key): render_card(g)
    else:
        st.info("Nenhum jogo hoje." if games else "⚠️ Dados indisponíveis.")

elif pagina == "🇧🇷 Jogos do Brasil":
    st.subheader("🇧🇷 Jogos do Brasil — Grupo C")
    br = [g for g in games if "Brasil" in (resolve(g["team1"])[1], resolve(g["team2"])[1])]
    if br:
        for g in sorted(br, key=sort_key): render_card(g)
    else:
        st.dataframe(pd.DataFrame([
            {"Data":"13/06 Sex","Hora BRT":"19:00","Adversário":"🇲🇦 Marrocos","Cidade":"New York/NJ"},
            {"Data":"19/06 Qui","Hora BRT":"21:30","Adversário":"🇭🇹 Haiti",   "Cidade":"Philadelphia"},
            {"Data":"24/06 Ter","Hora BRT":"19:00","Adversário":"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escócia","Cidade":"Miami"},
        ]), use_container_width=True, hide_index=True)

elif pagina == "🗓️ Todos os Jogos":
    st.subheader("🗓️ Calendário Completo")
    if not games:
        st.warning("⚠️ Dados indisponíveis. Tente atualizar.")
    else:
        c1,c2,c3 = st.columns(3)
        with c1: grp_f = st.selectbox("Grupo",["Todos"]+sorted({g.get("group","") for g in games if g.get("group")}))
        with c2: sta_f = st.selectbox("Status",["Todos","Agendado","Ao Vivo","Encerrado"])
        with c3:
            dates = sorted({g["datetime"].date() for g in games if g.get("datetime")})
            date_opts = ["Todas"] + [d.strftime("%d/%m") for d in dates]
            date_sel = st.selectbox("Data", date_opts)

        fil = games[:]
        if grp_f != "Todos": fil = [g for g in fil if g.get("group","") == grp_f]
        if sta_f == "Ao Vivo": fil = [g for g in fil if g["status"] in ("live","halftime")]
        elif sta_f == "Encerrado": fil = [g for g in fil if g["status"] == "finished"]
        elif sta_f == "Agendado": fil = [g for g in fil if g["status"] == "scheduled"]
        if date_sel != "Todas": fil = [g for g in fil if g.get("datetime") and g["datetime"].strftime("%d/%m") == date_sel]

        st.caption(f"{len(fil)} jogos encontrados")
        for g in sorted(fil, key=sort_key): render_card(g)

elif pagina == "🏅 Classificação":
    st.subheader("🏅 Classificação por Grupo")
    st.caption("Calculada a partir dos resultados oficiais (jogos encerrados).")
    standings = calc_standings_from_games(games)
    if standings:
        for grp in sorted(standings.keys()):
            st.markdown(f"<div class='grp-hdr'>Grupo {grp}</div>", unsafe_allow_html=True)
            rows = []
            for i, (team, stats) in enumerate(standings[grp]):
                fl, nm = resolve(team)
                sg = stats["GP"] - stats["GC"]
                rows.append({
                    "#": i+1,
                    "Seleção": f"{fl} {nm}",
                    "J": stats["J"], "V": stats["V"], "E": stats["E"], "D": stats["D"],
                    "GP": stats["GP"], "GC": stats["GC"],
                    "SG": f"+{sg}" if sg>0 else str(sg),
                    "Pts": stats["Pts"]
                })
            df = pd.DataFrame(rows)
            def hl(row):
                return ["background:rgba(0,156,59,.18)"]*len(row) if "Brasil" in str(row["Seleção"]) else [""]*len(row)
            st.dataframe(df.style.apply(hl, axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum resultado disponível ainda.")

elif pagina == "📊 Grupos":
    st.subheader("📊 Grupos da Copa do Mundo 2026")
    st.caption("48 seleções · 12 grupos de 4 · Os 2 primeiros + 8 melhores 3ºs avançam")
    cols = st.columns(3)
    for i,(grp,teams) in enumerate(GRUPOS_PT.items()):
        with cols[i%3]:
            st.markdown(f"<div class='grp-hdr'>Grupo {grp}</div>", unsafe_allow_html=True)
            for iso,name in teams:
                em = code_to_flag(iso)
                s = " style='background:rgba(0,156,59,.15);padding:2px 6px;border-radius:4px'" if name=="Brasil" else ""
                st.markdown(f"<div{s}>{em} {name}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
