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

# --- 3. CONNESSIONE E CACHING ---
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

@st.cache_data(ttl=60)
def get_cached_data(table):
    try: return supabase.table(table).select("*").execute().data
    except: return []

if 'chart_key' not in st.session_state:
    st.session_state.chart_key = 0

# --- MODALI ---
@st.dialog("📝 Modifica Log")
def modal_edit_log(log_id, current_op, current_start, current_end):
    st.write(f"Modifica Log ID: {log_id}")
    new_op = st.text_input("Operatore", value=current_op)
    c1, c2 = st.columns(2)
    new_start = c1.date_input("Inizio", value=pd.to_datetime(current_start), format="DD/MM/YYYY")
    new_end = c2.date_input("Fine", value=pd.to_datetime(current_end), format="DD/MM/YYYY")
    col1, col2 = st.columns(2)
    if col1.button("Aggiorna", type="primary", use_container_width=True):
        supabase.table("Log_Tempi").update({"operatore": new_op, "inizio": str(new_start), "fine": str(new_end)}).eq("id", log_id).execute()
        get_cached_data.clear()
        st.rerun()
    if col2.button("Elimina", use_container_width=True):
        supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
        get_cached_data.clear()
        st.rerun()

@st.dialog("➕ Nuova Commessa")
def modal_commessa():
    n = st.text_input("Nome Commessa")
    if st.button("Salva", use_container_width=True):
        supabase.table("Commesse").insert({"nome_commessa": n}).execute()
        get_cached_data.clear()
        st.rerun()

@st.dialog("📑 Nuovo Task")
def modal_task():
    cms = {c['nome_commessa']: c['id'] for c in get_cached_data("Commesse")}
    n = st.text_input("Nome Task")
    c = st.selectbox("Commessa", options=list(cms.keys()))
    if st.button("Crea", use_container_width=True):
        supabase.table("Task").insert({"nome_task": n, "commessa_id": cms[c]}).execute()
        get_cached_data.clear()
        st.rerun()

@st.dialog("⏱️ Nuovo Log")
def modal_log():
    ops_list = [o['nome'] for o in get_cached_data("Operatori")]
    cm_data = get_cached_data("Commesse")
    tk_data = get_cached_data("Task")
    op = st.selectbox("Operatore", ops_list)
    cms_dict = {c['nome_commessa']: c['id'] for c in cm_data}
    sel_cm_nome = st.selectbox("Commessa", list(cms_dict.keys()))
    sel_cm_id = cms_dict[sel_cm_nome]
    tasks_filtrati = [t for t in tk_data if t['commessa_id'] == sel_cm_id]
    task_opts = {t['nome_task']: t['id'] for t in tasks_filtrati}
    task_list = list(task_opts.keys()) + ["➕ Aggiungi nuovo task..."]
    sel_task = st.selectbox("Task", task_list)
    new_task_name = st.text_input("Inserisci nome nuovo task") if sel_task == "➕ Aggiungi nuovo task..." else ""
    c1, c2 = st.columns(2)
    i, f = c1.date_input("Inizio"), c2.date_input("Fine")
    if st.button("Registra Log", use_container_width=True):
        target_task_id = None
        if sel_task == "➕ Aggiungi nuovo task...":
            if new_task_name.strip():
                res = supabase.table("Task").insert({"nome_task": new_task_name, "commessa_id": sel_cm_id}).execute()
                if res.data: target_task_id = res.data[0]['id']
            else: st.error("Inserisci nome task"); return
        else: target_task_id = task_opts[sel_task]
        if target_task_id:
            supabase.table("Log_Tempi").insert({"operatore": op, "task_id": target_task_id, "inizio": str(i), "fine": str(f)}).execute()
            get_cached_data.clear()
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
                    merged.append(current_row); current_row = row.to_dict()
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
     # Controllo e validazione delta_giorni
    try:
        delta_giorni = int(delta_giorni)
    except:
        delta_giorni = 20 # Default di sicurezza
        
    df_merged = merge_consecutive_logs(df_plot)
    fig = go.Figure()
    
    # --- Rendering Barre ---
    for op in df_merged['operatore'].unique():
        df_op = df_merged[df_merged['operatore'] == op]
        c_w = ["<br>".join(textwrap.wrap(str(c), 15)) for c in df_op['Commessa']]
        t_w = ["<br>".join(textwrap.wrap(str(t), 20)) for t in df_op['Task']]
        
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], 
            x=df_op['Durata_ms'], 
            y=[c_w, t_w],
            orientation='h', 
            name=op, 
            alignmentgroup="g1", 
            offsetgroup=op,
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=12), 
            width=0.4, 
            customdata=df_op[['id', 'operatore', 'Inizio', 'Fine', 'Commessa', 'Task']],
            hovertemplate="<b>%{customdata[4]} - %{customdata[5]}</b><br>%{customdata[1]}<br>%{customdata[2]|%d/%m/%Y} - %{customdata[3]|%d/%m/%Y}<extra></extra>"
        ))
    # --- GENERAZIONE DINAMICA WEEKEND E GRIGLIA ---
    all_shapes = []
    # Estendiamo il range di 6 mesi per coprire il PAN
    start_pan = x_range[0] - timedelta(days=180)
    end_pan = x_range[1] + timedelta(days=180)
    
    curr = start_pan
    while curr <= end_pan:
        # 1. Linea giornaliera (Griglia)
        all_shapes.append(dict(
            type="line", x0=curr, x1=curr, y0=0, y1=1, yref="paper",
            line=dict(color="#e0e0e0", width=1), layer="below"
        ))
        
        # 2. Rettangolo Weekend (Sabato e Domenica)
        if curr.weekday() >= 5:  # 5=Sabato, 6=Domenica
            all_shapes.append(dict(
                type="rect",
                x0=curr, x1=curr + timedelta(days=1),
                y0=0, y1=1, yref="paper",
                fillcolor="#f0f0f0", opacity=0.5, line_width=0, layer="below"
            ))
        curr += timedelta(days=1)
    
    # --- Gestione Asse X Dinamica ---
    # Definiamo i confini dell'area "cuscinetto" per il PAN
    start_buffer = x_range[0] - timedelta(days=180)
    end_buffer = x_range[1] + timedelta(days=180)
    
    # Scegliamo la frequenza in base alla scala
    if delta_giorni > 60:
        # Vista ampia: un tick ogni Lunedì
        tick_range = pd.date_range(start=start_buffer, end=end_buffer, freq='W-MON')
    elif delta_giorni >20:
        
       full_range = pd.date_range(start=start_buffer, end=end_buffer, freq='D')
       tick_range = full_range[full_range.weekday.isin([0, 2, 4])]
    else:
        # Vista stretta: un tick ogni giorno
        tick_range = pd.date_range(start=start_buffer, end=end_buffer, freq='D')

    # 3. Generiamo i testi solo per i giorni filtrati
    tick_text = [get_it_date_label(d, delta_giorni) for d in tick_range]
    
    fig.update_layout(
        height=400 + (len(df_merged[['Commessa', 'Task']].drop_duplicates()) * 35), # Altezza dinamica OK
        margin=dict(l=10, r=10, t=40, b=0), 
        shapes=all_shapes, 
        barmode='overlay', 
        dragmode='pan',
        xaxis=dict(
            type="date", 
            side="top", 
            range=x_range, 
            fixedrange=False, 
            tickmode="array",
            tickvals=tick_range,
            ticktext=tick_text,
            showgrid=False, 
            zeroline=False,
            anchor="y"
        ),
        yaxis=dict(
            autorange="reversed", 
            showgrid=True, 
            gridcolor="#f0f0f0", 
            showdividers=True, 
            dividercolor="grey", 
            fixedrange=True
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.07, xanchor="center", x=0.5, font=dict(size=10)),
        clickmode='event+select' # Click per modale OK
    )
    
    fig.add_vline(x=oggi_dt.timestamp() * 1000, line_width=2, line_color="red")
    
    # --- Plotly Chart ---
    selected = st.plotly_chart(
        fig, 
        use_container_width=True, 
        key=f"gantt_{st.session_state.chart_key}", 
        on_select="rerun", 
        config={'scrollZoom': False, 'displayModeBar': False}
    )
    
    # --- Logica di selezione per Modifica ---
    if selected and "selection" in selected and "points" in selected["selection"]:
        p = selected["selection"]["points"]
        if p and "customdata" in p[0]:
            modal_edit_log(p[0]["customdata"][0], p[0]["customdata"][1], p[0]["customdata"][2], p[0]["customdata"][3])

# --- 6. MAIN UI ---
tabs = st.tabs(["📊 Timeline", "📋 Dati", "⚙️ Setup"])
l, tk, cm, ops_list = get_cached_data("Log_Tempi"), get_cached_data("Task"), get_cached_data("Commesse"), get_cached_data("Operatori")

with tabs[0]:
    if l and tk and cm:
        tk_m = {t['id']: {'n': t['nome_task'], 'c': t['commessa_id']} for t in tk}
        cm_m = {c['id']: c['nome_commessa'] for c in cm}
        df = pd.DataFrame(l)
        df['Inizio'], df['Fine'] = pd.to_datetime(df['inizio']).dt.normalize(), pd.to_datetime(df['fine']).dt.normalize()
        df['Commessa'] = df['task_id'].apply(lambda x: cm_m.get(tk_m.get(x, {}).get('c'), "N/A"))
        df['Task'] = df['task_id'].apply(lambda x: tk_m.get(x, {}).get('n', "N/A"))
        df['Durata_ms'] = ((df['Fine'] + pd.Timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000
        c_f1, c_f2, c_f3 = st.columns([2, 2, 4])
        with c_f3:
            cs, cd = st.columns([1, 1])
            scala = cs.selectbox("Scala", ["Settimana","2 Settimane", "Mese", "Trimestre", "Semestre", "Personalizzato"], index=1)
            f_custom = cd.date_input("Periodo", value=[datetime.now(), datetime.now() + timedelta(days=7)]) if scala == "Personalizzato" else None
        f_c, f_o = c_f1.multiselect("Progetti", sorted(df['Commessa'].unique())), c_f2.multiselect("Operatori", sorted(df['operatore'].unique()))
        st.markdown('<div class="spacer-btns"></div>', unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("➕ Commessa", use_container_width=True): modal_commessa()
        if b2.button("📑 Task", use_container_width=True): modal_task()
        if b3.button("⏱️ Log", use_container_width=True): modal_log()
        if b4.button("📍 Oggi", use_container_width=True): st.session_state.chart_key += 1; st.rerun()
        oggi_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        df_p = df.copy()
        if f_c: df_p = df_p[df_p['Commessa'].isin(f_c)]
        if f_o: df_p = df_p[df_p['operatore'].isin(f_o)]
        if scala == "Personalizzato" and f_custom and len(f_custom) == 2: x_range = [pd.to_datetime(f_custom[0]), pd.to_datetime(f_custom[1])]
        elif scala == "Personalizzato": st.warning("Seleziona data inizio e fine."); st.stop()
        else:
            d = {"Settimana": 4, "2 Settimane": 8, "Mese": 15, "Trimestre": 45, "Semestre": 90}.get(scala, 15)
            x_range = [oggi_dt - timedelta(days=d), oggi_dt + timedelta(days=d)]
        shapes = []
        curr = x_range[0] - timedelta(days=2)
        while curr <= x_range[1] + timedelta(days=32):
            if curr.weekday() >= 5: shapes.append(dict(type="rect", x0=curr, x1=curr+timedelta(days=1), y0=0, y1=1, yref="paper", fillcolor="rgba(200,200,200,0.15)", layer="below", line_width=0))
            curr += timedelta(days=1)
        render_gantt_fragment(df_p, {o['nome']: o.get('colore', '#8dbad2') for o in ops_list}, oggi_dt, x_range, (x_range[1]-x_range[0]).days, shapes)

# --- TAB 2: GESTIONE ATTIVITÀ (DATA EDITOR) ---
with tabs[1]:
    st.header("📝 Gestione Attività")
    if l is not None and cm and tk:
        df_edit = pd.DataFrame(l)
        df_edit['inizio'] = pd.to_datetime(df_edit['inizio']).dt.date
        df_edit['fine'] = pd.to_datetime(df_edit['fine']).dt.date
        
        task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in tk}
        commessa_map = {c['id']: c['nome_commessa'] for c in cm}
        
        df_edit['task_nome'] = df_edit['task_id'].map(lambda x: task_info[x]['nome'] if x in task_info else "N/A")
        df_edit['commessa_nome'] = df_edit['task_id'].map(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
        
        df_display = df_edit[['id', 'commessa_nome', 'task_nome', 'operatore', 'inizio', 'fine']].copy()
        st.info("💡 Modifica i dati direttamente in tabella e premi il tasto Salva.")

        edited_df = st.data_editor(
            df_display, key="log_editor_v3", num_rows="dynamic",
            disabled=["id", "commessa_nome"],
            column_config={
                "id": None, "commessa_nome": "Commessa",
                "task_nome": st.column_config.SelectboxColumn("Task", options=[t['nome_task'] for t in tk], required=True),
                "operatore": st.column_config.TextColumn("Operatore", required=True),
                "inizio": st.column_config.DateColumn("Inizio", format="DD/MM/YYYY"),
                "fine": st.column_config.DateColumn("Fine", format="DD/MM/YYYY"),
            }, hide_index=True, use_container_width=True
        )

        if st.button("💾 Salva modifiche", type="primary", use_container_width=True):
            inv_tk = {t['nome_task']: t['id'] for t in tk}
            for _, row in edited_df.iterrows():
                payload = {"operatore": row['operatore'], "task_id": inv_tk.get(row['task_nome']), "inizio": str(row['inizio']), "fine": str(row['fine'])}
                supabase.table("Log_Tempi").update(payload).eq("id", row['id']).execute()
            get_cached_data.clear()
            st.success("Database aggiornato!")
            st.rerun()

# --- TAB 3: CONFIGURAZIONE SISTEMA ---
with tabs[2]:
    st.header("⚙️ Configurazione")
    c_admin1, c_admin2, c_admin3 = st.tabs(["🏗️ Commesse", "👥 Operatori", "✅ Task"])

    with c_admin1:
        st.subheader("Elenco Commesse")
        if cm:
            df_c = pd.DataFrame(cm)
            st.dataframe(df_c[["nome_commessa"]], use_container_width=True, hide_index=True)
            with st.expander("📝 Modifica / 🗑️ Elimina"):
                c_sel = st.selectbox("Seleziona commessa", cm, format_func=lambda x: x["nome_commessa"])
                n_c = st.text_input("Nuovo nome", value=c_sel["nome_commessa"])
                col1, col2 = st.columns(2)
                if col1.button("Aggiorna Commessa"):
                    supabase.table("Commesse").update({"nome_commessa": n_c}).eq("id", c_sel["id"]).execute()
                    get_cached_data.clear(); st.rerun()
                confirm_key = f"delete_confirm_{c_sel['id']}"
            
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if col2.button("Elimina Commessa", type="primary"):
                        st.session_state[confirm_key] = True
                        st.rerun()
                else:
                    st.warning(f"⚠️ Sicuro? Saranno eliminati anche tutti i Log e i Task di: {c_sel['nome_commessa']}")
                    c_si, c_no = st.columns(2)
                    
                    if c_si.button("✅ Sì, elimina tutto", type="primary", use_container_width=True):
                        try:
                            # 1. Recuperiamo gli ID dei task associati a questa commessa
                            tasks_da_eliminare = supabase.table("Task").select("id").eq("commessa_id", c_sel["id"]).execute().data
        
                            if tasks_da_eliminare:
                                # Estraiamo solo i valori degli ID in una lista [1, 2, 3...]
                                list_task_ids = [t['id'] for t in tasks_da_eliminare]
            
                                # 2. Eliminiamo i Log che puntano a questi Task
                                # Usiamo l'operatore .in_() per colpire tutti i task_id in un colpo solo
                                supabase.table("Log_Tempi").delete().in_("task_id", list_task_ids).execute()
        
                            # 3. Ora possiamo eliminare i Task della commessa
                            supabase.table("Task").delete().eq("commessa_id", c_sel["id"]).execute()
        
                            # 4. Infine eliminiamo la Commessa
                            supabase.table("Commesse").delete().eq("id", c_sel["id"]).execute()
        
                            # Pulizia e reset
                            st.session_state[confirm_key] = False
                            get_cached_data.clear()
                            st.success("Commessa e tutta la gerarchia di Task e Log eliminati!")
                            st.rerun()
        
                        except Exception as e:
                            st.error(f"Errore durante l'eliminazione a catena: {e}")
                
                    if c_no.button("❌ Annulla", use_container_width=True):
                        st.session_state[confirm_key] = False
                        st.rerun()
                        
            with st.form("new_c_form"):
                st.write("➕ **Aggiungi Nuova Commessa**")
                n_new_c = st.text_input("Nome Commessa")
                submit_new = st.form_submit_button("Salva Commessa")
        
                if submit_new:
                    if n_new_c:
                        supabase.table("Commesse").insert({"nome_commessa": n_new_c}).execute()
                        get_cached_data.clear()
                        st.rerun()
                    else:
                        st.error("Inserisci un nome!")

    with c_admin2:
        st.subheader("Elenco Operatori")
        if ops_list:
            df_o = pd.DataFrame(ops_list)
            st.dataframe(df_o[["nome", "colore"]].style.apply(lambda x: [f"background-color: {val}" for val in df_o['colore']], subset=['colore']), 
                use_container_width=True, 
                hide_index=True)
            with st.expander("📝 Modifica / 🗑️ Elimina"):
                o_sel = st.selectbox("Seleziona operatore", ops_list, format_func=lambda x: x["nome"])
                n_o = st.text_input("Nome", value=o_sel["nome"])
                c_o = st.color_picker("Colore", value=o_sel.get("colore", "#8dbad2"))
                col1, col2 = st.columns(2)
                if col1.button("Aggiorna Operatore"):
                    supabase.table("Operatori").update({"nome": n_o, "colore": c_o}).eq("id", o_sel["id"]).execute()
                    get_cached_data.clear(); st.rerun()
                if col2.button("Elimina Operatore", type="primary"):
                    supabase.table("Operatori").delete().eq("id", o_sel["id"]).execute()
                    get_cached_data.clear(); st.rerun()
        with st.form("new_op"):
            n_new_o = st.text_input("➕ Nuovo Operatore")
            c_new_o = st.color_picker("Colore", "#8dbad2")
            if st.form_submit_button("Salva"):
                supabase.table("Operatori").insert({"nome": n_new_o, "colore": c_new_o}).execute()
                get_cached_data.clear(); st.rerun()

    with c_admin3:
        st.subheader("Elenco Task")
        if tk and cm:
            df_t = pd.DataFrame(tk)
            c_map = {c['id']: c['nome_commessa'] for c in cm}
            df_t['Commessa'] = df_t['commessa_id'].map(c_map)
            df_t = df_t.rename(columns={"nome_task": "Task"})
            df_t = df_t[["Commessa", "Task"]]
            st.dataframe(df_t, use_container_width=True, hide_index=True)
            with st.expander("📝 Modifica / 🗑️ Elimina"):
                t_sel = st.selectbox("Seleziona task", tk, format_func=lambda x: x["nome_task"])
                n_t = st.text_input("Rinomina", value=t_sel["nome_task"])
                c_t = st.selectbox("Sposta a Commessa", cm, format_func=lambda x: x['nome_commessa'])
                col1, col2 = st.columns(2)
                if col1.button("Salva Task"):
                    supabase.table("Task").update({"nome_task": n_t, "commessa_id": c_t["id"]}).eq("id", t_sel["id"]).execute()
                    get_cached_data.clear(); st.rerun()
                if col2.button("Rimuovi Task", type="primary"):
                    supabase.table("Task").delete().eq("id", t_sel["id"]).execute()
                    get_cached_data.clear(); st.rerun()
        with st.form("new_task"):
            nt_n = st.text_input("➕ Nuovo Task")
            nt_c = st.selectbox("Associa a Progetto", cm, format_func=lambda x: x['nome_commessa'])
            if st.form_submit_button("Aggiungi Task"):
                supabase.table("Task").insert({"nome_task": nt_n, "commessa_id": nt_c['id']}).execute()
                get_cached_data.clear(); st.rerun()
