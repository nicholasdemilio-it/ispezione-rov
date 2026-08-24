import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
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
    </style>
""", unsafe_allow_html=True)

# Inizializzazione Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_supabase()

# Gestione stato Login e Ruoli
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'is_admin' not in st.session_state:
    st.session_state['is_admin'] = False
if 'do_login' not in st.session_state:
    st.session_state['do_login'] = False

def trigger_login():
    st.session_state['do_login'] = True

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔒 Accesso Area Riservata</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 40px;'>Inserisci le credenziali. Se sei un cliente, inserisci la tua Licenza.</p>", unsafe_allow_html=True)
    
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
            
            # 1. ACCESSO SUPER ADMIN (Tu - senza licenza)
            if username == "admin" and password == "Mare2026!":
                st.session_state['logged_in'] = True
                st.session_state['is_admin'] = True
                st.rerun()
                
            # 2. ACCESSO CLIENTE (Verifica su Supabase)
            elif username == "cliente1" and password == "Mare2026!":
                if has_upper and has_num and has_spec:
                    try:
                        # Controlla la licenza nel database Supabase
                        response = supabase.table("licenze").select("*").eq("codice_licenza", licenza).execute()
                        dati = response.data
                        
                        if len(dati) > 0:
                            licenza_valida = dati[0].get("attiva", False)
                            nome_cliente = dati[0].get("cliente", "Sconosciuto")
                            
                            if licenza_valida:
                                st.session_state['logged_in'] = True
                                st.session_state['is_admin'] = False
                                st.session_state['nome_cliente'] = nome_cliente # Salviamo chi è entrato
                                st.rerun()
                            else:
                                st.error(f"🚫 La licenza di {nome_cliente} è stata DISATTIVATA.")
                        else:
                            st.error("🚫 Codice Licenza inesistente.")
                    except Exception as e:
                        st.error(f"Errore tecnico: {e}")
                else:
                    st.error("⚠️ La password non rispetta i requisiti minimi.")
            else:
                st.error("❌ Credenziali errate.")
    
    st.write("---")
    col_testo, _ = st.columns([1, 0.1])
    with col_testo:
        st.markdown("""
        ### 🚀 L'Evoluzione dell'Ispezione Infrastrutturale
        Questa piattaforma sfrutta un Workflow Agentico ad Intelligenza Artificiale per automatizzare, accelerare e certificare le ispezioni.
        """)

else:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # --- VISUALE SUPER ADMIN ---
    if st.session_state.get('is_admin'):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("⚙️ Pannello di Controllo (Super Admin)")
            st.write("Qui in futuro appariranno tutti i dati di Supabase in tempo reale.")
        with col2:
            if st.button("🚪 Esci (Logout)"):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.rerun()
                
    # --- VISUALE CLIENTE ---
    else:
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("🔍 Piattaforma di Ispezione Automatica")
            cliente = st.session_state.get('nome_cliente', 'Cliente')
            st.success(f"Autenticazione verificata via server. Benvenuto, **{cliente}**.")
        with col2:
            if st.button("🚪 Esci (Logout)"):
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
