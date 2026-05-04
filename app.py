
import streamlit as st
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime, date
import math

# ─────────────────────────────────────────────────────────────────
#  STATIC DB
# ─────────────────────────────────────────────────────────────────
MACRO_DB = {
    "DE": {
        "paese":"Germania","valuta":"EUR","banca":"BCE",
        "sp":{"v":"AAA","out":"Stable","d":"2024-09"},
        "fitch":{"v":"AAA","out":"Stable","d":"2024-08"},
        "debt_pil":62.2,"debt_ref":"2024","hh_debt":49.1,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01DEM156N","fred_debt":"GGGDTADEA188N","fred_hh":"HDTGPDDEQ163N",
        "spread_auto":True,
    },
    "IT": {
        "paese":"Italia","valuta":"EUR","banca":"BCE",
        "sp":{"v":"BBB+","out":"Positive","d":"2026-01"},
        "fitch":{"v":"BBB+","out":"Stable","d":"2025-10"},
        "debt_pil":135.3,"debt_ref":"2024","hh_debt":35.9,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01ITM156N","fred_debt":"GGGDTAITA188N","fred_hh":"HDTGPDITQ163N",
        "spread_auto":True,
    },
    "ES": {
        "paese":"Spagna","valuta":"EUR","banca":"BCE",
        "sp":{"v":"A+","out":"Stable","d":"2025-04"},
        "fitch":{"v":"A-","out":"Positive","d":"2025-06"},
        "debt_pil":100.8,"debt_ref":"2025","hh_debt":43.0,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01ESM156N","fred_debt":"GGGDTAESA188N","fred_hh":"HDTGPDESQ163N",
        "spread_auto":True,
    },
    "FR": {
        "paese":"Francia","valuta":"EUR","banca":"BCE",
        "sp":{"v":"AA-","out":"Negative","d":"2025-10"},
        "fitch":{"v":"AA-","out":"Negative","d":"2025-10"},
        "debt_pil":113.0,"debt_ref":"2024","hh_debt":59.9,"hh_ref":"2024",
        "fred_10y":"IRLTLT01FRM156N","fred_debt":"GGGDTAFRA188N","fred_hh":"HDTGPDFRA163N",
        "spread_auto":True,
    },
    "NL": {
        "paese":"Olanda","valuta":"EUR","banca":"BCE",
        "sp":{"v":"AAA","out":"Stable","d":"2025-05"},
        "fitch":{"v":"AAA","out":"Stable","d":"2025-04"},
        "debt_pil":43.7,"debt_ref":"2024","hh_debt":97.2,"hh_ref":"Q4 2025",
        "fred_10y":"IRLTLT01NLM156N","fred_debt":"GGGDTANLA188N","fred_hh":"HDTGPDNLQ163N",
        "spread_auto":False,
    },
    "PL": {
        "paese":"Polonia","valuta":"PLN","banca":"NBP",
        "sp":{"v":"A-","out":"Stable","d":"2025-03"},
        "fitch":{"v":"A-","out":"Stable","d":"2025-03"},
        "debt_pil":55.1,"debt_ref":"2024","hh_debt":35.0,"hh_ref":"Q3 2025",
        "fred_10y":"IRLTLT01PLM156N","fred_debt":"GGGDTAPLA188N","fred_hh":"HDTGPDPLQ163N",
        "spread_auto":False,
    },
    "RO": {
        "paese":"Romania","valuta":"RON","banca":"BNR",
        "sp":{"v":"BBB-","out":"Negative","d":"2025-09"},
        "fitch":{"v":"BBB-","out":"Negative","d":"2025-09"},
        "debt_pil":59.4,"debt_ref":"2025","hh_debt":20.0,"hh_ref":"Q3 2025",
        "fred_10y":None,"fred_debt":"GGGDTAROA188N","fred_hh":None,
        "spread_auto":False,
    },
}

ISIN_MAP = {
    "DE":"DE","IT":"IT","ES":"ES","FR":"FR",
    "NL":"NL","PL":"PL","RO":"RO","XS":None,
}

FLAGS = {"DE":"🇩🇪","IT":"🇮🇹","ES":"🇪🇸","FR":"🇫🇷","NL":"🇳🇱","PL":"🇵🇱","RO":"🇷🇴"}

# ─────────────────────────────────────────────────────────────────
#  BORSA ITALIANA SCRAPER
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900)
def scrape_borsa_italiana(isin):
    paths = [
        f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/btp/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/obbligazioni-in-euro/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/obbligazioni-in-altre-valute/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/euromot/obbligazioni-euro/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/euromot/obbligazioni-altre-valute/scheda/{isin}.html",
        f"https://www.borsaitaliana.it/borsa/obbligazioni/extramot/scheda/{isin}.html",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.borsaitaliana.it/",
    }
    result = {
        "descrizione":None,"prezzo":None,"divisa":None,
        "taglio_minimo":None,"data_rimborso":None,
        "tasso_cedolare":None,"periodicita":None,
        "scadenza":None,"duration":None,"convexity":None,
        "mercato":None,"source_url":None,"error":None,
    }

    for url in paths:
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200 or len(r.text) < 500:
                continue
            soup = BeautifulSoup(r.text, "html.parser")

            # Descrizione
            for tag in ["h1","h2"]:
                el = soup.find(tag)
                if el and len(el.get_text(strip=True)) > 4:
                    result["descrizione"] = el.get_text(strip=True)
                    break

            # Raccolta coppie label→valore da tutte le strutture
            pairs = []
            for row in soup.find_all("tr"):
                cells = row.find_all(["td","th"])
                if len(cells) >= 2:
                    pairs.append((cells[0].get_text(" ",strip=True), cells[1].get_text(" ",strip=True)))
            for dl in soup.find_all("dl"):
                dts = dl.find_all("dt"); dds = dl.find_all("dd")
                for dt,dd in zip(dts,dds):
                    pairs.append((dt.get_text(" ",strip=True), dd.get_text(" ",strip=True)))

            for label_raw, value_raw in pairs:
                label = label_raw.lower().strip()
                value = value_raw.strip()
                if not value or value in ("-","—","n/a","n.d.","nd"):
                    continue

                if any(x in label for x in ["ultimo prezzo","last price","prezzo ufficiale","prezzo di riferimento"]):
                    if not result["prezzo"] and re.search(r"\d{2,3}[,.]?\d{0,4}", value):
                        result["prezzo"] = value
                elif any(x in label for x in ["valuta","divisa","currency"]):
                    if not result["divisa"]:
                        result["divisa"] = value.upper().split("/")[0].strip()
                elif any(x in label for x in ["lotto minimo","taglio minimo","minimum denomination"]):
                    if not result["taglio_minimo"]:
                        result["taglio_minimo"] = value
                elif any(x in label for x in ["data di scadenza","data scadenza","maturity date","scadenza","rimborso"]):
                    if not result["data_rimborso"]:
                        result["data_rimborso"] = value
                        result["scadenza"] = value
                elif any(x in label for x in ["tasso cedola","cedola","coupon rate","tasso interesse","tasso nominale","tasso annuo","interest rate","coupon"]):
                    if not result["tasso_cedolare"]:
                        # % OBBLIGATORIO per evitare falsi positivi da altri campi numerici
                        m = re.search(r"(\d+[,.]?\d*)\s*%", value)
                        if m:
                            v = float(m.group(1).replace(",","."))
                            if 0.001 <= v <= 25.0:  # range ragionevole per una cedola
                                result["tasso_cedolare"] = str(v)
                elif any(x in label for x in ["periodicità","periodicita","frequency","frequenza","stacco cedola"]):
                    if not result["periodicita"]:
                        result["periodicita"] = value
                elif re.search(r"duration\s*(modif|mod\.?|modified)", label):
                    if not result["duration"]:
                        result["duration"] = value
                elif any(x in label for x in ["convexity","convessità","convessita"]):
                    if not result["convexity"]:
                        result["convexity"] = value

            # Fallback prezzo
            if not result["prezzo"]:
                for tag in soup.find_all(["span","div","td","strong"], class_=re.compile(r"(price|last|quot|value)",re.I)):
                    txt = tag.get_text(strip=True).replace("\xa0","")
                    m = re.match(r"^(\d{2,3}[,.]\d{2,4})$", txt)
                    if m:
                        result["prezzo"] = m.group(1)
                        break

            # Fallback cedola dal nome titolo (es. "BTP Tf 4,5% Ot53", "Obligaciones Tf 4,9% Lg40")
            if not result["tasso_cedolare"] and result["descrizione"]:
                m = re.search(r"(\d+[,.]?\d+)\s*%", result["descrizione"])
                if m:
                    v = float(m.group(1).replace(",","."))
                    if 0.001 <= v <= 25.0:  # range ragionevole
                        result["tasso_cedolare"] = str(v)

            # Fallback periodicità: BTP/Bund/OAT/Bonos → semestrale
            if not result["periodicita"] and result["descrizione"]:
                desc_l = result["descrizione"].lower()
                if any(x in desc_l for x in ["btp","bund","oat","bonos","dsl"]):
                    result["periodicita"] = "Semestrale"

            # Fallback scadenza dal nome titolo (es. "Ot53" → 01/10/2053)
            if not result["data_rimborso"] and result["descrizione"]:
                mesi = {
                    "ge":"01","gn":"01","fb":"02","fe":"02","mr":"03","ma":"03",
                    "ap":"04","mg":"05","gn":"06","lg":"07","lu":"07","ag":"08",
                    "st":"09","se":"09","ot":"10","nv":"11","no":"11","dc":"12","di":"12",
                    "jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
                    "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12"
                }
                m = re.search(r"([A-Za-z]{2,3})(\d{2,4})\b", result["descrizione"])
                if m:
                    mese_num = mesi.get(m.group(1).lower())
                    if mese_num:
                        anno = int(m.group(2))
                        if anno < 100: anno += 2000
                        result["data_rimborso"] = f"01/{mese_num}/{anno}"
                        result["scadenza"] = result["data_rimborso"]

            result["source_url"] = url
            result["mercato"] = _extract_market(url, isin[:2].upper() if len(isin)==12 else None)
            if result["descrizione"] or result["prezzo"]:
                return result

        except Exception as e:
            result["error"] = str(e)
            continue

    result["error"] = "Titolo non trovato su Borsa Italiana."
    return result


# Libreria interna: nome strumento per paese ISIN
STRUMENTO_LABEL = {
    "DE": "Bund",
    "IT": "BTP",
    "ES": "Bonos",
    "FR": "OAT",
    "NL": "DSL",
    "PL": "POLGB",
    "RO": "ROMGB",
    "XS": "Eurobond",
}

def _extract_market(url, isin_prefix=None):
    """Mercato di quotazione con nome strumento corretto da libreria interna."""
    if "mot/" in url:        segmento = "MOT"
    elif "euromot/" in url:  segmento = "EuroMOT"
    elif "extramot" in url:  segmento = "ExtraMOT"
    else:                    return "Borsa Italiana"

    # Nome strumento: libreria interna ha priorità sul path
    if isin_prefix and isin_prefix in STRUMENTO_LABEL:
        nome = STRUMENTO_LABEL[isin_prefix]
    elif "obbligazioni-in-altre" in url: nome = "Obbligazioni altre valute"
    elif "obbligazioni-in-euro" in url:  nome = "Obbligazioni EUR"
    elif "obbligazioni-euro" in url:     nome = "Obbligazioni EUR"
    else:                                nome = STRUMENTO_LABEL.get(isin_prefix, "Obbligazioni")

    return f"{segmento} - {nome}"


# ─────────────────────────────────────────────────────────────────
#  SPREAD — Borsa Italiana + FRED
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=1800)
def get_spread_bi(country_code):
    """Recupera spread da borsaitaliana.it/obbligazioni/spread per IT/ES/FR."""
    try:
        url = "https://www.borsaitaliana.it/obbligazioni/spread/overview.en.htm"
        r = requests.get(url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://www.borsaitaliana.it/"}, timeout=12)
        if r.status_code != 200:
            return None, None, None, None, "BI-error"
        soup = BeautifulSoup(r.text, "html.parser")

        names_map = {
            "IT":["italy","italia","btp"],
            "ES":["spain","spagna","bonos"],
            "FR":["france","francia","oat"],
        }
        names = names_map.get(country_code, [])
        bund_row = None; country_row = None

        for row in soup.find_all("tr"):
            txt = row.get_text(" ",strip=True).lower()
            if any(n in txt for n in ["germany","german","bund","germania"]):
                bund_row = row
            if any(n in txt for n in names):
                country_row = row

        def extract_yield(row):
            if not row: return None
            for cell in row.find_all(["td","th"]):
                txt = cell.get_text(strip=True).replace(",",".")
                m = re.search(r"(\d+\.\d{2,4})", txt)
                if m:
                    v = float(m.group(1))
                    if 0.1 < v < 15.0:
                        return v
            return None

        by = extract_yield(bund_row)
        cy = extract_yield(country_row)
        if by and cy:
            bp = round((cy - by) * 100, 1)
            # Cerca data aggiornamento
            dr = None
            for tag in soup.find_all(["span","div","p"], class_=re.compile(r"(date|data|aggiorn|update)",re.I)):
                m = re.search(r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}", tag.get_text(strip=True))
                if m:
                    dr = m.group(0); break
            return bp, by, cy, dr, "Borsa Italiana"
    except:
        pass
    return None, None, None, None, "BI-error"


@st.cache_data(ttl=3600)
def fred_latest(sid):
    if not sid: return None, None
    try:
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv?id="+sid, timeout=12)
        r.raise_for_status()
        for line in reversed(r.text.strip().split("\n")[1:]):
            p = line.split(",")
            if len(p)==2 and p[1].strip() not in (".",""):
                return float(p[1].strip()), p[0].strip()
    except: pass
    return None, None


def get_spread_data(code, macro):
    res = {"bund_y":None,"bund_d":None,"ctry_y":None,"ctry_d":None,
           "spread_bp":None,"source":None,"date_warning":False,"manual_needed":False}

    if code == "DE":
        by, bd = fred_latest("IRLTLT01DEM156N")
        res.update({"bund_y":by,"bund_d":bd,"ctry_y":by,"ctry_d":bd,"spread_bp":0.0,"source":"FRED"})
        return res

    if macro.get("spread_auto"):
        bp, by, cy, dr, src = get_spread_bi(code)
        if bp is not None:
            res.update({"bund_y":by,"bund_d":dr,"ctry_y":cy,"ctry_d":dr,"spread_bp":bp,"source":"Borsa Italiana"})
            return res

    # FRED fallback
    by, bd = fred_latest("IRLTLT01DEM156N")
    cy, cd = fred_latest(macro.get("fred_10y"))
    if by and cy:
        dw = False
        try:
            if bd and cd:
                b_m = datetime.strptime(bd[:7],"%Y-%m")
                c_m = datetime.strptime(cd[:7],"%Y-%m")
                dw = abs((b_m-c_m).days) > 35
        except: pass
        res.update({"bund_y":by,"bund_d":bd,"ctry_y":cy,"ctry_d":cd,
                    "spread_bp":round((cy-by)*100,1),"source":"FRED",
                    "date_warning":dw,"manual_needed":not macro.get("spread_auto") and dw})
    else:
        res["manual_needed"] = not macro.get("spread_auto")
    return res


# ─────────────────────────────────────────────────────────────────
#  CALCOLI FINANZIARI
# ─────────────────────────────────────────────────────────────────
def parse_float(s):
    if not s: return None
    try:
        s = str(s).strip().rstrip("%").strip()
        if re.search(r"\d\.\d{3},", s):
            s = s.replace(".","").replace(",",".")
        else:
            s = s.replace(",",".")
        m = re.search(r"[\d.]+", s)
        return float(m.group()) if m else None
    except: return None

def parse_date(s):
    if not s: return None
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d-%m-%Y","%d.%m.%Y","%d %b %Y","%d/%m/%y"):
        try: return datetime.strptime(str(s).strip(), fmt).date()
        except: continue
    return None

def anni_alla_scadenza(data_str):
    d = parse_date(data_str)
    if not d: return None
    delta = (d - date.today()).days
    return max(round(delta/365.25, 6), 0) if delta > 0 else None

def calc_ytm(prezzo, cedola_pct, anni, freq=2, face=100):
    if not prezzo or not cedola_pct or not anni or anni <= 0: return None
    try:
        c = (cedola_pct/100.0*face)/freq
        n = max(int(round(anni*freq)), 1)
        p = float(prezzo)

        def pv_fn(y):
            yp = y/freq
            if yp <= -1: return float('inf')
            return sum(c/(1+yp)**t for t in range(1,n+1)) + face/(1+yp)**n - p

        lo, hi = -0.98, 5.0
        if pv_fn(lo)*pv_fn(hi) > 0:
            hi = 20.0
        if pv_fn(lo)*pv_fn(hi) > 0:
            return None
        for _ in range(200):
            mid = (lo+hi)/2
            if abs(pv_fn(mid)) < 1e-10: break
            if pv_fn(lo)*pv_fn(mid) < 0: hi = mid
            else: lo = mid
        return round(mid*100.0, 4)
    except: return None

def calc_duration_mod(prezzo, cedola_pct, anni, ytm_pct, freq=2, face=100):
    if not all([prezzo, cedola_pct, anni, ytm_pct]) or anni <= 0: return None
    try:
        c   = (cedola_pct/100.0*face)/freq
        n   = max(int(round(anni*freq)), 1)
        yp  = ytm_pct/100.0/freq
        p   = float(prezzo)
        if yp <= -1: return None
        num = sum((t/freq)*c/(1+yp)**t for t in range(1,n+1)) + (n/freq)*face/(1+yp)**n
        mac = num/p
        dm  = mac/(1+yp)
        if dm > anni*1.05: return None
        return round(dm, 4)
    except: return None

def calc_convexity(prezzo, cedola_pct, anni, ytm_pct, freq=2, face=100):
    if not all([prezzo, cedola_pct, anni, ytm_pct]) or anni <= 0: return None
    try:
        c  = (cedola_pct/100.0*face)/freq
        n  = max(int(round(anni*freq)), 1)
        yp = ytm_pct/100.0/freq
        p  = float(prezzo)
        if yp <= -1: return None
        cv = sum(t*(t+1)*c/(1+yp)**(t+2) for t in range(1,n+1)) + n*(n+1)*face/(1+yp)**(n+2)
        return round(cv/(p*freq**2), 4)
    except: return None


# ─────────────────────────────────────────────────────────────────
#  UI HELPERS
# ─────────────────────────────────────────────────────────────────
def rating_color(v):
    if v in ("AAA","AA+","AA","AA-"): return "#22c55e"
    if v in ("A+","A","A-"):          return "#eab308"
    if v in ("BBB+","BBB","BBB-"):    return "#f97316"
    return "#ef4444"

def debt_color(v):
    if v is None: return "#94a3b8"
    if v < 60:    return "#22c55e"
    if v < 100:   return "#eab308"
    if v < 130:   return "#f97316"
    return "#ef4444"

def spread_color(bp):
    if bp is None: return "#94a3b8"
    if bp <= 30:   return "#22c55e"
    if bp <= 80:   return "#eab308"
    if bp <= 150:  return "#f97316"
    return "#ef4444"

def yield_color(y):
    if y is None: return "#94a3b8"
    return "#22c55e" if y > 0 else "#ef4444"

def card(label, val, sub="", col="#0f172a", bg="#f8fafc"):
    st.markdown(
        f'<div style="background:{bg};border-radius:10px;padding:14px 18px;'
        f'border-left:5px solid {col};margin-bottom:8px;">'
        f'<div style="font-size:10px;color:#64748b;font-weight:700;'
        f'text-transform:uppercase;letter-spacing:.08em;">{label}</div>'
        f'<div style="font-size:22px;font-weight:800;color:{col};margin:3px 0 2px;">{val}</div>'
        f'<div style="font-size:11px;color:#94a3b8;">{sub}</div>'
        f'</div>', unsafe_allow_html=True)

def section(title, icon=""):
    st.markdown(
        f'<h4 style="margin:24px 0 12px;color:#0f172a;">'
        f'<span style="margin-right:6px;">{icon}</span>{title}</h4>',
        unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
#  PAGE
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Bond Research Tool", page_icon="🏦", layout="wide")

st.markdown("""
<div style="background:linear-gradient(135deg,#0f172a 0%,#1e3a5f 100%);
padding:28px 32px;border-radius:14px;margin-bottom:24px;">
<div style="font-size:28px;font-weight:800;color:white;letter-spacing:-.5px;">
🏦 Bond Research Tool</div>
<div style="font-size:12px;color:#93c5fd;font-weight:600;
text-transform:uppercase;letter-spacing:.12em;margin-top:4px;">
B-Adviser S.r.l. | Analisi e Consulenza Finanziaria</div>
</div>
""", unsafe_allow_html=True)

tab_gov, tab_corp = st.tabs(["🏛️  Governativi", "🏢  Corporate"])

# ══════════════════════════════════════════════════════════════════
#  TAB GOVERNATIVI
# ══════════════════════════════════════════════════════════════════
with tab_gov:
    st.markdown("### Inserisci ISIN Governativo")
    c1, c2 = st.columns([4,1])
    with c1:
        isin_gov = st.text_input("ISIN", key="isin_gov",
            placeholder="es. IT0005534141", label_visibility="collapsed").strip().upper()
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        go_gov = st.button("🔍 Analizza", key="btn_gov", use_container_width=True, type="primary")

    st.caption("Esempi: IT0005534141 (BTP 4,5% Ot53) · IT0005534984 (BTP) · DE0001102580 (Bund) · ES0000012B39 (Bonos) · FR0014004L86 (OAT)")

    if go_gov and isin_gov:
        if len(isin_gov) != 12 or not isin_gov[:2].isalpha() or not isin_gov[2:].isalnum():
            st.error("❌ ISIN non valido."); st.stop()

        prefix = isin_gov[:2]
        if prefix not in ISIN_MAP:
            st.error(f"Prefisso {prefix} non supportato."); st.stop()
        code = ISIN_MAP[prefix]
        if code is None:
            st.warning("Prefisso XS = Eurobond. Identificazione paese manuale."); st.stop()

        macro = MACRO_DB[code]
        flag  = FLAGS.get(code,"🏳️")

        with st.spinner("📡 Recupero dati..."):
            debt_v, debt_d = fred_latest(macro.get("fred_debt"))
            hh_v,   hh_d   = fred_latest(macro.get("fred_hh"))
            bi = scrape_borsa_italiana(isin_gov)
            sd = get_spread_data(code, macro)

        # Dati titolo
        prezzo_f  = parse_float(bi.get("prezzo"))
        cedola_f  = parse_float(bi.get("tasso_cedolare"))
        scadenza_s = bi.get("data_rimborso") or bi.get("scadenza")
        anni_f    = anni_alla_scadenza(scadenza_s)
        divisa_f  = (bi.get("divisa") or macro["valuta"] or "EUR").split("/")[0].strip()

        periodo_raw = (bi.get("periodicita") or "").lower()
        freq = 4 if "trim" in periodo_raw else (1 if "annual" in periodo_raw or "annua" in periodo_raw else 2)

        # ── Input manuale cedola se non recuperata
        if not cedola_f:
            st.divider()
            st.warning("⚠️ Tasso cedolare non recuperato automaticamente. Inseriscilo:")
            mc1, mc2, mc3 = st.columns(3)
            with mc1:
                cedola_man = st.number_input("Tasso cedolare annuo (%)", min_value=0.0,
                    max_value=20.0, value=0.0, step=0.001, format="%.3f", key="ced_gov")
            with mc2:
                freq_sel = st.selectbox("Periodicità", ["Semestrale (x2)","Annuale (x1)","Trimestrale (x4)"], key="freq_gov")
                freq = 2 if "x2" in freq_sel else (1 if "x1" in freq_sel else 4)
            with mc3:
                if not scadenza_s:
                    scad_man = st.text_input("Data scadenza (gg/mm/aaaa)", placeholder="es. 01/10/2053", key="scad_gov")
                    if scad_man:
                        scadenza_s = scad_man
                        anni_f = anni_alla_scadenza(scadenza_s)
            if cedola_man and cedola_man > 0:
                cedola_f = cedola_man
                bi["tasso_cedolare"] = f"{cedola_man:.3f}"
                bi["periodicita"] = freq_sel.split(" ")[0]

        # ── Spread: input manuale per NL/PL/RO o se date sfasate
        spread_bp_final = sd.get("spread_bp")

        if sd.get("manual_needed"):
            st.divider()
            st.info(f"ℹ️ Spread {macro['paese']}: inserisci manualmente ([fonte Borsa Italiana](https://www.borsaitaliana.it/obbligazioni/spread/overview.en.htm))")
            s1, _ = st.columns([2,4])
            with s1:
                spread_man = st.number_input("Spread vs Bund (bp)", min_value=-500.0, max_value=2000.0,
                    value=float(spread_bp_final) if spread_bp_final else 0.0, step=0.1, format="%.1f", key="sp_man")
            spread_bp_final = spread_man
            sd["source"] = "Manuale"

        elif sd.get("date_warning"):
            st.warning(f"⚠️ Date FRED sfasate: Bund {sd.get('bund_d')} / {macro['paese']} {sd.get('ctry_d')}. Puoi sovrascrivere lo spread:")
            s1, _ = st.columns([2,4])
            with s1:
                sp_ov = st.number_input("Spread manuale (bp) — 0 = usa FRED", min_value=-500.0,
                    max_value=2000.0, value=0.0, step=0.1, format="%.1f", key="sp_ov")
            if sp_ov != 0:
                spread_bp_final = sp_ov
                sd["source"] = "Manuale"

        # Calcoli
        ytm      = calc_ytm(prezzo_f, cedola_f, anni_f, freq)
        dur_mod  = calc_duration_mod(prezzo_f, cedola_f, anni_f, ytm, freq)
        conv     = calc_convexity(prezzo_f, cedola_f, anni_f, ytm, freq)
        dur_disp = bi.get("duration") or (f"{dur_mod:.3f}" if dur_mod else None)
        con_disp = bi.get("convexity") or (f"{conv:.3f}" if conv else None)

        # Header
        st.divider()
        st.markdown(f"""
        <div style="background:#f1f5f9;border-radius:10px;padding:16px 22px;margin-bottom:20px;">
        <div style="font-size:20px;font-weight:800;color:#0f172a;">{flag} {isin_gov}</div>
        <div style="color:#475569;font-size:14px;margin-top:3px;">
        {bi.get("descrizione") or "—"} &nbsp;·&nbsp; {macro["paese"]} &nbsp;·&nbsp;
        {divisa_f} &nbsp;·&nbsp; {bi.get("mercato") or "Borsa Italiana"} &nbsp;·&nbsp; Governativo Sovrano
        </div></div>""", unsafe_allow_html=True)

        # S1: Dati Titolo
        section("Dati del Titolo","📋")
        r1a, r1b, r1c = st.columns(3)
        periodo_disp = bi.get("periodicita") or ("Semestrale" if freq==2 else ("Annuale" if freq==1 else "Trimestrale"))
        with r1a:
            card("ISIN", isin_gov, bi.get("descrizione") or "—")
            card("Paese", f"{flag} {macro['paese']}", macro["banca"])
            card("Divisa", divisa_f, "valuta di denominazione")
        with r1b:
            card("Prezzo di regolamento",
                 f"{prezzo_f:.2f}" if prezzo_f else (bi.get("prezzo") or "N/D"),
                 "ultimo prezzo Borsa Italiana")
            card("Tasso cedolare",
                 f"{cedola_f:.3f}%" if cedola_f else "N/D",
                 f"periodicità: {periodo_disp}")
            card("Taglio Minimo", bi.get("taglio_minimo") or "N/D", "lotto minimo acquistabile")
        with r1c:
            card("Scadenza / Data Rimborso", scadenza_s or "N/D",
                 f"anni residui: {anni_f:.2f}" if anni_f else "")
            card("Mercato", bi.get("mercato") or "—", "piazza di quotazione")

        # S2: Rating & Macro
        section("Rating & Solidità Paese","📊")
        sp_r = macro["sp"]; fi_r = macro["fitch"]
        r2a, r2b = st.columns(2)
        with r2a:
            card("S&P Global", sp_r["v"], f"Outlook: {sp_r['out']}  |  [{sp_r['d']}]", rating_color(sp_r["v"]))
        with r2b:
            card("Fitch", fi_r["v"], f"Outlook: {fi_r['out']}  |  [{fi_r['d']}]", rating_color(fi_r["v"]))

        if "Negative" in [sp_r["out"], fi_r["out"]]:
            st.warning("⚠️ Outlook NEGATIVO — rischio downgrade attivo")

        debt = debt_v if debt_v else macro["debt_pil"]
        hh   = hh_v   if hh_v   else macro["hh_debt"]
        r2c, r2d = st.columns(2)
        with r2c:
            dl = "Sostenibile" if debt<60 else ("Moderato" if debt<100 else ("Elevato" if debt<130 else "Zona critica"))
            card("Debito / PIL", f"{debt:.1f}%", f"{dl}  |  rif. {debt_d or macro['debt_ref']}", debt_color(debt))
        with r2d:
            hl = "Contenuto" if hh<50 else ("Moderato" if hh<80 else "Elevato")
            card("Household Debt / PIL", f"{hh:.1f}%", f"{hl}  |  rif. {hh_d or macro['hh_ref']}", debt_color(hh))

        fig_g = go.Figure(go.Indicator(
            mode="gauge+number", value=debt,
            number={"suffix":"%","font":{"size":24}},
            title={"text":"Debito / PIL","font":{"size":12}},
            gauge={"axis":{"range":[0,200]},"bar":{"color":debt_color(debt),"thickness":0.25},
                   "steps":[{"range":[0,60],"color":"#dcfce7"},{"range":[60,100],"color":"#fef9c3"},
                             {"range":[100,130],"color":"#ffedd5"},{"range":[130,200],"color":"#fee2e2"}],
                   "threshold":{"line":{"color":"#dc2626","width":3},"value":130}}))
        fig_g.update_layout(height=180, margin=dict(t=25,b=0,l=10,r=10), paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_g, use_container_width=True)

        # S3: Spread
        section("Spread vs Bund 10Y","📡")
        r3a, r3b, r3c = st.columns(3)
        with r3a:
            card("Bund 10Y",
                 f"{sd['bund_y']:.3f}%" if sd.get("bund_y") else "N/D",
                 f"rif. {sd.get('bund_d') or 'FRED'}")
        with r3b:
            lbl = "Germania 10Y" if code=="DE" else f"{macro['paese']} 10Y"
            val_y = sd.get("ctry_y")
            card(lbl, f"{val_y:.3f}%" if val_y else "N/D",
                 f"rif. {sd.get('ctry_d') or sd.get('source','FRED')}")
        with r3c:
            bp = spread_bp_final
            if code == "DE":
                card("Spread vs Bund","0 bp","Germania = benchmark","#22c55e")
            elif bp is not None:
                bp_lbl = ("Basso" if bp<=30 else "Moderato" if bp<=80 else
                          "Rilevante" if bp<=150 else "Elevato" if bp<=300 else "Critico")
                card("Spread vs Bund", f"{bp:+.1f} bp",
                     f"{bp_lbl}  |  fonte: {sd.get('source','FRED')}", spread_color(bp))
            else:
                card("Spread vs Bund","N/D","inserisci manualmente sopra","#94a3b8")

        # S4: Rendimento & Rischio
        section("Analisi Rendimento & Rischio","💹")
        col_tax, _ = st.columns([1,3])
        with col_tax:
            tax_rate = st.number_input("Aliquota fiscale (%)", min_value=0.0, max_value=50.0,
                value=12.5, step=0.5, help="12,5% gov. UE  |  26% corporate")

        rend_lordo = ytm
        rend_netto = round(ytm*(1.0-tax_rate/100.0),4) if ytm else None

        r4a, r4b, r4c, r4d = st.columns(4)
        with r4a:
            card("Rendimento Lordo", f"{rend_lordo:.3f}%" if rend_lordo else "N/D",
                 "YTM calcolato dal tool", yield_color(rend_lordo))
        with r4b:
            card("Rendimento Netto", f"{rend_netto:.3f}%" if rend_netto else "N/D",
                 f"al netto del {tax_rate:.1f}%", yield_color(rend_netto))
        with r4c:
            card("Duration Modificata", dur_disp or "N/D", f"sensibilità ai tassi | {freq}x/anno")
        with r4d:
            card("Convexity", con_disp or "N/D", "curvatura prezzo/rendimento")

        if not cedola_f:
            st.info("ℹ️ Inserisci tasso cedolare sopra per calcolare Rendimento, Duration e Convexity.")

        card("Tassazione applicata", f"{tax_rate:.1f}%", "12,5% gov. UE  |  26% corporate  |  modificabile sopra")

        # S5: Riepilogo
        section("Riepilogo Scheda Completa","📄")
        recap = {
            "Campo":["ISIN","Descrizione","Paese","Rating (S&P / Fitch)",
                     "Debito/PIL","Household Debt/PIL","Spread vs Bund",
                     "Prezzo di regolamento","Divisa","Taglio Minimo",
                     "Data Rimborso","Tasso cedolare","Periodicità cedola",
                     "Scadenza","Duration Modificata","Convexity",
                     "Rend. Lordo","Rend. Netto","Tassazione applicata"],
            "Valore":[
                isin_gov, bi.get("descrizione") or "—", macro["paese"],
                f"{sp_r['v']} / {fi_r['v']}", f"{debt:.1f}%", f"{hh:.1f}%",
                f"{bp:+.1f} bp" if bp is not None else "N/D",
                f"{prezzo_f:.2f}" if prezzo_f else (bi.get("prezzo") or "N/D"),
                divisa_f, bi.get("taglio_minimo") or "N/D",
                scadenza_s or "N/D",
                f"{cedola_f:.3f}%" if cedola_f else "N/D",
                periodo_disp, scadenza_s or "N/D",
                dur_disp or "N/D", con_disp or "N/D",
                f"{rend_lordo:.3f}%" if rend_lordo else "N/D",
                f"{rend_netto:.3f}%" if rend_netto else "N/D",
                f"{tax_rate:.1f}%",
            ],
        }
        st.dataframe(pd.DataFrame(recap), use_container_width=True, hide_index=True, height=640)

        if bi.get("source_url"):
            st.caption(f"📌 Dati titolo: {bi['source_url']}")
        if bi.get("error") and not bi.get("prezzo"):
            st.warning(f"⚠️ Borsa Italiana: {bi['error']}")
        st.divider()
        st.caption(f"Dati macro: FRED live  ·  Spread: {sd.get('source','FRED')}  ·  "
                   f"Dati titolo: Borsa Italiana  ·  Calcoli: tool interno  ·  "
                   f"Non costituisce consulenza finanziaria  ·  B-Adviser S.r.l.")


# ══════════════════════════════════════════════════════════════════
#  TAB CORPORATE
# ══════════════════════════════════════════════════════════════════
with tab_corp:
    st.markdown("### Inserisci ISIN Corporate")
    c1c, c2c = st.columns([4,1])
    with c1c:
        isin_corp = st.text_input("ISIN Corporate", key="isin_corp",
            placeholder="es. XS2543893458", label_visibility="collapsed").strip().upper()
    with c2c:
        st.markdown("<br>", unsafe_allow_html=True)
        go_corp = st.button("🔍 Analizza", key="btn_corp", use_container_width=True, type="primary")

    st.caption("Inserisci l'ISIN di un'obbligazione corporate quotata su Borsa Italiana")

    with st.expander("📝 Dati Emittente Corporate (compilazione manuale)", expanded=False):
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
            corp_seniority = st.selectbox("Seniority",
                ["Senior Secured","Senior Unsecured","Senior Non-Preferred","Subordinato","Tier 1","Tier 2"])

    if go_corp and isin_corp:
        if len(isin_corp)!=12 or not isin_corp[:2].isalpha() or not isin_corp[2:].isalnum():
            st.error("❌ ISIN non valido."); st.stop()

        with st.spinner("🌐 Borsa Italiana: recupero dati..."):
            bi_c = scrape_borsa_italiana(isin_corp)

        prezzo_c   = parse_float(bi_c.get("prezzo"))
        cedola_c   = parse_float(bi_c.get("tasso_cedolare"))
        scadenza_c = bi_c.get("data_rimborso") or bi_c.get("scadenza")
        anni_c     = anni_alla_scadenza(scadenza_c)
        divisa_c   = (bi_c.get("divisa") or corp_valuta or "EUR").split("/")[0].strip()
        periodo_c  = (bi_c.get("periodicita") or "").lower()
        freq_c = 4 if "trim" in periodo_c else (1 if "annual" in periodo_c else 2)

        if not cedola_c:
            st.warning("⚠️ Tasso cedolare non recuperato. Inseriscilo:")
            mc1c, mc2c = st.columns([2,2])
            with mc1c:
                ced_m = st.number_input("Tasso cedolare (%)", min_value=0.0, max_value=20.0,
                    value=0.0, step=0.001, format="%.3f", key="ced_corp")
            with mc2c:
                fr_sel = st.selectbox("Periodicità", ["Semestrale (x2)","Annuale (x1)","Trimestrale (x4)"], key="freq_corp")
                freq_c = 2 if "x2" in fr_sel else (1 if "x1" in fr_sel else 4)
            if ced_m > 0:
                cedola_c = ced_m
                bi_c["periodicita"] = fr_sel.split(" ")[0]

        ytm_c  = calc_ytm(prezzo_c, cedola_c, anni_c, freq_c)
        dur_c  = calc_duration_mod(prezzo_c, cedola_c, anni_c, ytm_c, freq_c)
        conv_c = calc_convexity(prezzo_c, cedola_c, anni_c, ytm_c, freq_c)
        dur_cd = bi_c.get("duration") or (f"{dur_c:.3f}" if dur_c else None)
        con_cd = bi_c.get("convexity") or (f"{conv_c:.3f}" if conv_c else None)

        debt_ebitda = round(corp_debito/corp_ebitda,2) if corp_ebitda>0 else None
        fcf_debt    = round(corp_fcf/corp_debito*100,2) if corp_debito>0 else None
        periodo_cd  = bi_c.get("periodicita") or ("Semestrale" if freq_c==2 else "Annuale")
        cedola_clbl = f"{cedola_c:.3f}%" if cedola_c else "N/D"

        st.divider()
        st.markdown(f"""
        <div style="background:#f1f5f9;border-radius:10px;padding:16px 22px;margin-bottom:20px;">
        <div style="font-size:20px;font-weight:800;color:#0f172a;">🏢 {isin_corp}</div>
        <div style="color:#475569;font-size:14px;margin-top:3px;">
        {bi_c.get("descrizione") or corp_nome or "—"} &nbsp;·&nbsp;
        {corp_paese or "—"} &nbsp;·&nbsp; {corp_settore or "—"} &nbsp;·&nbsp;
        {bi_c.get("mercato") or "Borsa Italiana"} &nbsp;·&nbsp; {corp_seniority}
        </div></div>""", unsafe_allow_html=True)

        section("Dati del Titolo","📋")
        rc1,rc2,rc3 = st.columns(3)
        with rc1:
            card("ISIN", isin_corp, bi_c.get("descrizione") or "—")
            card("Emittente", corp_nome or "—", corp_settore or "—")
            card("Divisa", divisa_c)
        with rc2:
            card("Prezzo di regolamento",
                 f"{prezzo_c:.2f}" if prezzo_c else (bi_c.get("prezzo") or "N/D"),
                 "ultimo prezzo Borsa Italiana")
            card("Tasso cedolare", cedola_clbl, f"periodicità: {periodo_cd}")
            card("Taglio Minimo", bi_c.get("taglio_minimo") or "N/D")
        with rc3:
            card("Scadenza / Data Rimborso", scadenza_c or "N/D",
                 f"anni residui: {anni_c:.2f}" if anni_c else "")
            card("Seniority", corp_seniority)
            card("Mercato", bi_c.get("mercato") or "—")

        section("Rating & Solidità Emittente","📊")
        if corp_rating:
            card("Rating S&P", corp_rating, f"{corp_nome} — {corp_settore}", rating_color(corp_rating))
        if corp_ebitda > 0:
            rf1,rf2,rf3,rf4 = st.columns(4)
            lc = "#22c55e" if debt_ebitda and debt_ebitda<2 else ("#eab308" if debt_ebitda and debt_ebitda<4 else "#ef4444")
            with rf1: card("Debito / EBITDA", f"{debt_ebitda:.2f}x" if debt_ebitda else "N/D", "< 2x ottimo  |  > 4x critico", lc)
            with rf2: card("EBITDA", f"{corp_ebitda:.1f} MLD")
            with rf3: card("Free Cash Flow", f"{corp_fcf:.1f} MLD", f"FCF/Debito: {fcf_debt:.1f}%" if fcf_debt else "")
            with rf4: card("Leva Finanziaria", f"{corp_leva:.2f}x" if corp_leva else (f"{debt_ebitda:.2f}x" if debt_ebitda else "N/D"))

        section("Analisi Rendimento & Rischio","💹")
        col_tc, _ = st.columns([1,3])
        with col_tc:
            tax_c = st.number_input("Aliquota fiscale (%)", key="tax_corp",
                min_value=0.0, max_value=50.0, value=26.0, step=0.5)

        rl_c = ytm_c
        rn_c = round(ytm_c*(1.0-tax_c/100.0),4) if ytm_c else None
        rr1,rr2,rr3,rr4 = st.columns(4)
        with rr1: card("Rendimento Lordo", f"{rl_c:.3f}%" if rl_c else "N/D", "YTM", yield_color(rl_c))
        with rr2: card("Rendimento Netto", f"{rn_c:.3f}%" if rn_c else "N/D", f"al netto del {tax_c:.1f}%", yield_color(rn_c))
        with rr3: card("Duration Modificata", dur_cd or "N/D", f"{freq_c}x/anno")
        with rr4: card("Convexity", con_cd or "N/D")

        if not cedola_c:
            st.info("ℹ️ Inserisci il tasso cedolare per calcolare Rendimento, Duration e Convexity.")

        section("Riepilogo Scheda Completa","📄")
        recap_c = {
            "Campo":["ISIN","Descrizione","Paese","Settore","Rating (S&P)",
                     "EBITDA","Debito","Debito/EBITDA","Free Cash Flow",
                     "FCF/Totale Debito","Margine EBITDA","Leva Finanziaria",
                     "Prezzo di regolamento","Divisa","Taglio Minimo",
                     "Data Rimborso","Tasso cedolare","Periodicità cedola",
                     "Scadenza","Seniority","Duration Modificata","Convexity",
                     "Rend. Lordo","Rend. Netto","Tassazione applicata"],
            "Valore":[
                isin_corp, bi_c.get("descrizione") or corp_nome or "—",
                corp_paese or "—", corp_settore or "—", corp_rating or "—",
                f"{corp_ebitda:.1f} MLD" if corp_ebitda else "—",
                f"{corp_debito:.1f} MLD" if corp_debito else "—",
                f"{debt_ebitda:.2f}x" if debt_ebitda else "—",
                f"{corp_fcf:.1f} MLD" if corp_fcf else "—",
                f"{fcf_debt:.1f}%" if fcf_debt else "—",
                f"{corp_margine:.1f}%" if corp_margine else "—",
                f"{corp_leva:.2f}x" if corp_leva else "—",
                f"{prezzo_c:.2f}" if prezzo_c else (bi_c.get("prezzo") or "N/D"),
                divisa_c, bi_c.get("taglio_minimo") or "N/D",
                scadenza_c or "N/D", cedola_clbl, periodo_cd,
                scadenza_c or "N/D", corp_seniority,
                dur_cd or "N/D", con_cd or "N/D",
                f"{rl_c:.3f}%" if rl_c else "N/D",
                f"{rn_c:.3f}%" if rn_c else "N/D",
                f"{tax_c:.1f}%",
            ],
        }
        st.dataframe(pd.DataFrame(recap_c), use_container_width=True, hide_index=True, height=780)

        if bi_c.get("source_url"):
            st.caption(f"📌 Dati titolo: {bi_c['source_url']}")
        if bi_c.get("error") and not bi_c.get("prezzo"):
            st.warning(f"⚠️ Borsa Italiana: {bi_c['error']}")
        st.divider()
        st.caption("Dati titolo: Borsa Italiana  ·  Dati emittente: inserimento manuale  ·  "
                   "Calcoli: tool interno  ·  Non costituisce consulenza finanziaria  ·  B-Adviser S.r.l.")

    elif not go_corp:
        st.info("📌 Inserisci l'ISIN corporate e compila il pannello dati emittente, poi clicca **Analizza**.")
