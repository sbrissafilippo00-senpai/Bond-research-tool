# Bond Research Tool
**B-Adviser S.r.l. | Analisi e Consulenza Finanziaria**

Web app Streamlit per l'analisi di obbligazioni governative e corporate.

## Funzionalità

### Tab Governativi
- Inserisci un ISIN → il tool recupera automaticamente tutti i dati
- **Dati macro live** (FRED / St. Louis Fed): Debt/PIL, Household Debt/PIL, Rendimento 10Y, Spread vs Bund
- **Dati titolo** (Borsa Italiana): Prezzo, Cedola, Scadenza, Taglio Minimo, Duration, Convexity
- **Calcoli automatici**: YTM (rendimento lordo), Rendimento Netto, Duration Modificata, Convexity
- **Rating** (S&P Global + Fitch): aggiornati manualmente in `app.py` → `MACRO_DB`

### Tab Corporate
- Stessi dati titolo da Borsa Italiana
- Pannello dati emittente (manuale): EBITDA, Debito, FCF, Leva, Seniority
- Calcolo automatico ratios: Debt/EBITDA, FCF/Debt, copertura interessi

### Campi coperti (da scheda B-Adviser)
`ISIN` · `Descrizione` · `Paese` · `Rating` · `Debito/PIL` · `Household Debt/PIL` ·
`Spread` · `Prezzo di regolamento` · `Divisa` · `Taglio Minimo` · `Data Rimborso` ·
`Tasso cedolare` · `Periodicità cedola` · `Scadenza` · `Duration Modificata` ·
`Convexity` · `Rend. Lordo` · `Rend. Netto` · `Tassazione applicata`

## Paesi governativi supportati
🇩🇪 Germania · 🇮🇹 Italia · 🇪🇸 Spagna · 🇫🇷 Francia · 🇳🇱 Olanda · 🇵🇱 Polonia · 🇷🇴 Romania

## Aggiornamento dati rating
Apri `app.py` e modifica il blocco `MACRO_DB` con i nuovi rating quando le agenzie pubblicano aggiornamenti.

## Deploy su Streamlit Cloud
1. Fork o upload di questo repository su GitHub
2. Vai su [share.streamlit.io](https://share.streamlit.io)
3. "New app" → seleziona il repo → `app.py` → Deploy

## Stack tecnologico
- **Frontend/Backend**: Streamlit
- **Dati macro**: FRED API (St. Louis Fed) — gratuita, no API key
- **Dati titolo**: Borsa Italiana (web scraping)
- **Calcoli**: Python puro (YTM Newton-Raphson, Duration, Convexity)
- **Grafici**: Plotly

## Note legali
Questo tool è ad uso interno di B-Adviser S.r.l. e non costituisce consulenza finanziaria.
