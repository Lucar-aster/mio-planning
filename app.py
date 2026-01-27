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

# --- TAB 1: TIMELINE PROFESSIONALE E GESTIONE LOG ---
with tabs[0]:
    st.header("📊 Planning e Gestione Progetti")
    
    try:
        # 1. RECUPERO DATI
        logs = get_data("Log_Tempi")
        res_tasks = get_data("Task")
        res_commesse = get_data("Commesse")
        res_operatori = get_data("Operatori") # Assumendo esista una tabella Operatori
        
        if logs and res_tasks and res_commesse:
            # Mappe di decodifica
            task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in res_tasks}
            commessa_map = {c['id']: c['nome_commessa'] for c in res_commesse}
            lista_op = sorted(list(set([l['operatore'] for l in logs])))

            # Preparazione DataFrame
            df = pd.DataFrame(logs)
            df['Inizio'] = pd.to_datetime(df['inizio'])
            df['Fine'] = pd.to_datetime(df['fine'])
            df['Durata_ms'] = (df['Fine'] - df['Inizio']).dt.total_seconds() * 1000 + 86400000
            df['Commessa'] = df['task_id'].apply(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
            df['Task'] = df['task_id'].apply(lambda x: task_info[x]['nome'] if x in task_info else "N/A")
            
            # --- 2. FILTRI SUPERIORI (Per la Timeline) ---
            col_f1, col_f2, col_f3, col_f4 = st.columns([2,2,2,1])
            f_commessa = col_f1.multiselect("Filtra Progetto", options=sorted(df['Commessa'].unique()))
            f_operatore = col_f2.multiselect("Filtra Operatore", options=lista_op)
            scala = col_f3.selectbox("Scala", ["Settimana", "Mese", "Trimestre"], index=1)
            
            # Applicazione Filtri al DF del grafico
            df_plot = df.copy()
            if f_commessa:
                df_plot = df_plot[df_plot['Commessa'].isin(f_commessa)]
            if f_operatore:
                df_plot = df_plot[df_plot['operatore'].isin(f_operatore)]
            
            df_plot = df_plot.sort_values(by=['Commessa', 'Task'], ascending=[False, False])

            # --- 3. DISEGNO TIMELINE ---
            fig = go.Figure()
            soft_colors = ["#8dbad2", "#a5d6a7", "#ffcc80", "#ce93d8", "#b0bec5"]
            color_map = {op: soft_colors[i % len(soft_colors)] for i, op in enumerate(lista_op)}

            for op in df_plot['operatore'].unique():
                df_op = df_plot[df_plot['operatore'] == op]
                fig.add_trace(go.Bar(
                    base=df_op['Inizio'],
                    x=df_op['Durata_ms'],
                    y=[df_op['Commessa'], df_op['Task']],
                    orientation='h',
                    name=op,
                    marker=dict(color=color_map[op], cornerradius=10),
                    text=df_op['operatore'],
                    textposition='inside',
                    hovertemplate="<b>%{y[1]}</b><br>Operatore: %{name}<extra></extra>"
                ))

            # Griglia gerarchica
            fig.update_layout(
                barmode='overlay', dragmode='pan', bargap=0.6,
                height=350 + (len(df_plot.groupby(['Commessa', 'Task'])) * 40),
                plot_bgcolor="white", margin=dict(l=10, r=10, t=50, b=50),
                xaxis=dict(
                    type="date", side="top", showgrid=True, gridcolor="#e0e0e0",
                    minor=dict(showgrid=True, gridcolor="#f5f5f5", gridwidth=0.5)
                )
            )
            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displaylogo': False})

            # --- 4. PANNELLO DI MODIFICA AVANZATO ---
            st.divider()
            with st.expander("🛠️ Strumenti di Modifica e Cancellazione", expanded=False):
                st.subheader("Modifica rapida Log")
                
                # Sotto-filtri per trovare il log
                c1, c2, c3 = st.columns(3)
                filtro_c = c1.selectbox("1. Scegli Progetto", options=["Tutti"] + sorted(df['Commessa'].unique()))
                
                df_filtro = df.copy()
                if filtro_c != "Tutti":
                    df_filtro = df_filtro[df_filtro['Commessa'] == filtro_c]
                
                filtro_o = c2.selectbox("2. Scegli Operatore", options=["Tutti"] + sorted(df_filtro['operatore'].unique()))
                if filtro_o != "Tutti":
                    df_filtro = df_filtro[df_filtro['operatore'] == filtro_o]
                
                # Selezione finale del Log specifico
                log_map = {f"{r['Commessa']} | {r['Task']} ({r['Inizio'].strftime('%d/%m')})": r['id'] for _, r in df_filtro.iterrows()}
                scelta_log_id = c3.selectbox("3. Seleziona il Log da modificare", options=list(log_map.keys()))
                
                if scelta_log_id:
                    log_id = log_map[scelta_log_id]
                    curr = df[df['id'] == log_id].iloc[0]
                    
                    st.write("---")
                    col_m1, col_m2, col_m3, col_m4 = st.columns([2,2,2,1])
                    
                    n_inizio = col_m1.date_input("Inizio", value=curr['Inizio'])
                    n_fine = col_m2.date_input("Fine", value=curr['Fine'])
                    n_op = col_m3.selectbox("Cambia Operatore", options=lista_op, index=lista_op.index(curr['operatore']))
                    
                    # Bottone Salva
                    if col_m4.button("💾 Salva", use_container_width=True):
                        supabase.table("Log_Tempi").update({
                            "inizio": n_inizio.isoformat(),
                            "fine": n_fine.isoformat(),
                            "operatore": n_op
                        }).eq("id", log_id).execute()
                        st.success("Modificato!")
                        st.rerun()
                    
                    # Bottone Elimina (con conferma)
                    st.write("")
                    if st.button(f"🗑️ Elimina definitivamente questo Log", type="secondary"):
                        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
                        st.warning("Log eliminato!")
                        st.rerun()

        else:
            st.info("Nessun dato disponibile.")
    except Exception as e:
        st.error(f"Errore: {e}")
        
# --- TAB 2: REGISTRA TEMPI ---
with tabs[1]:
    st.header("📝 Registrazione Attività")
    
    # ... (Modulo di inserimento esistente) ...

    st.divider()
    st.subheader("📋 Storico Log")
    
    logs = get_data("Log_Tempi")
    if logs:
        df_logs = pd.DataFrame(logs)
        
        # Semplificazione: convertiamo tutto in stringhe o date Python per evitare errori di tipo
        df_logs['inizio'] = pd.to_datetime(df_logs['inizio']).dt.date
        df_logs['fine'] = pd.to_datetime(df_logs['fine']).dt.date
        
        # Visualizzazione pulita (senza editor per ora per evitare crash, solo visualizzazione)
        # Se vuoi l'editing, assicurati che le colonne corrispondano al DataFrame
        st.data_editor(
            df_logs,
            column_order=("operatore", "inizio", "fine"), 
            column_config={
                "operatore": st.column_config.TextColumn("Operatore"),
                "inizio": st.column_config.DateColumn("Data Inizio", format="DD/MM/YYYY"),
                "fine": st.column_config.DateColumn("Data Fine", format="DD/MM/YYYY"),
            },
            disabled=["id"], # Impedisce di modificare l'ID primario
            use_container_width=True,
            key="log_editor_fixed"
        )
    else:
        st.info("Nessun log presente.")
        
# --- TAB 3: CONFIGURAZIONE (CON MODIFICA E CANCELLAZIONE) ---
with tabs[2]:
    st.header("⚙️ Configurazione Sistema")
    
    c_admin1, c_admin2, c_admin3 = st.tabs(["🏗️ Commesse", "👥 Operatori", "✅ Task"])

    # --- SOTTO-TAB: COMMESSE ---
    with c_admin1:
        st.subheader("Gestione Commesse")
        commesse = get_data("Commesse")
        
        if commesse:
            col_target = "nome_commessa"
            
            # --- SEZIONE: MODIFICA ---
            with st.expander("📝 Modifica Nome Commessa"):
                c_to_edit = st.selectbox("Seleziona commessa da rinominare", options=commesse, format_func=lambda x: x[col_target], key="edit_c_sel")
                new_name_c = st.text_input("Nuovo nome", value=c_to_edit[col_target])
                if st.button("Aggiorna Nome"):
                    supabase.table("Commesse").update({col_target: new_name_c}).eq("id", c_to_edit["id"]).execute()
                    st.success("Nome aggiornato!")
                    st.rerun()

            # --- SEZIONE: ELIMINA ---
            with st.expander("🗑️ Elimina Commessa"):
                c_to_del = st.selectbox("Seleziona commessa da rimuovere", options=commesse, format_func=lambda x: x[col_target], key="del_c_sel")
                if st.button("Conferma Eliminazione", type="primary"):
                    supabase.table("Commesse").delete().eq("id", c_to_del["id"]).execute()
                    st.rerun()
            
            st.divider()
            st.dataframe(pd.DataFrame(commesse)[[col_target]], use_container_width=True)
        
        with st.form("new_c", clear_on_submit=True):
            n_c = st.text_input("➕ Aggiungi Nuova Commessa")
            if st.form_submit_button("Salva"):
                if n_c:
                    supabase.table("Commesse").insert({col_target: n_c}).execute()
                    st.rerun()

    # --- SOTTO-TAB: OPERATORI ---
    with c_admin2:
        st.subheader("Gestione Operatori")
        ops = get_data("Operatori")
        col_op = "nome_operatore"
        
        if ops:
            with st.expander("📝 Modifica Operatore"):
                op_to_edit = st.selectbox("Seleziona operatore", options=ops, format_func=lambda x: x[col_op])
                new_name_op = st.text_input("Nuovo nome operatore", value=op_to_edit[col_op])
                if st.button("Aggiorna Operatore"):
                    supabase.table("Operatori").update({col_op: new_name_op}).eq("id", op_to_edit["id"]).execute()
                    st.rerun()

            with st.expander("🗑️ Elimina Operatore"):
                op_to_del = st.selectbox("Elimina operatore", options=ops, format_func=lambda x: x[col_op], key="del_op_sel")
                if st.button("Elimina Definitivamente"):
                    supabase.table("Operatori").delete().eq("id", op_to_del["id"]).execute()
                    st.rerun()

            st.divider()
            st.dataframe(pd.DataFrame(ops)[[col_op]], use_container_width=True)
        
        with st.form("new_op"):
            n_o = st.text_input("➕ Aggiungi Nuovo Operatore")
            if st.form_submit_button("Salva"):
                supabase.table("Operatori").insert({col_op: n_o}).execute()
                st.rerun()

    # --- SOTTO-TAB: TASK ---
    with c_admin3:
        st.subheader("Gestione Task")
        tasks = get_data("Task")
        cms = get_data("Commesse")
        
        if tasks and cms:
            with st.expander("📝 Modifica Task"):
                t_to_edit = st.selectbox("Seleziona task", options=tasks, format_func=lambda x: x['nome_task'])
                new_t_name = st.text_input("Rinomina Task", value=t_to_edit['nome_task'])
                new_t_comm = st.selectbox("Sposta a Commessa", options=cms, format_func=lambda x: x['nome_commessa'])
                if st.button("Salva Modifiche Task"):
                    supabase.table("Task").update({"nome_task": new_t_name, "commessa_id": new_t_comm["id"]}).eq("id", t_to_edit["id"]).execute()
                    st.rerun()

            with st.expander("🗑️ Elimina Task"):
                t_to_del = st.selectbox("Elimina task", options=tasks, format_func=lambda x: x['nome_task'], key="del_t_sel")
                if st.button("Elimina Task"):
                    supabase.table("Task").delete().eq("id", t_to_del["id"]).execute()
                    st.rerun()

            st.divider()
            df_t = pd.DataFrame(tasks)
            c_map = {c['id']: c['nome_commessa'] for c in cms}
            df_t['Progetto'] = df_t['commessa_id'].map(c_map)
            st.dataframe(df_t[["nome_task", "Progetto"]], use_container_width=True)
            
        with st.form("new_task"):
            t_n = st.text_input("➕ Nuovo Task")
            t_c = st.selectbox("Commessa", options=cms, format_func=lambda x: x['nome_commessa'])
            if st.form_submit_button("Aggiungi Task"):
                supabase.table("Task").insert({"nome_task": t_n, "commessa_id": t_c['id']}).execute()
                st.rerun()
