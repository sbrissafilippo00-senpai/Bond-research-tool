
import streamlit as st
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime, date
import math

# ─────────────────────────────────────────────────────────────────
#  STATIC DB — Rating & Macro (aggiornamento manuale)
# ─────────────────────────────────────────────────────────────────
MACRO_DB = {
    "DE": {
        "paese":"Germania","valuta":"EUR","banca":"BCE",
        "sp":{"v":"AAA","out":"Stable","d":"2024-09"},
        "fitch":{"v":"AAA","out":"Stable","d":"2024-08"},
        "debt_pil":62.2,"debt_ref":"2024","hh_debt":49.1,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01DEM156N","fred_debt":"GGGDTADEA188N","fred_hh":"HDTGPDDEQ163N",
    },
    "IT": {
        "paese":"Italia","valuta":"EUR","banca":"BCE",
        "sp":{"v":"BBB+","out":"Positive","d":"2026-01"},
        "fitch":{"v":"BBB+","out":"Stable","d":"2025-10"},
        "debt_pil":135.3,"debt_ref":"2024","hh_debt":35.9,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01ITM156N","fred_debt":"GGGDTAITA188N","fred_hh":"HDTGPDITQ163N",
    },
    "ES": {
        "paese":"Spagna","valuta":"EUR","banca":"BCE",
        "sp":{"v":"A+","out":"Stable","d":"2025-04"},
        "fitch":{"v":"A-","out":"Positive","d":"2025-06"},
        "debt_pil":100.8,"debt_ref":"2025","hh_debt":43.0,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01ESM156N","fred_debt":"GGGDTAESA188N","fred_hh":"HDTGPDESQ163N",
    },
    "FR": {
        "paese":"Francia","valuta":"EUR","banca":"BCE",
        "sp":{"v":"AA-","out":"Negative","d":"2025-10"},
        "fitch":{"v":"AA-","out":"Negative","d":"2025-10"},
        "debt_pil":113.0,"debt_ref":"2024","hh_debt":59.9,"hh_ref":"2024",
        "fred_10y":"IRLTLT01FRM156N","fred_debt":"GGGDTAFRA188N","fred_hh":"HDTGPDFRA163N",
    },
    "NL": {
        "paese":"Olanda","valuta":"EUR","banca":"BCE",
        "sp":{"v":"AAA","out":"Stable","d":"2025-05"},
        "fitch":{"v":"AAA","out":"Stable","d":"2025-04"},
        "debt_pil":43.7,"debt_ref":"2024","hh_debt":97.2,"hh_ref":"Q4 2025",
        "fred_10y":"IRLTLT01NLM156N","fred_debt":"GGGDTANLA188N","fred_hh":"HDTGPDNLQ163N",
    },
    "PL": {
        "paese":"Polonia","valuta":"PLN","banca":"NBP",
        "sp":{"v":"A-","out":"Stable","d":"2025-03"},
        "fitch":{"v":"A-","out":"Stable","d":"2025-03"},
        "debt_pil":55.1,"debt_ref":"2024","hh_debt":35.0,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01PLM156N","fred_debt":"GGGDTAPLA188N","fred_hh":"HDTGPDPLQ163N",
    },
    "RO": {
        "paese":"Romania","valuta":"RON","banca":"BNR",
        "sp":{"v":"BBB-","out":"Negative","d":"2025-09"},
        "fitch":{"v":"BBB-","out":"Negative","d":"2025-09"},
        "debt_pil":59.4,"debt_ref":"2025","hh_debt":20.0,"hh_ref":"Q3 2025",
        "fred_10y":None,"fred_debt":"GGGDTAROA188N","fred_hh":None,
    },
}

ISIN_MAP = {
    "DE":"DE","IT":"IT","ES":"ES","FR":"FR",
    "NL":"NL","PL":"PL","RO":"RO","XS":None,
}

FLAGS = {
    "DE":"🇩🇪","IT":"🇮🇹","ES":"🇪🇸","FR":"🇫🇷",
    "NL":"🇳🇱","PL":"🇵🇱","RO":"🇷🇴"
}

# ─────────────────────────────────────────────────────────────────
#  BORSA ITALIANA SCRAPER
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)
def scrape_borsa_italiana(isin):
    """
    Scrapa i dati del titolo da Borsa Italiana.
    Prova diversi path per BTP, corporate, eurobond.
    """
    paths = [
        f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/obbligazioni-in-euro/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/obbligazioni-in-altre-valute/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/euromot/obbligazioni-euro/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/euromot/obbligazioni-altre-valute/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/extramot/scheda/{isin}.html",
    ]

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.borsaitaliana.it/",
    }

    result = {
        "descrizione": None, "prezzo": None, "divisa": None,
        "taglio_minimo": None, "data_rimborso": None,
        "tasso_cedolare": None, "periodicita": None,
        "scadenza": None, "duration": None, "convexity": None,
        "mercato": None, "source_url": None, "error": None,
    }

    for url in paths:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200 and len(r.text) > 500:
                soup = BeautifulSoup(r.text, "html.parser")

                # Titolo / Descrizione
                h1 = soup.find("h1")
                if h1:
                    result["descrizione"] = h1.get_text(strip=True)

                # Tavola dei dati scheda
                # Borsa Italiana usa una tabella con coppie label/valore
                tables = soup.find_all("table")
                for table in tables:
                    rows = table.find_all("tr")
                    for row in rows:
                        cells = row.find_all(["td", "th"])
                        if len(cells) >= 2:
                            label = cells[0].get_text(strip=True).lower()
                            value = cells[1].get_text(strip=True)

                            if any(x in label for x in ["prezzo", "ultimo", "price"]):
                                result["prezzo"] = value
                            elif any(x in label for x in ["valuta", "divisa", "currency"]):
                                result["divisa"] = value
                            elif any(x in label for x in ["taglio", "lotto", "minimum"]):
                                result["taglio_minimo"] = value
                            elif any(x in label for x in ["rimborso", "maturity", "scadenza"]):
                                result["data_rimborso"] = value
                                result["scadenza"] = value
                            elif any(x in label for x in ["cedola", "coupon", "tasso"]):
                                result["tasso_cedolare"] = value
                            elif any(x in label for x in ["periodicità", "periodicita", "frequency"]):
                                result["periodicita"] = value
                            elif "duration" in label and "modified" not in label:
                                result["duration"] = value
                            elif any(x in label for x in ["duration mod", "modified", "modificata"]):
                                result["duration"] = value
                            elif "convexity" in label or "convessità" in label:
                                result["convexity"] = value

                # Cerca anche nei div/span con classi specifiche BI
                for tag in soup.find_all(["span", "div", "td"], class_=re.compile(r"(price|last|value)", re.I)):
                    txt = tag.get_text(strip=True)
                    if re.match(r"^\d{2,3}[,.]\d{2,4}$", txt):
                        if not result["prezzo"]:
                            result["prezzo"] = txt

                result["source_url"] = url
                result["mercato"] = _extract_market(url)

                # Se abbiamo almeno il prezzo o la descrizione consideriamo ok
                if result["descrizione"] or result["prezzo"]:
                    return result

        except Exception as e:
            result["error"] = str(e)
            continue

    result["error"] = "Titolo non trovato su Borsa Italiana. Verifica ISIN o mercato di quotazione."
    return result


def _extract_market(url):
    if "mot/btp" in url:            return "MOT - BTP"
    if "mot/obbligazioni-in-euro" in url: return "MOT - Obbligazioni EUR"
    if "mot/obbligazioni-in-altre" in url: return "MOT - Obbligazioni altre valute"
    if "euromot/obbligazioni-euro" in url: return "EuroMOT - EUR"
    if "euromot/obbligazioni-altre" in url: return "EuroMOT - altre valute"
    if "extramot" in url:           return "ExtraMOT"
    return "Borsa Italiana"


# ─────────────────────────────────────────────────────────────────
#  FRED FETCHER
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fred_latest(sid):
    if not sid:
        return None, None
    try:
        r = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + sid,
            timeout=12
        )
        r.raise_for_status()
        for line in reversed(r.text.strip().split("\n")[1:]):
            p = line.split(",")
            if len(p) == 2 and p[1].strip() not in (".", ""):
                return float(p[1].strip()), p[0].strip()
    except:
        pass
    return None, None


# ─────────────────────────────────────────────────────────────────
#  CALCOLI FINANZIARI
# ─────────────────────────────────────────────────────────────────
def parse_float(s):
    """Converte stringa italiana (es. 98,34) in float."""
    if not s:
        return None
    try:
        return float(str(s).replace(".", "").replace(",", ".").strip().split()[0])
    except:
        return None

def parse_date(s):
    """Prova vari formati data."""
    if not s:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y"):
        try:
            return datetime.strptime(str(s).strip(), fmt).date()
        except:
            continue
    return None

def calc_ytm(prezzo, cedola_pct, anni, freq=1, face=100):
    """
    Calcola YTM (Yield to Maturity) con metodo Newton-Raphson.
    prezzo: prezzo di mercato (es. 98.5)
    cedola_pct: tasso cedolare annuo (es. 4.5 → 4.5%)
    anni: anni alla scadenza
    freq: frequenza cedole per anno (1=annuale, 2=semestrale)
    """
    if not prezzo or not cedola_pct or not anni or anni <= 0:
        return None
    try:
        c = (cedola_pct / 100 * face) / freq
        n = int(round(anni * freq))
        p = prezzo

        def price_fn(y):
            r = y / freq
            pv = sum(c / (1 + r)**t for t in range(1, n + 1))
            pv += face / (1 + r)**n
            return pv - p

        # Bisezione robusta
        lo, hi = -0.5, 2.0
        for _ in range(100):
            mid = (lo + hi) / 2
            if abs(price_fn(mid)) < 1e-8:
                break
            if price_fn(lo) * price_fn(mid) < 0:
                hi = mid
            else:
                lo = mid
        return round(mid * freq * 100, 4)
    except:
        return None

def calc_duration_mod(prezzo, cedola_pct, anni, ytm, freq=1, face=100):
    """Duration modificata."""
    if not all([prezzo, cedola_pct, anni, ytm]):
        return None
    try:
        c  = (cedola_pct / 100 * face) / freq
        n  = int(round(anni * freq))
        y  = ytm / 100 / freq
        mac_dur = sum(
            (t / freq) * c / (1 + y)**t for t in range(1, n + 1)
        ) + (n / freq) * face / (1 + y)**n
        mac_dur /= prezzo
        return round(mac_dur / (1 + y), 4)
    except:
        return None

def calc_convexity(prezzo, cedola_pct, anni, ytm, freq=1, face=100):
    """Convexity."""
    if not all([prezzo, cedola_pct, anni, ytm]):
        return None
    try:
        c = (cedola_pct / 100 * face) / freq
        n = int(round(anni * freq))
        y = ytm / 100 / freq
        conv = sum(
            t * (t + 1) * c / (1 + y)**(t + 2) for t in range(1, n + 1)
        ) + n * (n + 1) * face / (1 + y)**(n + 2)
        conv /= prezzo * freq**2
        return round(conv, 4)
    except:
        return None

def anni_alla_scadenza(data_str):
    d = parse_date(data_str)
    if not d:
        return None
    oggi = date.today()
    return max(round((d - oggi).days / 365.25, 4), 0)


# ─────────────────────────────────────────────────────────────────
#  COLOR / UI HELPERS
# ─────────────────────────────────────────────────────────────────
def rc(v):
    if v in ("AAA","AA+","AA","AA-"): return "#22c55e"
    if v in ("A+","A","A-"):          return "#eab308"
    if v in ("BBB+","BBB","BBB-"):    return "#f97316"
    return "#ef4444"

def dc(v):
    if v is None: return "#94a3b8"
    if v < 60:    return "#22c55e"
    if v < 100:   return "#eab308"
    if v < 130:   return "#f97316"
    return "#ef4444"

def sc(bp):
    if bp is None: return "#94a3b8"
    if bp <= 30:   return "#22c55e"
    if bp <= 80:   return "#eab308"
    if bp <= 150:  return "#f97316"
    return "#ef4444"

def card(label, val, sub="", col="#0f172a", bg="#f8fafc"):
    st.markdown(
        f"""<div style="background:{bg};border-radius:10px;padding:14px 18px;
        border-left:5px solid {col};margin-bottom:8px;">
        <div style="font-size:10px;color:#64748b;font-weight:700;
        text-transform:uppercase;letter-spacing:.08em;">{label}</div>
        <div style="font-size:22px;font-weight:800;color:{col};margin:3px 0 2px;">{val}</div>
        <div style="font-size:11px;color:#94a3b8;">{sub}</div>
        </div>""",
        unsafe_allow_html=True
    )

def section(title, icon=""):
    st.markdown(
        f"<h4 style=\"margin:24px 0 12px;color:#0f172a;\"><span style=\"margin-right:6px;\">{icon}</span>{title}</h4>",
        unsafe_allow_html=True
    )

def badge_html(text, color):
    return f"<span style=\"background:{color}20;color:{color};border:1px solid {color}50;border-radius:6px;padding:2px 8px;font-size:12px;font-weight:600;\">{text}</span>"


# ─────────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bond Research Tool",
    page_icon="🏦",
    layout="wide"
)

# Header
st.markdown("""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);
padding:28px 32px;border-radius:14px;margin-bottom:24px;">
<div style="display:flex;align-items:center;gap:16px;">
<div>
<div style="font-size:28px;font-weight:800;color:white;letter-spacing:-.5px;">
🏦 Bond Research Tool</div>
<div style="font-size:12px;color:#93c5fd;font-weight:600;
text-transform:uppercase;letter-spacing:.12em;margin-top:4px;">
B-Adviser S.r.l. | Analisi e Consulenza Finanziaria</div>
</div>
</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
#  TABS
# ─────────────────────────────────────────────────────────────────
tab_gov, tab_corp = st.tabs(["🏛️  Governativi", "🏢  Corporate"])


# ══════════════════════════════════════════════════════════════════
#  TAB 1 — GOVERNATIVI
# ══════════════════════════════════════════════════════════════════
with tab_gov:

    st.markdown("### Inserisci ISIN Governativo")
    c1, c2 = st.columns([4, 1])
    with c1:
        isin_gov = st.text_input(
            "ISIN", key="isin_gov",
            placeholder="es. IT0005534984",
            label_visibility="collapsed"
        ).strip().upper()
    with c2:
        go_gov = st.button("🔍 Analizza", key="btn_gov",
                           use_container_width=True, type="primary")

    st.caption("Esempi: IT0005534984 (BTP) · DE0001102580 (Bund) · ES0000012B39 (Bonos) · FR0014004L86 (OAT) · NL0015614236 (DSL)")

    if go_gov and isin_gov:
        # ── Validazione ISIN
        if len(isin_gov) != 12 or not isin_gov[:2].isalpha() or not isin_gov[2:].isalnum():
            st.error("❌ ISIN non valido. Formato: 2 lettere + 10 caratteri  es. IT0005534984")
            st.stop()

        prefix = isin_gov[:2]
        if prefix not in ISIN_MAP:
            st.error(f"Prefisso **{prefix}** non nel database. Supportati: {list(ISIN_MAP.keys())}")
            st.stop()

        code = ISIN_MAP[prefix]
        if code is None:
            st.warning("Prefisso XS = Eurobond internazionale. Paese da identificare manualmente.")
            st.stop()

        macro = MACRO_DB[code]
        flag  = FLAGS.get(code, "🏳️")

        # ── Fetch dati
        col_prog = st.columns(2)
        with col_prog[0]:
            with st.spinner("📡 FRED: recupero rendimenti e macro..."):
                bund_y,  bund_d  = fred_latest("IRLTLT01DEM156N")
                ctry_y,  ctry_d  = fred_latest(macro.get("fred_10y"))
                debt_v,  debt_d  = fred_latest(macro.get("fred_debt"))
                hh_v,    hh_d    = fred_latest(macro.get("fred_hh"))

        with col_prog[1]:
            with st.spinner("🌐 Borsa Italiana: recupero dati titolo..."):
                bi = scrape_borsa_italiana(isin_gov)

        # ── Calcoli spread
        if code == "DE":
            spread_bp = 0.0
        elif bund_y and ctry_y:
            spread_bp = round((ctry_y - bund_y) * 100, 1)
        else:
            spread_bp = None

        # ── Calcoli finanziari
        prezzo_f    = parse_float(bi.get("prezzo"))
        cedola_f    = parse_float(bi.get("tasso_cedolare"))
        scadenza_s  = bi.get("data_rimborso") or bi.get("scadenza")
        anni_f      = anni_alla_scadenza(scadenza_s)

        # Frequenza cedola
        periodo_raw = (bi.get("periodicita") or "").lower()
        if "semi" in periodo_raw or "6" in periodo_raw:
            freq = 2
        elif "trim" in periodo_raw or "3" in periodo_raw:
            freq = 4
        else:
            freq = 1

        ytm       = calc_ytm(prezzo_f, cedola_f, anni_f, freq)
        dur_mod   = calc_duration_mod(prezzo_f, cedola_f, anni_f, ytm, freq) if bi.get("duration") is None else None
        conv      = calc_convexity(prezzo_f, cedola_f, anni_f, ytm, freq) if bi.get("convexity") is None else None

        # ── HEADER risultato
        st.divider()
        st.markdown(f"""
        <div style="background:#f1f5f9;border-radius:10px;padding:16px 22px;margin-bottom:20px;">
        <div style="font-size:20px;font-weight:800;color:#0f172a;">{flag} {isin_gov}</div>
        <div style="color:#475569;font-size:14px;margin-top:3px;">
        {bi.get("descrizione") or "—"} &nbsp;·&nbsp;
        {macro["paese"]} &nbsp;·&nbsp; {macro["valuta"]} &nbsp;·&nbsp;
        {bi.get("mercato") or "Borsa Italiana"} &nbsp;·&nbsp; Governativo Sovrano
        </div>
        </div>
        """, unsafe_allow_html=True)

        # ── SEZIONE 1: Dati Titolo
        section("Dati del Titolo", "📋")

        r1a, r1b, r1c = st.columns(3)
        with r1a:
            card("ISIN", isin_gov, bi.get("descrizione") or "—")
            card("Paese", f"{flag} {macro['paese']}", macro["valuta"])
            card("Divisa", bi.get("divisa") or macro["valuta"], "valuta di denominazione")
        with r1b:
            card("Prezzo di regolamento",
                 f"{prezzo_f:.2f}" if prezzo_f else (bi.get("prezzo") or "N/D"),
                 "ultimo prezzo Borsa Italiana")
            card("Tasso cedolare",
                 f"{cedola_f:.3f}%" if cedola_f else (bi.get("tasso_cedolare") or "N/D"),
                 f"periodicità: {bi.get('periodicita') or '—'}")
            card("Taglio Minimo",
                 bi.get("taglio_minimo") or "N/D",
                 "lotto minimo acquistabile")
        with r1c:
            card("Scadenza",
                 bi.get("data_rimborso") or "N/D",
                 f"anni residui: {anni_f:.2f}" if anni_f else "")
            card("Data Rimborso", bi.get("data_rimborso") or "N/D", "data finale rimborso capitale")
            card("Mercato", bi.get("mercato") or "—", "piazza di quotazione")

        # ── SEZIONE 2: Rating & Macro
        section("Rating & Solidità Paese", "📊")

        sp = macro["sp"]; fi = macro["fitch"]
        r2a, r2b = st.columns(2)
        with r2a:
            card("S&P Global", sp["v"],
                 f"Outlook: {sp['out']}  |  [{sp['d']}]", rc(sp["v"]))
        with r2b:
            card("Fitch", fi["v"],
                 f"Outlook: {fi['out']}  |  [{fi['d']}]", rc(fi["v"]))

        if "Negative" in [sp["out"], fi["out"]]:
            st.warning("⚠️ Outlook NEGATIVO — rischio downgrade attivo")

        debt  = debt_v if debt_v else macro["debt_pil"]
        hh    = hh_v   if hh_v   else macro["hh_debt"]

        r2c, r2d = st.columns(2)
        with r2c:
            dl = "Sostenibile" if debt < 60 else ("Moderato" if debt < 100 else ("Elevato" if debt < 130 else "Zona critica"))
            card("Debito / PIL", f"{debt:.1f}%",
                 f"{dl}  |  rif. {debt_d or macro['debt_ref']}", dc(debt))
        with r2d:
            hl = "Contenuto" if hh < 50 else ("Moderato" if hh < 80 else "Elevato")
            card("Household Debt / PIL", f"{hh:.1f}%",
                 f"{hl}  |  rif. {hh_d or macro['hh_ref']}", dc(hh))

        # Gauge Debt/PIL
        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=debt,
            number={"suffix":"%","font":{"size":24}},
            title={"text":"Debito / PIL","font":{"size":12}},
            gauge={
                "axis":{"range":[0,200]},
                "bar":{"color":dc(debt),"thickness":0.25},
                "steps":[
                    {"range":[0,60],"color":"#dcfce7"},
                    {"range":[60,100],"color":"#fef9c3"},
                    {"range":[100,130],"color":"#ffedd5"},
                    {"range":[130,200],"color":"#fee2e2"},
                ],
                "threshold":{"line":{"color":"#dc2626","width":3},"value":130}
            }
        ))
        fig_g.update_layout(height=180, margin=dict(t=25,b=0,l=10,r=10),
                            paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g, use_container_width=True)

        # ── SEZIONE 3: Spread
        section("Spread vs Bund 10Y", "📡")
        r3a, r3b, r3c = st.columns(3)
        with r3a:
            card("Bund 10Y",
                 f"{bund_y:.3f}%" if bund_y else "N/D",
                 f"rif. {bund_d}" if bund_d else "FRED")
        with r3b:
            card(f"{macro['paese']} 10Y",
                 f"{ctry_y:.3f}%" if ctry_y else "N/D",
                 f"rif. {ctry_d}" if ctry_d else "FRED")
        with r3c:
            if code == "DE":
                card("Spread vs Bund", "0 bp", "Germania = benchmark", "#22c55e")
            elif spread_bp is not None:
                bp_label = ("Basso" if spread_bp<=30 else
                            "Moderato" if spread_bp<=80 else
                            "Rilevante" if spread_bp<=150 else
                            "Elevato" if spread_bp<=300 else "Critico")
                card("Spread vs Bund", f"{spread_bp:+.1f} bp", bp_label, sc(spread_bp))
            else:
                card("Spread vs Bund", "N/D", "rendimento non su FRED", "#94a3b8")

        # ── SEZIONE 4: Analisi Rendimento
        section("Analisi Rendimento & Rischio", "💹")

        # Tassazione (input manuale)
        col_tax, col_empty = st.columns([1, 3])
        with col_tax:
            tax_rate = st.number_input(
                "Aliquota fiscale (%)",
                min_value=0.0, max_value=50.0,
                value=12.5, step=0.5,
                help="12,5% per titoli di stato UE — 26% per corporate"
            )

        rend_lordo = ytm
        rend_netto = round(ytm * (1 - tax_rate / 100), 4) if ytm else None

        r4a, r4b, r4c, r4d = st.columns(4)
        with r4a:
            card("Rendimento Lordo",
                 f"{rend_lordo:.3f}%" if rend_lordo else "N/D",
                 "YTM calcolato dal tool",
                 "#0f172a" if not rend_lordo else ("#22c55e" if rend_lordo > 0 else "#ef4444"))
        with r4b:
            card("Rendimento Netto",
                 f"{rend_netto:.3f}%" if rend_netto else "N/D",
                 f"al netto del {tax_rate}%",
                 "#0f172a" if not rend_netto else ("#22c55e" if rend_netto > 0 else "#ef4444"))
        with r4c:
            dur_display = bi.get("duration") or (f"{dur_mod:.3f}" if dur_mod else None)
            card("Duration Modificata",
                 dur_display or "N/D",
                 "sensibilità ai tassi")
        with r4d:
            conv_display = bi.get("convexity") or (f"{conv:.3f}" if conv else None)
            card("Convexity",
                 conv_display or "N/D",
                 "curvatura prezzo/rendimento")

        card("Tassazione applicata", f"{tax_rate}%",
             "12,5% gov. UE  |  26% corporate  |  modificabile sopra")

        # ── SEZIONE 5: Tabella Riepilogo
        section("Riepilogo Scheda Completa", "📄")

        recap = {
            "Campo": [
                "ISIN","Descrizione","Paese","Rating (S&P / Fitch)",
                "Debito/PIL","Household Debt/PIL","Spread vs Bund",
                "Prezzo di regolamento","Divisa","Taglio Minimo",
                "Data Rimborso","Tasso cedolare","Periodicità cedola",
                "Scadenza","Duration Modificata","Convexity",
                "Rend. Lordo","Rend. Netto","Tassazione applicata"
            ],
            "Valore": [
                isin_gov,
                bi.get("descrizione") or "—",
                f"{flag} {macro['paese']}",
                f"{sp['v']} / {fi['v']}",
                f"{debt:.1f}%",
                f"{hh:.1f}%",
                f"{spread_bp:+.1f} bp" if spread_bp is not None else "N/D",
                f"{prezzo_f:.2f}" if prezzo_f else (bi.get("prezzo") or "N/D"),
                bi.get("divisa") or macro["valuta"],
                bi.get("taglio_minimo") or "N/D",
                bi.get("data_rimborso") or "N/D",
                f"{cedola_f:.3f}%" if cedola_f else (bi.get("tasso_cedolare") or "N/D"),
                bi.get("periodicita") or "—",
                bi.get("scadenza") or "N/D",
                dur_display or "N/D",
                conv_display or "N/D",
                f"{rend_lordo:.3f}%" if rend_lordo else "N/D",
                f"{rend_netto:.3f}%" if rend_netto else "N/D",
                f"{tax_rate}%",
            ],
        }
        df_recap = pd.DataFrame(recap)
        st.dataframe(df_recap, use_container_width=True, hide_index=True, height=640)

        # Nota fonte
        if bi.get("source_url"):
            st.caption(f"📌 Fonte dati titolo: {bi['source_url']}")
        if bi.get("error") and not bi.get("prezzo"):
            st.warning(f"⚠️ Borsa Italiana: {bi['error']}")

        st.divider()
        st.caption(
            "Dati macro/rendimenti: FRED (St. Louis Fed) live · "
            "Dati titolo: Borsa Italiana · "
            "YTM, Duration, Convexity calcolati dal tool · "
            "Non costituisce consulenza finanziaria · "
            "B-Adviser S.r.l. | info@bankadviser.it"
        )


# ══════════════════════════════════════════════════════════════════
#  TAB 2 — CORPORATE
# ══════════════════════════════════════════════════════════════════
with tab_corp:

    st.markdown("### Inserisci ISIN Corporate")
    c1c, c2c = st.columns([4, 1])
    with c1c:
        isin_corp = st.text_input(
            "ISIN Corporate", key="isin_corp",
            placeholder="es. XS2543893458",
            label_visibility="collapsed"
        ).strip().upper()
    with c2c:
        go_corp = st.button("🔍 Analizza", key="btn_corp",
                            use_container_width=True, type="primary")

    st.caption("Inserisci l'ISIN di un'obbligazione corporate (societaria) quotata su Borsa Italiana")

    # ── Form dati emittente (corporate)
    with st.expander("📝 Dati Emittente Corporate (compilazione manuale)", expanded=False):
        st.markdown("*Compila i dati fondamentali dell'emittente — verranno usati nell'analisi*")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            corp_nome    = st.text_input("Nome Emittente", placeholder="es. ENI S.p.A.")
            corp_paese   = st.text_input("Paese", placeholder="es. Italia")
            corp_settore = st.text_input("Settore", placeholder="es. Energia")
            corp_rating  = st.text_input("Rating (S&P)", placeholder="es. BBB+")
        with cc2:
            corp_ebitda  = st.number_input("EBITDA (MLD)", min_value=0.0, step=0.1)
            corp_debito  = st.number_input("Debito Totale (MLD)", min_value=0.0, step=0.1)
            corp_fcf     = st.number_input("Free Cash Flow (MLD)", min_value=-100.0, step=0.1)
            corp_margine = st.number_input("Margine EBITDA (%)", min_value=0.0, max_value=100.0, step=0.1)
        with cc3:
            corp_leva    = st.number_input("Leva (Debito/EBITDA)", min_value=0.0, step=0.1)
            corp_cov_int = st.number_input("Copertura Interessi (EBITDA/Int.)", min_value=0.0, step=0.1)
            corp_valuta  = st.selectbox("Valuta", ["EUR","USD","GBP","CHF","PLN","RON"])
            corp_seniority = st.selectbox("Seniority", [
                "Senior Secured","Senior Unsecured",
                "Senior Non-Preferred","Subordinato","Tier 1","Tier 2"
            ])

    if go_corp and isin_corp:
        if len(isin_corp) != 12 or not isin_corp[:2].isalpha() or not isin_corp[2:].isalnum():
            st.error("❌ ISIN non valido. Formato: 2 lettere + 10 caratteri")
            st.stop()

        with st.spinner("🌐 Borsa Italiana: recupero dati titolo..."):
            bi_c = scrape_borsa_italiana(isin_corp)

        # Calcoli
        prezzo_c   = parse_float(bi_c.get("prezzo"))
        cedola_c   = parse_float(bi_c.get("tasso_cedolare"))
        scadenza_c = bi_c.get("data_rimborso") or bi_c.get("scadenza")
        anni_c     = anni_alla_scadenza(scadenza_c)

        periodo_c  = (bi_c.get("periodicita") or "").lower()
        freq_c = 2 if ("semi" in periodo_c or "6" in periodo_c) else (4 if "trim" in periodo_c else 1)

        ytm_c    = calc_ytm(prezzo_c, cedola_c, anni_c, freq_c)
        dur_c    = calc_duration_mod(prezzo_c, cedola_c, anni_c, ytm_c, freq_c) if not bi_c.get("duration") else None
        conv_c   = calc_convexity(prezzo_c, cedola_c, anni_c, ytm_c, freq_c) if not bi_c.get("convexity") else None

        # Ratios corporate
        debt_ebitda = round(corp_debito / corp_ebitda, 2) if corp_ebitda > 0 else None
        fcf_debt    = round(corp_fcf / corp_debito * 100, 2) if corp_debito > 0 else None

        # Header risultato
        st.divider()
        st.markdown(f"""
        <div style="background:#f1f5f9;border-radius:10px;padding:16px 22px;margin-bottom:20px;">
        <div style="font-size:20px;font-weight:800;color:#0f172a;">🏢 {isin_corp}</div>
        <div style="color:#475569;font-size:14px;margin-top:3px;">
        {bi_c.get("descrizione") or corp_nome or "—"} &nbsp;·&nbsp;
        {corp_paese or "—"} &nbsp;·&nbsp; {corp_settore or "—"} &nbsp;·&nbsp;
        {bi_c.get("mercato") or "Borsa Italiana"} &nbsp;·&nbsp;
        {corp_seniority}
        </div>
        </div>
        """, unsafe_allow_html=True)

        # ── S1: Dati Titolo
        section("Dati del Titolo", "📋")
        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            card("ISIN", isin_corp, bi_c.get("descrizione") or "—")
            card("Emittente", corp_nome or "—", corp_settore or "—")
            card("Divisa", bi_c.get("divisa") or corp_valuta)
        with rc2:
            card("Prezzo di regolamento",
                 f"{prezzo_c:.2f}" if prezzo_c else (bi_c.get("prezzo") or "N/D"),
                 "ultimo prezzo Borsa Italiana")
            card("Tasso cedolare",
                 f"{cedola_c:.3f}%" if cedola_c else (bi_c.get("tasso_cedolare") or "N/D"),
                 f"periodicità: {bi_c.get('periodicita') or '—'}")
            card("Taglio Minimo", bi_c.get("taglio_minimo") or "N/D")
        with rc3:
            card("Scadenza", bi_c.get("data_rimborso") or "N/D",
                 f"anni residui: {anni_c:.2f}" if anni_c else "")
            card("Seniority", corp_seniority)
            card("Mercato", bi_c.get("mercato") or "—")

        # ── S2: Rating
        section("Rating & Solidità Emittente", "📊")
        if corp_rating:
            card("Rating S&P", corp_rating, f"{corp_nome} — {corp_settore}", rc(corp_rating))

        if corp_ebitda > 0:
            rf1, rf2, rf3, rf4 = st.columns(4)
            with rf1:
                leva_col = "#22c55e" if (debt_ebitda and debt_ebitda < 2) else ("#eab308" if (debt_ebitda and debt_ebitda < 4) else "#ef4444")
                card("Debito / EBITDA",
                     f"{debt_ebitda:.2f}x" if debt_ebitda else "N/D",
                     "< 2x ottimo | > 4x critico", leva_col)
            with rf2:
                card("EBITDA", f"{corp_ebitda:.1f} MLD", "risultato operativo lordo")
            with rf3:
                card("Free Cash Flow", f"{corp_fcf:.1f} MLD",
                     f"FCF/Debito: {fcf_debt:.1f}%" if fcf_debt else "")
            with rf4:
                card("Leva Finanziaria",
                     f"{corp_leva:.2f}x" if corp_leva else (f"{debt_ebitda:.2f}x" if debt_ebitda else "N/D"),
                     "inserita manualmente")

        # ── S3: Rendimento
        section("Analisi Rendimento & Rischio", "💹")
        col_tax_c, _ = st.columns([1, 3])
        with col_tax_c:
            tax_rate_c = st.number_input(
                "Aliquota fiscale (%)", key="tax_corp",
                min_value=0.0, max_value=50.0,
                value=26.0, step=0.5,
                help="26% per obbligazioni corporate"
            )

        rend_lordo_c = ytm_c
        rend_netto_c = round(ytm_c * (1 - tax_rate_c / 100), 4) if ytm_c else None

        rr1, rr2, rr3, rr4 = st.columns(4)
        with rr1:
            card("Rend. Lordo",
                 f"{rend_lordo_c:.3f}%" if rend_lordo_c else "N/D",
                 "YTM", "#0f172a")
        with rr2:
            card("Rend. Netto",
                 f"{rend_netto_c:.3f}%" if rend_netto_c else "N/D",
                 f"al netto del {tax_rate_c}%", "#0f172a")
        with rr3:
            dur_c_display = bi_c.get("duration") or (f"{dur_c:.3f}" if dur_c else None)
            card("Duration Modificata", dur_c_display or "N/D")
        with rr4:
            conv_c_display = bi_c.get("convexity") or (f"{conv_c:.3f}" if conv_c else None)
            card("Convexity", conv_c_display or "N/D")

        # ── S4: Riepilogo tabella
        section("Riepilogo Scheda Completa", "📄")
        recap_c = {
            "Campo": [
                "ISIN","Descrizione","Paese","Settore","Rating (S&P)",
                "EBITDA","Debito","Debito/EBITDA","Free Cash Flow",
                "FCF/Totale Debito","Margine EBITDA","Leva Finanziaria",
                "Prezzo di regolamento","Divisa","Taglio Minimo",
                "Data Rimborso","Tasso cedolare","Periodicità cedola",
                "Scadenza","Seniority","Duration Modificata","Convexity",
                "Rend. Lordo","Rend. Netto","Tassazione applicata"
            ],
            "Valore": [
                isin_corp,
                bi_c.get("descrizione") or corp_nome or "—",
                corp_paese or "—",
                corp_settore or "—",
                corp_rating or "—",
                f"{corp_ebitda:.1f} MLD" if corp_ebitda else "—",
                f"{corp_debito:.1f} MLD" if corp_debito else "—",
                f"{debt_ebitda:.2f}x" if debt_ebitda else "—",
                f"{corp_fcf:.1f} MLD" if corp_fcf else "—",
                f"{fcf_debt:.1f}%" if fcf_debt else "—",
                f"{corp_margine:.1f}%" if corp_margine else "—",
                f"{corp_leva:.2f}x" if corp_leva else "—",
                f"{prezzo_c:.2f}" if prezzo_c else (bi_c.get("prezzo") or "N/D"),
                bi_c.get("divisa") or corp_valuta,
                bi_c.get("taglio_minimo") or "N/D",
                bi_c.get("data_rimborso") or "N/D",
                f"{cedola_c:.3f}%" if cedola_c else (bi_c.get("tasso_cedolare") or "N/D"),
                bi_c.get("periodicita") or "—",
                bi_c.get("scadenza") or "N/D",
                corp_seniority,
                dur_c_display or "N/D",
                conv_c_display or "N/D",
                f"{rend_lordo_c:.3f}%" if rend_lordo_c else "N/D",
                f"{rend_netto_c:.3f}%" if rend_netto_c else "N/D",
                f"{tax_rate_c}%",
            ],
        }
        df_recap_c = pd.DataFrame(recap_c)
        st.dataframe(df_recap_c, use_container_width=True, hide_index=True, height=780)

        if bi_c.get("source_url"):
            st.caption(f"📌 Fonte dati titolo: {bi_c['source_url']}")
        if bi_c.get("error") and not bi_c.get("prezzo"):
            st.warning(f"⚠️ Borsa Italiana: {bi_c['error']}")

        st.divider()
        st.caption(
            "Dati titolo: Borsa Italiana · "
            "Dati emittente: inserimento manuale · "
            "YTM, Duration, Convexity calcolati dal tool · "
            "Non costituisce consulenza finanziaria · "
            "B-Adviser S.r.l. | info@bankadviser.it"
        )

    elif not go_corp:
        st.info("📌 Inserisci l'ISIN dell'obbligazione corporate e compila i dati dell'emittente nell'apposito pannello, poi clicca **Analizza**.")
