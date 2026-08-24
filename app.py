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
    .stApp {
        background: radial-gradient(circle at top left, #0b1a30 0%, #050b14 100%);
        color: #f1f5f9;
    }
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
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        background-color: rgba(15, 23, 42, 0.6);
        color: #e2e8f0;
        border: 1px solid #1e3a8a;
        border-radius: 8px;
    }
    .stAlert {
        background-color: rgba(30, 58, 138, 0.2);
        border: 1px solid #1e3a8a;
        color: #e2e8f0;
    }
    </style>
""", unsafe_allow_html=True)

# --- SISTEMA DI LOGIN CON DESCRIZIONE COMMERCIALE ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔒 Accesso Area Riservata</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 40px;'>Inserisci le tue credenziali per accedere alla piattaforma di ispezione.</p>", unsafe_allow_html=True)
    
    # 3 Colonne per centrare il login (vuota, form, vuota)
    col_sx, col_centro, col_dx = st.columns([1, 1.5, 1])
    
    with col_centro:
        st.markdown("<div style='background-color: rgba(15, 23, 42, 0.6); padding: 30px; border-radius: 15px; border: 1px solid #1e3a8a;'>", unsafe_allow_html=True)
        username = st.text_input("Nome Utente")
        password = st.text_input("Password", type="password")
        
        if st.button("Accedi", use_container_width=True):
            if username == "admin" and password == "mare2026":
                st.session_state['logged_in'] = True
                st.rerun()
            else:
                st.error("❌ Credenziali errate. Riprova.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    st.write("---")
    st.write("")
    
    # Sezione Marketing / Vantaggi
    col_testo, _ = st.columns([1, 0.1])
    with col_testo:
        st.markdown("""
        ### 🚀 L'Evoluzione dell'Ispezione Infrastrutturale
        Questa piattaforma sfrutta un Workflow Agentico ad Intelligenza Artificiale per automatizzare, accelerare e certificare le ispezioni di condotte sottomarine (ROV) e reti idrico-fognarie civili.
        
        **Perché scegliere il nostro software? I tuoi Vantaggi Esclusivi:**
        *   ⏱️ **Risparmio di Tempo del 90%:** L'IA analizza i file video e audio in pochi secondi, liberando gli operatori da ore di noiosa revisione manuale.
        *   🎯 **Affidabilità Estrema (Doppia Verifica):** Il sistema non si ferma alla prima occhiata. Utilizza un processo in cui un "Supervisore QA Virtuale" controlla e corregge il lavoro del primo agente, eliminando i falsi allarmi causati da sporco, riflessi o interferenze.
        *   📋 **Standard Internazionali:** Classificazione automatica e rigorosa dei difetti secondo la normativa europea **EN 13508-2**, pronta per enti pubblici o privati.
        *   🗂️ **Supporto Multi-Formato Avanzato:** Compatibilità totale con sistemi di ripresa professionali. Accetta video ad alta risoluzione (.mp4, .mov, .avi, .mpeg) e tracce audio tattiche (.wav, .mp3, .flac).
        *   📄 **Pronto per la Consegna:** Generazione immediata di report PDF formali, revisionabili manualmente e pronti per l'approvazione finale.
        """)

else:
    # --- L'APP VERA E PROPRIA ---
    
    API_KEY = st.secrets["GEMINI_API_KEY"]
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

    # Elenco formati supportati espanso
    formati_accettati = ["mp4", "mov", "avi", "mpeg", "wmv", "webm", "wav", "mp3", "flac", "aac", "ogg"]
    
    uploaded_file = st.file_uploader(
        "Trascina qui il file dell'ispezione (Video o Audio)", 
        type=formati_accettati
    )

    if uploaded_file is not None:
        if st.button("Avvia Analisi con Doppia Verifica"):
            
            # Rileva automaticamente l'estensione del file caricato
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
            
            with st.spinner("Caricamento del file sui server sicuri..."):
                media_file = genai.upload_file(path=tmp_file_path)
                while media_file.state.name == "PROCESSING":
                    time.sleep(3)
                    media_file = genai.get_file(media_file.name)
            
            model = genai.GenerativeModel(model_name="gemini-3.6-flash")
            
            with st.spinner("Fase 1/2: Scansione IA in corso (rilevamento anomalie primarie)..."):
                if tipo_ispezione == "Tubazione Sottomarina (ROV)":
                    ruolo_1 = "Sei un Ispettore Offshore. Trova tutte le possibili anomalie nel file multimediale ROV (video o audio)."
                else:
                    ruolo_1 = "Sei un tecnico fognario. Trova tutte le possibili anomalie nel file multimediale della tubazione stradale."
                
                prompt_1 = f"{ruolo_1}\nElenca tutte le anomalie che rilevi con il minuto esatto. Sii meticoloso, segna anche i casi dubbi."
                risposta_1 = model.generate_content([media_file, prompt_1])
                bozza_iniziale = risposta_1.text

            with st.spinner("Fase 2/2: Supervisore QA al lavoro (stesura report dettagliato)..."):
                prompt_2 = f"""
                Sei un Supervisore di Qualità (QA) Senior per ispezioni di {tipo_ispezione}.
                Bozza iniziale rilevata:
                {bozza_iniziale}
                
                IL TUO COMPITO:
                1. Riguarda il file e verifica la bozza. Scarta solo i palesi falsi positivi (es. sporco o riflessi).
                2. Applica rigorosamente i codici EN 13508-2.
                3. Per ogni difetto, scrivi una DESCRIZIONE TECNICA ESTREMAMENTE DETTAGLIATA (almeno 2-3 frasi che spieghino l'entità del difetto, l'aspetto e le possibili implicazioni strutturali).
                4. Aggiungi alla fine un paragrafo riassuntivo intitolato "VALUTAZIONE STRUTTURALE GENERALE".
                
                NON usare asterischi o formattazione Markdown. Restituisci SOLO testo puro e discorsivo.
                """
                risposta_finale = model.generate_content([media_file, prompt_2])
                st.session_state['report_text'] = risposta_finale.text
                
                os.remove(tmp_file_path)

    if 'report_text' in st.session_state:
        st.success("✅ Doppia verifica completata con successo!")
        st.subheader("📝 Fase 3: Approvazione Finale dell'Ispettore")
        testo_revisionato = st.text_area("Bozza Certificata (Modificabile)", value=st.session_state['report_text'], height=400)
        
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
