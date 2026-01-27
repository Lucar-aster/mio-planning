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

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# --- TAB 1: PLANNING PROGETTI (VERSIONE COMPLETA E OTTIMIZZATA) ---
with tabs[0]:
    st.header("📊 Planning Progetti")
    
    try:
        # 1. RECUPERO DATI E PREPARAZIONE
        logs = get_data("Log_Tempi")
        res_tasks = get_data("Task")
        res_commesse = get_data("Commesse")
        
        if logs and res_tasks and res_commesse:
            # Creazione mappe per decodifica nomi
            task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in res_tasks}
            commessa_map = {c['id']: c['nome_commessa'] for c in res_commesse}
            
            df = pd.DataFrame(logs)
            df['Inizio'] = pd.to_datetime(df['inizio'])
            df['Fine'] = pd.to_datetime(df['fine'])
            # Calcolo durata in millisecondi (aggiungiamo fine giornata per visibilità barre giornaliere)
            df['Fine_Visual'] = df['Fine'] + pd.Timedelta(hours=23, minutes=59, seconds=59)
            df['Durata_ms'] = (df['Fine_Visual'] - df['Inizio']).dt.total_seconds() * 1000
            
            # Arricchimento dati
            df['Commessa'] = df['task_id'].apply(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
            df['Task'] = df['task_id'].apply(lambda x: task_info[x]['nome'] if x in task_info else "N/A")
            lista_op = sorted(df['operatore'].unique().tolist())

            # 2. FILTRI SUPERIORI
            col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
            f_commessa = col_f1.multiselect("Progetti", options=sorted(df['Commessa'].unique()), key="f_comm")
            f_operatore = col_f2.multiselect("Operatori", options=lista_op, key="f_oper")
            scala = col_f3.selectbox("Scala Temporale", ["Settimana", "Mese", "Trimestre"], index=1, key="f_scala")
            
            if col_f4.button("📍 Oggi", use_container_width=True):
                st.rerun()

            # Applicazione filtri
            df_plot = df.copy()
            if f_commessa:
                df_plot = df_plot[df_plot['Commessa'].isin(f_commessa)]
            if f_operatore:
                df_plot = df_plot[df_plot['operatore'].isin(f_operatore)]
            
            # Ordinamento fondamentale per la gerarchia dell'asse Y
            df_plot = df_plot.sort_values(by=['Commessa', 'Task'], ascending=[False, False])

            # 3. CONFIGURAZIONE ESTETICA
            soft_colors = ["#8dbad2", "#a5d6a7", "#ffcc80", "#ce93d8", "#b0bec5", "#ffab91"]
            color_map = {op: soft_colors[i % len(soft_colors)] for i, op in enumerate(lista_op)}
            
            # Impostazioni scala temporale
            scale_settings = {
                "Settimana": {"dtick": 86400000, "format": "%a %d\nSett %V", "zoom": 7},
                "Mese": {"dtick": 86400000 * 2, "format": "%d %b\nSett %V", "zoom": 30},
                "Trimestre": {"dtick": "M1", "format": "%b %Y", "zoom": 90}
            }
            conf = scale_settings[scala]
            oggi = datetime.now()
            inizio_zoom = (oggi - pd.Timedelta(days=conf["zoom"]//2))
            fine_zoom = (oggi + pd.Timedelta(days=conf["zoom"]//2))

            # 4. COSTRUZIONE GRAFICO
            fig = go.Figure()

            for op in df_plot['operatore'].unique():
                df_op = df_plot[df_plot['operatore'] == op]
                
                fig.add_trace(go.Bar(
                    base=df_op['Inizio'],
                    x=df_op['Durata_ms'],
                    y=[df_op['Commessa'], df_op['Task']],
                    orientation='h',
                    name=op,
                    offsetgroup=op,  # Raggruppa per operatore per evitare sovrapposizioni
                    marker=dict(
                        color=color_map[op], 
                        cornerradius=10,
                        line=dict(width=1, color="white")
                    ),
                    width=0.4, # Altezza barra ridotta (permette affiancamento)
                    text=df_op['operatore'],
                    textposition='inside',
                    insidetextanchor='middle',
                    hovertemplate="<b>%{y[1]}</b><br>Progetto: %{y[0]}<br>Operatore: %{name}<br>Dal: %{base|%d/%m}<extra></extra>"
                ))

            # Configurazione Layout e Griglia
            fig.update_layout(
                barmode='group', # Barre affiancate se condividono lo stesso Y
                dragmode='pan',
                bargap=0.3,      # Spazio tra diversi Task
                bargroupgap=0.05, # Spazio minimo tra barre operatori nello stesso Task
                height=400 + (len(df_plot.groupby(['Commessa', 'Task'])) * 50),
                margin=dict(l=10, r=10, t=60, b=50),
                plot_bgcolor="white",
                xaxis=dict(
                    type="date",
                    side="top",
                    range=[inizio_zoom, fine_zoom],
                    rangeslider=dict(visible=True, thickness=0.03),
                    showgrid=True,
                    gridcolor="#e0e0e0", # Settimane/Mesi
                    gridwidth=1.5,
                    minor=dict(showgrid=True, gridcolor="#f5f5f5", gridwidth=0.5) # Giorni
                ),
                yaxis=dict(
                    autorange="reversed",
                    gridcolor="#f5f5f5",
                    tickfont=dict(size=11)
                ),
                legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5),
                showlegend=True
            )

            # Formattazione assi X
            fig.update_xaxes(tickformat=conf["format"], dtick=conf["dtick"])

            # Linea "Oggi"
            fig.add_vline(x=oggi.timestamp() * 1000, line_width=2, line_dash="solid", line_color="#ff5252")

            st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True, 'displaylogo': False})

            # --- 5. PANNELLO MODIFICA (VERSIONE STABILE) ---
            st.divider()
            with st.expander("🛠️ Gestione Rapida Log (Modifica / Elimina)", expanded=False):
                # Filtri di ricerca log
                c1, c2, c3 = st.columns(3)
                sel_c = c1.selectbox("Filtra Progetto", options=["Tutti"] + sorted(df['Commessa'].unique()), key="edit_c")
                
                df_edit = df.copy()
                if sel_c != "Tutti": df_edit = df_edit[df_edit['Commessa'] == sel_c]
                
                sel_o = c2.selectbox("Filtra Operatore", options=["Tutti"] + sorted(df_edit['operatore'].unique()), key="edit_o")
                if sel_o != "Tutti": df_edit = df_edit[df_edit['operatore'] == sel_o]
                
                # Selezione log specifico
                log_options = {f"{r['Commessa']} | {r['Task']} ({r['Inizio'].strftime('%d/%m')})": r['id'] for _, r in df_edit.iterrows()}
                if log_options:
                    scelta_nome = c3.selectbox("Seleziona Log", options=list(log_options.keys()))
                    log_id = log_options[scelta_nome]
                    curr_log = df[df['id'] == log_id].iloc[0]
                    
                    st.write("---")
                    col_m1, col_m2, col_m3, col_m4 = st.columns([2, 2, 2, 1])
                    
                    new_in = col_m1.date_input("Inizio", value=curr_log['Inizio'])
                    new_fi = col_m2.date_input("Fine", value=curr_log['Fine'])
                    new_op = col_m3.selectbox("Operatore", options=lista_op, index=lista_op.index(curr_log['operatore']))
                    
                    if col_m4.button("💾 Salva", use_container_width=True):
                        supabase.table("Log_Tempi").update({
                            "inizio": new_in.isoformat(),
                            "fine": new_fi.isoformat(),
                            "operatore": new_op
                        }).eq("id", log_id).execute()
                        st.success("Log aggiornato!")
                        st.rerun()
                    
                    if st.button("🗑️ Elimina Log Selezionato", type="secondary"):
                        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
                        st.warning("Log eliminato!")
                        st.rerun()
                else:
                    st.info("Nessun log trovato con i filtri selezionati.")

        else:
            st.info("Configura i dati (Commesse e Task) e inserisci dei log per visualizzare il planning.")
            
    except Exception as e:
        st.error(f"Errore tecnico nel caricamento della Timeline: {e}")
        
# --- TAB 2: REGISTRA TEMPI (VERSIONE ANTI-ERRORE) ---
with tabs[1]:
    st.header("📝 Registrazione Attività")
    
    logs = get_data("Log_Tempi")
    cms = get_data("Commesse")
    tasks = get_data("Task")
    ops = get_data("Operatori")

    if logs and cms and tasks and ops:
        df_logs = pd.DataFrame(logs)
        
        # --- FUNZIONE DETECTIVE PER COLONNE ---
        def get_col(df, possibili_nomi):
            for nome in possibili_nomi:
                if nome in df.columns:
                    return nome
            return df.columns[0] # Fallback sulla prima colonna se non trova nulla

        # Identifichiamo le colonne corrette nelle tabelle
        col_log_op = get_col(df_logs, ["operatore_id", "id_operatore", "operatore"])
        col_log_tk = get_col(df_logs, ["task_id", "id_task", "task"])
        
        col_op_name = get_col(pd.DataFrame(ops), ["nome_operatore", "nome", "operatore"])
        col_tk_name = get_col(pd.DataFrame(tasks), ["nome_task", "nome", "task"])
        col_tk_link = get_col(pd.DataFrame(tasks), ["commessa_id", "id_commessa", "progetto_id"])
        col_cm_name = get_col(pd.DataFrame(cms), ["nome_commessa", "nome", "commessa"])

        # --- MAPPATURE ---
        o_map = {o['id']: o.get(col_op_name, 'N/A') for o in ops}
        t_map = {t['id']: t.get(col_tk_name, 'N/A') for t in tasks}
        
        # Mappa Task -> Nome Commessa
        task_to_comm_id = {t['id']: t.get(col_tk_link) for t in tasks}
        comm_id_to_name = {c['id']: c.get(col_cm_name, 'N/A') for c in cms}

        # --- CREAZIONE COLONNE VISUALIZZAZIONE ---
        df_logs['Operatore'] = df_logs[col_log_op].map(o_map)
        df_logs['Task'] = df_logs[col_log_tk].map(t_map)
        df_logs['Commessa'] = df_logs[col_log_tk].map(task_to_comm_id).map(comm_id_to_name)
        
        # Gestione date (cerchiamo 'inizio' o 'data')
        col_inizio = get_col(df_logs, ["inizio", "data_inizio", "start"])
        col_fine = get_col(df_logs, ["fine", "data_fine", "end"])
        
        df_logs['Inizio'] = pd.to_datetime(df_logs[col_inizio]).dt.strftime('%d/%m/%Y %H:%M')
        df_logs['Fine'] = pd.to_datetime(df_logs[col_fine]).dt.strftime('%d/%m/%Y %H:%M')

        # --- VISUALIZZAZIONE ---
        st.subheader("📋 Storico Log")
        st.dataframe(df_logs[["Commessa", "Task", "Operatore", "Inizio", "Fine"]], use_container_width=True)
        
        st.divider()

        # --- GESTIONE IN FONDO ---
        c1, c2 = st.columns(2)
        with c1:
            with st.expander("🗑️ Elimina Log"):
                log_to_del = st.selectbox("Seleziona log da rimuovere", options=logs, 
                                          format_func=lambda x: f"{o_map.get(x[col_log_op])} - {t_map.get(x[col_log_tk])}", key="del_l")
                if st.button("Elimina ora", type="primary"):
                    supabase.table("Log_Tempi").delete().eq("id", log_to_del["id"]).execute()
                    st.rerun()
        
        with c2:
            with st.expander("📝 Modifica Log"):
                st.info("Seleziona un log per modificarne i dettagli.")
                # Qui si può implementare la logica di update simile a quella del Tab 3

    else:
        st.warning("Dati insufficienti per mostrare lo storico. Controlla le configurazioni.")

    # --- AGGIUNGI NUOVO ---
    with st.expander("➕ Registra Nuova Attività"):
        with st.form("new_log_form"):
            sel_op = st.selectbox("Operatore", ops, format_func=lambda x: x[col_op_name])
            sel_tk = st.selectbox("Task", tasks, format_func=lambda x: f"{x[col_tk_name]} ({comm_id_to_name.get(x[col_tk_link])})")
            
            d1, d2 = st.columns(2)
            data_i = d1.date_input("Inizio")
            ora_i = d1.time_input("Ora", value=None, key="time_i")
            data_f = d2.date_input("Fine")
            ora_f = d2.time_input("Ora", value=None, key="time_f")
            
            if st.form_submit_button("Salva Log"):
                # Inserimento usando le colonne trovate dal detective
                payload = {
                    col_log_op: sel_op['id'],
                    col_log_tk: sel_tk['id'],
                    col_inizio: f"{data_i} {ora_i}",
                    col_fine: f"{data_f} {ora_f}"
                }
                supabase.table("Log_Tempi").insert(payload).execute()
                st.rerun()
        
# --- TAB 3: CONFIGURAZIONE (GESTIONE IN FONDO) ---
with tabs[2]:
    st.header("⚙️ Configurazione Sistema")
    
    c_admin1, c_admin2, c_admin3 = st.tabs(["🏗️ Commesse", "👥 Operatori", "✅ Task"])

    # --- SOTTO-TAB: COMMESSE ---
    with c_admin1:
        st.subheader("Elenco Commesse")
        commesse = get_data("Commesse")
        if commesse:
            df_c = pd.DataFrame(commesse)
            col_c = next((c for c in ["nome_commessa", "nome"] if c in df_c.columns), df_c.columns[0])
            
            # 1. Visualizzazione (In alto)
            st.dataframe(df_c[[col_c]], use_container_width=True)
            st.divider()

            # 2. Pannelli Gestione (In fondo)
            with st.expander("📝 Modifica Nome Commessa"):
                c_edit = st.selectbox("Seleziona commessa", options=commesse, format_func=lambda x: x[col_c], key="ed_c")
                n_val_c = st.text_input("Nuovo nome", value=c_edit[col_c], key="txt_c")
                if st.button("Aggiorna", key="btn_c"):
                    supabase.table("Commesse").update({col_c: n_val_c}).eq("id", c_edit["id"]).execute()
                    st.rerun()

            with st.expander("🗑️ Elimina Commessa"):
                c_del = st.selectbox("Elimina commessa", options=commesse, format_func=lambda x: x[col_c], key="dl_c")
                if st.button("Elimina Definitivamente", type="primary", key="btn_dl_c"):
                    supabase.table("Commesse").delete().eq("id", c_del["id"]).execute()
                    st.rerun()
        
        with st.form("new_c"):
            n_c = st.text_input("➕ Aggiungi Nuova Commessa")
            if st.form_submit_button("Salva"):
                supabase.table("Commesse").insert({"nome_commessa": n_c}).execute()
                st.rerun()

    # --- SOTTO-TAB: OPERATORI ---
    with c_admin2:
        st.subheader("Elenco Operatori")
        ops = get_data("Operatori")
        if ops:
            df_o = pd.DataFrame(ops)
            col_o = next((c for c in ["nome_operatore", "nome"] if c in df_o.columns), df_o.columns[0])
            
            # 1. Visualizzazione
            st.dataframe(df_o[[col_o]], use_container_width=True)
            st.divider()

            # 2. Pannelli Gestione
            with st.expander("📝 Modifica Operatore"):
                o_edit = st.selectbox("Seleziona operatore", options=ops, format_func=lambda x: x[col_o], key="ed_o")
                n_val_o = st.text_input("Nuovo nome", value=o_edit[col_o], key="txt_o")
                if st.button("Aggiorna", key="btn_o"):
                    supabase.table("Operatori").update({col_o: n_val_o}).eq("id", o_edit["id"]).execute()
                    st.rerun()

            with st.expander("🗑️ Elimina Operatore"):
                o_del = st.selectbox("Elimina operatore", options=ops, format_func=lambda x: x[col_o], key="dl_o")
                if st.button("Elimina Definitivamente", type="primary", key="btn_dl_o"):
                    supabase.table("Operatori").delete().eq("id", o_del["id"]).execute()
                    st.rerun()
        
        with st.form("new_op"):
            n_o = st.text_input("➕ Aggiungi Nuovo Operatore")
            if st.form_submit_button("Salva"):
                supabase.table("Operatori").insert({"nome_operatore": n_o}).execute()
                st.rerun()

    # --- SOTTO-TAB: TASK ---
    with c_admin3:
        st.subheader("Elenco Task")
        tasks = get_data("Task")
        cms = get_data("Commesse")
        if tasks and cms:
            df_t = pd.DataFrame(tasks)
            col_t = next((c for c in ["nome_task", "nome", "task"] if c in df_t.columns), df_t.columns[0])
            c_map = {c['id']: c.get('nome_commessa', 'N/A') for c in cms}
            df_t['Progetto'] = df_t['commessa_id'].map(c_map)

            # 1. Visualizzazione
            st.dataframe(df_t[[col_t, "Progetto"]], use_container_width=True)
            st.divider()

            # 2. Pannelli Gestione
            with st.expander("📝 Modifica Task"):
                t_edit = st.selectbox("Seleziona task", options=tasks, format_func=lambda x: x[col_t], key="ed_t")
                n_val_t = st.text_input("Rinomina", value=t_edit[col_t], key="txt_v_t")
                t_comm = st.selectbox("Sposta a Commessa", options=cms, format_func=lambda x: x.get('nome_commessa', 'N/A'), key="ed_t_c")
                if st.button("Salva Modifiche", key="btn_s_t"):
                    supabase.table("Task").update({col_t: n_val_t, "commessa_id": t_comm["id"]}).eq("id", t_edit["id"]).execute()
                    st.rerun()

            with st.expander("🗑️ Elimina Task"):
                t_del = st.selectbox("Elimina task", options=tasks, format_func=lambda x: x[col_t], key="dl_t")
                if st.button("Rimuovi Task", type="primary", key="btn_d_t"):
                    supabase.table("Task").delete().eq("id", t_del["id"]).execute()
                    st.rerun()

        with st.form("new_task"):
            t_n = st.text_input("➕ Nuovo Task")
            t_c = st.selectbox("Associa a Progetto", options=cms, format_func=lambda x: x.get('nome_commessa', 'N/A'))
            if st.form_submit_button("Aggiungi Task"):
                supabase.table("Task").insert({"nome_task": t_n, "commessa_id": t_c['id']}).execute()
                st.rerun()
