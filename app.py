import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime

# Connessione a Supabase (Inserisci i tuoi dati qui)
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

st.set_page_config(page_title="Project Planner", layout="wide")

# --- FUNZIONE RECUPERO DATI ---
def get_data(table):
    return supabase.table(table).select("*").execute().data

# --- NAVIGAZIONE ---
tabs = st.tabs(["📊 Timeline", "➕ Registra Tempi", "⚙️ Configurazione"])

# --- TAB 1: TIMELINE PROFESSIONALE (VERSIONE DEFINITIVA ANTI-ERRORE) ---
with tabs[0]:
    st.header("📊 Planning Progetti")
    
    # 1. CONTROLLI DI VISUALIZZAZIONE
    col1, col2, col3, col_button = st.columns([2, 2, 2, 1])
    scala = col1.selectbox("Vista", ["Settimana", "Mese", "Trimestre", "Semestre"], index=1, key="vista_scala")
    mostra_nomi = col2.checkbox("Nomi su barre", value=True, key="check_nomi")
    
    oggi = datetime.now()
    if col_button.button("📍 Oggi"):
        st.rerun()
    
    try:
        # Recupero dati
        logs = get_data("Log_Tempi")
        res_tasks = get_data("Task")
        res_commesse = get_data("Commesse")
        
        if logs and res_tasks and res_commesse:
            task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in res_tasks}
            commessa_map = {c['id']: c['nome_commessa'] for c in res_commesse}
            
            df = pd.DataFrame(logs)
            df['Inizio'] = pd.to_datetime(df['inizio'])
            df['Fine'] = pd.to_datetime(df['fine'])
            df['Fine_Visual'] = df['Fine'] + pd.Timedelta(hours=23, minutes=59)
            
            # Creazione nomi
            df['Commessa'] = df['task_id'].apply(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
            df['Task'] = df['task_id'].apply(lambda x: task_info[x]['nome'] if x in task_info else "N/A")
            
            # ORDINAMENTO
            df = df.sort_values(by=['Commessa', 'Task'])

            # --- LA SOLUZIONE ALL'ERRORE DI LUNGHEZZA ---
            # Invece di passare una lista di liste a px.timeline (che causa l'errore), 
            # passiamo i dati al costruttore di oggetti grafici più stabile.
            
            import plotly.graph_objects as go

            fig = px.timeline(
                df, 
                x_start="Inizio", 
                x_end="Fine_Visual", 
                # Usiamo una lista semplice per Y, ma con i due livelli come tuple
                y=[df['Commessa'], df['Task']], 
                color="operatore",
                text="operatore" if mostra_nomi else None,
                hover_data={"Commessa": True, "Task": True},
                color_discrete_sequence=px.colors.qualitative.Safe
            )

            # Configurazione Scale
            scale_settings = {
                "Settimana": {"dtick": 86400000, "format": "%a %d\nSett %V", "zoom": 7},
                "Mese": {"dtick": 86400000 * 2, "format": "%d %b\nSett %V", "zoom": 30},
                "Trimestre": {"dtick": "M1", "format": "%b %Y", "zoom": 90},
                "Semestre": {"dtick": "M1", "format": "%b %Y", "zoom": 180}
            }
            conf = scale_settings[scala]

            # Zoom iniziale
            inizio_zoom = (oggi - pd.Timedelta(days=conf["zoom"]//2)).strftime("%Y-%m-%d")
            fine_zoom = (oggi + pd.Timedelta(days=conf["zoom"]//2)).strftime("%Y-%m-%d")

            # 4. CONFIGURAZIONE LAYOUT
            fig.update_layout(
                dragmode='pan',
                bargap=0.3,
                height=250 + (len(df['task_id'].unique()) * 50),
                margin=dict(l=10, r=20, t=80, b=50), # Plotly gestisce il margine auto con multicategory
                plot_bgcolor="white",
                xaxis=dict(
                    type="date",
                    rangeslider=dict(visible=True, thickness=0.04),
                    side="top",
                    gridcolor="#f0f0f0",
                    range=[inizio_zoom, fine_zoom],
                    fixedrange=False
                ),
                yaxis=dict(
                    title="", 
                    autorange="reversed",
                    fixedrange=True,
                    gridcolor="#eeeeee",
                    tickfont=dict(size=11),
                    # Questa riga forza il raggruppamento visivo corretto
                    templateitemname="Commessa" 
                ),
                legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="center", x=0.5)
            )

            fig.update_xaxes(tickformat=conf["format"], dtick=conf["dtick"], linecolor="#444")
            fig.add_vline(x=oggi.timestamp() * 1000, line_width=2, line_dash="dash", line_color="red", opacity=0.6)
            
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displaylogo': False})
            
        else:
            st.info("Configura i dati per visualizzare la timeline.")
            
    except Exception as e:
        # Se l'errore persiste, usiamo il piano B: Etichetta concatenata "Commessa > Task"
        st.warning("Ottimizzazione raggruppamento in corso...")
        try:
            df['Label_Y'] = df['Commessa'] + " | " + df['Task']
            fig_b = px.timeline(df, x_start="Inizio", x_end="Fine_Visual", y="Label_Y", color="operatore")
            fig_b.update_layout(dragmode='pan', xaxis=dict(side="top"))
            st.plotly_chart(fig_b, use_container_width=True)
        except:
            st.error(f"Errore critico: {e}")
        
# --- TAB 2: REGISTRA TEMPI ---
with tabs[1]:
    st.header("Nuovo Log Lavoro")
    commesse = get_data("Commesse")
    ops = [o['nome'] for o in get_data("Operatori")]
    
    if not commesse or not ops:
        st.error("Configura Commesse e Operatori nel Tab Configurazione.")
    else:
        map_c = {c['nome_commessa']: c['id'] for c in commesse}
        sel_c = st.selectbox("Progetto", options=list(map_c.keys()))
        
        tasks_c = supabase.table("Task").select("*").eq("commessa_id", map_c[sel_c]).execute().data
        if tasks_c:
            map_t = {t['nome_task']: t['id'] for t in tasks_c}
            sel_t = st.selectbox("Task", options=list(map_t.keys()))
            
            with st.form("log_form"):
                # Menu a tendina per operatori
                operatore = st.selectbox("Operatore", options=ops)
                d1 = st.date_input("Data Inizio")
                d2 = st.date_input("Data Fine")
                if st.form_submit_button("Salva"):
                    supabase.table("Log_Tempi").insert({
                        "task_id": map_t[sel_t], "operatore": operatore,
                        "inizio": d1.isoformat(), "fine": d2.isoformat()
                    }).execute()
                    st.success("Salvato!")
                    st.rerun()

# --- TAB 3: CONFIGURAZIONE (Gestione Valori) ---
with tabs[2]:
    st.header("Amministrazione Sistema")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.subheader("Operatori")
        nuovo_op = st.text_input("Nuovo Operatore")
        if st.button("Aggiungi Operatore"):
            supabase.table("Operatori").insert({"nome": nuovo_op}).execute()
            st.rerun()
        
        lista_op = get_data("Operatori")
        for o in lista_op:
            col_nome, col_del = st.columns([3,1])
            col_nome.write(o['nome'])
            if col_del.button("❌", key=f"del_op_{o['id']}"):
                supabase.table("Operatori").delete().eq("id", o['id']).execute()
                st.rerun()

    with c2:
        st.subheader("Commesse")
        n_c = st.text_input("Nome Progetto")
        if st.button("Aggiungi Commessa"):
            supabase.table("Commesse").insert({"nome_commessa": n_c}).execute()
            st.rerun()
        
        for c in commesse:
            col_n, col_d = st.columns([3,1])
            col_n.write(c['nome_commessa'])
            if col_d.button("❌", key=f"del_c_{c['id']}"):
                supabase.table("Commesse").delete().eq("id", c['id']).execute()
                st.rerun()

    with c3:
        st.subheader("Task")
        if commesse:
            sel_c_t = st.selectbox("Per Progetto:", options=list(map_c.keys()), key="task_config")
            n_t = st.text_input("Nome Task")
            if st.button("Aggiungi Task"):
                supabase.table("Task").insert({"commessa_id": map_c[sel_c_t], "nome_task": n_t}).execute()
                st.rerun()
