import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import platform
import plotly.io as pio

# 1. CONFIGURAZIONE (DEVE ESSERE LA PRIMA ISTRUZIONE STREAMLIT)
LOGO_URL = "https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png"
st.set_page_config(page_title="Aster Contract", page_icon=LOGO_URL, layout="wide")

# 2. CSS CUSTOM
st.markdown("""
    <style>
    header[data-testid="stHeader"] { visibility: hidden; height: 0%; }
    .block-container { padding-top: 1rem!important; }
    [data-testid="stVerticalBlock"] { gap: 0.5rem; }
    </style>
    <div style='display: flex; align-items: center; gap: 10px;'>
        <img src='""" + LOGO_URL + """' width='40'>
        <h1 style='margin: 0; color: #1E3A8A; font-size: 24px;'>Progetti Aster Contract</h1>
    </div>
    <hr style='margin: 10px 0;'>
""", unsafe_allow_html=True)

# 3. CONNESSIONE SUPABASE
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

# 4. SESSION STATE
if 'chart_key' not in st.session_state:
    st.session_state.chart_key = 0

# --- FUNZIONI RECUPERO DATI ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return res.data
    except:
        return []

# --- FRAGMENT GRAFICO ---
@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, color_map, oggi_dt, x_range, x_dtick):
    fig = go.Figure()
    
    for op in df_plot['operatore'].unique():
        df_op = df_plot[df_plot['operatore'] == op]
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], 
            x=df_op['Durata_ms'], 
            y=[df_op['Commessa'], df_op['Task']],
            orientation='h', name=op,
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=10),
            customdata=df_op[['id', 'operatore', 'task_id', 'inizio', 'fine']],
            hovertemplate="<b>%{y}</b><br>%{customdata[3]} al %{customdata[4]}<extra></extra>"
        ))

    fig.update_layout(
        height=450 + (len(df_plot) * 5),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(type="date", range=x_range, dtick=x_dtick, side="top", gridcolor="#f0f0f0"),
        yaxis=dict(autorange="reversed", showdividers=True),
        plot_bgcolor="white",
        showlegend=True,
        legend=dict(orientation="h", y=-0.1)
    )
    
    fig.add_vline(x=oggi_dt.timestamp() * 1000, line_width=2, line_color="red")
    st.plotly_chart(fig, use_container_width=True, key=f"gantt_{st.session_state.chart_key}")

# --- INTERFACCIA PRINCIPALE ---
tabs = st.tabs(["📊 Timeline", "⚙️ Configurazione"])

with tabs[0]:
    # Caricamento dati
    logs = get_data("Log_Tempi")
    res_tasks = get_data("Task")
    res_commesse = get_data("Commesse")
    res_ops = get_data("Operatori")

    if logs and res_tasks and res_commesse:
        # Preparazione DataFrame
        task_map = {t['id']: {'n': t['nome_task'], 'c': t['commessa_id']} for t in res_tasks}
        comm_map = {c['id']: c['nome_commessa'] for c in res_commesse}
        color_map = {o['nome']: o.get('colore', '#8dbad2') for o in res_ops}

        df = pd.DataFrame(logs)
        df['Inizio'] = pd.to_datetime(df['inizio']).dt.normalize()
        df['Fine'] = pd.to_datetime(df['fine']).dt.normalize()
        df['Commessa'] = df['task_id'].apply(lambda x: comm_map.get(task_map.get(x, {}).get('c'), "N/A"))
        df['Task'] = df['task_id'].apply(lambda x: task_map.get(x, {}).get('n', "N/A"))
        df['Durata_ms'] = ((df['Fine'] + pd.Timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000

        # FILTRI UI
        c1, c2, c3 = st.columns([2, 2, 4])
        with c1: f_p = st.multiselect("Progetti", options=sorted(df['Commessa'].unique()))
        with c2: f_o = st.multiselect("Operatori", options=sorted(df['operatore'].unique()))
        
        with c3:
            ci1, ci2 = st.columns([1, 1])
            with ci1:
                scala = st.selectbox("Scala", ["Settimana", "Mese", "Trimestre", "Personalizzato"], index=1)
            
            filtro_custom = None
            if scala == "Personalizzato":
                with ci2:
                    filtro_custom = st.date_input("Periodo", value=None, format="DD/MM/YYYY")

        # LOGICA RANGE
        oggi_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        df_plot = df.copy()
        if f_p: df_plot = df_plot[df_plot['Commessa'].isin(f_p)]
        if f_o: df_plot = df_plot[df_plot['operatore'].isin(f_o)]

        if scala == "Personalizzato" and filtro_custom and len(filtro_custom) == 2:
            x_range = [pd.to_datetime(filtro_custom[0]), pd.to_datetime(filtro_custom[1])]
        else:
            days = {"Settimana": 4, "Mese": 15, "Trimestre": 45}.get(scala, 15)
            x_range = [oggi_dt - timedelta(days=days), oggi_dt + timedelta(days=days)]

        delta = (x_range[1] - x_range[0]).days
        x_dtick = 86400000 if delta <= 7 else 86400000 * 7

        # BOTTONI
        bc1, bc2, bc3 = st.columns([1,1,1])
        if bc1.button("📍 Oggi"): 
            st.session_state.chart_key += 1
            st.rerun()

        # RENDER
        render_gantt_fragment(df_plot, color_map, oggi_dt, x_range, x_dtick)
    else:
        st.info("Nessun dato disponibile.")
        
# --- TAB 2: REGISTRA TEMPI (CON COLONNA COMMESSA) ---
with tabs[1]:
    st.header("📝 Gestione Attività")
    
    logs = get_data("Log_Tempi")
    cms = get_data("Commesse")
    tasks = get_data("Task")
    ops = get_data("Operatori")

    if logs and cms and tasks and ops:
        # 1. PREPARAZIONE DATAFRAME
        df_edit = pd.DataFrame(logs)
        
        # Conversione date obbligatoria per evitare errori nell'editor
        df_edit['inizio'] = pd.to_datetime(df_edit['inizio']).dt.date
        df_edit['fine'] = pd.to_datetime(df_edit['fine']).dt.date
        
        # Mappature per ricostruire i nomi
        task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in tasks}
        commessa_map = {c['id']: c['nome_commessa'] for c in cms}
        
        # Creiamo le colonne leggibili
        df_edit['task_nome'] = df_edit['task_id'].map(lambda x: task_info[x]['nome'] if x in task_info else "N/A")
        df_edit['commessa_nome'] = df_edit['task_id'].map(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
        
        # 2. ORDINAMENTO COLONNE RICHIESTO
        # Ordine: commessa, task, operatore, inizio, fine (ID nascosto)
        cols_ordine = ['id', 'commessa_nome', 'task_nome', 'operatore', 'inizio', 'fine']
        df_display = df_edit[cols_ordine].copy()

        st.info("💡 Modifica i dati direttamente in tabella e premi il tasto Salva.")

        # 3. IL DATA EDITOR (CORRETTO)
        edited_df = st.data_editor(
            df_display,
            key="log_editor_v3",
            num_rows="dynamic",
            disabled=["id", "commessa_nome"], 
            column_config={
                "id": None, 
                "commessa_nome": st.column_config.TextColumn("Commessa"),
                "task_nome": st.column_config.SelectboxColumn(
                    "Task", 
                    options=[t['nome_task'] for t in tasks], 
                    required=True
                ),
                "operatore": st.column_config.TextColumn("Operatore", required=True),
                "inizio": st.column_config.DateColumn("Inizio", format="DD/MM/YYYY"),
                "fine": st.column_config.DateColumn("Fine", format="DD/MM/YYYY"),
            },
            hide_index=True,
            use_container_width=True
        )

        # 4. SALVATAGGIO
        if st.button("💾 Salva modifiche", type="primary", use_container_width=True):
            try:
                inv_task_map = {t['nome_task']: t['id'] for t in tasks}
                for index, row in edited_df.iterrows():
                    update_payload = {
                        "operatore": row['operatore'],
                        "task_id": inv_task_map.get(row['task_nome']),
                        "inizio": str(row['inizio']),
                        "fine": str(row['fine'])
                    }
                    supabase.table("Log_Tempi").update(update_payload).eq("id", row['id']).execute()
                st.success("Database aggiornato!")
                st.rerun()
            except Exception as e:
                st.error(f"Errore: {e}")

    else:
        st.info("Nessun dato disponibile.")
        
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

            df_display = df_o[[col_o, "colore"]].copy() if "colore" in df_o.columns else df_o[[col_o]].copy()

            def style_colore(v):
                # Colora lo sfondo della cella con il suo stesso valore HEX
                return f'background-color: {v}; color: white; font-weight: bold; border-radius: 5px;' if v else ''

            st.write("Lista operatori attivi:")
            st.dataframe(
                df_display.style.applymap(style_colore, subset=['colore']) if "colore" in df_display.columns else df_display,
                use_container_width=True,
                hide_index=True
            )
            
            cols_to_show = [col_o]
            if "colore" in df_o.columns:
                cols_to_show.append("colore")
            
            # 1. Visualizzazione
            st.dataframe(df_o[[col_o]], use_container_width=True)
            st.divider()

            # 2. Pannelli Gestione
            with st.expander("📝 Modifica Operatore"):
                o_edit = st.selectbox("Seleziona operatore", options=ops, format_func=lambda x: x[col_o], key="ed_o")
                n_val_o = st.text_input("Nuovo nome", value=o_edit[col_o], key="txt_o")
                colore_attuale = o_edit.get('colore', '#8dbad2')
                n_val_c = st.color_picker("Nuovo colore", value=colore_attuale, key="clr_o")
                if st.button("Aggiorna", key="btn_o"):
                    supabase.table("Operatori").update({
                        col_o: n_val_o, 
                        "colore": n_val_c
                    }).eq("id", o_edit["id"]).execute()
                    st.rerun()
                    
            with st.expander("🗑️ Elimina Operatore"):
                o_del = st.selectbox("Elimina operatore", options=ops, format_func=lambda x: x[col_o], key="dl_o")
                if st.button("Elimina Definitivamente", type="primary", key="btn_dl_o"):
                    supabase.table("Operatori").delete().eq("id", o_del["id"]).execute()
                    st.rerun()
        
        with st.form("new_op"):
            st.write("➕ Aggiungi Nuovo Operatore")
            n_o = st.text_input("Nome")
            c_o = st.color_picker("Assegna Colore", "#8dbad2")
            if st.form_submit_button("Salva"):
                    supabase.table("Operatori").insert({col_o: n_o, "colore": c_o}).execute()
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
