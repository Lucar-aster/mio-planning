import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime

# Connessione a Supabase (Inserisci i tuoi dati qui)
URL = https://vjeqrhseqbfsomketjoj.supabase.co
KEY = sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8
supabase = create_client(URL, KEY)

st.title("⏱️ Team Project Planning")

# --- SEZIONE INSERIMENTO DATI ---
with st.sidebar:
    st.header("Registra Tempo")
    # Qui carichiamo le commesse dal database
    commesse = supabase.table("Commesse").select("*").execute().data
    lista_commesse = {c['nome_commessa']: c['id'] for c in commesse}
    
    scelta_c = st.selectbox("Seleziona Commessa", options=list(lista_commesse.keys()))
    
    # Carichiamo i task relativi
    task = supabase.table("Task").select("*").eq("commessa_id", lista_commesse[scelta_c]).execute().data
    lista_task = {t['nome_task']: t['id'] for t in task}
    
    scelta_t = st.selectbox("Seleziona Task", options=list(lista_task.keys()))
    operatore = st.text_input("Nome Operatore")
    
    col1, col2 = st.columns(2)
    with col1:
        data_inizio = st.date_input("Data Inizio")
        ora_inizio = st.time_input("Ora Inizio")
    with col2:
        data_fine = st.date_input("Data Fine")
        ora_fine = st.time_input("Ora Fine")

    if st.button("Salva Intervallo"):
        inizio_dt = datetime.combine(data_inizio, ora_inizio).isoformat()
        fine_dt = datetime.combine(data_fine, ora_fine).isoformat()
        
        supabase.table("Log_Tempi").insert({
            "task_id": lista_task[scelta_t],
            "operatore": operatore,
            "inizio": inizio_dt,
            "fine": fine_dt
        }).execute()
        st.success("Tempo registrato!")

# --- VISUALIZZAZIONE TIMELINE ---
st.subheader("Visualizzazione Timeline")
logs = supabase.table("Log_Tempi").select("*, Task(nome_task)").execute().data

if logs:
    df = pd.DataFrame(logs)
    # Pulizia dati per il grafico
    df['Task Name'] = df['Task'].apply(lambda x: x['nome_task'])
    
    fig = px.timeline(df, x_start="inizio", x_end="fine", y="Task Name", color="operatore",
                      title="Distribuzione Carico di Lavoro")
    fig.update_yaxes(autorange="reversed") 
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nessun dato presente. Inizia a registrare i tempi!")
