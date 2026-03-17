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
    if delta_giorni <= 14:
        return f"{giorni_it[d.weekday()]} {d.day}"
    elif delta_giorni <= 60:
        return f"{d.day} {mesi_it[d.month-1][:3]}"
    else:
        return f"{mesi_it[d.month-1][:3]} {d.year}"

def merge_consecutive_logs(df):
    if df.empty: return df
    df = df.sort_values(['operatore', 'task_id', 'inizio'])
    merged = []
    curr = df.iloc[0].to_dict()
    for i in range(1, len(df)):
        row = df.iloc[i].to_dict()
        if (row['operatore'] == curr['operatore'] and 
            row['task_id'] == curr['task_id'] and 
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

def aggiorna_database_setup(table_name, df_new, raw_old):
    df_old = pd.DataFrame(raw_old)
    ids_new = set(df_new['id'].dropna().astype(int)) if 'id' in df_new.columns else set()
    ids_to_del = [int(rid) for rid in df_old['id'] if int(rid) not in ids_new]
    for rid in ids_to_del:
        supabase.table(table_name).delete().eq("id", rid).execute()
    for _, row in df_new.iterrows():
        item = {k: v for k, v in row.items() if pd.notnull(v)}
        if 'id' in item and item['id'] != "":
            supabase.table(table_name).upsert(item).execute()
        else:
            if 'id' in item: del item['id']
            supabase.table(table_name).insert(item).execute()
    st.success(f"Database {table_name} aggiornato!")
    get_cached_data.clear()
    st.rerun()

# --- 5. MODALI ---
@st.dialog("⚙️ Gestione Task e Nuovo Log")
def modal_manage_task_and_log(task_id, data_clic):
    cm_data = get_cached_data("Commesse")
    tk_data = get_cached_data("Task")
    task_info = next((t for t in tk_data if t['id'] == task_id), None)
    if not task_info: st.error("Task non trovato"); return
    commessa_info = next((c for c in cm_data if c['id'] == task_info['commessa_id']), None)

    st.subheader("🏗️ Modifica Nomi e Stati")
    with st.expander("Modifica Anagrafica", expanded=False):
        new_tk_name = st.text_input("Nome Task", value=task_info.get('nome', ''))
        new_tk_status = st.selectbox("Stato Task", options=STATI_TASK, index=STATI_TASK.index(task_info.get('stato', STATI_TASK[0])))
        if commessa_info:
            new_cm_name = st.text_input("Nome Commessa", value=commessa_info.get('nome_commessa', ''))
            new_cm_status = st.selectbox("Stato Commessa", options=STATI_COMMESSA, index=STATI_COMMESSA.index(commessa_info.get('stato', STATI_COMMESSA[0])))
        if st.button("Salva Modifiche", use_container_width=True):
            supabase.table("Task").update({"nome": new_tk_name, "stato": new_tk_status}).eq("id", task_id).execute()
            if commessa_info:
                supabase.table("Commesse").update({"nome_commessa": new_cm_name, "stato": new_cm_status}).eq("id", commessa_info['id']).execute()
            get_cached_data.clear(); st.rerun()

    st.divider()
    st.subheader(f"⏱️ Nuovo Log - {data_clic.strftime('%d/%m/%Y')}")
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
    col_b1, col_b2 = st.columns(2)
    if col_b1.button("Salva", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").update({"operatore": new_op, "inizio": str(new_ini), "fine": str(new_fin), "note": new_nota}).eq("id", log_id).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()
    if col_b2.button("Elimina", type="secondary", use_container_width=True):
        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
        get_cached_data.clear(); st.session_state.chart_key += 1; st.rerun()

# --- 6. LOGICA DATI (CORRETTA) ---
raw_cm = get_cached_data("Commesse")
raw_tk = get_cached_data("Task")
raw_log = get_cached_data("Log_Tempi")

df_cm = pd.DataFrame(raw_cm)
df_tk = pd.DataFrame(raw_tk)
df_log = pd.DataFrame(raw_log)

# Verifichiamo che i DataFrame non siano vuoti e contengano le colonne necessarie
if not df_log.empty and not df_tk.empty and not df_cm.empty:
    
    # Identifichiamo dinamicamente la colonna del nome nel task
    # (cerca 'nome', se non esiste cerca 'nome_task')
    col_nome_task = 'nome' if 'nome' in df_tk.columns else ('nome_task' if 'nome_task' in df_tk.columns else None)
    
    if col_nome_task is None:
        st.error("Errore: La tabella 'Task' non contiene una colonna 'nome' o 'nome_task'. Controlla il DB.")
        df = pd.DataFrame()
    else:
        # Eseguiamo il merge usando la colonna trovata
        df = df_log.merge(
            df_tk[['id', col_nome_task, 'commessa_id', 'stato']], 
            left_on='task_id', 
            right_on='id', 
            suffixes=('', '_tk')
        )
        df = df.merge(
            df_cm[['id', 'nome_commessa', 'stato']], 
            left_on='commessa_id', 
            right_on='id', 
            suffixes=('', '_cm')
        )
        
        # Rinominiamo per uniformità nel resto del codice
        df = df.rename(columns={
            col_nome_task: 'Task', 
            'nome_commessa': 'Commessa', 
            'stato_cm': 'stato_commessa', 
            'stato': 'stato_task'
        })
        df['note_html'] = df['note'].fillna('').apply(lambda x: str(x).replace('\n', '<br>'))
else:
    # DataFrame vuoto di emergenza per non rompere i filtri UI
    df = pd.DataFrame(columns=['id', 'operatore', 'inizio', 'fine', 'Task', 'Commessa', 'task_id', 'stato_commessa', 'stato_task', 'note_html'])

# --- 7. CSS E HEADER ---
st.markdown("<style>.fixed-header { position: sticky; top: 0; background-color: white; z-index: 999; padding: 10px 0; border-bottom: 1px solid #ddd; }</style>", unsafe_allow_html=True)
with st.container():
    st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([3, 3, 4])
    f_c = c1.multiselect("Progetti", sorted(df['Commessa'].unique()) if not df.empty else [], label_visibility="collapsed", placeholder="Progetti")
    f_o = c2.multiselect("Operatori", sorted(df['operatore'].unique()) if not df.empty else [], label_visibility="collapsed", placeholder="Operatori")
    with c3:
        cc1, cc2 = st.columns(2)
        scala = cc1.selectbox("Scala", ["Settimana", "2 Settimane", "Mese", "Trimestre", "Semestre", "Personalizzato"], index=1, label_visibility="collapsed")
        f_custom = cc2.date_input("Periodo", value=[datetime.now(), datetime.now() + timedelta(days=7)], label_visibility="collapsed") if scala == "Personalizzato" else None
    s1, s2, s3 = st.columns([3, 3, 4])
    f_s_cm = s1.multiselect("Stato Commesse", options=STATI_COMMESSA, label_visibility="collapsed", placeholder="Stato Commesse")
    f_s_tk = s2.multiselect("Stato Task", options=STATI_TASK, label_visibility="collapsed", placeholder="Stato Task")
    with s3:
        f_range = st.date_input("Intervallo Date", value=[], format="DD/MM/YYYY", label_visibility="collapsed")
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    if b4.button("📍 Oggi", use_container_width=True): st.session_state.chart_key += 1; st.rerun()
    label_v = "↔️ Espandi" if st.session_state.vista_compressa else "↕️ Comprimi"
    if b5.button(label_v, use_container_width=True): st.session_state.vista_compressa = not st.session_state.vista_compressa; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- 8. FILTRAGGIO ---
df_p = df.copy()
if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]
if f_s_cm: df_p = df_p[df_p['stato_commessa'].isin(f_s_cm)]
if f_s_tk: df_p = df_p[df_p['stato_task'].isin(f_s_tk)]
if f_range and len(f_range) == 2:
    df_p = df_p[(pd.to_datetime(df_p['inizio']).dt.date <= f_range[1]) & (pd.to_datetime(df_p['fine']).dt.date >= f_range[0])]

# --- 9. GANTT ---
@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, oggi_dt, x_range):
    if df_plot.empty: st.info("Nessun dato."); return
    df_merged = merge_consecutive_logs(df_plot)
    fig = go.Figure()
    mappa_emoji = {s: s.split()[-1] for s in STATI_COMMESSA}
    mappa_emoji_task = {s: s.split()[-1] for s in STATI_TASK}
    color_map = {op: f"hsl({(i * 137) % 360}, 50%, 60%)" for i, op in enumerate(df_merged['operatore'].unique())}
    df_tasks = df_merged[['Commessa', 'Task', 'task_id', 'stato_commessa', 'stato_task']].drop_duplicates()

    for _, row_t in df_tasks.iterrows():
        e_cm, e_tk = mappa_emoji.get(row_t['stato_commessa'], "⚫"), mappa_emoji_task.get(row_t.get('stato_task'), "⚫")
        c_l = "<br>".join(textwrap.wrap(f"{e_cm} {row_t['Commessa']}", 15))
        y_val = c_l if st.session_state.vista_compressa else (c_l, "<br>".join(textwrap.wrap(f"{e_tk} {row_t['Task']}", 20)))
        fig.add_trace(go.Bar(base=[x_range[0]], x=[(x_range[1] - x_range[0]).total_seconds() * 1000], y=[y_val], orientation='h', marker=dict(color="rgba(0,0,0,0)"), showlegend=False, hoverinfo='none', customdata=[["GHOST", row_t['task_id']]], width=0.5))

    for op in df_merged['operatore'].unique():
        df_op = df_merged[df_merged['operatore'] == op]
        y_labels = []
        for _, r in df_op.iterrows():
            e_cm, e_tk = mappa_emoji.get(r['stato_commessa'], "⚫"), mappa_emoji_task.get(r.get('stato_task'), "⚫")
            c_l = "<br>".join(textwrap.wrap(f"{e_cm} {r['Commessa']}", 15))
            y_labels.append(c_l if st.session_state.vista_compressa else (c_l, "<br>".join(textwrap.wrap(f"{e_tk} {r['Task']}", 20))))
        fig.add_trace(go.Bar(base=df_op['Inizio'], x=df_op['Durata_ms'], y=y_labels, orientation='h', name=op, marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12), width=0.4,
            customdata=[["LOG", r['id'], r['operatore'], r['Inizio'], r['Fine'], r['Commessa'], r['Task'], r['note_html'], r['task_id']] for _, r in df_op.iterrows()],
            hovertemplate="<b>%{customdata[5]} - %{customdata[6]}</b><br>%{customdata[2]}<extra></extra>"))

    all_shapes = []
    curr = x_range[0] - timedelta(days=5)
    while curr <= x_range[1] + timedelta(days=5):
        if curr.weekday() >= 5: all_shapes.append(dict(type="rect", x0=curr, x1=curr+timedelta(days=1), y0=0, y1=1, yref="paper", fillcolor="#f0f0f0", opacity=0.3, line_width=0, layer="below"))
        curr += timedelta(days=1)

    fig.update_layout(height=400 + (len(df_tasks) * 28), shapes=all_shapes, barmode='group', xaxis=dict(type="date", range=x_range, side="top"), yaxis=dict(autorange="reversed"), showlegend=False, margin=dict(l=10, r=10, t=40, b=0))
    fig.add_vline(x=oggi_dt.timestamp() * 1000 + 43200000, line_width=2, line_color="red")
    selected = st.plotly_chart(fig, use_container_width=True, key=f"gantt_{st.session_state.chart_key}", on_select="rerun", config={'displayModeBar': False})
    
    if selected and "selection" in selected and selected["selection"]["points"]:
        pt = selected["selection"]["points"][0]
        if "customdata" in pt:
            d = pt["customdata"]
            if d[0] == "LOG": modal_edit_log(d[1], d[2], d[3], d[4], d[8], d[7])
            elif d[0] == "GHOST": modal_manage_task_and_log(d[1], pd.to_datetime(pt["x"]).date())

oggi_dt = datetime.now()
delta_g = {"Settimana": 7, "2 Settimane": 14, "Mese": 30, "Trimestre": 90, "Semestre": 180}.get(scala, 14)
x_r = [oggi_dt - timedelta(days=2), oggi_dt + timedelta(days=delta_g)]
if scala == "Personalizzato" and f_custom and len(f_custom) == 2: x_r = [pd.to_datetime(f_custom[0]), pd.to_datetime(f_custom[1])]
render_gantt_fragment(df_p, oggi_dt, x_r)

# --- 10. TABS ---
tabs = st.tabs(["📊 Gantt", "📅 Calendario", "🏢 Setup", "📋 Task Setup", "📈 Stats"])
with tabs[1]:
    if not df_p.empty:
        cal_ev = [{"id": r['id'], "title": f"{r['operatore']} - {r['Task']}", "start": r['inizio'], "end": r['fine'], "allDay": True} for _, r in df_p.iterrows()]
        calendar(events=cal_ev, options={"headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"}}, key="cal_v7")

with tabs[2]:
    st.subheader("🏢 Gestione Commesse")
    ed_cm = st.data_editor(df_cm, column_config={"id": None, "stato": st.column_config.SelectboxColumn("Stato", options=STATI_COMMESSA)}, num_rows="dynamic", hide_index=True, key="ed_cm_v7")
    if st.button("Salva Commesse", key="btn_cm_v7"): aggiorna_database_setup("Commesse", ed_cm, raw_cm)

with tabs[3]:
    st.subheader("📋 Gestione Task")
    if not df_tk.empty and not df_cm.empty:
        name_to_id = {c['nome_commessa']: c['id'] for c in raw_cm}
        df_tk_setup = df_tk.copy()
        df_tk_setup['commessa_nome'] = df_tk_setup['commessa_id'].map({c['id']: c['nome_commessa'] for c in raw_cm})
        ed_tk = st.data_editor(df_tk_setup, column_config={"id": None, "commessa_id": None, "commessa_nome": st.column_config.SelectboxColumn("Commessa", options=list(name_to_id.keys())), "stato": st.column_config.SelectboxColumn("Stato", options=STATI_TASK)}, num_rows="dynamic", hide_index=True, key="ed_tk_v7")
        if st.button("Salva Task", key="btn_tk_v7"):
            df_save = ed_tk.copy()
            df_save['commessa_id'] = df_save['commessa_nome'].map(name_to_id)
            aggiorna_database_setup("Task", df_save.drop(columns=['commessa_nome']), raw_tk)

with tabs[4]:
    if not df_p.empty:
        c1, c2 = st.columns(2)
        c1.bar_chart(df_p.groupby('operatore').size())
        c2.pie_chart(df_p.groupby('stato_commessa').size())
