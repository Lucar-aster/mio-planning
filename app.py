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

# --- 2. CONNESSIONE E CACHING ---
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=60)
def get_cached_data(table):
    try: return supabase.table(table).select("*").execute().data
    except: return []

if 'chart_key' not in st.session_state: st.session_state.chart_key = 0
if 'vista_compressa' not in st.session_state: st.session_state.vista_compressa = False

# --- 3. FUNZIONI UTILITY ---
def get_it_date_label(d, delta):
    giorni = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    if delta <= 14: return f"{giorni[d.weekday()]} {d.day}"
    if delta <= 60: return f"{d.day} {mesi[d.month-1][:3]}"
    return f"{mesi[d.month-1][:3]} {d.year}"

def merge_consecutive_logs(df):
    if df.empty: return df
    df = df.sort_values(['operatore', 'task_id', 'inizio'])
    merged = []
    curr = df.iloc[0].to_dict()
    for i in range(1, len(df)):
        row = df.iloc[i].to_dict()
        if (row['operatore'] == curr['operatore'] and row['task_id'] == curr['task_id'] and 
            pd.to_datetime(row['inizio']) <= pd.to_datetime(curr['fine']) + timedelta(days=1)):
            curr['fine'] = max(curr['fine'], row['fine'])
        else:
            merged.append(curr)
            curr = row
    merged.append(curr)
    res = pd.DataFrame(merged)
    res['Inizio'] = pd.to_datetime(res['inizio'])
    res['Fine'] = pd.to_datetime(res['fine'])
    res['Durata_ms'] = (res['Fine'] - res['Inizio']).dt.total_seconds() * 1000 + 86400000
    return res

def get_y_label(row, vista_compressa, mappa_emoji, mappa_emoji_task):
    e_cm = mappa_emoji.get(row['stato_commessa'], "⚫")
    e_tk = mappa_emoji_task.get(row.get('stato_task'), "⚫")
    c_label = "<br>".join(textwrap.wrap(f"{e_cm} {row['Commessa']}", 15))
    if vista_compressa:
        return c_label
    else:
        t_label = "<br>".join(textwrap.wrap(f"{e_tk} {row['Task']}", 20))
        return (c_label, t_label)

# --- 4. MODALI ---
@st.dialog("⚙️ Gestione Task e Nuovo Log")
def modal_manage_task_and_log(task_id, data_clic):
    cm_data = get_cached_data("Commesse")
    tk_data = get_cached_data("Task")
    task_info = next((t for t in tk_data if t['id'] == task_id), None)
    if not task_info: st.error("Task non trovato"); return
    
    curr_cm_id = task_info['commessa_id']
    commessa_info = next((c for c in cm_data if c['id'] == curr_cm_id), None)

    st.subheader("🏗️ Modifica Struttura")
    with st.expander("Modifica Nomi e Stati", expanded=False):
        new_tk_name = st.text_input("Nome Task", value=task_info['nome'])
        new_tk_status = st.selectbox("Stato Task", STATI_TASK, index=STATI_TASK.index(task_info.get('stato', STATI_TASK[0])))
        if commessa_info:
            new_cm_name = st.text_input("Nome Commessa", value=commessa_info['nome_commessa'])
            new_cm_status = st.selectbox("Stato Commessa", STATI_COMMESSA, index=STATI_COMMESSA.index(commessa_info.get('stato', STATI_COMMESSA[0])))
        
        if st.button("Salva Modifiche Anagrafiche", use_container_width=True):
            supabase.table("Task").update({"nome": new_tk_name, "stato": new_tk_status}).eq("id", task_id).execute()
            if commessa_info:
                supabase.table("Commesse").update({"nome_commessa": new_cm_name, "stato": new_cm_status}).eq("id", curr_cm_id).execute()
            st.success("Aggiornato!"); get_cached_data.clear(); st.rerun()

    st.divider()
    st.subheader(f"⏱️ Nuovo Log per il {data_clic}")
    ops = [o['nome'] for o in get_cached_data("Operatori")]
    c1, c2 = st.columns(2)
    with c1:
        op_sel = st.selectbox("Operatore", ops)
        d_ini = st.date_input("Inizio", value=data_clic)
    with c2:
        d_fin = st.date_input("Fine", value=data_clic)
        nota = st.text_input("Nota")

    if st.button("Registra Log", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").insert({"task_id": task_id, "operatore": op_sel, "inizio": str(d_ini), "fine": str(d_fin), "note": nota}).execute()
        st.success("Registrato!"); get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()

@st.dialog("⏱️ Modifica Log")
def modal_edit_log(log_id, operatore, inizio, fine, task_id, nota):
    ops = [o['nome'] for o in get_cached_data("Operatori")]
    c1, c2 = st.columns(2)
    with c1:
        new_op = st.selectbox("Operatore", ops, index=ops.index(operatore) if operatore in ops else 0)
        new_ini = st.date_input("Inizio", value=pd.to_datetime(inizio).date())
    with c2:
        new_fin = st.date_input("Fine", value=pd.to_datetime(fine).date())
        new_nota = st.text_input("Nota", value=nota if nota else "")
    
    col_b1, col_b2 = st.columns(2)
    if col_b1.button("Salva", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").update({"operatore": new_op, "inizio": str(new_ini), "fine": str(new_fin), "note": new_nota}).eq("id", log_id).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
    if col_b2.button("Elimina", type="secondary", use_container_width=True):
        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()

# --- 5. LOGICA DATI ---
raw_cm = get_cached_data("Commesse")
raw_tk = get_cached_data("Task")
raw_log = get_cached_data("Log_Tempi")

df_cm = pd.DataFrame(raw_cm)
df_tk = pd.DataFrame(raw_tk)
df_log = pd.DataFrame(raw_log)

if not df_log.empty:
    df = df_log.merge(df_tk[['id', 'nome', 'commessa_id', 'stato']], left_on='task_id', right_on='id', suffixes=('', '_tk'))
    df = df.merge(df_cm[['id', 'nome_commessa', 'stato']], left_on='commessa_id', right_on='id', suffixes=('', '_cm'))
    df = df.rename(columns={'nome': 'Task', 'nome_commessa': 'Commessa', 'stato_cm': 'stato_commessa', 'stato': 'stato_task'})
    if 'note' in df.columns: df['note_html'] = df['note'].fillna('').apply(lambda x: x.replace('\n', '<br>'))
    else: df['note_html'] = ''
else:
    df = pd.DataFrame(columns=['id', 'operatore', 'inizio', 'fine', 'Task', 'Commessa', 'task_id', 'stato_commessa', 'stato_task', 'note_html'])

# --- 6. INTERFACCIA HEADER ---
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 3, 4])
    f_c = c1.multiselect("Progetti", sorted(df['Commessa'].unique()) if not df.empty else [], label_visibility="collapsed", placeholder="Progetti")
    f_o = c2.multiselect("Operatori", sorted(df['operatore'].unique()) if not df.empty else [], label_visibility="collapsed", placeholder="Operatori")
    with c3:
        cs, cd = st.columns(2)
        scala = cs.selectbox("Scala", ["Settimana","2 Settimane", "Mese", "Trimestre", "Semestre", "Personalizzato"], index=1, label_visibility="collapsed")
        f_custom = cd.date_input("Periodo", value=[datetime.now(), datetime.now() + timedelta(days=7)], label_visibility="collapsed") if scala == "Personalizzato" else None
    
    s1, s2, s3 = st.columns([3, 3, 4])
    f_s_cm = s1.multiselect("Stato Commesse", options=STATI_COMMESSA, label_visibility="collapsed", placeholder="Stato Commesse")
    f_s_tk = s2.multiselect("Stato Task", options=STATI_TASK, label_visibility="collapsed", placeholder="Stato Task")
    with s3:
        f_range = st.date_input("Intervallo Date", value=[None, None], format="DD/MM/YYYY", label_visibility="collapsed", placeholder="📅 Tutto il periodo (Clicca per range)")

    b1, b2, b3, b4, b5, b6 = st.columns(6)
    if b4.button("📍 Oggi", use_container_width=True): st.session_state.chart_key += 1; st.rerun()
    label_view = "↔️ Espandi" if st.session_state.vista_compressa else "↕️ Comprimi"
    if b5.button(label_view, use_container_width=True): st.session_state.vista_compressa = not st.session_state.vista_compressa; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 7. FILTRAGGIO ---
df_p = df.copy()
if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]
if f_s_cm: df_p = df_p[df_p['stato_commessa'].isin(f_s_cm)]
if f_s_tk: df_p = df_p[df_p['stato_task'].isin(f_s_tk)]
if f_range and len(f_range) == 2 and all(v is not None for v in f_range):
    df_p = df_p[(pd.to_datetime(df_p['inizio']).dt.date <= f_range[1]) & (pd.to_datetime(df_p['fine']).dt.date >= f_range[0])]

# --- 8. GANTT FRAGMENT ---
@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, oggi_dt, x_range, delta_giorni):
    if df_plot.empty: st.info("Nessun dato."); return
    df_merged = merge_consecutive_logs(df_plot)
    fig = go.Figure()
    
    mappa_emoji = {s: s.split()[-1] for s in STATI_COMMESSA}
    mappa_emoji_task = {s: s.split()[-1] for s in STATI_TASK}
    color_map = {op: f"hsl({(i * 137) % 360}, 50%, 60%)" for i, op in enumerate(df_merged['operatore'].unique())}
    vista = st.session_state.vista_compressa

    # GHOST BARS
    df_tasks = df_merged[['Commessa', 'Task', 'task_id', 'stato_commessa', 'stato_task']].drop_duplicates()
    for _, row_t in df_tasks.iterrows():
        y_val = get_y_label(row_t, vista, mappa_emoji, mappa_emoji_task)
        fig.add_trace(go.Bar(
            base=[x_range[0]], x=[(x_range[1] - x_range[0]).total_seconds() * 1000], y=[y_val],
            orientation='h', marker=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo='none',
            customdata=[["GHOST", row_t['task_id'], row_t['Task']]], width=0.5
        ))

    # LOG BARS
    for op in df_merged['operatore'].unique():
        df_op = df_merged[df_merged['operatore'] == op]
        y_labels = [get_y_label(r, vista, mappa_emoji, mappa_emoji_task) for _, r in df_op.iterrows()]
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], x=df_op['Durata_ms'], y=y_labels, orientation='h', name=op,
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12), width=0.4,
            customdata=[["LOG", r['id'], r['operatore'], r['Inizio'], r['Fine'], r['Commessa'], r['Task'], r['note_html'], r['task_id']] for _, r in df_op.iterrows()],
            hovertemplate="<b>%{customdata[5]} - %{customdata[6]}</b><br>%{customdata[2]}<extra></extra>"
        ))

    # Griglia e Weekend
    all_shapes = []
    curr = x_range[0] - timedelta(days=5)
    while curr <= x_range[1] + timedelta(days=5):
        if curr.weekday() >= 5:
            all_shapes.append(dict(type="rect", x0=curr, x1=curr+timedelta(days=1), y0=0, y1=1, yref="paper", fillcolor="#f0f0f0", opacity=0.3, line_width=0, layer="below"))
        curr += timedelta(days=1)

    fig.update_layout(height=400 + (len(df_tasks) * 25), shapes=all_shapes, barmode='group', xaxis=dict(type="date", range=x_range, side="top"), yaxis=dict(autorange="reversed"))
    fig.add_vline(x=oggi_dt.timestamp() * 1000 + 43200000, line_width=2, line_color="red")
    
    selected = st.plotly_chart(fig, use_container_width=True, key=f"gantt_{st.session_state.chart_key}", on_select="rerun")
    
    if selected and "selection" in selected and selected["selection"]["points"]:
        d = selected["selection"]["points"][0].get("customdata")
        if d:
            if d[0] == "LOG": modal_edit_log(d[1], d[2], d[3], d[4], d[8], d[7])
            elif d[0] == "GHOST": modal_manage_task_and_log(d[1], pd.to_datetime(selected["selection"]["points"][0]["x"]).date())

# Calcolo Range X
oggi_dt = datetime.now()
scale_days = {"Settimana": 7, "2 Settimane": 14, "Mese": 30, "Trimestre": 90, "Semestre": 180}.get(scala, 14)
x_range = [oggi_dt - timedelta(days=2), oggi_dt + timedelta(days=scale_days)]
if scala == "Personalizzato" and f_custom and len(f_custom) == 2:
    x_range = [pd.to_datetime(f_custom[0]), pd.to_datetime(f_custom[1])]

render_gantt_fragment(df_p, oggi_dt, x_range, scale_days)

# --- 9. SETUP TABS (TUA LOGICA ORIGINALE) ---
  
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
