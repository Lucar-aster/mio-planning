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

# --- TAB 1: TIMELINE PROFESSIONALE ---
with tabs[0]:
    st.header("📊 Planning Progetti")
    
    # 1. CONTROLLI DI VISUALIZZAZIONE
    col1, col2, col3 = st.columns([2, 2, 2])
    scala = col1.selectbox("Vista", ["Settimana", "Mese", "Trimestre", "Semestre"], index=1)
    mostra_nomi = col2.checkbox("Mostra nomi su barre", value=True)
    
    try:
        logs = get_data("Log_Tempi")
        res_tasks = get_data("Task")
        task_map = {t['id']: t['nome_task'] for t in res_tasks} if res_tasks else {}
        
        if logs:
            df = pd.DataFrame(logs)
            df['Inizio'] = pd.to_datetime(df['inizio'])
            df['Fine'] = pd.to_datetime(df['fine'])
            # Importante: per vedere la barra di 1 giorno piena, aggiungiamo 23:59 alla fine
            df['Fine_Visual'] = df['Fine'] + pd.Timedelta(hours=23, minutes=59)
            df['Task'] = df['task_id'].map(task_map)

            # 2. CONFIGURAZIONE SCALE (SIMILE AL COMPONENTE DASH)
            scale_settings = {
                "Settimana": {"dtick": 86400000, "format": "%a %d\nSett %V", "zoom": 7},
                "Mese": {"dtick": 86400000 * 2, "format": "%d %b\nSett %V", "zoom": 30},
                "Trimestre": {"dtick": "M1", "format": "%b %Y", "zoom": 90},
                "Semestre": {"dtick": "M1", "format": "%b %Y", "zoom": 180}
            }
            conf = scale_settings[scala]

            # 3. CREAZIONE GRAFICO
            fig = px.timeline(
                df, 
                x_start="Inizio", 
                x_end="Fine_Visual", 
                y="Task", 
                color="operatore",
                text="operatore" if mostra_nomi else None,
                hover_data={"Inizio": "|%d %b %Y", "Fine": "|%d %b %Y", "operatore": True},
                color_discrete_sequence=px.colors.qualitative.Safe
            )

            # 4. LOGICA DI ZOOM (CENTRATA SU OGGI)
            oggi = datetime.now()
            inizio_zoom = (oggi - pd.Timedelta(days=conf["zoom"]//2))
            fine_zoom = (oggi + pd.Timedelta(days=conf["zoom"]//2))

            # 5. ESTETICA AVANZATA (Layout "Calendar-like")
            fig.update_layout(
                bargap=0.3,
                height=150 + (len(df['Task'].unique()) * 60), # Altezza dinamica
                margin=dict(l=10, r=10, t=50, b=100),
                plot_bgcolor="white",
                xaxis=dict(
                    type="date",
                    rangeslider=dict(visible=True, thickness=0.05), # Slider sottile
                    side="top", # Date in alto come nei calendari
                    gridcolor="#f0f0f0",
                    zeroline=False,
                    range=[inizio_zoom, fine_zoom]
                ),
                yaxis=dict(
                    type='category',
                    tickfont=dict(family="Arial Black", size=13),
                    gridcolor="#f8f8f8",
                    fixedrange=True # Evita lo scroll verticale del grafico, usa quello della pagina
                ),
                legend=dict(orientation="h", y=-0.2)
            )

            # Formattazione asse X con numero settimana
            fig.update_xaxes(
                tickformat=conf["format"],
                dtick=conf["dtick"],
                tickfont=dict(size=10),
                linecolor="#444"
            )

            # Linea "OGGI"
            fig.add_vline(x=oggi.timestamp() * 1000, line_width=3, line_dash="solid", line_color="red", opacity=0.5)
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("Nessun dato registrato.")
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
