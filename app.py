import streamlit as st
from supabase import create_client
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import platform
import textwrap
import plotly.io as pio

# Configura Plotly per usare l'italiano nelle date
pio.templates.default = "plotly_white"
config_it = dict({
    'monthNames': ['Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno', 'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'],
    'shortMonthNames': ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'],
    'dayNames': ['Domenica', 'Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato'],
    'shortDayNames': ['Dom', 'Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab']
})

# Configurazione globale per i widget Streamlit


# Prova a impostare il locale in italiano
def set_it_locale():
    try:
        # Su Windows (PC locale)
        if platform.system() == "Windows":
            locale.setlocale(locale.LC_ALL, 'ita_it' or 'it_IT')
        # Su Linux (Streamlit Cloud)
        else:
            locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
    except Exception as e:
        print(f"Impossibile impostare il locale: {e}")

set_it_locale()

def get_it_date_label(dt):
    mesi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
    giorni = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
    
    mese = mesi[dt.month - 1]
    giorno_sett = giorni[dt.weekday()]
    if delta_giorni <= 15:
        giorno_sett = giorni[dt.weekday()]
        return f"{giorno_sett} {dt.day:02d}<br>{mese}<br>Sett. {dt.isocalendar()[1]}"
    
    # Vista MESE o TRIMESTRE (Compatta)
    else:
        return f"{dt.day:02d} {mese}<br>Sett. {dt.isocalendar()[1]}"
        
LOGO_URL = "https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png"
st.set_page_config(page_title="Aster Contract", layout="wide")
st.markdown("""
    <style>
    /* Nasconde la barra superiore di Streamlit (Toolbar) */
    header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0%;
    }

    /* Rimuove lo spazio bianco lasciato dalla barra */
    .block-container {
        padding-top: 0rem!important;
    }
    
    /* Contenitore titolo con margini azzerati */
    .compact-title {
        display: flex; 
        align-items: center; 
        gap: 10px; 
        margin-top: 0px;    /* Sposta il titolo verso l'alto */
        margin-bottom: -20px;  /* Avvicina le Tab al titolo */
    }

    .compact-title h2 {
        font-size: 18px !important; /* Testo più piccolo */
        font-weight: 700;
        margin: 0 !important;
        padding: 0 !important;
        color: #1E3A8A;
    }
      
    /* Opzionale: Nasconde il menu "hamburger" in alto a destra e il footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 1. Riduce lo spazio tra i vari elementi (div) di Streamlit */
    .block-container {
        max-width: 100% !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 2rem;    /* Spazio in alto alla pagina */
        padding-bottom: 1rem;
    }
    
    /* 2. Riduce lo spazio tra i singoli widget (bottoni, selectbox, ecc) */
    [data-testid="stVerticalBlock"] {
        gap: 0.2rem;          /* Default è 1rem. Più abbassi, più sono vicini */
    }

    /* 3. Riduce lo spazio sopra i titoli */
    h1, h2, h3 {
        margin-top: -10px !important;
        padding-top: 10px !important;
    }

    /* 4. Rende i Tab più compatti */
    button[data-baseweb="tab"] {
        padding-top: 0px !important;
        padding-bottom: 0px !important;
    }
    
    </style>
    <div class="compact-title">
        <img src="https://vjeqrhseqbfsomketjoj.supabase.co/storage/v1/object/public/icona/logo.png" width="40"> 
        <h1 style="margin: 0; font-family: sans-serif; color: #1E3A8A;">Progetti Aster Contract</h1>
    </div>
    <hr style="margin-top: 5px; margin-bottom: 20px;">
    """,
    unsafe_allow_html=True
)

# --- CONNESSIONE A SUPABASE ---
URL = "https://vjeqrhseqbfsomketjoj.supabase.co"
KEY = "sb_secret_slE3QQh9j3AZp_gK3qWbAg_w9hznKs8"
supabase = create_client(URL, KEY)

st.set_page_config(page_title="Project Planner", page_icon=LOGO_URL, layout="wide")

# --- FUNZIONE RECUPERO DATI ---
def get_data(table):
    return supabase.table(table).select("*").execute().data

# --- INIZIALIZZAZIONE SESSION STATE (MODIFICATO: Spostato in alto per sicurezza) ---
if 'chart_key' not in st.session_state:
    st.session_state.chart_key = 0
if "intervallo_filtro" not in st.session_state:
    st.session_state.intervallo_filtro = [] # Vuoto al primo avvio
# --- FUNZIONI DI INSERIMENTO (MODALS) ---

@st.dialog("➕ Nuova Commessa")
def modal_commessa():
    nome = st.text_input("Nome Commessa")
    cliente = st.text_input("Cliente (Opzionale)")
    if st.button("Salva nel Database", type="primary"):
        if nome:
            try:
                supabase.table("Commesse").insert({"nome_commessa": nome, "cliente": cliente}).execute()
                st.success("Commessa salvata!")
                st.rerun()
            except Exception as e: st.error(f"Errore: {e}")
        else: st.warning("Inserisci il nome della commessa.")

@st.dialog("📑 Nuovo Task")
def modal_task():
    res_c = supabase.table("Commesse").select("id, nome_commessa").execute()
    commesse = {c['nome_commessa']: c['id'] for c in res_c.data}
    nome_t = st.text_input("Nome del Task")
    scelta_c = st.selectbox("Associa a Commessa", options=list(commesse.keys()))
    if st.button("Crea Task", type="primary"):
        if nome_t:
            try:
                supabase.table("Task").insert({"nome_task": nome_t, "commessa_id": commesse[scelta_c]}).execute()
                st.success("Task creato!")
                st.rerun()
            except Exception as e: st.error(f"Errore: {e}")

@st.dialog("⏱️ Nuovo Log Tempi")
def modal_log():
    try:
        # Recupero dati
        res_c = supabase.table("Commesse").select("id, nome_commessa").execute()
        res_t = supabase.table("Task").select("id, nome_task, commessa_id").execute()
        res_o = supabase.table("Operatori").select("nome").execute()
        
        commesse_dict = {c['nome_commessa']: c['id'] for c in res_c.data}
        operatori_lista = [o['nome'] for o in res_o.data]
        all_tasks = res_t.data

        # 1. Selezione Operatore e Commessa
        operatore = st.selectbox("Seleziona Operatore", options=operatori_lista)
        scelta_c_nome = st.selectbox("Seleziona Commessa", options=list(commesse_dict.keys()))
        id_commessa_scelta = commesse_dict[scelta_c_nome]

        # 2. Gestione Task (Esistenti + Opzione Nuovo)
        tasks_filtrati = {t['nome_task']: t['id'] for t in all_tasks if t['commessa_id'] == id_commessa_scelta}
        opzioni_task = list(tasks_filtrati.keys())
        opzione_crea_nuovo = "➕ Crea nuovo task..."
        opzioni_task.append(opzione_crea_nuovo)

        scelta_t_nome = st.selectbox("Seleziona Task", options=opzioni_task)

        # Se l'utente sceglie di creare un nuovo task, mostra il campo di testo
        nuovo_task_nome = None
        if scelta_t_nome == opzione_crea_nuovo:
            nuovo_task_nome = st.text_input("Inserisci il nome del nuovo task")

        # 3. Date
        col1, col2 = st.columns(2)
        inizio = col1.date_input("Data Inizio", datetime.now())
        fine = col2.date_input("Data Fine", datetime.now())
        
        # 4. Salvataggio
        if st.button("Registra Log", type="primary"):
            id_task_finale = None

            # CASO A: Nuovo Task da creare
            if scelta_t_nome == opzione_crea_nuovo:
                if nuovo_task_nome and nuovo_task_nome.strip() != "":
                    # Inserisce il nuovo task nel database
                    res_new_task = supabase.table("Task").insert({
                        "nome_task": nuovo_task_nome, 
                        "commessa_id": id_commessa_scelta
                    }).execute()
                    if res_new_task.data:
                        id_task_finale = res_new_task.data[0]['id']
                else:
                    st.error("Per favore, inserisci un nome per il nuovo task.")
                    return
            
            # CASO B: Task esistente selezionato
            else:
                id_task_finale = tasks_filtrati[scelta_t_nome]

            # Registrazione finale del Log
            if id_task_finale:
                supabase.table("Log_Tempi").insert({
                    "operatore": operatore, 
                    "task_id": id_task_finale,
                    "inizio": str(inizio), 
                    "fine": str(fine)
                }).execute()
                st.success("Log registrato con successo!")
                st.rerun()
                
    except Exception as e: 
        st.error(f"Errore: {e}")
        
@st.dialog("📝 Modifica o Elimina Log")
def modal_edit_log(log_id, data_corrente):
    try:
        res_c = supabase.table("Commesse").select("id, nome_commessa").execute()
        res_t = supabase.table("Task").select("id, nome_task, commessa_id").execute()
        res_o = supabase.table("Operatori").select("nome").execute()
        
        commesse_dict = {c['nome_commessa']: c['id'] for c in res_c.data}
        inv_commesse_dict = {v: k for k, v in commesse_dict.items()}
        operatori_lista = [o['nome'] for o in res_o.data]
        all_tasks = res_t.data

        nuovo_op = st.selectbox("Operatore", options=operatori_lista, 
                                index=operatori_lista.index(data_corrente['operatore']) if data_corrente['operatore'] in operatori_lista else 0)

        task_attuale = next((t for t in all_tasks if t['id'] == data_corrente['task_id']), None)
        id_commessa_attuale = task_attuale['commessa_id'] if task_attuale else list(commesse_dict.values())[0]
        nome_commessa_attuale = inv_commesse_dict.get(id_commessa_attuale, list(commesse_dict.keys())[0])

        scelta_c_nome = st.selectbox("Commessa", options=list(commesse_dict.keys()), 
                                     index=list(commesse_dict.keys()).index(nome_commessa_attuale))
        id_commessa_scelta = commesse_dict[scelta_c_nome]

        tasks_filtrati = {t['nome_task']: t['id'] for t in all_tasks if t['commessa_id'] == id_commessa_scelta}
        if not tasks_filtrati:
            st.warning("Nessun task trovato per questa commessa.")
            nuovo_t_id = None
        else:
            lista_nomi_t = list(tasks_filtrati.keys())
            idx_t = list(tasks_filtrati.values()).index(data_corrente['task_id']) if data_corrente['task_id'] in tasks_filtrati.values() else 0
            nuovo_t_nome = st.selectbox("Task", options=lista_nomi_t, index=idx_t)
            nuovo_t_id = tasks_filtrati[nuovo_t_nome]

        def safe_date(d):
            try: return pd.to_datetime(d).date()
            except: return datetime.now().date()

        col1, col2 = st.columns(2)
        nuovo_inizio = col1.date_input("Inizio", safe_date(data_corrente['inizio']))
        nuovo_fine = col2.date_input("Fine", safe_date(data_corrente['fine']))

        st.divider()
        c1, c2, c3 = st.columns(3)
        if c1.button("💾 Salva", type="primary", use_container_width=True):
            if nuovo_t_id:
                supabase.table("Log_Tempi").update({
                    "operatore": nuovo_op, "task_id": nuovo_t_id,
                    "inizio": str(nuovo_inizio), "fine": str(nuovo_fine)
                }).eq("id", log_id).execute()
                st.session_state.chart_key += 1
                st.rerun()

        if c2.button("🗑️ Elimina", type="secondary", use_container_width=True):
            supabase.table("Log_Tempi").delete().eq("id", log_id).execute()
            st.session_state.chart_key += 1
            st.rerun()
            
        if c3.button("✖️ Annulla", type="secondary", use_container_width=True):
            st.session_state.chart_key += 1
            st.rerun()

    except Exception as e: st.error(f"Errore: {e}")

# --- NEW: FRAGMENT FUNZIONE PER IL GRAFICO (Real-Time 60s) ---
@st.fragment(run_every=60)
def render_gantt_fragment(df_plot, lista_op, oggi, x_range, x_dtick, formato_it, shapes):
    import textwrap
    fig = go.Figure()
    mesi_it = {1:"Gen", 2:"Feb", 3:"Mar", 4:"Apr", 5:"Mag", 6:"Giu", 7:"Lug", 8:"Ago", 9:"Set", 10:"Ott", 11:"Nov", 12:"Dic"}
    
    def apply_wrap(val, width):
        if not val or val == "N/A": return ""
        # textwrap crea una lista di righe, <br> le unisce per l'HTML di Plotly
        lines = textwrap.wrap(str(val), width=width, break_long_words=False)
        return "<br>".join(lines)
    
    for op in df_plot['operatore'].unique():
        df_op = df_plot[df_plot['operatore'] == op]
        commesse_wrapped = [apply_wrap(c, 15) for c in df_op['Commessa']]
        tasks_wrapped = [apply_wrap(t, 20) for t in df_op['Task']]
    
        fig.add_trace(go.Bar(
            base=df_op['Inizio'], 
            x=df_op['Durata_ms'], 
            y=[commesse_wrapped, tasks_wrapped],
            orientation='h', name=op, offsetgroup=op,
            # MODIFICATO: Prende il colore assegnato all'operatore dalla color_map
            marker=dict(color=color_map.get(op, "#8dbad2"), cornerradius=15), 
            width=0.4,
            customdata=df_op[['id', 'operatore', 'task_id', 'inizio', 'fine']],
            hovertemplate="<b>%{y}</b><br>Operatore: %{customdata[1]}<br>%{customdata[3]|%d/%m/%Y} - %{customdata[4]|%d/%m/%Y}<br><extra></extra>"
        ))
        
    frequenza = 'D' if delta_giorni <= 31 else 'W-MON'
    tick_vals = pd.date_range(start=x_range[0], end=x_range[1], freq=frequenza)
    tick_text = [get_it_date_label(d) for d in tick_vals]
    
    fig.update_layout(
        clickmode='event+select', barmode='group', dragmode='pan', plot_bgcolor="white",
        height=400 + (len(df_plot.groupby(['Commessa', 'Task'])) * 30),
        margin=dict(l=10, r=20, t=10, b=10),
        shapes=shapes,
        automargin=True,
        xaxis=dict(type="date", side="top", tickmode="array",       # Forza l'uso dei nostri valori
        tickvals=tick_vals,    # Le posizioni dei giorni
        ticktext=tick_text,    # Le etichette tradotte in italiano
        tickfont=dict(size=10, color="#1E3A8A"),range=x_range, dtick=x_dtick, tickformat="%b<br>%d %a<br>Sett. %V", showgrid=True, gridcolor="#e0e0e0"),
        yaxis=dict(autorange="reversed", gridcolor="#f5f5f5"),
        legend=dict(orientation="h", y=-0.01, x=0.5, xanchor="center")
    )

    fig.update_yaxes(
        type='category',
        # Questa impostazione forza Plotly a mostrare tutte le etichette
        tickmode='linear', 
        automargin=True,
        # Impedisce a Plotly di raggruppare troppo se ci sono <br>
        showdividers=True, 
        dividercolor="grey")
    
    fig.add_vline(x=oggi.timestamp() * 1000+ 43200000, line_width=2, line_color="#ff5252")

    # MODIFICATO: render del grafico isolato nel fragment
    event = st.plotly_chart(fig, use_container_width=True, on_select="rerun", 
                             key=f"gantt_chart_{st.session_state.chart_key}", 
                             config={'displayModeBar': True,'modeBarButtonsToRemove': [    # ...ma togliamo TUTTO tranne il download
                                        'zoom2d', 'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 
                                        'zoomOut2d', 'autoScale2d', 'resetScale2d'
                                     ],'scrollZoom': False, 'displaylogo': False,'toImageButtonOptions': {
                                'format': 'png',
                                'filename': 'Planning_Aster_Contract',
                                'scale': 2 # Alta qualità
                            }})

    # MODIFICATO: Gestione Clic spostata dentro il fragment
    if event and "selection" in event and event["selection"]["points"]:
        point = event["selection"]["points"][0]
        c_data = point["customdata"]
        modal_edit_log(c_data[0], {
            "operatore": c_data[1], "task_id": c_data[2], "inizio": c_data[3], "fine": c_data[4]
        })

# --- NAVIGAZIONE ---
tabs = st.tabs(["📊 Timeline", "⏱️ Gestione Log", "⚙️ Configurazione"])

# --- TAB 1: PLANNING ---
with tabs[0]:

    try:
        # Recupero dati globale (fuori dal fragment per efficienza)
        logs = get_data("Log_Tempi")
        res_tasks = get_data("Task")
        res_commesse = get_data("Commesse")
        res_ops = get_data("Operatori")
        color_map = {o['nome']: o.get('colore', '#8dbad2') for o in res_ops}
        
        if logs and res_tasks and res_commesse:
            # 1. PREPARAZIONE DATI
            task_info = {t['id']: {'nome': t['nome_task'], 'c_id': t['commessa_id']} for t in res_tasks}
            commessa_map = {c['id']: c['nome_commessa'] for c in res_commesse}
            
            df_raw = pd.DataFrame(logs)
            df_raw['Inizio'] = pd.to_datetime(df_raw['inizio']).dt.normalize()
            df_raw['Fine'] = pd.to_datetime(df_raw['fine']).dt.normalize()
            df_raw['Commessa'] = df_raw['task_id'].apply(lambda x: commessa_map[task_info[x]['c_id']] if x in task_info else "N/A")
            df_raw['Task'] = df_raw['task_id'].apply(lambda x: task_info[x]['nome'] if x in task_info else "N/A")

            # 2. FUSIONE LOG (Logica temporale)
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
            df['Durata_ms'] = ((df['Fine'] + pd.Timedelta(days=1)) - df['Inizio']).dt.total_seconds() * 1000

            # 3. FILTRI UI
            col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 2])
            # 1. Definiamo la scala PRIMA di tutto
            scala = col_f4.selectbox("Visualizzazione", ["Settimana", "Mese", "Trimestre"], index=1)

            # 2. CALCOLO RANGE AUTOMATICO (Variabile interna, NON passata al widget)
            oggi_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            if scala == "Settimana":
                range_automatico = [oggi_dt - timedelta(days=3), oggi_dt + timedelta(days=4)]
            elif scala == "Mese":
                range_automatico = [oggi_dt - timedelta(days=15), oggi_dt + timedelta(days=15)]
            else: # Trimestre
                range_automatico = [oggi_dt - timedelta(days=45), oggi_dt + timedelta(days=45)]

            # 3. IL WIDGET (Deve avere value=None o [] per essere vuoto)
            with col_f3:
                scelta_date = st.date_input(
                    "Periodo Visibile",
                    value=None,            # <--- FORZA IL VUOTO
                    format="DD/MM/YYYY",
                    key=f"p_{scala}",      # <--- RESETTA SE CAMBI SCALA
                    placeholder="Seleziona date..."
                )

            # 4. ALTRI FILTRI
            lista_op = sorted(df['operatore'].unique().tolist())
            f_commessa = col_f1.multiselect("Progetti", options=sorted(df['Commessa'].unique()))
            f_operatore = col_f2.multiselect("Operatori", options=lista_op)

            # 5. LOGICA DI DECISIONE: Chi comanda il grafico?
            df_plot = df.copy()
            if f_commessa: df_plot = df_plot[df_plot['Commessa'].isin(f_commessa)]
            if f_operatore: df_plot = df_plot[df_plot['operatore'].isin(f_operatore)]

            # CONTROLLO SE IL WIDGET HA DATE
            if scelta_date and len(scelta_date) == 2:
                # Se l'utente ha scelto date, usiamo quelle
                x_range = [pd.to_datetime(scelta_date[0]), pd.to_datetime(scelta_date[1])]
                mask = (df_plot['Inizio'].dt.date >= scelta_date[0]) & (df_plot['Fine'].dt.date <= scelta_date[1])
                df_plot = df_plot[mask]
            else:
                # Se il widget è vuoto, usiamo la scala automatica
                x_range = range_automatico

            delta_giorni = (x_range[1] - x_range[0]).days
            
            # 4. BOTTONI RAPIDI
            c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
            if c1.button("➕ Commessa", use_container_width=True): modal_commessa()
            if c2.button("📑 Task", use_container_width=True): modal_task()
            if c3.button("⏱️ Log", use_container_width=True): modal_log()
            if c4.button("📍 Oggi", use_container_width=True):
                # Forziamo il reset della scala e il refresh del grafico
                st.session_state.chart_key += 1 
                st.rerun()
            st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)

            # 5. LOGICA WEEKEND / SCALA (Costanti per il fragment)
            oggi = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            x_min_sh = oggi - timedelta(days=100); x_max_sh = oggi + timedelta(days=100)
            festivita_it = ["01-01", "06-01", "25-04", "01-05", "02-06", "15-08", "01-11", "08-12", "25-12", "26-12"]
            shapes = []
            curr = x_min_sh
            while curr <= x_max_sh:
                if curr.weekday() >= 5 or curr.strftime("%d-%m") in festivita_it:
                    shapes.append(dict(type="rect", x0=curr.strftime("%Y-%m-%d 00:00:00"), x1=(curr + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00"),
                                       y0=0, y1=1, yref="paper", fillcolor="rgba(180, 180, 180, 0.3)", layer="below", line_width=0))
                curr += timedelta(days=1)

            formato_it = "%d/%m<br>%a"
           delta_giorni = (x_range[1] - x_range[0]).days
            
            if delta_giorni <= 7:
                x_dtick = 86400000          # Un tick ogni giorno
                formato_it = "%b<br>%d %a<br>Sett. %V"
            elif delta_giorni <= 31:
                x_dtick = 86400000 * 2      # Ogni 2 giorni
                formato_it = "%b<br>%d %a<br>Sett. %V"
            elif delta_giorni <= 90:
                x_dtick = 86400000 * 7      # Ogni settimana (Lunedì)
                formato_it = "%b<br>Sett. %V"
            else:
                x_dtick = 86400000 * 14     # Ogni 2 settimane
                formato_it = "%b<br>Sett. %V"

            # --- NEW: CHIAMATA AL FRAGMENT ---
            render_gantt_fragment(df_plot, color_map, oggi_dt, x_range, x_dtick, "%d/%m", shapes)

        else:
            st.info("Benvenuto! Inizia creando una commessa e un task.")
            if st.button("Aggiungi la prima Commessa"): modal_commessa()
    except Exception as e: st.error(f"Errore: {e}")
        
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
