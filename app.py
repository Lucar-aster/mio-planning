import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.express as px
from datetime import datetime

# Connessione a Supabase (Inserisci i tuoi dati qui)
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

st.title("⏱️ Team Project Planning")

# --- SEZIONE INSERIMENTO DATI ---
with st.sidebar:
    st.header("Registra Tempo")
    
    # Recupero commesse
    res_c = supabase.table("Commesse").select("*").execute()
    commesse = res_c.data if res_c.data else []
    
    if not commesse:
        st.warning("⚠️ Nessuna commessa trovata. Aggiungine una su Supabase!")
        lista_commesse = {}
    else:
        lista_commesse = {c['nome_commessa']: c['id'] for c in commesse}
        scelta_c = st.selectbox("Seleziona Commessa", options=list(lista_commesse.keys()))
        
        # Recupero task relativi
        res_t = supabase.table("Task").select("*").eq("commessa_id", lista_commesse[scelta_c]).execute()
        tasks = res_t.data if res_t.data else []
        
        if not tasks:
            st.warning("⚠️ Nessun task per questa commessa.")
            lista_task = {}
        else:
            lista_task = {t['nome_task']: t['id'] for t in tasks}
            scelta_t = st.selectbox("Seleziona Task", options=list(lista_task.keys()))
            
            operatore = st.text_input("Nome Operatore", value="Operatore 1")
            
            col1, col2 = st.columns(2)
            with col1:
                data_i = st.date_input("Inizio")
                ora_i = st.time_input("Ora Inizio")
            with col2:
                data_f = st.date_input("Fine")
                ora_f = st.time_input("Ora Fine")

            if st.button("Salva Intervallo"):
                inizio_dt = datetime.combine(data_i, ora_i).isoformat()
                fine_dt = datetime.combine(data_f, ora_f).isoformat()
                
                supabase.table("Log_Tempi").insert({
                    "task_id": lista_task[scelta_t],
                    "operatore": operatore,
                    "inizio": inizio_dt,
                    "fine": fine_dt
                }).execute()
                st.success("Registrato! Ricarica la pagina.")
                
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
