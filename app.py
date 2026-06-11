import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone
import time

st.set_page_config(
    page_title="Copa do Mundo 2026 🏆",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "https://worldcup26.ir/get"

# ─── Bandeira por código ISO alpha-2 via unicode ──────────────────────────────
def code_to_flag(code: str) -> str:
    special = {"SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "WAL": "🏴󠁧󠁢󠁷󠁬󠁳󠁿", "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿"}
    if not code: return "🏳️"
    if code.upper() in special: return special[code.upper()]
    c = code.upper()[:2]
    try:
        return chr(0x1F1E6 + ord(c[0]) - ord('A')) + chr(0x1F1E6 + ord(c[1]) - ord('A'))
    except Exception:
        return "🏳️"

# Mapa nome EN → (iso, nome PT)
TEAM_MAP = {
    "Mexico":("MX","México"), "South Africa":("ZA","África do Sul"),
    "South Korea":("KR","Coreia do Sul"), "Korea Republic":("KR","Coreia do Sul"),
    "Czech Republic":("CZ","Rep. Tcheca"), "Czechia":("CZ","Rep. Tcheca"),
    "Denmark":("DK","Dinamarca"), "North Macedonia":("MK","Macedônia do Norte"),
    "Ireland":("IE","Irlanda"),
    "Canada":("CA","Canadá"), "Qatar":("QA","Catar"),
    "Switzerland":("CH","Suíça"), "Italy":("IT","Itália"),
    "Northern Ireland":("GB","Irlanda do Norte"),
    "Wales":("WAL","País de Gales"), "Bosnia and Herzegovina":("BA","Bósnia"),
    "Brazil":("BR","Brasil"), "Morocco":("MA","Marrocos"),
    "Haiti":("HT","Haiti"), "Scotland":("SCO","Escócia"),
    "USA":("US","Estados Unidos"), "United States":("US","Estados Unidos"),
    "Paraguay":("PY","Paraguai"), "Australia":("AU","Austrália"),
    "Turkey":("TR","Turquia"), "Romania":("RO","Romênia"),
    "Slovakia":("SK","Eslováquia"), "Kosovo":("XK","Kosovo"),
    "Germany":("DE","Alemanha"), "Curacao":("CW","Curaçao"),
    "Ivory Coast":("CI","Costa do Marfim"), "Côte d'Ivoire":("CI","Costa do Marfim"),
    "Ecuador":("EC","Equador"),
    "Netherlands":("NL","Holanda"), "Japan":("JP","Japão"),
    "Tunisia":("TN","Tunísia"), "Ukraine":("UA","Ucrânia"),
    "Sweden":("SE","Suécia"), "Poland":("PL","Polônia"), "Albania":("AL","Albânia"),
    "Belgium":("BE","Bélgica"), "Egypt":("EG","Egito"),
    "Iran":("IR","Irã"), "New Zealand":("NZ","Nova Zelândia"),
    "Spain":("ES","Espanha"), "Cape Verde":("CV","Cabo Verde"),
    "Saudi Arabia":("SA","Arábia Saudita"), "Uruguay":("UY","Uruguai"),
    "France":("FR","França"), "Senegal":("SN","Senegal"),
    "Norway":("NO","Noruega"), "Iraq":("IQ","Iraque"),
    "Bolivia":("BO","Bolívia"), "Suriname":("SR","Suriname"),
    "Argentina":("AR","Argentina"), "Algeria":("DZ","Argélia"),
    "Austria":("AT","Áustria"), "Jordan":("JO","Jordânia"),
    "Portugal":("PT","Portugal"), "Uzbekistan":("UZ","Uzbequistão"),
    "Colombia":("CO","Colômbia"),
    "DR Congo":("CD","RD Congo"), "Jamaica":("JM","Jamaica"),
    "New Caledonia":("NC","Nova Caledônia"),
    "England":("ENG","Inglaterra"), "Croatia":("HR","Croácia"),
    "Ghana":("GH","Gana"), "Panama":("PA","Panamá"),
}

def resolve_name(name_en: str) -> tuple[str, str]:
    """Dado nome em inglês, retorna (flag_emoji, nome_pt)."""
    if not name_en or name_en in ("null", "None", "?"):
        return "🏳️", "?"
    n = name_en.strip()
    # Match exato
    if n in TEAM_MAP:
        iso, pt = TEAM_MAP[n]
        return code_to_flag(iso), pt
    # Match parcial
    for k, (iso, pt) in TEAM_MAP.items():
        if k.lower() in n.lower() or n.lower() in k.lower():
            return code_to_flag(iso), pt
    return "🏳️", n  # fallback: mostra nome em inglês com bandeira branca

# Extrair nome EN do jogo (campos da API worldcup26.ir)
def get_team_name(game: dict, side: str) -> str:
    """side = 'home' ou 'away'"""
    # Formato real da API: home_team_name_en / away_team_name_en
    name = game.get(f"{side}_team_name_en") or game.get(f"{side}_team_name")
    if name and name not in ("null", "None", ""):
        return name
    # Fallbacks para outras estruturas possíveis
    obj = game.get(f"{side}_team")
    if isinstance(obj, dict):
        return obj.get("en_name") or obj.get("name") or ""
    if isinstance(obj, str) and obj not in ("null","None",""):
        return obj
    return ""

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

FASES = {
    "group":"Fase de Grupos","Group Stage":"Fase de Grupos","notstarted":"Fase de Grupos",
    "round_of_32":"Oitavas (R32)","round_of_16":"Oitavas de Final",
    "quarter_finals":"Quartas de Final","semi_finals":"Semifinais",
    "third_place":"3º Lugar","final":"🏆 Final",
}

STATUS_PT = {
    "notstarted":"🕐 Agendado","scheduled":"🕐 Agendado","NS":"🕐 Agendado",
    "inprogress":"🔴 AO VIVO","in_progress":"🔴 AO VIVO","live":"🔴 AO VIVO",
    "1H":"🔴 AO VIVO","2H":"🔴 AO VIVO",
    "halftime":"⏸️ Intervalo","HT":"⏸️ Intervalo",
    "finished":"✅ Encerrado","FT":"✅ Encerrado","TRUE":"✅ Encerrado",
}

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.match-card {
  background: linear-gradient(135deg,#1a1a2e,#16213e,#0f3460);
  border: 1px solid #e94560;
  border-radius: 12px;
  padding: 14px 18px;
  margin-bottom: 10px;
  color: white;
}
.match-live  { border-color:#ff4444!important; box-shadow:0 0 14px rgba(255,68,68,.5);
               animation:pulse 2s infinite; }
.brasil-card { border-color:#009c3b!important; box-shadow:0 0 10px rgba(0,156,59,.3); }
@keyframes pulse {
  0%,100%{box-shadow:0 0 14px rgba(255,68,68,.4);}
  50%    {box-shadow:0 0 28px rgba(255,68,68,.9);}
}
.score-num { font-size:2.2em; font-weight:900; color:#f5a623; }
.vs-text   { font-size:1em; color:#888; }
.flag-big  { font-size:2em; }
.tname     { font-size:.9em; font-weight:600; margin-top:4px; }
.meta      { font-size:.75em; color:#aaa; text-align:center; margin-top:8px; }
.grp-hdr   { background:#e94560; color:white; padding:6px 14px; border-radius:8px;
             font-weight:bold; text-align:center; margin-bottom:8px; }
</style>
""", unsafe_allow_html=True)

# ─── API ─────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_games():
    try:
        r = requests.get(f"{API_BASE}/games", timeout=10,
                         headers={"User-Agent":"Mozilla/5.0 Copa2026/1.0"})
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
                         headers={"User-Agent":"Mozilla/5.0 Copa2026/1.0"})
        if r.status_code == 200:
            d = r.json()
            return d if isinstance(d, list) else d.get("groups", [])
    except Exception:
        pass
    return []

def parse_dt(s):
    if not s: return None
    # Formato da API: "06/11/2026 13:00"
    for fmt in ["%m/%d/%Y %H:%M", "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(s, fmt)
            # API usa UTC-6 (horário do México/EUA Central) — ajustar se necessário
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

def get_status(g: dict) -> str:
    if g.get("finished") in ("TRUE","true",True):
        return "finished"
    te = g.get("time_elapsed","").lower()
    if te in ("notstarted",""):
        return "notstarted"
    if "half" in te or te == "ht":
        return "halftime"
    if te in ("inprogress","1h","2h","live"):
        return "inprogress"
    return g.get("status", "notstarted")

def is_brasil(g: dict) -> bool:
    return "brazil" in (get_team_name(g,"home") + get_team_name(g,"away")).lower()

def render_card(g: dict):
    hname_en = get_team_name(g, "home")
    aname_en = get_team_name(g, "away")
    hflag, hname = resolve_name(hname_en)
    aflag, aname = resolve_name(aname_en)

    hs  = g.get("home_score")
    as_ = g.get("away_score")
    # A API retorna "0" como string mesmo antes do jogo
    finished = g.get("finished") in ("TRUE","true",True)
    status   = get_status(g)
    live     = status in ("inprogress","halftime")

    # Só mostra placar se o jogo tiver começado
    has_score = finished or live
    if has_score and hs is not None and as_ is not None and str(hs) != "null":
        score_html = f"<span class='score-num'>{hs} — {as_}</span>"
    elif live:
        score_html = "<span class='score-num' style='color:#ff4444'>⚽</span>"
    else:
        score_html = "<span class='vs-text'>vs</span>"

    status_label = STATUS_PT.get(status, "🕐 Agendado")
    phase = FASES.get(g.get("type","group"), "Fase de Grupos")
    group = g.get("group","")
    dt    = parse_dt(g.get("local_date"))
    # Converter UTC para horário de Brasília (UTC-3)
    time_str = ""
    if dt:
        from datetime import timedelta
        brt = dt + timedelta(hours=-6+3)  # local_date está em UTC-6, BRT = UTC-3
        time_str = brt.strftime("%d/%m %H:%M") + " BRT"

    stadium = g.get("stadium_name","") or g.get("stadium","") or ""
    if isinstance(stadium, dict): stadium = stadium.get("name","")
    meta = " · ".join(filter(None,[str(stadium), time_str]))

    css = "match-card"
    if live:              css += " match-live"
    if is_brasil(g):      css += " brasil-card"

    st.markdown(f"""
    <div class="{css}">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <small style="color:#aaa">{phase}{' · Grupo '+group if group else ''}</small>
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

def sort_key(g):
    return g.get("local_date") or g.get("datetime") or ""

# ─── Sidebar ─────────────────────────────────────────────────────────────────
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
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
        st.rerun()
    st.caption("API: worldcup26.ir  \n11 Jun – 19 Jul 2026")

st.markdown("# 🏆 Copa do Mundo FIFA 2026")
st.caption(f"Atualizado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if auto:
    time.sleep(60)
    st.rerun()

games = fetch_games()
today = datetime.now(timezone.utc).date()

# ════════════════════════════════════════════════════════
if pagina == "🔴 Ao Vivo & Hoje":
    live_games = [g for g in games if get_status(g) in ("inprogress","halftime")]
    st.subheader("🔴 Ao Vivo")
    if live_games:
        for g in live_games: render_card(g)
    else:
        st.info("Nenhum jogo ao vivo agora.")

    st.subheader("📅 Jogos de Hoje")
    today_games = []
    for g in games:
        dt = parse_dt(g.get("local_date"))
        if dt and dt.date() == today:
            today_games.append(g)
    if today_games:
        for g in sorted(today_games, key=sort_key): render_card(g)
    else:
        st.info("Nenhum jogo encontrado para hoje." if games else "⚠️ API indisponível.")

# ════════════════════════════════════════════════════════
elif pagina == "🇧🇷 Jogos do Brasil":
    st.subheader("🇧🇷 Jogos do Brasil — Grupo C")
    br = [g for g in games if is_brasil(g)]
    if br:
        for g in sorted(br, key=sort_key): render_card(g)
    else:
        st.info("Jogos confirmados do Brasil:")
        st.dataframe(pd.DataFrame([
            {"Data":"13/06 Sex","Hora (BRT)":"16h","Adversário":"🇲🇦 Marrocos","Cidade":"Atlanta"},
            {"Data":"19/06 Qui","Hora (BRT)":"16h","Adversário":"🇭🇹 Haiti",   "Cidade":"Los Angeles"},
            {"Data":"24/06 Ter","Hora (BRT)":"16h","Adversário":"🏴󠁧󠁢󠁳󠁣󠁴󠁿 Escócia","Cidade":"Dallas"},
        ]), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════
elif pagina == "🗓️ Todos os Jogos":
    st.subheader("🗓️ Calendário Completo")
    if not games:
        st.warning("⚠️ API fora do ar. Tente atualizar.")
    else:
        c1, c2, c3 = st.columns(3)
        with c1: grp_f = st.selectbox("Grupo", ["Todos"]+list("ABCDEFGHIJKL"))
        with c2: sta_f = st.selectbox("Status", ["Todos","Agendado","Ao Vivo","Encerrado"])
        with c3: fas_f = st.selectbox("Fase", ["Todas","Fase de Grupos","Mata-mata"])

        fil = games[:]
        if grp_f != "Todos":
            fil = [g for g in fil if str(g.get("group","")).upper() == grp_f]
        if sta_f == "Ao Vivo":
            fil = [g for g in fil if get_status(g) in ("inprogress","halftime")]
        elif sta_f == "Encerrado":
            fil = [g for g in fil if get_status(g) == "finished"]
        elif sta_f == "Agendado":
            fil = [g for g in fil if get_status(g) == "notstarted"]
        if fas_f == "Fase de Grupos":
            fil = [g for g in fil if g.get("type","group") == "group"]
        elif fas_f == "Mata-mata":
            fil = [g for g in fil if g.get("type","group") != "group"]

        st.caption(f"{len(fil)} jogos encontrados")
        for g in sorted(fil, key=sort_key): render_card(g)

# ════════════════════════════════════════════════════════
elif pagina == "🏅 Classificação":
    st.subheader("🏅 Classificação por Grupo")
    gdata = fetch_groups()
    if gdata:
        for grp in gdata:
            gname = grp.get("name") or grp.get("group","?")
            standings = grp.get("standings") or grp.get("teams",[])
            if not standings: continue
            st.markdown(f"<div class='grp-hdr'>Grupo {gname}</div>", unsafe_allow_html=True)
            rows = []
            for i, t in enumerate(standings):
                name_en = t.get("name_en") or t.get("team") or t.get("name") or ""
                fl, nm  = resolve_name(name_en)
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
        for grp, teams in GRUPOS_PT.items():
            st.markdown(f"<div class='grp-hdr'>Grupo {grp}</div>", unsafe_allow_html=True)
            st.dataframe(pd.DataFrame({
                "Seleção":[f"{code_to_flag(iso)} {name}" for iso,name in teams],
                "J":[0]*4,"V":[0]*4,"E":[0]*4,"D":[0]*4,"Pts":[0]*4
            }), use_container_width=True, hide_index=True)

# ════════════════════════════════════════════════════════
elif pagina == "📊 Grupos":
    st.subheader("📊 Grupos da Copa do Mundo 2026")
    st.caption("48 seleções · 12 grupos de 4 · Os 2 primeiros + 8 melhores 3ºs avançam")
    cols = st.columns(3)
    for i, (grp, teams) in enumerate(GRUPOS_PT.items()):
        with cols[i % 3]:
            st.markdown(f"<div class='grp-hdr'>Grupo {grp}</div>", unsafe_allow_html=True)
            for iso, name in teams:
                em = code_to_flag(iso)
                s = " style='background:rgba(0,156,59,.15);padding:2px 6px;border-radius:4px'" if name=="Brasil" else ""
                st.markdown(f"<div{s}>{em} {name}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
