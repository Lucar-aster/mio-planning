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

STATI_COMMESSA = ["Quotazione", "Pianificata", "In corso", "Completata", "Sospesa", "Cancellata"]
STATI_TASK = ["In programma", "In corso", "Completato", "Sospeso"]

# --- 2. CSS ---
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ visibility: hidden; height: 0px; }}
    .block-container {{ padding-top: 0rem !important; }}
    .compact-title {{ display: flex; align-items: center; gap: 12px; padding-top: 10px; }}
    .compact-title h1 {{ font-size: 26px !important; color: #1E3A8A; margin: 0; }}
    .spacer-btns {{ margin-top: 15px; margin-bottom: 10px; }}
    [data-testid="stContainer"] {{overflow: auto;}}
    .js-plotly-plot .xaxislayer-above {{position: sticky !important; top: 0; z-index: 1000 !important; background: white !important;}}
    .js-plotly-plot .gridlayer {{z-index: 1;}}
    /* Sticky Header per i filtri */
    div[data-testid="stVerticalBlock"] > div:has(.fixed-header) {{
        position: sticky;
        top: 0;
        background-color: white;
        z-index: 999;
        padding-bottom: 10px;
        border-bottom: 2px solid #f0f2f6;
    }}
    </style>
    <div class="compact-title">
        <img src="{LOGO_URL}" width="40">
        <h1>Progetti Aster Contract</h1>
    </div>
    <hr style="margin-top: 0px; margin-bottom: 0px; border: 0; border-top: 0px solid #eee;">
""", unsafe_allow_html=True)

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
@st.dialog("📝 Gestione Dettaglio Log")
def modal_edit_log(log_id, current_op, current_start, current_end, current_task_id, current_note=""):
    st.write(f"Operatore: **{current_op}**")
    all_logs = supabase.table("Log_Tempi").select("*").eq("operatore", current_op).eq("task_id", current_task_id).execute().data
    df_sub = pd.DataFrame(all_logs)
    if not df_sub.empty:
        df_sub['inizio'] = pd.to_datetime(df_sub['inizio']).dt.date
        df_sub['fine'] = pd.to_datetime(df_sub['fine']).dt.date
        mask = (df_sub['inizio'] >= pd.to_datetime(current_start).date()) & (df_sub['inizio'] <= pd.to_datetime(current_end).date())
        df_sub = df_sub[mask].sort_values("inizio")
    
    if df_sub.empty:
        st.warning("Nessun dato trovato.")
        return

    df_sub["Elimina"] = False
    edited_df = st.data_editor(
        df_sub,
        column_config={
            "id": None, "task_id": None,
            "inizio": st.column_config.DateColumn("Inizio", format="DD/MM/YYYY"),
            "fine": st.column_config.DateColumn("Fine", format="DD/MM/YYYY"),
            "Elimina": st.column_config.CheckboxColumn("Elimina", default=False)
        },
        disabled=["id", "task_id"], use_container_width=True, hide_index=True, key="editor_log_multi"
    )

    c1, c2 = st.columns(2)
    if c1.button("Salva Modifiche", type="primary", use_container_width=True):
        for _, row in edited_df.iterrows():
            if row["Elimina"]:
                supabase.table("Log_Tempi").delete().eq("id", row["id"]).execute()
            else:
                supabase.table("Log_Tempi").update({"operatore": row["operatore"], "inizio": str(row["inizio"]), "fine": str(row["fine"]), "note": row["note"]}).eq("id", row["id"]).execute()
        get_cached_data.clear(); st.rerun()
    if c2.button("Annulla", use_container_width=True): st.rerun()

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
    s = st.selectbox("Stato", options=STATI_TASK, index=0)
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
    task_list = list(task_opts.keys()) + ["➕ Aggiungi nuovo task..."]
    sel_task = st.selectbox("Task", options=task_list, key="new_log_tk_sb")
    new_task_name = st.text_input("Inserisci nome nuovo task", key="new_log_new_tk_ti") if sel_task == "➕ Aggiungi nuovo task..." else ""
    c1, c2 = st.columns(2)
    oggi = datetime.now().date()
    data_i, data_f = c1.date_input("Inizio", value=oggi), c2.date_input("Fine", value=oggi)
    nota = st.text_area("Note")
    if st.button("Registra Log", use_container_width=True, type="primary"):
        if not op_ms: st.error("⚠️ Seleziona operatore!"); return
        target_id = None
        if sel_task == "➕ Aggiungi nuovo task...":
            if new_task_name.strip():
                res = supabase.table("Task").insert({"nome_task": new_task_name.strip(), "commessa_id": sel_cm_id, "stato": "In corso"}).execute()
                if res.data: target_id = res.data[0]['id']
            else: st.error("Nome task mancante"); return
        else: target_id = task_opts[sel_task]
        if target_id:
            for op_name in op_ms:
                supabase.table("Log_Tempi").insert({"operatore": op_name, "task_id": target_id, "inizio": str(data_i), "fine": str(data_f), "note": nota}).execute()
            get_cached_data.clear(); st.rerun()

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
                res_tk = supabase.table("Task").insert({"nome_task": t['nome_task'], "commessa_id": new_cm_id, "stato": t.get('stato', 'In programma')}).execute()
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
    fig = go.Figure()
    
    for op in df_merged['operatore'].unique():
        df_op = df_merged[df_merged['operatore'] == op]
        c_w = ["<br>".join(textwrap.wrap(str(c), 15)) for c in df_op['Commessa']]
        t_w = ["<br>".join(textwrap.wrap(str(t), 20)) for t in df_op['Task']]
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], x=df_op['Durata_ms'], y=[c_w, t_w], orientation='h', name=op,
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12), width=0.4,
            customdata=list(zip(df_op['id'], df_op['operatore'], df_op['Inizio'], df_op['Fine'], df_op['Commessa'], df_op['Task'], df_op['note_html'], df_op['task_id'])),
            hovertemplate="<b>%{customdata[4]} - %{customdata[5]}</b><br>%{customdata[1]}<br>%{customdata[2]|%d/%m/%Y} - %{customdata[3]|%d/%m/%Y}<extra></extra>"
        ))

    all_shapes = []
    curr = x_range[0] - timedelta(days=60)
    while curr <= x_range[1] + timedelta(days=60):
        all_shapes.append(dict(type="line", x0=curr, x1=curr, y0=0, y1=1, yref="paper", line=dict(color="#e0e0e0", width=1), layer="below"))
        if curr.weekday() >= 5:
            all_shapes.append(dict(type="rect", x0=curr, x1=curr+timedelta(days=1), y0=0, y1=1, yref="paper", fillcolor="#f0f0f0", opacity=0.5, line_width=0, layer="below"))
        curr += timedelta(days=1)

    fig.update_layout(
        height=400 + (len(df_merged[['Commessa', 'Task']].drop_duplicates()) * 35),
        margin=dict(l=10, r=10, t=40, b=0), shapes=all_shapes, barmode='overlay', dragmode='pan',
        xaxis=dict(type="date", side="top", range=x_range, tickvals=pd.date_range(x_range[0]-timedelta(days=30), x_range[1]+timedelta(days=30), freq='D'), 
                   ticktext=[get_it_date_label(d, delta_giorni) for d in pd.date_range(x_range[0]-timedelta(days=30), x_range[1]+timedelta(days=30), freq='D')]),
        yaxis=dict(autorange="reversed", showgrid=True, showdividers=True, fixedrange=True),
        legend=dict(orientation="h", y=1.08, x=0.5, xanchor="center")
    )
    fig.add_vline(x=oggi_dt.timestamp() * 1000 + 43200000, line_width=2, line_color="red")
    
    selected = st.plotly_chart(fig, use_container_width=True, key=f"gantt_{st.session_state.chart_key}", on_select="rerun", config={'displayModeBar': False})
    
    if selected and "selection" in selected and "points" in selected["selection"]:
        p = selected["selection"]["points"]
        if p and "customdata" in p[0]:
            d = p[0]["customdata"]
            modal_edit_log(d[0], d[1], d[2], d[3], d[7], d[6])

# --- 8. MAIN UI ---
l, tk, cm, ops_list = get_cached_data("Log_Tempi"), get_cached_data("Task"), get_cached_data("Commesse"), get_cached_data("Operatori")
df = pd.DataFrame()
if l and tk and cm:
    tk_m = {t['id']: {'n': t['nome_task'], 'c': t['commessa_id'], 's': t.get('stato', 'In programma')} for t in tk}
    cm_m = {c['id']: {'n': c['nome_commessa'], 's': c.get('stato', 'In corso')} for c in cm}
    df = pd.DataFrame(l)
    df['Inizio'], df['Fine'] = pd.to_datetime(df['inizio']).dt.normalize(), pd.to_datetime(df['fine']).dt.normalize()
    df['Commessa'] = df['task_id'].apply(lambda x: cm_m.get(tk_m.get(x, {}).get('c'), {}).get('n', "N/A"))
    df['Task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('n', "N/A"))
    df['stato_commessa'] = df['task_id'].apply(lambda x: cm_m.get(tk_m.get(x, {}).get('c'), {}).get('s', "In corso"))
    df['stato_task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('s', "In programma"))
    df['Durata_ms'] = ((df['Fine'] + pd.Timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000

    # --- AREA CONTROLLI (FIXED HEADER) ---
    with st.container():
        st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
        # Riga 1: Progetti, Operatori, Scala
        c1, c2, c3 = st.columns([3, 3, 4])
        f_c = c1.multiselect("Progetti", sorted(df['Commessa'].unique()))
        f_o = c2.multiselect("Operatori", sorted(df['operatore'].unique()))
        with c3:
            cs, cd = st.columns(2)
            scala = cs.selectbox("Scala", ["Settimana","2 Settimane", "Mese", "Trimestre", "Semestre", "Personalizzato"], index=1)
            f_custom = cd.date_input("Periodo", value=[datetime.now(), datetime.now() + timedelta(days=7)]) if scala == "Personalizzato" else None
        
        # Riga 2: Stati
        s1, s2 = st.columns(2)
        f_s_cm = s1.multiselect("Stato Commesse", options=STATI_COMMESSA, default=["In corso", "Pianificata", "Quotazione", "Sospesa"])
        f_s_tk = s2.multiselect("Stato Task", options=STATI_TASK, default=STATI_TASK)

        # Riga 3: Pulsanti
        st.markdown('<div class="spacer-btns"></div>', unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("➕ Commessa", use_container_width=True): modal_commessa()
        if b2.button("📑 Task", use_container_width=True): modal_task()
        if b3.button("⏱️ Log", use_container_width=True): modal_log()
        if b4.button("📍 Oggi", use_container_width=True): st.session_state.chart_key += 1; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- FILTRAGGIO DATI ---
    df_p = df.copy()
    if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
    if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]
    if f_s_cm: df_p = df_p[df_p['stato_commessa'].isin(f_s_cm)]
    if f_s_tk: df_p = df_p[df_p['stato_task'].isin(f_s_tk)]

tabs = st.tabs(["📊 Timeline", "📅 Calendario", "📋 Dati", "⚙️ Setup", "📈 Statistiche"])    

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
        cal_events = []
        color_map = {o['nome']: o.get('colore', '#3D85C6') for o in ops_list}
        for _, row in df_p.iterrows():
            cal_events.append({"id": str(row["id"]), "title": f"{row['operatore']} | {row['Task']}", "start": row["Inizio"].strftime("%Y-%m-%d"), "end": (row["Fine"] + timedelta(days=1)).strftime("%Y-%m-%d"), "color": color_map.get(row["operatore"], "#3D85C6"), "allDay": True})
        state = calendar(events=cal_events, options={"locale": "it", "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,multiMonthYear"}}, key="v_cal")
        if state and "eventClick" in state:
            sel = df[df['id'] == int(state["eventClick"]["event"]["id"])].iloc[0]
            modal_edit_log(sel['id'], sel['operatore'], sel['Inizio'], sel['Fine'], sel['task_id'])

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
        df_cm_edit = pd.DataFrame(cm)
        ed_cm = st.data_editor(df_cm_edit, column_config={"id": None, "stato": st.column_config.SelectboxColumn("Stato", options=STATI_COMMESSA)}, use_container_width=True, num_rows="dynamic")
        if st.button("Aggiorna Commesse"): aggiorna_database_setup("Commesse", ed_cm, cm)
    with s2:
        df_op_edit = pd.DataFrame(ops_list)
        ed_op = st.data_editor(df_op_edit, column_config={"id": None}, use_container_width=True, num_rows="dynamic")
        if st.button("Aggiorna Operatori"): aggiorna_database_setup("Operatori", ed_op, ops_list)
with s3:
        df_tk_edit = pd.DataFrame(tk)
        if not df_tk_edit.empty:
            # Creiamo la lista delle opzioni assicurandoci che siano Integer (o il tipo usato nel DB)
            cm_opts = {int(c['id']): str(c['nome_commessa']) for c in cm}
            
            ed_tk = st.data_editor(
                df_tk_edit, 
                column_config={
                    "id": None, 
                    # Usiamo i valori (nomi) o le chiavi castate correttamente
                    "commessa_id": st.column_config.SelectboxColumn(
                        "Commessa", 
                        options=list(cm_opts.keys()), 
                        format=lambda x: cm_opts.get(x, "Sconosciuta")
                    ),
                    "stato": st.column_config.SelectboxColumn("Stato", options=STATI_TASK)
                }, 
                use_container_width=True, 
                num_rows="dynamic",
                key="editor_task_setup"
            )
            if st.button("Aggiorna Task", key="btn_save_tk_setup"): 
                aggiorna_database_setup("Task", ed_tk, tk)

with tabs[4]: # STATS
    if not df_p.empty:
        c1, c2 = st.columns(2)
        c1.bar_chart(df_p.groupby('Commessa').size())
        c2.bar_chart(df_p.groupby('operatore').size())
        st.metric("Totale Log", len(df_p))
