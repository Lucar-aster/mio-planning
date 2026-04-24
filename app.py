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
STATI_TASK = ["Pianificato 🔵", "In corso 🟡", "In attesa ⚪", "Completato 🟢", "Sospeso 🟠"]

# Nuova costante per gli orari lavorativi
ORARI_LAVORO = [f"{h:02d}:{m:02d}" for h in range(8, 18) for m in [0, 15, 30, 45]]
if "17:15" in ORARI_LAVORO: ORARI_LAVORO = ORARI_LAVORO[:ORARI_LAVORO.index("17:15")] # Limita a 17:00

# --- 2. CONNESSIONE E CACHING ---
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "TU_SECRET_KEY" # Assicurati di usare la tua chiave
supabase = create_client(URL, KEY)

@st.cache_data(ttl=60)
def get_cached_data(table):
    try: return supabase.table(table).select("*").execute().data
    except: return []

# --- 4. FUNZIONI DI SUPPORTO ---
def render_gantt_fragment(df_p, x_range, tick_range, tick_text, unique_key):
    if df_p.empty: return
    fig = go.Figure()
    for i, row in df_p.iterrows():
        color = "#3498db" if row['stato_task'] == "Pianificato 🔵" else "#f1c40f" if row['stato_task'] == "In corso 🟡" else "#2ecc71"
        fig.add_trace(go.Bar(
            x=[row['Durata_ms']], q1=[0], median=[0], q3=[0],
            base=row['Inizio'].timestamp() * 1000,
            y=[row['operatore']], orientation='h',
            marker_color=color,
            text=f"<b>{row['Commessa']}</b><br>{row['Task']}",
            textposition="inside", insidetextanchor="middle",
            hovertemplate=f"<b>{row['Commessa']}</b><br>{row['Task']}<br>Inizio: %{{base|%d/%m %H:%M}}<br>Fine: {row['Fine'].strftime('%H:%M')}<extra></extra>",
            customdata=[row['id']]
        ))
    
    fig.update_layout(
        barmode='stack', showlegend=False, height=250 + (len(df_p['operatore'].unique()) * 30),
        margin=dict(l=10, r=10, t=40, b=20),
        xaxis=dict(
            type="date", side="top", range=x_range,
            tickvals=tick_range + pd.Timedelta(hours=12), ticktext=tick_text,
            # TRUCCO: Nasconde le ore non lavorative per compattare la giornata
            rangebreaks=[dict(bounds=[17, 8], pattern="hour")] 
        ),
        yaxis=dict(autorange="reversed", gridcolor="#eee")
    )
    
    selected = st.plotly_chart(fig, use_container_width=True, key=unique_key, on_select="rerun")
    if selected and "points" in selected and selected["points"]:
        modal_gestione_clic(selected["points"][0]["customdata"])

# --- 5. MODALI (DIALOGS) ---

@st.dialog("⏱️ Nuovo Log")
def modal_log():
    cm_data, tk_data = get_cached_data("Commesse"), get_cached_data("Task")
    ops_list = [o['nome'] for o in get_cached_data("Operatori")]
    
    op_ms = st.multiselect("Operatore", options=ops_list)
    
    c1, c2 = st.columns(2)
    with c1:
        cm_sel = st.selectbox("Commessa", options=["---"] + [c['nome'] for c in cm_data])
    with c2:
        tk_options = [t['nome'] for t in tk_data if t['commessa_id'] == next((c['id'] for c in cm_data if c['nome'] == cm_sel), None)] if cm_sel != "---" else []
        tk_sel = st.selectbox("Task", options=["Nuovo Task..."] + tk_options)
    
    if tk_sel == "Nuovo Task...":
        new_tk_name = st.text_input("Nome Nuovo Task")
        new_task_status = st.selectbox("Stato Task", options=STATI_TASK)
    
    # --- NUOVA SEZIONE ORARI ---
    st.divider()
    data_log = st.date_input("Giorno", value=datetime.now())
    col_a, col_b = st.columns(2)
    ora_i = col_a.selectbox("Ora Inizio", options=ORARI_LAVORO, index=0, key="ni")
    ora_f = col_b.selectbox("Ora Fine", options=ORARI_LAVORO, index=len(ORARI_LAVORO)-1, key="nf")
    
    nota = st.text_area("Note")
    
    if st.button("Registra Log", width='stretch', type="primary"):
        if not op_ms or cm_sel == "---": st.error("⚠️ Campi obbligatori!"); return
        
        inizio_dt = f"{data_log} {ora_i}:00"
        fine_dt = f"{data_log} {ora_f}:00"
        
        if datetime.strptime(ora_i, "%H:%M") >= datetime.strptime(ora_f, "%H:%M"):
            st.error("L'ora di fine deve essere successiva all'ora di inizio"); return

        c_id = next(c['id'] for c in cm_data if c['nome'] == cm_sel)
        t_id = None
        if tk_sel == "Nuovo Task...":
            if new_tk_name:
                t_res = supabase.table("Task").insert({"nome": new_tk_name, "commessa_id": c_id, "stato": new_task_status}).execute()
                if t_res.data: t_id = t_res.data[0]['id']
        else:
            t_id = next(t['id'] for t in tk_data if t['nome'] == tk_sel and t['commessa_id'] == c_id)
            
        if t_id:
            for op in op_ms:
                supabase.table("Log_Tempi").insert({"operatore": op, "task_id": t_id, "inizio": inizio_dt, "fine": fine_dt, "note": nota}).execute()
            get_cached_data.clear()
            st.rerun()

@st.dialog("⚙️ Gestione Log")
def modal_gestione_clic(log_id):
    l_data = supabase.table("Log_Tempi").select("*, task:task_id(nome, stato, commessa:commessa_id(nome))").eq("id", log_id).execute().data
    if not l_data: return
    log = l_data[0]
    
    st.write(f"**{log['task']['commessa']['nome']}** > {log['task']['nome']}")
    st.caption(f"Operatore: {log['operatore']}")
    
    azione = st.radio("Azione", ["Visualizza/Note", "Modifica Log", "Elimina"], horizontal=True)
    
    if azione == "Visualizza/Note":
        st.info(f"Note: {log.get('note') or 'Nessuna nota'}")
    
    elif azione == "Modifica Log":
        dt_i = pd.to_datetime(log['inizio'])
        dt_f = pd.to_datetime(log['fine'])
        
        nuova_data = st.date_input("Data", value=dt_i.date())
        c1, c2 = st.columns(2)
        
        # Cerchiamo l'indice degli orari attuali
        str_i, str_f = dt_i.strftime("%H:%M"), dt_f.strftime("%H:%M")
        idx_i = ORARI_LAVORO.index(str_i) if str_i in ORARI_LAVORO else 0
        idx_f = ORARI_LAVORO.index(str_f) if str_f in ORARI_LAVORO else len(ORARI_LAVORO)-1
        
        n_ora_i = c1.selectbox("Inizio", options=ORARI_LAVORO, index=idx_i, key="ei")
        n_ora_f = c2.selectbox("Fine", options=ORARI_LAVORO, index=idx_f, key="ef")
        nuova_nota = st.text_area("Note", value=log.get('note', ""))
        
        if st.button("Salva Modifiche"):
            supabase.table("Log_Tempi").update({
                "inizio": f"{nuova_data} {n_ora_i}:00",
                "fine": f"{nuova_data} {n_ora_f}:00",
                "note": nuova_nota
            }).eq("id", log_id).execute()
            get_cached_data.clear(); st.rerun()

    elif azione == "Elimina":
        if st.button("Conferma Eliminazione", type="primary"):
            supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
            get_cached_data.clear(); st.rerun()

# --- 8. MAIN UI ---
st.title("🚀 Aster Planning")

with st.sidebar:
    st.image(LOGO_URL, width=100)
    if st.button("➕ Nuovo Log", use_container_width=True, type="primary"): modal_log()
    
    st.header("🛠️ Filtri")
    # ... (Mantieni i tuoi filtri esistenti per operatori, commesse, etc.) ...
    # Assumiamo che qui ci siano i multiselect e il date_input per 'range_filtro'

# Recupero dati
l, t, c, o = get_cached_data("Log_Tempi"), get_cached_data("Task"), get_cached_data("Commesse"), get_cached_data("Operatori")

if l:
    df = pd.DataFrame(l)
    # MODIFICA: Non usiamo più .dt.normalize() per tenere ore e minuti
    df['Inizio'] = pd.to_datetime(df['inizio'])
    df['Fine'] = pd.to_datetime(df['fine'])
    
    # Mapping
    tk_m = {i['id']: {'n': i['nome'], 'c': i['commessa_id'], 's': i['stato']} for i in t}
    cm_m = {i['id']: {'n': i['nome'], 's': i['stato']} for i in c}
    
    df['Commessa'] = df['task_id'].apply(lambda x: cm_m.get(tk_m.get(x, {}).get('c'), {}).get('n', "N/A"))
    df['Task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('n', "N/A"))
    df['stato_task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('s', "Pianificato 🔵"))
    
    # Calcolo durata esatta per il Gantt
    df['Durata_ms'] = (df['Fine'] - df['Inizio']).dt.total_seconds() * 1000

    # ... (Logica di filtraggio del DataFrame df_p in base alla sidebar) ...
    # [Codice dei filtri omesso per brevità, resta uguale al tuo]

    tabs = st.tabs(["📅 Carico Lavoro", "📊 Dashboard", "📋 Lista Logs"])

    with tabs[0]:
        # Logica del range temporale (settimana/mese)
        # Assicurati di passare rangebreaks=[dict(bounds=[17, 8], pattern="hour")] nel grafico
        # render_gantt_fragment(...) viene chiamato qui
        pass 

    with tabs[2]:
        st.dataframe(df[['operatore', 'Commessa', 'Task', 'Inizio', 'Fine', 'note']])

else:
    st.info("Nessun log trovato.")
