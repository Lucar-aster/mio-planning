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
from datetime import datetime, timedelta


# --- FUNZIONI DI INSERIMENTO REALI SU SUPABASE ---

@st.dialog("➕ Nuova Commessa")
def modal_commessa():
    nome = st.text_input("Nome Commessa")
    cliente = st.text_input("Cliente (Opzionale)")
    if st.button("Salva nel Database", type="primary"):
        if nome:
            try:
                # Inserimento in Supabase
                supabase.table("Commesse").insert({"nome_commessa": nome, "cliente": cliente}).execute()
                st.success("Commessa salvata!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")
        else:
            st.warning("Inserisci il nome della commessa.")

@st.dialog("📑 Nuovo Task")
def modal_task():
    # Recuperiamo le commesse per il menu a tendina
    res_c = supabase.table("Commesse").select("id, nome_commessa").execute()
    commesse = {c['nome_commessa']: c['id'] for c in res_c.data}
    
    nome_t = st.text_input("Nome del Task")
    scelta_c = st.selectbox("Associa a Commessa", options=list(commesse.keys()))
    
    if st.button("Crea Task", type="primary"):
        if nome_t:
            try:
                supabase.table("Task").insert({
                    "nome_task": nome_t, 
                    "commessa_id": commesse[scelta_c]
                }).execute()
                st.success("Task creato!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

@st.dialog("⏱️ Nuovo Log Tempi")
def modal_log():
    try:
        # 1. Recupero dati necessari da Supabase
        res_c = supabase.table("Commesse").select("id, nome_commessa").execute()
        res_t = supabase.table("Task").select("id, nome_task, commessa_id").execute()
        res_o = supabase.table("Operatori").select("nome").execute() # Assumendo che la colonna si chiami 'nome'
        
        commesse_dict = {c['nome_commessa']: c['id'] for c in res_c.data}
        operatori_lista = [o['nome'] for o in res_o.data]
        all_tasks = res_t.data

        # 2. Input Operatore (limitato alla tabella Operatori)
        operatore = st.selectbox("Seleziona Operatore", options=operatori_lista)

        # 3. Selezione Commessa (per filtrare i task)
        scelta_c_nome = st.selectbox("Seleziona Commessa", options=list(commesse_dict.keys()))
        id_commessa_scelta = commesse_dict[scelta_c_nome]

        # 4. Selezione Task (filtrato in base alla commessa scelta sopra)
        tasks_filtrati = {t['nome_task']: t['id'] for t in all_tasks if t['commessa_id'] == id_commessa_scelta}
        
        if not tasks_filtrati:
            st.warning("Nessun task trovato per questa commessa.")
            scelta_t_nome = None
        else:
            scelta_t_nome = st.selectbox("Seleziona Task", options=list(tasks_filtrati.keys()))

        # 5. Date
        col1, col2 = st.columns(2)
        inizio = col1.date_input("Data Inizio", datetime.now())
        fine = col2.date_input("Data Fine", datetime.now())
        
        # 6. Salvataggio
        if st.button("Registra Log", type="primary"):
            if operatore and scelta_t_nome:
                supabase.table("Log_Tempi").insert({
                    "operatore": operatore,
                    "task_id": tasks_filtrati[scelta_t_nome],
                    "inizio": str(inizio),
                    "fine": str(fine)
                }).execute()
                st.success("Log registrato con successo!")
                st.rerun()
            else:
                st.error("Assicurati di aver selezionato tutti i campi.")

    except Exception as e:
        st.error(f"Errore nel caricamento dei dati: {e}")

@st.dialog("📝 Modifica o Elimina Log")
def modal_edit_log(log_id, data_corrente):
    try:
        # 1. Recupero dati necessari da Supabase
        res_c = supabase.table("Commesse").select("id, nome_commessa").execute()
        res_t = supabase.table("Task").select("id, nome_task, commessa_id").execute()
        res_o = supabase.table("Operatori").select("nome").execute()
        
        commesse_dict = {c['nome_commessa']: c['id'] for c in res_c.data}
        inv_commesse_dict = {v: k for k, v in commesse_dict.items()}
        operatori_lista = [o['nome'] for o in res_o.data]
        all_tasks = res_t.data

        # 2. SELEZIONE OPERATORE
        nuovo_op = st.selectbox("Operatore", options=operatori_lista, 
                                index=operatori_lista.index(data_corrente['operatore']) if data_corrente['operatore'] in operatori_lista else 0)

        # 3. SELEZIONE COMMESSA (Aggiunta)
        # Recuperiamo la commessa attuale del task per pre-selezionarla
        task_attuale = next((t for t in all_tasks if t['id'] == data_corrente['task_id']), None)
        id_commessa_attuale = task_attuale['commessa_id'] if task_attuale else list(commesse_dict.values())[0]
        nome_commessa_attuale = inv_commesse_dict.get(id_commessa_attuale, list(commesse_dict.keys())[0])

        scelta_c_nome = st.selectbox("Commessa", options=list(commesse_dict.keys()), 
                                     index=list(commesse_dict.keys()).index(nome_commessa_attuale))
        id_commessa_scelta = commesse_dict[scelta_c_nome]

        # 4. SELEZIONE TASK (Filtrato per Commessa)
        tasks_filtrati = {t['nome_task']: t['id'] for t in all_tasks if t['commessa_id'] == id_commessa_scelta}
        
        if not tasks_filtrati:
            st.warning("Nessun task trovato per questa commessa.")
            nuovo_t_id = None
        else:
            # Pre-selezioniamo il task originale se appartiene alla commessa scelta, altrimenti il primo
            lista_nomi_t = list(tasks_filtrati.keys())
            idx_t = 0
            if data_corrente['task_id'] in tasks_filtrati.values():
                idx_t = list(tasks_filtrati.values()).index(data_corrente['task_id'])
            
            nuovo_t_nome = st.selectbox("Task", options=lista_nomi_t, index=idx_t)
            nuovo_t_id = tasks_filtrati[nuovo_t_nome]

        # 5. MODIFICA DATE (Inizio e Fine)
        def safe_date(d):
            try:
                return pd.to_datetime(d).date()
            except:
                return datetime.now().date()

        col1, col2 = st.columns(2)
        nuovo_inizio = col1.date_input("Inizio", safe_date(data_corrente['inizio']))
        nuovo_fine = col2.date_input("Fine", safe_date(data_corrente['fine']))

        st.divider()
        
        # 6. TASTI AZIONE
        c1, c2 = st.columns(2)
        if c1.button("💾 Salva Modifiche", type="primary", use_container_width=True):
            if nuovo_t_id:
                supabase.table("Log_Tempi").update({
                    "operatore": nuovo_op,
                    "task_id": nuovo_t_id,
                    "inizio": str(nuovo_inizio),
                    "fine": str(nuovo_fine)
                }).eq("id", log_id).execute()
                st.session_state.chart_key += 1
                st.success("Log aggiornato!")
                st.rerun()
            else:
                st.error("Seleziona un task valido.")
        
        if c2.button("🗑️ Elimina", type="secondary", use_container_width=True):
            supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
            st.session_state.chart_key += 1
            st.warning("Log eliminato.")
            st.rerun()
            
        if btn_col3.button("✖️ Annulla", type="secondary", use_container_width=True):
            # Non facciamo nulla al database, resettiamo solo il grafico
            st.session_state.chart_key += 1 # Pulizia evidenziazione
            st.rerun()

    except Exception as e:
        st.error(f"Errore nella modifica: {e}")

# --- TAB 1: PLANNING  ---
with tabs[0]:
    st.header("📊 Progetti Aster Contract")
    if 'chart_key' not in st.session_state:
        st.session_state.chart_key = 0
    
    try:
        logs = get_data("Log_Tempi")
        res_tasks = get_data("Task")
        res_commesse = get_data("Commesse")
        
        if logs and res_tasks and res_commesse:
            # 1. PREPARAZIONE DATI
            task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in res_tasks}
            commessa_map = {c['id']: c['nome_commessa'] for c in res_commesse}
            
            df_raw = pd.DataFrame(logs)
            df_raw['Inizio'] = pd.to_datetime(df_raw['inizio']).dt.normalize()
            df_raw['Fine'] = pd.to_datetime(df_raw['fine']).dt.normalize()
            df_raw['Commessa'] = df_raw['task_id'].apply(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
            df_raw['Task'] = df_raw['task_id'].apply(lambda x: task_info[x]['nome'] if x in task_info else "N/A")

            # 2. FUSIONE LOG
            df_sorted = df_raw.sort_values(['operatore', 'task_id', 'Inizio'])
            merged_data = []
            if not df_sorted.empty:
                current_row = df_sorted.iloc[0].to_dict()
                for i in range(1, len(df_sorted)):
                    next_row = df_sorted.iloc[i].to_dict()
                    if (next_row['operatore'] == current_row['operatore'] and 
                        next_row['task_id'] == current_row['task_id'] and 
                        next_row['Inizio'] <= current_row['Fine'] + timedelta(days=1)):
                        current_row['Fine'] = max(current_row['Fine'], next_row['Fine'])
                    else:
                        merged_data.append(current_row)
                        current_row = next_row
                merged_data.append(current_row)
            df = pd.DataFrame(merged_data)
            
            # Calcolo durata precisa per allineamento barre
            df['Durata_ms'] = ((df['Fine'] + pd.Timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000

            # 3. FILTRI
            col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
            lista_op = sorted(df_raw['operatore'].unique().tolist())
            f_commessa = col_f1.multiselect("Progetti", options=sorted(df['Commessa'].unique()))
            f_operatore = col_f2.multiselect("Operatori", options=lista_op)
            scala = col_f3.selectbox("Visualizzazione", ["Settimana", "Mese", "Trimestre"], index=1)
            if col_f4.button("📍 Oggi", use_container_width=True): st.rerun()

            df_plot = df.copy()
            if f_commessa: df_plot = df_plot[df_plot['Commessa'].isin(f_commessa)]
            if f_operatore: df_plot = df_plot[df_plot['operatore'].isin(f_operatore)]
            df_plot = df_plot.sort_values(by=['Commessa', 'Task'], ascending=[False, False])
            # 3.2 --- SEZIONE TASTI RAPIDI ---
            st.write("") # Spazio
            c1, c2, c3, _ = st.columns([1, 1, 1, 2])
            if c1.button("➕ Commessa", use_container_width=True): modal_commessa()
            if c2.button("📑 Task", use_container_width=True): modal_task()
            if c3.button("⏱️ Log", use_container_width=True): modal_log()
            st.divider()
            
            # --- 4. LOGICA WEEKEND E FESTIVITÀ (FIX ALLINEAMENTO) ---
            oggi = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            x_min_sh = oggi - timedelta(days=100)
            x_max_sh = oggi + timedelta(days=100)
            festivita_it = ["01-01", "06-01", "25-04", "01-05", "02-06", "15-08", "01-11", "08-12", "25-12", "26-12"]
            
            shapes = []
            curr = x_min_sh
            while curr <= x_max_sh:
                if curr.weekday() >= 5 or curr.strftime("%d-%m") in festivita_it:
                    shapes.append(dict(
                        type="rect",
                        # Forza l'inizio e la fine al limite esatto del giorno
                        x0=curr.strftime("%Y-%m-%d 00:00:00"),
                        x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
                        y0=0, y1=1, yref="paper",
                        fillcolor="rgba(180, 180, 180, 0.3)",
                        layer="below", line_width=0
                    ))
                curr += timedelta(days=1)

            # --- 5. CONFIGURAZIONE SCALA ---
            formato_it = "%d/%m<br>Sett %V<br>%a"
            if scala == "Settimana":
                x_range = [oggi - timedelta(days=3), oggi + timedelta(days=5)]
                x_dtick = 86400000 
            elif scala == "Mese":
                x_range = [oggi - timedelta(days=15), oggi + timedelta(days=16)]
                x_dtick = 86400000 * 2
            else:
                x_range = [oggi - timedelta(days=45), oggi + timedelta(days=45)]
                x_dtick = 86400000 * 7

            # --- 6. GRAFICO ---
            fig = go.Figure()
            mesi_it = {1:"Gen", 2:"Feb", 3:"Mar", 4:"Apr", 5:"Mag", 6:"Giu", 7:"Lug", 8:"Ago", 9:"Set", 10:"Ott", 11:"Nov", 12:"Dic"}
            soft_colors = ["#8dbad2", "#a5d6a7", "#ffcc80", "#ce93d8", "#b0bec5", "#ffab91"]
            color_map = {op: soft_colors[i % len(soft_colors)] for i, op in enumerate(lista_op)}

            for op in df_plot['operatore'].unique():
                df_op = df_plot[df_plot['operatore'] == op]
                df_op['Inizio_Str'] = df_op['Inizio'].apply(lambda x: f"{x.day} {mesi_it[x.month]}")
                df_op['Fine_Str'] = df_op['Fine'].apply(lambda x: f"{x.day} {mesi_it[x.month]}")

                fig.add_trace(go.Bar(
                    base=df_op['Inizio'], x=df_op['Durata_ms'], y=[df_op['Commessa'], df_op['Task']],
                    orientation='h', name=op, offsetgroup=op,
                    marker=dict(color=color_map[op], cornerradius=10), width=0.4,
                    customdata=df_op[['id', 'Commessa', 'Task', 'operatore', 'Inizio_Str', 'Fine_Str']],
                    hovertemplate="<b>%{customdata[2]}</b><br>%{customdata[0]}<br>%{customdata[1]}<br>Periodo: %{customdata[3]} - %{customdata[4]}<extra></extra>"
                ))

            fig.update_layout(
                clickmode='event+select', barmode='group', dragmode='pan', plot_bgcolor="white",
                height=550 + (len(df_plot.groupby(['Commessa', 'Task'])) * 40),
                margin=dict(l=10, r=20, t=120, b=50),
                shapes=shapes,
                xaxis=dict(
                    type="date", side="top", range=x_range, dtick=x_dtick,
                    tickformat=formato_it, tickangle=0,
                    tickfont=dict(size=9, color="#444"),
                    # Rimuove lo spazio bianco iniziale/finale dell'asse per l'allineamento
                    rangebreaks=[dict(values=[])], 
                    showgrid=True, gridcolor="#e0e0e0",
                    rangeslider=dict(visible=True, thickness=0.04)
                ),
                yaxis=dict(autorange="reversed", gridcolor="#f5f5f5"),
                legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center")
            )

            fig.add_vline(x=oggi.timestamp() * 1000, line_width=2, line_color="#ff5252")

            event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key=f"gantt_chart_{st.session_state.chart_key}", config={
                'scrollZoom': True, 'displaylogo': False,
                'locale': 'it',
                'locales': {
                    'it': {
                        'dictionary': {
                            'month_names': ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'],
                            'month_names_short': ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'],
                            'day_names': ['Domenica', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato'],
                            'day_names_short': ['Dom', 'Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab'],
                            'firstdayofweek': 1
                        }
                    }
                }
            })
            if event and "selection" in event and event["selection"]["points"]:
                # Estraiamo i dati dal customdata del punto cliccato
                point = event["selection"]["points"][0]
                c_data = point["customdata"]
    
                log_id_scelto = c_data[0]
                data_info = {
                    "operatore": c_data[1],
                    "task_id": c_data[2],
                    "inizio": c_data[3],
                    "fine": c_data[4]
                }
                modal_edit_log(log_id_scelto, data_info)
              
                
        else:
            st.info("Benvenuto! Inizia creando una commessa e un task.")
            if st.button("Aggiungi la prima Commessa"): modal_commessa()
    except Exception as e:
        st.error(f"Errore: {e}")
        
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
