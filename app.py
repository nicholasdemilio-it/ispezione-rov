import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import random
import string
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from supabase import create_client, Client

st.set_page_config(page_title="Ispettore IA multi-settore", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top left, #0b1a30 0%, #050b14 100%); color: #f1f5f9; }
    div.stButton > button { background: linear-gradient(135deg, #1e3a8a 0%, #0ea5e9 100%); color: white; border: none; border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    div.stButton > button:hover { box-shadow: 0 0 15px rgba(14, 165, 233, 0.6); transform: translateY(-2px); color: white; border: none; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea { background-color: rgba(15, 23, 42, 0.6); color: #e2e8f0; border: 1px solid #1e3a8a; border-radius: 8px; }
    .stAlert { background-color: rgba(30, 58, 138, 0.2); border: 1px solid #1e3a8a; color: #e2e8f0; }
    .req-box { font-size: 13px; margin-top: 5px; margin-bottom: 15px; padding: 10px; background-color: rgba(0,0,0,0.2); border-radius: 5px;}
    details > summary { cursor: pointer; color: #94a3b8; font-size: 14px; margin-bottom: 5px; font-weight: bold; }
    .info-card { background: rgba(15, 23, 42, 0.6); border: 1px solid #1e3a8a; padding: 20px; border-radius: 12px; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True)

# Inizializzazione Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# Gestione stato Login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False
if 'do_login' not in st.session_state:
    st.session_state['do_login'] = False
if 'delete_target' not in st.session_state:
    st.session_state['delete_target'] = None

# Stati di memoria per i campi di inserimento
if 'input_cliente' not in st.session_state:
    st.session_state['input_cliente'] = ""
if 'input_licenza' not in st.session_state:
    st.session_state['input_licenza'] = ""

def trigger_login():
    st.session_state['do_login'] = True

def genera_codice():
    p1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    p2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    st.session_state['input_licenza'] = f"LIC-{p1}-{p2}"

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔒 Accesso Area Riservata</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Inserisci le credenziali. Se sei un cliente, inserisci la tua Licenza.</p>", unsafe_allow_html=True)
    
    col_sx, col_centro, col_dx = st.columns([1, 1.5, 1])
    with col_centro:
        licenza = st.text_input("Codice Licenza Aziendale (Clienti)", type="password", placeholder="Es: LIC-ROV-...")
        username = st.text_input("Nome Utente")
        password = st.text_input("Password", type="password", on_change=trigger_login)
        
        has_upper = any(c.isupper() for c in password) if password else False
        has_num = any(c.isdigit() for c in password) if password else False
        has_spec = any(not c.isalnum() for c in password) if password else False
        
        if not password:
            i_up = i_num = i_spec = "-"
            c_up = c_num = c_spec = "#94a3b8"
        else:
            i_up, c_up = ("✅", "#10b981") if has_upper else ("❌", "#ef4444")
            i_num, c_num = ("✅", "#10b981") if has_num else ("❌", "#ef4444")
            i_spec, c_spec = ("✅", "#10b981") if has_spec else ("❌", "#ef4444")

        st.markdown(f"""
        <details>
            <summary>ℹ️ Clicca qui per le Regole Password</summary>
            <div class="req-box">
                <div style="color: {c_up};">{i_up} Almeno una lettera maiuscola</div>
                <div style="color: {c_num};">{i_num} Almeno un numero</div>
                <div style="color: {c_spec};">{i_spec} Almeno un carattere speciale (!, ?, @, ecc.)</div>
            </div>
        </details>
        """, unsafe_allow_html=True)
        
        btn_accedi = st.button("Accedi", use_container_width=True)
        
        if btn_accedi or st.session_state['do_login']:
            st.session_state['do_login'] = False
            
            if username == "admin" and password == "Mare2026!":
                st.session_state['logged_in'] = True
                st.session_state['is_admin'] = True
                st.rerun()
                
            elif username == "cliente1" and password == "Mare2026!":
                if has_upper and has_num and has_spec:
                    try:
                        response = supabase.table("licenze").select("*").eq("codice_licenza", licenza).execute()
                        dati = response.data
                        
                        if len(dati) > 0:
                            licenza_valida = dati[0].get("attiva", False)
                            nome_cliente = dati[0].get("cliente", "Sconosciuto")
                            
                            if licenza_valida:
                                st.session_state['logged_in'] = True
                                st.session_state['is_admin'] = False
                                st.session_state['nome_cliente'] = nome_cliente
                                st.session_state['codice_licenza'] = licenza 
                                st.rerun()
                            else:
                                st.error(f"🚫 La licenza di {nome_cliente} è stata DISATTIVATA.")
                        else:
                            st.error("🚫 Codice Licenza inesistente.")
                    except Exception as e:
                        st.error("Errore di connessione al database di sicurezza.")
                else:
                    st.error("⚠️ La password non rispetta i requisiti minimi.")
            else:
                st.error("❌ Credenziali errate.")
    
    # SEZIONE VANTAGGI RIPRISTINATA IN BASSO
    st.markdown("<br><hr style='border-color: #1e3a8a;'><br>", unsafe_allow_html=True)
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.markdown("""
        <div class="info-card">
            <h4>🚀 Automazione Intelligente</h4>
            <p style="color: #94a3b8; font-size: 14px;">Workflow agentico avanzato per analizzare filmati ROV e fognari azzerando i tempi di revisione manuale.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_v2:
        st.markdown("""
        <div class="info-card">
            <h4>🛡️ Standard EN 13508-2</h4>
            <p style="color: #94a3b8; font-size: 14px;">Doppia verifica con IA supervisore per scartare falsi positivi e produrre descrizioni tecniche certificate.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_v3:
        st.markdown("""
        <div class="info-card">
            <h4>📄 Certificazione PDF</h4>
            <p style="color: #94a3b8; font-size: 14px;">Generazione istantanea di report pronti per la consegna ai committenti con un layout professionale.</p>
        </div>
        """, unsafe_allow_html=True)

else:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # --- VISUALE SUPER ADMIN (DASHBOARD CRM) ---
    if st.session_state.get('is_admin'):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("Pannello di Controllo Direzionale")
            st.write("Gestisci i tuoi clienti e le licenze attive in tempo reale.")
        with col2:
            if st.button("Esci (Logout)"):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.session_state['delete_target'] = None
                st.rerun()
        
        st.markdown("---")
        
        # 1. Modulo Creazione Nuova Licenza
        with st.expander("➕ Aggiungi Nuovo Cliente e Licenza", expanded=False):
            st.session_state['input_cliente'] = st.text_input("Nome Cliente / Azienda", value=st.session_state['input_cliente'])
            
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1:
                st.session_state['input_licenza'] = st.text_input("Codice Licenza", value=st.session_state['input_licenza'])
            with col_l2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Genera", use_container_width=True):
                    genera_codice()
                    st.rerun()
            
            btn_crea = st.button("✅ Salva Nuova Licenza", use_container_width=True)
            if btn_crea:
                if st.session_state['input_cliente'] and st.session_state['input_licenza']:
                    try:
                        supabase.table("licenze").insert({
                            "cliente": st.session_state['input_cliente'], 
                            "codice_licenza": st.session_state['input_licenza'], 
                            "attiva": True
                        }).execute()
                        
                        st.success(f"✅ Licenza per {st.session_state['input_cliente']} creata con successo!")
                        
                        st.session_state['input_cliente'] = ""
                        st.session_state['input_licenza'] = ""
                        
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        st.error("Errore: Impossibile creare la licenza. Verifica che il codice non esista già.")
                else:
                    st.warning("⚠️ Compila entrambi i campi prima di salvare.")

        st.markdown("<br>", unsafe_allow_html=True)
        
        # BARRA DI RICERCA
        st.subheader("👥 Database Clienti")
        ricerca = st.text_input("🔍 Cerca per nome cliente o codice licenza...", placeholder="Digita qui per filtrare la lista...")
        
        # 2. Tabella Lettura e Gestione Licenze (Stile Zebra)
        try:
            risposta = supabase.table("licenze").select("*").order("id", desc=True).execute()
            dati_licenze = risposta.data
            
            if ricerca:
                dati_licenze = [d for d in dati_licenze if ricerca.lower() in d['cliente'].lower() or ricerca.lower() in d['codice_licenza'].lower()]
            
            if not dati_licenze:
                st.info("Nessun cliente trovato.")
            else:
                st.markdown("""
                <div style="display: flex; padding: 0px 15px; margin-bottom: 10px; color: #94a3b8; font-weight: bold; font-size: 14px;">
                    <span style="width: 8%;"></span>
                    <span style="width: 32%;">🏢 Cliente</span>
                    <span style="width: 32%;">🔑 Codice Licenza</span>
                    <span style="width: 28%;">Stato</span>
                </div>
                """, unsafe_allow_html=True)
                
                for i, riga in enumerate(dati_licenze):
                    if st.session_state['delete_target'] == riga['codice_licenza']:
                        st.warning(f"⚠️ Sei sicuro di voler **eliminare definitivamente** il cliente '{riga['cliente']}'? L'azione è irreversibile.")
                        col_yes, col_no, _ = st.columns([1, 1, 3])
                        with col_yes:
                            if st.button("Sì, Elimina", key=f"yes_{riga['codice_licenza']}", use_container_width=True):
                                supabase.table("licenze").delete().eq("codice_licenza", riga['codice_licenza']).execute()
                                st.session_state['delete_target'] = None
                                st.success("Cliente eliminato.")
                                time.sleep(1)
                                st.rerun()
                        with col_no:
                            if st.button("Annulla", key=f"no_{riga['codice_licenza']}", use_container_width=True):
                                st.session_state['delete_target'] = None
                                st.rerun()
                    else:
                        bg_color = "rgba(30, 41, 59, 0.6)" if i % 2 == 0 else "rgba(15, 23, 42, 0.4)"
                        
                        c_del, c_info, c_act = st.columns([0.4, 4.5, 1])
                        
                        with c_del:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            if st.button("❌", key=f"del_{riga['codice_licenza']}", help="Elimina cliente"):
                                st.session_state['delete_target'] = riga['codice_licenza']
                                st.rerun()
                                
                        with c_info:
                            stato_visivo = "🟢 <span style='color: #10b981;'>Attivo</span>" if riga['attiva'] else "🔴 <span style='color: #ef4444;'>Sospeso</span>"
                            
                            st.markdown(f"""
                            <div style="background-color: {bg_color}; padding: 14px 15px; border-radius: 8px; border-left: 4px solid {'#10b981' if riga['attiva'] else '#ef4444'}; display: flex; justify-content: space-between; align-items: center; height: 100%;">
                                <span style="font-weight: bold; font-size: 16px; width: 35%; color: #f8fafc;">{riga['cliente']}</span>
                                <span style="font-family: monospace; color: #38bdf8; width: 35%; font-size: 15px;">{riga['codice_licenza']}</span>
                                <span style="width: 30%; font-weight: bold;">{stato_visivo}</span>
                            </div>
                            """, unsafe_allow_html=True)
                            
                        with c_act:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            etichetta_bottone = "Sospendi" if riga['attiva'] else "Riattiva"
                            if st.button(etichetta_bottone, key=f"btn_{riga['codice_licenza']}", use_container_width=True):
                                nuovo_stato = not riga['attiva']
                                supabase.table("licenze").update({"attiva": nuovo_stato}).eq("codice_licenza", riga['codice_licenza']).execute()
                                st.rerun()
        except Exception as e:
            st.error("Errore di connessione a Supabase durante il caricamento dei clienti.")
                
    # --- VISUALE CLIENTE ---
    else:
        # 🚨 GUARDIA REALE: CONTROLLO CONTINUO DELLA LICENZA 🚨
        if 'codice_licenza' in st.session_state:
            try:
                check_lic = supabase.table("licenze").select("attiva").eq("codice_licenza", st.session_state['codice_licenza']).execute()
                if not check_lic.data or not check_lic.data[0].get("attiva", False):
                    st.session_state['logged_in'] = False
                    if 'report_text' in st.session_state:
                        del st.session_state['report_text']
                    st.rerun()
            except:
                pass
                
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("🔍 Piattaforma di Ispezione Automatica")
            cliente = st.session_state.get('nome_cliente', 'Cliente')
            st.success(f"Autenticazione verificata via server. Benvenuto, **{cliente}**.")
        with col2:
            if st.button("Esci (Logout)"):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.rerun()

        tipo_ispezione = st.selectbox("Seleziona l'ambiente:", ("Tubazione Sottomarina (ROV)", "Fognatura / Rete Stradale civile"))
        formati_accettati = ["mp4", "mov", "avi", "mpeg", "wmv", "webm", "wav", "mp3", "flac", "aac", "ogg"]
        
        uploaded_file = st.file_uploader("Trascina qui il file dell'ispezione", type=formati_accettati)

        if uploaded_file is not None:
            if st.button("Avvia Analisi con Doppia Verifica"):
                file_ext = os.path.splitext(uploaded_file.name)[1].lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    tmp_file_path = tmp_file.name
                
                with st.spinner("Caricamento in corso..."):
                    media_file = genai.upload_file(path=tmp_file_path)
                    while media_file.state.name == "PROCESSING":
                        time.sleep(3)
                        media_file = genai.get_file(media_file.name)
                
                model = genai.GenerativeModel(model_name="gemini-3.6-flash")
                
                with st.spinner("Fase 1/2: Scansione IA in corso..."):
                    ruolo = "Sei un Ispettore Offshore. Trova le anomalie nel file ROV." if tipo_ispezione == "Tubazione Sottomarina (ROV)" else "Sei un tecnico fognario. Trova le anomalie nella tubazione."
                    bozza = model.generate_content([media_file, f"{ruolo}\nElenca le anomalie con il minuto esatto."]).text

                with st.spinner("Fase 2/2: Supervisore QA al lavoro..."):
                    prompt_2 = f"""Sei un Supervisore QA. Bozza: {bozza}
                    1. Scarta i falsi positivi.
                    2. Applica i codici EN 13508-2.
                    3. Scrivi DESCRIZIONI TECNICHE ESTREMAMENTE DETTAGLIATE.
                    4. Concludi con "VALUTAZIONE STRUTTURALE GENERALE". Solo testo puro."""
                    st.session_state['report_text'] = model.generate_content([media_file, prompt_2]).text
                    os.remove(tmp_file_path)

        if 'report_text' in st.session_state:
            st.success("✅ Doppia verifica completata!")
            testo_revisionato = st.text_area("Bozza Certificata", value=st.session_state['report_text'], height=400)
            
            if st.button("Genera PDF Definitivo"):
                pdf_filename = "Report_Ispezione.pdf"
                doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
                styles = getSampleStyleSheet()
                story = [Paragraph(f"<b>RAPPORTO - {tipo_ispezione.upper()}</b>", ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, spaceAfter=15)),
                         Paragraph("<b>Standard:</b> EN 13508-2", styles['Normal']), Spacer(1, 20)]
                for line in testo_revisionato.split('\n'):
                    if line.strip():
                        story.extend([Paragraph(line, styles['Normal']), Spacer(1, 6)])
                doc.build(story)
                with open(pdf_filename, "rb") as pdf_file:
                    st.download_button("📥 SCARICA IL REPORT PDF", data=pdf_file, file_name=pdf_filename, mime="application/pdf")
