import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# 1. Configurazione della pagina Web
st.set_page_config(page_title="Ispettore IA multi-settore", page_icon="🔍", layout="wide")

# --- DESIGN PREMIUM CSS ---
st.markdown("""
    <style>
    /* Sfondo principale scuro con sfumatura radiale blu notte */
    .stApp {
        background: radial-gradient(circle at top left, #0b1a30 0%, #050b14 100%);
        color: #f1f5f9;
    }
    
    /* Stile pulsanti (Gradient blu/azzurro) */
    div.stButton > button {
        background: linear-gradient(135deg, #1e3a8a 0%, #0ea5e9 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        box-shadow: 0 0 15px rgba(14, 165, 233, 0.6);
        transform: translateY(-2px);
        color: white;
        border: none;
    }
    
    /* Aree di testo e input */
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(15, 23, 42, 0.6);
        color: #e2e8f0;
        border: 1px solid #1e3a8a;
        border-radius: 8px;
    }
    
    /* Box delle notifiche (Success/Info) */
    .stAlert {
        background-color: rgba(30, 58, 138, 0.2);
        border: 1px solid #1e3a8a;
        color: #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DI LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.title("🔒 Accesso Area Riservata")
    st.write("Inserisci le tue credenziali per accedere al pannello di ispezione.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        username = st.text_input("Nome Utente")
        password = st.text_input("Password", type="password")
        
        if st.button("Accedi"):
            if username == "admin" and password == "mare2026":
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("❌ Credenziali errate. Riprova.")
else:
    # --- L'APP VERA E PROPRIA ---
    
    # LA TUA CHIAVE API FISSA E NASCOSTA
    API_KEY = "INAIzaSyB02fsZD6oWJWpJB1HfPW1zRjIniiIcxts"
    genai.configure(api_key=API_KEY)
    
    col1, col2 = st.columns([5, 1])
    with col1:
        st.title("🔍 Piattaforma di Ispezione Automatica")
        st.write("Sistema ad alta precisione con doppia verifica AI (Self-Reflection).")
    with col2:
        if st.button("🚪 Esci (Logout)"):
            st.session_state['logged_in'] = False
            st.rerun()

    tipo_ispezione = st.selectbox(
        "Seleziona l'ambiente di ispezione:",
        ("Tubazione Sottomarina (ROV)", "Fognatura / Rete Stradale civile")
    )

    uploaded_file = st.file_uploader("Trascina qui il video .mp4 dell'ispezione", type=["mp4"])

    if uploaded_file is not None:
        if st.button("Avvia Analisi con Doppia Verifica"):
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
            
            # FASE 0: Caricamento
            with st.spinner("Caricamento del video sui server sicuri..."):
                video_file = genai.upload_file(path=tmp_file_path)
                while video_file.state.name == "PROCESSING":
                    time.sleep(3)
                    video_file = genai.get_file(video_file.name)
            
            model = genai.GenerativeModel(model_name="gemini-3.6-flash")
            
            # FASE 1: Prima Analisi
            with st.spinner("Fase 1/2: Scansione IA in corso (rilevamento anomalie primarie)..."):
                if tipo_ispezione == "Tubazione Sottomarina (ROV)":
                    ruolo_1 = "Sei un Ispettore Offshore. Trova tutte le possibili anomalie nel video ROV."
                else:
                    ruolo_1 = "Sei un tecnico fognario. Trova tutte le possibili anomalie nel tubo stradale."
                
                prompt_1 = f"{ruolo_1}\nElenca tutte le anomalie che vedi con il minuto esatto. Sii meticoloso, segna anche i casi dubbi."
                risposta_1 = model.generate_content([video_file, prompt_1])
                bozza_iniziale = risposta_1.text

            # FASE 2: Seconda Analisi
            with st.spinner("Fase 2/2: Supervisore QA al lavoro (eliminazione falsi positivi e codifica EN 13508-2)..."):
                prompt_2 = f"""
                Sei un Supervisore di Qualità (QA) Senior per ispezioni di {tipo_ispezione}.
                Bozza iniziale rilevata:
                {bozza_iniziale}
                
                IL TUO COMPITO:
                1. Riguarda il video e verifica OGNI punto della bozza.
                2. ELIMINA i falsi positivi.
                3. Applica rigorosamente i codici EN 13508-2.
                NON usare asterischi o formattazione Markdown. Restituisci SOLO il report finale (Minuto, Codice, Descrizione, Gravità).
                """
                risposta_finale = model.generate_content([video_file, prompt_2])
                st.session_state['report_text'] = risposta_finale.text
                
                os.remove(tmp_file_path)

    # 3. Fase di Revisione
    if 'report_text' in st.session_state:
        st.success("✅ Doppia verifica completata con successo!")
        st.subheader("📝 Fase 3: Approvazione Finale dell'Ispettore")
        testo_revisionato = st.text_area("Bozza Certificata (Modificabile)", value=st.session_state['report_text'], height=300)
        
        if st.button("Genera PDF Definitivo"):
            pdf_filename = "Report_Ispezione_Certificato.pdf"
            doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, spaceAfter=15, textColor='navy')
            story.append(Paragraph(f"<b>RAPPORTO DI ISPEZIONE - {tipo_ispezione.upper()}</b>", title_style))
            story.append(Paragraph("<b>Standard applicato:</b> EN 13508-2 | <b>Verifica:</b> AI Multi-Pass + Controllo Umano", styles['Normal']))
            story.append(Spacer(1, 20))
            
            for line in testo_revisionato.split('\n'):
                if line.strip():
                    story.append(Paragraph(line, styles['Normal']))
                    story.append(Spacer(1, 6))
            
            doc.build(story)
            
            with open(pdf_filename, "rb") as pdf_file:
                st.download_button(
                    label="📥 SCARICA IL REPORT PDF",
                    data=pdf_file,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )