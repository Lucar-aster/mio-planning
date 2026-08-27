import streamlit as st
import os
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
import pytz
from datetime import datetime, timedelta, time, timezone
from zoneinfo import ZoneInfo
import textwrap
import hashlib
from streamlit_calendar import calendar
import plotly.express as px
import io

# --- 1. CONFIGURAZIONE PAGINA E COSTANTI ---
LOGO_URL = "https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png"
st.set_page_config(page_title="Aster Contract", page_icon=LOGO_URL, layout="wide")

STATI_COMMESSA = ["Quotazione 🟣", "Pianificata 🔵", "In corso 🟡", "Completata 🟢", "Sospesa 🟠", "Cancellata 🔴"]
STATI_TASK = ["Pianificato 🔵", "In corso 🟡", "In attesa ⚪", "Completato 🟢", "Sospeso 🟠"]
tz = ZoneInfo("Europe/Rome")

# --- 3. CONNESSIONE E CACHING ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

@st.cache_data
def get_cached_data(table):
    try: return supabase.table(table).select("*").execute().data
    except: return []

if 'chart_key' not in st.session_state: st.session_state.chart_key = 0
if 'vista_compressa' not in st.session_state: st.session_state.vista_compressa = False

# --- 2. CSS ---
st.markdown(f"""
    <head>
        <link rel="icon" href="{LOGO_URL}" type="image/png">
        <link rel="shortcut icon" href="{LOGO_URL}" type="image/png">
        <link rel="apple-touch-icon" href="{LOGO_URL}">
    </head>
""", unsafe_allow_html=True)

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f: st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        st.error(f"⚠️ Attenzione: il file {file_name} non è stato trovato!")
    
local_css("style.css")

header_col1, header_col2 = st.columns([1, 4])

with header_col1:
    st.markdown(f"""
        <div class="compact-title" style="margin-top: 5px;">
            <img src="{LOGO_URL}" width="30">
            <h1 style="font-size: 18px !important; margin-left: 5px;">Progetti Aster</h1>
        </div>
    """, unsafe_allow_html=True)
    ops = get_cached_data("Operatori")
    op_def = st.selectbox("Operatore Attivo", [o['nome'] for o in ops], label_visibility="collapsed")

with header_col2:
    tags = get_cached_data("Tag")
    op_html = "".join([f'<div class="legend-pill" style="background-color:{o.get("colore", "#8dbad2")}">{o["nome"]}</div>' for o in ops])
    cm_html = "".join([f'<div class="legend-pill">{s}</div>' for s in STATI_COMMESSA])
    tk_html = "".join([f'<div class="legend-pill">{s}</div>' for s in STATI_TASK])
    tag_html = "".join([f'<div class="legend-pill" style="background-color:{t.get("colore", "#8dbad2")}">{t["nome"]}</div>' for t in tags])
    
    st.markdown(f"""
        <div class="legend-container">
            <div class="legend-row"><span class="legend-label">👤 Operatori</span>{op_html}</div>
            <div class="legend-row"><span class="legend-label">🏗️ Commesse</span>{cm_html}</div>
            <div class="legend-row"><span class="legend-label">📋 Task</span>{tk_html}</div>
            <div class="legend-row"><span class="legend-label">🔖 Tag</span>{tag_html}</div>
        </div>
    """, unsafe_allow_html=True)
    
# --- 4. FUNZIONI DI AGGIORNAMENTO DB (SETUP) ---
def aggiorna_database_setup(nome_tabella, edited_df, original_df):
    try:
        ids_originali = set(pd.DataFrame(original_df)['id'].dropna()) if original_df else set()
        ids_attuali = set(edited_df['id'].dropna())
        
        for idx in (ids_originali - ids_attuali): supabase.table(nome_tabella).delete().eq("id", idx).execute()

        for _, row in edited_df.iterrows():
            row_dict = row.dropna().to_dict()
            for key, val in row_dict.items():
                if isinstance(val, time): row_dict[key] = str(val)
                elif isinstance(val, datetime): row_dict[key] = str(val.date())
                
            curr_id = row_dict.pop('id', None)
            if curr_id is None or pd.isna(curr_id):
                supabase.table(nome_tabella).insert(row_dict).execute()
            else:
                supabase.table(nome_tabella).update(row_dict).eq("id", curr_id).execute()
        st.success(f"Dati {nome_tabella} aggiornati!")
        get_cached_data.clear(); st.rerun()
    except Exception as e: st.error(f"Errore: {e}")

# --- 5. MODALI ---
@st.dialog("Gestione Task & Log", width="large")
def modal_gestione_clic(task_id, data_clic):
    cm_data, tk_data = get_cached_data("Commesse"), get_cached_data("Task")
    task_info = next((t for t in tk_data if t['id'] == task_id), None)
    if not task_info: st.error("Task non trovato."); return
    
    commessa_info = next((c for c in cm_data if c['id'] == task_info['commessa_id']), None)
    tags_data = get_cached_data("Tag")
    lista_tag = sorted([t['nome'] for t in tags_data])
    mappa_tags = {t['nome']: t['id'] for t in tags_data}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.expander("🏗️ Modifica Anagrafica", expanded=True):
            new_tk_name = st.text_input("Nome Task", value=task_info.get('nome_task', ''))
            new_tk_status = st.selectbox("Stato Task", options=STATI_TASK, index=STATI_TASK.index(task_info.get('stato', STATI_TASK[0])))
            if commessa_info:
                new_cm_name = st.text_input("Nome Commessa", value=commessa_info.get('nome_commessa', ''))
                new_cm_status = st.selectbox("Stato Commessa", options=STATI_COMMESSA, index=STATI_COMMESSA.index(commessa_info.get('stato', STATI_COMMESSA[0])))
            if st.button("Salva Modifiche", width='stretch'):
                supabase.table("Task").update({"nome_task": new_tk_name, "stato": new_tk_status}).eq("id", task_id).execute()
                if commessa_info: supabase.table("Commesse").update({"nome_commessa": new_cm_name, "stato": new_cm_status}).eq("id", commessa_info['id']).execute()
                get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
    with col2:
        with st.expander("📑 Nuovo Task con Log", expanded=True):
            cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
            lista_scelte_cm = list(cms_dict.keys()) + ["➕ Nuova Commessa..."]
            idx_default = lista_scelte_cm.index(commessa_info['nome_commessa']) if commessa_info and commessa_info['nome_commessa'] in cms_dict else 0
            
            sel_cm = st.selectbox("Commessa di destinazione", options=lista_scelte_cm, index=idx_default)
            nome_nuova_cm = st.text_input("Nome della Nuova Commessa") if sel_cm == "➕ Nuova Commessa..." else ""
            nome_nuovo_tk = st.text_input("Nome del Nuovo Task")
            new_tk_status_1 = st.selectbox("Stato Task", options=STATI_TASK, index=STATI_TASK.index(task_info.get('stato', STATI_TASK[0])), key="newtkstat")
            
            op_sel_t = st.multiselect("Seleziona Operatore", [o['nome'] for o in ops], default=op_def)
            id_tag_scelto_t = mappa_tags.get(st.selectbox("Seleziona Tag", options=lista_tag, index=None, key="tag_sclt_t"))
            date_range_t = st.date_input("Periodo Log", value=(data_clic, data_clic), format="DD/MM/YYYY")
        
            ot1, ot2 = st.columns(2) 
            ora_i_t = datetime.now(tz).time() if ot1.checkbox("Usa ora attuale", value=True, key="ao_i_t") else ot1.time_input("Ora Inizio", value=time(8, 0), key="o_i_t")
            if ot1.checkbox("Usa ora attuale", value=True, key="ao_i_t_msg"): st.info(f"Registrato orario d'inizio: {ora_i_t.strftime('%H:%M')}")
            
            ora_f_t = None if ot2.checkbox("Log aperto", value=True, key="ao_f_t") else ot2.time_input("Ora Fine", value=time(17, 0), key="o_f_t")
                
            nota_t = st.text_input("Nota log")  
            c1, c2 = st.columns(2)
            if c1.button("Registra Task", type="primary", width='stretch'):
                if not op_sel_t or len(date_range_t) < 2: st.warning("Seleziona operatore e range date valido.")
                else:
                    curr_cm_id = cms_dict.get(sel_cm)
                    if sel_cm == "➕ Nuova Commessa...":
                        if not nome_nuova_cm: st.error("Inserisci nome commessa"); return
                        curr_cm_id = supabase.table("Commesse").insert({"nome_commessa": nome_nuova_cm, "stato": STATI_COMMESSA[2]}).execute().data[0]['id']
                    if not nome_nuovo_tk: st.error("Inserisci nome task"); return
                    
                    final_task_id = supabase.table("Task").insert({"nome_task": nome_nuovo_tk, "commessa_id": curr_cm_id, "stato": new_tk_status_1}).execute().data[0]['id']
                    
                    nuovi_log_t = [{"task_id": final_task_id, "operatore": op, "inizio": str(date_range_t[0]), "fine": str(date_range_t[1]), "ora_i": ora_i_t.strftime('%H:%M:%S'), "ora_f": ora_f_t.strftime('%H:%M:%S') if ora_f_t else None, "note": nota_t, "tag": id_tag_scelto_t} for op in op_sel_t]
                    supabase.table("Log_Tempi").insert(nuovi_log_t).execute()
                    get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
        
            if c2.button("Annulla", width='stretch', key="annulla_t"): st.session_state.chart_key += 1; st.rerun()
    with col3:    
        with st.expander(f"⏱️ Nuovo Log - {data_clic.strftime('%d/%m/%Y')}", expanded=True):
            st.info(f"📋 **Commessa:** {commessa_info.get('nome_commessa', 'Non specificata') if commessa_info else 'Non specificata'}  \n **Task:** {task_info.get('nome_task', 'Senza nome')}")
            date_range_l = st.date_input("Periodo Log", value=(data_clic, data_clic), format="DD/MM/YYYY", key="date_range_l")

            ol1, ol2 = st.columns(2) 
            ora_i_l = datetime.now(tz).time() if ol1.checkbox("Usa ora attuale", value=True, key="ao_i_l") else ol1.time_input("Ora Inizio", value=time(8, 0), key="o_i_t_l")
            if ol1.checkbox("Usa ora attuale", value=True, key="ao_i_l_msg"): st.info(f"Registrato orario d'inizio: {ora_i_l.strftime('%H:%M')}")
            
            ora_f_l = None if ol2.checkbox("Log aperto", value=True, key="ao_f_l") else ol2.time_input("Ora Fine", value=time(17, 0), key="o_f_l")
        
            op_sel_l = st.multiselect("Seleziona Operatore", [o['nome'] for o in ops], default=op_def, key="op_sel_l")
            id_tag_scelto_l = mappa_tags.get(st.selectbox("Seleziona Tag", options=lista_tag, index=None, key="tag_scelti_l"))
            new_tk_status_2 = st.selectbox("Stato Task", options=STATI_TASK, index=STATI_TASK.index(task_info.get('stato', STATI_TASK[0])), key="newtkstat2")
            nota_l = st.text_input("Nota log", key="nota_l")
            
            c1, c2 = st.columns(2)
            if c1.button("Registra Log", type="primary", width='stretch', key="regista_l"):
                supabase.table("Task").update({"stato": new_tk_status_2}).eq("id", task_id).execute()
                if not op_sel_l or len(date_range_l) < 2: st.warning("Seleziona operatore e range date.")
                else:
                    nuovi_log_l = [{"task_id": task_id, "operatore": op, "inizio": str(date_range_l[0]), "fine": str(date_range_l[1]), "ora_i": ora_i_l.strftime('%H:%M:%S'), "ora_f": ora_f_l.strftime('%H:%M:%S') if ora_f_l else None, "note": nota_l, "tag": id_tag_scelto_l} for op in op_sel_l]
                    supabase.table("Log_Tempi").insert(nuovi_log_l).execute()
                    get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
        
            if c2.button("Annulla", width='stretch', key="annulla_l"): st.session_state.chart_key += 1; st.rerun()
        
@st.dialog("📝 Gestione Dettaglio Log", width="large")
def modal_edit_log(log_id, current_op, current_start, current_end, current_task_id, current_note=""):
    st.markdown("""<style>div[data-testid="stDialog"] div[role="dialog"] { width: 90vw !important; max-width: 1300px !important; }</style>""", unsafe_allow_html=True)
    
    cm_data, tk_data, tags_data = get_cached_data("Commesse"), get_cached_data("Task"), get_cached_data("Tag")
    ops_list, tag_list = sorted([o['nome'] for o in get_cached_data("Operatori")]), sorted([t['nome'] for t in tags_data])
    cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
    cms_id_to_nome = {c['id']: c['nome_commessa'] for c in cm_data}
    mappa_tags = {t['nome']: t['id'] for t in tags_data}
    id_to_tag_nome = {t['id']: t['nome'] for t in tags_data}
    
    current_task_info = next((t for t in tk_data if t['id'] == current_task_id), None)
    if not current_task_info: st.error("Dati task non trovati."); return
    
    curr_cm_nome = cms_id_to_nome.get(current_task_info['commessa_id'], list(cms_dict.keys())[0])

    st.info("💡 Modifica i dettagli qui sotto. Se cambi 'Commessa/Task' sopra, sposterai TUTTI i log visualizzati.")
    col_c, col_t, col_s = st.columns(3)
    
    with col_c:
        sel_cm_nome = st.selectbox("Sposta in Commessa:", options=list(cms_dict.keys()), index=list(cms_dict.keys()).index(curr_cm_nome), key="ed_cm")
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
    
    all_logs = supabase.table("Log_Tempi").select("*").eq("operatore", current_op).eq("task_id", current_task_id).execute().data
    df_sub = pd.DataFrame(all_logs)
    
    if not df_sub.empty:
        df_sub = df_sub[["operatore", "tag", "note", "inizio", "fine", "ora_i", "ora_f", "id", "task_id"]]
        if 'tag' in df_sub.columns: df_sub['tag'] = df_sub['tag'].map(id_to_tag_nome)
        
        df_sub['inizio'] = pd.to_datetime(df_sub['inizio']).dt.date
        df_sub['fine'] = pd.to_datetime(df_sub['fine']).dt.date
        df_sub['ora_i'] = pd.to_datetime(df_sub.get('ora_i'), format='%H:%M:%S', errors='coerce').dt.time
        
        df_sub['era_aperto'] = df_sub['ora_f'].isna() | (df_sub['ora_f'] == "")
        df_sub['ora_f'] = pd.to_datetime(df_sub.get('ora_f'), format='%H:%M:%S', errors='coerce').dt.time.fillna(time(0, 0))
        
        mask = (df_sub['inizio'] >= pd.to_datetime(current_start).date()) & (df_sub['inizio'] <= pd.to_datetime(current_end).date())
        df_sub = df_sub[mask].copy()
        df_sub["Sposta"], df_sub["Elimina"] = False, False

    if df_sub.empty: st.warning("Nessun log trovato."); return

    edited_df = st.data_editor(
        df_sub,
        column_config={
            "id": None, "task_id": None,"era_aperto": None,
            "operatore": st.column_config.SelectboxColumn("Operatore", options=ops_list, width="medium", required=True),
            "tag": st.column_config.SelectboxColumn("Tag", options=tag_list, width="medium"), 
            "note": st.column_config.TextColumn("Note", width="large"),
            "inizio": st.column_config.DateColumn("Inizio", format="DD/MM/YYYY"),
            "fine": st.column_config.DateColumn("Fine", format="DD/MM/YYYY"),
            "ora_i": st.column_config.TimeColumn("Ora Inizio", format="HH:mm"),
            "ora_f": st.column_config.TimeColumn("Ora Fine", format="HH:mm"),
            "Sposta": st.column_config.CheckboxColumn("Sposta ➡️", default=False),
            "Elimina": st.column_config.CheckboxColumn("Elimina", default=False)
        },
        disabled=["id", "task_id"], width='stretch', hide_index=True, key="editor_v10"
    )
    
    c1, c2 = st.columns(2)
    if c1.button("Salva Tutto", type="primary", width='stretch'):
        supabase.table("Task").update({"stato": nuovo_stato_task}).eq("id", id_task_target).execute()
        for _, row in edited_df.iterrows():
            if row["Elimina"]: supabase.table("Log_Tempi").delete().eq("id", row["id"]).execute()
            else:
                ora_f_val = None
                if pd.notna(row["ora_f"]) and not (row["era_aperto"] and row["ora_f"] == time(0, 0)):
                    ora_f_val = row["ora_f"].strftime("%H:%M:%S") if hasattr(row["ora_f"], "strftime") else str(row["ora_f"])
                
                supabase.table("Log_Tempi").update({
                    "task_id": id_task_target if row["Sposta"] else row["task_id"], 
                    "operatore": row["operatore"], "tag": mappa_tags.get(row["tag"]),
                    "inizio": str(row["inizio"]) if pd.notna(row["inizio"]) else None, 
                    "fine": str(row["fine"]) if pd.notna(row["fine"]) else None,
                    "ora_i": str(row["ora_i"]) if pd.notna(row["ora_i"]) else None, 
                    "ora_f": ora_f_val,
                    "note": str(row["note"]) if pd.notna(row["note"]) and row["note"] else ""
                }).eq("id", row["id"]).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
    if c2.button("Annulla", width='stretch'): st.session_state.chart_key += 1; st.rerun()

@st.dialog("➕ Nuova Commessa")
def modal_commessa():
    n = st.text_input("Nome Commessa")
    s = st.selectbox("Stato", options=STATI_COMMESSA, index=1)
    if st.button("Salva", width='stretch'):
        supabase.table("Commesse").insert({"nome_commessa": n, "stato": s}).execute()
        get_cached_data.clear(); st.rerun()

@st.dialog("⏱️ Nuovo Log")
def modal_log():
    cm_data, tk_data, tags_data = get_cached_data("Commesse"), get_cached_data("Task"), get_cached_data("Tag")
    ops_list, lista_tag = [o['nome'] for o in ops], sorted([t['nome'] for t in tags_data])
    mappa_tags = {t['nome']: t['id'] for t in tags_data}
    cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
    
    op_ms = st.multiselect("Operatore", options=ops_list, default=op_def, key="new_log_ops_ms")
    sel_cm_id = cms_dict[st.selectbox("Commessa", options=list(cms_dict.keys()), key="new_log_cm_sb")]
    
    tasks_filtrati = [t for t in tk_data if t['commessa_id'] == sel_cm_id]
    task_opts = {t['nome_task']: t['id'] for t in tasks_filtrati}
    task_status_map = {t['nome_task']: t.get('stato', STATI_TASK[1]) for t in tasks_filtrati}
    
    sel_task = st.selectbox("Task", options=list(task_opts.keys()) + ["➕ Aggiungi nuovo task..."], key="new_log_tk_sb")
    new_task_name = st.text_input("Inserisci nome nuovo task", key="new_log_new_tk_ti") if sel_task == "➕ Aggiungi nuovo task..." else ""
    
    default_status_index = 1 if sel_task == "➕ Aggiungi nuovo task..." else (STATI_TASK.index(task_status_map.get(sel_task)) if task_status_map.get(sel_task) in STATI_TASK else 1)
    new_task_status = st.selectbox("Stato Task", options=STATI_TASK, index=default_status_index)

    id_tag_scelto_lg = mappa_tags.get(st.selectbox("Seleziona Tag", options=lista_tag, index=None, key="tag_scelti_lg"))
    
    c1, c2 = st.columns(2)
    oggi = datetime.now().date()
    data_i, data_f = c1.date_input("Inizio", value=oggi), c2.date_input("Fine", value=oggi)

    olg1, olg2 = st.columns(2) 
    ora_i = datetime.now(tz).time() if olg1.checkbox("Usa ora attuale", value=True, key="ao_i_lg") else olg1.time_input("Ora Inizio", value=time(8, 0), key="o_i_tg")
    if olg1.checkbox("Usa ora attuale", value=True, key="ao_i_lg_msg"): st.info(f"Registrato orario d'inizio: {ora_i.strftime('%H:%M')}")
    
    ora_f = None if olg2.checkbox("Log aperto", value=True, key="ao_f_lg") else olg2.time_input("Ora Fine", value=time(17, 0), key="o_f_lg")
    
    nota = st.text_area("Note")
    
    if st.button("Registra Log", width='stretch', type="primary"):
        if not op_ms: st.error("⚠️ Seleziona operatore!"); return
        target_id = None
        if sel_task == "➕ Aggiungi nuovo task...":
            if new_task_name.strip():
                res = supabase.table("Task").insert({"nome_task": new_task_name.strip(), "commessa_id": sel_cm_id, "stato": new_task_status.strip()}).execute()
                if res.data: target_id = res.data[0]['id']
            else: st.error("Nome task mancante"); return
        else:
            target_id = task_opts[sel_task]
            supabase.table("Task").update({"stato": new_task_status.strip()}).eq("id", target_id).execute()
        
        if target_id:
            for op_name in op_ms:
                supabase.table("Log_Tempi").insert({
                    "operatore": op_name, "task_id": target_id, 
                    "inizio": str(data_i), "fine": str(data_f),
                    "ora_i": ora_i.strftime('%H:%M:%S'), "ora_f": str(ora_f) if ora_f else None, "note": nota, "tag": id_tag_scelto_lg
                }).execute()
            get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
            
@st.dialog("📂 Clona Commessa con Date")
def modal_clona_avanzata():
    cm_data, tk_data, log_data = get_cached_data("Commesse"), get_cached_data("Task"), get_cached_data("Log_Tempi")
    cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
    sel_cm_nome = st.selectbox("Seleziona la Commessa sorgente", list(cms_dict.keys()))
    nuovo_nome = st.text_input("Nome della nuova Commessa", value=f"{sel_cm_nome} (COPIA)")
    copia_log = st.checkbox("Copia anche i log tempi (Pianificazione)", value=False)
    
    offset, logs_vecchi = 0, []
    if copia_log:
        ids_task_vecchi = [t['id'] for t in tk_data if t['commessa_id'] == cms_dict[sel_cm_nome]]
        logs_vecchi = [l for l in log_data if l['task_id'] in ids_task_vecchi]
        if logs_vecchi:
            offset = (st.date_input("Nuova data di inizio", value=datetime.now().date()) - pd.to_datetime([l['inizio'] for l in logs_vecchi]).min().date()).days
    
    if st.button("🚀 Avvia Clonazione", type="primary", width='stretch'):
        res_cm = supabase.table("Commesse").insert({"nome_commessa": nuovo_nome, "stato": "Pianificata"}).execute()
        if res_cm.data:
            new_cm_id = res_cm.data[0]['id']
            old_to_new_tasks = {}
            for t in [t for t in tk_data if t['commessa_id'] == cms_dict[sel_cm_nome]]:
                res_tk = supabase.table("Task").insert({"nome_task": t['nome_task'], "commessa_id": new_cm_id, "stato": t.get('stato', 'Pianificato 🔵')}).execute()
                if res_tk.data: old_to_new_tasks[t['id']] = res_tk.data[0]['id']
            if copia_log and logs_vecchi:
                nuovi_logs = [{"operatore": l['operatore'], "task_id": old_to_new_tasks[l['task_id']], "inizio": (pd.to_datetime(l['inizio']) + pd.Timedelta(days=offset)).strftime('%Y-%m-%d'), "fine": (pd.to_datetime(l['fine']) + pd.Timedelta(days=offset)).strftime('%Y-%m-%d'), "ora_i": l.get('ora_i', '08:00:00'), "ora_f": l.get('ora_f', '17:00:00'), "note": l.get('note', "")} for l in logs_vecchi]
                supabase.table("Log_Tempi").insert(nuovi_logs).execute()
            get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
            
@st.dialog("📥 Importa Log da Excel")
def import_excel_modal():
    st.write("Scarica il modello, compilalo e caricalo qui sotto.")
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        pd.DataFrame([['Mario Rossi', '2024-05-10', 'Commessa Alpha', 'Cantiere', 'Montaggio', '08:30:00', '12:30:00', 'Note opzionali']], columns=['operatore', 'data', 'commessa', 'task', 'tag', 'ora_inizio', 'ora_fine', 'note']).to_excel(writer, index=False, sheet_name='Modello')
        
    st.download_button("📥 Scarica Modello Excel", data=buffer.getvalue(), file_name="Modello_Import_Log.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    if uploaded_file := st.file_uploader("Carica file .xlsx", type="xlsx"):
        if st.button("Avvia Importazione"):
            with st.spinner("Elaborazione in corso..."):
                try:
                    ops_ref = {str(o['nome']).strip().lower(): str(o['nome']).strip() for o in get_cached_data("Operatori")}
                    tags_ref = {str(t['nome']).strip().lower(): t['id'] for t in get_cached_data("Tag")}
                    comms_ref = {str(c['nome_commessa']).strip().lower(): c['id'] for c in get_cached_data("Commesse")}
                    
                    df_excel = pd.read_excel(uploaded_file)
                    logs_to_insert, error_log = [], []

                    for idx, row in df_excel.iterrows():
                        op_name = str(row.get('operatore', '')).strip().lower()
                        t_name = str(row.get('tag', '')).strip().lower()
                        if op_name not in ops_ref or t_name not in tags_ref:
                            st.warning(f"Riga {idx+2}: Operatore o Tag non trovato."); continue

                        c_key = str(row.get('commessa', '')).strip().lower()
                        c_id = comms_ref.get(c_key)
                        if not c_id:
                            c_id = supabase.table("Commesse").insert({"nome_commessa": str(row.get('commessa', '')).strip(), "stato": "In corso 🟡"}).execute().data[0]['id']
                            comms_ref[c_key] = c_id

                        task_name = str(row.get('task', '')).strip()
                        check_t = supabase.table("Task").select("id").eq("commessa_id", c_id).eq("nome_task", task_name).execute()
                        task_id = check_t.data[0]['id'] if check_t.data else supabase.table("Task").insert({"commessa_id": c_id, "nome_task": task_name, "stato": "In corso 🟡"}).execute().data[0]['id']

                        try:
                            def fmt_time(val): return val.strftime('%H:%M:%S') if hasattr(val, 'strftime') else (str(val).strip() if pd.notna(val) else "00:00:00")
                            logs_to_insert.append({
                                "operatore": ops_ref[op_name], "inizio": pd.to_datetime(row['data']).strftime('%Y-%m-%d'), "fine": pd.to_datetime(row['data']).strftime('%Y-%m-%d'),
                                "ora_i": fmt_time(row['ora_inizio']), "ora_f": fmt_time(row['ora_fine']), "tag": tags_ref[t_name], "task_id": task_id, "note": str(row['note']) if pd.notna(row['note']) else ""
                            })
                        except Exception as e: st.warning(f"Errore riga {idx+2}: {e}")

                    if logs_to_insert:
                        supabase.table("Log_Tempi").insert(logs_to_insert).execute()
                        st.success(f"Inseriti {len(logs_to_insert)} log!")
                        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
                    else: st.error("Nessun dato valido trovato.")
                except Exception as ex: st.error(f"Errore tecnico: {ex}")

def calcola_ore_evolute_12h(group, col_tag):
    intervalli = []
    for _, r in group.iterrows():
        durata_lorda, f_i, f_f = (r['frac_f'] - r['frac_i']) * 12.0, r['frac_i'], r['frac_f'] 
        if durata_lorda >= 8.0: f_f = max(f_i, f_f - (1.0 / 12.0))
        intervalli.append({'inizio': f_i, 'fine': f_f, 'tag': r[col_tag]})
    
    intervalli.sort(key=lambda x: x['inizio'])
    ore_per_tag = {}
    if not intervalli: return pd.Series(ore_per_tag)

    punti = sorted(list(set([t['inizio'] for t in intervalli] + [t['fine'] for t in intervalli])))
    for i in range(len(punti) - 1):
        p_inizio, p_fine = punti[i], punti[i+1]
        if p_fine == p_inizio: continue
        midpoint = (p_inizio + p_fine) / 2.0    
        task_attivi = [t for t in intervalli if t['inizio'] <= midpoint and t['fine'] >= midpoint]
        if task_attivi:
            quota_ore = ((p_fine - p_inizio) * 12.0) / len(task_attivi)   
            for t in task_attivi: ore_per_tag[t['tag']] = ore_per_tag.get(t['tag'], 0) + quota_ore            
    return pd.Series(ore_per_tag)

# --- 6. FUNZIONI HELPER GRAFICHE ---
def get_it_date_label(dt, delta):
    mesi, giorni = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"], ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    return f"Sett. {dt.isocalendar()[1]}<br>{mesi[dt.month-1]}" if delta > 40 else f"{giorni[dt.weekday()]} {dt.day:02d}<br>{mesi[dt.month-1]}<br>Sett. {dt.isocalendar()[1]}"
	
def genera_colore_opaco(testo):
    tinta = int(hashlib.md5(testo.encode()).hexdigest()[:8], 16) % 360
    l = 55 / 100
    a = 40 * min(l, 1 - l) / 100
    def f(n):
        k = (n + tinta / 30) % 12
        return f'{round(255 * (l - a * max(min(k - 3, 9 - k, 1), -1))):02x}'
    return f'#{f(0)}{f(8)}{f(4)}'
    
@st.dialog("🔖 Nuovo tag")
def modal_tag():
    lista_tag = sorted([t['nome'] for t in get_cached_data("Tag")])
    if nuovo_tag_n := st.text_input("➕ Crea nuovo Tag (scrivi e premi invio)", key="tag_input_n"):
        if nuovo_tag_n not in lista_tag:
            supabase.table("Tag").insert({"nome": nuovo_tag_n, "colore": genera_colore_opaco(nuovo_tag_n)}).execute()
            st.success(f"Tag '{nuovo_tag_n}' creato!")
            get_cached_data.clear(); st.rerun()
                    
# --- 7. GANTT FRAGMENT ---
@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, color_map, oggi_dt, x_range, delta_giorni, shapes):
    if df_plot.empty: st.info("Nessun dato trovato."); return
    
    mappa_colori_tag = {str(t['nome']).strip().lower(): t['colore'] for t in supabase.table("Tag").select("id, nome, colore").execute().data}
    df_merged = df_plot.copy()
    df_tasks_univoci = df_merged[['Commessa', 'Task', 'task_id', 'stato_commessa', 'stato_task']].drop_duplicates()
    fig = go.Figure()

    m_emj_cm = {"Quotazione 🟣": "🟣", "Pianificata 🔵": "🔵", "In corso 🟡": "🟡", "Completata 🟢": "🟢", "Sospesa 🟠": "🟠", "Cancellata 🔴": "🔴"}
    m_emj_tk = {"Pianificato 🔵": "🔵", "In corso 🟡": "🟡", "In attesa ⚪": "⚪", "Completato 🟢": "🟢", "Sospeso 🟠": "🟠"}
    
    click_dates = pd.date_range(start=x_range[0], end=x_range[1], freq='D')
    grid_bases, grid_xs, grid_ys, grid_customdata = [], [], [], []

    for _, r in df_tasks_univoci.iterrows():
        c_label = "<br>".join(textwrap.wrap(f"{m_emj_cm.get(r['stato_commessa'], '⚫')} {r['Commessa']}", 15))
        y_val = c_label if st.session_state.vista_compressa else (c_label, "<br>".join(textwrap.wrap(f"{m_emj_tk.get(r.get('stato_task'), '⚫')} {r['Task']}", 30)))
        for d in click_dates:
            grid_bases.append(d); grid_xs.append(86400000); grid_ys.append(y_val); grid_customdata.append(["LOG_FITTIZIO", r['task_id'], d.date()])

    fig.add_trace(go.Bar(base=grid_bases, x=grid_xs, y=grid_ys if st.session_state.vista_compressa else list(zip(*grid_ys)), orientation='h', marker=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo='none', customdata=grid_customdata, width=0.9, offset=-0.45))
            
    for op in df_merged['operatore'].unique():
        df_op = df_merged[df_merged['operatore'] == op]
        colore_tag = df_op['tag'].astype(str).str.strip().str.lower().map(mappa_colori_tag).fillna("rgba(0,0,0,0)").tolist()
        y_labels = [("<br>".join(textwrap.wrap(f"{m_emj_cm.get(r['stato_commessa'], '⚫')} {r['Commessa']}", 15)) if st.session_state.vista_compressa else ["<br>".join(textwrap.wrap(f"{m_emj_cm.get(r['stato_commessa'], '⚫')} {r['Commessa']}", 15)), "<br>".join(textwrap.wrap(f"{m_emj_tk.get(r.get('stato_task'), '⚫')} {r['Task']}", 30))]) for _, r in df_op.iterrows()]

        fig.add_trace(go.Bar(base=df_op['Visual_Inizio'], x=df_op['Durata_ms'], y=y_labels if st.session_state.vista_compressa else list(zip(*y_labels)), orientation='h', marker=dict(color=[color_map.get(op, "#8dbad2")] * len(df_op), cornerradius=12), width=0.4, offsetgroup=f"group_{op}", hoverinfo='skip'))
        fig.add_trace(go.Bar(base=df_op['Visual_Inizio'], x=df_op['Durata_ms'], y=y_labels if st.session_state.vista_compressa else list(zip(*y_labels)), orientation='h', name=op, offsetgroup=f"group_{op}", marker=dict(color="rgba(0,0,0,0)", cornerradius=12, pattern=dict(shape="/", fgcolor=colore_tag, fgopacity=0.9, size=6,solidity=0.3, fillmode="overlay")), width=0.4, customdata=list(zip(df_op['id'], df_op['operatore'], df_op['Inizio'], df_op['Fine'], df_op['Commessa'], df_op['Task'], df_op['note_html'], df_op['task_id'], df_op['tag'], colore_tag)), hovertemplate="<b>%{customdata[4]} - %{customdata[5]}</b><br>%{customdata[1]} / <span style='background-color:%{customdata[9]}'>&nbsp;%{customdata[8]}&nbsp;</span><br>%{customdata[6]}<extra></extra>"))
        
    start_buffer, end_buffer = x_range[0] - timedelta(days=180), x_range[1] + timedelta(days=180)
    full_range = pd.date_range(start=start_buffer, end=end_buffer, freq='D')
    tick_range = pd.date_range(start=start_buffer, end=end_buffer, freq='W-MON') if delta_giorni > 60 else (full_range[full_range.weekday.isin([0, 2, 4])] if delta_giorni > 20 else full_range)
    
    all_shapes, curr = [], x_range[0] - timedelta(days=60)
    while curr <= x_range[1] + timedelta(days=60):
        all_shapes.append(dict(type="line", x0=curr, x1=curr, y0=0, y1=1, yref="paper", line=dict(color="#e0e0e0", width=1), layer="below"))
        if curr.weekday() >= 5: all_shapes.append(dict(type="rect", x0=curr, x1=curr+timedelta(days=1), y0=0, y1=1, yref="paper", fillcolor="#f0f0f0", opacity=0.5, line_width=0, layer="below"))
        curr += timedelta(days=1)
        
    fig.update_layout(clickmode='event+select', height=300 + (len(df_merged['Commessa'].unique() if st.session_state.vista_compressa else df_merged[['Commessa', 'Task']].drop_duplicates()) * 25), showlegend=False, margin=dict(l=10, r=10, t=40, b=0), shapes=all_shapes, barmode= 'group', bargap=0.2, bargroupgap=0, dragmode='pan', xaxis=dict(type="date", ticklabelmode="period", side="top", range=x_range, tickvals=tick_range + pd.Timedelta(hours=12), ticktext=[get_it_date_label(d, delta_giorni) for d in tick_range]), yaxis=dict(autorange="reversed", showgrid=True, showdividers=True, fixedrange=True,tickson="boundaries"), legend=dict(orientation="h", y=1.14, x=0.5, xanchor="center"))
    
    frac_oggi = max(0, min(1, ((datetime.now(tz).hour + datetime.now(tz).minute / 60.0) - 7.0) / 12.0))
    fig.add_vline(x=datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000 + (frac_oggi * 86400000), line_width=2, line_color="red", annotation_text=datetime.now(tz).strftime("%H:%M"), annotation_position="top right")
    
    if selected := st.plotly_chart(fig, width='stretch', key=f"gantt_chart_{st.session_state.chart_key}", on_select="rerun", config={'displaylogo': False, 'modeBarButtonsToRemove': ['zoom', 'pan', 'select', 'lasso2d', 'zoomIn', 'zoomOut', 'autoScale', 'resetScale', 'hoverClosestCartesian', 'hoverCompareCartesian', 'toggleSpikelines'], 'toImageButtonOptions': {'format': 'png','filename': 'gantt_aster','height': 1080,'width': 1920, 'scale': 2}}):
        if "selection" in selected and "points" in selected["selection"] and (pts := selected["selection"]["points"]):
            d = pts[0].get("customdata", [])
            if d: modal_gestione_clic(d[1], pd.to_datetime(d[2]).date()) if d[0] == "LOG_FITTIZIO" else modal_edit_log(d[0], d[1], d[2], d[3], d[7], d[6])
    
# --- 8. MAIN UI ---
l, tk, cm, ops_list = get_cached_data("Log_Tempi"), get_cached_data("Task"), get_cached_data("Commesse"), get_cached_data("Operatori")
df = pd.DataFrame()

if l and tk and cm:
    tk_m = {t['id']: {'n': t['nome_task'], 'c': t['commessa_id'], 's': t.get('stato', 'Pianificato 🔵')} for t in tk}
    cm_m = {c['id']: {'n': c['nome_commessa'], 's': c.get('stato', 'In corso 🟡')} for c in cm}
    df = pd.DataFrame(l)
    
    # Ottimizzazione: Vettorializzazione e map invece di lambda functions
    df['Inizio'], df['Fine'] = pd.to_datetime(df['inizio']).dt.normalize(), pd.to_datetime(df['fine']).dt.normalize()
    
    tk_mapped = df['task_id'].map(tk_m).fillna({})
    df['Commessa'] = tk_mapped.map(lambda x: cm_m.get(x.get('c'), {}).get('n', "N/A") if isinstance(x, dict) else "N/A")
    df['Task'] = tk_mapped.map(lambda x: x.get('n', "N/A") if isinstance(x, dict) else "N/A")
    df['stato_commessa'] = tk_mapped.map(lambda x: cm_m.get(x.get('c'), {}).get('s', "In corso 🟡") if isinstance(x, dict) else "In corso 🟡")
    df['stato_task'] = tk_mapped.map(lambda x: x.get('s', "Pianificato 🔵") if isinstance(x, dict) else "Pianificato 🔵")
    
    # Ottimizzazione VETTORIALE di `calcola_logica_visuale`
    df['ora_i'] = df.get('ora_i', '08:00:00').fillna('08:00:00').astype(str)
    if 'ora_f' not in df.columns: df['ora_f'] = None
    
    t_i = pd.to_datetime(df['ora_i'], format='%H:%M:%S', errors='coerce')
    df['frac_i'] = ((t_i.dt.hour + t_i.dt.minute / 60.0) - 7.0) / 12.0
    df['frac_i'] = df['frac_i'].fillna(0.0)

    m_open = df['ora_f'].isna() | (df['ora_f'] == 'None') | (df['ora_f'] == '')
    t_f = pd.to_datetime(df['ora_f'].where(~m_open, datetime.now().strftime('%H:%M:%S')), format='%H:%M:%S', errors='coerce')
    df['frac_f'] = ((t_f.dt.hour + t_f.dt.minute / 60.0) - 7.0) / 12.0
    df['frac_f'] = df['frac_f'].fillna(1.0)
    
    # Min/Max vettoriali
    df['frac_f'] = df[['frac_f', 'frac_i']].max(axis=1).clip(upper=1.0)
    df['Visual_Durata_Frac'] = (df['frac_f'] - df['frac_i']).clip(lower=0.5/12.0)
    
    df['Visual_Inizio'] = df['Inizio'] + pd.to_timedelta(df['frac_i'], unit='D')
    df['Durata_ms'] = df['Visual_Durata_Frac'] * 86400000
    df['Visual_Fine'] = df['Visual_Inizio'] + pd.to_timedelta(df['Visual_Durata_Frac'], unit='D')
    
    # Ottimizzazione VETTORIALE di `formatta_nota`
    d_str = df['Inizio'].dt.strftime('%d/%m')
    oi_str = df['ora_i'].str[:5].fillna("??:??")
    of_str = df['ora_f'].astype(str).str[:5].where(~m_open, "In corso")
    n_str = df.get('note', '').fillna("")
    df['note_html'] = "• <i>" + d_str + " [" + oi_str + "-" + of_str + "]</i>: " + n_str
    
    # --- AREA CONTROLLI (FIXED HEADER) ---
    with st.expander("🛠️ Pannello Filtri e Strumenti", expanded=True):
        if 'tag' in df.columns: df['tag'] = df['tag'].map({t['id']: t['nome'] for t in get_cached_data("Tag")}).fillna("Senza Tag")
            
        c1, c2, c4, c3 = st.columns([1, 1, 1, 2])
        f_c = c1.multiselect("Progetti", sorted(df['Commessa'].unique()), label_visibility="collapsed", placeholder="Progetti")
        f_o = c2.multiselect("Operatori", sorted(df['operatore'].unique()), label_visibility="collapsed", placeholder="Operatori")
        f_s_tag = c4.multiselect("Tag", sorted(df['tag'].unique().astype(str)), label_visibility="collapsed", placeholder="Tag")
        with c3:
            cs, cd = st.columns(2)
            scala = cs.selectbox("Scala", ["Settimana","2 Settimane", "Mese", "Trimestre", "Semestre", "Personalizzato"], index=0, label_visibility="collapsed")
            f_custom = cd.date_input("Periodo", value=[datetime.now(), datetime.now() + timedelta(days=7)], label_visibility="collapsed") if scala == "Personalizzato" else None
		
        s1, s2, s4, s3 = st.columns([1, 1, 1, 2])
        f_s_cm = s1.multiselect("Stato Commesse", STATI_COMMESSA, label_visibility="collapsed", placeholder="Stato Commesse")
        f_s_tk = s2.multiselect("Stato Task", STATI_TASK, label_visibility="collapsed", placeholder="Stato Task")

        with s3:
            f_range = st.date_input("Intervallo Date", value=[df['Inizio'].min(), df['Fine'].max() + pd.Timedelta(days=7)], format="DD/MM/YYYY", label_visibility="collapsed", key="filter_date_range")
        with s4:
            search_text = st.text_input("🔍 Cerca per Testo", value="", placeholder="Cerca per Testo", label_visibility="collapsed").lower()
            
        st.markdown('<div class="spacer-btns"></div>', unsafe_allow_html=True)
        b1, b3, b7, b4, b5, b6 = st.columns(6)
        if b1.button("➕ Commessa", width='stretch'): modal_commessa()
        if b3.button("⏱️ Log", width='stretch'): modal_log()
        if b7.button("🔖 Tag", width='stretch'): modal_tag()
        if b4.button("📍 Oggi", width='stretch'): st.session_state.chart_key += 1; st.rerun()
        if b5.button("↔️ Espandi" if st.session_state.vista_compressa else "↕️ Comprimi", width='stretch'): st.session_state.vista_compressa = not st.session_state.vista_compressa; st.rerun()
        if b6.button("Importa 📥", width='stretch'): import_excel_modal()
        st.markdown('</div>', unsafe_allow_html=True)
		
    # --- SEZIONE LOG APERTI ---
    if not (log_aperti := df[df['ora_f'].isna() | (df['ora_f'] == 'None')]).empty:
        st.markdown("<h4 style='margin-bottom: 0px; padding-top: 0px;'>⏱️ Log in Corso</h4>", unsafe_allow_html=True)
        for _, row in log_aperti.iterrows():
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([4, 2, 2, 0.7, 0.7], gap="small")
                trascorso = datetime.now(tz) - datetime.combine(row['Inizio'].date() if hasattr(row['Inizio'], 'date') else row['Inizio'], pd.to_datetime(row['ora_i']).time()).replace(tzinfo=tz)
                c1.markdown(f"<p style='margin-bottom:0; font-size:14px;'><strong>{row['Commessa']} - {row['Task']}</strong> | {row['operatore']} - {row['tag']} | {row['note']}</p>", unsafe_allow_html=True)
                c2.markdown(f"<p style='margin-bottom:0; font-size:14px;'>Iniziato alle: {row['ora_i'][:5]}</p>", unsafe_allow_html=True)
                c3.markdown(f"<p style='margin-bottom:0; font-size:14px; color:#d97706;'>⏳ da {trascorso.seconds // 3600}h {(trascorso.seconds % 3600) // 60}m</p>", unsafe_allow_html=True)
                
                if c4.button("Fine", key=f"stop_{row['id']}", type="primary"):
                    supabase.table("Log_Tempi").update({"ora_f": datetime.now(tz).strftime('%H:%M:%S')}).eq("id", row['id']).execute()
                    get_cached_data.clear(); st.rerun()
                    
                if c5.button("Fine + ➕", key=f"next_{row['id']}", type="primary", use_container_width=True):
                    supabase.table("Log_Tempi").update({"ora_f": datetime.now(tz).strftime('%H:%M:%S')}).eq("id", row['id']).execute()
                    get_cached_data.clear()
                    modal_gestione_clic(task_id=row['task_id'], data_clic=datetime.now(tz).date())

    # --- FILTRAGGIO DATI ---
    df_p = df.copy()
    if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
    if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]
    if f_s_cm: df_p = df_p[df_p['stato_commessa'].isin(f_s_cm)]
    if f_s_tk: df_p = df_p[df_p['stato_task'].isin(f_s_tk)]
    if f_s_tag: df_p = df_p[df_p['tag'].isin(f_s_tag)]
    if search_text: df_p = df_p[df_p['Commessa'].astype(str).str.lower().str.contains(search_text) | df_p['Task'].astype(str).str.lower().str.contains(search_text)]
    
if isinstance(f_range, (list, tuple)) and len(f_range) == 2:
    start_search, end_search = pd.to_datetime(f_range[0]), pd.to_datetime(f_range[1])
    df_p['inizio'], df_p['fine'] = pd.to_datetime(df_p['inizio']), pd.to_datetime(df_p['fine'])
    df_p = df_p[(df_p['inizio'] <= end_search) & (df_p['fine'] >= start_search)]
    
tabs = st.tabs(["📊 Timeline", "📅 Calendario", "📑 Agenda", "📋 Gestione Logs", "⚙️ Gestione", "📈 Statistiche"])    

with tabs[0]: 
    if not df.empty:
        oggi_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if not (start_search <= oggi_dt <= end_search): oggi_dt = start_search + (end_search-start_search)/2
        
        x_range = [pd.to_datetime(f_custom[0]), pd.to_datetime(f_custom[1])] if scala == "Personalizzato" and f_custom and len(f_custom) == 2 else [oggi_dt - timedelta(days={"Settimana": 4, "2 Settimane": 8, "Mese": 15, "Trimestre": 45, "Semestre": 90}.get(scala, 15)), oggi_dt + timedelta(days={"Settimana": 4, "2 Settimane": 8, "Mese": 15, "Trimestre": 45, "Semestre": 90}.get(scala, 15))]
        render_gantt_fragment(df_p, {o['nome']: o.get('colore', '#8dbad2') for o in ops_list}, oggi_dt, x_range, (x_range[1]-x_range[0]).days, [])
        
with tabs[1]: 
    if not df.empty:
        cal_events = []
        color_map = {o['nome']: o.get('colore', '#3D85C6') for o in ops_list}
        for _, row in df_p.iterrows():
            try:
                cal_events.append({"id": str(row["id"]), "title": f"{row['operatore']} | {row['Task']}".replace('"', "'").replace('\n', ' '), "start": f"{row['Inizio'].strftime('%Y-%m-%d')}T{row['ora_i']}", "end": f"{row['Fine'].strftime('%Y-%m-%d')}T{row['ora_f']}", "color": color_map.get(row["operatore"], "#3D85C6"), "allDay": True, "extendedProps": {"nota": str(row.get('note', '')).replace('"', "'").replace('\n', ' ')}})
            except: continue

        st.markdown("""<style>.fc .fc-multimonth-month {padding: 0px !important; margin-bottom: 2px !important;} .fc .fc-daygrid-day-frame {min-height: 35px !important; max-height: 120px !important;} .fc .fc-daygrid-day-top {flex-direction: row !important; font-size: 0.85em !important;} .fc-daygrid-event {margin-top: 0px !important; margin-bottom: 1px !important; padding: 0px 2px !important; font-size: 0.8em !important;} .fc-multimonth-daygrid {--fc-daygrid-event-h-height: 18px;} iframe[title="streamlit_calendar.calendar"] {width: 100% !important; min-height: 1500px !important; height: 1500px !important;}</style>""", unsafe_allow_html=True)
        try:
            state = calendar(events=cal_events, options={"initialView": "multiMonthYear", "multiMonthMaxColumns": 2,"multiMonthMinWidth": 500, "views": {"multiMonthYear": {"duration": {"months": 2}}}, "height": "auto", "contentHeight": "auto", "aspectRatio": 1.3, "expandRows": False, "locale": "it", "firstDay": 1, "weekNumbers": True, "weekText": "Sett.", "headerToolbar": {"left": "prev,next today", "center": "title", "right": "multiMonthYear,dayGridMonth,timeGridWeek"}, "editable": False, "selectable": True}, key=f"calendar_{st.session_state.chart_key}")
            if state and "eventClick" in state:
                sel = df[df['id'] == int(state["eventClick"]["event"]["id"])].iloc[0]
                modal_edit_log(sel['id'], sel['operatore'], sel['Inizio'], sel['Fine'], sel['task_id'], sel['note'])
            if state and state.get("dateClick"): modal_log()
        except Exception as e: st.error(f"Errore nel componente calendario: {e}")
    else: st.info("Nessun dato presente. Registra un log per vedere il calendario.")

with tabs[2]: 
    if not df.empty:
        st.subheader("Agenda Verticale")
        color_map = {o['nome']: o.get('colore', '#3D85C6') for o in ops_list}
        cal_events_agenda = [{"id": str(row["id"]), "title": f"{row['operatore']} | {row['Commessa']} | {row['Task']} - {row['note']}".replace('"', "'").replace('\n', ' '), "start": f"{row['Inizio'].strftime('%Y-%m-%d')}T{row['ora_i']}", "end": f"{row['Fine'].strftime('%Y-%m-%d')}T{row['ora_f']}", "color": color_map.get(row["operatore"], "#3D85C6"), "extendedProps": {"nota": str(row.get('note', '')).replace('"', "'").replace('\n', ' ')}} for _, row in df_p.iterrows()]
        calendar(events=cal_events_agenda, options={"initialView": "listDay", "headerToolbar": {"left": "prev,next today", "center": "title", "right": "listDay,listWeek,listMonth"}, "buttonText": {"listDay": "Giorno", "listWeek": "Settimana", "listMonth": "Mese"}, "noEventsContent": "Nessun task per questa data", "displayEventTime": True, "locale": "it", "height": 1000}, key="calendar_agenda_vertical")
        
with tabs[3]: 
    st.header("📋 Gestione Logs")
    if not df_p.empty:
        df_edit = df_p[['id', 'Commessa', 'Task', 'operatore', 'tag', 'Inizio', 'Fine', 'ora_i', 'ora_f', 'note']].copy()
        df_edit['Inizio'], df_edit['Fine'] = pd.to_datetime(df_edit['Inizio']).dt.date, pd.to_datetime(df_edit['Fine']).dt.date
        df_edit['ora_i'], df_edit['ora_f'] = pd.to_datetime(df_edit['ora_i'], format='%H:%M:%S', errors='coerce').dt.time.fillna(time(8, 0)), pd.to_datetime(df_edit['ora_f'], format='%H:%M:%S', errors='coerce').dt.time.fillna(time(17, 0))

        map_task = {s['nome_task']: s['id'] for s in get_cached_data("Task")}
        mappa_tags = {t['nome']: t['id'] for t in get_cached_data("Tag")}

        edited_log = st.data_editor(df_edit, column_config={"id": None, "Commessa": st.column_config.Column(disabled=True), "Task": st.column_config.Column(disabled=True), "operatore": st.column_config.SelectboxColumn("Operatore", options=sorted([o['nome'] for o in ops_list]), width="medium", required=True), "tag": st.column_config.SelectboxColumn("Tag", options=sorted(list(mappa_tags.keys())), width="medium"), "inizio": st.column_config.DateColumn("Inizio", format="DD/MM/YYYY"), "fine": st.column_config.DateColumn("Fine", format="DD/MM/YYYY"), "ora_i": st.column_config.TimeColumn("Ora Inizio", format="HH:mm"), "ora_f": st.column_config.TimeColumn("Ora Fine", format="HH:mm")}, width='stretch', hide_index=True)
        if st.button("Salva Modifiche Tabella"):
            for _, r in edited_log.iterrows():
                try: supabase.table("Log_Tempi").update({"operatore": r['operatore'], "inizio": str(r['Inizio']), "fine": str(r['Fine']), "ora_i": str(r['ora_i']), "ora_f": str(r['ora_f']), "note": r['note'], "tag": mappa_tags.get(r["tag"])}).eq("id", r['id']).execute()
                except Exception as e: st.error(f"Errore log {r['id']}: {e}")
            st.success("Modifiche salvate!"); get_cached_data.clear(); st.rerun()

with tabs[4]: 
    st.header("⚙️ Setup di Sistema")
    s1, s2, s4, s3 = st.tabs(["🏗️ Commesse", "👥 Operatori", "🔖 Tag", "✅ Task"])
    
    with s1:
        if not (df_cm_setup := pd.DataFrame(cm)).empty:
            df_cm_setup['stato'] = df_cm_setup['stato'].fillna("Pianificata").astype(str)
            if st.button("Aggiorna Commesse", key="btn_cm_v4"): aggiorna_database_setup("Commesse", st.data_editor(df_cm_setup, column_config={"id": None, "stato": st.column_config.SelectboxColumn("Stato", options=STATI_COMMESSA)}, width='stretch', num_rows="dynamic", key="setup_cm_editor_v4"), cm)
            if st.button("Clona Commessa"): modal_clona_avanzata()

    with s2:
        st.subheader("Gestione Operatori")
        if ops_list:
            ed_op = st.data_editor(pd.DataFrame(ops_list), column_config={"id": None, "nome": st.column_config.TextColumn("Nome Operatore", required=True), "colore": st.column_config.TextColumn("Colore (HEX)")}, width='stretch', num_rows="dynamic", hide_index=True, key="setup_operatori_vfinal")
            st.code(st.color_picker("Scegli un colore e copia il codice HEX nella tabella", "#8dbad2")) 
            if st.button("Salva Operatori"): aggiorna_database_setup("Operatori", ed_op, ops_list)

    with s4:
        st.subheader("Gestione Tag")
        if raw_tag := get_cached_data("Tag"):
            ed_tag = st.data_editor(pd.DataFrame(raw_tag), column_config={"id": None, "nome": st.column_config.TextColumn("Tag", required=True), "colore": st.column_config.TextColumn("Colore (HEX)")}, width='stretch', num_rows="dynamic", hide_index=True, key="setup_tag_vfinal")
            st.code(st.color_picker("Scegli un colore e copia il codice HEX nella tabella", "#8dbad2", key="col_tag_pick")) 
            if st.button("Salva Tag"): aggiorna_database_setup("Tag", ed_tag, raw_tag)

    with s3:
        st.subheader("Gestione Task")
        if tk:
            name_to_id = {str(c['nome_commessa']): c['id'] for c in cm}
            df_tk_setup = pd.DataFrame(tk)
            df_tk_setup['commessa_nome'] = df_tk_setup['commessa_id'].map({c['id']: str(c['nome_commessa']) for c in cm}).fillna(sorted(list(name_to_id.keys()))[0] if name_to_id else "")
            df_tk_setup['stato'] = df_tk_setup['stato'].fillna(STATI_TASK[0])

            ed_tk = st.data_editor(df_tk_setup, column_config={"id": None, "commessa_id": None, "commessa_nome": st.column_config.SelectboxColumn("Commessa", options=sorted(list(name_to_id.keys()))), "stato": st.column_config.SelectboxColumn("Stato", options=STATI_TASK)}, width='stretch', num_rows="dynamic", hide_index=True, key="editor_tk_string_v6")
            
            if st.button("Aggiorna Task", key="btn_save_tk_v6"):
                df_da_salvare = ed_tk.copy()
                df_da_salvare['commessa_id'] = df_da_salvare['commessa_nome'].map(name_to_id)
                aggiorna_database_setup("Task", df_da_salvare.drop(columns=['commessa_nome']), tk)

with tabs[5]:
    def format_hours_to_hhmm(decimal_hours):
        hours, minutes = int(decimal_hours), int(round((decimal_hours - int(decimal_hours)) * 60))
        if minutes == 60: hours += 1; minutes = 0
        return f"{hours:02d}:{minutes:02d}"
        
    if not df_p.empty:
        col_tag, col_comm = 'Tag' if 'Tag' in df_p.columns else 'tag', 'commessa' if 'commessa' in df_p.columns else ('Commessa' if 'Commessa' in df_p.columns else 'commessa_id')
        df_p[col_tag], df_p['data_log'] = df_p[col_tag].fillna("Nessun Tag").astype(str).str.strip(), pd.to_datetime(df_p['inizio']).dt.date

        risultato_apply = df_p.groupby(['operatore', 'data_log'], group_keys=True).apply(lambda x: calcola_ore_evolute_12h(x, col_tag), include_groups=False)
        df_netto_globale = risultato_apply.stack().reset_index() if isinstance(risultato_apply, pd.DataFrame) else risultato_apply.reset_index()

        df_netto_globale = df_netto_globale.rename(columns={df_netto_globale.columns[-1]: 'ore_lavorate', df_netto_globale.columns[-2]: col_tag, df_netto_globale.columns[0]: 'operatore', df_netto_globale.columns[1]: 'data_log'})[['operatore', 'data_log', col_tag, 'ore_lavorate']]
        
        if not (df_totale_periodo := df_netto_globale.groupby(['operatore', col_tag])['ore_lavorate'].sum().reset_index()).empty:
            df_totale_periodo[col_tag] = df_totale_periodo.get(col_tag, pd.Series()).fillna("Altro").astype(str)
            df_totale_periodo['testo_ore'] = df_totale_periodo['ore_lavorate'].apply(lambda x: format_hours_to_hhmm(x) if pd.notna(x) and x > 0 else "00:00")
            
        c1, c2 = st.columns([2, 1])

        color_discrete_map = {str(t.get('nome', '')).strip(): (str(t.get('colore', '#8dbad2')).strip() if str(t.get('colore', '')).startswith('#') else f"#{str(t.get('colore', '#8dbad2')).strip()}") for t in get_cached_data("Tag")}

        with c1:
            st.subheader("👥 Carico Lavoro per Operatore")
            fig_stats = px.bar(df_totale_periodo, x='operatore', y='ore_lavorate', color=col_tag, barmode='group', color_discrete_map=color_discrete_map, text='testo_ore', title="Ore Effettive (Netto sovrapposizioni e pausa)", labels={'testo_ore': 'Ore Totali', 'operatore': 'Operatore', col_tag: 'Tag'}, template="plotly_white")
            fig_stats.update_layout(hovermode="x unified")
            st.plotly_chart(fig_stats, use_container_width=True)

        with c2:
            st.subheader("🔖 Ore Totali per Tag")
            if not df_totale_periodo.empty:
                df_tag_pie = df_totale_periodo.groupby(col_tag)['ore_lavorate'].sum().reset_index()
                df_tag_pie['testo_ore_tag'] = df_tag_pie['ore_lavorate'].apply(format_hours_to_hhmm)
                df_tag_pie['legenda_tag'] = df_tag_pie[col_tag] + ": " + df_tag_pie['testo_ore_tag'] + " ore"
                
                fig_tag_pie = px.pie(df_tag_pie, names='legenda_tag', values='ore_lavorate', color=col_tag, color_discrete_map=color_discrete_map, hole=.3)
                fig_tag_pie.update_traces(textposition='inside', textinfo='text', text=df_tag_pie[col_tag] + "<br>" + df_tag_pie['testo_ore_tag'], hovertemplate="<b>%{label}</b><br>Ore: %{customdata}<extra></extra>", customdata=df_tag_pie['testo_ore_tag'], insidetextorientation='horizontal')
                fig_tag_pie.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0), showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02))
                st.plotly_chart(fig_tag_pie, use_container_width=True)
            else: st.info("Nessun dato sui tag trovato per generare il grafico.")
				
        st.markdown("---")
        st.subheader("📊 Flusso Ore: Commesse ➔ Tag")
        
        distribuzione_commesse = df_p.groupby(['operatore', col_tag, col_comm])['Visual_Durata_Frac'].sum().reset_index()
        distribuzione_commesse['peso'] = distribuzione_commesse['Visual_Durata_Frac'] / distribuzione_commesse.groupby(['operatore', col_tag])['Visual_Durata_Frac'].transform('sum')
        
        df_sankey_final = distribuzione_commesse.merge(df_netto_globale, on=['operatore', col_tag])
        df_sankey_final['ore_pesate'] = df_sankey_final['ore_lavorate'] * df_sankey_final['peso']
        
        if not (links_sankey := df_sankey_final.groupby([col_comm, col_tag])['ore_pesate'].sum().reset_index()).empty:
            links_sankey['ore_formattate'] = links_sankey['ore_pesate'].apply(format_hours_to_hhmm)
            list_commesse, list_tags = sorted(list(links_sankey[col_comm].unique())), sorted(list(links_sankey[col_tag].unique()))
            all_nodes = list_commesse + list_tags
            node_map = {name: i for i, name in enumerate(all_nodes)}
            
            node_colors = ["#1E3A8A"] * len(list_commesse) + [color_discrete_map.get(t, "#4B5563") for t in list_tags]
            def hex_to_rgba(hex_val, alpha=0.5): return f'rgba({tuple(int(hex_val.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))[0]}, {tuple(int(hex_val.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))[1]}, {tuple(int(hex_val.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))[2]}, {alpha})' if pd.notna(hex_val) else f'rgba(128, 128, 128, {alpha})'

            fig_sankey = go.Figure(data=[go.Sankey(node = dict(pad=30, thickness=20, label=all_nodes, color=node_colors), textfont = dict(size = 14, color = "black"), link = dict(source=links_sankey[col_comm].map(node_map), target=links_sankey[col_tag].map(node_map), value=links_sankey['ore_pesate'], color=[hex_to_rgba(color_discrete_map.get(t, "#808080"), 0.5) for t in links_sankey[col_tag]], customdata=links_sankey['ore_formattate'], hovertemplate='Da: %{source.label}<br>A: %{target.label}<br>Durata: %{customdata}<extra></extra>'))])
            fig_sankey.update_layout(height=600, margin=dict(l=150, r=150, t=60, b=10))
            st.plotly_chart(fig_sankey, use_container_width=True)
            
    else: st.info("Nessun dato disponibile per le statistiche. Filtra i log o inserisci nuove attività.")
