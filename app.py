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

# --- TAB 1: TIMELINE (Visualizzazione) ---
with menu[0]:
    st.header("Timeline Lavori")
    # Join tra Log_Tempi e Task per avere i nomi dei task
    res = supabase.table("Log_Tempi").select("*, Task(nome_task)").execute()
    logs = res.data if res.data else []

    if logs:
        df = pd.DataFrame(logs)
        df['Task'] = df['Task'].apply(lambda x: x['nome_task'] if x else "N/A")
        
        fig = px.timeline(df, x_start="inizio", x_end="fine", y="Task", color="operatore",
                          hover_data=["operatore"], title="Distribuzione Intervalli")
        fig.update_yaxes(autorange="reversed")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Nessun log presente. Vai a registrare dei tempi!")

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
