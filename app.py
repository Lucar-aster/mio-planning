import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import textwrap

# --- 1. CONFIGURAZIONE PAGINA ---
LOGO_URL = "https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png"
st.set_page_config(page_title="Aster Contract", page_icon=LOGO_URL, layout="wide")

# --- 2. CSS ---
st.markdown(f"""
    <style>
    header[data-testid="stHeader"] {{ visibility: hidden; height: 0px; }}
    .block-container {{ padding-top: 0rem !important; }}
    .compact-title {{ display: flex; align-items: center; gap: 12px; padding-top: 10px; }}
    .compact-title h1 {{ font-size: 26px !important; color: #1E3A8A; margin: 0; }}
    .spacer-btns {{ margin-top: 15px; margin-bottom: 10px; }}
    </style>
    <div class="compact-title">
        <img src="{LOGO_URL}" width="40">
        <h1>Progetti Aster Contract</h1>
    </div>
    <hr style="margin-top: 5px; margin-bottom: 15px; border: 0; border-top: 1px solid #eee;">
""", unsafe_allow_html=True)

# --- 3. CONNESSIONE ---
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

if 'chart_key' not in st.session_state:
    st.session_state.chart_key = 0

def get_data(table):
    try: return supabase.table(table).select("*").execute().data
    except: return []

# --- MODALI ---
@st.dialog("📝 Modifica Log")
def modal_edit_log(log_id, current_op, current_start, current_end):
    st.write(f"Modifica Log ID: {log_id}")
    new_op = st.text_input("Operatore", value=current_op)
    c1, c2 = st.columns(2)
    new_start = c1.date_input("Inizio", value=pd.to_datetime(current_start))
    new_end = c2.date_input("Fine", value=pd.to_datetime(current_end))
    col1, col2 = st.columns(2)
    if col1.button("Aggiorna", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").update({"operatore": new_op, "inizio": str(new_start), "fine": str(new_end)}).eq("id", log_id).execute()
        st.rerun()
    if col2.button("Elimina", use_container_width=True):
        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
        st.rerun()

@st.dialog("➕ Nuova Commessa")
def modal_commessa():
    n = st.text_input("Nome Commessa")
    if st.button("Salva", use_container_width=True):
        supabase.table("Commesse").insert({"nome_commessa": n}).execute()
        st.rerun()

@st.dialog("📑 Nuovo Task")
def modal_task():
    cms = {c['nome_commessa']: c['id'] for c in get_data("Commesse")}
    n = st.text_input("Nome Task")
    c = st.selectbox("Commessa", options=list(cms.keys()))
    if st.button("Crea", use_container_width=True):
        supabase.table("Task").insert({"nome_task": n, "commessa_id": cms[c]}).execute()
        st.rerun()

@st.dialog("⏱️ Nuovo Log")
def modal_log():
    ops_list = [o['nome'] for o in get_data("Operatori")]
    tk_data = get_data("Task")
    cm_data = {c['id']: c['nome_commessa'] for c in get_data("Commesse")}
    op = st.selectbox("Operatore", ops_list)
    t_opts = {f"{cm_data.get(t['commessa_id'])} - {t['nome_task']}": t['id'] for t in tk_data}
    scelta = st.selectbox("Task", list(t_opts.keys()))
    c1, c2 = st.columns(2)
    i = c1.date_input("Inizio")
    f = c2.date_input("Fine")
    if st.button("Registra", use_container_width=True):
        supabase.table("Log_Tempi").insert({"operatore": op, "task_id": t_opts[scelta], "inizio": str(i), "fine": str(f)}).execute()
        st.rerun()

# --- 4. LOGICA MERGE E ETICHETTE ---
def merge_consecutive_logs(df):
    if df.empty: return df
    df = df.sort_values(['operatore', 'Commessa', 'Task', 'Inizio'])
    merged = []
    for _, group in df.groupby(['operatore', 'Commessa', 'Task']):
        current_row = None
        for _, row in group.iterrows():
            if current_row is None: current_row = row.to_dict()
            else:
                if row['Inizio'] <= (pd.to_datetime(current_row['Fine']) + timedelta(days=1)):
                    current_row['Fine'] = max(pd.to_datetime(current_row['Fine']), pd.to_datetime(row['Fine']))
                    current_row['Durata_ms'] = ((pd.to_datetime(current_row['Fine']) + timedelta(days=1)) - pd.to_datetime(current_row['Inizio'])).total_seconds() * 1000
                else:
                    merged.append(current_row)
                    current_row = row.to_dict()
        if current_row: merged.append(current_row)
    return pd.DataFrame(merged)

def get_it_date_label(dt, delta):
    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    giorni = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    if delta > 40: return f"Sett. {dt.isocalendar()[1]}<br>{mesi[dt.month-1]}"
    return f"{giorni[dt.weekday()]} {dt.day:02d}<br>{mesi[dt.month-1]}<br>Sett. {dt.isocalendar()[1]}"

# --- 5. GANTT FRAGMENT ---
@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, color_map, oggi_dt, x_range, delta_giorni, shapes):
    if df_plot.empty:
        st.info("Nessun dato trovato.")
        return

    df_merged = merge_consecutive_logs(df_plot)
    fig = go.Figure()

    for op in df_merged['operatore'].unique():
        df_op = df_merged[df_merged['operatore'] == op]
        c_w = ["<br>".join(textwrap.wrap(str(c), 15)) for c in df_op['Commessa']]
        t_w = ["<br>".join(textwrap.wrap(str(t), 20)) for t in df_op['Task']]
        
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], x=df_op['Durata_ms'], y=[c_w, t_w],
            orientation='h', name=op, alignmentgroup="g1", offsetgroup=op,
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12),
            width=0.4, 
            customdata=df_op[['id', 'operatore', 'Inizio', 'Fine', 'Commessa', 'Task']],
            # NUOVO HOVERTEMPLTE RICHIESTO
            hovertemplate=(
                "<b>%{customdata[4]} - %{customdata[5]}</b><br>" +
                "%{customdata[1]}<br>" +
                "%{customdata[2]|%d/%m/%Y} - %{customdata[3]|%d/%m/%Y}" +
                "<extra></extra>"
            )
        ))
    
    grid_vals = pd.date_range(start=x_range[0], end=x_range[1], freq='D')
    if 15 < delta_giorni <= 40:
        tick_vals = grid_vals[::2]
    elif delta_giorni > 40:
        tick_vals = pd.date_range(start=x_range[0], end=x_range[1], freq='W-MON')
    else:
        tick_vals = grid_vals

    tick_text = [get_it_date_label(d, delta_giorni) for d in tick_vals]
    
    fig.update_layout(
        height=400 + (len(df_merged[['Commessa', 'Task']].drop_duplicates()) * 35),
        margin=dict(l=10, r=10, t=40, b=0), shapes=shapes, barmode='overlay', dragmode='pan',
        xaxis=dict(
            type="date", side="top", range=x_range, fixedrange=False,
            tickmode="array", tickvals=tick_vals, ticktext=tick_text,
            showgrid=True, gridcolor="#e0e0e0", dtick=86400000.0
        ),
        yaxis=dict(autorange="reversed", showgrid=True, gridcolor="#f0f0f0", showdividers=True, dividercolor="grey", fixedrange=True),
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5, font=dict(size=10)),
        clickmode='event+select'
    )
    fig.add_vline(x=oggi_dt.timestamp() * 1000, line_width=2, line_color="red")
    
    selected = st.plotly_chart(fig, use_container_width=True, key=f"gantt_{st.session_state.chart_key}", on_select="rerun", config={'scrollZoom': False, 'displayModeBar': False})
    
    if selected and "selection" in selected and "points" in selected["selection"]:
        p = selected["selection"]["points"]
        if p and "customdata" in p[0]:
            modal_edit_log(p[0]["customdata"][0], p[0]["customdata"][1], p[0]["customdata"][2], p[0]["customdata"][3])

# --- 6. MAIN UI ---
tabs = st.tabs(["📊 Timeline", "📋 Dati", "⚙️ Setup"])
l, tk, cm, ops_list = get_data("Log_Tempi"), get_data("Task"), get_data("Commesse"), get_data("Operatori")

with tabs[0]:
    if l and tk and cm:
        tk_m = {t['id']: {'n': t['nome_task'], 'c': t['commessa_id']} for t in tk}
        cm_m = {c['id']: c['nome_commessa'] for c in cm}
        df = pd.DataFrame(l)
        df['Inizio'] = pd.to_datetime(df['inizio']).dt.normalize()
        df['Fine'] = pd.to_datetime(df['fine']).dt.normalize()
        df['Commessa'] = df['task_id'].apply(lambda x: cm_m.get(tk_m.get(x, {}).get('c'), "N/A"))
        df['Task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('n', "N/A"))
        df['Durata_ms'] = ((df['Fine'] + pd.Timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000

        c_f1, c_f2, c_f3 = st.columns([2, 2, 4])
        with c_f3:
            cs, cd = st.columns([1, 1])
            scala = cs.selectbox("Scala", ["Settimana", "Mese", "Trimestre", "Personalizzato"], index=1)
            f_custom = cd.date_input("Periodo", value=None) if scala == "Personalizzato" else None

        f_c = c_f1.multiselect("Progetti", sorted(df['Commessa'].unique()))
        f_o = c_f2.multiselect("Operatori", sorted(df['operatore'].unique()))

        st.markdown('<div class="spacer-btns"></div>', unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("➕ Commessa", use_container_width=True): modal_commessa()
        if b2.button("📑 Task", use_container_width=True): modal_task()
        if b3.button("⏱️ Log", use_container_width=True): modal_log()
        if b4.button("📍 Oggi", use_container_width=True): 
            st.session_state.chart_key += 1
            st.rerun()

        oggi_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        df_p = df.copy()
        if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
        if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]

        if scala == "Personalizzato" and f_custom and len(f_custom) == 2:
            x_range = [pd.to_datetime(f_custom[0]), pd.to_datetime(f_custom[1])]
        else:
            d = {"Settimana": 4, "Mese": 15, "Trimestre": 45}.get(scala, 15)
            x_range = [oggi_dt - timedelta(days=d), oggi_dt + timedelta(days=d)]

        shapes = []
        curr = x_range[0] - timedelta(days=2)
        while curr <= x_range[1] + timedelta(days=32):
            if curr.weekday() >= 5:
                shapes.append(dict(type="rect", x0=curr, x1=curr+timedelta(days=1), y0=0, y1=1, yref="paper", fillcolor="rgba(200,200,200,0.15)", layer="below", line_width=0))
            curr += timedelta(days=1)
        
        render_gantt_fragment(df_p, {o['nome']: o.get('colore', '#8dbad2') for o in ops_list}, oggi_dt, x_range, (x_range[1]-x_range[0]).days, shapes)
        
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
