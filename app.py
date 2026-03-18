import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import textwrap
from streamlit_calendar import calendar

# --- 1. CONFIGURAZIONE PAGINA E COSTANTI ---
LOGO_URL = "https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png"
st.set_page_config(page_title="Aster Contract", page_icon=LOGO_URL, layout="wide")

STATI_COMMESSA = ["Quotazione 🟣", "Pianificata 🔵", "In corso 🟡", "Completata 🟢", "Sospesa 🟠", "Cancellata 🔴"]
STATI_TASK = ["Pianificato 🔵", "In corso 🟡", "Completato 🟢", "Sospeso 🟠"]

# --- 3. CONNESSIONE E CACHING ---
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=60)
def get_cached_data(table):
    try: return supabase.table(table).select("*").execute().data
    except: return []

if 'chart_key' not in st.session_state:
    st.session_state.chart_key = 0
if 'vista_compressa' not in st.session_state:
    st.session_state.vista_compressa = False

# --- 2. CSS ---
st.markdown(f"""
    <head>
        <link rel="icon" href="https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png" type="image/png">
        <link rel="shortcut icon" href="https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png" type="image/png">
        <link rel="apple-touch-icon" href="https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png">
    </head>
""", unsafe_allow_html=True)
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ visibility: hidden; height: 0px; }}
    .block-container {{ padding-top: 0rem !important; padding-bottom: 0rem !important; margin-top: -30px; }}
    
    /* Riduce lo spazio tra gli elementi dei filtri */
    [data-testid="stVerticalBlock"] > div {{
        gap: 0rem !important;
    }}
    
    .compact-title {{ display: flex; align-items: center; gap: 0px; padding-top: 0px; }}
    .compact-title h1 {{ font-size: 22px !important; color: #1E3A8A; margin: 0; }}
    
    /* Header fisso ultra-compatto */
    div[data-testid="stVerticalBlock"] > div:has(.fixed-header) {{
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        padding-bottom: 0px;
        border-bottom: 1px solid #f0f2f6;
    }}

    /* Rimuove lo spazio specifico sopra le Tab */
    [data-testid="stTabs"] {{
        margin-top: -10px !important;
     }}
    
    /* Riduce il margine superiore dei bottoni e dei widget */
    .stButton, .stMultiSelect, .stSelectbox, .stDateInput {{
        margin-bottom: -10px !important;
    }}
    
    /* Riduce lo spazio interno delle colonne */
    [data-testid="column"] {{
        padding: 0px 5px !important;
        margin-bottom: -10px !important;
    }}
    .legend-container {{
        display: flex; 
        flex-direction: column; 
        gap: 2px; 
        padding: 10px 15px; 
        background: #f8f9fa; 
        border-radius: 8px; 
        border: 1px solid #eee;
    }}
    
    /* Singola riga della legenda */
    .legend-row {{
        display: flex;
        flex-direction: row; /* Voci in orizzontale */
        align-items: center;
        gap: 6px;
        flex-wrap: nowrap; /* Evita che vadano a capo se c'è spazio */
        overflow-x: auto;   /* Permette lo scroll orizzontale su schermi piccoli */
    }}

    /* Titolo della riga (es: OPERATORI) */
    .legend-label {{
        font-weight: bold;
        color: #888;
        min-width: 90px;
        font-size: 10px;
        text-transform: uppercase;
    }}

    /* Pillola singola */
    .legend-pill {{
        display: flex;
        align-items: center;
        gap: 3px;
        padding: 2px 10px;
        border-radius: 20px;
        border: 1px solid #ddd;
        font-size: 11px;
        white-space: nowrap;
    }}
    
    /* REGOLE PER LA STAMPA */
    @media print {{
    /* Imposta la pagina A4 Orizzontale */
        @page {{
            size: A4 landscape;
            margin: 0.5cm;
        }}
        
        /* Nasconde sidebar, pulsanti, filtri e footer di Streamlit */
        [data-testid="stSidebar"], 
        [data-testid="stHeader"],
        .stButton, 
        [data-testid="stSelectbox"], 
        [data-testid="stMultiSelect"],
        [data-testid="stTabs"] [role="tablist"], /* Nasconde i titoli dei Tab */
        footer {{
            display: none !important;
        }}

    /* Forza il contenitore a occupare tutto lo spazio */
        .block-container {{
            padding: 0 !important;
            margin: 0 !important;
            top: 0 !important;
        }}

    /* Assicura che il grafico Plotly sia visibile */
        .js-plotly-plot {{
            width: 100% !important;
        }}
        
    /* Evita che la legenda venga tagliata tra due pagine */
        .legend-container {{
            break-inside: avoid;
            border: 1px solid #ccc !important;
        }}
    /* Compatta l'header Aster per la stampa */
        .legend-container {{
            margin-bottom: 7px !important;
            padding: 5px !important;
        }}

        /* Rimuove lo spazio bianco tra header e grafico */
        [data-testid="stVerticalBlock"] {{
            gap: 0 !important;
        }}
        /* Rimuove la linea sotto le Tab e il bordo del contenitore delle Tab */
        [data-testid="stTabs"] {{
            border-bottom: none !important;
            box-shadow: none !important;
        }}
    
        [data-testid="stTab"] {{
            border-bottom: none !important;
            box-shadow: none !important;
        }}

        /* Rimuove la linea di separazione decorativa delle Tab di Streamlit */
        div[data-baseweb="tab-list"] {{
            border-bottom: none !important;
            box-shadow: none !important;
        }}

        /* Rimuove eventuali bordi dai blocchi verticali */
        [data-testid="stVerticalBlock"] > div {{
            border: none !important;
            box-shadow: none !important;
        }}
    
        /* Se avevi un <hr> o un st.divider(), questo lo nasconde */
        hr {{
            display: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }}
    }}
    </style>
""", unsafe_allow_html=True)

header_col1, header_col2 = st.columns([1, 4])

with header_col1:
    st.markdown(f"""
        <div class="compact-title" style="margin-top: 5px;">
            <img src="{LOGO_URL}" width="30">
            <h1 style="font-size: 18px !important; margin-left: 5px;">Progetti Aster</h1>
        </div>
    """, unsafe_allow_html=True)

with header_col2:
    # Generazione Legenda Operatori Dinamica
    ops = get_cached_data("Operatori")
    op_html = "".join([f'<div class="legend-pill" style="background-color:{o.get("colore", "#8dbad2")}">{o["nome"]}</div>' for o in ops])
    
    # Legende Stati
    cm_html = "".join([f'<div class="legend-pill">{s}</div>' for s in STATI_COMMESSA])
    tk_html = "".join([f'<div class="legend-pill">{s}</div>' for s in STATI_TASK])
    
    st.markdown(f"""
        <div class="legend-container">
            <div class="legend-row">
                <span class="legend-label">👤 Operatori</span>
                {op_html}
            </div>
            <div class="legend-row">
                <span class="legend-label">🏗️ Progetti</span>
                {cm_html}
            </div>
            <div class="legend-row">
                <span class="legend-label">📋 Task</span>
                {tk_html}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
# --- 4. FUNZIONI DI AGGIORNAMENTO DB (SETUP) ---
def aggiorna_database_setup(nome_tabella, edited_df, original_df):
    try:
        ids_originali = set(pd.DataFrame(original_df)['id'].tolist()) if original_df else set()
        ids_attuali = set(edited_df['id'].dropna().tolist())
        ids_da_eliminare = ids_originali - ids_attuali
        
        for idx in ids_da_eliminare:
            supabase.table(nome_tabella).delete().eq("id", idx).execute()

        for _, row in edited_df.iterrows():
            row_dict = row.dropna().to_dict()
            if pd.isna(row.get('id')):
                row_dict.pop('id', None)
                supabase.table(nome_tabella).insert(row_dict).execute()
            else:
                curr_id = row_dict.pop('id')
                supabase.table(nome_tabella).update(row_dict).eq("id", curr_id).execute()
        st.success(f"Dati {nome_tabella} aggiornati!")
        get_cached_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"Errore: {e}")

# --- 5. MODALI ---
@st.dialog("Gestione Task & Log")
def modal_gestione_clic(task_id, data_clic):
    cm_data, tk_data = get_cached_data("Commesse"), get_cached_data("Task")
    task_info = next((t for t in tk_data if t['id'] == task_id), None)
    if not task_info: 
        st.error("Task non trovato.")
        return
    commessa_info = next((c for c in cm_data if c['id'] == task_info['commessa_id']), None)
    
    st.subheader("🏗️ Modifica Anagrafica")
    with st.expander("Nomi e Stati", expanded=False):
        new_tk_name = st.text_input("Nome Task", value=task_info.get('nome_task', ''))
        new_tk_status = st.selectbox("Stato Task", options=STATI_TASK, index=STATI_TASK.index(task_info.get('stato', STATI_TASK[0])))
        if commessa_info:
            new_cm_name = st.text_input("Nome Commessa", value=commessa_info.get('nome_commessa', ''))
            new_cm_status = st.selectbox("Stato Commessa", options=STATI_COMMESSA, index=STATI_COMMESSA.index(commessa_info.get('stato', STATI_COMMESSA[0])))
        if st.button("Salva Modifiche", use_container_width=True):
            supabase.table("Task").update({"nome_task": new_tk_name, "stato": new_tk_status}).eq("id", task_id).execute()
            if commessa_info: supabase.table("Commesse").update({"nome_commessa": new_cm_name, "stato": new_cm_status}).eq("id", commessa_info['id']).execute()
            get_cached_data.clear(); st.rerun()
            
    st.divider()
    st.subheader(f"⏱️ Nuovo Log - {data_clic.strftime('%d/%m/%Y')}")
    date_range = st.date_input(
        "Periodo Log", 
        value=(data_clic, data_clic), # Range predefinito (Inizio, Fine)
        format="DD/MM/YYYY"
    )
    ops = [o['nome'] for o in get_cached_data("Operatori")]
    op_sel = st.multiselect("Seleziona Operatore", ops)
    nota = st.text_input("Nota log")
    c1, c2 = st.columns(2)
    if c1.button("Registra Log", type="primary", use_container_width=True):
        if not ops_selezionati:
            st.warning("Seleziona almeno un operatore.")
        elif len(date_range) < 2:
            st.warning("Seleziona sia la data di inizio che quella di fine nel calendario.")
        else:
            data_inizio, data_fine = date_range
            nuovi_log = []
            for op in ops_selezionati:
                nuovi_log.append({
                    "task_id": task_id,
                    "operatore": op,
                    "inizio": str(data_inizio),
                    "fine": str(data_fine),
                    "note": nota
                })
            try:
                supabase.table("Log_Tempi").insert(nuovi_log).execute()
                st.success(f"Inseriti {len(ops_selezionati)} log con successo!")
                get_cached_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Errore durante l'inserimento: {e}")
        
        get_cached_data.clear()
        st.empty()
        st.session_state.chart_key += 1
        st.switch_page("app.py")
        st.rerun()
        
    if c2.button("Annulla", use_container_width=True): 
        get_cached_data.clear()
        st.empty()
        st.session_state.chart_key += 1
        st.switch_page("app.py")
        st.rerun()    
        
@st.dialog("📝 Gestione Dettaglio Log")
def modal_edit_log(log_id, current_op, current_start, current_end, current_task_id, current_note=""):
    st.markdown("""<style>div[data-testid="stDialog"] div[role="dialog"] { width: 90vw !important; max-width: 1300px !important; }</style>""", unsafe_allow_html=True)
    
    # --- 1. DATI DALLA CACHE ---
    cm_data, tk_data = get_cached_data("Commesse"), get_cached_data("Task")
    # Recuperiamo anche la lista nomi operatori per il menu a tendina nella tabella
    ops_list = sorted([o['nome'] for o in get_cached_data("Operatori")])
    
    cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
    cms_id_to_nome = {c['id']: c['nome_commessa'] for c in cm_data}
    
    current_task_info = next((t for t in tk_data if t['id'] == current_task_id), None)
    if not current_task_info:
        st.error("Dati task non trovati."); return
    
    curr_cm_id = current_task_info['commessa_id']
    curr_cm_nome = cms_id_to_nome.get(curr_cm_id, list(cms_dict.keys())[0])

    # --- 2. UI SPOSTAMENTO RAPIDO (Intestazione) ---
    st.info("💡 Modifica i dettagli qui sotto. Se cambi 'Commessa/Task' sopra, sposterai TUTTI i log visualizzati.")
    col_c, col_t, col_s = st.columns(3)
    
    with col_c:
        list_cm = list(cms_dict.keys())
        sel_cm_nome = st.selectbox("Sposta in Commessa:", options=list_cm, index=list_cm.index(curr_cm_nome), key="ed_cm")
        sel_cm_id = cms_dict[sel_cm_nome]
    
    with col_t:
        tasks_filtrati = [t for t in tk_data if t['commessa_id'] == sel_cm_id]
        task_opts = {t['nome_task']: t['id'] for t in tasks_filtrati}
        list_tk = list(task_opts.keys())
        idx_tk = list_tk.index(current_task_info['nome_task']) if current_task_info['nome_task'] in list_tk else 0
        sel_task_nome = st.selectbox("Sposta in Task:", options=list_tk, index=idx_tk, key="ed_tk")
        id_task_target = task_opts[sel_task_nome]

    with col_s:
        current_status = next((t['stato'] for t in tasks_filtrati if t['nome_task'] == sel_task_nome), STATI_TASK[0])
        nuovo_stato_task = st.selectbox("Aggiorna Stato Task:", options=STATI_TASK, index=STATI_TASK.index(current_status))

    st.divider()

    # --- 3. DATA EDITOR CON CAMBIO OPERATORE ---
    all_logs = supabase.table("Log_Tempi").select("*").eq("operatore", current_op).eq("task_id", current_task_id).execute().data
    df_sub = pd.DataFrame(all_logs)
    
    if not df_sub.empty:
        df_sub['inizio'] = pd.to_datetime(df_sub['inizio']).dt.date
        df_sub['fine'] = pd.to_datetime(df_sub['fine']).dt.date
        mask = (df_sub['inizio'] >= pd.to_datetime(current_start).date()) & (df_sub['inizio'] <= pd.to_datetime(current_end).date())
        df_sub = df_sub[mask].copy()
        df_sub["Elimina"] = False

    if df_sub.empty:
        st.warning("Nessun log trovato."); return

    # Editor con colonna Operatore come Selectbox
    edited_df = st.data_editor(
        df_sub,
        column_config={
            "id": None, "task_id": None,
            "operatore": st.column_config.SelectboxColumn(
                "Operatore",
                options=ops_list,
                width="medium",
                required=True
            ),
            "inizio": st.column_config.DateColumn("Inizio", format="DD/MM/YYYY"),
            "fine": st.column_config.DateColumn("Fine", format="DD/MM/YYYY"),
            "note": st.column_config.TextColumn("Note", width="large"),
            "Elimina": st.column_config.CheckboxColumn("Elimina", default=False)
        },
        disabled=["id", "task_id"],
        use_container_width=True, hide_index=True, key="editor_v10"
    )

    # --- 4. SALVATAGGIO ---
    c1, c2 = st.columns(2)
    if c1.button("Salva Tutto", type="primary", use_container_width=True):
        # A. Stato Task
        supabase.table("Task").update({"stato": nuovo_stato_task}).eq("id", id_task_target).execute()
        
        # B. Loop Log
        for _, row in edited_df.iterrows():
            if row["Elimina"]:
                supabase.table("Log_Tempi").delete().eq("id", row["id"]).execute()
            else:
                supabase.table("Log_Tempi").update({
                    "task_id": id_task_target,
                    "operatore": row["operatore"], # Salva il nuovo operatore scelto nella riga
                    "inizio": str(row["inizio"]),
                    "fine": str(row["fine"]),
                    "note": str(row["note"]) if row["note"] else ""
                }).eq("id", row["id"]).execute()
            
        st.success("Dati aggiornati!")
        get_cached_data.clear()
        st.session_state.chart_key += 1
        st.rerun()

    if c2.button("Annulla", use_container_width=True): 
        get_cached_data.clear()
        st.session_state.chart_key += 1
        st.rerun()

@st.dialog("➕ Nuova Commessa")
def modal_commessa():
    n = st.text_input("Nome Commessa")
    s = st.selectbox("Stato", options=STATI_COMMESSA, index=1)
    if st.button("Salva", use_container_width=True):
        supabase.table("Commesse").insert({"nome_commessa": n, "stato": s}).execute()
        get_cached_data.clear(); st.rerun()

@st.dialog("📑 Nuovo Task")
def modal_task():
    cms = {c['nome_commessa']: c['id'] for c in get_cached_data("Commesse")}
    n = st.text_input("Nome Task")
    c = st.selectbox("Commessa", options=list(cms.keys()))
    s = st.selectbox("Stato", options=STATI_TASK, index=1)
    if st.button("Crea", use_container_width=True):
        supabase.table("Task").insert({"nome_task": n, "commessa_id": cms[c], "stato": s}).execute()
        get_cached_data.clear(); st.rerun()

@st.dialog("⏱️ Nuovo Log")
def modal_log():
    cm_data, tk_data, ops_list = get_cached_data("Commesse"), get_cached_data("Task"), [o['nome'] for o in get_cached_data("Operatori")]
    
    op_ms = st.multiselect("Operatore", options=ops_list, key="new_log_ops_ms")
    
    cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
    sel_cm_nome = st.selectbox("Commessa", options=list(cms_dict.keys()), key="new_log_cm_sb")
    sel_cm_id = cms_dict[sel_cm_nome]
    
    tasks_filtrati = [t for t in tk_data if t['commessa_id'] == sel_cm_id]
    task_opts = {t['nome_task']: t['id'] for t in tasks_filtrati}
    # Creiamo una mappa inversa per recuperare lo stato attuale se il task esiste
    task_status_map = {t['nome_task']: t.get('stato', STATI_TASK[1]) for t in tasks_filtrati}
    
    task_list = list(task_opts.keys()) + ["➕ Aggiungi nuovo task..."]
    sel_task = st.selectbox("Task", options=task_list, key="new_log_tk_sb")
    
    new_task_name = ""
    default_status_index = 1 # "In Corso" o quello definito in STATI_TASK
    
    if sel_task == "➕ Aggiungi nuovo task...":
        new_task_name = st.text_input("Inserisci nome nuovo task", key="new_log_new_tk_ti")
    else:
        # Se il task esiste, cerchiamo di pre-selezionare il suo stato attuale nella selectbox
        current_status = task_status_map.get(sel_task, STATI_TASK[1])
        if current_status in STATI_TASK:
            default_status_index = STATI_TASK.index(current_status)

    # Il campo stato è ora fuori dall'if: sempre visibile
    new_task_status = st.selectbox("Stato Task", options=STATI_TASK, index=default_status_index)
    
    c1, c2 = st.columns(2)
    oggi = datetime.now().date()
    data_i, data_f = c1.date_input("Inizio", value=oggi), c2.date_input("Fine", value=oggi)
    nota = st.text_area("Note")
    
    if st.button("Registra Log", use_container_width=True, type="primary"):
        if not op_ms: st.error("⚠️ Seleziona operatore!"); return
        
        target_id = None
        
        if sel_task == "➕ Aggiungi nuovo task...":
            if new_task_name.strip():
                # Inserimento nuovo Task con lo stato scelto
                res = supabase.table("Task").insert({
                    "nome_task": new_task_name.strip(), 
                    "commessa_id": sel_cm_id, 
                    "stato": new_task_status.strip()
                }).execute()
                if res.data: target_id = res.data[0]['id']
            else:
                st.error("Nome task mancante"); return
        else:
            # Task esistente: aggiorniamo lo stato sul DB prima di procedere
            target_id = task_opts[sel_task]
            supabase.table("Task").update({"stato": new_task_status.strip()}).eq("id", target_id).execute()
        
        if target_id:
            # Creazione dei log per ogni operatore selezionato
            for op_name in op_ms:
                supabase.table("Log_Tempi").insert({
                    "operatore": op_name, 
                    "task_id": target_id, 
                    "inizio": str(data_i), 
                    "fine": str(data_f), 
                    "note": nota
                }).execute()
            
            get_cached_data.clear()
            st.rerun()
            
@st.dialog("📂 Clona Commessa con Date")
def modal_clona_avanzata():
    cm_data, tk_data, log_data = get_cached_data("Commesse"), get_cached_data("Task"), get_cached_data("Log_Tempi")
    cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
    sel_cm_nome = st.selectbox("Seleziona la Commessa sorgente", list(cms_dict.keys()))
    nuovo_nome = st.text_input("Nome della nuova Commessa", value=f"{sel_cm_nome} (COPIA)")
    copia_log = st.checkbox("Copia anche i log tempi (Pianificazione)", value=False)
    offset = 0
    if copia_log:
        old_cm_id = cms_dict[sel_cm_nome]
        ids_task_vecchi = [t['id'] for t in tk_data if t['commessa_id'] == old_cm_id]
        logs_vecchi = [l for l in log_data if l['task_id'] in ids_task_vecchi]
        if logs_vecchi:
            data_min_originale = pd.to_datetime([l['inizio'] for l in logs_vecchi]).min().date()
            nuova_data_inizio = st.date_input("Nuova data di inizio", value=datetime.now().date())
            offset = (nuova_data_inizio - data_min_originale).days
    
    if st.button("🚀 Avvia Clonazione", type="primary", use_container_width=True):
        old_cm_id = cms_dict[sel_cm_nome]
        res_cm = supabase.table("Commesse").insert({"nome_commessa": nuovo_nome, "stato": "Pianificata"}).execute()
        if res_cm.data:
            new_cm_id = res_cm.data[0]['id']
            old_to_new_tasks = {}
            for t in [t for t in tk_data if t['commessa_id'] == old_cm_id]:
                res_tk = supabase.table("Task").insert({"nome_task": t['nome_task'], "commessa_id": new_cm_id, "stato": t.get('stato', 'Pianificato 🔵')}).execute()
                if res_tk.data: old_to_new_tasks[t['id']] = res_tk.data[0]['id']
            if copia_log and logs_vecchi:
                nuovi_logs = [{"operatore": l['operatore'], "task_id": old_to_new_tasks[l['task_id']], "inizio": (pd.to_datetime(l['inizio']) + pd.Timedelta(days=offset)).strftime('%Y-%m-%d'), "fine": (pd.to_datetime(l['fine']) + pd.Timedelta(days=offset)).strftime('%Y-%m-%d'), "note": l.get('note', "")} for l in logs_vecchi]
                supabase.table("Log_Tempi").insert(nuovi_logs).execute()
            get_cached_data.clear(); st.rerun()

# --- 6. LOGICA MERGE ---
def merge_consecutive_logs(df):
    if df.empty: return df
    df = df.sort_values(['operatore', 'Commessa', 'Task', 'Inizio'])
    merged = []
    for _, group in df.groupby(['operatore', 'Commessa', 'Task']):
        current_row = None
        for _, row in group.iterrows():
            nota_testo = str(row['note']).strip() if pd.notnull(row['note']) else ""
            nota_formattata = f"• <i>{row['Inizio'].strftime('%d/%m')}</i>: {nota_testo}" if nota_testo else ""
            if current_row is None: 
                current_row = row.to_dict()
                current_row['note_html'] = nota_formattata
            else:
                if row['Inizio'] <= (pd.to_datetime(current_row['Fine']) + timedelta(days=1)):
                    current_row['Fine'] = max(pd.to_datetime(current_row['Fine']), pd.to_datetime(row['Fine']))
                    current_row['Durata_ms'] = ((pd.to_datetime(current_row['Fine']) + timedelta(days=1)) - pd.to_datetime(current_row['Inizio'])).total_seconds() * 1000
                    if nota_formattata: current_row['note_html'] = (current_row['note_html'] + "<br>" + nota_formattata).strip("<br>")
                else:
                    merged.append(current_row); current_row = row.to_dict(); current_row['note_html'] = nota_formattata
        if current_row: merged.append(current_row)
    return pd.DataFrame(merged)

def get_it_date_label(dt, delta):
    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    giorni = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    if delta > 40: return f"Sett. {dt.isocalendar()[1]}<br>{mesi[dt.month-1]}"
    return f"{giorni[dt.weekday()]} {dt.day:02d}<br>{mesi[dt.month-1]}<br>Sett. {dt.isocalendar()[1]}"

# --- 7. GANTT FRAGMENT ---
@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, color_map, oggi_dt, x_range, delta_giorni, shapes):
    if df_plot.empty: st.info("Nessun dato trovato."); return
    df_merged = merge_consecutive_logs(df_plot)
    df_tasks_univoci = df_merged[['Commessa', 'Task', 'task_id', 'stato_commessa', 'stato_task']].drop_duplicates()
    fig = go.Figure()

    mappa_emoji = {
    "Quotazione 🟣": "🟣",
    "Pianificata 🔵": "🔵",
    "In corso 🟡": "🟡",
    "Completata 🟢": "🟢",
    "Sospesa 🟠": "🟠",
    "Cancellata 🔴": "🔴"
    }

    mappa_emoji_task = {
    "Pianificato 🔵": "🔵",
    "In corso 🟡": "🟡",
    "Completato 🟢": "🟢",
    "Sospeso 🟠": "🟠",
    }
    
    vista_compressa = st.session_state.vista_compressa

    y_labels_pulsanti = []
    custom_data_full = []
    for _, r in df_tasks_univoci.iterrows():
        e_cm = mappa_emoji.get(r['stato_commessa'], "⚫")
        e_tk = mappa_emoji_task.get(r.get('stato_task'), "⚫")

        c_label_pulsanti = "<br>".join(textwrap.wrap(f"{e_cm} {r['Commessa']}", 15))

        if vista_compressa:
            y_labels_pulsanti.append(c_label_pulsanti)
        else:
            t_label_pulsanti = "<br>".join(textwrap.wrap(f"{e_tk} {r['Task']}", 20))
            y_labels_pulsanti.append([c_label_pulsanti, t_label_pulsanti])
        custom_data_full.append(["LOG_FITTIZIO", r['task_id']])
    
    fig.add_trace(go.Bar(
        base=["2000-01-01"] * len(df_tasks_univoci),
        x=[36500 * 24 * 3600 * 1000] * len(df_tasks_univoci),
        y=y_labels_pulsanti if st.session_state.vista_compressa else list(zip(*y_labels_pulsanti)),
        orientation='h',
        width=0.9,
        offset= -0.45,
        name="LOG", # Nome dell'operatore fittizio
        marker=dict(color="rgba(0,0,0,0.01)"), # Trasparente
        showlegend=False,
        hoverinfo='none',
        customdata=custom_data_full
        ))
            
    for op in df_merged['operatore'].unique():
        df_op = df_merged[df_merged['operatore'] == op]
        y_labels = []
        for _, row in df_op.iterrows():
            e_cm = mappa_emoji.get(row['stato_commessa'], "⚫")
            e_tk = mappa_emoji_task.get(row.get('stato_task'), "⚫")

            c_label = "<br>".join(textwrap.wrap(f"{e_cm} {row['Commessa']}", 15))

            if vista_compressa:
                y_labels.append(c_label)
            else:
                t_label = "<br>".join(textwrap.wrap(f"{e_tk} {row['Task']}", 20))
                y_labels.append([c_label, t_label])

        
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], x=df_op['Durata_ms'], y=y_labels if vista_compressa else list(zip(*y_labels)), orientation='h', name=op,
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12), width=0.4,
            customdata=list(zip(df_op['id'], df_op['operatore'], df_op['Inizio'], df_op['Fine'], df_op['Commessa'], df_op['Task'], df_op['note_html'], df_op['task_id'])),
            hovertemplate="<b>%{customdata[4]} - %{customdata[5]}</b><br>%{customdata[1]}<br>%{customdata[2]|%d/%m/%Y} - %{customdata[3]|%d/%m/%Y}<br>%{customdata[6]}<extra></extra>"
        ))
        
    # --- Gestione Asse X Dinamica ---
    # Definiamo i confini dell'area "cuscinetto" per il PAN
    start_buffer = x_range[0] - timedelta(days=180)
    end_buffer = x_range[1] + timedelta(days=180)
    
    # Scegliamo la frequenza in base alla scala
    if delta_giorni > 60:
        tick_range = pd.date_range(start=start_buffer, end=end_buffer, freq='W-MON')
    elif delta_giorni >20:
       full_range = pd.date_range(start=start_buffer, end=end_buffer, freq='D')
       tick_range = full_range[full_range.weekday.isin([0, 2, 4])]
    else:
        tick_range = pd.date_range(start=start_buffer, end=end_buffer, freq='D')

     # 3. Generiamo i testi solo per i giorni filtrati
    tick_text = [get_it_date_label(d, delta_giorni) for d in tick_range]
    
    all_shapes = []
    curr = x_range[0] - timedelta(days=60)
    while curr <= x_range[1] + timedelta(days=60):
        all_shapes.append(dict(type="line", x0=curr, x1=curr, y0=0, y1=1, yref="paper", line=dict(color="#e0e0e0", width=1), layer="below"))
        if curr.weekday() >= 5:
            all_shapes.append(dict(type="rect", x0=curr, x1=curr+timedelta(days=1), y0=0, y1=1, yref="paper", fillcolor="#f0f0f0", opacity=0.5, line_width=0, layer="below"))
        curr += timedelta(days=1)
        
    vista_compressa = st.session_state.vista_compressa
    
    unique_rows = df_merged['Commessa'].unique() if vista_compressa else df_merged[['Commessa', 'Task']].drop_duplicates()
    n_r = len(unique_rows)

    fig.update_layout(
        clickmode='event+select',
        height=300 + (n_r * 25),
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=0), shapes=all_shapes, barmode= 'group', bargap=0.1, bargroupgap=0, dragmode='pan',
        xaxis=dict(type="date", ticklabelmode="period", side="top", range=x_range, tickvals=tick_range + pd.Timedelta(hours=12), ticktext=tick_text),
        yaxis=dict(autorange="reversed", showgrid=True, showdividers=True, fixedrange=True,tickson="boundaries"),
        legend=dict(orientation="h", y=1.14, x=0.5, xanchor="center")
    )
    fig.add_vline(x=oggi_dt.timestamp() * 1000 + 43200000, line_width=2, line_color="red")
    
    selected = st.plotly_chart(fig, use_container_width=True, key="gantt_interattivo", on_select="rerun", config={'displayModeBar': False})

    if selected and "selection" in selected and "points" in selected["selection"]:
        p = selected["selection"]["points"]
        try:
            if "x" in p:
                data_punto = pd.to_datetime(punto["x"]).date()
            elif "base" in punto:
                data_punto = pd.to_datetime(punto["base"]).date()
            else:
                data_punto = oggi_dt
        except Exception:
            data_punto = oggi_dt
        
        if p and "customdata" in p[0]:
            d = p[0]["customdata"]
            if d[0] == "LOG_FITTIZIO":
                modal_gestione_clic(task_id=d[1], data_clic=pd.to_datetime(p[0]["x"]).date())
            else:
                modal_edit_log(d[0], d[1], d[2], d[3], d[7], d[6])

# --- 8. MAIN UI ---
l, tk, cm, ops_list = get_cached_data("Log_Tempi"), get_cached_data("Task"), get_cached_data("Commesse"), get_cached_data("Operatori")
df = pd.DataFrame()
if l and tk and cm:
    tk_m = {t['id']: {'n': t['nome_task'], 'c': t['commessa_id'], 's': t.get('stato', 'Pianificato 🔵')} for t in tk}
    cm_m = {c['id']: {'n': c['nome_commessa'], 's': c.get('stato', 'In corso 🟡')} for c in cm}
    df = pd.DataFrame(l)
    df['Inizio'], df['Fine'] = pd.to_datetime(df['inizio']).dt.normalize(), pd.to_datetime(df['fine']).dt.normalize()
    df['Commessa'] = df['task_id'].apply(lambda x: cm_m.get(tk_m.get(x, {}).get('c'), {}).get('n', "N/A"))
    df['Task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('n', "N/A"))
    df['stato_commessa'] = df['task_id'].apply(lambda x: cm_m.get(tk_m.get(x, {}).get('c'), {}).get('s', "In corso 🟡"))
    df['stato_task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('s', "Pianificato 🔵"))
    df['Durata_ms'] = ((df['Fine'] + pd.Timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000

    # --- AREA CONTROLLI (FIXED HEADER) ---
    with st.container():
        st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
        # Riga 1: Progetti, Operatori, Scala
        c1, c2, c3 = st.columns([3, 3, 4])
        f_c = c1.multiselect("Progetti", sorted(df['Commessa'].unique()), label_visibility="collapsed", placeholder="Progetti")
        f_o = c2.multiselect("Operatori", sorted(df['operatore'].unique()), label_visibility="collapsed", placeholder="Operatori")
        with c3:
            cs, cd = st.columns(2)
            scala = cs.selectbox("Scala", ["Settimana","2 Settimane", "Mese", "Trimestre", "Semestre", "Personalizzato"], index=1, label_visibility="collapsed")
            f_custom = cd.date_input("Periodo", value=[datetime.now(), datetime.now() + timedelta(days=7)], label_visibility="collapsed") if scala == "Personalizzato" else None
        
        # Riga 2: Stati
        s1, s2, s3 = st.columns([3, 3, 4])
        f_s_cm = s1.multiselect("Stato Commesse", options=STATI_COMMESSA, default=[], label_visibility="collapsed", placeholder="Stato Commesse")
        f_s_tk = s2.multiselect("Stato Task", options=STATI_TASK, default=[], label_visibility="collapsed", placeholder="Stato Task")

        with s3:
            # Filtro intervallo date (Date Range)
            min_d = pd.to_datetime(df['inizio']).min().date()
            max_d = pd.to_datetime(df['fine']).max().date()
            # Default: oggi -> +30 giorni (o quello che preferisci)
            f_range = st.date_input(
                "Intervallo Date",
                value=[df['inizio'].min(), df['fine'].max()], # Range preimpostato sui dati esistenti
                format="DD/MM/YYYY",
                label_visibility="collapsed",
                key="filter_date_range"
            )
            
        # Riga 3: Pulsanti
        st.markdown('<div class="spacer-btns"></div>', unsafe_allow_html=True)
        b1, b2, b3, b4, b5, b6 = st.columns(6)
        if b1.button("➕ Commessa", use_container_width=True): modal_commessa()
        if b2.button("📑 Task", use_container_width=True): modal_task()
        if b3.button("⏱️ Log", use_container_width=True): modal_log()
        if b4.button("📍 Oggi", use_container_width=True): st.session_state.chart_key += 1; st.rerun()
        label_view = "↔️ Espandi" if st.session_state.vista_compressa else "↕️ Comprimi"
        if b5.button(label_view, use_container_width=True):
            st.session_state.vista_compressa = not st.session_state.vista_compressa
            st.rerun()
        if b6.button("🖨️ Stampa PDF", use_container_width=True):st.markdown('<script>window.print();</script>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- FILTRAGGIO DATI ---
    df_p = df.copy()
    if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
    if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]
    if f_s_cm: df_p = df_p[df_p['stato_commessa'].isin(f_s_cm)]
    if f_s_tk: df_p = df_p[df_p['stato_task'].isin(f_s_tk)]
    
# Filtro temporale (FIXATO)
if isinstance(f_range, (list, tuple)) and len(f_range) == 2:
    # Convertiamo i limiti del filtro in datetime
    start_search = pd.to_datetime(f_range[0])
    end_search = pd.to_datetime(f_range[1])
    
    # Assicuriamoci che le colonne inizio/fine siano datetime
    df_p['inizio'] = pd.to_datetime(df_p['inizio'])
    df_p['fine'] = pd.to_datetime(df_p['fine'])
    
    # Applichiamo il filtro di intersezione
    df_p = df_p[
        (df_p['inizio'] <= end_search) & 
        (df_p['fine'] >= start_search)
    ].copy()
    
tabs = st.tabs(["📊 Timeline", "📅 Calendario", "📋 Logs", "⚙️ Gestione", "📈 Statistiche"])    

with tabs[0]: # TIMELINE
    if not df.empty:
        oggi_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if scala == "Personalizzato" and f_custom and len(f_custom) == 2: x_range = [pd.to_datetime(f_custom[0]), pd.to_datetime(f_custom[1])]
        else:
            d = {"Settimana": 4, "2 Settimane": 8, "Mese": 15, "Trimestre": 45, "Semestre": 90}.get(scala, 15)
            x_range = [oggi_dt - timedelta(days=d), oggi_dt + timedelta(days=d)]
        render_gantt_fragment(df_p, {o['nome']: o.get('colore', '#8dbad2') for o in ops_list}, oggi_dt, x_range, (x_range[1]-x_range[0]).days, [])

with tabs[1]: # CALENDARIO
    if not df.empty:
               
        # 1. Preparazione Eventi (Formato ISO rigoroso)
        cal_events = []
        color_map = {o['nome']: o.get('colore', '#3D85C6') for o in ops_list}
        
        for _, row in df_p.iterrows():
            try:
                # Trasformiamo in stringa pura YYYY-MM-DD
                s_date = row["Inizio"].strftime("%Y-%m-%d")
                # FullCalendar vuole la fine esclusiva (+1 giorno)
                e_date = (row["Fine"] + timedelta(days=1)).strftime("%Y-%m-%d")
                
                cal_events.append({
                    "id": str(row["id"]),
                    "title": f"{row['operatore']} | {row['Task']}",
                    "start": s_date,
                    "end": e_date,
                    "color": color_map.get(row["operatore"], "#3D85C6"),
                    "allDay": True,
                    "extendedProps": {"nota": row.get('note', '')}
                })
            except:
                continue

        # 2. Opzioni con ALTEZZA FISSA (Indispensabile per la visibilità)
        cal_options = {
            "initialView": "multiMonthYear", "multiMonthMaxColumns": 2,"multiMonthMinWidth": 500, "views": {
                "multiMonthYear": {
                    "duration": {"months": 2} # LIMITA LA VISTA A SOLI 2 MESI
                }
            },
            "height": "auto",
            "contentHeight": "auto",
            "aspectRatio": 1.3,
            "expandRows": False,
            "locale": "it",
            "firstDay": 1,           # Inizia da Lunedì
            "weekNumbers": True,
            "weekText": "Sett.",
            "headerToolbar": {
                "left": "prev,next today",
                "center": "title",
                "right": "multiMonthYear,dayGridMonth,timeGridWeek"
            },
            "editable": False,
            "selectable": True,
        }
        
        # 3. Custom CSS per forzare la visibilità del componente
        st.markdown("""
            <style>
                /* 1. Riduce lo spazio tra i mesi */
                .fc .fc-multimonth-month {padding: 0px !important; margin-bottom: 2px !important;}
                /* 2. Riduce l'altezza minima della cella del giorno */
                .fc .fc-daygrid-day-frame {min-height: 35px !important; max-height: 120px !important;}
                /* 3. Riduce lo spazio sopra il numero del giorno */
                .fc .fc-daygrid-day-top {flex-direction: row !important; font-size: 0.85em !important;}
                /* 4. Comprime gli eventi all'interno delle celle */
                .fc-daygrid-event {margin-top: 0px !important; margin-bottom: 1px !important; padding: 0px 2px !important; font-size: 0.8em !important;}
                /* 5. Rimuove padding in eccesso dal contenitore del mese */
                .fc-multimonth-daygrid {--fc-daygrid-event-h-height: 18px;}
                /* 6. Forza l'altezza dell'iframe di Streamlit per evitare scroll interni */
                iframe[title="streamlit_calendar.calendar"] {width: 100% !important; min-height: 1500px !important; height: 1500px !important;}
            </style>
        """, unsafe_allow_html=True)

        # 4. Rendering con gestione dei dati di ritorno
        try:
            state = calendar(
                events=cal_events,
                options=cal_options,
                key="v_calendar_final" # Cambia la chiave se avevi errori prima
            )
            
            # Gestione click (stessa logica della tua modale)
            if state and "eventClick" in state:
                eid = int(state["eventClick"]["event"]["id"])
                sel = df[df['id'] == eid].iloc[0]
                modal_edit_log(sel['id'], sel['operatore'], sel['Inizio'], sel['Fine'])
                
        except Exception as e:
            st.error(f"Errore nel caricamento del componente: {e}")
    else:
        st.info("Nessun dato presente. Registra un log per vedere il calendario.")


with tabs[2]: # DATI
    st.header("📋 Gestione Log Esistenti")
    if not df_p.empty:
        df_edit = df_p[['id', 'Commessa', 'Task', 'operatore', 'Inizio', 'Fine', 'note']].copy()
        df_edit['Inizio'] = pd.to_datetime(df_edit['Inizio']).dt.date
        df_edit['Fine'] = pd.to_datetime(df_edit['Fine']).dt.date
        edited_log = st.data_editor(df_edit, column_config={"id": None}, use_container_width=True, hide_index=True)
        if st.button("Salva Modifiche Tabella"):
            for _, r in edited_log.iterrows():
                supabase.table("Log_Tempi").update({"operatore": r['operatore'], "inizio": str(r['Inizio']), "fine": str(r['Fine']), "note": r['note']}).eq("id", r['id']).execute()
            get_cached_data.clear(); st.rerun()

with tabs[3]: # SETUP
    st.header("⚙️ Setup di Sistema")
    s1, s2, s3 = st.tabs(["🏗️ Commesse", "👥 Operatori", "✅ Task"])
    
    with s1:
        df_cm_setup = pd.DataFrame(cm)
        if not df_cm_setup.empty:
            # Pulizia preventiva: assicurati che lo stato sia una stringa valida
            df_cm_setup['stato'] = df_cm_setup['stato'].fillna("Pianificata").astype(str)
            
            ed_cm = st.data_editor(
                df_cm_setup, 
                column_config={
                    "id": None, 
                    "stato": st.column_config.SelectboxColumn("Stato", options=STATI_COMMESSA)
                }, 
                use_container_width=True, 
                num_rows="dynamic",
                key="setup_cm_editor_v4"
            )
            
            if st.button("Aggiorna Commesse", key="btn_cm_v4"): 
                aggiorna_database_setup("Commesse", ed_cm, cm)
            if st.button("Clona Commessa"): modal_clona_avanzata()

    with s2:
        st.subheader("Gestione Operatori")
        raw_op = get_cached_data("Operatori")
        if raw_op:
            df_op_setup = pd.DataFrame(raw_op)
            
            # Configurazione colonne definita separatamente per chiarezza
            config_colonne = {
                "id": None,
                "nome": st.column_config.TextColumn("Nome Operatore", required=True),
                "colore": st.column_config.TextColumn("Colore (HEX)")
            }
            
            ed_op = st.data_editor(
                df_op_setup,
                column_config=config_colonne,
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
                key="setup_operatori_vfinal"
            )

            st.write("🎨 **Aiuto Colori**")
            col_helper = st.color_picker("Scegli un colore e copia il codice HEX nella tabella sopra", "#8dbad2")
            st.code(col_helper) # Mostra il codice da copiare e incollare nella cella
            
            if st.button("Salva Operatori"):
                # La funzione aggiorna_database_setup gestirà i codici HEX (es. #FF0000)
                aggiorna_database_setup("Operatori", ed_op, raw_op)

with s3:
        st.subheader("Gestione Task")
        raw_tk = get_cached_data("Task")
        if raw_tk:
            # 1. Creiamo il DataFrame e le mappe di conversione
            df_tk_setup = pd.DataFrame(raw_tk)
            cm_data = get_cached_data("Commesse")
            
            # Mappa ID -> Nome e Nome -> ID
            id_to_name = {c['id']: str(c['nome_commessa']) for c in cm_data}
            name_to_id = {str(c['nome_commessa']): c['id'] for c in cm_data}
            lista_nomi_commesse = sorted(list(name_to_id.keys()))

            # 2. TRASFORMAZIONE: Usiamo i NOMI nell'editor, non gli ID
            # Creiamo una colonna temporanea 'Commessa' basata sui nomi
            df_tk_setup['commessa_nome'] = df_tk_setup['commessa_id'].map(id_to_name).fillna(lista_nomi_commesse[0] if lista_nomi_commesse else "")
            df_tk_setup['stato'] = df_tk_setup['stato'].fillna(STATI_TASK[0])

            # 3. DATA EDITOR (Mostriamo il nome della commessa come stringa)
            ed_tk = st.data_editor(
                df_tk_setup,
                column_config={
                    "id": None, 
                    "commessa_id": None, # Nascondiamo l'ID numerico che crasha
                    "commessa_nome": st.column_config.SelectboxColumn(
                        "Commessa",
                        options=lista_nomi_commesse,
                        help="Seleziona la commessa dal menu"
                    ),
                    "stato": st.column_config.SelectboxColumn("Stato", options=STATI_TASK)
                },
                use_container_width=True,
                num_rows="dynamic",
                hide_index=True,
                key="editor_tk_string_v6"
            )
            
            if st.button("Aggiorna Task", key="btn_save_tk_v6"):
                # 4. RICONVERSIONE: Prima di salvare, riportiamo i nomi in ID
                df_da_salvare = ed_tk.copy()
                df_da_salvare['commessa_id'] = df_da_salvare['commessa_nome'].map(name_to_id)
                
                # Rimuoviamo la colonna temporanea dei nomi prima di inviare a Supabase
                df_da_salvare = df_da_salvare.drop(columns=['commessa_nome'])
                
                aggiorna_database_setup("Task", df_da_salvare, raw_tk)

with tabs[4]: # STATS
    if not df_p.empty:
        c1, c2 = st.columns(2)
        c1.bar_chart(df_p.groupby('Commessa').size())
        c2.bar_chart(df_p.groupby('operatore').size())
        st.metric("Totale Log", len(df_p))
