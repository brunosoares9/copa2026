import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import time

st.set_page_config(
    page_title="Copa do Mundo 2026 🏆",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRT = timezone(timedelta(hours=-3))
API_SCORES  = "https://worldcup26.ir/get"      # Endpoint externo (pode falhar)
API_SCHED   = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# ──────────────────────────────── Bandeiras e nomes ────────────────────────────────
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
    """Retorna (emoji bandeira, nome em português)."""
    if not name_en or name_en in ("null","None","?"):
        return "🏳️","?"
    n = name_en.strip()
    if n in TEAM_MAP:
        iso, pt = TEAM_MAP[n]
        return code_to_flag(iso), pt
    for k, (iso, pt) in TEAM_MAP.items():
        if k.lower() in n.lower() or n.lower() in k.lower():
            return code_to_flag(iso), pt
    return "🏳️", n

# ──────────────────────────────── Grupos (única fonte) ─────────────────────────────
# Formato: { "A": [("MX","México"), ...] }
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
# Mapa nome_inglês -> grupo (populado automaticamente)
NOME_PARA_GRUPO = {}
for grp, times in GRUPOS_PT.items():
    for iso, pt in times:
        # Precisa encontrar o nome em inglês correspondente ao iso
        for en, (code, _) in TEAM_MAP.items():
            if code == iso:
                NOME_PARA_GRUPO[en] = grp
                break

# ──────────────────────────────── Parsing de horário ──────────────────────────────
def parse_brt(date_str: str, time_str: str):
    """Converte formatos como '15:00 UTC-4' ou '20:30' para datetime em BRT."""
    if not time_str:
        return None
    m = re.search(r'UTC([+-]\d+)', time_str)
    offset = int(m.group(1)) if m else 0
    clean_time = re.sub(r'\s*UTC[+-]\d+', '', time_str).strip()
    try:
        dt = datetime.strptime(f"{date_str} {clean_time}", "%Y-%m-%d %H:%M")
    except:
        return None
    tz_local = timezone(timedelta(hours=offset))
    return dt.replace(tzinfo=tz_local).astimezone(BRT)

# ──────────────────────────────── Busca dados (cache) ─────────────────────────────
@st.cache_data(ttl=600)  # 10 minutos
def fetch_scores() -> dict:
    """Retorna dict {(team1,team2): {home_score, away_score, finished, time_elapsed}}"""
    try:
        r = requests.get(f"{API_SCORES}/games", timeout=5)
        if r.status_code == 200:
            d = r.json()
            games = d if isinstance(d, list) else d.get("games",[])
            out = {}
            for g in games:
                h = g.get("home_team_name_en","")
                a = g.get("away_team_name_en","")
                if h and a:
                    out[(h,a)] = {
                        "home_score": g.get("home_score"),
                        "away_score": g.get("away_score"),
                        "finished":   g.get("finished","FALSE") in ("TRUE","true",True),
                        "time_elapsed": g.get("time_elapsed","notstarted"),
                    }
            return out
    except Exception:
        pass
    return {}

@st.cache_data(ttl=600)
def fetch_schedule() -> tuple[list, dict]:
    """Retorna (lista de jogos com horário BRT, dict grupos->[times])"""
    try:
        r = requests.get(API_SCHED, timeout=10)
        if r.status_code == 200:
            data = r.json()
            matches = []
            group_teams = defaultdict(set)
            for m in data.get("matches",[]):
                dt_brt = parse_brt(m.get("date",""), m.get("time",""))
                group = m.get("group","").replace("Group ","").strip()
                if group and m.get("team1"):
                    group_teams[group].add(m["team1"])
                if group and m.get("team2"):
                    group_teams[group].add(m["team2"])
                # Extrai gols (se existirem) do campo score.goals1/goals2
                score_info = m.get("score", {})
                goals1 = score_info.get("goals1", [])
                goals2 = score_info.get("goals2", [])
                matches.append({
                    "team1": m.get("team1","?"),
                    "team2": m.get("team2","?"),
                    "dt_brt": dt_brt,
                    "group": group,
                    "ground": m.get("ground",""),
                    "round": m.get("round",""),
                    "score": score_info,          # contém ft, goals1, goals2, etc.
                    "goals1": goals1,
                    "goals2": goals2,
                })
            return matches, dict(group_teams)
    except Exception:
        pass
    # Fallback com dados de exemplo
    example_matches = [
        {"team1":"Brazil","team2":"Morocco","dt_brt":datetime(2026,6,13,19,0,tzinfo=BRT),
         "group":"C","ground":"New York/NJ","round":"Group stage","score":{"ft":[0,0]},"goals1":[],"goals2":[]},
        {"team1":"Brazil","team2":"Haiti","dt_brt":datetime(2026,6,19,21,30,tzinfo=BRT),
         "group":"C","ground":"Philadelphia","round":"Group stage","score":{},"goals1":[],"goals2":[]},
    ]
    example_groups = {"C":{"Brazil","Morocco","Haiti","Scotland"}}
    return example_matches, example_groups

# ──────────────────────────────── Cálculo da classificação ───────────────────────
def calc_standings(matches: list) -> dict:
    groups = defaultdict(dict)
    for m in matches:
        score = m.get("score", {})
        ft = score.get("ft")
        if not ft or len(ft) < 2:
            continue
        g1, g2 = int(ft[0]), int(ft[1])
        t1, t2 = m["team1"], m["team2"]
        grp = m.get("group","")
        if not grp:
            # Tenta inferir grupo pelo nome do time
            grp = NOME_PARA_GRUPO.get(t1) or NOME_PARA_GRUPO.get(t2)
            if not grp:
                continue
        for team in (t1, t2):
            if team not in groups[grp]:
                groups[grp][team] = {"J":0,"V":0,"E":0,"D":0,"GP":0,"GC":0,"Pts":0}
        s1, s2 = groups[grp][t1], groups[grp][t2]
        s1["J"]+=1; s2["J"]+=1
        s1["GP"]+=g1; s1["GC"]+=g2
        s2["GP"]+=g2; s2["GC"]+=g1
        if g1 > g2:
            s1["V"]+=1; s1["Pts"]+=3; s2["D"]+=1
        elif g2 > g1:
            s2["V"]+=1; s2["Pts"]+=3; s1["D"]+=1
        else:
            s1["E"]+=1; s1["Pts"]+=1; s2["E"]+=1; s2["Pts"]+=1
    result = {}
    for grp, teams in groups.items():
        result[grp] = sorted(teams.items(),
            key=lambda x: (-x[1]["Pts"], -(x[1]["GP"]-x[1]["GC"]), -x[1]["GP"]))
    return result

# ──────────────────────────────── Mescla schedule + scores ao vivo ───────────────
def build_games(schedule, scores) -> list:
    games = []
    for m in schedule:
        t1, t2 = m["team1"], m["team2"]
        sc = scores.get((t1,t2)) or scores.get((t2,t1))

        # Status baseado na API de scores (se disponível)
        if sc:
            finished    = sc["finished"]
            time_el     = sc["time_elapsed"]
            home_score  = sc["home_score"]
            away_score  = sc["away_score"]
            if finished:
                status = "finished"
            elif time_el in ("inprogress","1h","2h","live","in_progress"):
                status = "live"
            elif time_el in ("halftime","ht"):
                status = "halftime"
            else:
                status = "scheduled"
        else:
            # Sem dados ao vivo: usa score do openfootball
            ft = m.get("score", {}).get("ft")
            if ft and len(ft) == 2:
                home_score, away_score = ft[0], ft[1]
                status = "finished"
            else:
                home_score = away_score = None
                status = "scheduled"

        games.append({
            **m,
            "status": status,
            "home_score": home_score,
            "away_score": away_score,
        })
    return games

STATUS_PT = {
    "scheduled":"🕐 Agendado",
    "live":"🔴 AO VIVO",
    "halftime":"⏸️ Intervalo",
    "finished":"✅ Encerrado",
}

# ──────────────────────────────── CSS e componentes visuais ──────────────────────
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
.goals-list { font-size: 0.75em; color: #ccc; margin-top: 4px; text-align: center; }
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
    if (live or finished) and hs is not None and str(hs) not in ("null","None"):
        score_html = f"<span class='score-num'>{hs} — {as_}</span>"
    elif live:
        score_html = "<span class='score-num' style='color:#ff4444'>⚽</span>"
    else:
        score_html = "<span class='vs-text'>vs</span>"

    status_label = STATUS_PT.get(status, "🕐 Agendado")
    group  = g.get("group","")
    ground = g.get("ground","")
    dt_brt = g.get("dt_brt")

    time_str = ""
    if dt_brt:
        time_str = f"<span class='brt-time'>{dt_brt.strftime('%d/%m às %H:%M')} BRT</span>"

    meta_parts = list(filter(None,[ground, time_str]))
    meta = " &nbsp;·&nbsp; ".join(meta_parts)

    # Exibe lista de gols (se disponível e jogo terminado ou ao vivo)
    goals_html = ""
    if finished and (g.get("goals1") or g.get("goals2")):
        gols1 = g.get("goals1", [])
        gols2 = g.get("goals2", [])
        if gols1 or gols2:
            goals_lines = []
            for goal in gols1:
                scorer = goal.get("name", "?")
                minute = goal.get("minute", "")
                goals_lines.append(f"⚽ {scorer} ({minute}')")
            for goal in gols2:
                scorer = goal.get("name", "?")
                minute = goal.get("minute", "")
                goals_lines.append(f"⚽ {scorer} ({minute}')")
            if goals_lines:
                goals_html = '<div class="goals-list">' + " &nbsp;|&nbsp; ".join(goals_lines) + '</div>'

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
      {goals_html}
    </div>
    """, unsafe_allow_html=True)

def sort_key(g): return g.get("dt_brt") or datetime.min.replace(tzinfo=BRT)

def get_next_brazil_game(games):
    """Retorna o próximo jogo do Brasil (futuro) ou None."""
    now = datetime.now(BRT)
    future = [g for g in games if g.get("dt_brt") and g["dt_brt"] > now and
              "Brasil" in (resolve(g["team1"])[1], resolve(g["team2"])[1])]
    if future:
        return min(future, key=lambda x: x["dt_brt"])
    return None

# ──────────────────────────────── Sidebar com próximo jogo do Brasil ─────────────
with st.sidebar:
    st.markdown("## ⚽ Copa 2026")
    st.markdown("🇧🇷 **Grupo C** — Brasil, Marrocos, Haiti, Escócia")
    st.divider()
    pagina = st.radio("Página",[
        "🔴 Ao Vivo & Hoje",
        "🇧🇷 Jogos do Brasil",
        "🗓️ Todos os Jogos",
        "🏅 Classificação",
    ])
    st.divider()

    # Auto-refresh sem bloquear
    auto = st.checkbox("Auto-refresh 60s", value=False)
    if auto:
        # Usa session_state para controlar o tempo
        if "last_refresh" not in st.session_state:
            st.session_state.last_refresh = time.time()
        if time.time() - st.session_state.last_refresh > 60:
            st.session_state.last_refresh = time.time()
            st.rerun()
        st.caption("🔄 Atualizando automaticamente...")

    if st.button("🔄 Atualizar agora"):
        st.cache_data.clear()
        st.rerun()

    # Próximo jogo do Brasil
    # Precisamos dos dados carregados; faremos isso após carregar, mas o sidebar é renderizado antes.
    # Solução: carregar dados novamente? Vamos carregar aqui também (cache evita custo)
    with st.spinner("Carregando jogos..."):
        sched, _ = fetch_schedule()
        scores = fetch_scores()
        games_sidebar = build_games(sched, scores)
        next_br = get_next_brazil_game(games_sidebar)
    if next_br:
        dt = next_br["dt_brt"]
        agora = datetime.now(BRT)
        diff = dt - agora
        dias = diff.days
        horas = diff.seconds // 3600
        if dias > 0:
            falta = f"{dias} dia(s) e {horas}h"
        else:
            falta = f"{horas} horas"
        adv = resolve(next_br["team2"])[1] if "Brasil" in resolve(next_br["team1"])[1] else resolve(next_br["team1"])[1]
        st.markdown("### 🇧🇷 Próximo jogo")
        st.markdown(f"**{adv}**  \n{dt.strftime('%d/%m às %H:%M')} BRT  \n⏳ {falta}")
    else:
        st.info("Sem jogos futuros do Brasil agendados.")

    st.caption("Horários em BRT (UTC-3)  \n11 Jun – 19 Jul 2026")

st.markdown("# 🏆 Copa do Mundo FIFA 2026")
st.caption(f"⏰ Horários em **Brasília (BRT)** · Atualizado: {datetime.now(BRT).strftime('%d/%m/%Y %H:%M')}")

# Carrega dados principais
schedule, group_teams = fetch_schedule()
scores = fetch_scores()
games = build_games(schedule, scores)
now_brt = datetime.now(BRT)
today = now_brt.date()

# ═══════════════════════════════════════════════════════════════════════════════
# PÁGINA: Ao Vivo & Hoje (com fallback para próximo jogo)
if pagina == "🔴 Ao Vivo & Hoje":
    live_games = [g for g in games if g["status"] in ("live","halftime")]
    st.subheader("🔴 Ao Vivo")
    if live_games:
        for g in live_games: render_card(g)
    else:
        st.info("Nenhum jogo ao vivo agora.")

    st.subheader("📅 Jogos de Hoje")
    today_games = [g for g in games if g.get("dt_brt") and g["dt_brt"].date() == today]
    if today_games:
        for g in sorted(today_games, key=sort_key): render_card(g)
    else:
        # Mostra próximo jogo da competição (não necessariamente do Brasil)
        future_games = [g for g in games if g.get("dt_brt") and g["dt_brt"] > now_brt]
        if future_games:
            next_game = min(future_games, key=lambda x: x["dt_brt"])
            st.info(f"⚠️ Nenhum jogo hoje. **Próximo jogo:** {next_game['dt_brt'].strftime('%d/%m às %H:%M')} BRT")
            # Opcional: mostrar card do próximo jogo
            with st.expander("Ver próximo jogo"):
                render_card(next_game)
        else:
            st.info("Nenhum jogo programado nas próximas datas.")

# ═══════════════════════════════════════════════════════════════════════════════
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

# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🗓️ Todos os Jogos":
    st.subheader("🗓️ Calendário Completo")
    if not games:
        st.warning("⚠️ Dados indisponíveis. Tente atualizar.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            grupos_disponiveis = sorted({g["group"] for g in games if g["group"]})
            grp_f = st.selectbox("Grupo", ["Todos"] + grupos_disponiveis)
        with c2:
            sta_f = st.selectbox("Status", ["Todos","Agendado","Ao Vivo","Encerrado"])
        with c3:
            dates = sorted({g["dt_brt"].date() for g in games if g.get("dt_brt")})
            date_opts = ["Todas"] + [d.strftime("%d/%m") for d in dates]
            date_sel = st.selectbox("Data", date_opts)

        fil = games[:]
        if grp_f != "Todos":
            fil = [g for g in fil if g.get("group","") == grp_f]
        if sta_f == "Ao Vivo":
            fil = [g for g in fil if g["status"] in ("live","halftime")]
        elif sta_f == "Encerrado":
            fil = [g for g in fil if g["status"] == "finished"]
        elif sta_f == "Agendado":
            fil = [g for g in fil if g["status"] == "scheduled"]
        if date_sel != "Todas":
            fil = [g for g in fil if g.get("dt_brt") and g["dt_brt"].strftime("%d/%m") == date_sel]

        st.caption(f"{len(fil)} jogos encontrados")
        for g in sorted(fil, key=sort_key): render_card(g)

# ═══════════════════════════════════════════════════════════════════════════════
elif pagina == "🏅 Classificação":
    st.subheader("🏅 Classificação por Grupo")
    st.caption("Os dois primeiros de cada grupo avançam (verde); o terceiro pode avançar como um dos melhores (amarelo).")
    standings_all = calc_standings(schedule)  # usa schedule original com score.ft

    # Se não houver standings, usa grupos vazios
    all_groups = list(GRUPOS_PT.keys())
    for grp in all_groups:
        st.markdown(f"<div class='grp-hdr'>Grupo {grp}</div>", unsafe_allow_html=True)
        # Obtém lista de times (inglês) do grupo via GRUPOS_PT
        team_names_en = []
        for iso, pt in GRUPOS_PT[grp]:
            # encontra nome em inglês correspondente ao iso
            for en, (code, _) in TEAM_MAP.items():
                if code == iso:
                    team_names_en.append(en)
                    break
        # Se não encontrou, fallback para o que veio do schedule
        if not team_names_en:
            team_names_en = list(group_teams.get(grp, set()))

        # Monta dados
        teams_data = dict(standings_all.get(grp, []))
        for t in team_names_en:
            if t not in teams_data:
                teams_data[t] = {"J":0,"V":0,"E":0,"D":0,"GP":0,"GC":0,"Pts":0}
        ordered = sorted(teams_data.items(),
                         key=lambda x: (-x[1]["Pts"], -(x[1]["GP"]-x[1]["GC"]), -x[1]["GP"]))
        rows = []
        for i, (t, s) in enumerate(ordered):
            fl, nm = resolve(t)
            sg = s["GP"] - s["GC"]
            rows.append({
                "#": i+1,
                "Seleção": f"{fl} {nm}",
                "J": s["J"], "V": s["V"], "E": s["E"], "D": s["D"],
                "GP": s["GP"], "GC": s["GC"],
                "SG": f"+{sg}" if sg>0 else str(sg),
                "Pts": s["Pts"]
            })

        df = pd.DataFrame(rows)
        # Destaca 1º e 2º em verde, 3º em amarelo
        def highlight_row(row):
            idx = row.name  # índice da linha (0-based)
            if idx < 2:
                return ["background-color: rgba(0,156,59,0.2)"] * len(row)  # verde claro
            elif idx == 2:
                return ["background-color: rgba(255,255,0,0.2)"] * len(row) # amarelo
            else:
                return [""] * len(row)
        st.dataframe(df.style.apply(highlight_row, axis=1), use_container_width=True, hide_index=True)

# Nota: a página "Grupos" foi removida por redundância; agora a classificação já exibe os grupos.
