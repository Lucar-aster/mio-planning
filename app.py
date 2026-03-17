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

# --- 4. FUNZIONI UTILITY ORIGINALI ---
def get_it_date_label(d, delta_giorni):
    giorni_it = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    mesi_it = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    if delta_giorni <= 14: return f"{giorni_it[d.weekday()]} {d.day}"
    elif delta_giorni <= 60: return f"{d.day} {mesi_it[d.month-1][:3]}"
    else: return f"{mesi_it[d.month-1][:3]} {d.year}"

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
            merged.append(curr); curr = row
    merged.append(curr)
    res = pd.DataFrame(merged)
    res['Inizio'] = pd.to_datetime(res['inizio'])
    res['Fine'] = pd.to_datetime(res['fine'])
    res['Durata_ms'] = (res['Fine'] - res['Inizio']).dt.total_seconds() * 1000 + 86400000
    return res

def aggiorna_database_setup(table_name, df_new, raw_old):
    df_old = pd.DataFrame(raw_old)
    ids_new = set(df_new['id'].dropna().astype(int)) if 'id' in df_new.columns else set()
    ids_to_del = [int(rid) for rid in df_old['id'] if int(rid) not in ids_new]
    for rid in ids_to_del: supabase.table(table_name).delete().eq("id", rid).execute()
    for _, row in df_new.iterrows():
        item = {k: v for k, v in row.items() if pd.notnull(v)}
        if 'id' in item and item['id'] != "": supabase.table(table_name).upsert(item).execute()
        else:
            if 'id' in item: del item['id']
            supabase.table(table_name).insert(item).execute()
    st.success(f"{table_name} aggiornato!"); get_cached_data.clear(); st.rerun()

# --- 5. NUOVE MODALI (INTEGRATE) ---
@st.dialog("⚙️ Gestione Task / Nuovo Log")
def modal_manage_task_and_log(task_id, data_clic):
    cm_data, tk_data = get_cached_data("Commesse"), get_cached_data("Task")
    task_info = next((t for t in tk_data if t['id'] == task_id), None)
    if not task_info: st.error("Task non trovato"); return
    commessa_info = next((c for c in cm_data if c['id'] == task_info['commessa_id']), None)
    
    st.subheader("🏗️ Modifica Struttura")
    with st.expander("Dettagli Task e Progetto", expanded=False):
        # Cerchiamo dinamicamente il nome del task
        c_n = 'nome' if 'nome' in task_info else ('nome_task' if 'nome_task' in task_info else 'nome')
        new_tk_name = st.text_input("Nome Task", value=task_info.get(c_n, ''))
        new_tk_status = st.selectbox("Stato Task", options=STATI_TASK, index=STATI_TASK.index(task_info.get('stato', STATI_TASK[0])))
        if commessa_info:
            new_cm_name = st.text_input("Nome Commessa", value=commessa_info.get('nome_commessa', ''))
            new_cm_status = st.selectbox("Stato Commessa", options=STATI_COMMESSA, index=STATI_COMMESSA.index(commessa_info.get('stato', STATI_COMMESSA[0])))
        if st.button("Salva Modifiche", use_container_width=True):
            supabase.table("Task").update({c_n: new_tk_name, "stato": new_tk_status}).eq("id", task_id).execute()
            if commessa_info: supabase.table("Commesse").update({"nome_commessa": new_cm_name, "stato": new_cm_status}).eq("id", commessa_info['id']).execute()
            get_cached_data.clear(); st.rerun()
    st.divider()
    st.subheader(f"⏱️ Nuovo Log - {data_clic.strftime('%d/%m/%Y')}")
    ops = [o['nome'] for o in get_cached_data("Operatori")]
    c1, c2 = st.columns(2)
    with c1: 
        op_sel = st.selectbox("Operatore", ops)
        d_ini = st.date_input("Inizio", value=data_clic)
    with c2: 
        nota = st.text_input("Nota")
        d_fin = st.date_input("Fine", value=data_clic)
    if st.button("Registra Log", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").insert({"task_id": task_id, "operatore": op_sel, "inizio": str(d_ini), "fine": str(d_fin), "note": nota}).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()

@st.dialog("⏱️ Modifica Log")
def modal_edit_log(log_id, operatore, inizio, fine, task_id, nota):
    ops_list = [o['nome'] for o in get_cached_data("Operatori")]
    c1, c2 = st.columns(2)
    with c1: 
        new_op = st.selectbox("Operatore", ops_list, index=ops_list.index(operatore) if operatore in ops_list else 0)
        new_ini = st.date_input("Inizio", value=pd.to_datetime(inizio).date())
    with c2: 
        new_fin = st.date_input("Fine", value=pd.to_datetime(fine).date())
        new_nota = st.text_input("Nota", value=nota if nota else "")
    cb1, cb2 = st.columns(2)
    if cb1.button("Salva", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").update({"operatore": new_op, "inizio": str(new_ini), "fine": str(new_fin), "note": new_nota}).eq("id", log_id).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
    if cb2.button("Elimina", type="secondary", use_container_width=True):
        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()

# --- 6. LOGICA DATI ---
raw_cm, raw_tk, raw_log = get_cached_data("Commesse"), get_cached_data("Task"), get_cached_data("Log_Tempi")
df_cm, df_tk, df_log = pd.DataFrame(raw_cm), pd.DataFrame(raw_tk), pd.DataFrame(raw_log)

if not df_log.empty and not df_tk.empty:
    # --- FIX CRUCIALE PER IL TUO ERRORE ---
    # Cerchiamo come si chiama la colonna del nome nei task
    col_nome_effettiva = 'nome' if 'nome' in df_tk.columns else ('nome_task' if 'nome_task' in df_tk.columns else None)
    
    if col_nome_effettiva:
        df = df_log.merge(df_tk[['id', col_nome_effettiva, 'commessa_id', 'stato']], left_on='task_id', right_on='id', suffixes=('', '_tk'))
        if not df_cm.empty:
            df = df.merge(df_cm[['id', 'nome_commessa', 'stato']], left_on='commessa_id', right_on='id', suffixes=('', '_cm'))
            df = df.rename(columns={col_nome_effettiva: 'Task', 'nome_commessa': 'Commessa', 'stato_cm': 'stato_commessa', 'stato': 'stato_task'})
            df['note_html'] = df['note'].fillna('').apply(lambda x: str(x).replace('\n', '<br>'))
    else:
        st.error("Colonna 'nome' non trovata nella tabella Task. Controlla il DB.")
        df = pd.DataFrame()
else:
    df = pd.DataFrame(columns=['id', 'operatore', 'inizio', 'fine', 'Task', 'Commessa', 'task_id', 'stato_commessa', 'stato_task', 'note_html'])

# --- 7. UI E FILTRI ---
st.markdown("<style>.fixed-header { position: sticky; top: 0; background-color: white; z-index: 999; padding: 10px 0; border-bottom: 1px solid #ddd; }</style>", unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 3, 4])
    f_c = c1.multiselect("Progetti", sorted(df['Commessa'].unique()) if not df.empty else [], label_visibility="collapsed", placeholder="Progetti")
    f_o = c2.multiselect("Operatori", sorted(df['operatore'].unique()) if not df.empty else [], label_visibility="collapsed", placeholder="Operatori")
    with c3:
        cc1, cc2 = st.columns(2)
        scala = cc1.selectbox("Scala", ["Settimana", "2 Settimane", "Mese", "Trimestre", "Semestre", "Personalizzato"], index=1, label_visibility="collapsed")
        f_custom = cc2.date_input("Periodo", value=[], label_visibility="collapsed") if scala == "Personalizzato" else None
    s1, s2, s3 = st.columns([3, 3, 4])
    f_s_cm = s1.multiselect("Stato Commesse", options=STATI_COMMESSA, label_visibility="collapsed", placeholder="Stato Commesse")
    f_s_tk = s2.multiselect("Stato Task", options=STATI_TASK, label_visibility="collapsed", placeholder="Stato Task")
    with s3: f_range = st.date_input("Intervallo Date", value=[], format="DD/MM/YYYY", label_visibility="collapsed")
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    if b4.button("📍 Oggi", use_container_width=True): st.session_state.chart_key += 1; st.rerun()
    lv = "↔️ Espandi" if st.session_state.vista_compressa else "↕️ Comprimi"
    if b5.button(lv, use_container_width=True): st.session_state.vista_compressa = not st.session_state.vista_compressa; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

df_p = df.copy()
if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]
if f_s_cm: df_p = df_p[df_p['stato_commessa'].isin(f_s_cm)]
if f_s_tk: df_p = df_p[df_p['stato_task'].isin(f_s_tk)]
if f_range and len(f_range) == 2: df_p = df_p[(pd.to_datetime(df_p['inizio']).dt.date <= f_range[1]) & (pd.to_datetime(df_p['fine']).dt.date >= f_range[0])]

# --- 8. TABS (SOPRA IL GRAFICO COME ORIGINALE) ---
tabs = st.tabs(["📊 Gantt", "📅 Calendario", "🏢 Setup", "📋 Task Setup", "📈 Stats"])

with tabs[0]:
    @st.fragment(run_every=60)
    def render_gantt_fragment(df_plot, oggi_dt, x_range):
        if df_plot.empty: st.info("Nessun dato."); return
        df_merged = merge_consecutive_logs(df_plot)
        fig = go.Figure()
        mappa_emoji = {s: s.split()[-1] for s in STATI_COMMESSA}
        mappa_emoji_task = {s: s.split()[-1] for s in STATI_TASK}
        color_map = {op: f"hsl({(i * 137) % 360}, 50%, 60%)" for i, op in enumerate(df_merged['operatore'].unique())}
        df_tasks = df_merged[['Commessa', 'Task', 'task_id', 'stato_commessa', 'stato_task']].drop_duplicates()

        # Ghost Bars per il clic
        for _, row_t in df_tasks.iterrows():
            ecm, etk = mappa_emoji.get(row_t['stato_commessa'], "⚫"), mappa_emoji_task.get(row_t.get('stato_task'), "⚫")
            cl = "<br>".join(textwrap.wrap(f"{ecm} {row_t['Commessa']}", 15))
            yv = cl if st.session_state.vista_compressa else (cl, "<br>".join(textwrap.wrap(f"{etk} {row_t['Task']}", 20)))
            fig.add_trace(go.Bar(base=[x_range[0]], x=[(x_range[1]-x_range[0]).total_seconds()*1000], y=[yv], orientation='h', marker=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo='none', customdata=[["GHOST", row_t['task_id']]], width=0.5))

        # Log Bars
        for op in df_merged['operatore'].unique():
            df_op = df_merged[df_merged['operatore'] == op]
            y_labs = []
            for _, r in df_op.iterrows():
                ecm, etk = mappa_emoji.get(r['stato_commessa'], "⚫"), mappa_emoji_task.get(r.get('stato_task'), "⚫")
                cl = "<br>".join(textwrap.wrap(f"{ecm} {r['Commessa']}", 15))
                y_labs.append(cl if st.session_state.vista_compressa else (cl, "<br>".join(textwrap.wrap(f"{etk} {r['Task']}", 20))))
            fig.add_trace(go.Bar(base=df_op['Inizio'], x=df_op['Durata_ms'], y=y_labs, orientation='h', name=op, marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12), width=0.4,
                customdata=[["LOG", r['id'], r['operatore'], r['Inizio'], r['Fine'], r['Commessa'], r['Task'], r['note_html'], r['task_id']] for _, r in df_op.iterrows()],
                hovertemplate="<b>%{customdata[5]} - %{customdata[6]}</b><br>%{customdata[2]}<extra></extra>"))

        fig.update_layout(height=400+(len(df_tasks)*30), barmode='group', xaxis=dict(type="date", range=x_range, side="top"), yaxis=dict(autorange="reversed"), showlegend=False, margin=dict(l=10, r=10, t=40, b=0))
        fig.add_vline(x=oggi_dt.timestamp()*1000+43200000, line_width=2, line_color="red")
        
        # Weekend
        c = x_range[0] - timedelta(days=5)
        while c <= x_range[1] + timedelta(days=5):
            if c.weekday() >= 5: fig.add_vrect(x0=c, x1=c+timedelta(days=1), fillcolor="#f0f0f0", opacity=0.3, layer="below", line_width=0)
            c += timedelta(days=1)

        sel = st.plotly_chart(fig, use_container_width=True, key=f"gantt_{st.session_state.chart_key}", on_select="rerun", config={'displayModeBar': False})
        if sel and "selection" in sel and sel["selection"]["points"]:
            pt = sel["selection"]["points"][0]
            if "customdata" in pt:
                d = pt["customdata"]
                if d[0] == "LOG": modal_edit_log(d[1], d[2], d[3], d[4], d[8], d[7])
                elif d[0] == "GHOST": modal_manage_task_and_log(d[1], pd.to_datetime(pt["x"]).date())

    odt = datetime.now()
    dg = {"Settimana": 7, "2 Settimane": 14, "Mese": 30, "Trimestre": 90, "Semestre": 180}.get(scala, 14)
    xr = [odt - timedelta(days=2), odt + timedelta(days=dg)]
    if scala == "Personalizzato" and f_custom and len(f_custom) == 2: xr = [pd.to_datetime(f_custom[0]), pd.to_datetime(f_custom[1])]
    render_gantt_fragment(df_p, odt, xr)

with tabs[1]:
    if not df_p.empty:
        cal_evs = [{"id": r['id'], "title": f"{r['operatore']} - {r['Task']}", "start": r['inizio'], "end": r['fine'], "allDay": True} for _, r in df_p.iterrows()]
        calendar(events=cal_evs, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"}}, key="cal_v7")

with tabs[2]:
    st.subheader("🏢 Gestione Commesse")
    ecm = st.data_editor(df_cm, column_config={"id": None, "stato": st.column_config.SelectboxColumn("Stato", options=STATI_COMMESSA)}, num_rows="dynamic", hide_index=True, key="ed_cm_v7")
    if st.button("Salva Commesse"): aggiorna_database_setup("Commesse", ecm, raw_cm)

with tabs[3]:
    st.subheader("📋 Gestione Task")
    if not df_tk.empty and not df_cm.empty:
        n2id = {c['nome_commessa']: c['id'] for c in raw_cm}
        dftk_s = df_tk.copy()
        # Fix colonna nome per il setup
        c_n_s = 'nome' if 'nome' in dftk_s.columns else 'nome_task'
        dftk_s['commessa_nome'] = dftk_s['commessa_id'].map({c['id']: c['nome_commessa'] for c in raw_cm})
        etk = st.data_editor(dftk_s, column_config={"id": None, "commessa_id": None, "commessa_nome": st.column_config.SelectboxColumn("Commessa", options=list(n2id.keys())), "stato": st.column_config.SelectboxColumn("Stato", options=STATI_TASK)}, num_rows="dynamic", hide_index=True, key="ed_tk_v7")
        if st.button("Salva Task"):
            dfs = etk.copy(); dfs['commessa_id'] = dfs['commessa_nome'].map(n2id)
            aggiorna_database_setup("Task", dfs.drop(columns=['commessa_nome']), raw_tk)

with tabs[4]:
    if not df_p.empty:
        c1, c2 = st.columns(2)
        c1.bar_chart(df_p['operatore'].value_counts())
        c2.bar_chart(df_p['stato_commessa'].value_counts())
