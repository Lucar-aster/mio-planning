import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import textwrap

# --- 1. CONFIGURAZIONE PAGINA E COSTANTI ---
LOGO_URL = "https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png"
st.set_page_config(page_title="Aster Contract", page_icon=LOGO_URL, layout="wide")

STATI_COMMESSA = ["Quotazione 🟣", "Pianificata 🔵", "In corso 🟡", "Completata 🟢", "Sospesa 🟠", "Cancellata 🔴"]
STATI_TASK = ["Pianificato 🔵", "In corso 🟡", "Completato 🟢", "Sospeso 🟠"]

# --- 2. CONNESSIONE SUPABASE E CACHING ---
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=60)
def get_cached_data(table_name):
    try:
        res = supabase.table(table_name).select("*").execute()
        return res.data
    except Exception as e:
        st.error(f"Errore caricamento {table_name}: {e}")
        return []

# Inizializzazione Session State
if 'chart_key' not in st.session_state: st.session_state.chart_key = 0
if 'vista_compressa' not in st.session_state: st.session_state.vista_compressa = False

# --- 3. CSS PERSONALIZZATO (Legende e Header) ---
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ visibility: hidden; height: 0px; }}
    .block-container {{ padding-top: 1rem !important; }}
    
    .compact-header {{ display: flex; align-items: center; justify-content: space-between; gap: 20px; margin-bottom: 10px; }}
    .title-area {{ display: flex; align-items: center; gap: 10px; min-width: 250px; }}
    .title-area h1 {{ font-size: 22px !important; margin: 0; color: #1E3A8A; white-space: nowrap; }}

    /* Container Legenda Orizzontale */
    .legend-container {{
        display: flex; flex-wrap: nowrap; gap: 8px; align-items: center;
        font-size: 11px; color: #444; overflow-x: auto; white-space: nowrap;
        padding: 5px 10px; background: #f8f9fa; border-radius: 10px; border: 1px solid #eee;
    }}
    .legend-pill {{
        display: flex; align-items: center; gap: 4px;
        background: white; padding: 2px 8px; border-radius: 20px; border: 1px solid #ddd;
    }}
    .dot {{ height: 8px; width: 8px; border-radius: 50%; display: inline-block; }}
    </style>
""", unsafe_allow_html=True)

# --- 4. HEADER DINAMICO ---
col_h1, col_h2 = st.columns([1, 4])
with col_h1:
    st.markdown(f"""
        <div class="title-area">
            <img src="{LOGO_URL}" width="35">
            <h1>Aster Planning</h1>
        </div>
    """, unsafe_allow_html=True)

with col_h2:
    # Recupero dati per legende
    ops_data = get_cached_data("Operatori")
    op_html = "".join([f'<div class="legend-pill"><span class="dot" style="background-color:{o.get("colore", "#8dbad2")}"></span>{o["nome"]}</div>' for o in ops_data])
    cm_html = "".join([f'<div class="legend-pill">{s}</div>' for s in STATI_COMMESSA])
    tk_html = "".join([f'<div class="legend-pill">{s}</div>' for s in STATI_TASK])
    
    st.markdown(f"""
        <div class="legend-container">
            <span style="font-weight:bold; color:#888;">👤 OPERATORI:</span> {op_html}
            <span style="border-left:1px solid #ccc; height:15px; margin:0 5px;"></span>
            <span style="font-weight:bold; color:#888;">🏗️ PROGETTI:</span> {cm_html}
            <span style="border-left:1px solid #ccc; height:15px; margin:0 5px;"></span>
            <span style="font-weight:bold; color:#888;">📋 TASK:</span> {tk_html}
        </div>
    """, unsafe_allow_html=True)

# --- 5. FUNZIONI LOGICHE ---

def merge_consecutive_logs(df):
    if df.empty: return df
    df = df.sort_values(['operatore', 'Commessa', 'Task', 'Inizio'])
    merged = []
    for (op, comm, task), group in df.groupby(['operatore', 'Commessa', 'Task']):
        current_row = None
        for _, row in group.iterrows():
            nota_testo = str(row['note']).strip() if pd.notnull(row['note']) and str(row['note']).strip() != "" else ""
            nota_f = f"• <i>{row['Inizio'].strftime('%d/%m')}</i>: {nota_testo}" if nota_testo else ""
            if current_row is None:
                current_row = row.to_dict()
                current_row['note_html'] = nota_f
            else:
                if row['Inizio'] <= (pd.to_datetime(current_row['Fine']) + timedelta(days=1)):
                    current_row['Fine'] = max(pd.to_datetime(current_row['Fine']), pd.to_datetime(row['Fine']))
                    current_row['Durata_ms'] = ((pd.to_datetime(current_row['Fine']) + timedelta(days=1)) - pd.to_datetime(current_row['Inizio'])).total_seconds() * 1000
                    if nota_f: current_row['note_html'] = (current_row['note_html'] + "<br>" + nota_f).strip("<br>")
                else:
                    merged.append(current_row); current_row = row.to_dict(); current_row['note_html'] = nota_f
        if current_row: merged.append(current_row)
    return pd.DataFrame(merged)

def aggiorna_database_setup(tabella, df_nuovo, df_vecchio):
    ids_nuovi = set(df_nuovo['id'].dropna()) if 'id' in df_nuovo.columns else set()
    ids_vecchi = set(pd.DataFrame(df_vecchio)['id']) if df_vecchio else set()
    to_del = ids_vecchi - ids_nuovi
    for i in to_del: supabase.table(tabella).delete().eq("id", i).execute()
    for _, row in df_nuovo.iterrows():
        d = row.dropna().to_dict()
        if pd.notnull(row.get('id')): supabase.table(tabella).update(d).eq("id", row['id']).execute()
        else: supabase.table(tabella).insert(d).execute()
    get_cached_data.clear(); st.success(f"{tabella} Aggiornato!"); st.rerun()

# --- 6. MODALI ---

@st.dialog("📝 Modifica Log")
def modal_edit_log(log_id, op_nome, inizio, fine, task_id, note_html):
    st.write(f"Log di: **{op_nome}**")
    c1, c2 = st.columns(2)
    ni, nf = c1.date_input("Inizio", pd.to_datetime(inizio)), c2.date_input("Fine", pd.to_datetime(fine))
    st.markdown(f"<div style='font-size:12px; color:gray;'>{note_html}</div>", unsafe_allow_html=True)
    if st.button("🗑️ Elimina", use_container_width=True):
        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
        get_cached_data.clear(); st.rerun()
    if st.button("💾 Salva", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").update({"inizio": str(ni), "fine": str(nf)}).eq("id", log_id).execute()
        get_cached_data.clear(); st.rerun()

@st.dialog("🏗️ Nuova Commessa")
def modal_commessa():
    n = st.text_input("Nome Progetto")
    s = st.selectbox("Stato", STATI_COMMESSA)
    if st.button("Salva"):
        supabase.table("Commesse").insert({"nome_commessa": n, "stato_commessa": s}).execute()
        get_cached_data.clear(); st.rerun()

@st.dialog("📋 Nuovo Task")
def modal_task():
    cms = get_cached_data("Commesse")
    sel = st.selectbox("Progetto", [c['nome_commessa'] for c in cms])
    nt = st.text_input("Nome Task")
    if st.button("Crea"):
        cid = next(c['id'] for c in cms if c['nome_commessa'] == sel)
        supabase.table("Task").insert({"nome_task": nt, "commessa_id": cid, "stato": STATI_TASK[0]}).execute()
        get_cached_data.clear(); st.rerun()

@st.dialog("⏱️ Registra Log")
def modal_log():
    cms, tks = get_cached_data("Commesse"), get_cached_data("Task")
    ops = [o['nome'] for o in get_cached_data("Operatori")]
    o_sel = st.multiselect("Operatori", ops)
    c_sel = st.selectbox("Progetto", [c['nome_commessa'] for c in cms])
    cid = next(c['id'] for c in cms if c['nome_commessa'] == c_sel)
    t_f = [t for t in tks if t['commessa_id'] == cid]
    t_sel = st.selectbox("Task", [t['nome_task'] for t in t_f] + ["➕ Nuovo..."])
    nota = st.text_area("Note")
    if st.button("Registra"):
        tid = None
        if t_sel == "➕ Nuovo...":
            res = supabase.table("Task").insert({"nome_task": "Nuovo Task", "commessa_id": cid, "stato": STATI_TASK[0]}).execute()
            tid = res.data[0]['id']
        else: tid = next(t['id'] for t in t_f if t['nome_task'] == t_sel)
        for o in o_sel:
            supabase.table("Log_Tempi").insert({"operatore": o, "task_id": tid, "inizio": str(datetime.now().date()), "fine": str(datetime.now().date()), "note": nota}).execute()
        get_cached_data.clear(); st.rerun()

# --- 7. FRAGMENT GANTT ---

@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, color_map, oggi_dt, x_range):
    if df_plot.empty: st.info("Nessun dato."); return
    df_m = merge_consecutive_logs(df_plot)
    fig = go.Figure()
    m_cm = {s: s.split()[-1] for s in STATI_COMMESSA}
    m_tk = {s: s.split()[-1] for s in STATI_TASK}

    for op in df_m['operatore'].unique():
        df_op = df_m[df_m['operatore'] == op]
        y_labels = []
        for _, r in df_op.iterrows():
            e_c, e_t = m_cm.get(r['stato_commessa'], "🏗️"), m_tk.get(r['stato_task'], "📋")
            l_c = "<br>".join(textwrap.wrap(f"{e_c} {r['Commessa']}", 15))
            l_t = "<br>".join(textwrap.wrap(f"{e_t} {r['Task']}", 20))
            y_labels.append(l_c if st.session_state.vista_compressa else [l_c, l_t])

        y_axis = y_labels if st.session_state.vista_compressa else list(zip(*y_labels))
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], x=df_op['Durata_ms'], y=y_axis, orientation='h', name=op,
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12),
            width=0.7 if st.session_state.vista_compressa else 0.4,
            customdata=list(zip(df_op['id'], df_op['operatore'], df_op['Inizio'], df_op['Fine'], df_op['Commessa'], df_op['Task'], df_op['note_html'], df_op['task_id'])),
            hovertemplate="<b>%{customdata[4]}</b><br>%{customdata[5]}<extra></extra>"
        ))

    n_r = len(df_m['Commessa'].unique()) if st.session_state.vista_compressa else len(df_m[['Commessa', 'Task']].drop_duplicates())
    fig.update_layout(
        height=200 + (n_r * (45 if st.session_state.vista_compressa else 30)),
        showlegend=False, barmode='overlay' if st.session_state.vista_compressa else 'group',
        margin=dict(l=10, r=10, t=40, b=0), xaxis=dict(type="date", side="top", range=x_range, gridcolor="#eee"),
        yaxis=dict(autorange="reversed", showgrid=True, fixedrange=True), plot_bgcolor="white"
    )
    fig.add_vline(x=oggi_dt.timestamp() * 1000 + 43200000, line_width=2, line_color="red", line_dash="dot")
    sel = st.plotly_chart(fig, use_container_width=True, key=f"gantt_{st.session_state.chart_key}", on_select="rerun", config={'displayModeBar': False})
    if sel and "selection" in sel and sel["selection"]["points"]:
        d = sel["selection"]["points"][0]["customdata"]
        modal_edit_log(d[0], d[1], d[2], d[3], d[7], d[6])

# --- 8. CARICAMENTO E UI ---

data_log, data_tk, data_cm, data_op = get_cached_data("Log_Tempi"), get_cached_data("Task"), get_cached_data("Commesse"), get_cached_data("Operatori")

if data_log and data_tk and data_cm:
    df = pd.DataFrame(data_log).merge(pd.DataFrame(data_tk), left_on="task_id", right_on="id", suffixes=('', '_tk'))
    df = df.merge(pd.DataFrame(data_cm), left_on="commessa_id", right_on="id", suffixes=('', '_cm'))
    df['Inizio'], df['Fine'] = pd.to_datetime(df['inizio']), pd.to_datetime(df['fine'])
    df['Durata_ms'] = ((df['Fine'] + timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000
    df['Commessa'], df['Task'], df['stato_task'] = df['nome_commessa'], df['nome_task'], df['stato']
    
    color_map = {o['nome']: o.get('colore', '#8dbad2') for o in data_op}

    # FILTRI
    st.markdown('<div style="margin-top:-10px;"></div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns([2.5, 2.5, 4])
    s_cm = f1.multiselect("Progetti", sorted(df['Commessa'].unique()))
    s_op = f2.multiselect("Operatori", sorted(df['operatore'].unique()))
    with f3:
        cc1, cc2 = st.columns(2)
        scala = cc1.selectbox("Vista", ["Settimana", "2 Settimane", "Mese", "Trimestre"], index=1)
    
    df_p = df.copy()
    if s_cm: df_p = df_p[df_p['Commessa'].isin(s_cm)]
    if s_op: df_p = df_p[df_p['operatore'].isin(s_op)]

    oggi = datetime.now()
    d_days = {"Settimana": 7, "2 Settimane": 14, "Mese": 30, "Trimestre": 90}[scala]
    x_range = [oggi - timedelta(days=2), oggi + timedelta(days=d_days)]

    # PULSANTI
    st.markdown('<div style="margin-top:10px;"></div>', unsafe_allow_html=True)
    b1, b2, b3, b4, b5 = st.columns([1, 1, 1, 1, 1.5])
    if b1.button("➕ Progetto", use_container_width=True): modal_commessa()
    if b2.button("📑 Task", use_container_width=True): modal_task()
    if b3.button("⏱️ Log", use_container_width=True): modal_log()
    if b4.button("📍 Oggi", use_container_width=True): st.session_state.chart_key += 1; st.rerun()
    
    txt_v = "↕️ Espandi Task" if st.session_state.vista_compressa else "↔️ Comprimi Commesse"
    if b5.button(txt_v, use_container_width=True, type="secondary"):
        st.session_state.vista_compressa = not st.session_state.vista_compressa
        st.rerun()

    tabs = st.tabs(["📊 Gantt", "⚙️ Setup", "📈 Stats"])
    with tabs[0]: render_gantt_fragment(df_p, color_map, oggi, x_range)
    with tabs[1]:
        st.subheader("Configurazione")
        s_t = st.tabs(["Operatori", "Commesse", "Task"])
        with s_t[0]:
            e_op = st.data_editor(pd.DataFrame(data_op), use_container_width=True, num_rows="dynamic", hide_index=True)
            if st.button("Salva Operatori"): aggiorna_database_setup("Operatori", e_op, data_op)
        with s_t[1]:
            e_cm = st.data_editor(pd.DataFrame(data_cm), column_config={"stato_commessa": st.column_config.SelectboxColumn("Stato", options=STATI_COMMESSA)}, use_container_width=True, num_rows="dynamic", hide_index=True)
            if st.button("Salva Commesse"): aggiorna_database_setup("Commesse", e_cm, data_cm)
    with tabs[2]:
        if not df_p.empty: st.bar_chart(df_p.groupby('operatore')['Durata_ms'].sum() / 3600000)

else:
    st.warning("Nessun dato trovato nel database. Inizia creando una Commessa.")
