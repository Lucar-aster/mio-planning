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

# --- TAB 1: TIMELINE ---
with tabs[0]:
    st.header("Timeline Progetti")

# --- SELETTORE DI SCALA ---
    col_scale, col_empty = st.columns([2, 4])
    scala = col_scale.selectbox(
        "Seleziona Scala Temporale", 
        ["Settimanale", "Mensile", "Trimestrale", "Semestrale"],
        index=1)
    try:
        logs = get_data("Log_Tempi")
        tasks = {t['id']: t['nome_task'] for t in get_data("Task")}
        
        if logs:
            df = pd.DataFrame(logs)
            df['Inizio'] = pd.to_datetime(df['inizio']).dt.date
            df['Fine'] = pd.to_datetime(df['fine']).dt.date
            df['Task'] = df['task_id'].map(tasks)
# Formattazione Etichetta: "01/01/2026 (Sett. 1)"
            df['label_settimana'] = df['Inizio'].dt.strftime('%d/%m/%Y') + " (Sett. " + df['Inizio'].dt.isocalendar().week.astype(str) + ")"

            # Configurazione Scala
            scale_config = {
                "Settimanale": {"dtick": "D1", "format": "%d %b\nSett.%V"},
                "Mensile": {"dtick": "D7", "format": "%d/%m\nSett.%V"},
                "Trimestrale": {"dtick": "M1", "format": "%b %Y\nSett.%V"},
                "Semestrale": {"dtick": "M1", "format": "%b %Y"}
            }
            conf = scale_config[scala]

# Creazione Grafico
            fig = px.timeline(
                df, 
                x_start="Inizio", 
                x_end="Fine", 
                y="Task", 
                color="operatore", 
                text="operatore",
                color_discrete_sequence=px.colors.qualitative.Pastel # Colori più eleganti
            )

            # Estetica Avanzata
            fig.update_layout(
                bar_gap=0.4, # Spazio tra le barre
                plot_bgcolor="rgba(0,0,0,0)", # Sfondo trasparente
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Arial", size=12),
                showlegend=True,
                legend_title_text="Operatore",
                margin=dict(l=20, r=20, t=40, b=20)
            )

            # Configurazione Asse X (Date + Settimana)
            fig.update_xaxes(
                tickformat=conf["format"],
                dtick=conf["dtick"],
                gridcolor="LightGrey",
                linecolor="Black",
                mirror=True,
                ticks="outside"
            )

            fig.update_yaxes(
                autorange="reversed", 
                showgrid=True, 
                gridcolor="whitesmoke"
            )

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Nessun dato presente. Inizia a configurare il sistema.")
    except Exception as e:
        st.error(f"Errore nel caricamento del grafico: {e}")
        
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
