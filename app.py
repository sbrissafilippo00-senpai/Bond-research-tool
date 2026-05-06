
import streamlit as st
import requests
import pandas as pd
import re
from bs4 import BeautifulSoup
import plotly.graph_objects as go
from datetime import datetime, date
import math

# ─────────────────────────────────────────────────────────────────
#  LIBRERIA INTERNA — Dati Paese
#  Aggiornare: rating (sp/fitch), debt_pil, hh_debt quando cambiano
#  I dati FRED (rendimenti, macro) vengono recuperati automaticamente
# ─────────────────────────────────────────────────────────────────
MACRO_DB = {
    # ── GERMANIA ─────────────────────────────────────────────────
    "DE": {
        "paese":          "Germania",
        "area":           "Eurozona",
        "valuta":         "EUR",
        "banca":          "BCE",
        # Rating (aggiornare manualmente)
        "sp":             {"v":"AAA",  "out":"Stable",   "d":"2024-09"},
        "fitch":          {"v":"AAA",  "out":"Stable",   "d":"2024-08"},
        # Macro statici (fallback se FRED non disponibile)
        "debt_pil":       62.2,  "debt_ref":"2024",
        "hh_debt":        49.1,  "hh_ref":"Q3 2025",
        "deficit_pil":    1.6,   "deficit_ref":"2024",
        "int_spesa_pil":  1.07,  "int_ref":"2024",
        "gold_t":         3350.25,"gold_usd":394.67,   "gold_ref":"Q4 2025",
        "fx_reserves":    518.7,  "fx_ref":"Mar 2026",
        "inflazione":     2.7,    "infl_ref":"Mar 2026",
        "disoccupazione": 6.3,    "disoc_ref":"Mar 2026",
        "pil_mld":        4670,   "pil_ref":"2024",
        # FRED series (automatici)
        "fred_10y":       "IRLTLT01DEM156N",
        "fred_debt":      "GGGDTADEA188N",
        "fred_hh":        "HDTGPDDEQ163N",
        "fred_2y":        "IRLTLT01DEM156N",
        "fred_5y":        "IRLTLT01DEM156N",
        "fred_30y":       "IRLTLT01DEM156N",
        "fred_gold":      "GOLDAMGBD228NLBM",
        "cds_url":        "https://www.worldgovernmentbonds.com/cds/germany/",
        "spread_auto":    True,
        "freq_cedola":    1,
        "strumento":      "Bund",
        "note_rischio":   "Benchmark Eurozona. AAA stabile. Debito/PIL sotto soglia Maastricht.",
    },
    # ── ITALIA ───────────────────────────────────────────────────
    "IT": {
        "paese":          "Italia",
        "area":           "Eurozona",
        "valuta":         "EUR",
        "banca":          "BCE",
        "sp":             {"v":"BBB+", "out":"Positive", "d":"2026-01"},
        "fitch":          {"v":"BBB+", "out":"Stable",   "d":"2025-10"},
        "debt_pil":       135.3, "debt_ref":"2024",
        "hh_debt":        35.9,  "hh_ref":"Q3 2025",
        "deficit_pil":    3.4,   "deficit_ref":"2024",
        "int_spesa_pil":  4.25,  "int_ref":"2024",
        "gold_t":         2451.87,"gold_usd":339.44,   "gold_ref":"Q4 2025",
        "fx_reserves":    55.4,   "fx_ref":"Feb 2026",
        "inflazione":     1.7,    "infl_ref":"Mar 2026",
        "disoccupazione": 5.3,    "disoc_ref":"Mar 2026",
        "pil_mld":        2372,   "pil_ref":"2024",
        "fred_10y":       "IRLTLT01ITM156N",
        "fred_debt":      "GGGDTAITA188N",
        "fred_hh":        "HDTGPDITQ163N",
        "fred_2y":        "IRLTLT01ITM156N",
        "fred_5y":        "IRLTLT01ITM156N",
        "fred_30y":       "IRLTLT01ITM156N",
        "fred_gold":      "GOLDAMGBD228NLBM",
        "cds_url":        "https://www.worldgovernmentbonds.com/cds/italy/",
        "spread_auto":    True,
        "freq_cedola":    2,
        "strumento":      "BTP",
        "note_rischio":   "Debito/PIL critico >130%. Outlook positivo S&P. Spread monitorato. Spesa interessi al 4,25% PIL.",
    },
    # ── SPAGNA ───────────────────────────────────────────────────
    "ES": {
        "paese":          "Spagna",
        "area":           "Eurozona",
        "valuta":         "EUR",
        "banca":          "BCE",
        "sp":             {"v":"A+",   "out":"Stable",   "d":"2025-04"},
        "fitch":          {"v":"A-",   "out":"Positive", "d":"2025-06"},
        "debt_pil":       100.8, "debt_ref":"2025",
        "hh_debt":        43.0,  "hh_ref":"Q3 2025",
        "deficit_pil":    3.2,   "deficit_ref":"2024",
        "int_spesa_pil":  2.0,   "int_ref":"2024",
        "gold_t":         281.58, "gold_usd":39.0,     "gold_ref":"Q4 2025",
        "fx_reserves":    None,   "fx_ref":"N/D",
        "inflazione":     3.4,    "infl_ref":"Mar 2026",
        "disoccupazione": 9.93,   "disoc_ref":"Q4 2025",
        "pil_mld":        1722,   "pil_ref":"2024",
        "fred_10y":       "IRLTLT01ESM156N",
        "fred_debt":      "GGGDTAESA188N",
        "fred_hh":        "HDTGPDESQ163N",
        "fred_2y":        "IRLTLT01ESM156N",
        "fred_5y":        "IRLTLT01ESM156N",
        "fred_30y":       None,
        "fred_gold":      "GOLDAMGBD228NLBM",
        "cds_url":        "https://www.worldgovernmentbonds.com/cds/spain/",
        "spread_auto":    True,
        "freq_cedola":    1,
        "strumento":      "Bonos",
        "note_rischio":   "Traiettoria fiscale in miglioramento. Disoccupazione strutturalmente elevata. Rating in salita.",
    },
    # ── FRANCIA ──────────────────────────────────────────────────
    "FR": {
        "paese":          "Francia",
        "area":           "Eurozona",
        "valuta":         "EUR",
        "banca":          "BCE",
        "sp":             {"v":"AA-",  "out":"Negative", "d":"2025-10"},
        "fitch":          {"v":"AA-",  "out":"Negative", "d":"2025-10"},
        "debt_pil":       113.0, "debt_ref":"2024",
        "hh_debt":        59.9,  "hh_ref":"2024",
        "deficit_pil":    5.1,   "deficit_ref":"2024",
        "int_spesa_pil":  2.0,   "int_ref":"2024",
        "gold_t":         2437.0, "gold_usd":334.0,    "gold_ref":"Q4 2025",
        "fx_reserves":    409.26, "fx_ref":"Gen 2026",
        "inflazione":     1.0,    "infl_ref":"2025",
        "disoccupazione": 7.5,    "disoc_ref":"Q2 2025",
        "pil_mld":        2970,   "pil_ref":"2024",
        "fred_10y":       "IRLTLT01FRM156N",
        "fred_debt":      "GGGDTAFRA188N",
        "fred_hh":        "HDTGPDFRA163N",
        "fred_2y":        "IRLTLT01FRM156N",
        "fred_5y":        "IRLTLT01FRM156N",
        "fred_30y":       None,
        "fred_gold":      "GOLDAMGBD228NLBM",
        "cds_url":        "https://www.worldgovernmentbonds.com/cds/france/",
        "spread_auto":    True,
        "freq_cedola":    1,
        "strumento":      "OAT",
        "note_rischio":   "Outlook negativo su entrambe le agenzie. Deficit al 5,1% PIL. Debito verso 120% nel 2027.",
    },
    # ── OLANDA ───────────────────────────────────────────────────
    "NL": {
        "paese":          "Olanda",
        "area":           "Eurozona",
        "valuta":         "EUR",
        "banca":          "BCE",
        "sp":             {"v":"AAA",  "out":"Stable",   "d":"2025-05"},
        "fitch":          {"v":"AAA",  "out":"Stable",   "d":"2025-04"},
        "debt_pil":       43.7,  "debt_ref":"2024",
        "hh_debt":        97.2,  "hh_ref":"Q4 2025",
        "deficit_pil":    0.9,   "deficit_ref":"2024",
        "int_spesa_pil":  1.6,   "int_ref":"2024",
        "gold_t":         612.45, "gold_usd":102.8,    "gold_ref":"Q4 2025",
        "fx_reserves":    13.2,   "fx_ref":"Feb 2026",
        "inflazione":     3.3,    "infl_ref":"2025",
        "disoccupazione": 4.0,    "disoc_ref":"Q4 2025",
        "pil_mld":        1134,   "pil_ref":"2024",
        "fred_10y":       "IRLTLT01NLM156N",
        "fred_debt":      "GGGDTANLA188N",
        "fred_hh":        "HDTGPDNLQ163N",
        "fred_2y":        "IRLTLT01NLM156N",
        "fred_5y":        "IRLTLT01NLM156N",
        "fred_30y":       None,
        "fred_gold":      "GOLDAMGBD228NLBM",
        "cds_url":        "https://www.worldgovernmentbonds.com/cds/netherlands/",
        "spread_auto":    False,
        "freq_cedola":    1,
        "strumento":      "DSL",
        "note_rischio":   "AAA stabile. Debito/PIL ottimo. Attenzione: HH Debt/PIL al 97% — rischio canale immobiliare.",
    },
    # ── POLONIA ──────────────────────────────────────────────────
    "PL": {
        "paese":          "Polonia",
        "area":           "UE extra-euro",
        "valuta":         "PLN",
        "banca":          "NBP",
        "sp":             {"v":"A-",   "out":"Stable",   "d":"2025-03"},
        "fitch":          {"v":"A-",   "out":"Stable",   "d":"2025-03"},
        "debt_pil":       55.1,  "debt_ref":"2024",
        "hh_debt":        35.0,  "hh_ref":"Q3 2025",
        "deficit_pil":    6.5,   "deficit_ref":"2024",
        "int_spesa_pil":  2.2,   "int_ref":"2024",
        "gold_t":         550.21, "gold_usd":76.3,     "gold_ref":"Q4 2025",
        "fx_reserves":    293.9,  "fx_ref":"Gen 2026",
        "inflazione":     4.9,    "infl_ref":"Mar 2026",
        "disoccupazione": 3.0,    "disoc_ref":"2025",
        "pil_mld":        840,    "pil_ref":"2024",
        "fred_10y":       "IRLTLT01PLM156N",
        "fred_debt":      "GGGDTAPLA188N",
        "fred_hh":        "HDTGPDPLQ163N",
        "fred_2y":        None,
        "fred_5y":        None,
        "fred_30y":       None,
        "fred_gold":      "GOLDAMGBD228NLBM",
        "cds_url":        "https://www.worldgovernmentbonds.com/cds/poland/",
        "spread_auto":    False,
        "freq_cedola":    1,
        "strumento":      "POLGB",
        "note_rischio":   "Valuta sovrana PLN. Politica monetaria indipendente NBP. Deficit in deterioramento (+difesa). Riserve FX eccellenti.",
    },
    # ── ROMANIA ──────────────────────────────────────────────────
    "RO": {
        "paese":          "Romania",
        "area":           "UE extra-euro",
        "valuta":         "RON",
        "banca":          "BNR",
        "sp":             {"v":"BBB-", "out":"Negative", "d":"2025-09"},
        "fitch":          {"v":"BBB-", "out":"Negative", "d":"2025-09"},
        "debt_pil":       59.4,  "debt_ref":"2025",
        "hh_debt":        20.0,  "hh_ref":"Q3 2025",
        "deficit_pil":    9.3,   "deficit_ref":"2024",
        "int_spesa_pil":  3.2,   "int_ref":"2024",
        "gold_t":         103.6,  "gold_usd":14.9,     "gold_ref":"Q4 2025",
        "fx_reserves":    65.81,  "fx_ref":"Gen 2026",
        "inflazione":     9.9,    "infl_ref":"Mar 2026",
        "disoccupazione": 6.3,    "disoc_ref":"Q2 2025",
        "pil_mld":        390,    "pil_ref":"2024",
        "fred_10y":       None,
        "fred_debt":      "GGGDTAROA188N",
        "fred_hh":        None,
        "fred_2y":        None,
        "fred_5y":        None,
        "fred_30y":       None,
        "fred_gold":      "GOLDAMGBD228NLBM",
        "cds_url":        "https://www.worldgovernmentbonds.com/cds/romania/",
        "spread_auto":    False,
        "freq_cedola":    1,
        "strumento":      "ROMGB",
        "note_rischio":   "A un gradino dal junk (BBB- Negative). Deficit al 9,3% PIL — il più alto UE. Inflazione al 9,9%. Monitorare con massima attenzione.",
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
    # Per ISIN XS (Eurobond): prova prima EuroMOT, poi MOT, poi ExtraMOT
    # Per ISIN nazionali: prova prima MOT, poi EuroMOT
    isin_prefix = isin[:2].upper() if len(isin) == 12 else ""
    if isin_prefix == "XS":
        paths = [
            f"https://www.borsaitaliana.it/borsa/obbligazioni/euromot/obbligazioni-euro/scheda/{isin}.html",
            f"https://www.borsaitaliana.it/borsa/obbligazioni/euromot/obbligazioni-altre-valute/scheda/{isin}.html",
            f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/obbligazioni-in-euro/scheda/{isin}.html",
            f"https://www.borsaitaliana.it/borsa/obbligazioni/mot/obbligazioni-in-altre-valute/scheda/{isin}.html",
            f"https://www.borsaitaliana.it/borsa/obbligazioni/extramot/scheda/{isin}.html",
        ]
    else:
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
        "_isin_prefix": isin[:2].upper() if len(isin)==12 else "",
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
                elif (
                    # Label ESATTO "scadenza" o "maturity date" — esclude esplicitamente
                    # campi con date diverse: godimento, stacco cedola, inizio negoziazione, rimborso anticipato
                    label.strip() in ("scadenza","maturity date","data di scadenza","data scadenza","data rimborso")
                    or (label.strip() == "scadenza")
                ) and not any(x in label for x in ["cedola","godimento","stacco","inizio","negoziaz","anticip","emissione"]):
                    if not result["data_rimborso"]:
                        result["data_rimborso"] = value
                        result["scadenza"] = value
                elif any(x in label for x in ["tasso cedola periodale","tasso cedola su base annua","tasso cedola","cedola","coupon rate","tasso interesse","tasso nominale","tasso annuo","interest rate","coupon"]):
                    if not result["tasso_cedolare"]:
                        # % OBBLIGATORIO per evitare falsi positivi da altri campi numerici
                        m = re.search(r"(\d+[,.]?\d*)\s*%", value)
                        if m:
                            v = float(m.group(1).replace(",","."))
                            if 0.001 <= v <= 25.0:  # range ragionevole per una cedola
                                result["tasso_cedolare"] = str(v)
                elif any(x in label for x in ["periodicità cedola","periodicita cedola","periodicità","periodicita","frequency","frequenza","stacco cedola"]):
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

            # Fallback periodicità: solo BTP/Bund/OAT/DSL → semestrale
            # I Bonos spagnoli sono ANNUALI — non assumiamo mai semestrale per ES
            if not result["periodicita"] and result["descrizione"]:
                desc_l = result["descrizione"].lower()
                isin_prefix = result.get("_isin_prefix","")
                if any(x in desc_l for x in ["btp","bund","oat","dsl"]) and isin_prefix != "ES":
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
    s = str(s).strip()
    # Gestione formato corto gg/mm/aa (es. "30/07/40" da Borsa Italiana)
    # Python interpreta anni 00-68 come 2000-2068 e 69-99 come 1969-1999
    # ma le obbligazioni hanno scadenze future → forziamo sempre 2000+
    m_short = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2})$", s)
    if m_short:
        g, mo, a = m_short.group(1), m_short.group(2), int(m_short.group(3))
        anno = 2000 + a  # sempre futuro per obbligazioni
        s = f"{g}/{mo}/{anno}"
    for fmt in ("%d/%m/%Y","%Y-%m-%d","%d-%m-%Y","%d.%m.%Y","%d %b %Y"):
        try: return datetime.strptime(s, fmt).date()
        except: continue
    return None

def anni_alla_scadenza(data_str):
    d = parse_date(data_str)
    if not d: return None
    delta = (d - date.today()).days
    return max(round(delta/365.25, 6), 0) if delta > 0 else None

def format_date(data_str):
    """Normalizza qualsiasi formato data a gg/mm/aaaa per la visualizzazione."""
    d = parse_date(data_str)
    if not d: return data_str or "N/D"
    return d.strftime("%d/%m/%Y")

# ─────────────────────────────────────────────────────────────────
#  ACCRUED INTEREST (rateo cedolare)
# ─────────────────────────────────────────────────────────────────
def calc_accrued_interest(cedola_pct, freq, last_coupon_date=None, settlement_date=None, face=100):
    """
    Calcola il rateo cedolare (accrued interest) con convenzione ACT/ACT.
    Se last_coupon_date non disponibile, stima dalla periodicità.
    Ritorna (rateo, giorni_trascorsi, giorni_periodo, tel_quel_label)
    """
    if not cedola_pct or not freq:
        return None, None, None
    coupon_annuo = cedola_pct / 100.0 * face
    coupon_periodo = coupon_annuo / freq
    giorni_periodo = 365 // freq  # approssimazione: 365/freq

    if settlement_date is None:
        settlement_date = date.today()

    if last_coupon_date:
        d = parse_date(last_coupon_date)
        if d:
            giorni_trascorsi = (settlement_date - d).days
        else:
            giorni_trascorsi = giorni_periodo // 2  # stima
    else:
        # Stima: metà periodo (worst case conservativo)
        giorni_trascorsi = min(giorni_periodo // 2, 180)

    giorni_trascorsi = max(0, min(giorni_trascorsi, giorni_periodo))
    rateo = round(coupon_periodo * (giorni_trascorsi / giorni_periodo), 6)
    return rateo, giorni_trascorsi, giorni_periodo


# ─────────────────────────────────────────────────────────────────
#  GOLD PRICE — prezzo trimestre precedente da FRED
# ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=86400)
def get_gold_price_prev_quarter():
    """
    Recupera il prezzo di chiusura dell'oro (USD/oz) dell'ultimo giorno
    lavorativo del trimestre precedente a quello corrente.

    Fonti FRED (in ordine di priorità):
      1. GOLDPMGBD228NLBM — London Gold Fixing PM (giornaliero, più stabile)
      2. GOLDAMGBD228NLBM — London Gold Fixing AM (fallback)
    Ritorna (price, date_ref, quarter_label)
    """
    today = date.today()
    q = (today.month - 1) // 3   # trimestre corrente (0=Q1, 1=Q2, 2=Q3, 3=Q4)

    if q == 0:
        # Siamo in Q1 → trimestre precedente = Q4 dell'anno scorso
        end_prev_q = date(today.year - 1, 12, 31)
        q_label = f"Q4 {today.year - 1}"
    else:
        end_month = q * 3   # ultimo mese del trim. precedente
        # Calcola ultimo giorno del mese correttamente
        import calendar
        last_day = calendar.monthrange(today.year, end_month)[1]
        end_prev_q = date(today.year, end_month, last_day)
        q_label = f"Q{q} {today.year}"

    def fetch_gold_series(series_id):
        """Scarica serie FRED e cerca l'ultima quotazione <= end_prev_q."""
        try:
            url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            r = requests.get(url, timeout=15,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                return None, None
            lines = r.text.strip().split("\n")[1:]  # salta header
            for line in reversed(lines):
                p = line.strip().split(",")
                if len(p) == 2 and p[1].strip() not in (".", "", "NA"):
                    try:
                        d_parsed = datetime.strptime(p[0].strip(), "%Y-%m-%d").date()
                        if d_parsed <= end_prev_q:
                            return float(p[1].strip()), d_parsed.strftime("%d/%m/%Y")
                    except:
                        continue
        except:
            pass
        return None, None

    # Prova PM fixing prima, poi AM fixing
    for series in ("GOLDPMGBD228NLBM", "GOLDAMGBD228NLBM"):
        price, date_ref = fetch_gold_series(series)
        if price and price > 100:   # sanity check: oro sempre > 100 USD/oz
            return price, date_ref, q_label

    return None, None, q_label


def calc_gold_value_usd(gold_tonnes, gold_price_usd_oz):
    """
    Controvalore oro in USD.
    1 tonnellata metrica = 32,150.746 troy oz
    """
    if not gold_tonnes or not gold_price_usd_oz:
        return None
    troy_oz_per_tonne = 32150.746
    return round(gold_tonnes * troy_oz_per_tonne * gold_price_usd_oz / 1e9, 3)  # in MLD USD


# ─────────────────────────────────────────────────────────────────
#  YIELD CURVE — FRED multi-scadenza
# ─────────────────────────────────────────────────────────────────
# Serie FRED per la curva dei tassi per paese
YIELD_CURVE_SERIES = {
    "DE": {"2Y":"IRLTLT01DEM156N","5Y":"IRLTLT01DEM156N","10Y":"IRLTLT01DEM156N","30Y":"IRLTLT01DEM156N"},
    "IT": {"2Y":"IRLTLT01ITM156N","5Y":"IRLTLT01ITM156N","10Y":"IRLTLT01ITM156N","30Y":"IRLTLT01ITM156N"},
    "ES": {"2Y":"IRLTLT01ESM156N","5Y":"IRLTLT01ESM156N","10Y":"IRLTLT01ESM156N","30Y":None},
    "FR": {"2Y":"IRLTLT01FRM156N","5Y":"IRLTLT01FRM156N","10Y":"IRLTLT01FRM156N","30Y":None},
    "NL": {"2Y":"IRLTLT01NLM156N","5Y":"IRLTLT01NLM156N","10Y":"IRLTLT01NLM156N","30Y":None},
    "PL": {"2Y":None,"5Y":None,"10Y":"IRLTLT01PLM156N","30Y":None},
    "RO": {"2Y":None,"5Y":None,"10Y":None,"30Y":None},
}

# Note: FRED ha solo la serie long-term per molti paesi EU.
# Usiamo proxy ECB per 2Y/5Y dove disponibili, altrimenti N/D.
# Serie ECB più precise (formato JSON):
ECB_YIELD_SERIES = {
    "DE": {"2Y":"FM.B.U2.EUR.4F.BB.U2_2Y.YLD","5Y":"FM.B.U2.EUR.4F.BB.U2_5Y.YLD",
           "10Y":"FM.B.U2.EUR.4F.BB.U2_10Y.YLD","30Y":"FM.B.U2.EUR.4F.BB.U2_30Y.YLD"},
    "IT": {"2Y":"FM.B.U2.EUR.4F.BB.U2_2Y.YLD","5Y":"FM.B.U2.EUR.4F.BB.U2_5Y.YLD",
           "10Y":"FM.B.U2.EUR.4F.BB.U2_10Y.YLD","30Y":"FM.B.U2.EUR.4F.BB.U2_30Y.YLD"},
}

@st.cache_data(ttl=3600)
def get_yield_curve(code):
    """
    Recupera la curva dei tassi 3M/2Y/5Y/10Y/30Y per un paese.

    Fonte 1: ECB SDW REST API (sdw-wsrest.ecb.europa.eu)
             Serie AAA Euro Area per scadenza esatta.
             Per paese: aggiunge spread paese vs Germania (dal 10Y FRED).
    Fonte 2: FRED fallback per 10Y per paese.
    Fonte 3: Dati statici di backup.
    Ritorna dict {tenor: (valore, data, fonte)}
    """
    # ── Serie ECB SDW: curva AAA Euro Area per scadenza
    # Endpoint: sdw-wsrest.ecb.europa.eu/service/data/YC/{series}
    ECB_SDW = {
        "3M":  "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_3M",
        "2Y":  "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",
        "5Y":  "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_5Y",
        "10Y": "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y",
        "30Y": "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_30Y",
    }

    # ── 10Y FRED per spread paese
    FRED_10Y = {
        "DE": "IRLTLT01DEM156N", "IT": "IRLTLT01ITM156N",
        "ES": "IRLTLT01ESM156N", "FR": "IRLTLT01FRM156N",
        "NL": "IRLTLT01NLM156N", "PL": "IRLTLT01PLM156N",
        "RO": None,
    }

    result = {}
    tenors = ["3M", "2Y", "5Y", "10Y", "30Y"]

    if code in ("DE", "IT", "ES", "FR", "NL"):
        # Step 1: recupera curva AAA da ECB SDW
        aaa = {}
        base_ecb = "https://sdw-wsrest.ecb.europa.eu/service/data/YC"
        for tenor, series_id in ECB_SDW.items():
            try:
                url = f"{base_ecb}/{series_id}?format=csvdata&lastNObservations=1&detail=dataonly"
                r = requests.get(url, timeout=12,
                    headers={"Accept":"text/csv","User-Agent":"Mozilla/5.0"})
                if r.status_code == 200:
                    import re as _re
                    lines = [l for l in r.text.strip().split("\n")
                             if l and not l.upper().startswith(("KEY","SERIES"))]
                    for line in reversed(lines):
                        parts = [p.strip() for p in line.split(",")]
                        date_found = None
                        val_found  = None
                        for p in parts:
                            if _re.match(r"^\d{4}-\d{2}-\d{2}$", p):
                                date_found = p
                            if val_found is None:
                                try:
                                    fv = float(p)
                                    if -5.0 <= fv <= 25.0:
                                        val_found = round(fv, 3)
                                except:
                                    pass
                        if val_found is not None:
                            aaa[tenor] = (val_found, date_found or "ECB")
                            break
            except:
                pass

        # Step 2: calcola spread paese (10Y FRED paese - 10Y FRED Bund)
        spread = 0.0
        if code != "DE":
            bund_10y, _ = fred_latest(FRED_10Y["DE"])
            ctry_10y, _ = fred_latest(FRED_10Y.get(code))
            if bund_10y and ctry_10y:
                spread = round(ctry_10y - bund_10y, 4)

        # Step 3: componi curva per paese
        for tenor in tenors:
            if tenor in aaa:
                v, d = aaa[tenor]
                country_v = round(v + spread, 3)
                src = "ECB AAA" if code == "DE" else f"ECB AAA+spread {spread:+.3f}%"
                result[tenor] = (country_v, d, src)
            else:
                result[tenor] = (None, None, "N/D su ECB")

        # Step 4: FRED override sul 10Y se ECB non disponibile
        if result.get("10Y", (None,))[0] is None:
            v10, d10 = fred_latest(FRED_10Y.get(code))
            if v10:
                result["10Y"] = (round(v10, 3), d10, "FRED 10Y")

    elif code == "PL":
        for t in tenors:
            result[t] = (None, None, "N/D")
        v10, d10 = fred_latest(FRED_10Y["PL"])
        if v10:
            result["10Y"] = (round(v10, 3), d10, "FRED")

    else:  # RO
        for t in tenors:
            result[t] = (None, None, "N/D")

    return result



# ─────────────────────────────────────────────────────────────────
#  SCENARIO ANALYSIS — variazione prezzo per shift tassi
# ─────────────────────────────────────────────────────────────────
def scenario_price_change(prezzo, dur_mod, conv, delta_y_bp):
    """
    Stima la variazione percentuale del prezzo per uno shift parallelo
    della curva di delta_y_bp basis points.
    Formula: ΔP/P ≈ -DM * Δy + 0.5 * Convexity * Δy²
    """
    if not prezzo or not dur_mod:
        return None
    dy = delta_y_bp / 10000.0
    dp_pct = -dur_mod * dy
    if conv:
        dp_pct += 0.5 * conv * dy**2
    new_price = round(prezzo * (1 + dp_pct), 4)
    dp_abs = round(new_price - prezzo, 4)
    dp_pct_rounded = round(dp_pct * 100, 3)
    return {"delta_bp": delta_y_bp, "new_price": new_price,
            "dp_abs": dp_abs, "dp_pct": dp_pct_rounded}


def calc_scenario_table(prezzo, dur_mod, conv, scenarios_bp=None):
    """
    Calcola la tabella degli scenari per una serie di shift in bp.
    Default: da -300 a +300 bp.
    """
    if scenarios_bp is None:
        scenarios_bp = [-300, -200, -100, -50, 0, +50, +100, +200, +300]
    rows = []
    for bp in scenarios_bp:
        r = scenario_price_change(prezzo, dur_mod, conv, bp)
        if r:
            rows.append(r)
    return rows


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
    # ── Session state: mantiene ISIN e paese XS tra i rerun di Streamlit
    if "gov_isin" not in st.session_state:
        st.session_state.gov_isin = ""
    if "gov_run" not in st.session_state:
        st.session_state.gov_run = False

    st.markdown("### Inserisci ISIN Governativo")
    c1, c2 = st.columns([4,1])
    with c1:
        isin_input = st.text_input("ISIN", key="isin_gov",
            placeholder="es. IT0005534141", label_visibility="collapsed").strip().upper()
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        go_gov = st.button("🔍 Analizza", key="btn_gov", use_container_width=True, type="primary")

    st.caption("Esempi gov. EUR: IT0005534141 (BTP) · DE0001102580 (Bund) · ES0000012B39 (Bonos) · FR0014004L86 (OAT)  |  Eurobond XS: XS2832668606 (Romania XS) · XS2692298962 (Poland XS)")

    if go_gov and isin_input:
        st.session_state.gov_isin = isin_input
        st.session_state.gov_run  = True
        # Reset conferma XS quando si analizza un nuovo ISIN
        st.session_state.pop("gov_xs_confirmed", None)

    isin_gov = st.session_state.gov_isin

    if st.session_state.gov_run and isin_gov:
        if len(isin_gov) != 12 or not isin_gov[:2].isalpha() or not isin_gov[2:].isalnum():
            st.error("❌ ISIN non valido."); st.stop()

        prefix = isin_gov[:2]
        if prefix not in ISIN_MAP:
            st.error(f"Prefisso {prefix} non supportato."); st.stop()
        code = ISIN_MAP[prefix]

        # ── Gestione ISIN XS
        if code is None:
            st.divider()
            st.markdown(
                '<div style="background:#fef3c7;border-left:5px solid #f59e0b;'
                'border-radius:8px;padding:12px 16px;margin-bottom:12px;">'
                '<strong>🌍 Eurobond XS rilevato</strong> — seleziona il paese emittente '
                'per caricare i dati macro e procedere con l\'analisi.</div>',
                unsafe_allow_html=True
            )
            xs_paese_sel = st.selectbox(
                "Paese emittente",
                ["Romania", "Polonia"],
                key="xs_paese_sel",
                help="Seleziona il paese che ha emesso questo Eurobond",
                index=0 if st.session_state.get("gov_xs_paese","Romania")=="Romania" else 1,
            )
            xs_go = st.button("✅ Conferma paese e analizza", key="xs_go", type="primary")
            if xs_go:
                st.session_state.gov_xs_paese     = xs_paese_sel
                st.session_state.gov_xs_confirmed = True
                st.rerun()
            if not st.session_state.get("gov_xs_confirmed", False):
                st.stop()
            xs_paese = st.session_state.get("gov_xs_paese", "Romania")
            code     = "RO" if xs_paese == "Romania" else "PL"
            xs_mode  = True
        else:
            st.session_state.pop("gov_xs_confirmed", None)
            xs_mode = False

        macro = MACRO_DB[code]
        flag  = FLAGS.get(code,"🏳️")

        # Per Eurobond XS: valuta sempre EUR, spread vs Bund calcolabile
        if xs_mode:
            macro = dict(macro)          # copia per non modificare il DB
            macro["valuta"]    = "EUR"   # Eurobond sempre in EUR
            macro["strumento"] = f"{macro['strumento']} Eurobond (XS)"
            # Spread auto attivato: il rendimento è in EUR, confrontabile col Bund
            macro["spread_auto"] = True

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

        # Frequenza cedola: 1) Borsa Italiana (fonte primaria)
        #                   2) Libreria interna MACRO_DB (freq_cedola)
        #                   3) Default annuale (standard per gov bond)
        periodo_raw = (bi.get("periodicita") or "").lower()
        if "trim" in periodo_raw or "quarter" in periodo_raw:
            freq = 4
        elif "semestral" in periodo_raw or "semi" in periodo_raw or "biannual" in periodo_raw:
            freq = 2
        elif "annual" in periodo_raw or "annua" in periodo_raw:
            freq = 1
        else:
            # Nessuna info da BI → usa libreria interna
            freq = macro.get("freq_cedola", 1)

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
        tipo_label = "Governativo Sovrano — Eurobond (XS)" if xs_mode else "Governativo Sovrano"
        badge_xs   = (' <span style="background:#fef3c7;color:#92400e;font-size:11px;'
                      'font-weight:700;padding:2px 8px;border-radius:4px;'
                      'border:1px solid #f59e0b;">EUROBOND XS</span>'
                      if xs_mode else "")
        st.markdown(f"""
        <div style="background:#f1f5f9;border-radius:10px;padding:16px 22px;margin-bottom:20px;">
        <div style="font-size:20px;font-weight:800;color:#0f172a;">{flag} {isin_gov}{badge_xs}</div>
        <div style="color:#475569;font-size:14px;margin-top:3px;">
        {bi.get("descrizione") or "—"} &nbsp;·&nbsp; {macro["paese"]} &nbsp;·&nbsp;
        {divisa_f} &nbsp;·&nbsp; {bi.get("mercato") or "EuroMOT"} &nbsp;·&nbsp; {tipo_label}
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
            card("Scadenza / Data Rimborso", format_date(scadenza_s),
                 f"anni residui: {round(anni_f,2)}" if anni_f else "")
            card("Mercato", bi.get("mercato") or "—", "piazza di quotazione")

        # Accrued Interest / Tel Quel
        if prezzo_f and cedola_f:
            rateo, gg_trascorsi, gg_periodo = calc_accrued_interest(cedola_f, freq)
            tel_quel = round(prezzo_f + (rateo or 0), 4) if rateo is not None else None
            ai1, ai2, ai3 = st.columns(3)
            with ai1:
                card("Accrued Interest (Rateo)",
                     f"{rateo:.4f}" if rateo is not None else "N/D",
                     f"giorni trascorsi: {gg_trascorsi or '—'} / {gg_periodo or '—'}",
                     "#7c3aed")
            with ai2:
                card("Corso Secco (Clean Price)",
                     f"{prezzo_f:.4f}" if prezzo_f else "N/D",
                     "prezzo Borsa Italiana — esclude rateo",
                     "#0f172a")
            with ai3:
                card("Prezzo Tel Quel (Dirty Price)",
                     f"{tel_quel:.4f}" if tel_quel else "N/D",
                     "corso secco + rateo — prezzo effettivo pagato",
                     "#7c3aed")

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

        # Dati macro estesi dalla libreria interna
        with st.expander("📊 Dati Macro Estesi — " + macro["paese"], expanded=False):
            me1, me2, me3, me4 = st.columns(4)
            with me1:
                card("PIL",
                     f"{macro['pil_mld']:,.0f} MLD USD",
                     f"rif. {macro['pil_ref']}", "#0f172a")
                card("Deficit / PIL",
                     f"{macro['deficit_pil']:.1f}%",
                     f"rif. {macro['deficit_ref']}",
                     "#22c55e" if macro["deficit_pil"]<3 else ("#eab308" if macro["deficit_pil"]<5 else "#ef4444"))
            with me2:
                card("% Interessi / PIL",
                     f"{macro['int_spesa_pil']:.2f}%",
                     f"rif. {macro['int_ref']}",
                     "#22c55e" if macro["int_spesa_pil"]<2 else ("#eab308" if macro["int_spesa_pil"]<3.5 else "#ef4444"))
                card("Inflazione",
                     f"{macro['inflazione']:.1f}%",
                     f"rif. {macro['infl_ref']}",
                     "#22c55e" if macro["inflazione"]<2.5 else ("#eab308" if macro["inflazione"]<4 else "#ef4444"))
            with me3:
                card("Disoccupazione",
                     f"{macro['disoccupazione']:.1f}%",
                     f"rif. {macro['disoc_ref']}",
                     "#22c55e" if macro["disoccupazione"]<5 else ("#eab308" if macro["disoccupazione"]<8 else "#ef4444"))
                card("Riserve Valutarie",
                     f"{macro['fx_reserves']:,.1f} MLD" if macro.get("fx_reserves") else "N/D",
                     f"rif. {macro['fx_ref']}", "#0f172a")
            with me4:
                # Oro con valorizzazione dinamica al prezzo del trimestre precedente
                with st.spinner("Prezzo oro..."):
                    gp, gp_date, gp_q = get_gold_price_prev_quarter()
                gold_t_val = macro.get("gold_t", 0)
                gold_calc  = calc_gold_value_usd(gold_t_val, gp) if gp else None
                if gold_calc:
                    gold_sub = f"{gold_calc:,.2f} MLD USD ({gp_q} | ${gp:,.0f}/oz)"
                    gold_col = "#22c55e"
                else:
                    gold_sub = f"≈ {macro['gold_usd']:.1f} MLD USD (libreria) | rif. {macro['gold_ref']}"
                    gold_col = "#b45309"
                card("Gold Reserve",
                     f"{gold_t_val:,.2f} t",
                     gold_sub, gold_col)
                card("Area / Banca Centrale",
                     macro["area"],
                     macro["banca"], "#0f172a")
            st.markdown(
                f'<div style="background:#fef9c3;border-left:4px solid #eab308;'
                f'border-radius:8px;padding:10px 14px;margin-top:8px;font-size:13px;color:#0f172a;">'
                f'<strong>⚠️ Note di Rischio:</strong> {macro.get("note_rischio","—")}'
                f'</div>', unsafe_allow_html=True)

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

        # ── CURVA DEI TASSI
        section("Curva dei Tassi","📈")

        # Mappa paese → slug WGB
        WGB_COUNTRY = {
            "DE":"germany","IT":"italy","ES":"spain","FR":"france",
            "NL":"netherlands","PL":"poland","RO":"romania",
        }
        wgb_slug = WGB_COUNTRY.get(code, "")
        wgb_url  = f"https://www.worldgovernmentbonds.com/country/{wgb_slug}/"

        # Recupera 10Y da FRED (unica serie affidabile per paese)
        fred_10y_series = {
            "DE":"IRLTLT01DEM156N","IT":"IRLTLT01ITM156N",
            "ES":"IRLTLT01ESM156N","FR":"IRLTLT01FRM156N",
            "NL":"IRLTLT01NLM156N","PL":"IRLTLT01PLM156N","RO":None,
        }
        with st.spinner("Recupero rendimento 10Y..."):
            y10, d10 = fred_latest(fred_10y_series.get(code))

        # Card 10Y da FRED
        c10a, c10b, _ = st.columns([1, 1, 3])
        with c10a:
            card("Rendimento 10Y",
                 f"{y10:.3f}%" if y10 else "N/D",
                 f"rif. {d10}  |  FRED" if d10 else "FRED",
                 "#0ea5e9" if y10 else "#94a3b8")
        with c10b:
            card("Spread vs Bund",
                 f"{spread_bp_final:+.1f} bp" if spread_bp_final is not None else "N/D",
                 "calcolato nella sezione sopra",
                 spread_color(spread_bp_final) if spread_bp_final is not None else "#94a3b8")

        # Box link WGB per curva completa (3M/2Y/5Y/10Y/30Y)
        st.markdown(
            f'<div style="background:#f1f5f9;border-radius:10px;padding:14px 18px;'
            f'border-left:5px solid #0ea5e9;margin-top:8px;">'
            f'<div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.08em;">Curva dei Tassi Completa — {macro["paese"]}</div>'
            f'<div style="font-size:13px;color:#0f172a;margin-top:6px;">'
            f'La curva multi-scadenza (3M · 2Y · 5Y · 10Y · 30Y) con dati in tempo reale,'
            f' storico e analisi di inversione è disponibile su '
            f'<strong>World Government Bonds</strong>.</div>'
            f'<a href="{wgb_url}" target="_blank" '
            f'style="display:inline-block;margin-top:10px;background:#0ea5e9;color:white;'
            f'font-size:12px;font-weight:600;padding:6px 14px;border-radius:6px;'
            f'text-decoration:none;">'
            f'📈 Consulta Yield Curve — {macro["paese"]}</a>'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── CDS SPREAD SOVRANO
        section("CDS Spread Sovrano","🛡️")
        # Mappa paese italiano → nome inglese per World Government Bonds
        CDS_COUNTRY_EN = {
            "DE": "Germany",  "IT": "Italy",
            "ES": "Spain",    "FR": "France",
            "NL": "Netherlands","PL": "Poland","RO": "Romania",
        }
        cds_base = "https://www.worldgovernmentbonds.com/cds-historical-data/"
        cds_country_en = CDS_COUNTRY_EN.get(code, macro["paese"])
        st.markdown(
            f'<div style="background:#f1f5f9;border-radius:10px;padding:14px 18px;'
            f'border-left:5px solid #6366f1;margin-bottom:12px;">'
            f'<div style="font-size:10px;color:#64748b;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.08em;">CDS Spread Sovrano — {macro["paese"]} ({cds_country_en})</div>'
            f'<div style="font-size:13px;color:#0f172a;margin-top:6px;">'
            f'I dati CDS sono caricati in JavaScript dinamico e non scrapabili automaticamente.<br>'
            f'Consulta la pagina storica su <strong>World Government Bonds</strong> e cerca '
            f'<strong>{cds_country_en}</strong> nella tabella.</div>'
            f'<a href="{cds_base}" target="_blank" style="display:inline-block;margin-top:10px;'
            f'background:#6366f1;color:white;font-size:12px;font-weight:600;padding:6px 14px;'
            f'border-radius:6px;text-decoration:none;">'
            f'🔗 CDS Historical Data — cerca: {cds_country_en}</a>'
            f'</div>',
            unsafe_allow_html=True
        )

        # S4: Rendimento & Rischio
        section("Analisi Rendimento & Rischio","💹")
        col_tax, _ = st.columns([1,3])
        with col_tax:
            # Eurobond XS → 26% (non beneficiano dell'aliquota agevolata 12,5%)
            default_tax = 26.0 if xs_mode else 12.5
            tax_rate = st.number_input("Aliquota fiscale (%)", min_value=0.0, max_value=50.0,
                value=default_tax, step=0.5,
                help="12,5% titoli di stato UE  |  26% Eurobond XS e corporate")

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

        # ── SCENARIO ANALYSIS
        if prezzo_f and dur_mod:
            section("Scenario Analysis — Variazione Prezzo per Shift Tassi","📉")
            st.caption("Stima la variazione del prezzo al variare dei tassi di interesse (shift parallelo della curva). Formula: ΔP/P ≈ −Duration × Δy + ½ × Convexity × Δy²")

            col_sc1, col_sc2 = st.columns([2, 4])
            with col_sc1:
                custom_bp = st.number_input(
                    "Aggiungi scenario personalizzato (bp)",
                    min_value=-1000, max_value=1000, value=0, step=25,
                    key="custom_bp",
                    help="Inserisci uno shift personalizzato in basis points (es. +150 o -75)"
                )
            scenarios = [-300, -200, -100, -50, 0, +50, +100, +200, +300]
            if custom_bp != 0 and custom_bp not in scenarios:
                scenarios = sorted(set(scenarios + [custom_bp]))

            scenario_rows = calc_scenario_table(prezzo_f, dur_mod, conv, scenarios)

            if scenario_rows:
                # Tabella heatmap
                df_sc = pd.DataFrame(scenario_rows)
                df_sc.columns = ["Shift (bp)", "Nuovo Prezzo", "ΔP (abs)", "ΔP (%)"]

                def color_dp(val):
                    try:
                        v = float(val)
                        if v > 2:    return "background-color:#dcfce7;color:#14532d"
                        if v > 0:    return "background-color:#f0fdf4;color:#166534"
                        if v == 0:   return "background-color:#f8fafc;color:#0f172a;font-weight:600"
                        if v > -2:   return "background-color:#fff7ed;color:#7c2d12"
                        return            "background-color:#fee2e2;color:#7f1d1d"
                    except:
                        return ""

                styled = df_sc.style.map(color_dp, subset=["ΔP (%)"]).format({
                    "Shift (bp)": lambda x: f"{x:+.0f} bp",
                    "Nuovo Prezzo": "{:.4f}",
                    "ΔP (abs)": "{:+.4f}",
                    "ΔP (%)": "{:+.3f}%",
                })
                st.dataframe(styled, use_container_width=True, hide_index=True)

                # Grafico Plotly
                import plotly.graph_objects as go_sc
                colors = ["#22c55e" if r["dp_pct"] > 0 else ("#94a3b8" if r["dp_pct"] == 0 else "#ef4444")
                          for r in scenario_rows]
                fig_sc = go_sc.Figure()
                fig_sc.add_trace(go_sc.Bar(
                    x=[f"{r['delta_bp']:+d} bp" for r in scenario_rows],
                    y=[r["dp_pct"] for r in scenario_rows],
                    marker_color=colors,
                    text=[f"{r['dp_pct']:+.2f}%" for r in scenario_rows],
                    textposition="outside",
                    name="ΔP (%)"
                ))
                fig_sc.update_layout(
                    title="Variazione % prezzo per shift parallelo della curva",
                    xaxis_title="Shift tassi (bp)",
                    yaxis_title="ΔP (%)",
                    height=360,
                    margin=dict(t=50, b=30, l=40, r=20),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    showlegend=False,
                    font=dict(size=11),
                )
                fig_sc.add_hline(y=0, line_dash="dash", line_color="#94a3b8", line_width=1)
                st.plotly_chart(fig_sc, use_container_width=True)

        # S5: Riepilogo
        section("Riepilogo Scheda Completa","📄")
        recap = {
            "Campo":["ISIN","Descrizione","Paese","Tipologia","Rating (S&P / Fitch)",
                     "Debito/PIL","Household Debt/PIL","Spread vs Bund",
                     "Prezzo di regolamento","Divisa","Taglio Minimo",
                     "Data Rimborso","Tasso cedolare","Periodicità cedola",
                     "Scadenza","Duration Modificata","Convexity",
                     "Rend. Lordo","Rend. Netto","Tassazione applicata"],
            "Valore":[
                isin_gov, bi.get("descrizione") or "—", macro["paese"],
                "Governativo Sovrano — Eurobond (XS)" if xs_mode else "Governativo Sovrano",
                f"{sp_r['v']} / {fi_r['v']}", f"{debt:.1f}%", f"{hh:.1f}%",
                f"{bp:+.1f} bp" if bp is not None else "N/D",
                f"{prezzo_f:.2f}" if prezzo_f else (bi.get("prezzo") or "N/D"),
                divisa_f, bi.get("taglio_minimo") or "N/D",
                format_date(scadenza_s),
                f"{cedola_f:.3f}%" if cedola_f else "N/D",
                periodo_disp, format_date(scadenza_s),
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
            card("Scadenza / Data Rimborso", format_date(scadenza_c),
                 f"anni residui: {round(anni_c,2)}" if anni_c else "")
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
                format_date(scadenza_c), cedola_clbl, periodo_cd,
                format_date(scadenza_c), corp_seniority,
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
