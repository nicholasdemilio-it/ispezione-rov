import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import random
import string
import hashlib
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from supabase import create_client, Client

st.set_page_config(page_title="HydroAegis AI - Ispettore IA", page_icon="🔍", layout="wide")

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
    .privacy-box { background: rgba(15, 23, 42, 0.7); border: 1px solid #0ea5e9; padding: 20px; border-radius: 12px; margin-top: 25px; margin-bottom: 20px; font-size: 14px; color: #cbd5e1; }
    .roi-box { background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; padding: 20px; border-radius: 12px; margin-top: 15px; }
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

def calcola_hash_file(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def pulisci_testo_ia(testo_grezzo):
    """Filtro di pulizia per rimuovere markdown grezzo e formattare per PDF."""
    testo = re.sub(r'#{1,6}\s*', '', testo_grezzo)
    testo = re.sub(r'\*\*(.*?)\*\*', r'\1', testo)
    testo = re.sub(r'\*(.*?)\*', r'\1', testo)
    testo = re.sub(r'__(.*?)__', r'\1', testo)
    testo = re.sub(r'`(.*?)`', r'\1', testo)
    testo = re.sub(r'^\s*[-*•]\s+', '• ', testo, flags=re.MULTILINE)
    return testo.strip()

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
    
    st.markdown("<br><hr style='border-color: #1e3a8a;'><br>", unsafe_allow_html=True)
    
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1:
        st.markdown("""
        <div class="info-card">
            <h4>⚡ Motore Enterprise "Pro"</h4>
            <p style="color: #94a3b8; font-size: 14px;">Il nuovo core IA di classe Pro elabora logiche complesse, classificazione normativa e grammatica peritale in un unico flusso ad altissima precisione.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_v2:
        st.markdown("""
        <div class="info-card">
            <h4>🔐 Impronta Crittografica SHA-256</h4>
            <p style="color: #94a3b8; font-size: 14px;">Ogni report genera un hash forense univoco che lega indissolubilmente il PDF al filmato originale a prova di contestazione legale.</p>
        </div>
        """, unsafe_allow_html=True)
    with col_v3:
        st.markdown("""
        <div class="info-card">
            <h4>📊 Classificazione IQI Automatica</h4>
            <p style="color: #94a3b8; font-size: 14px;">Algoritmo integrato per il calcolo immediato dell'Indice di Priorità d'Intervento strutturale secondo standard normativi.</p>
        </div>
        """, unsafe_allow_html=True)

else:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # --- VISUALE SUPER ADMIN ---
    if st.session_state.get('is_admin'):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("Pannello di Controllo Direzionale & Vendite")
            st.write("Gestisci le licenze, calcola il ROI e genera i moduli d'ordine blindati.")
        with col2:
            if st.button("Esci (Logout)"):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.session_state['delete_target'] = None
                st.rerun()
        
        st.markdown("---")
        
        with st.expander("📄 Generatore Modulo d'Ordine / Proposta B2B (Per la Vendita)", expanded=False):
            st.write("Genera il contratto PDF completo di clausole per la legge italiana (Doppia Firma, Art. 1341 c.c.).")
            
            c_ord1, c_ord2 = st.columns(2)
            with c_ord1:
                cli_nome = st.text_input("Ragione Sociale Azienda", placeholder="Es. Idrica Srl")
                cli_piva = st.text_input("Partita IVA / C.F.", placeholder="Es. 01234567890")
                cli_email = st.text_input("Email Referente", placeholder="ing.rossi@idricasrl.it")
                giorno_rinnovo = st.number_input("Giorno del mese per la scadenza/rinnovo", min_value=1, max_value=31, value=1)
            with c_ord2:
                tipo_piano = st.selectbox("Formula Commerciale", ("Abbonamento Annuale (Canone mensile agevolato con impegno 12 mesi)", "Abbonamento Mensile Flessibile (Senza vincoli, disdetta 30 giorni)"))
                prezzo_mensile = st.number_input("Canone Mensile Imponibile (€ + IVA)", min_value=100, max_value=5000, value=390 if "Annuale" in tipo_piano else 490)
                report_inclusi = st.number_input("Report mensili inclusi nel piano", min_value=10, max_value=500, value=50)
            
            iva_mese = prezzo_mensile * 0.22
            totale_mese_iva = prezzo_mensile + iva_mese

            if st.button("📥 Genera PDF Modulo d'Ordine B2B", use_container_width=True):
                if cli_nome and cli_piva:
                    ordine_filename = f"Modulo_Ordine_HydroAegis_{cli_nome.replace(' ', '_')}.pdf"
                    doc_ord = SimpleDocTemplate(ordine_filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
                    styles_ord = getSampleStyleSheet()
                    
                    style_titolo_ord = ParagraphStyle('TitleOrd', parent=styles_ord['Heading1'], fontSize=13, leading=16, spaceAfter=10, textColor=colors.HexColor("#0b1a30"))
                    style_testo_ord = ParagraphStyle('TextOrd', parent=styles_ord['Normal'], fontSize=8.5, leading=11, spaceAfter=6, textColor=colors.HexColor("#1e293b"))
                    style_doppia_firma = ParagraphStyle('DoppiaFirma', parent=styles_ord['Normal'], fontSize=7.5, leading=9.5, spaceAfter=8, textColor=colors.HexColor("#334155"), fontName="Helvetica-Oblique")
                    
                    if "Annuale" in tipo_piano:
                        dettaglio_durata = "• Durata Contratto: <b>12 (dodici) mesi</b> con impegno di fornitura.<br/>• Condizioni di recesso: Impegno annuale con fatturazione mensile ricorrente."
                    else:
                        dettaglio_durata = "• Durata Contratto: <b>Mensile rinnovabile</b> senza vincoli pluriennali.<br/>• Condizioni di recesso: Disdicibile con preavviso scritto di almeno 30 giorni."

                    story_ord = [
                        Paragraph("<b>MODULO D'ORDINE E CONTRATTO DI ABBONAMENTO SaaS B2B</b>", style_titolo_ord),
                        Paragraph("<b>HydroAegis AI – Piattaforma IA per Ispezioni e Certificazione Forense</b>", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>1. DATI DEL COMMITTENTE:</b><br/>• Ragione Sociale: {cli_nome}<br/>• P.IVA / C.F.: {cli_piva}<br/>• Email Referente: {cli_email}", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>2. SELEZIONE DEL PIANO E CORRISPETTIVI:</b><br/>• Formula Commerciale: <b>{tipo_piano}</b><br/>{dettaglio_durata}<br/>• Volume Incluso: Fino a <b>{report_inclusi} Report Certificati</b> mensili.<br/>• Canone Imponibile: € {prezzo_mensile:.2f} | IVA (22%): € {iva_mese:.2f}<br/>• <b>TOTALE DOVUTO MENSILE: € {totale_mese_iva:.2f}</b>", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>3. TERMINI DI PAGAMENTO, DECORRENZA E RISOLUZIONE:</b><br/>• Scadenza Pagamento: Il <b>{giorno_rinnovo} di ogni mese</b> solare.<br/>• Metodo: Bonifico bancario anticipato a 5 giorni data fattura.<br/>• Decorrenza: A far data dalla ricezione del presente modulo controfirmato e rilascio credenziali.<br/>• <b>Clausola Risolutiva Espressa (Art. 1456 c.c.):</b> Il mancato o ritardato pagamento anche di una sola mensilità comporta la disattivazione immediata della licenza e la risoluzione di diritto del contratto, salvo il diritto al risarcimento.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>4. LIMITAZIONE DI RESPONSABILITÀ E MANLEVA (HUMAN-IN-THE-LOOP):</b><br/>Il software costituisce esclusivamente uno strumento informatico di supporto decisionale. La validazione tecnica dei dati, la classificazione definitiva alla norma EN 13508-2 e la responsabilità della firma del report finale restano ad esclusivo carico del tecnico abilitato del Committente. Il Fornitore è espressamente manlevato da ogni responsabilità in merito alle decisioni operative di cantiere derivanti dall'uso del software.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>5. FORZA MAGGIORE E CONTINUITÀ DEL SERVIZIO (SLA):</b><br/>Il servizio è fornito 'as is' (così com'è) dipendendo da infrastrutture Cloud di terze parti. Il Fornitore non assume responsabilità per disservizi, perdite di dati o ritardi imputabili a cause di forza maggiore, interruzioni di rete o malfunzionamenti delle API fornitrici.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>6. PROPRIETÀ INTELLETTUALE E FORO COMPETENTE:</b><br/>I dati immessi restano di proprietà del Committente (GDPR Reg. UE 2016/679) e non vengono conservati per l'addestramento di IA pubbliche. Per qualsiasi controversia derivante dal presente contratto sarà competente in via esclusiva il Foro della sede legale del Fornitore.", style_testo_ord),
                        Spacer(1, 10),
                        Paragraph("<b>Luogo e Data:</b> _________________________ &nbsp;&nbsp;&nbsp;&nbsp; <b>Il Committente (Firma e Timbro):</b> _________________________", style_testo_ord),
                        Spacer(1, 14),
                        Paragraph("Ai sensi e per gli effetti degli artt. 1341 e 1342 del Codice Civile, il Committente dichiara di aver letto, compreso e di approvare specificamente e separatamente le seguenti clausole: <b>3</b> (Clausola Risolutiva Espressa), <b>4</b> (Limitazione di Responsabilità e Manleva), <b>5</b> (Forza Maggiore e SLA) e <b>6</b> (Foro Competente).", style_doppia_firma),
                        Spacer(1, 8),
                        Paragraph("<b>Il Committente (Seconda Firma Obbligatoria):</b> _________________________", style_testo_ord)
                    ]
                    doc_ord.build(story_ord)
                    
                    with open(ordine_filename, "rb") as f_ord:
                        st.download_button("⬇️ SCARICA IL CONTRATTO B2B COMPILATO", data=f_ord, file_name=ordine_filename, mime="application/pdf")
                    st.success("✅ Modulo d'Ordine generato con 'Doppia Firma' legale inclusa!")
                else:
                    st.warning("⚠️ Inserisci almeno la Ragione Sociale e la Partita IVA.")

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("💼 Simulatore di Prezzo e ROI per Trattativa Commerciale", expanded=False):
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                ore_video_mese = st.number_input("Ore di video analizzate al mese:", min_value=1, max_value=500, value=20)
            with c_r2:
                costo_orario_tecnico = st.number_input("Costo orario tecnico (stipendio + oneri):", min_value=15, max_value=100, value=35)
            
            ore_risparmiate = ore_video_mese * 2.5
            risparmio = ore_risparmiate * costo_orario_tecnico
            prezzo_consigliato = max(290, round(risparmio * 0.3, -1))
            
            st.markdown(f"""
            <div class="roi-box">
                <p>🕒 Ore umane risparmiate: <b>{ore_risparmiate:.1f} ore/mese</b></p>
                <p>💸 Costo manuale sprecato: <b>{risparmio:,.2f} € / mese</b></p>
                <p style="color: #38bdf8; font-size: 18px;">💡 <b>Prezzo Vendita Suggerito: {prezzo_consigliato:,.0f} € / mese</b></p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

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
            limite_impostato = st.number_input("Report mensili inclusi:", min_value=5, max_value=1000, value=50)

            if st.button("✅ Salva Nuova Licenza", use_container_width=True):
                if st.session_state['input_cliente'] and st.session_state['input_licenza']:
                    try:
                        supabase.table("licenze").insert({
                            "cliente": st.session_state['input_cliente'], 
                            "codice_licenza": st.session_state['input_licenza'], 
                            "attiva": True,
                            "limite_report": limite_impostato,
                            "report_consumati": 0
                        }).execute()
                        st.success("✅ Licenza creata con successo!")
                        st.session_state['input_cliente'] = ""
                        st.session_state['input_licenza'] = ""
                        time.sleep(1)
                        st.rerun()
                    except:
                        st.error("Errore: Impossibile creare la licenza.")
                else:
                    st.warning("⚠️ Compila entrambi i campi.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("👥 Database Clienti")
        ricerca = st.text_input("🔍 Cerca per nome o codice...", placeholder="Digita qui...")
        
        try:
            risposta = supabase.table("licenze").select("*").order("id", desc=True).execute()
            dati_licenze = risposta.data
            
            if ricerca:
                dati_licenze = [d for d in dati_licenze if ricerca.lower() in d['cliente'].lower() or ricerca.lower() in d['codice_licenza'].lower()]
            
            if dati_licenze:
                for i, riga in enumerate(dati_licenze):
                    if st.session_state['delete_target'] == riga['codice_licenza']:
                        st.warning(f"⚠️ Eliminare definitivamente '{riga['cliente']}'?")
                        col_yes, col_no, _ = st.columns([1, 1, 3])
                        with col_yes:
                            if st.button("Sì, Elimina", key=f"yes_{riga['codice_licenza']}", use_container_width=True):
                                supabase.table("licenze").delete().eq("codice_licenza", riga['codice_licenza']).execute()
                                st.session_state['delete_target'] = None
                                st.rerun()
                        with col_no:
                            if st.button("Annulla", key=f"no_{riga['codice_licenza']}", use_container_width=True):
                                st.session_state['delete_target'] = None
                                st.rerun()
                    else:
                        bg_color = "rgba(30, 41, 59, 0.6)" if i % 2 == 0 else "rgba(15, 23, 42, 0.4)"
                        limite = riga.get('limite_report', 50)
                        consumati = riga.get('report_consumati', 0)
                        
                        c_del, c_info, c_act = st.columns([0.4, 4.5, 1])
                        with c_del:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            if st.button("❌", key=f"del_{riga['codice_licenza']}"):
                                st.session_state['delete_target'] = riga['codice_licenza']
                                st.rerun()
                        with c_info:
                            stato = "🟢 Attivo" if riga['attiva'] else "🔴 Sospeso"
                            st.markdown(f"""
                            <div style="background-color: {bg_color}; padding: 14px; border-radius: 8px; border-left: 4px solid {'#10b981' if riga['attiva'] else '#ef4444'}; display: flex; justify-content: space-between;">
                                <span style="font-weight: bold; width: 35%;">{riga['cliente']}</span>
                                <span style="font-family: monospace; color: #38bdf8; width: 35%;">{riga['codice_licenza']}</span>
                                <span style="width: 30%; font-size: 13px; color: #94a3b8;">{stato} | {consumati}/{limite} rep.</span>
                            </div>
                            """, unsafe_allow_html=True)
                        with c_act:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            lbl = "Sospendi" if riga['attiva'] else "Riattiva"
                            if st.button(lbl, key=f"btn_{riga['codice_licenza']}", use_container_width=True):
                                supabase.table("licenze").update({"attiva": not riga['attiva']}).eq("codice_licenza", riga['codice_licenza']).execute()
                                st.rerun()
        except:
            st.error("Errore di connessione a Supabase.")
                
    # --- VISUALE CLIENTE ---
    else:
        dati_cliente = None
        if 'codice_licenza' in st.session_state:
            try:
                check = supabase.table("licenze").select("*").eq("codice_licenza", st.session_state['codice_licenza']).execute()
                if not check.data or not check.data[0].get("attiva", False):
                    st.session_state['logged_in'] = False
                    st.rerun()
                else:
                    dati_cliente = check.data[0]
            except: pass
                
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("🔍 Piattaforma di Ispezione Automatica")
            cliente = st.session_state.get('nome_cliente', 'Cliente')
            limite_totale = dati_cliente.get('limite_report', 50) if dati_cliente else 50
            report_fatti = dati_cliente.get('report_consumati', 0) if dati_cliente else 0
            
            st.markdown(f"Benvenuto, **{cliente}** &nbsp;|&nbsp; <span style='font-size: 13px; color: #38bdf8; background: rgba(14, 165, 233, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(14, 165, 233, 0.3);'>📊 Utilizzo Crediti: {report_fatti} / {limite_totale} Report</span>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
            if st.button("Esci (Logout)", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        tipo_ispezione = st.selectbox("Seleziona l'ambiente:", ("Tubazione Sottomarina (ROV)", "Fognatura / Rete Stradale civile"))
        
        formati = ["mp4", "mov", "avi", "mpeg", "wmv", "webm", "wav", "mp3", "flac", "aac", "ogg"]
        uploaded_file = st.file_uploader("Trascina qui il file video o audio dell'ispezione", type=formati)

        if uploaded_file is not None:
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            if file_ext in ['.pdf', '.docx', '.doc', '.txt', '.xlsx']:
                st.error("🚫 Formato non supportato. Carica un file video (es. MP4, MOV) o audio.")
            else:
                if (uploaded_file.size / (1024 * 1024)) > 200:
                    st.error("🚫 File superiore a 200MB. Contatta l'amministratore.")
                elif report_fatti >= limite_totale:
                    st.error("🚫 Crediti esauriti. Contatta l'amministratore per il rinnovo.")
                else:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("🚀 Avvia Analisi Enterprise (Gemini Pro)", use_container_width=True):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name
                        
                        st.session_state['file_hash'] = calcola_hash_file(tmp_file_path)
                        
                        with st.spinner("Caricamento del flusso multimediale sui server sicuri..."):
                            media_file = genai.upload_file(path=tmp_file_path)
                            while media_file.state.name == "PROCESSING":
                                time.sleep(3)
                                media_file = genai.get_file(media_file.name)
                        
                        model = genai.GenerativeModel(model_name="gemini-1.5-pro")
                        
                        with st.spinner("Fase 1/2: Scansione IA strutturale profonda..."):
                            ruolo = "Sei un Ispettore Tecnico Offshore. Identifica tutte le anomalie nel video ROV." if tipo_ispezione == "Tubazione Sottomarina (ROV)" else "Sei un Ingegnere Civile. Identifica tutte le anomalie strutturali nel video."
                            bozza = model.generate_content([media_file, f"{ruolo}\nElenca le anomalie in ordine cronologico con il minuto esatto."]).text

                        with st.spinner("Fase 2/2: Applicazione QA, Calcolo IQI e Revisione Ortografica Peritale..."):
                            prompt_2 = f"""Sei un Ingegnere Capo specializzato in certificazioni. Prendi la bozza sottostante:
                            {bozza}
                            
                            Fai le seguenti operazioni in UN SINGOLO PASSAGGIO perfetto:
                            1. Filtra ed elimina i falsi positivi.
                            2. Assegna a ogni difetto il codice normativo EN 13508-2 pertinente.
                            3. Calcola l'Indice di Priorità d'Intervento (IQI: Classe 1 - Emergenza, Classe 2 - Programmata, Classe 3 - Monitoraggio).
                            4. Struttura chiaramente in 3 sezioni: RILEVAZIONE ANOMALIE, CLASSIFICAZIONE IQI, VALUTAZIONE STRUTTURALE.
                            5. CORREZIONE ORTOGRAFICA OBBLIGATORIA: Il testo deve essere grammaticalmente perfetto, sintatticamente formale, con accordi di genere/numero ineccepibili. Usa terminologia accademica/ingegneristica.
                            6. ASSOLUTAMENTE VIETATO USARE ASTERISCHI, CANCELLETTI O MARKDOWN. Scrivi puro testo professionale formattato in paragrafi e punti elenco nativi.
                            """
                            
                            testo_generato = model.generate_content([media_file, prompt_2]).text
                            st.session_state['report_text'] = pulisci_testo_ia(testo_generato)
                            os.remove(tmp_file_path)

        # --- CONFERMA E PDF ---
        if 'report_text' in st.session_state:
            st.success("✅ Analisi Pro e correzione ortografica completate con successo!")
            testo_revisionato = st.text_area("Bozza Certificata (Modificabile)", value=st.session_state['report_text'], height=400)
            
            if st.button("Genera PDF Definitivo con Impronta Forense"):
                try:
                    supabase.table("licenze").update({"report_consumati": report_fatti + 1}).eq("codice_licenza", st.session_state['codice_licenza']).execute()
                except: pass

                pdf_filename = "Report_Ispezione_Certificato.pdf"
                doc = SimpleDocTemplate(pdf_filename, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
                styles = getSampleStyleSheet()
                
                style_header_title = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=colors.HexColor("#0f172a"))
                style_header_sub = ParagraphStyle('HeaderSub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11, textColor=colors.HexColor("#475569"))
                style_meta = ParagraphStyle('MetaText', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"))
                style_hash = ParagraphStyle('HashText', parent=styles['Normal'], fontName='Courier', fontSize=7.5, leading=9, textColor=colors.HexColor("#0284c7"))
                style_section = ParagraphStyle('SecHeading', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor("#0f2942"), spaceBefore=10, spaceAfter=4)
                style_body = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor("#1e293b"))
                style_bullet = ParagraphStyle('Bullet', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, leftIndent=12, firstLineIndent=-10, textColor=colors.HexColor("#1e293b"))
                style_legal = ParagraphStyle('LegalNotice', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor("#64748b"))

                story = []

                data_odierna = datetime.now().strftime("%d/%m/%Y - %H:%M")
                table_header = Table([
                    [Paragraph("<b>HYDROAEGIS AI | RAPPORTO TECNICO CERTIFICATO</b>", style_header_title), Paragraph(f"<b>Data Emissione:</b> {data_odierna}", style_meta)],
                    [Paragraph("<b>Standard di Riferimento:</b> EN 13508-2 | Motore Enterprise Pro", style_header_sub), Paragraph(f"<b>Ambiente:</b> {tipo_ispezione}", style_meta)],
                    [Paragraph(f"<b>Committente:</b> {cliente}", style_meta), Paragraph("<b>Stato Procedura:</b> Convalidato e Revisionato", style_meta)]
                ], colWidths=[340, 200])
                table_header.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")), ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")), ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")), ('PADDING', (0,0), (-1,-1), 6)]))
                story.append(table_header)
                story.append(Spacer(1, 10))

                table_hash = Table([[Paragraph("<b>CATENA DI CUSTODIA FORENSE & IMPRONTA DIGITALE DEL FLUSSO VIDEO ORIGINALE</b>", ParagraphStyle('HBoxTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#0f172a")))],
                                    [Paragraph(f"SHA-256 HASH: {st.session_state.get('file_hash', 'N/D')}", style_hash)]], colWidths=[540])
                table_hash.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f0f9ff")), ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor("#bae6fd")), ('PADDING', (0,0), (-1,-1), 5)]))
                story.append(table_hash)
                story.append(Spacer(1, 12))

                for riga in pulisci_testo_ia(testo_revisionato).split('\n'):
                    r = riga.strip()
                    if not r:
                        story.append(Spacer(1, 4))
                        continue
                    if r.isupper() and len(r) > 4:
                        story.append(Paragraph(r, style_section))
                    elif r.startswith(('1.', '2.', '3.', '4.', '5.', 'SEZIONE', 'FASE')):
                        story.append(Paragraph(f"<b>{r}</b>", style_section))
                    elif r.startswith(('•', '-')):
                        story.append(Paragraph(f"• {r.lstrip('•- ').strip()}", style_bullet))
                    else:
                        story.append(Paragraph(r, style_body))

                story.append(Spacer(1, 16))
                table_legal = Table([[Paragraph("<b>NOTE LEGALI & LIMITAZIONE DI RESPONSABILITÀ (HUMAN-IN-THE-LOOP):</b> Il presente documento è elaborato mediante ausilio di sistemi algoritmici automatici a fini di supporto decisionale. La validazione peritale definitiva, la congruità normativa rispetto agli standard tecnici e la sottoscrizione formale del fascicolo rimangono a totale ed esclusivo carico del tecnico abilitato dell'azienda committente.", style_legal)]], colWidths=[540])
                table_legal.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")), ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")), ('PADDING', (0,0), (-1,-1), 6)]))
                story.append(table_legal)

                doc.build(story)
                with open(pdf_filename, "rb") as pdf_file:
                    st.download_button("📥 SCARICA IL REPORT PDF CERTIFICATO", data=pdf_file, file_name=pdf_filename, mime="application/pdf")

        # --- ISTRUZIONI E PRIVACY ---
        st.markdown("""
        <div class="privacy-box">
            <h4 style="color: #38bdf8; margin-top: 0;">📌 Istruzioni operative e Garanzia di Privacy</h4>
            <ol style="margin-bottom: 12px; padding-left: 20px;">
                <li><b>Seleziona l'ambiente corretto</b> dal menu a tendina.</li>
                <li><b>Carica il file multimediale</b> dell'ispezione.</li>
                <li><b>Avvia l'analisi</b> e attendi il completamento del workflow dell'Intelligenza Artificiale Pro.</li>
            </ol>
            <hr style="border-color: #1e3a8a; margin: 12px 0;">
            <p style="margin: 0; font-size: 13px; color: #94a3b8;">
                🛡️ <b>Disclaimer sulla Privacy:</b> I file caricati vengono elaborati temporaneamente per la generazione del report e <b>non vengono conservati o usati per addestrare modelli IA.</b> La proprietà resta interamente del committente.
            </p>
        </div>
        """, unsafe_allow_html=True)
