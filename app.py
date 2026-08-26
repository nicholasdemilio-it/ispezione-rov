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
from zoneinfo import ZoneInfo
from dateutil.relativedelta import relativedelta
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from supabase import create_client, Client

st.set_page_config(page_title="HydroAegis AI - Ispettore IA", page_icon="🔍", layout="wide")
# --- BANNER DI TEST ---
if st.secrets.get("AMBIENTE") == "TEST":
    st.markdown("""
        <div style='background-color: #ef4444; color: white; text-align: center; padding: 8px; font-weight: bold; border-radius: 8px; margin-bottom: 15px; border: 2px solid #b91c1c;'>
            🧪 ATTENZIONE: SEI NELL'AMBIENTE DI TEST - QUALSIASI MODIFICA AL DATABASE È REALE 🧪
        </div>
    """, unsafe_allow_html=True)

# --- SCUDO CSS PER NASCONDERE STREAMLIT E ABBELLIRE LA UI ---
st.markdown("""
    <style>
    /* Nasconde il menu e il footer di Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp { background: radial-gradient(circle at top left, #0b1a30 0%, #050b14 100%); color: #f1f5f9; }
    div.stButton > button { background: linear-gradient(135deg, #1e3a8a 0%, #0ea5e9 100%); color: white; border: none; border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    div.stButton > button:hover { box-shadow: 0 0 15px rgba(14, 165, 233, 0.6); transform: translateY(-2px); color: white; border: none; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea, .stSelectbox>div>div>div { background-color: rgba(15, 23, 42, 0.6); color: #e2e8f0; border: 1px solid #1e3a8a; border-radius: 8px; }
    .stAlert { background-color: rgba(30, 58, 138, 0.2); border: 1px solid #1e3a8a; color: #e2e8f0; }
    .info-card { background: rgba(15, 23, 42, 0.6); border: 1px solid #1e3a8a; padding: 20px; border-radius: 12px; margin-top: 20px; }
    .privacy-box { background: rgba(15, 23, 42, 0.7); border: 1px solid #0ea5e9; padding: 20px; border-radius: 12px; margin-top: 25px; margin-bottom: 20px; font-size: 14px; color: #cbd5e1; }
    .support-box { background: rgba(15, 23, 42, 0.8); border: 1px solid #38bdf8; padding: 20px; border-radius: 12px; margin-top: 30px; margin-bottom: 20px; }
    .roi-box { background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; padding: 20px; border-radius: 12px; margin-top: 15px; }
    .client-row { background-color: rgba(15, 23, 42, 0.6); padding: 15px; border-radius: 8px; border-left: 4px solid #10b981; margin-bottom: 10px; }
    .client-suspended { border-left: 4px solid #ef4444; opacity: 0.8; }
    .ticket-row { background-color: rgba(15, 23, 42, 0.6); padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b; margin-bottom: 10px; }
    .ticket-resolved { border-left: 4px solid #10b981; opacity: 0.7; }
    .price-table { width: 100%; border-collapse: collapse; margin-top: 10px; color: #e2e8f0; font-size: 14px;}
    .price-table th { background-color: #1e3a8a; padding: 10px; border: 1px solid #0f172a; }
    .price-table td { background-color: rgba(15, 23, 42, 0.6); padding: 10px; border: 1px solid #0f172a; text-align: center; }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource
def init_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_supabase()

if 'logged_in' not in st.session_state: st.session_state['logged_in'] = False
if 'is_admin' not in st.session_state: st.session_state['is_admin'] = False
if 'do_login' not in st.session_state: st.session_state['do_login'] = False
if 'delete_target' not in st.session_state: st.session_state['delete_target'] = None

def trigger_login(): st.session_state['do_login'] = True

def genera_codice():
    p1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    p2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"LIC-{p1}-{p2}"

def calcola_hash_file(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def pulisci_testo_ia(testo_grezzo):
    testo = re.sub(r'#{1,6}\s*', '', testo_grezzo)
    testo = re.sub(r'\*\*(.*?)\*\*', r'\1', testo)
    testo = re.sub(r'\*(.*?)\*', r'\1', testo)
    testo = re.sub(r'__(.*?)__', r'\1', testo)
    testo = re.sub(r'`(.*?)`', r'\1', testo)
    testo = re.sub(r'^\s*[-*•]\s+', '• ', testo, flags=re.MULTILINE)
    return testo.strip()

if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center;'>🔒 Accesso Area Riservata</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 30px;'>Inserisci le tue credenziali e il Codice Licenza fornito dall'amministratore.</p>", unsafe_allow_html=True)
    
    col_sx, col_centro, col_dx = st.columns([1, 1.5, 1])
    with col_centro:
        licenza = st.text_input("Codice Licenza Aziendale", placeholder="Es: LIC-ABCD-1234")
        username = st.text_input("Nome Utente")
        password = st.text_input("Password", type="password", on_change=trigger_login)
        
        btn_accedi = st.button("Accedi", use_container_width=True)
        
        if btn_accedi or st.session_state['do_login']:
            st.session_state['do_login'] = False
            
            # ACCESSO ADMIN
            if username == "Hydroadmin45" and password == "Hydremilio.368":
                st.session_state['logged_in'] = True
                st.session_state['is_admin'] = True
                st.rerun()
            # ACCESSO CLIENTE DINAMICO (Verifica DB)
            else:
                if not licenza or not username or not password:
                    st.warning("⚠️ Compila tutti i campi per accedere.")
                else:
                    for tentativo in range(2): 
                        try:
                            response = supabase.table("licenze").select("*").eq("codice_licenza", licenza).eq("username", username).eq("password", password).execute()
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
                                    st.error(f"🚫 La licenza di {nome_cliente} è stata DISATTIVATA dall'amministrazione.")
                            else:
                                st.error("❌ Credenziali errate o Licenza non valida.")
                            break 
                        except Exception as e:
                            if tentativo == 0:
                                time.sleep(1.5)
                            else:
                                st.error("Errore di rete: il server di sicurezza è temporaneamente irraggiungibile.")
    
    st.markdown("<br><hr style='border-color: #1e3a8a;'><br>", unsafe_allow_html=True)
    col_v1, col_v2, col_v3 = st.columns(3)
    with col_v1: st.markdown("<div class='info-card'><h4>⚡ Motore Enterprise</h4><p style='color: #94a3b8; font-size: 14px;'>Core IA per logiche complesse, classificazione normativa e grammatica peritale.</p></div>", unsafe_allow_html=True)
    with col_v2: st.markdown("<div class='info-card'><h4>🔐 Impronta Crittografica</h4><p style='color: #94a3b8; font-size: 14px;'>Ogni report genera un hash forense univoco a prova di contestazione legale.</p></div>", unsafe_allow_html=True)
    with col_v3: st.markdown("<div class='info-card'><h4>📊 Classificazione IQI</h4><p style='color: #94a3b8; font-size: 14px;'>Calcolo immediato dell'Indice di Priorità d'Intervento strutturale.</p></div>", unsafe_allow_html=True)

else:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    
    # --- VISUALE SUPER ADMIN ---
    if st.session_state.get('is_admin'):
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("Pannello di Controllo Direzionale")
        with col2:
            if st.button("Esci (Logout)"):
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.session_state['delete_target'] = None
                st.rerun()
        st.markdown("---")

        with st.expander("🛎️ Ticket di Assistenza Clienti", expanded=False):
            try:
                res_tickets = supabase.table("ticket_assistenza").select("*").order("id", desc=True).execute()
                tickets = res_tickets.data
                
                if tickets:
                    for t in tickets:
                        bg_tk = "ticket-row" if t.get('stato') == 'Aperto' else "ticket-row ticket-resolved"
                        stato_icon = "🟠 APERTO" if t.get('stato') == 'Aperto' else "🟢 RISOLTO"
                        
                        c_tk_info, c_tk_act = st.columns([4.5, 1])
                        with c_tk_info:
                            st.markdown(f"""
                            <div class="{bg_tk}">
                                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                    <span style="font-weight: bold; font-size: 15px;">{t.get('cliente', 'N/D')} <span style="font-size: 12px; color: #94a3b8; font-weight: normal;">({t.get('codice_licenza', 'N/D')})</span></span>
                                    <span style="font-size: 13px; font-weight: bold;">{stato_icon}</span>
                                </div>
                                <div style="font-size: 13px; color: #cbd5e1; margin-bottom: 8px;">
                                    <b>Oggetto:</b> {t.get('tipo_problema', 'N/D')} <br>
                                    <b>Contatto:</b> {t.get('preferenza_contatto', 'N/D')} - {t.get('recapito', 'N/D')}
                                </div>
                                <div style="font-size: 13px; color: #e2e8f0; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 4px;">
                                    "{t.get('descrizione', 'N/D')}"
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        with c_tk_act:
                            st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                            if t.get('stato') == 'Aperto':
                                if st.button("Segna Risolto", key=f"tk_{t['id']}", use_container_width=True):
                                    supabase.table("ticket_assistenza").update({"stato": "Risolto"}).eq("id", t['id']).execute()
                                    st.rerun()
                            else:
                                if st.button("🗑️ Elimina", key=f"tk_del_{t['id']}", use_container_width=True):
                                    supabase.table("ticket_assistenza").delete().eq("id", t['id']).execute()
                                    st.rerun()
                else:
                    st.info("Nessun ticket di assistenza presente.")
            except Exception as e:
                st.error(f"Nessun ticket (o tabella 'ticket_assistenza' non ancora creata).")

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("💶 Cruscotto Finanziario (MRR & ARR)", expanded=False):
            try:
                res_fin = supabase.table("licenze").select("*").execute()
                tutti_clienti = res_fin.data
                clienti_attivi = sum(1 for c in tutti_clienti if c.get('attiva', False))
                mrr_reale = sum(c.get('prezzo', 0) for c in tutti_clienti if c.get('attiva', False) and c.get('frequenza') == 'Mensile')
                mrr_annuali = sum(c.get('prezzo', 0)/12 for c in tutti_clienti if c.get('attiva', False) and c.get('frequenza') == 'Annuale')
                mrr_totale = mrr_reale + mrr_annuali
                arr_totale = mrr_totale * 12
            except:
                clienti_attivi, mrr_totale, arr_totale = 0, 0, 0

            st.markdown(f"""
            <div style="display: flex; gap: 20px; margin-top: 5px;">
                <div style="flex: 1; background: rgba(14, 165, 233, 0.1); border: 1px solid #0ea5e9; padding: 20px; border-radius: 12px; text-align: center;">
                    <h5 style="color: #cbd5e1; margin: 0; font-size: 14px;">MRR (Incasso Mensile)</h5>
                    <h2 style="color: #38bdf8; margin: 5px 0 0 0; font-size: 32px;">€ {mrr_totale:,.2f}</h2>
                    <p style="color: #94a3b8; font-size: 12px; margin: 5px 0 0 0;">Fatturato ricorrente calcolato dal DB</p>
                </div>
                <div style="flex: 1; background: rgba(16, 185, 129, 0.1); border: 1px solid #10b981; padding: 20px; border-radius: 12px; text-align: center;">
                    <h5 style="color: #cbd5e1; margin: 0; font-size: 14px;">ARR (Incasso Annuale)</h5>
                    <h2 style="color: #10b981; margin: 5px 0 0 0; font-size: 32px;">€ {arr_totale:,.2f}</h2>
                    <p style="color: #94a3b8; font-size: 12px; margin: 5px 0 0 0;">Proiezione su 12 mesi</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.expander("📚 Prontuario Commerciale (Pacchetti Listino)", expanded=False):
            st.markdown("""
            <p style='color: #94a3b8; font-size: 14px;'>Listino ufficiale differenziato tra <b>Impegno Annuale</b> (scontato per fare cassa) e <b>Mensile Flessibile</b> (maggiorato del 25% per disdetta libera).</p>
            <table class="price-table">
                <tr>
                    <th>Nome Pacchetto</th>
                    <th>Report Inclusi</th>
                    <th>Prezzo Ann. Impegno (al mese)</th>
                    <th>Prezzo Mensile Flessibile</th>
                </tr>
                <tr>
                    <td><b>SMALL</b></td>
                    <td>15 Report / mese</td>
                    <td><b>290 € / mese</b></td>
                    <td><b>350 € / mese</b></td>
                </tr>
                <tr>
                    <td><b>MEDIUM</b></td>
                    <td>50 Report / mese</td>
                    <td><b>690 € / mese</b></td>
                    <td><b>830 € / mese</b></td>
                </tr>
                <tr>
                    <td><b>CORPORATE</b></td>
                    <td>150 Report / mese</td>
                    <td><b>1.490 € / mese</b></td>
                    <td><b>1.790 € / mese</b></td>
                </tr>
            </table>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.expander("📄 Generatore Modulo d'Ordine / Proposta B2B", expanded=False):
            with st.form("form_contratto_b2b"):
                c_ord1, c_ord2 = st.columns(2)
                with c_ord1:
                    cli_nome = st.text_input("Ragione Sociale Azienda", placeholder="Es. Idrica Srl")
                    cli_piva = st.text_input("Partita IVA / C.F.", placeholder="Es. 01234567890")
                    cli_email = st.text_input("Email Referente", placeholder="ing.rossi@idricasrl.it")
                with c_ord2:
                    tipo_piano = st.selectbox("Formula Commerciale", ("Abbonamento Annuale (Canone agevolato, impegno 12 mesi)", "Abbonamento Mensile Flessibile (Rinnovo automatico)"))
                    
                    # --- PREZZI DINAMICI IN BASE AL TIPO DI PIANO ---
                    default_prezzo = 690 if "Annuale" in tipo_piano else 830
                    prezzo_mensile = st.number_input("Canone Netto Concordato (€)", min_value=100, max_value=5000, value=default_prezzo)
                    report_inclusi = st.number_input("Report mensili inclusi nel piano", min_value=10, max_value=500, value=50)
                
                btn_genera_pdf = st.form_submit_button("⚙️ Prepara Contratto in PDF", use_container_width=True)

            if btn_genera_pdf:
                if cli_nome and cli_piva:
                    ordine_filename = f"Modulo_Ordine_HydroAegis_{cli_nome.replace(' ', '_')}.pdf"
                    doc_ord = SimpleDocTemplate(ordine_filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
                    styles_ord = getSampleStyleSheet()
                    style_titolo_ord = ParagraphStyle('TitleOrd', parent=styles_ord['Heading1'], fontSize=13, leading=16, spaceAfter=10, textColor=colors.HexColor("#0b1a30"))
                    style_testo_ord = ParagraphStyle('TextOrd', parent=styles_ord['Normal'], fontSize=8.5, leading=11, spaceAfter=6, textColor=colors.HexColor("#1e293b"))
                    style_fiscale = ParagraphStyle('Fiscale', parent=styles_ord['Normal'], fontSize=7.5, leading=9.5, spaceAfter=4, textColor=colors.HexColor("#64748b"))
                    style_doppia_firma = ParagraphStyle('DoppiaFirma', parent=styles_ord['Normal'], fontSize=7.5, leading=9.5, spaceAfter=8, textColor=colors.HexColor("#334155"), fontName="Helvetica-Oblique")
                    
                    dettaglio_durata = "• Durata Contratto: <b>12 (dodici) mesi</b> con impegno di fornitura ed esclusiva tariffa agevolata.<br/>• Condizioni di recesso: Impegno annuale, rinnovo automatico salvo disdetta 7 gg prima della scadenza." if "Annuale" in tipo_piano else "• Durata Contratto: <b>Mensile rinnovabile automaticamente</b>.<br/>• Condizioni di recesso: Disdicibile liberamente con preavviso scritto di almeno <b>7 (sette) giorni</b> prima del successivo rinnovo."

                    story_ord = [
                        Paragraph("<b>MODULO D'ORDINE E CONTRATTO DI ABBONAMENTO SaaS B2B</b>", style_titolo_ord),
                        Paragraph("<b>HydroAegis AI – Piattaforma IA per Ispezioni e Certificazione Forense</b>", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>1. DATI DEL COMMITTENTE:</b><br/>• Ragione Sociale: {cli_nome}<br/>• P.IVA / C.F.: {cli_piva}<br/>• Email Referente: {cli_email}", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>2. SELEZIONE DEL PIANO E CORRISPETTIVI:</b><br/>• Formula Commerciale: <b>{tipo_piano}</b><br/>{dettaglio_durata}<br/>• Volume Incluso: Fino a <b>{report_inclusi} Report Certificati</b> mensili.<br/>• <b>CANONE IMPONIBILE: € {prezzo_mensile:.2f}</b><br/><i>*Operazione attualmente in franchigia da IVA (Regime Forfettario). In caso di variazione del regime fiscale del Fornitore, l'IVA di legge (22%) verrà aggiunta in fattura e risulterà interamente detraibile dal Committente, mantenendo invariato il costo netto pattuito.</i>", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph(f"<b>3. TERMINI DI PAGAMENTO E RISOLUZIONE:</b><br/>• Metodo di Pagamento: Addebito automatico su metodo di pagamento registrato (Carta/SEPA) o Bonifico Bancario anticipato.<br/>• Decorrenza: Dalla ricezione del presente modulo controfirmato.<br/>• Rinnovo: <b>Automatico</b> alla scadenza del periodo, salvo disdetta formale inviata almeno 7 giorni prima.<br/>• <b>Clausola Risolutiva (Art. 1456 c.c.):</b> Il mancato pagamento comporta la disattivazione immediata della licenza.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>4. CLAUSOLA FISCALE PRE-APERTURA:</b><br/>Il Committente prende formalmente atto che l'entità giuridica del Fornitore (HydroAegis) è attualmente in fase di formale costituzione e attribuzione del numero di Partita IVA. La prima fatturazione utile verrà emessa non appena la posizione fiscale sarà attiva, inglobando i canoni maturati a partire dalla data di attivazione dell'abbonamento.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>5. LIMITAZIONE DI RESPONSABILITÀ (HUMAN-IN-THE-LOOP):</b><br/>Il software costituisce uno strumento di supporto decisionale. La validazione tecnica dei dati e la classificazione alla norma EN 13508-2 restano ad esclusivo carico del tecnico abilitato del Committente. Il Fornitore è manlevato da responsabilità inerenti le decisioni di cantiere.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>6. FORZA MAGGIORE E SLA:</b><br/>Il servizio è fornito 'as is' dipendendo da Cloud di terze parti. Il Fornitore non assume responsabilità per disservizi o ritardi imputabili a interruzioni di rete o API.", style_testo_ord),
                        Spacer(1, 4),
                        Paragraph("<b>7. PROPRIETÀ INTELLETTUALE E FORO COMPETENTE:</b><br/>I dati restano di proprietà del Committente (GDPR UE 2016/679) e non formano IA pubbliche. Per le controversie sarà competente in via esclusiva il Foro del Fornitore.", style_testo_ord),
                        Spacer(1, 10),
                        Paragraph("<b>Luogo e Data:</b> _________________________ &nbsp;&nbsp;&nbsp;&nbsp; <b>Il Committente (Firma):</b> _________________________", style_testo_ord),
                        Spacer(1, 14),
                        Paragraph("Ai sensi e per gli effetti degli artt. 1341 e 1342 C.C., il Committente dichiara di approvare specificamente le clausole: <b>3</b> (Pagamento e Rinnovo Automatico), <b>4</b> (Clausola Fiscale Pre-Apertura), <b>5</b> (Limitazione Responsabilità), <b>6</b> (Forza Maggiore) e <b>7</b> (Foro Competente).", style_doppia_firma),
                        Spacer(1, 8),
                        Paragraph("<b>Il Committente (Seconda Firma Obbligatoria):</b> _________________________", style_testo_ord),
                        Spacer(1, 20),
                        Paragraph("<i>Operazione in franchigia da IVA ai sensi dell'art. 1, commi da 54 a 89, L. 190/2014. Importo soggetto a imposta di bollo di € 2,00 (assolta in fattura elettronica) se superiore a € 77,47.</i>", style_fiscale)
                    ]
                    doc_ord.build(story_ord)
                    with open(ordine_filename, "rb") as f_ord:
                        st.session_state['pdf_ord_bytes'] = f_ord.read()
                        st.session_state['pdf_ord_name'] = ordine_filename
            if 'pdf_ord_bytes' in st.session_state:
                st.download_button("⬇️ SCARICA IL CONTRATTO B2B", data=st.session_state['pdf_ord_bytes'], file_name=st.session_state['pdf_ord_name'], mime="application/pdf")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🚀 Generatore Accordo Early-Bird (7 Giorni Prova + Abbonamento)", expanded=False):
            st.markdown("<p style='color: #94a3b8; font-size: 13px;'>Usa questo modulo per i primissimi clienti. Prevede 7 giorni di prova gratuiti, scaduti i quali si attiva in automatico l'abbonamento. Include la clausola di P.IVA in via di attribuzione.</p>", unsafe_allow_html=True)
            with st.form("form_early_bird"):
                c_eb1, c_eb2 = st.columns(2)
                with c_eb1:
                    cli_nome_eb = st.text_input("Ragione Sociale Azienda", placeholder="Es. Idrica Srl", key="eb_nome")
                    cli_piva_eb = st.text_input("Partita IVA / C.F.", placeholder="Es. 01234567890", key="eb_piva")
                    cli_email_eb = st.text_input("Email Referente", placeholder="ing.rossi@idricasrl.it", key="eb_email")
                with c_eb2:
                    tipo_piano_eb = st.selectbox("Formula Successiva (Post-Prova)", ("Abbonamento Annuale (Canone agevolato)", "Abbonamento Mensile Flessibile"), key="eb_piano")
                    prezzo_mensile_eb = st.number_input("Canone Netto Post-Prova (€)", min_value=100, max_value=5000, value=690, key="eb_prezzo")
                    report_inclusi_eb = st.number_input("Report mensili inclusi", min_value=10, max_value=500, value=50, key="eb_report")
                    crediti_prova_eb = st.number_input("Crediti Gratuiti (Prova)", min_value=1, max_value=20, value=3, key="eb_prova")
                
                btn_genera_eb = st.form_submit_button("⚙️ Prepara Accordo Early-Bird in PDF", use_container_width=True)

            if btn_genera_eb:
                if cli_nome_eb and cli_piva_eb:
                    eb_filename = f"Accordo_Prova_Vincolata_{cli_nome_eb.replace(' ', '_')}.pdf"
                    doc_eb = SimpleDocTemplate(eb_filename, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=30, bottomMargin=30)
                    
                    # Usa gli stili definiti in precedenza (li ricreiamo per sicurezza nel blocco)
                    styles_eb = getSampleStyleSheet()
                    style_titolo_eb = ParagraphStyle('TitleEB', parent=styles_eb['Heading1'], fontSize=13, leading=16, spaceAfter=10, textColor=colors.HexColor("#0b1a30"))
                    style_testo_eb = ParagraphStyle('TextEB', parent=styles_eb['Normal'], fontSize=8.5, leading=11, spaceAfter=6, textColor=colors.HexColor("#1e293b"))
                    style_fiscale_eb = ParagraphStyle('FiscaleEB', parent=styles_eb['Normal'], fontSize=7.5, leading=9.5, spaceAfter=4, textColor=colors.HexColor("#64748b"))
                    style_firma_eb = ParagraphStyle('FirmaEB', parent=styles_eb['Normal'], fontSize=7.5, leading=9.5, spaceAfter=8, textColor=colors.HexColor("#334155"), fontName="Helvetica-Oblique")
                    
                    story_eb = [
                        Paragraph("<b>ACCORDO DI PROVA (TRIAL) CON CONVERSIONE IN ABBONAMENTO SaaS B2B</b>", style_titolo_eb),
                        Paragraph("<b>HydroAegis AI – Piattaforma IA per Ispezioni e Certificazione Forense</b>", style_testo_eb),
                        Spacer(1, 4),
                        Paragraph(f"<b>1. DATI DEL COMMITTENTE:</b><br/>• Ragione Sociale: {cli_nome_eb}<br/>• P.IVA / C.F.: {cli_piva_eb}<br/>• Email Referente: {cli_email_eb}", style_testo_eb),
                        Spacer(1, 4),
                        Paragraph("<b>2. PERIODO DI PROVA GRATUITO (FASE 1):</b><br/>Il Fornitore concede al Committente un periodo di prova a titolo totalmente gratuito della durata di <b>7 (sette) giorni solari</b> a partire dall'attivazione delle credenziali. Durante tale periodo, il Committente potrà testare le funzionalità della piattaforma senza alcun onere.", style_testo_eb),
                        Spacer(1, 4),
                        Paragraph(f"<b>3. SOTTOSCRIZIONE AUTOMATICA (FASE 2):</b><br/>In assenza di formale disdetta inviata via email/PEC entro il settimo giorno di prova, il presente accordo <b>si convertirà automaticamente in un abbonamento a pagamento</b> con le seguenti condizioni:<br/>• Formula Commerciale: <b>{tipo_piano_eb}</b><br/>• Volume Incluso: Fino a <b>{report_inclusi_eb} Report Certificati</b> mensili.<br/>• <b>CANONE IMPONIBILE: € {prezzo_mensile_eb:.2f} / mese</b>", style_testo_eb),
                        Spacer(1, 4),
                        Paragraph("<b>4. CLAUSOLA FISCALE PRE-APERTURA:</b><br/>Il Committente prende formalmente atto che l'entità giuridica del Fornitore (HydroAegis) è attualmente in fase di formale costituzione e attribuzione del numero di Partita IVA. La prima fatturazione utile verrà emessa non appena la posizione fiscale sarà attiva, inglobando i canoni maturati a partire dalla data di conversione dell'abbonamento.", style_testo_eb),
                        Spacer(1, 4),
                        Paragraph("<b>5. NOTE LEGALI E LIMITAZIONE DI RESPONSABILITÀ:</b><br/>Il software costituisce uno strumento di supporto decisionale. La validazione tecnica dei dati e la classificazione alla norma EN 13508-2 restano ad esclusivo carico del tecnico abilitato del Committente. I dati inseriti non saranno utilizzati per l'addestramento di modelli IA pubblici (Privacy e GDPR).", style_testo_eb),
                        Spacer(1, 10),
                        Paragraph("<b>Luogo e Data:</b> _________________________ &nbsp;&nbsp;&nbsp;&nbsp; <b>Il Committente (Firma):</b> _________________________", style_testo_eb),
                        Spacer(1, 14),
                        Paragraph("Ai sensi e per gli effetti degli artt. 1341 e 1342 C.C., il Committente dichiara di approvare specificamente le clausole: <b>3</b> (Sottoscrizione Automatica), <b>4</b> (Clausola Fiscale Pre-Apertura) e <b>5</b> (Limitazione di Responsabilità).", style_firma_eb),
                        Spacer(1, 8),
                        Paragraph("<b>Il Committente (Seconda Firma Obbligatoria):</b> _________________________", style_testo_eb),
                    ]
                    
                    doc_eb.build(story_eb)
                    with open(eb_filename, "rb") as f_eb:
                        st.session_state['pdf_eb_bytes'] = f_eb.read()
                        st.session_state['pdf_eb_name'] = eb_filename
                        
            if 'pdf_eb_bytes' in st.session_state:
                st.download_button("⬇️ SCARICA ACCORDO EARLY-BIRD", data=st.session_state['pdf_eb_bytes'], file_name=st.session_state['pdf_eb_name'], mime="application/pdf")
        
        with st.expander("📦 Gestione Ricarica Crediti Extra (Pacchetti Report)", expanded=False):
            try:
                res_cli = supabase.table("licenze").select("codice_licenza, cliente, limite_report").execute()
                lista_clienti = res_cli.data
            except:
                lista_clienti = []
                
            if lista_clienti:
                clienti_dict = {f"{c['cliente']} ({c['codice_licenza']})": c['codice_licenza'] for c in lista_clienti}
                scelta_cliente_extra = st.selectbox("Seleziona Azienda Cliente", options=list(clienti_dict.keys()))
                
                c_ex1, c_ex2 = st.columns(2)
                with c_ex1: qt_report_extra = st.number_input("Numero Report Extra nel Pacchetto", min_value=5, max_value=200, value=10)
                with c_ex2: prezzo_pacchetto = st.number_input("Prezzo Totale Pacchetto (€ - Netto)", min_value=50, max_value=2000, value=250)
                
                if st.button("⚡ Aggiungi Report al Cliente", use_container_width=True):
                    cod_selezionato = clienti_dict[scelta_cliente_extra]
                    attuale = supabase.table("licenze").select("limite_report").eq("codice_licenza", cod_selezionato).execute().data[0]['limite_report']
                    supabase.table("licenze").update({"limite_report": attuale + int(qt_report_extra)}).eq("codice_licenza", cod_selezionato).execute()
                    st.success(f"✅ Aggiunti {qt_report_extra} report extra a {scelta_cliente_extra}!")
            else:
                st.info("Nessun cliente registrato.")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("💼 Simulatore di Prezzo e ROI per Trattativa Commerciale", expanded=False):
            c_r1, c_r2 = st.columns(2)
            with c_r1: ore_video_mese = st.number_input("Ore di video analizzate al mese:", min_value=1, max_value=500, value=20)
            with c_r2: costo_orario_tecnico = st.number_input("Costo orario tecnico (stipendio + oneri):", min_value=15, max_value=100, value=35)
            
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
        with st.expander("➕ Aggiungi Nuovo Cliente (Attivazione Licenza e Password)", expanded=False):
            
            if 'input_cliente' not in st.session_state: st.session_state['input_cliente'] = ""
            st.session_state['input_cliente'] = st.text_input("Ragione Sociale Azienda Cliente", value=st.session_state['input_cliente'])
            
            c_log1, c_log2 = st.columns(2)
            with c_log1:
                nuovo_username = st.text_input("Username per il Cliente (Es. idrica_srl)", placeholder="Nessuno spazio")
            with c_log2:
                nuova_password = st.text_input("Password per il Cliente", placeholder="Inserisci una password sicura")
            
            col_l1, col_l2 = st.columns([3, 1])
            with col_l1: 
                if 'input_licenza_tmp' not in st.session_state: st.session_state['input_licenza_tmp'] = ""
                st.session_state['input_licenza_tmp'] = st.text_input("Codice Licenza Generato", value=st.session_state['input_licenza_tmp'])
            with col_l2:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                if st.button("Genera Codice", use_container_width=True):
                    st.session_state['input_licenza_tmp'] = genera_codice()
                    st.rerun()
                    
            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1: limite_impostato = st.number_input("Report mensili inclusi:", min_value=5, max_value=1000, value=50)
            with col_d2: frequenza_scelta = st.selectbox("Frequenza Pagamento (Nuovo)", ["Mensile Flessibile", "Annuale"])
            
            # Prezzo predefinito basato sulla scelta frequenza nel form di creazione
            def_crea = 830 if frequenza_scelta == "Mensile Flessibile" else 690
            with col_d3: prezzo_inserito = st.number_input("Prezzo Concordato (€)", min_value=0, max_value=10000, value=def_crea)

            if st.button("✅ Salva Nuova Licenza e Credenziali", use_container_width=True):
                if st.session_state['input_cliente'] and st.session_state['input_licenza_tmp'] and nuovo_username and nuova_password:
                    oggi = datetime.now()
                    str_oggi = oggi.strftime("%d/%m/%Y")
                    prossimo = (oggi + relativedelta(months=1)).strftime("%d/%m/%Y") if "Mensile" in frequenza_scelta else (oggi + relativedelta(years=1)).strftime("%d/%m/%Y")
                    try:
                        supabase.table("licenze").insert({
                            "cliente": st.session_state['input_cliente'], 
                            "codice_licenza": st.session_state['input_licenza_tmp'], 
                            "username": nuovo_username,
                            "password": nuova_password,
                            "attiva": True, 
                            "limite_report": limite_impostato, 
                            "report_consumati": 0, 
                            "prezzo": prezzo_inserito, 
                            "frequenza": frequenza_scelta, 
                            "ultimo_pagamento": str_oggi, 
                            "prossimo_rinnovo": prossimo
                        }).execute()
                        st.success("✅ Cliente creato con successo! Manda al cliente Username, Password e Codice Licenza.")
                        st.session_state['input_cliente'] = ""
                        st.session_state['input_licenza_tmp'] = ""
                        time.sleep(2)
                        st.rerun()
                    except Exception as e: 
                        st.error(f"Errore DB: {e}. (Assicurati di aver aggiunto le colonne 'username' e 'password' su Supabase).")
                else: 
                    st.warning("⚠️ Compila tutti i campi: Ragione Sociale, Username, Password e Codice Licenza.")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("👥 Database Clienti e Pagamenti (Riservato)", expanded=False):
            ricerca = st.text_input("🔍 Cerca per nome o codice...", placeholder="Digita qui...")
            try:
                risposta = supabase.table("licenze").select("*").order("id", desc=True).execute()
                dati_licenze = risposta.data
                if ricerca: dati_licenze = [d for d in dati_licenze if ricerca.lower() in d['cliente'].lower() or ricerca.lower() in d['codice_licenza'].lower()]
                if dati_licenze:
                    for riga in dati_licenze:
                        if st.session_state['delete_target'] == riga['codice_licenza']:
                            st.warning(f"⚠️ Eliminare '{riga['cliente']}'?")
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
                            bg_class = "client-row" if riga['attiva'] else "client-row client-suspended"
                            c_del, c_info, c_act = st.columns([0.4, 4.5, 1])
                            with c_del:
                                st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                                if st.button("❌", key=f"del_{riga['codice_licenza']}"):
                                    st.session_state['delete_target'] = riga['codice_licenza']
                                    st.rerun()
                            with c_info:
                                st.markdown(f"""
                                <div class="{bg_class}">
                                    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                                        <span style="font-weight: bold; font-size: 16px;">{riga['cliente']}</span>
                                        <span style="font-size: 14px; color: #38bdf8;">€ {riga.get('prezzo','N/D')} ({riga.get('frequenza','N/D')})</span>
                                        <span style="font-family: monospace; color: #94a3b8;">{riga['codice_licenza']}</span>
                                    </div>
                                    <div style="display: flex; justify-content: space-between; font-size: 12px; color: #cbd5e1;">
                                        <span><b>User/Pass:</b> {riga.get('username','N/D')} / {riga.get('password','N/D')}</span>
                                        <span><b>Report:</b> {riga.get('report_consumati',0)}/{riga.get('limite_report',50)}</span>
                                        <span style="color: {'#10b981' if riga['attiva'] else '#ef4444'};"><b>Prox Rinnovo:</b> {riga.get('prossimo_rinnovo','N/D')}</span>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            with c_act:
                                st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
                                lbl = "Sospendi" if riga['attiva'] else "Riattiva"
                                if st.button(lbl, key=f"btn_{riga['codice_licenza']}", use_container_width=True):
                                    supabase.table("licenze").update({"attiva": not riga['attiva']}).eq("codice_licenza", riga['codice_licenza']).execute()
                                    st.rerun()
            except Exception as e: 
                st.error(f"Errore di sistema nel database clienti: {e}")
                
    # --- VISUALE CLIENTE ---
    else:
        dati_cliente = None
        if 'codice_licenza' in st.session_state:
            try:
                check = supabase.table("licenze").select("*").eq("codice_licenza", st.session_state['codice_licenza']).execute()
                if not check.data or not check.data[0].get("attiva", False):
                    st.session_state['logged_in'] = False
                    st.rerun()
                else: dati_cliente = check.data[0]
            except: pass
                
        col1, col2 = st.columns([5, 1])
        with col1:
            st.title("🔍 Piattaforma di Ispezione Automatica")
            cliente_nome = st.session_state.get('nome_cliente', 'Cliente')
            limite_totale = dati_cliente.get('limite_report', 50) if dati_cliente else 50
            report_fatti = dati_cliente.get('report_consumati', 0) if dati_cliente else 0
            prox_rinnovo = dati_cliente.get('prossimo_rinnovo', 'N/D') if dati_cliente else 'N/D'
            
            st.markdown(f"""Benvenuto, **{cliente_nome}** &nbsp;|&nbsp; 
                        <span style='font-size: 13px; color: #38bdf8; background: rgba(14, 165, 233, 0.1); padding: 3px 8px; border-radius: 4px; border: 1px solid rgba(14, 165, 233, 0.3);'>📊 Crediti: {report_fatti} / {limite_totale} Report</span>
                        &nbsp;|&nbsp; <span style='font-size: 12px; color: #94a3b8;'>Rinnovo Licenza: {prox_rinnovo}</span>
                        """, unsafe_allow_html=True)
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
            if file_ext in ['.pdf', '.docx', '.doc', '.txt', '.xlsx']: st.error("🚫 Formato non supportato. Carica un file video o audio.")
            else:
                if (uploaded_file.size / (1024 * 1024)) > 2000: st.error("🚫 File superiore a 2GB (circa 1 ora di video). Si consiglia di dividerlo in due parti.")
                elif report_fatti >= limite_totale: st.error("🚫 Crediti esauriti. Contatta l'amministratore tramite il modulo in basso per ricaricare.")
                else:
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if st.button("Avvia Analisi Enterprise", use_container_width=True):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            tmp_file_path = tmp_file.name
                        
                        st.session_state['file_hash'] = calcola_hash_file(tmp_file_path)
                        
                        with st.spinner("Caricamento del video in corso (i file pesanti richiedono una buona connessione)..."):
                            try:
                                media_file = genai.upload_file(path=tmp_file_path)
                                
                                while media_file.state.name == "PROCESSING":
                                    time.sleep(3)
                                    media_file = genai.get_file(media_file.name)
                                
                                if media_file.state.name == "FAILED":
                                    st.error("🚫 Errore Google: Impossibile elaborare il file. Potrebbe essere danneggiato o in un formato non supportato.")
                                    st.stop()
                            
                            except Exception as e:
                                st.error("⚠️ Tempo di connessione scaduto (Timeout). Il server di Google è temporaneamente sovraccarico o la rete è instabile. Attendi 1 minuto e riprova.")
                                st.stop()
                        
                        modello_ideale = "gemini-1.5-pro-latest"
                            
                        model = genai.GenerativeModel(model_name=modello_ideale)
                        
                        with st.spinner("Fase 1/2: Scansione IA strutturale profonda..."):
                            try:
                                time.sleep(2)
                                ruolo = "Sei un Ispettore Tecnico Offshore. Identifica tutte le anomalie nel video ROV." if tipo_ispezione == "Tubazione Sottomarina (ROV)" else "Sei un Ingegnere Civile. Identifica tutte le anomalie strutturali nel video."
                                bozza = model.generate_content([media_file, f"{ruolo}\nElenca le anomalie in ordine cronologico con il minuto esatto."]).text
                            except Exception as e:
                                st.error(f"⚠️ ERRORE TECNICO GOOGLE: {e}")
                                st.stop()

                        with st.spinner("Fase 2/2: Applicazione QA, Calcolo IQI e Revisione Ortografica Peritale..."):
                            try:
                                prompt_2 = f"""Sei un Ingegnere Capo specializzato in certificazioni. Prendi la bozza sottostante:
                                {bozza}
                                
                                Fai le seguenti operazioni in UN SINGOLO PASSAGGIO perfetto:
                                1. Filtra ed elimina i falsi positivi.
                                2. Assegna a ogni difetto il codice normativo EN 13508-2 pertinente.
                                3. Calcola l'Indice di Priorità d'Intervento (IQI).
                                4. Struttura chiaramente in 3 sezioni: RILEVAZIONE ANOMALIE, CLASSIFICAZIONE IQI, VALUTAZIONE STRUTTURALE.
                                5. CORREZIONE ORTOGRAFICA OBBLIGATORIA.
                                6. ASSOLUTAMENTE VIETATO USARE ASTERISCHI, CANCELLETTI O MARKDOWN. Scrivi puro testo professionale formattato in paragrafi.
                                """
                                testo_generato = model.generate_content([media_file, prompt_2]).text
                                st.session_state['report_text'] = pulisci_testo_ia(testo_generato)
                                os.remove(tmp_file_path)
                            except Exception as e:
                                st.error(f"⚠️ Errore durante la fase di certificazione (Fase 2): {e}")
                                st.stop()
                            
                            try:
                                supabase.table("licenze").update({"report_consumati": report_fatti + 1}).eq("codice_licenza", st.session_state['codice_licenza']).execute()
                            except: pass

        if 'report_text' in st.session_state:
            st.success("✅ Analisi completata! (Un credito è stato regolarmente scalato dal tuo abbonamento).")
            testo_revisionato = st.text_area("Bozza Certificata (Modificabile)", value=st.session_state['report_text'], height=400)
            
            if st.button("Genera PDF Definitivo con Impronta Forense"):
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
                data_odierna = datetime.now(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y - %H:%M")
                table_header = Table([
                    [Paragraph("<b>HYDROAEGIS AI | RAPPORTO TECNICO CERTIFICATO</b>", style_header_title), Paragraph(f"<b>Data Emissione:</b> {data_odierna}", style_meta)],
                    [Paragraph("<b>Standard di Riferimento:</b> EN 13508-2 | Motore Enterprise", style_header_sub), Paragraph(f"<b>Ambiente:</b> {tipo_ispezione}", style_meta)],
                    [Paragraph(f"<b>Committente:</b> {cliente_nome}", style_meta), Paragraph("<b>Stato Procedura:</b> Convalidato e Revisionato", style_meta)]
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
                    if r.isupper() and len(r) > 4: story.append(Paragraph(r, style_section))
                    elif r.startswith(('1.', '2.', '3.', '4.', '5.', 'SEZIONE', 'FASE')): story.append(Paragraph(f"<b>{r}</b>", style_section))
                    elif r.startswith(('•', '-')): story.append(Paragraph(f"• {r.lstrip('•- ').strip()}", style_bullet))
                    else: story.append(Paragraph(r, style_body))

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
                <li><b>Avvia l'analisi</b> e attendi il completamento del workflow dell'Intelligenza Artificiale. <i>(Il credito viene scalato all'avvio dell'elaborazione).</i></li>
            </ol>
            <hr style="border-color: #1e3a8a; margin: 12px 0;">
            <p style="margin: 0; font-size: 13px; color: #94a3b8;">
                🛡️ <b>Disclaimer sulla Privacy:</b> I file caricati vengono elaborati temporaneamente per la generazione del report e <b>non vengono conservati o usati per addestrare modelli IA.</b> La proprietà resta interamente del committente.
            </p>
        </div>
        """, unsafe_allow_html=True)

        # --- MODULO DI SUPPORTO COLLEGATO A SUPABASE ---
        st.markdown("""
        <div class="support-box">
            <h4 style="color: #38bdf8; margin-top: 0;">🛠️ Assistenza Tecnica & Supporto Clienti</h4>
            <p style="font-size: 13px; color: #94a3b8;">Hai riscontrato un problema tecnico o desideri acquistare un pacchetto extra di report? Compila il modulo sottostante: la richiesta arriverà direttamente alla nostra amministrazione e verrai ricontattato entro 48 ore.</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("form_assistenza_cliente"):
            tipo_problema = st.selectbox("Seleziona la tipologia di richiesta:", ("Errore nel caricamento del file video", "Problema nella generazione del report PDF", "Richiesta acquisto pacchetto crediti EXTRA", "Disdetta abbonamento (Preavviso 7 giorni)", "Altra segnalazione tecnica"))
            preferenza_contatto = st.radio("Come preferisci essere ricontattato?", ("Email", "Telefono"))
            recapito_utente = st.text_input("Inserisci la tua Email o il tuo numero di Telefono:", placeholder="Es. ing.rossi@aziendacliente.it oppure 3331234567")
            descrizione_problema = st.text_area("Descrivi brevemente la richiesta o il problema riscontrato:")
            
            btn_invia_ticket = st.form_submit_button("Invia Richiesta di Assistenza", use_container_width=True)

        if btn_invia_ticket:
            if recapito_utente and descrizione_problema:
                try:
                    supabase.table("ticket_assistenza").insert({"codice_licenza": st.session_state['codice_licenza'], "cliente": cliente_nome, "tipo_problema": tipo_problema, "preferenza_contatto": preferenza_contatto, "recapito": recapito_utente, "descrizione": descrizione_problema, "stato": "Aperto"}).execute()
                    st.success("✅ Richiesta inviata con successo! Il nostro team tecnico ha preso in carico la segnalazione. Puoi chiudere questa finestra.")
                except Exception as e:
                    st.error(f"⚠️ Errore nell'invio della richiesta.")
            else:
                st.warning("⚠️ Compila tutti i campi (recapito e descrizione) prima di inviare la richiesta.")

# --- FOOTER LEGALE AZIENDALE OBBIGATORIO ---
st.markdown("""
    <br><br>
    <div style="border-top: 1px solid #1e3a8a; padding-top: 20px; text-align: center; color: #64748b; font-size: 12px; margin-top: 50px; margin-bottom: 10px;">
        <b>HydroAegis AI</b> sviluppato da HydroAegis <br>
        Sede Legale: Via Campagna 18, 21036 Gemonio (VA) | P.IVA: In fase di attivazione <br>
        Contatti: info@hydroaegis.it | PEC: hydroaegis@pec.it
    </div>
""", unsafe_allow_html=True)

# Layout a colonne per centrare il pulsante nativo di Streamlit
col_vuota_sx, col_link, col_vuota_dx = st.columns([4, 2, 4])
with col_link:
    st.page_link("pages/privacy.py", label="Informativa sulla Privacy", icon="🛡️")
