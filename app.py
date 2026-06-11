import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, timezone, timedelta
import time

st.set_page_config(
    page_title="Copa do Mundo 2026 🏆",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

BRT = timezone(timedelta(hours=-3))
API_SCORES  = "https://worldcup26.ir/get"
API_SCHED   = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

# ─── Bandeiras ────────────────────────────────────────────────────────────────
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

# ─── Parse horário openfootball com timezone correto ──────────────────────────
def parse_brt(date_str: str, time_str: str):
    """Converte 'YYYY-MM-DD' + 'HH:MM UTC±X' para datetime em BRT."""
    m = re.match(r'(\d+:\d+)\s+UTC([+-]\d+)', time_str or "")
    if not m: return None
    t, offset = m.group(1), int(m.group(2))
    dt = datetime.strptime(f"{date_str} {t}", "%Y-%m-%d %H:%M")
    tz_local = timezone(timedelta(hours=offset))
    return dt.replace(tzinfo=tz_local).astimezone(BRT)

# ─── Fetch ───────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_scores() -> dict:
    """Retorna dict keyed por (team1_en, team2_en) → {home_score, away_score, status}"""
    try:
        r = requests.get(f"{API_SCORES}/games", timeout=10,
                         headers={"User-Agent":"Copa2026App/1.0"})
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

@st.cache_data(ttl=300)
def fetch_schedule() -> list:
    """Retorna lista de jogos do openfootball com horário BRT correto."""
    try:
        r = requests.get(API_SCHED, timeout=15)
        if r.status_code == 200:
            data = r.json()
            matches = []
            for m in data.get("matches",[]):
                dt_brt = parse_brt(m.get("date",""), m.get("time",""))
                group = m.get("group","").replace("Group ","").strip()
                matches.append({
                    "team1":    m.get("team1","?"),
                    "team2":    m.get("team2","?"),
                    "dt_brt":   dt_brt,
                    "group":    group,
                    "ground":   m.get("ground",""),
                    "round":    m.get("round",""),
                })
            return matches
    except Exception:
        pass
    return []

# ─── Merge schedule + scores ──────────────────────────────────────────────────
def build_games(schedule, scores) -> list:
    games = []
    for m in schedule:
        t1, t2 = m["team1"], m["team2"]
        sc = scores.get((t1,t2)) or scores.get((t2,t1))
        finished    = sc["finished"]    if sc else False
        time_el     = sc["time_elapsed"] if sc else "notstarted"
        home_score  = sc["home_score"]  if sc else None
        away_score  = sc["away_score"]  if sc else None

        # Status
        if finished:
            status = "finished"
        elif time_el in ("inprogress","1h","2h","live","in_progress"):
            status = "live"
        elif time_el in ("halftime","ht"):
            status = "halftime"
        else:
            status = "scheduled"

        games.append({**m,
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

GRUPOS_PT = {
    "A":[("MX","México"),("ZA","África do Sul"),("KR","Coreia do Sul"),("CZ","Rep. Tcheca")],
    "B":[("CA","Canadá"),("QA","Catar"),("CH","Suíça"),("IT","Europa A")],
    "C":[("BR","Brasil"),("MA","Marrocos"),("HT","Haiti"),("SCO","Escócia")],
    "D":[("US","Estados Unidos"),("PY","Paraguai"),("AU","Austrália"),("TR","Europa C")],
    "E":[("DE","Alemanha"),("CW","Curaçao"),("CI","Costa do Marfim"),("EC","Equador")],
    "F":[("NL","Holanda"),("JP","Japão"),("TN","Tunísia"),("UA","Europa B")],
    "G":[("BE","Bélgica"),("EG","Egito"),("IR","Irã"),("NZ","Nova Zelândia")],
    "H":[("ES","Espanha"),("CV","Cabo Verde"),("SA","Arábia Saudita"),("UY","Uruguai")],
    "I":[("FR","França"),("SN","Senegal"),("NO","Noruega"),("IQ","Repescagem 2")],
    "J":[("AR","Argentina"),("DZ","Argélia"),("AT","Áustria"),("JO","Jordânia")],
    "K":[("PT","Portugal"),("UZ","Uzbequistão"),("CO","Colômbia"),("CD","Repescagem 1")],
    "L":[("ENG","Inglaterra"),("HR","Croácia"),("GH","Gana"),("PA","Panamá")],
}

# ─── CSS ─────────────────────────────────────────────────────────────────────
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

# ─── Card ─────────────────────────────────────────────────────────────────────
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

def sort_key(g): return g.get("dt_brt") or datetime.min.replace(tzinfo=BRT)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
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
    auto = st.toggle("Auto-refresh 60s", value=False)
    if st.button("🔄 Atualizar"):
        st.cache_data.clear(); st.rerun()
    st.caption("Horários em BRT (UTC-3)  \n11 Jun – 19 Jul 2026")

st.markdown("# 🏆 Copa do Mundo FIFA 2026")
st.caption(f"⏰ Horários em **Brasília (BRT)** · Atualizado: {datetime.now(BRT).strftime('%d/%m/%Y %H:%M')}")

if auto:
    time.sleep(60); st.rerun()

schedule = fetch_schedule()
scores   = fetch_scores()
games    = build_games(schedule, scores)
now_brt  = datetime.now(BRT)
today    = now_brt.date()

# ══════════════════════════════════════════════════════════
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
        st.info("Nenhum jogo hoje." if games else "⚠️ Dados indisponíveis.")

# ══════════════════════════════════════════════════════════
elif pagina == "🇧🇷 Jogos do Brasil":
    st.subheader("🇧🇷 Jogos do Brasil — Grupo C")
    br = [g for g in games if "Brasil" in (resolve(g["team1"])[1], resolve(g["team2"])[1])]
    if br:
        for g in sorted(br, key=sort_key): render_card(g)
    else:
        st.info("Jogos do Brasil:")
        st.dataframe(pd.DataFrame([
            {"Data":"13/06 Sex","Hora BRT":"19:00","Adversário":"🇲🇦 Marrocos","Cidade":"New York/NJ"},
            {"Data":"19/06 Qui","Hora BRT":"21:30","Adversário":"🇭🇹 Haiti",   "Cidade":"Philadelphia"},
            {"Data":"24/06 Ter","Hora BRT":"19:00","Adversário":"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escócia","Cidade":"Miami"},
        ]), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
elif pagina == "🗓️ Todos os Jogos":
    st.subheader("🗓️ Calendário Completo")
    if not games:
        st.warning("⚠️ Dados indisponíveis. Tente atualizar.")
    else:
        c1,c2,c3 = st.columns(3)
        with c1: grp_f = st.selectbox("Grupo",["Todos"]+list("ABCDEFGHIJKL"))
        with c2: sta_f = st.selectbox("Status",["Todos","Agendado","Ao Vivo","Encerrado"])
        with c3:
            # Data picker
            dates = sorted({g["dt_brt"].date() for g in games if g.get("dt_brt")})
            date_opts = ["Todas"] + [d.strftime("%d/%m") for d in dates]
            date_sel = st.selectbox("Data", date_opts)

        fil = games[:]
        if grp_f != "Todos":
            fil = [g for g in fil if g.get("group","").upper() == grp_f]
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

# ══════════════════════════════════════════════════════════
elif pagina == "🏅 Classificação":
    st.subheader("🏅 Classificação por Grupo")
    try:
        r = requests.get(f"{API_SCORES}/groups", timeout=10,
                         headers={"User-Agent":"Copa2026App/1.0"})
        gdata = r.json() if r.status_code==200 else []
        if not isinstance(gdata, list): gdata = gdata.get("groups",[])
    except Exception:
        gdata = []

    if gdata:
        for grp in gdata:
            gname = grp.get("name") or grp.get("group","?")
            standings = grp.get("standings") or grp.get("teams",[])
            if not standings: continue
            st.markdown(f"<div class='grp-hdr'>Grupo {gname}</div>", unsafe_allow_html=True)
            rows=[]
            for i,t in enumerate(standings):
                ne = t.get("name_en") or t.get("team") or t.get("name") or ""
                fl,nm = resolve(ne)
                rows.append({"#":i+1,"Seleção":f"{fl} {nm}",
                    "J":t.get("played",0),"V":t.get("w",0),"E":t.get("d",0),
                    "D":t.get("l",0),"GP":t.get("gf",0),"GC":t.get("ga",0),
                    "SG":t.get("gd",0),"Pts":t.get("points",0)})
            df = pd.DataFrame(rows)
            def hl(row):
                return ["background:rgba(0,156,59,.18)"]*len(row) if "Brasil" in str(row["Seleção"]) else [""]*len(row)
            st.dataframe(df.style.apply(hl,axis=1), use_container_width=True, hide_index=True)
    else:
        st.info("Classificação ainda não disponível.")
        for grp,teams in GRUPOS_PT.items():
            st.markdown(f"<div class='grp-hdr'>Grupo {grp}</div>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame({
                "Seleção":[f"{code_to_flag(iso)} {name}" for iso,name in teams],
                "J":[0]*4,"V":[0]*4,"E":[0]*4,"D":[0]*4,"Pts":[0]*4
            }), use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
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
