import streamlit as st
import google.generativeai as genai
import tempfile
import os
import time
import random
import string
import hashlib
import re
from datetime import datetime, timedelta
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
    """Rimuove completamente asterischi, cancelletti e simboli indesiderati."""
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
            <h4>⚡ Workflow Agentico Dual-Core</h4>
            <p style="color: #94a3b8; font-size: 14px;">Architettura a due livelli con IA primaria di scansione e IA Supervisore QA dedicata all'azzeramento dei falsi positivi.</p>
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
            st.write("Gestisci le licenze, calcola il ROI e genera i moduli d'ordine per i clienti.")
        with col2:
            if st.button("Esci (Logout)"):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.session_state['delete_target'] = None
                st.rerun()
        
        st.markdown("---")
        
        with st.expander("📄 Generatore Modulo d'Ordine / Proposta B2B (Per la Vendita)", expanded=False):
            st.write("Compila i dati dell'azienda acquirente per generare istantaneamente il contratto PDF completo di totali, scadenze e termini di pagamento.")
            
            c_ord1, c_ord2 = st.columns(2)
            with c_ord1:
                cli_nome = st.text_input("Ragione Sociale Azienda", placeholder="Es. Idrica Srl")
                cli_piva = st.text_input("Partita IVA / C.F.", placeholder="Es. 01234567890")
                cli_email = st.text_input("Email Referente", placeholder="ing.rossi@idricasrl.it")
                giorno_rinnovo = st.number_input("Giorno del mese per la scadenza/rinnovo", min_value=1, max_value=31, value=1)
            with c_ord2:
                tipo_piano = st.selectbox("Formula Commerciale", ("Abbonamento Annuale (Canone mensile agevolato)", "Abbonamento Mensile Flessibile (Senza vincoli)"))
                prezzo_mensile = st.number_input("Canone Mensile Imponibile (€ + IVA)", min_value=100, max_value=5000, value=390)
                report_inclusi = st.number_input("Report mensili inclusi nel piano", min_value=10, max_value=500, value=50)
            
            # Calcolo automatico IVA (22%) e totale
            iva_mese = prezzo_mensile * 0.22
            totale_mese_iva = prezzo_mensile + iva_mese

            st.info(f"💡 **Riepilogo Economico Automatico:** Canone Imponibile: €{prezzo_mensile:.2f} + IVA 22% (€{iva_mese:.2f}) = **Totale da pagare ogni mese: €{totale_mese_iva:.2f} IVA inclusa**")

            if st.button("📥 Genera PDF Modulo d'Ordine B2B", use_container_width=True):
                if cli_nome and cli_piva:
                    ordine_filename = f"Modulo_Ordine_HydroAegis_{cli_nome.replace(' ', '_')}.pdf"
                    doc_ord = SimpleDocTemplate(ordine_filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
                    styles_ord = getSampleStyleSheet()
                    
                    style_titolo_ord = ParagraphStyle('TitleOrd', parent=styles_ord['Heading1'], fontSize=14, leading=17, spaceAfter=8, textColor=colors.HexColor("#0b1a30"))
                    style_testo_ord = ParagraphStyle('TextOrd', parent=styles_ord['Normal'], fontSize=9.5, leading=13.5, spaceAfter=6, textColor=colors.HexColor("#1e293b"))
                    
                    story_ord = [
                        Paragraph("<b>MODULO D'ORDINE E PROPOSTA DI ABBONAMENTO SaaS B2B</b>", style_titolo_ord),
                        Paragraph("<b>HydroAegis AI – Piattaforma di Ispezione Automatica e Certificazione Forense</b>", style_testo_ord),
                        Spacer(1, 6),
                        Paragraph(f"<b>1. DATI DEL COMMITTENTE:</b><br/>• Ragione Sociale: {cli_nome}<br/>• P.IVA / C.F.: {cli_piva}<br/>• Email Referente: {cli_email}", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>2. SELEZIONE DEL PIANO E CORRISPETTIVI:</b><br/>• Formula Commerciale: {tipo_piano}<br/>• Volume Incluso: Fino a <b>{report_inclusi} Report Certificati</b> mensili.<br/>• Canone Mensile Imponibile: € {prezzo_mensile:.2f}<br/>• IVA di Legge (22%): € {iva_mese:.2f}<br/>• <b>TOTALE DOVUTO MENSILE (IVA Inclusa): € {totale_mese_iva:.2f}</b>", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>3. MODALITÀ E TERMINI DI PAGAMENTO:</b><br/>• Scadenza Pagamento: Il <b>{giorno_rinnovo} di ogni mese</b> solare.<br/>• Metodo di Pagamento: Bonifico bancario anticipato a 5 giorni data fattura.<br/>• Decorrenza Abbonamento: A far data dalla ricezione del presente modulo controfirmato e rilascio delle credenziali di accesso.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>4. LIMITAZIONE DI RESPONSABILITÀ (HUMAN-IN-THE-LOOP):</b><br/>Il software costituisce uno strumento di supporto decisionale basato su IA. La validazione tecnica definitiva, la conformità alla norma EN 13508-2 e la responsabilità della firma del report rimangono a totale ed esclusivo carico del tecnico abilitato dell'azienda committente.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>5. PROPRIETÀ INTELLETTUALE E DATI:</b><br/>Il Committente mantiene la piena titolarità dei file caricati. Il Fornitore garantisce l'assenza di memorizzazione permanente o utilizzo dei dati per addestramento di IA pubbliche.", style_testo_ord),
                        Spacer(1, 14),
                        Paragraph("<b>Luogo e Data:</b> ___________________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>Firma e Timbro per Accettazione:</b> ___________________________", style_testo_ord)
                    ]
                    doc_ord.build(story_ord)
                    
                    with open(ordine_filename, "rb") as f_ord:
                        st.download_button("⬇️ SCARICA IL MODULO D'ORDINE COMPILATO", data=f_ord, file_name=ordine_filename, mime="application/pdf")
                    st.success("✅ Modulo d'Ordine generato con successo!")
                else:
                    st.warning("⚠️ Inserisci almeno la Ragione Sociale e la Partita IVA dell'azienda.")

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("💼 Simulatore di Prezzo e ROI per Trattativa Commerciale", expanded=False):
            st.write("Usa questo calcolatore durante una chiamata con un cliente per dimostrargli il ritorno economico dell'investimento.")
            
            c_r1, c_r2 = st.columns(2)
            with c_r1:
                ore_video_mese = st.number_input("Ore di video ispezione analizzate al mese dall'azienda:", min_value=1, max_value=500, value=20)
            with c_r2:
                costo_orario_tecnico = st.number_input("Costo orario stimato del tecnico (stipendio + oneri):", min_value=15, max_value=100, value=35)
            
            ore_risparmiate_per_ora_video = 2.5
            totale_ore_risparmiate = ore_video_mese * ore_risparmiate_per_ora_video
            risparmio_economico_mensile = totale_ore_risparmiate * costo_orario_tecnico
            prezzo_consigliato = max(290, round(risparmio_economico_mensile * 0.3, -1))
            
            st.markdown(f"""
            <div class="roi-box">
                <h4 style="color: #10b981; margin-top: 0;">📈 Risultati della Simulazione per il Cliente</h4>
                <p>🕒 Ore di lavoro umano risparmiate al mese: <b>{totale_ore_risparmiate:.1f} ore</b></p>
                <p>💸 Costo attuale del lavoro manuale sprecato: <b>{risparmio_economico_mensile:,.2f} € / mese</b></p>
                <hr style="border-color: #10b981; opacity: 0.3;">
                <p style="font-size: 16px; margin-bottom: 0;">💡 <b>Prezzo di vendita consigliato (Abbonamento Mensile):</b> <span style="color: #38bdf8; font-size: 20px;"><b>{prezzo_consigliato:,.0f} € / mese</b></span></p>
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
            
            limite_impostato = st.number_input("Report mensili inclusi per questo cliente:", min_value=5, max_value=1000, value=50)

            btn_crea = st.button("✅ Salva Nuova Licenza", use_container_width=True)
            if btn_crea:
                if st.session_state['input_cliente'] and st.session_state['input_licenza']:
                    try:
                        supabase.table("licenze").insert({
                            "cliente": st.session_state['input_cliente'], 
                            "codice_licenza": st.session_state['input_licenza'], 
                            "attiva": True,
                            "limite_report": limite_impostato,
                            "report_consumati": 0
                        }).execute()
                        
                        st.success(f"✅ Licenza per {st.session_state['input_cliente']} creata con successo ({limite_impostato} report inclusi)!")
                        st.session_state['input_cliente'] = ""
                        st.session_state['input_licenza'] = ""
                        time.sleep(1.2)
                        st.rerun()
                    except Exception as e:
                        st.error("Errore: Impossibile creare la licenza. Verifica che il codice non esista già.")
                else:
                    st.warning("⚠️ Compila entrambi i campi prima di salvare.")

        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("👥 Database Clienti")
        ricerca = st.text_input("🔍 Cerca per nome cliente o codice licenza...", placeholder="Digita qui per filtrare la lista...")
        
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
                    <span style="width: 28%;">Stato / Utilizzo</span>
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
                        limite_visualizzato = riga.get('limite_report', 50)
                        consumati_visualizzati = riga.get('report_consumati', 0)
                        
                        c_del, c_info, c_act = st.columns([0.4, 4.5, 1])
                        
                        with c_del:
                            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
                            if st.button("❌", key=f"del_{riga['codice_licenza']}", help="Elimina cliente"):
                                st.session_state['delete_target'] = riga['codice_licenza']
                                st.rerun()
                                
                        with c_info:
                            stato_testo = "🟢 Attivo" if riga['attiva'] else "🔴 Sospeso"
                            
                            st.markdown(f"""
                            <div style="background-color: {bg_color}; padding: 14px 15px; border-radius: 8px; border-left: 4px solid {'#10b981' if riga['attiva'] else '#ef4444'}; display: flex; justify-content: space-between; align-items: center; height: 100%;">
                                <span style="font-weight: bold; font-size: 16px; width: 35%; color: #f8fafc;">{riga['cliente']}</span>
                                <span style="font-family: monospace; color: #38bdf8; width: 35%; font-size: 15px;">{riga['codice_licenza']}</span>
                                <span style="width: 30%; font-weight: bold; font-size: 13px; color: #94a3b8;">{stato_testo} | {consumati_visualizzati}/{limite_visualizzato} rep.</span>
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
        dati_cliente_corrente = None
        if 'codice_licenza' in st.session_state:
            try:
                check_lic = supabase.table("licenze").select("*").eq("codice_licenza", st.session_state['codice_licenza']).execute()
                if not check_lic.data or not check_lic.data[0].get("attiva", False):
                    st.session_state['logged_in'] = False
                    if 'report_text' in st.session_state:
                        del st.session_state['report_text']
                    st.rerun()
                else:
                    dati_cliente_corrente = check_lic.data[0]
            except:
                pass
                
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("🔍 Piattaforma di Ispezione Automatica")
            cliente = st.session_state.get('nome_cliente', 'Cliente')
            limite_totale = dati_cliente_corrente.get('limite_report', 50) if dati_cliente_corrente else 50
            report_fatti = dati_cliente_corrente.get('report_consumati', 0) if dati_cliente_corrente else 0
            
            st.markdown(f"Benvenuto, **{cliente}** &nbsp;|&nbsp; <span style='font-size: 13px; color: #38bdf8; background: rgba(14, 165, 233, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(14, 165, 233, 0.3);'>📊 Utilizzo Crediti: {report_fatti} / {limite_totale} Report</span>", unsafe_allow_html=True)
        with col2:
            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
            if st.button("Esci (Logout)", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        tipo_ispezione = st.selectbox("Seleziona l'ambiente:", ("Tubazione Sottomarina (ROV)", "Fognatura / Rete Stradale civile"))
        
        formati_accettati = ["mp4", "mov", "avi", "mpeg", "wmv", "webm", "wav", "mp3", "flac", "aac", "ogg"]
        uploaded_file = st.file_uploader("Trascina qui il file video o audio dell'ispezione", type=formati_accettati)

        if uploaded_file is not None:
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            
            if file_ext in ['.pdf', '.docx', '.doc', '.txt', '.xlsx']:
                st.error("🚫 I documenti testuali (PDF, Word, Excel) non possono essere elaborati dal motore video. Carica un file video (es. MP4, MOV) o audio dell'ispezione.")
            else:
                max_mb = 200
                file_size_mb = uploaded_file.size / (1024 * 1024)
                
                if file_size_mb > max_mb:
                    st.error(f"🚫 Il file supera la dimensione massima consentita di {max_mb}MB per questo piano. Contatta l'amministratore per sbloccare file più pesanti o passare a un piano superiore.")
                elif report_fatti >= limite_totale:
                    st.error(f"🚫 Hai esaurito i report disponibili per questo mese ({report_fatti}/{limite_totale}). Contatta l'amministratore per effettuare l'upgrade del piano o rinnovare i crediti.")
                else:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("Avvia Analisi con Doppia Verifica", use_container_width=True):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name
                        
                        st.session_state['file_hash'] = calcola_hash_file(tmp_file_path)
                        
                        with st.spinner("Caricamento del flusso multimediale in corso..."):
                            media_file = genai.upload_file(path=tmp_file_path)
                            while media_file.state.name == "PROCESSING":
                                time.sleep(3)
                                media_file = genai.get_file(media_file.name)
                        
                        model = genai.GenerativeModel(model_name="gemini-3.6-flash")
                        
                        with st.spinner("Fase 1/2: Scansione strutturale primaria..."):
                            ruolo = "Sei un Ispettore Tecnico Offshore. Analizza il filmato ROV e identifica le anomalie con timestamp esatto." if tipo_ispezione == "Tubazione Sottomarina (ROV)" else "Sei un Ingegnere Civile. Analizza l'ispezione e rileva tutte le anomalie strutturali con timestamp."
                            bozza = model.generate_content([media_file, f"{ruolo}\nFornisci l'elenco preliminare delle anomalie."]).text

                        with st.spinner("Fase 2/2: Supervisore QA al lavoro (Calcolo IQI & Standard EN 13508-2)..."):
                            prompt_2 = f"""Sei un Supervisore Tecnico QA per certificazioni infrastrutturali. 
                            Analizza la bozza seguente:
                            {bozza}
                            
                            Istruzioni di redazione formale:
                            1. Filtra ed elimina ogni falso positivo.
                            2. Assegna a ogni difetto il codice normativo EN 13508-2 pertinente.
                            3. Calcola l'Indice di Priorità d'Intervento (IQI: Classe 1 - Emergenza Strutturale / Classe 2 - Manutenzione Programmata / Classe 3 - Monitoraggio).
                            4. Struttura chiaramente le sezioni:
                               - RILEVAZIONE ANOMALIE E CODIFICA NORMATIVA
                               - CLASSIFICAZIONE PRIORITÀ D'INTERVENTO (IQI)
                               - VALUTAZIONE STRUTTURALE GENERALE E CONCLUSIONI
                            5. ASSOLUTAMENTE VIETATO USARE ASTERISCHI, VIETATO USARE CANCELLETTI (#), VIETATO USARE QUALSIASI SIMBOLO DI MARKDOWN. Scrivi solo testo pulito, formale e ingegneristico."""
                            
                            testo_generato = model.generate_content([media_file, prompt_2]).text
                            st.session_state['report_text'] = pulisci_testo_ia(testo_generato)
                            os.remove(tmp_file_path)

        # --- CONFERMA DI COMPLETAMENTO SOPRA LE ISTRUZIONI ---
        if 'report_text' in st.session_state:
            st.success("✅ Doppia verifica completata con successo e classificazione IQI inclusa!")
            testo_revisionato = st.text_area("Bozza Certificata (Modificabile)", value=st.session_state['report_text'], height=400)
            
            if st.button("Genera PDF Definitivo con Impronta Forense"):
                try:
                    nuovo_consumo = report_fatti + 1
                    supabase.table("licenze").update({"report_consumati": nuovo_consumo}).eq("codice_licenza", st.session_state['codice_licenza']).execute()
                except:
                    pass

                pdf_filename = "Report_Ispezione_Certificato.pdf"
                doc = SimpleDocTemplate(
                    pdf_filename, 
                    pagesize=letter,
                    rightMargin=36,
                    leftMargin=36,
                    topMargin=36,
                    bottomMargin=36
                )
                styles = getSampleStyleSheet()
                
                style_header_title = ParagraphStyle('HeaderTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=16, textColor=colors.HexColor("#0f172a"))
                style_header_sub = ParagraphStyle('HeaderSub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=11, textColor=colors.HexColor("#475569"))
                style_meta = ParagraphStyle('MetaText', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=11, textColor=colors.HexColor("#1e293b"))
                style_hash = ParagraphStyle('HashText', parent=styles['Normal'], fontName='Courier', fontSize=7.5, leading=9, textColor=colors.HexColor("#0284c7"))
                style_section_heading = ParagraphStyle('SecHeading', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor("#0f2942"), spaceBefore=10, spaceAfter=4)
                style_body = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor("#1e293b"))
                style_bullet = ParagraphStyle('Bullet', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, leftIndent=12, firstLineIndent=-10, textColor=colors.HexColor("#1e293b"))
                style_legal = ParagraphStyle('LegalNotice', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=9.5, textColor=colors.HexColor("#64748b"))

                story = []

                data_odierna = datetime.now().strftime("%d/%m/%Y - %H:%M")
                header_data = [
                    [
                        Paragraph("<b>HYDROAEGIS AI | RAPPORTO TECNICO CERTIFICATO</b>", style_header_title),
                        Paragraph(f"<b>Data Emissione:</b> {data_odierna}", style_meta)
                    ],
                    [
                        Paragraph("<b>Standard di Riferimento:</b> EN 13508-2 | Protocollo Dual-Core QA", style_header_sub),
                        Paragraph(f"<b>Ambiente:</b> {tipo_ispezione}", style_meta)
                    ],
                    [
                        Paragraph(f"<b>Committente:</b> {cliente}", style_meta),
                        Paragraph("<b>Stato Procedura:</b> Convalidato", style_meta)
                    ]
                ]
                
                table_header = Table(header_data, colWidths=[340, 200])
                table_header.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(table_header)
                story.append(Spacer(1, 10))

                hash_val = st.session_state.get('file_hash', 'N/D')
                hash_box_data = [[
                    Paragraph("<b>CATENA DI CUSTODIA FORENSE & IMPRONTA DIGITALE DEL FLUSSO VIDEO ORIGINALE</b>", ParagraphStyle('HBoxTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#0f172a"))),
                ], [
                    Paragraph(f"SHA-256 HASH: {hash_val}", style_hash)
                ]]
                table_hash = Table(hash_box_data, colWidths=[540])
                table_hash.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
                    ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#bae6fd")),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(table_hash)
                story.append(Spacer(1, 12))

                testo_pulito = pulisci_testo_ia(testo_revisionato)
                righe = testo_pulito.split('\n')

                for riga in righe:
                    riga_strip = riga.strip()
                    if not riga_strip:
                        story.append(Spacer(1, 4))
                        continue

                    if riga_strip.isupper() and len(riga_strip) > 4:
                        story.append(Paragraph(riga_strip, style_section_heading))
                        story.append(Spacer(1, 3))
                    elif riga_strip.startswith(('1.', '2.', '3.', '4.', '5.', 'SEZIONE', 'FASE')):
                        story.append(Paragraph(f"<b>{riga_strip}</b>", style_section_heading))
                        story.append(Spacer(1, 3))
                    elif riga_strip.startswith(('•', '-')):
                        testo_elenco = riga_strip.lstrip('•- ').strip()
                        story.append(Paragraph(f"• {testo_elenco}", style_bullet))
                    else:
                        story.append(Paragraph(riga_strip, style_body))

                story.append(Spacer(1, 16))
                legal_box_data = [[
                    Paragraph("<b>NOTE LEGALI & LIMITAZIONE DI RESPONSABILITÀ (HUMAN-IN-THE-LOOP):</b> Il presente documento è elaborato mediante ausilio di sistemi algoritmici automatici (HydroAegis AI) a fini di supporto decisionale. La validazione peritale definitiva, la congruità normativa rispetto agli standard tecnici e la sottoscrizione formale del fascicolo rimangono a totale ed esclusivo carico del tecnico abilitato dell'azienda committente.", style_legal)
                ]]
                table_legal = Table(legal_box_data, colWidths=[540])
                table_legal.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ('TOPPADDING', (0, 0), (-1, -1), 6),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('LEFTPADDING', (0, 0), (-1, -1), 8),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ]))
                story.append(table_legal)

                doc.build(story)
                with open(pdf_filename, "rb") as pdf_file:
                    st.download_button("📥 SCARICA IL REPORT PDF CERTIFICATO", data=pdf_file, file_name=pdf_filename, mime="application/pdf")

        # --- ISTRUZIONI E PRIVACY SOTTO LA CONFERMA ---
        st.markdown("""
        <div class="privacy-box">
            <h4 style="color: #38bdf8; margin-top: 0;">📌 Istruzioni operative e Garanzia di Privacy</h4>
            <ol style="margin-bottom: 12px; padding-left: 20px;">
                <li><b>Seleziona l'ambiente corretto</b> dal menu a tendina in base al tipo di ispezione (ROV o Fognatura).</li>
                <li><b>Carica il file multimediale</b> (video o audio) dell'ispezione utilizzando l'apposito riquadro sopra.</li>
                <li><b>Avvia l'analisi</b> e attendi il completamento del workflow di doppia verifica dell'Intelligenza Artificiale.</li>
            </ol>
            <hr style="border-color: #1e3a8a; margin: 12px 0;">
            <p style="margin: 0; font-size: 13px; color: #94a3b8;">
                🛡️ <b>Disclaimer sulla Privacy e Proprietà dei Dati:</b> I file caricati vengono elaborati in via temporanea ed esclusiva per la generazione del report tecnico richiesto. <b>Nessun video, audio o dato aziendale viene memorizzato in modo permanente sui server di terze parti o utilizzato per addestrare modelli di intelligenza artificiale pubblici.</b> La proprietà intellettuale e la riservatezza dei materiali rimangono interamente del committente.
            </p>
        </div>
        """, unsafe_allow_html=True)
