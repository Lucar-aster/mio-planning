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

import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events

# --- TAB 1: TIMELINE CON SELEZIONE E MODIFICA ---
with tabs[0]:
    st.header("📊 Planning Interattivo")
    
    # Inizializziamo lo stato per la selezione se non esiste
    if 'selected_task' not in st.session_state:
        st.session_state.selected_task = None

    col1, col2, col3, col_button = st.columns([2, 2, 2, 1])
    scala = col1.selectbox("Vista", ["Settimana", "Mese", "Trimestre", "Semestre"], index=1)
    mostra_nomi = col2.checkbox("Nomi su barre", value=True)
    
    if col_button.button("📍 Oggi"):
        st.session_state.selected_task = None
        st.rerun()

    try:
        logs = get_data("Log_Tempi")
        res_tasks = get_data("Task")
        res_commesse = get_data("Commesse")
        
        if logs and res_tasks and res_commesse:
            task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in res_tasks}
            commessa_map = {c['id']: c['nome_commessa'] for c in res_commesse}
            
            df = pd.DataFrame(logs)
            df['Inizio'] = pd.to_datetime(df['inizio'])
            df['Fine'] = pd.to_datetime(df['fine'])
            df['Durata_ms'] = (df['Fine'] - df['Inizio']).dt.total_seconds() * 1000 + (86400000) # +1 giorno
            
            df['Commessa'] = df['task_id'].apply(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
            df['Task'] = df['task_id'].apply(lambda x: task_info[x]['nome'] if x in task_info else "N/A")
            df = df.sort_values(by=['Commessa', 'Task'], ascending=[False, False])

            # Creazione Grafico
            fig = go.Figure()
            operatori = df['operatore'].unique()
            color_map = {op: ["#8dbad2", "#a5d6a7", "#ffcc80", "#ce93d8", "#b0bec5"][i%5] for i, op in enumerate(operatori)}

            for op in operatori:
                df_op = df[df['operatore'] == op]
                # Evidenziazione se selezionato
                opacities = [1.0 if not st.session_state.selected_task or row['id'] == st.session_state.selected_task['id'] else 0.3 for _, row in df_op.iterrows()]
                
                fig.add_trace(go.Bar(
                    base=df_op['Inizio'],
                    x=df_op['Durata_ms'],
                    y=[df_op['Commessa'], df_op['Task']],
                    orientation='h',
                    name=op,
                    marker=dict(color=color_map[op], cornerradius=10, opacity=opacities),
                    customdata=df_op['id'], # Passiamo l'ID per riconoscerlo al click
                    text=df_op['operatore'] if mostra_nomi else None,
                    textposition='inside'
                ))

            # Configurazione Layout
            fig.update_layout(
                barmode='overlay', dragmode='pan', bargap=0.5,
                height=400 + (len(df) * 20), plot_bgcolor="white",
                xaxis=dict(type="date", side="top", showgrid=True, gridcolor="#f0f0f0"),
                yaxis=dict(gridcolor="#f5f5f5")
            )

            # --- GESTIONE EVENTO CLICK ---
            # Questo sostituisce st.plotly_chart e cattura il click
            selected_points = plotly_events(fig, click_event=True, hover_event=False, override_height=600)

            if selected_points:
                point_index = selected_points[0]['pointIndex']
                curve_index = selected_points[0]['curveNumber']
                # Troviamo l'ID del log cliccato
                clicked_id = fig.data[curve_index].customdata[point_index]
                st.session_state.selected_task = df[df['id'] == clicked_id].iloc[0].to_dict()
                st.rerun()

            # --- PANNELLO DI MODIFICA (Appare solo se clicchi una barra) ---
            if st.session_state.selected_task:
                st.divider()
                with st.expander("📝 Modifica Rapida Task Selezionato", expanded=True):
                    task_sel = st.session_state.selected_task
                    st.write(f"Modifica: **{task_sel['Task']}** ({task_sel['Commessa']})")
                    
                    col_edit1, col_edit2, col_edit3 = st.columns(3)
                    nuovo_inizio = col_edit1.date_input("Inizio", value=pd.to_datetime(task_sel['inizio']))
                    nuova_fine = col_edit2.date_input("Fine", value=pd.to_datetime(task_sel['fine']))
                    
                    if col_edit3.button("Salva Modifiche"):
                        supabase.table("Log_Tempi").update({
                            "inizio": nuovo_inizio.isoformat(),
                            "fine": nuova_fine.isoformat()
                        }).eq("id", task_sel['id']).execute()
                        st.success("Aggiornato!")
                        st.session_state.selected_task = None
                        st.rerun()
                    
                    if st.button("Annulla Selezione"):
                        st.session_state.selected_task = None
                        st.rerun()

        else:
            st.info("Nessun dato da mostrare.")
    except Exception as e:
        st.error(f"Errore: {e}")
        
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
