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

# --- MENU NAVIGAZIONE ---
menu = st.tabs(["📊 Timeline", "➕ Registra Tempi", "⚙️ Gestione Anagrafica"])

# --- TAB 1: TIMELINE (Visualizzazione + Inserimento Rapido) ---
with menu[0]:
    st.header("Timeline Lavori")
    
    # --- NUOVO: MODULO DI INSERIMENTO RAPIDO ---
    with st.expander("➕ Registra rapidamente un nuovo intervallo"):
        # Carichiamo i dati necessari per i menu a tendina
        c_res = supabase.table("Commesse").select("id, nome_commessa").execute().data
        if c_res:
            col_c, col_t = st.columns(2)
            lista_c = {c['nome_commessa']: c['id'] for c in c_res}
            sel_c = col_c.selectbox("Progetto", options=list(lista_c.keys()), key="quick_c")
            
            t_res = supabase.table("Task").select("id, nome_task").eq("commessa_id", lista_c[sel_c]).execute().data
            if t_res:
                lista_t = {t['nome_task']: t['id'] for t in t_res}
                sel_t = col_t.selectbox("Task", options=list(lista_t.keys()), key="quick_t")
                
                with st.form("quick_log_form"):
                    op = st.text_input("Operatore", key="quick_op")
                    c1, c2 = st.columns(2)
                    d_i = c1.date_input("Inizio", key="q_di")
                    t_i = c1.time_input("Ora", key="q_ti")
                    d_f = c2.date_input("Fine", key="q_df")
                    t_f = c2.time_input("Ora", key="q_tf")
                    
                    if st.form_submit_button("Salva ed Aggiorna Timeline"):
                        inizio = datetime.combine(d_i, t_i).isoformat()
                        fine = datetime.combine(d_f, t_f).isoformat()
                        supabase.table("Log_Tempi").insert({
                            "task_id": lista_t[sel_t], "operatore": op,
                            "inizio": inizio, "fine": fine
                        }).execute()
                        st.success("Registrato!")
                        st.rerun()
            else:
                st.info("Aggiungi task a questa commessa nell'anagrafica.")
        else:
            st.info("Nessuna commessa trovata.")

    st.divider()

    # --- VISUALIZZAZIONE GRAFICA ---
   try:
    res_logs = supabase.table("Log_Tempi").select("*").execute().data
    res_tasks = supabase.table("Task").select("id, nome_task").execute().data
    task_map = {t['id']: t['nome_task'] for t in res_tasks} if res_tasks else {}

    if res_logs:
        df = pd.DataFrame(res_logs)
        
        # Trasformiamo le colonne in oggetti data (rimuovendo l'informazione dell'ora per il calcolo)
        df['inizio_data'] = pd.to_datetime(df['inizio']).dt.date
        df['fine_data'] = pd.to_datetime(df['fine']).dt.date
        
        df['Task'] = df['task_id'].map(task_map).fillna("Sconosciuto")
        
        # Creazione Timeline
        fig = px.timeline(
            df, 
            x_start="inizio_data", 
            x_end="fine_data", 
            y="Task", 
            color="operatore",
            text="operatore",
            title="Pianificazione Commesse (Vista Giornaliera)"
        )
        
        # Forza l'asse X a mostrare solo le date
        fig.update_xaxes(
            tickformat="%d/%m/%Y", # Formato italiano: Giorno/Mese/Anno
            dtick="D1"             # Forza uno scatto ogni 1 giorno
        )
        
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun dato da visualizzare.")
except Exception as e:
    st.error(f"Errore tecnico: {e}")
    
# --- TAB 2: REGISTRA TEMPI (Operatività) ---
with menu[1]:
    st.header("Inserimento Intervallo di Lavoro")
    commesse_res = supabase.table("Commesse").select("*").execute().data
    
    if not commesse_res:
        st.warning("Crea prima una Commessa nella sezione Gestione Anagrafica.")
    else:
        lista_c = {c['nome_commessa']: c['id'] for c in commesse_res}
        scelta_c = st.selectbox("Seleziona Progetto", options=list(lista_c.keys()))
        
        tasks_res = supabase.table("Task").select("*").eq("commessa_id", lista_c[scelta_c]).execute().data
        
        if not tasks_res:
            st.info("Nessun task associato a questa commessa.")
        else:
            lista_t = {t['nome_task']: t['id'] for t in tasks_res}
            scelta_t = st.selectbox("Seleziona Task", options=list(lista_t.keys()))
            
            with st.form("form_log"):
                operatore = st.text_input("Operatore")
                c1, c2 = st.columns(2)
                data_i = c1.date_input("Giorno Inizio")
                ora_i = c1.time_input("Ora Inizio")
                data_f = c2.date_input("Giorno Fine")
                ora_f = c2.time_input("Ora Fine")
                
                if st.form_submit_button("Salva Log"):
                    inizio = datetime.combine(data_i, ora_i).isoformat()
                    fine = datetime.combine(data_f, ora_f).isoformat()
                    supabase.table("Log_Tempi").insert({
                        "task_id": lista_t[scelta_t], "operatore": operatore,
                        "inizio": inizio, "fine": fine
                    }).execute()
                    st.success("Tempo registrato!")
                    st.rerun()

# --- TAB 3: GESTIONE ANAGRAFICA (Admin) ---
with menu[2]:
    st.header("Configurazione Progetti e Task")
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("Nuova Commessa")
        with st.form("form_commessa"):
            nome_c = st.text_input("Nome Commessa")
            cliente = st.text_input("Cliente")
            if st.form_submit_button("Crea Commessa"):
                supabase.table("Commesse").insert({"nome_commessa": nome_c, "cliente": cliente}).execute()
                st.success("Commessa creata!")
                st.rerun()

    with col_b:
        st.subheader("Nuovo Task")
        if commesse_res:
            with st.form("form_task"):
                lista_c_task = {c['nome_commessa']: c['id'] for c in commesse_res}
                sel_c = st.selectbox("Per Commessa:", options=list(lista_c_task.keys()))
                nome_t = st.text_input("Nome Task (es. Progettazione)")
                if st.form_submit_button("Crea Task"):
                    supabase.table("Task").insert({"commessa_id": lista_c_task[sel_c], "nome_task": nome_t}).execute()
                    st.success("Task creato!")
                    st.rerun()
