import os, sys, base64, hmac, hashlib, secrets, sqlite3, html as _html

# ── SSL fix para Python 3.14 / Windows — DEBE IR ANTES DE CUALQUIER IMPORT DE GOOGLE ──
os.environ["PYTHONHTTPSVERIFY"] = "0"
os.environ["REQUESTS_CA_BUNDLE"] = ""
os.environ["SSL_CERT_FILE"] = ""
os.environ["CURL_CA_BUNDLE"] = ""
try:
    import ssl as _ssl
    _ssl._create_default_https_context = _ssl._create_unverified_context
except Exception:
    pass
try:
    import urllib3 as _u3
    _u3.disable_warnings(_u3.exceptions.InsecureRequestWarning)
except Exception:
    pass
try:
    import requests as _req_ssl
    _orig_send = _req_ssl.Session.send
    def _no_verify_send(self, r, **kw):
        kw["verify"] = False
        return _orig_send(self, r, **kw)
    _req_ssl.Session.send = _no_verify_send
except Exception:
    pass
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
try:
    import plotly.graph_objects as go
    import plotly.express as px
    _PLOTLY_OK = True
except ImportError:
    _PLOTLY_OK = False
import pytz, requests, concurrent.futures
from datetime import datetime, timedelta
from collections import defaultdict

# ─────────────────────────────────────────────────────────
# 1. PAGE CONFIG — siempre primero
# ─────────────────────────────────────────────────────────
st.set_page_config(page_title="Torneo Fefe Wolf 2026", layout="wide", page_icon="🏆")
st.markdown('<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">',
            unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# 2. CSS — cacheado, se inyecta ANTES de cualquier import lento
# ─────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _css():
    css_path = os.path.join("ui","styles.css")
    if not os.path.exists(css_path): return ""
    with open(css_path,"r",encoding="utf-8") as f: css = f.read()
    img = os.path.join("ui","FORMULEROS.jpg")
    bg  = ""
    if os.path.exists(img):
        with open(img,"rb") as f2: bg = "data:image/jpeg;base64,"+base64.b64encode(f2.read()).decode()
    return css.replace("__LOGIN_BG__", bg)

def load_css():
    c = _css()
    if c: st.markdown(f"<style>{c}</style>", unsafe_allow_html=True)

load_css()

# CSS global — tablas centradas + mejoras mobile
st.markdown("""
<style>
/* ── Tablas historial — centradas y scroll horizontal en mobile ── */
.tabla_historial_dark {
    width: 100%; max-width: 900px;
    margin: 10px auto 12px auto !important;
    border-collapse: collapse;
    background: rgba(7,10,25,.96); color: #e8ecff;
    border: 1px solid rgba(212,175,55,.25);
    border-radius: 14px; overflow-x: auto; display: block; font-size: 14px;
}
.tabla_historial_dark th {
    background: linear-gradient(90deg, rgba(212,175,55,.18), rgba(255,255,255,.03));
    color: #ffdd7a; text-align: center; padding: 12px 14px;
    border-bottom: 1px solid rgba(212,175,55,.22); font-weight: 800;
}
.tabla_historial_dark td {
    padding: 11px 14px; color: #e8ecff; text-align: center;
    border-bottom: 1px solid rgba(255,255,255,.06); background: rgba(255,255,255,.02);
}
.tabla_historial_dark tr:hover td { background: rgba(255,221,122,.05); }
/* fw-table también centrada */
.fw-table-wrap { overflow-x: auto; }
/* Selectbox golden arrow — desktop + mobile */
[data-baseweb="select"] > div:first-child {
  border-color: rgba(212,175,55,.4) !important;
  background: rgba(5,7,18,.95) !important;
}
[data-baseweb="select"] > div:first-child:hover,
[data-baseweb="select"] > div:first-child:focus-within {
  border-color: rgba(212,175,55,.85) !important;
  box-shadow: 0 0 8px rgba(212,175,55,.18) !important;
}
[data-baseweb="select"] svg { fill: #d4af37 !important; }
[data-testid="stSelectbox"] label { color: rgba(246,195,73,.8) !important; }
/* Mobile responsive */
@media (max-width:640px) {
  .mc-bubble { max-width:96% !important; }
  .mc-bubble-text { font-size:12px !important; }
  [data-testid="stSidebar"] { min-width:200px !important; }
  /* Pilot cards */
  .fw-pilot-card { min-width:110px !important; padding:12px 8px !important; }
  .fw-pilot-name { font-size:10px !important; }
  /* Profile */
  .prof-stat-val { font-size:22px !important; }
  .prof-stat-lbl { font-size:9px !important; }
  /* Podio */
  .pod-pts { font-size:24px !important; }
  .pod-medal { font-size:28px !important; }
  /* Section titles */
  .section-title { font-size:18px !important; }
  /* Logros grid */
  .logro-grid { grid-template-columns: repeat(2,1fr) !important; }
  /* Hide decorative elements on mobile */
  .fw-deco { display:none !important; }
  /* Sidebar compact */
  .sidebar-profile-card { padding:10px 8px !important; }
  /* Tables */
  table { font-size:11px !important; }
  th, td { padding:5px 4px !important; }
}
@media (max-width:480px) {
  .fw-pilot-card { min-width:90px !important; }
  .fw-pilot-name { font-size:9px !important; }
  .prof-stat-val { font-size:18px !important; }
  .pod-pts { font-size:20px !important; }
}
/* Mesa Chica MOD badge glow */
.mc-badge {
  display:inline-flex!important; align-items:center!important; gap:4px!important;
  white-space:nowrap!important; flex-shrink:0!important;
  border-radius:20px!important; padding:2px 8px!important;
  font-size:9px!important; font-weight:800!important; letter-spacing:.06em!important;
}
.mc-badge.fipf { background:linear-gradient(90deg,#0d2a6e,#1565c0,#0d2a6e)!important;
  color:#90caf9!important; border:1px solid rgba(100,180,255,.5)!important;
  box-shadow:0 0 10px rgba(21,101,192,.4)!important;
  text-shadow:0 0 8px rgba(100,180,255,.6); }
.mc-stars { color:#d4af37!important; text-shadow:0 0 6px #d4af37; }
.mc-badge.formulero { background:linear-gradient(90deg,#4a0080,#7b2ff7,#4a0080)!important;
  color:#e0b0ff!important; border:1px solid rgba(180,100,255,.6)!important;
  box-shadow:0 0 10px rgba(123,47,247,.4)!important;
  text-shadow:0 0 8px rgba(200,140,255,.7); font-weight:800!important; }
.fw-table { width: 100%; max-width: 860px; margin: 0 auto; }
/* Hide native sidebar collapse arrow - all possible selectors */
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarHeader"] button,
button[data-testid="collapsedControl"],
button[data-testid="baseButton-headerNoPadding"],
.st-emotion-cache-1cyp2mc,
.st-emotion-cache-czk5ss,
.st-emotion-cache-vk3wp9,
button[aria-label="Collapse sidebar"],
button[aria-label="Expand sidebar"],
button[aria-label="Close sidebar"],
button[aria-label="Open sidebar"],
[data-testid="baseButton-headerNoPadding"] { display: none !important; }
/* Mobile */
@media (max-width: 768px) {
    .tabla_historial_dark { font-size: 12px; }
    .tabla_historial_dark th, .tabla_historial_dark td { padding: 8px 6px; }
    .mc-title { font-size: 20px !important; }
}
/* ── Login fullscreen style (prodef1.com inspired) ── */
.fw-login-card {
    background-size: cover !important;
    background-position: center 20% !important;
    background-repeat: no-repeat !important;
    border-radius: 14px 14px 0 0 !important;
    min-height: 260px !important; max-height: 320px !important;
    overflow: hidden !important; position: relative !important;
}
/* Fullscreen background on login page */
[data-testid="stAppViewContainer"]:has(.fw-login-page) {
    background-attachment: fixed !important;
    background-size: cover !important;
}
.fw-login-shell { width:100%!important; max-width:480px!important; margin:0 auto!important; }
.fw-login-shell-outer {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg,rgba(6,15,40,.92),rgba(0,8,30,.88));
    padding: 20px;
}
.fw-login-overlay {
    position:absolute!important; bottom:0!important; left:0!important; right:0!important;
    height:55%!important;
    background:linear-gradient(to top,rgba(6,15,40,.98) 0%,transparent 100%)!important;
}
.fw-login-inner { position:relative!important; z-index:2!important; }
.fw-login-page { max-width:480px!important; margin:0 auto!important; padding-top:6px!important; }
.fw-login-form-header { text-align:center!important; padding:12px 0 6px!important; }
.fw-login-form-title { font-size:20px!important; font-weight:900!important;
    color:#ffdd7a!important; letter-spacing:.08em!important; }
.fw-login-form-sub { font-size:11px!important; color:rgba(169,178,214,.6)!important; }
/* ── LOGIN BUTTON — azul oscuro + texto dorado + borde azul neón ── */
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-secondary"][kind="secondary"],
div[data-testid="stButton"] > button,
.stButton > button {
    background: linear-gradient(135deg,#060f28 0%,#0c1e50 100%) !important;
    border: 1.5px solid #3b82f6 !important;
    border-radius: 8px !important;
    box-shadow: 0 2px 12px rgba(59,130,246,.25) !important;
    padding: 0.35rem 0.7rem !important;
    min-height: 0 !important;
}
button[data-testid="baseButton-secondary"] p,
button[data-testid="baseButton-secondary"] span,
div[data-testid="stButton"] > button p,
.stButton > button p {
    color: #D4AF37 !important;
    font-weight: 800 !important;
    letter-spacing: .06em !important;
    font-size: 0.86rem !important;
    text-shadow: 0 0 10px rgba(212,175,55,.5) !important;
}
button[data-testid="baseButton-secondary"]:hover,
div[data-testid="stButton"] > button:hover {
    border-color: #60a5fa !important;
    background: linear-gradient(135deg,#0b1d4d 0%,#162d7a 100%) !important;
    box-shadow: 0 0 30px rgba(59,130,246,.7) !important;
}
button[data-testid="baseButton-secondary"]:hover p,
button[data-testid="baseButton-secondary"]:hover span,
div[data-testid="stButton"] > button:hover p { color:#ffe896 !important; }
/* Kill any red background on login button */
[data-testid="baseButton-secondary"][style*="background"],
button[kind="secondary"][style*="red"],
button[kind="secondary"][style*="#ff"],
button[kind="secondary"][style*="rgb("] {
    background: linear-gradient(135deg,#060f28 0%,#0c1e50 100%) !important;
}

/* ══════════════════════════════════════════════════════════════
   TEMA GLOBAL — AZUL + DORADO  (Torneo Fefe Wolf)
   ══════════════════════════════════════════════════════════════ */

/* ═══ NUCLEAR BUTTON OVERRIDE — azul + dorado, SIN ROJO ═══ */
/* Targets every possible Streamlit button selector including inline styles */
.stButton > button,
.stButton > button:focus,
.stButton > button:active,
div[data-testid="stButton"] > button,
div[data-testid="stButton"] > button:focus,
button[data-testid^="baseButton"],
button[data-testid="baseButton-primary"],
button[data-testid="baseButton-secondary"],
button[data-testid="baseButton-tertiary"],
button[kind="primary"],
button[kind="secondary"],
button[kind="tertiary"],
[data-testid="stBaseButton-primary"],
[data-testid="stBaseButton-secondary"],
section[data-testid="stSidebar"] button,
.stMainBlockContainer button:not([data-baseweb="tab"]):not(.stChatInputSubmitButton) {
    background: linear-gradient(135deg,#060f28 0%,#0c1e50 100%) !important;
    background-color: #060f28 !important;
    border: 1.5px solid #3b82f6 !important;
    border-radius: 8px !important;
    color: #D4AF37 !important;
    box-shadow: 0 2px 12px rgba(59,130,246,.25) !important;
    transition: all .2s ease !important;
}
.stButton > button:hover,
div[data-testid="stButton"] > button:hover,
button[data-testid^="baseButton"]:hover {
    background: linear-gradient(135deg,#0c1e50 0%,#1a3278 100%) !important;
    background-color: #0c1e50 !important;
    border-color: #60a5fa !important;
    box-shadow: 0 4px 20px rgba(59,130,246,.5) !important;
}
/* Force text gold — ALL variants */
.stButton > button p, .stButton > button span, .stButton > button div,
div[data-testid="stButton"] > button p, div[data-testid="stButton"] > button span,
button[data-testid^="baseButton"] p, button[data-testid^="baseButton"] span,
button[data-testid="baseButton-primary"] p, button[data-testid="baseButton-primary"] span,
button[kind="primary"] p, button[kind="secondary"] p, button[kind="tertiary"] p,
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-secondary"] p {
    color: #D4AF37 !important;
    font-weight: 700 !important;
}
.stButton > button:hover p, div[data-testid="stButton"] > button:hover p,
button[data-testid^="baseButton"]:hover p { color: #ffe896 !important; }
/* Kill Streamlit's inline background-color from config.toml primaryColor */
button[style*="background-color"],
button[style*="background:"] {
    background: linear-gradient(135deg,#060f28 0%,#0c1e50 100%) !important;
    background-color: #060f28 !important;
}

/* Tabs — keep transparent */
button[data-baseweb="tab"],
button[data-baseweb="tab"]:hover {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
button[data-baseweb="tab"] p { color: rgba(169,178,214,.65) !important; }
button[data-baseweb="tab"][aria-selected="true"] p { color: #D4AF37 !important; }

/* Metrics */
[data-testid="stMetricValue"] { color: #D4AF37 !important; font-weight: 900 !important; }
[data-testid="stMetricLabel"] { color: rgba(169,178,214,.6) !important; }
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────
# 3. LAZY MODULE LOADERS
# ─────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _mod_auth():
    try:
        from core.auth import (login, change_password, reset_password_with_mother,
                               bootstrap_user, get_user_row, admin_update_user_fields,
                               admin_reset_password, verify_pin, set_pin, save_foto_url)
        return dict(login=login, change_password=change_password,
                    reset_password_with_mother=reset_password_with_mother,
                    bootstrap_user=bootstrap_user, get_user_row=get_user_row,
                    admin_update_user_fields=admin_update_user_fields,
                    admin_reset_password=admin_reset_password,
                    verify_pin=verify_pin, set_pin=set_pin,
                    save_foto_url=save_foto_url)
    except Exception as e:
        return {"_error": str(e)}

@st.cache_resource(show_spinner=False)
def _mod_db():
    try:
        from core.database import (guardar_etapa, recuperar_predicciones_piloto,
                                   leer_tabla_posiciones, actualizar_tabla_general,
                                   guardar_historial, leer_historial_df,
                                   leer_historial_detalle_df, lock_exists, set_lock,
                                   clear_lock,
                                   aplicar_sanciones_dns, aplicar_bonus_campeones_final,
                                   revertir_dns_gp, leer_predicciones_raw_gp)
        # Optional — only in updated database.py
        try:
            from core.database import guardar_resultados_oficiales, leer_resultados_oficiales
        except ImportError:
            def guardar_resultados_oficiales(gp, oficial): return False
            def leer_resultados_oficiales(gp): return {}
        return dict(guardar_etapa=guardar_etapa,
                    recuperar_predicciones_piloto=recuperar_predicciones_piloto,
                    leer_tabla_posiciones=leer_tabla_posiciones,
                    actualizar_tabla_general=actualizar_tabla_general,
                    guardar_historial=guardar_historial,
                    leer_historial_df=leer_historial_df,
                    leer_historial_detalle_df=leer_historial_detalle_df,
                    lock_exists=lock_exists, set_lock=set_lock,
                    clear_lock=clear_lock,
                    aplicar_sanciones_dns=aplicar_sanciones_dns,
                    aplicar_bonus_campeones_final=aplicar_bonus_campeones_final,
                    revertir_dns_gp=revertir_dns_gp,
                    leer_predicciones_raw_gp=leer_predicciones_raw_gp,
                    guardar_resultados_oficiales=guardar_resultados_oficiales,
                    leer_resultados_oficiales=leer_resultados_oficiales)
    except Exception as e:
        return {"_error": str(e)}

@st.cache_resource(show_spinner=False)
def _mod_admin():
    try:
        from core.admin_tools import calcular_y_actualizar_todos, generar_historial_solo
        return dict(calcular=calcular_y_actualizar_todos, historial=generar_historial_solo)
    except Exception as e:
        return {"_error": str(e)}

@st.cache_resource(show_spinner=False)
def _mod_core():
    try:
        from core.scoring import calcular_puntos
        from core.rules  import obtener_estado_gp
        from core.utils  import normalizar_nombre
        return dict(calcular_puntos=calcular_puntos,
                    obtener_estado_gp=obtener_estado_gp,
                    normalizar_nombre=normalizar_nombre)
    except Exception as e:
        return {"_error": str(e)}

@st.cache_resource(show_spinner=False)
def _mod_mesa():
    try:
        from core.mesa_chica_db import (mc_is_mod, mc_badge_for, mc_is_spam,
                                         mc_add_message, mc_list_messages,
                                         mc_update_message, mc_soft_delete_message,
                                         mc_purge_html_messages, _mc_safe_text,
                                         mc_toggle_like, mc_like_count, mc_user_liked)
    except Exception as e:
        return {"_error": str(e)}

    # News functions — always defined inline (SQLite) — never imported
    # This ensures compatibility regardless of which mesa_chica_db.py version is deployed
    def _news_ts():
        import datetime as _dtn
        try:
            import pytz as _tzn
            return _dtn.datetime.now(_tzn.timezone("America/Argentina/Buenos_Aires")).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return _dtn.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def news_can_publish(u):
        return str(u).strip() in {"Checo Perez", "Lando Norris"}

    def _ndb():
        import sqlite3 as _sq
        c = _sq.connect("mesa_chica.db", check_same_thread=False)
        c.execute("CREATE TABLE IF NOT EXISTS paddock_noticias (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                  "autor TEXT, titulo TEXT, imagen_url TEXT, cuerpo TEXT, ts TEXT, "
                  "deleted INTEGER NOT NULL DEFAULT 0, deleted_ts TEXT, deleted_by TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS paddock_noticias_reacciones "
                  "(noticia_id INTEGER, usuario TEXT, emoji TEXT, ts TEXT, "
                  "PRIMARY KEY (noticia_id, usuario, emoji))")
        c.execute("CREATE TABLE IF NOT EXISTS paddock_noticias_comentarios "
                  "(id INTEGER PRIMARY KEY AUTOINCREMENT, noticia_id INTEGER, "
                  "autor TEXT, texto TEXT, ts TEXT, deleted INTEGER NOT NULL DEFAULT 0)")
        c.commit(); return c

    def news_toggle_reaccion(noticia_id, usuario, emoji):
        """Devuelve True si quedó con reacción, False si se quitó."""
        try:
            c = _ndb()
            existing = c.execute(
                "SELECT 1 FROM paddock_noticias_reacciones WHERE noticia_id=? AND usuario=? AND emoji=?",
                (int(noticia_id), str(usuario), str(emoji))).fetchone()
            if existing:
                c.execute("DELETE FROM paddock_noticias_reacciones WHERE noticia_id=? AND usuario=? AND emoji=?",
                          (int(noticia_id), str(usuario), str(emoji)))
                c.commit(); c.close(); return False
            else:
                c.execute("INSERT INTO paddock_noticias_reacciones (noticia_id,usuario,emoji,ts) VALUES (?,?,?,?)",
                          (int(noticia_id), str(usuario), str(emoji), _news_ts()))
                c.commit(); c.close(); return True
        except Exception: return False

    def news_get_reacciones(noticia_id):
        """Retorna dict {emoji: count}"""
        try:
            c = _ndb()
            rows = c.execute(
                "SELECT emoji, COUNT(*) as cnt FROM paddock_noticias_reacciones "
                "WHERE noticia_id=? GROUP BY emoji", (int(noticia_id),)).fetchall()
            c.close(); return {r[0]: r[1] for r in rows}
        except Exception: return {}

    def news_user_reacciones(noticia_id, usuario):
        """Retorna set de emojis que el usuario puso"""
        try:
            c = _ndb()
            rows = c.execute(
                "SELECT emoji FROM paddock_noticias_reacciones WHERE noticia_id=? AND usuario=?",
                (int(noticia_id), str(usuario))).fetchall()
            c.close(); return {r[0] for r in rows}
        except Exception: return set()

    def news_add_comentario(noticia_id, autor, texto):
        _ts_c = _news_ts()
        # Write to SQLite
        try:
            c = _ndb()
            c.execute("INSERT INTO paddock_noticias_comentarios (noticia_id,autor,texto,ts,deleted) VALUES (?,?,?,?,0)",
                      (int(noticia_id), str(autor), str(texto).strip(), _ts_c))
            c.commit(); c.close()
        except Exception: pass
        # Persist to GSheets (Comentarios tab)
        try:
            from core.database import conectar_google_sheets as _cgs_c, _GS_CACHE as _gsc_c
            _ws_c = _cgs_c("Comentarios")
            if _ws_c is None:
                _ss_c = _gsc_c.get("ss")
                if _ss_c:
                    _ws_c = _ss_c.add_worksheet("Comentarios", rows=2000, cols=6)
                    _ws_c.update("A1", [["id","noticia_id","autor","texto","ts","deleted"]])
            if _ws_c:
                _all_c = _ws_c.get_all_values()
                if not _all_c:
                    _ws_c.append_row(["id","noticia_id","autor","texto","ts","deleted"])
                    _all_c = [["id","noticia_id","autor","texto","ts","deleted"]]
                _nid_c = len(_all_c)
                _ws_c.append_row([_nid_c, int(noticia_id), str(autor), str(texto).strip(), _ts_c, 0])
        except Exception: pass

    def news_get_comentarios(noticia_id):
        # Try SQLite first
        try:
            c = _ndb()
            rows = c.execute(
                "SELECT id,autor,texto,ts FROM paddock_noticias_comentarios "
                "WHERE noticia_id=? AND deleted=0 ORDER BY id ASC", (int(noticia_id),)).fetchall()
            c.close()
            if rows: return rows
        except Exception: pass
        # Fallback: GSheets (sobrevive reinicios de Streamlit Cloud)
        try:
            from core.database import conectar_google_sheets as _cgs_gc
            _ws_gc = _cgs_gc("Comentarios")
            if _ws_gc:
                _vals_gc = _ws_gc.get_all_values()
                if _vals_gc and len(_vals_gc) > 1:
                    _hdr_gc = [h.lower().strip() for h in _vals_gc[0]]
                    def _ci(name, d):
                        return _hdr_gc.index(name) if name in _hdr_gc else d
                    _i_id  = _ci("id",0); _i_nid = _ci("noticia_id",1)
                    _i_aut = _ci("autor",2); _i_txt = _ci("texto",3)
                    _i_ts  = _ci("ts",4); _i_del = _ci("deleted",5)
                    _out = []
                    for _r in _vals_gc[1:]:
                        try:
                            _nid_v = str(_r[_i_nid]) if _i_nid < len(_r) else ""
                            if _nid_v != str(noticia_id): continue
                            _del_v = str(_r[_i_del]) if (_i_del is not None and _i_del < len(_r)) else "0"
                            if _del_v in ("1","True","true"): continue
                            _id_v = 0
                            try: _id_v = int(_r[_i_id]) if _i_id < len(_r) else 0
                            except Exception: _id_v = 0
                            _out.append((
                                _id_v,
                                str(_r[_i_aut]) if _i_aut < len(_r) else "",
                                str(_r[_i_txt]) if _i_txt < len(_r) else "",
                                str(_r[_i_ts]) if _i_ts < len(_r) else ""))
                        except Exception: continue
                    return _out
        except Exception: pass
        return []

    def news_delete_comentario(com_id):
        try:
            c = _ndb()
            c.execute("UPDATE paddock_noticias_comentarios SET deleted=1 WHERE id=?", (int(com_id),))
            c.commit(); c.close()
        except Exception: pass

    def news_add(autor, titulo, cuerpo="", imagen_url=""):
        """Guarda noticia — GSheets para persistencia, SQLite para imagen base64."""
        _img_for_sheets = "" if str(imagen_url or "").startswith("data:") else str(imagen_url or "")
        _ts_n = _news_ts()
        # Always write to SQLite (supports base64 images)
        try:
            c = _ndb()
            c.execute("INSERT INTO paddock_noticias (autor,titulo,imagen_url,cuerpo,ts,deleted) VALUES (?,?,?,?,?,0)",
                      (str(autor), str(titulo), str(imagen_url or ""), str(cuerpo or ""), _ts_n))
            c.commit(); c.close()
        except Exception: pass
        # Write to Google Sheets (sin base64 — usa URL directo o vacío)
        try:
            from core.database import conectar_google_sheets as _cgs_n, _GS_CACHE as _cache_n
            _ws_n = _cgs_n("Noticias")
            if _ws_n is None:
                try:
                    _ss_n = _cache_n.get("ss")
                    if _ss_n is None:
                        _cgs_n("sheet1"); _ss_n = _cache_n.get("ss")
                    if _ss_n:
                        _ws_n = _ss_n.add_worksheet("Noticias", rows=500, cols=8)
                        _ws_n.update("A1", [["id","autor","titulo","imagen_url","cuerpo","ts","deleted","deleted_by"]])
                except Exception: pass
            if _ws_n:
                _all_n = _ws_n.get_all_values()
                _next_id = len(_all_n)
                _ws_n.append_row([_next_id, str(autor), str(titulo), _img_for_sheets,
                                   str(cuerpo or ""), _ts_n, 0, ""])
        except Exception: pass

    def news_list(limit=50):
        """Lee noticias — Sheets para persistencia, SQLite para imágenes base64."""
        _sheets_rows = []
        _sqlite_rows = {}
        # Leer SQLite para tener las imágenes base64 (aunque se borren en reinicios)
        try:
            c = _ndb()
            _sq = c.execute("SELECT id,autor,titulo,imagen_url,cuerpo,ts FROM paddock_noticias "
                            "WHERE deleted=0 ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            c.close()
            for _sr in _sq:
                _sqlite_rows[int(_sr[0])] = _sr
        except Exception: pass
        # Leer Sheets (fuente principal)
        try:
            from core.database import conectar_google_sheets as _cgs_n2
            _ws_n2 = _cgs_n2("Noticias")
            if _ws_n2:
                _rows_n2 = _ws_n2.get_all_records()
                _out = []
                for _r in reversed(_rows_n2):
                    if str(_r.get("deleted","0")) in ("1","True","true"): continue
                    try:
                        _nid = int(_r.get("id",0))
                        _img = str(_r.get("imagen_url","")).strip()
                        # Si Sheets no tiene imagen pero SQLite sí, usar SQLite
                        if not _img and _nid in _sqlite_rows:
                            _img = str(_sqlite_rows[_nid][3] or "")
                        _out.append((_nid, str(_r.get("autor","")),
                                     str(_r.get("titulo","")), _img,
                                     str(_r.get("cuerpo","")), str(_r.get("ts",""))))
                    except Exception: pass
                    if len(_out) >= limit: break
                if _out: return _out
        except Exception: pass
        # Fallback: solo SQLite
        return list(_sqlite_rows.values()) if _sqlite_rows else []

    def news_delete(nid, deleted_by=""):
        try:
            from core.database import conectar_google_sheets as _cgs_nd
            _ws_nd = _cgs_nd("Noticias")
            if _ws_nd:
                _recs = _ws_nd.get_all_records()
                for _i, _r in enumerate(_recs, start=2):
                    if str(_r.get("id","")) == str(nid):
                        _ws_nd.update_cell(_i, 7, 1)
                        _ws_nd.update_cell(_i, 8, str(deleted_by))
                        return
        except Exception: pass
        try:
            c = _ndb()
            c.execute("UPDATE paddock_noticias SET deleted=1,deleted_ts=?,deleted_by=? WHERE id=?",
                      (_news_ts(), str(deleted_by), int(nid)))
            c.commit(); c.close()
        except Exception: pass

    def news_update(nid, titulo, cuerpo, imagen_url):
        try:
            from core.database import conectar_google_sheets as _cgs_nu
            _ws_nu = _cgs_nu("Noticias")
            if _ws_nu:
                _recs = _ws_nu.get_all_records()
                for _i, _r in enumerate(_recs, start=2):
                    if str(_r.get("id","")) == str(nid):
                        _ws_nu.update(f"C{_i}:E{_i}", [[str(titulo or ""), str(imagen_url or ""), str(cuerpo or "")]])
                        return
        except Exception: pass
        try:
            c = _ndb()
            c.execute("UPDATE paddock_noticias SET titulo=?,cuerpo=?,imagen_url=? WHERE id=?",
                      (str(titulo or ""), str(cuerpo or ""), str(imagen_url or ""), int(nid)))
            c.commit(); c.close()
        except Exception: pass

    return dict(mc_is_mod=mc_is_mod, mc_badge_for=mc_badge_for,
                mc_is_spam=mc_is_spam, mc_add_message=mc_add_message,
                mc_list_messages=mc_list_messages,
                mc_update_message=mc_update_message,
                mc_soft_delete_message=mc_soft_delete_message,
                mc_purge_html_messages=mc_purge_html_messages,
                _mc_safe_text=_mc_safe_text,
                mc_toggle_like=mc_toggle_like,
                mc_like_count=mc_like_count,
                mc_user_liked=mc_user_liked,
                news_can_publish=news_can_publish,
                news_add=news_add, news_list=news_list,
                news_delete=news_delete, news_update=news_update,
                news_toggle_reaccion=news_toggle_reaccion,
                news_get_reacciones=news_get_reacciones,
                news_user_reacciones=news_user_reacciones,
                news_add_comentario=news_add_comentario,
                news_get_comentarios=news_get_comentarios,
                news_delete_comentario=news_delete_comentario)

def _auth(fn, *a, default=(False,"Módulo no disponible"), timeout=10, **kw):
    m = _mod_auth()
    if "_error" in m or fn not in m: return default
    return _safe_call(m[fn], *a, timeout_sec=timeout, default=default, **kw)

def _db(fn, *a, default=None, timeout=8, **kw):
    m = _mod_db()
    if "_error" in m or fn not in m: return default
    return _safe_call(m[fn], *a, timeout_sec=timeout, default=default, **kw)

def _core(fn, *a, default=None, timeout=4, **kw):
    m = _mod_core()
    if "_error" in m or fn not in m: return default
    return _safe_call(m[fn], *a, timeout_sec=timeout, default=default, **kw)

def _safe_call(fn, *a, timeout_sec=8, default=None, **kw):
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, *a, **kw)
        try:    return fut.result(timeout=timeout_sec)
        except: return default

# ─────────────────────────────────────────────────────────
# 4. CONSTANTES
# ─────────────────────────────────────────────────────────
TZ = pytz.timezone("America/Argentina/Buenos_Aires")
API_BASE = "http://127.0.0.1:8000"

HORARIOS_CARRERA = {
    "01. Gran Premio de Australia":      "2026-03-08 01:00",
    "02. Gran Premio de China":          "2026-03-15 04:00",
    "03. Gran Premio de Japón":          "2026-03-29 02:00",
    "04. Gran Premio de Baréin":         "2026-04-12 12:00",
    "05. Gran Premio de Arabia Saudita": "2026-04-19 14:00",
    "06. Gran Premio de Miami":          "2026-05-03 13:00",
    "07. Gran Premio de Canadá":         "2026-05-24 15:00",
    "08. Gran Premio de Mónaco":         "2026-06-07 10:00",
    "09. Gran Premio de España":         "2026-06-14 10:00",
    "10. Gran Premio de Austria":        "2026-06-28 10:00",
    "11. Gran Premio de Gran Bretaña":   "2026-07-05 11:00",
    "12. Gran Premio de Bélgica":        "2026-07-19 10:00",
    "13. Gran Premio de Hungría":        "2026-07-26 10:00",
    "14. Gran Premio de los Países Bajos":"2026-08-23 10:00",
    "15. Gran Premio de Italia":         "2026-09-06 10:00",
    "16. Gran Premio de Madrid":         "2026-09-13 10:00",
    "17. Gran Premio de Azerbaiyán":     "2026-09-27 08:00",
    "18. Gran Premio de Singapur":       "2026-10-11 09:00",
    "19. Gran Premio de los Estados Unidos":"2026-10-25 17:00",
    "20. Gran Premio de México":         "2026-11-01 17:00",
    "21. Gran Premio de Brasil":         "2026-11-08 14:00",
    "22. Gran Premio de Las Vegas":      "2026-11-21 01:00",
    "23. Gran Premio de Qatar":          "2026-11-29 13:00",
    "24. Gran Premio de Abu Dabi":       "2026-12-06 10:00",
}
GPS_OFICIALES = list(HORARIOS_CARRERA.keys())
GPS_SPRINT = [
    "02. Gran Premio de China",
    "06. Gran Premio de Miami",
    "07. Gran Premio de Canadá",
    "11. Gran Premio de Gran Bretaña",
    "14. Gran Premio de los Países Bajos",
    "18. Gran Premio de Singapur",
]
# ── GPs suspendidos por la F1 oficial 2026 ────────────────────
GPS_SUSPENDIDOS = [
    "04. Gran Premio de Baréin",
    "05. Gran Premio de Arabia Saudita",
]
GPS_ACTIVOS = [g for g in GPS_OFICIALES if g not in GPS_SUSPENDIDOS]
PILOTOS_TORNEO = ["Checo Perez","Nicki Lauda","Valteri Bottas","Lando Norris","Fernando Alonso","Yuki Tsunoda"]

# ── DNS: base histórica manual (fallback si la columna DNS aún no existe en Supabase) ──
DNS_BASE_HISTORICO = {
    "Fernando Alonso": 3,
    "Nicki Lauda":      2,
    "Lando Norris":     1,
}
DNS_GP_DESDE = "11. Gran Premio de Gran Bretaña"

@st.cache_data(ttl=60, show_spinner=False)
def _dns_counts_todos():
    """Cuenta sanciones DNS por piloto leyendo la columna DNS real de Supabase
    (tabla posiciones). Si esa columna todavía no existe (falta migración SQL),
    usa la base histórica manual como fallback."""
    counts = {p: DNS_BASE_HISTORICO.get(p, 0) for p in PILOTOS_TORNEO}
    try:
        m = _mod_db()
        if "_error" in m: return counts
        _df = _safe_call(m["leer_tabla_posiciones"], PILOTOS_TORNEO, timeout_sec=8, default=None)
        if _df is None or _df.empty or "DNS" not in _df.columns: return counts
        for _, _row in _df.iterrows():
            _pil = str(_row.get("Piloto","")).strip()
            if _pil in counts:
                counts[_pil] = int(_row.get("DNS", 0) or 0)
    except Exception:
        pass
    return counts

def _dns_count(usuario):
    """Cantidad total de sanciones DNS de un piloto/formulero."""
    return _dns_counts_todos().get(usuario, 0)
GRILLA_2026 = {
    "MCLAREN":      ["Oscar Piastri","Lando Norris"],
    "RED BULL":     ["Max Verstappen","Isack Hadjar"],
    "MERCEDES":     ["George Russell","Kimi Antonelli"],
    "FERRARI":      ["Charles Leclerc","Lewis Hamilton"],
    "WILLIAMS":     ["Alex Albon","Carlos Sainz"],
    "ASTON MARTIN": ["Lance Stroll","Fernando Alonso"],
    "RACING BULLS": ["Liam Lawson","Arvid Lindblad"],
    "HAAS":         ["Oliver Bearman","Esteban Ocon"],
    "AUDI":         ["Nico Hulkenberg","Gabriel Bortoleto"],
    "ALPINE":       ["Pierre Gasly","Franco Colapinto"],
    "CADILLAC":     ["Checo Perez","Valteri Bottas"],
}
ESCALA_CARRERA_JUEGO = {1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}
PILOTO_COLORS = {
    "Checo Perez":"#B026FF","Nicki Lauda":"#1E90FF","Lando Norris":"#FFA500","Fernando Alonso":"#FF4444",
    "Valteri Bottas":"#00CFFF","Yuki Tsunoda":"#A3E635",
}
TEAM_COLORS = {
    "MCLAREN":"#FF8000","RED BULL":"#3671C6","MERCEDES":"#00D2BE",
    "FERRARI":"#DC0000","WILLIAMS":"#005AFF","ASTON MARTIN":"#006F62",
    "RACING BULLS":"#2B4562","HAAS":"#B6BABD","AUDI":"#00E676",
    "ALPINE":"#FF4FD8","CADILLAC":"#E6C200",
}
TEAM_LOGOS_SVG = {
    "MCLAREN":"MCL","RED BULL":"RBR","MERCEDES":"AMG","FERRARI":"SF",
    "WILLIAMS":"WRC","ASTON MARTIN":"AMR","RACING BULLS":"RB",
    "HAAS":"HAA","AUDI":"AUD","ALPINE":"ALP","CADILLAC":"CAD",
}

# ── Logos oficiales de equipos (CDN Formula1.com) ──────────────
TEAM_LOGOS_CDN = {
    # Logos oficiales F1 — URLs directas y verificadas
    "MCLAREN":      "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/mclaren/2026mclarenlogowhite.webp",
    "RED BULL":     "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2025/redbullracing/2025redbullracinglogowhite.webp",
    "MERCEDES":     "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/mercedes/2026mercedeslogowhite.webp",
    "FERRARI":      "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/ferrari/2026ferrarilogowhite.webp",
    "WILLIAMS":     "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/williams/2026williamslogowhite.webp",
    "ASTON MARTIN": "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/astonmartin/2026astonmartinlogowhite.webp",
    "RACING BULLS": "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/racingbulls/2026racingbullslogowhite.webp",
    "HAAS":         "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/haasf1team/2026haasf1teamlogowhite.webp",
    "AUDI":         "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/audi/2026audilogowhite.webp",
    "ALPINE":       "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/alpine/2026alpinelogowhite.webp",
    "CADILLAC":     "https://media.formula1.com/image/upload/c_fit,h_64/q_auto/v1740000000/common/f1/2026/cadillac/2026cadillaclogowhite.webp",
}
# ── Imágenes de autos para constructores (módulo global) ──
TEAM_CARS_MODULE = {
    "MCLAREN":      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/mclaren/2026mclarencarright.webp",
    "RED BULL":     "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/redbullracing/2026redbullracingcarright.webp",
    "MERCEDES":     "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/mercedes/2026mercedescarright.webp",
    "FERRARI":      "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/ferrari/2026ferraricarright.webp",
    "WILLIAMS":     "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/williams/2026williamscarright.webp",
    "ASTON MARTIN": "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/astonmartin/2026astonmartincarright.webp",
    "RACING BULLS": "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/racingbulls/2026racingbullscarright.webp",
    "HAAS":         "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/haas/2026haascarright.webp",
    "AUDI":         "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/audi/2026audicarright.webp",
    "ALPINE":       "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/alpine/2026alpinecarright.webp",
    "CADILLAC":     "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2026/cadillac/2026cadillaccarright.webp",
}
DRIVER_PHOTOS = {
    # Cuerpo completo — usado en sección Pilotos y Escuderías
    "Lando Norris":      "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/mclaren/lannor01/2026mclarenlannor01right.webp",
    "Oscar Piastri":     "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/mclaren/oscpia01/2026mclarenoscpia01right.webp",
    "Max Verstappen":    "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/redbullracing/maxver01/2026redbullracingmaxver01right.webp",
    "Isack Hadjar":      "https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/common/f1/2026/redbullracing/isahad01/2026redbullracingisahad01right.webp",
    "George Russell":    "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/mercedes/georus01/2026mercedesgeorus01right.webp",
    "Kimi Antonelli":    "https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/common/f1/2026/mercedes/andant01/2026mercedesandant01right.webp",
    "Charles Leclerc":   "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/ferrari/chalec01/2026ferrarichalec01right.webp",
    "Lewis Hamilton":    "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/ferrari/lewham01/2026ferrarilewham01right.webp",
    "Alex Albon":        "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/williams/alealb01/2026williamsalealb01right.webp",
    "Carlos Sainz":      "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/williams/carsai01/2026williamscarsai01right.webp",
    "Lance Stroll":      "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/astonmartin/lanstr01/2026astonmartinlanstr01right.webp",
    "Fernando Alonso":   "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/astonmartin/feralo01/2026astonmartinferalo01right.webp",
    "Liam Lawson":       "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/racingbulls/lialaw01/2026racingbullslialaw01right.webp",
    "Arvid Lindblad":    "https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/common/f1/2026/racingbulls/arvlin01/2026racingbullsarvlin01right.webp",
    "Oliver Bearman":    "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/haasf1team/olibea01/2026haasf1teamolibea01right.webp",
    "Esteban Ocon":      "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/haasf1team/estoco01/2026haasf1teamestoco01right.webp",
    "Nico Hulkenberg":   "https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/common/f1/2026/audi/nichul01/2026audinichul01right.webp",
    "Gabriel Bortoleto": "https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/common/f1/2026/audi/gabbor01/2026audigabbor01right.webp",
    "Pierre Gasly":      "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/alpine/piegas01/2026alpinepiegas01right.webp",
    "Franco Colapinto":  "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000000/common/f1/2026/alpine/fracol01/2026alpinefracol01right.webp",
    "Checo Perez":       "https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/common/f1/2026/cadillac/serper01/2026cadillacserper01right.webp",
    "Valteri Bottas":    "https://media.formula1.com/image/upload/c_lfill,w_440/q_auto/v1740000000/common/f1/2026/cadillac/valbot01/2026cadillacvalbot01right.webp",
    "Yuki Tsunoda":      "https://media.formula1.com/image/upload/c_fill,w_720/q_auto/v1740000001/common/f1/2025/redbullracing/yuktsu01/2025redbullracingyuktsu01right.webp",
}

# Headshots (cara) — crop desde arriba con Cloudinary g_north — usado en Predicciones
DRIVER_HEADSHOTS = {
    "Lando Norris":      "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/mclaren/lannor01/2026mclarenlannor01right.webp",
    "Oscar Piastri":     "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/mclaren/oscpia01/2026mclarenoscpia01right.webp",
    "Max Verstappen":    "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/redbullracing/maxver01/2026redbullracingmaxver01right.webp",
    "Isack Hadjar":      "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/redbullracing/isahad01/2026redbullracingisahad01right.webp",
    "George Russell":    "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/mercedes/georus01/2026mercedesgeorus01right.webp",
    "Kimi Antonelli":    "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/mercedes/andant01/2026mercedesandant01right.webp",
    "Charles Leclerc":   "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/ferrari/chalec01/2026ferrarichalec01right.webp",
    "Lewis Hamilton":    "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/ferrari/lewham01/2026ferrarilewham01right.webp",
    "Alex Albon":        "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/williams/alealb01/2026williamsalealb01right.webp",
    "Carlos Sainz":      "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/williams/carsai01/2026williamscarsai01right.webp",
    "Lance Stroll":      "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/astonmartin/lanstr01/2026astonmartinlanstr01right.webp",
    "Fernando Alonso":   "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/astonmartin/feralo01/2026astonmartinferalo01right.webp",
    "Liam Lawson":       "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/racingbulls/lialaw01/2026racingbullslialaw01right.webp",
    "Arvid Lindblad":    "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/racingbulls/arvlin01/2026racingbullsarvlin01right.webp",
    "Oliver Bearman":    "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/haasf1team/olibea01/2026haasf1teamolibea01right.webp",
    "Esteban Ocon":      "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/haasf1team/estoco01/2026haasf1teamestoco01right.webp",
    "Nico Hulkenberg":   "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/audi/nichul01/2026audinichul01right.webp",
    "Gabriel Bortoleto": "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/audi/gabbor01/2026audigabbor01right.webp",
    "Pierre Gasly":      "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/alpine/piegas01/2026alpinepiegas01right.webp",
    "Franco Colapinto":  "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/alpine/fracol01/2026alpinefracol01right.webp",
    "Checo Perez":       "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/cadillac/serper01/2026cadillacserper01right.webp",
    "Valteri Bottas":    "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000000/common/f1/2026/cadillac/valbot01/2026cadillacvalbot01right.webp",
    # Nicki Lauda — foto real incrustada en base64
    "Nicki Lauda":       "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSgd3Dq9OHc2zK46t1QQLXbN_49nouLYDYv1w&s",
    "Yuki Tsunoda":      "https://media.formula1.com/image/upload/c_fill,w_272,h_272,g_north/q_auto/v1740000001/common/f1/2025/redbullracing/yuktsu01/2025redbullracingyuktsu01right.webp",
}
MESA_CHICA_MODS   = {"Valteri Bottas","Lando Norris","Fernando Alonso"}
MESA_CHICA_BADGES = {
    "Valteri Bottas": {"tipo":"fipf",      "label":"MIEMBRO FIPF","stars":"★"},
    "Lando Norris":   {"tipo":"fipf",      "label":"MIEMBRO FIPF","stars":""},
    "Fernando Alonso":{"tipo":"fipf",      "label":"MIEMBRO FIPF","stars":""},
    "Checo Perez":    {"tipo":"formulero", "label":"FORMULERO",   "stars":"★★★"},
    "Nicki Lauda":    {"tipo":"formulero", "label":"FORMULERO",   "stars":"★"},
    "Yuki Tsunoda":   {"tipo":"formulero", "label":"FORMULERO",   "stars":""},
}
CALENDARIO_VISUAL = [
    {"Fecha":"06-08 Mar","Gran Premio":"GP Australia",          "Circuito":"Melbourne",          "Formato":"Clásico"},
    {"Fecha":"13-15 Mar","Gran Premio":"GP China",              "Circuito":"Shanghái",           "Formato":"⚡ SPRINT"},
    {"Fecha":"27-29 Mar","Gran Premio":"GP Japón",              "Circuito":"Suzuka",             "Formato":"Clásico"},
    {"Fecha":"10-12 Abr","Gran Premio":"GP Bahréin ⛔ SUSPENDIDO","Circuito":"Sakhir",           "Formato":"❌ No juega"},
    {"Fecha":"17-19 Abr","Gran Premio":"GP Arabia Saudita ⛔ SUSPENDIDO","Circuito":"Jeddah",   "Formato":"❌ No juega"},
    {"Fecha":"01-03 May","Gran Premio":"GP Miami",              "Circuito":"Miami",              "Formato":"⚡ SPRINT"},
    {"Fecha":"22-24 May","Gran Premio":"GP Canadá",             "Circuito":"Montréal",           "Formato":"⚡ SPRINT"},
    {"Fecha":"05-07 Jun","Gran Premio":"GP Mónaco",             "Circuito":"Montecarlo",         "Formato":"Clásico"},
    {"Fecha":"12-14 Jun","Gran Premio":"GP España",             "Circuito":"Barcelona",          "Formato":"Clásico"},
    {"Fecha":"26-28 Jun","Gran Premio":"GP Austria",            "Circuito":"Spielberg",          "Formato":"Clásico"},
    {"Fecha":"03-05 Jul","Gran Premio":"GP Gran Bretaña",       "Circuito":"Silverstone",        "Formato":"⚡ SPRINT"},
    {"Fecha":"17-19 Jul","Gran Premio":"GP Bélgica",            "Circuito":"Spa",                "Formato":"Clásico"},
    {"Fecha":"24-26 Jul","Gran Premio":"GP Hungría",            "Circuito":"Budapest",           "Formato":"Clásico"},
    {"Fecha":"21-23 Ago","Gran Premio":"GP Países Bajos",       "Circuito":"Zandvoort",          "Formato":"⚡ SPRINT"},
    {"Fecha":"04-06 Sep","Gran Premio":"GP Italia",             "Circuito":"Monza",              "Formato":"Clásico"},
    {"Fecha":"11-13 Sep","Gran Premio":"GP Madrid",             "Circuito":"Madrid",             "Formato":"Clásico"},
    {"Fecha":"25-27 Sep","Gran Premio":"GP Azerbaiyán",         "Circuito":"Bakú",               "Formato":"Clásico"},
    {"Fecha":"09-11 Oct","Gran Premio":"GP Singapur",           "Circuito":"Marina Bay",         "Formato":"⚡ SPRINT"},
    {"Fecha":"23-25 Oct","Gran Premio":"GP Estados Unidos",     "Circuito":"Austin",             "Formato":"Clásico"},
    {"Fecha":"30-01 Nov","Gran Premio":"GP México",             "Circuito":"Hermanos Rodríguez", "Formato":"Clásico"},
    {"Fecha":"06-08 Nov","Gran Premio":"GP Brasil",             "Circuito":"Interlagos",         "Formato":"Clásico"},
    {"Fecha":"19-21 Nov","Gran Premio":"GP Las Vegas",          "Circuito":"Las Vegas",          "Formato":"Clásico"},
    {"Fecha":"27-29 Nov","Gran Premio":"GP Qatar",              "Circuito":"Lusail",             "Formato":"Clásico"},
    {"Fecha":"04-06 Dic","Gran Premio":"GP Abu Dabi",           "Circuito":"Yas Marina",         "Formato":"Clásico"},
]

# ─────────────────────────────────────────────────────────
# 5. AUTH TOKENS
# ─────────────────────────────────────────────────────────
def _auth_secret():
    try:
        from streamlit.errors import StreamlitSecretNotFoundError
        s = st.secrets.get("AUTH_SECRET", None)
    except Exception: s = None
    return s or os.getenv("AUTH_SECRET","DEV_SECRET_FW_2026_CAMBIAR")

def _b64u(b): return base64.urlsafe_b64encode(b).decode().rstrip("=")
def _b64ud(s):
    pad = "="*(-len(s)%4)
    return base64.urlsafe_b64decode((s+pad).encode())

def auth_create_token(usuario, hours=168):
    exp = int((datetime.utcnow()+timedelta(hours=hours)).timestamp())
    payload = f"{usuario}|{exp}|{secrets.token_urlsafe(8)}".encode()
    sig = hmac.new(_auth_secret().encode(), payload, hashlib.sha256).digest()
    return f"{_b64u(payload)}.{_b64u(sig)}"

def auth_user_from_token(token):
    try:
        if not token or "." not in token: return None
        p64,s64 = token.split(".",1)
        payload = _b64ud(p64); sig = _b64ud(s64)
        good = hmac.new(_auth_secret().encode(), payload, hashlib.sha256).digest()
        if not hmac.compare_digest(sig,good): return None
        usuario,exp_str,_ = payload.decode().split("|",2)
        if int(exp_str) < int(datetime.utcnow().timestamp()): return None
        return usuario
    except: return None

# ─────────────────────────────────────────────────────────
# 6. PERFIL CACHEADO
# ─────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _get_perfil(usuario: str):
    m = _mod_auth()
    if "_error" in m or "get_user_row" not in m: return None
    def _do():
        result, _ = m["get_user_row"](usuario)
        if not result: return None
        data = result[1] if (isinstance(result,tuple) and len(result)==2) else result
        if isinstance(data,dict):
            return {"usuario":str(data.get("usuario",usuario)),
                    "rol":str(data.get("rol","")),
                    "copas":int(data.get("copas",0) or 0),
                    "color":str(data.get("color","gray")),
                    "forzar_cambio":int(data.get("forzar_cambio",0) or 0),
                    "foto_url":str(data.get("foto_url","") or "")}
        if isinstance(data,(list,tuple)) and len(data)>0:
            return {"usuario":data[0],
                    "rol":data[1] if len(data)>1 else "",
                    "copas":int(data[2]) if len(data)>2 else 0,
                    "color":data[3] if len(data)>3 else "white",
                    "forzar_cambio":int(data[4]) if len(data)>4 else 0,
                    "foto_url":""}
        return None
    return _safe_call(_do, timeout_sec=30, default=None)

# ─────────────────────────────────────────────────────────
# 7. HELPERS UI
# ─────────────────────────────────────────────────────────
def qp_get(k): v=st.query_params.get(k,None); return (v[0] if isinstance(v,list) else v)
def qp_set(k,v): qp=dict(st.query_params); qp[k]=v; st.query_params.update(qp)

def is_logged_in(): return st.session_state.get("perfil") is not None
def is_admin():
    rol = str((st.session_state.get("perfil") or {}).get("rol","")).lower()
    return "admin" in rol or "comisario" in rol

def logout():
    try: st.query_params.clear()
    except: pass
    for k in ("perfil","usuario","_tok_done"): st.session_state[k] = None if k!="_tok_done" else False
    try: _get_perfil.clear()
    except: pass
    components.html('<script>localStorage.removeItem("fw_token");</script>',height=0)

def _driver_avatar_html(nombre, color="#a855f7", size=48):
    url = DRIVER_PHOTOS.get(nombre,"")
    ini = "".join(w[0] for w in nombre.split()[:2]).upper()
    if url:
        return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;overflow:hidden;'
                f'border:2px solid {color};flex-shrink:0;">'
                f'<img src="{url}" width="{size}" height="{size}" style="object-fit:cover;" '
                f'onerror="this.style.display=\'none\'"/></div>')
    return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;'
            f'background:{color}33;border:2px solid {color};display:flex;align-items:center;'
            f'justify-content:center;font-weight:900;color:{color};font-size:{size//3}px;'
            f'flex-shrink:0;">{ini}</div>')

def render_dark_table(df, prev_ranking=None):
    """Renders the standings table with colors, arrows, and highlights."""
    if df is None or (hasattr(df,"empty") and df.empty): return
    df2 = df.copy()
    if {"Piloto","Puntos"}.issubset(df2.columns):
        df2 = df2.sort_values("Puntos",ascending=False).reset_index(drop=True)

    # Find leaders per category
    max_pts = int(df2["Puntos"].max()) if "Puntos" in df2.columns else 0
    max_q   = int(df2["Qualys"].max())  if "Qualys"   in df2.columns else 0
    max_s   = int(df2["Sprints"].max()) if "Sprints"  in df2.columns else 0
    max_r   = int(df2["Carreras"].max())if "Carreras" in df2.columns else 0

    rows_html = ""
    for i, row in df2.iterrows():
        pil  = str(row.get("Piloto",""))
        pts  = int(row.get("Puntos",0))
        q    = int(row.get("Qualys",0))  if "Qualys"   in df2.columns else 0
        sp   = int(row.get("Sprints",0)) if "Sprints"  in df2.columns else 0
        ca   = int(row.get("Carreras",0))if "Carreras" in df2.columns else 0
        clr  = PILOTO_COLORS.get(pil,"#a855f7")
        medals = {0:"🥇",1:"🥈",2:"🥉"}
        pos_ico = medals.get(i, f"<b style='color:rgba(169,178,214,.5);'>{i+1}</b>")

        # Position change arrow
        if prev_ranking and pil in prev_ranking:
            prev = prev_ranking[pil]
            if i < prev:   arrow = f'<span style="color:#4ade80;font-size:11px;">▲</span>'
            elif i > prev: arrow = f'<span style="color:#ef4444;font-size:11px;">▼</span>'
            else:           arrow = f'<span style="color:rgba(169,178,214,.3);font-size:11px;">—</span>'
        else: arrow = ""

        is_leader = (i == 0)
        row_bg = f"background:linear-gradient(90deg,{clr}18,{clr}08,transparent)" if is_leader else ("rgba(255,255,255,.025)" if i%2==0 else "transparent")
        row_border = f"border-left:3px solid {clr};" if is_leader else f"border-left:3px solid {clr}55;"

        # Category badges
        q_badge  = f' <span style="background:#D4AF3788;color:#1a1000;border-radius:6px;padding:0 4px;font-size:8px;font-weight:900;">👑Q</span>' if q == max_q and max_q > 0 else ""
        s_badge  = f' <span style="background:#a855f788;color:#fff;border-radius:6px;padding:0 4px;font-size:8px;font-weight:900;">⚡S</span>' if sp == max_s and max_s > 0 else ""
        r_badge  = f' <span style="background:#4ade8088;color:#051a05;border-radius:6px;padding:0 4px;font-size:8px;font-weight:900;">🏁R</span>' if ca == max_r and max_r > 0 else ""

        pts_style = f"color:#ffdd7a;font-weight:900;font-size:{'16' if is_leader else '14'}px;"
        rows_html += (
            f'<tr style="{row_bg};{row_border}">'
            f'<td style="text-align:center;width:36px;">{pos_ico}</td>'
            f'<td style="padding-left:4px;">{arrow}</td>'
            f'<td><span style="color:{clr};font-weight:800;">{pil}</span>{q_badge}{s_badge}{r_badge}</td>'
            f'<td style="text-align:center;{pts_style}">{pts}</td>'
        )
        if "Qualys"   in df2.columns: rows_html += f'<td style="text-align:center;color:{"#D4AF37" if q==max_q and max_q>0 else "rgba(169,178,214,.6)"};font-weight:{"900" if q==max_q and max_q>0 else "400"};">{q}</td>'
        if "Sprints"  in df2.columns: rows_html += f'<td style="text-align:center;color:{"#a855f7" if sp==max_s and max_s>0 else "rgba(169,178,214,.6)"};font-weight:{"900" if sp==max_s and max_s>0 else "400"};">{sp}</td>'
        if "Carreras" in df2.columns: rows_html += f'<td style="text-align:center;color:{"#4ade80" if ca==max_r and max_r>0 else "rgba(169,178,214,.6)"};font-weight:{"900" if ca==max_r and max_r>0 else "400"};">{ca}</td>'
        rows_html += "</tr>"

    # Headers
    headers = ["#","","Formulero","Pts"]
    if "Qualys"   in df2.columns: headers.append("Qualys")
    if "Sprints"  in df2.columns: headers.append("Sprints")
    if "Carreras" in df2.columns: headers.append("Carreras")
    head_html = "".join(f'<th style="font-size:9px;letter-spacing:.1em;color:rgba(212,175,55,.7);text-transform:uppercase;padding:8px 6px;">{h}</th>' for h in headers)

    st.markdown(
        f'<div class="fw-table-wrap">'
        f'<table class="fw-table" style="width:100%;border-collapse:collapse;">'
        f'<thead><tr style="border-bottom:1px solid rgba(212,175,55,.2);">{head_html}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></div>',
        unsafe_allow_html=True
    )
    # Legend
    st.markdown(
        '<div style="font-size:9px;color:rgba(169,178,214,.4);margin-top:4px;">'
        '👑Q = más qualys ganadas &nbsp;·&nbsp; ⚡S = más sprints ganados &nbsp;·&nbsp; 🏁R = más carreras ganadas'
        '</div>', unsafe_allow_html=True
    )

def normalizar_keys_num(d):
    if not isinstance(d,dict): return {}
    return {int(k) if (isinstance(k,str) and k.isdigit()) else k:v for k,v in d.items()}

def calcular_constructores_auto(of_r, grilla, escala, top_n=3):
    m = _mod_core()
    nn = m.get("normalizar_nombre", lambda x:x.lower().strip()) if "_error" not in m else lambda x:x.lower().strip()
    d2t = {nn(d):t for t,ds in grilla.items() for d in ds}
    tp = defaultdict(int)
    for pos,pts in escala.items():
        p = nn(of_r.get(pos,""))
        if p and p in d2t: tp[d2t[p]] += int(pts)
    ranking = sorted(tp.items(),key=lambda x:(-x[1],x[0]))
    return [t for t,_ in ranking[:top_n]], dict(tp)

def _mc_safe(s):
    m = _mod_mesa()
    if "_error" not in m and "_mc_safe_text" in m:
        try: return m["_mc_safe_text"](s)
        except: pass
    return _html.escape(s or "").replace("\n","<br>")

def _mc_badge(u):
    m = _mod_mesa()
    if "_error" not in m and "mc_badge_for" in m:
        try: return m["mc_badge_for"](u)
        except: pass
    b = MESA_CHICA_BADGES.get(u,{"tipo":"formulero","label":"FORMULERO","stars":""})
    return b["tipo"],b["label"],b["stars"]

def _mc_is_mod(u):
    m = _mod_mesa()
    if "_error" not in m and "mc_is_mod" in m:
        try: return m["mc_is_mod"](u)
        except: pass
    return u in MESA_CHICA_MODS

# ─────────────────────────────────────────────────────────
# 7b. NUEVOS HELPERS VISUALES PARA PREDICCIONES (estilo VueltaRápida)
# ─────────────────────────────────────────────────────────
def _make_lineup_preview(kp, count):
    """Genera HTML con cards estilo VueltaRápida leyendo session_state."""
    POS_COL = {1:"#FFD700", 2:"#C0C0C0", 3:"#CD7F32"}
    rows = []
    for i in range(1, count + 1):
        nombre = st.session_state.get(f"{kp}_{i}", "")
        pc = POS_COL.get(i, "#6366f1")

        if not nombre:
            rows.append(
                f'<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;'
                f'background:rgba(255,255,255,.015);border:1px dashed rgba(255,255,255,.09);'
                f'border-radius:10px;min-height:56px;">'
                f'<span style="color:{pc};font-weight:900;font-size:15px;min-width:24px;'
                f'text-align:center;">{i}</span>'
                f'<div style="width:42px;height:42px;border-radius:50%;background:rgba(255,255,255,.04);'
                f'border:1.5px dashed rgba(255,255,255,.15);flex-shrink:0;"></div>'
                f'<span style="color:rgba(169,178,214,.35);font-size:11px;font-style:italic;">'
                f'Sin seleccionar</span></div>'
            )
        else:
            eq   = next((t for t, ds in GRILLA_2026.items() if nombre in ds), "")
            tc   = TEAM_COLORS.get(eq, "#a855f7")
            # ← Headshot (cara) para predicciones, fallback a full-body
            ph   = DRIVER_HEADSHOTS.get(nombre, DRIVER_PHOTOS.get(nombre, ""))
            ini  = "".join(w[0] for w in nombre.split()[:2]).upper()
            last  = nombre.split()[-1].upper()
            first = " ".join(nombre.split()[:-1])
            sz = "18px" if i <= 3 else "15px"

            img_html = (
                f'<img src="{ph}" '
                f'style="width:100%;height:100%;object-fit:cover;object-position:top 5%;display:block;" '
                f'onerror="this.style.display=\'none\';this.nextSibling.style.display=\'flex\'">'
            ) if ph else ""
            fallback_html = (
                f'<div style="display:{"none" if ph else "flex"};width:100%;height:100%;'
                f'align-items:center;justify-content:center;font-weight:900;font-size:11px;color:{tc};">'
                f'{ini}</div>'
            )
            rows.append(
                f'<div style="display:flex;align-items:center;gap:10px;padding:7px 12px;'
                f'background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);'
                f'border-left:3px solid {tc};border-radius:10px;min-height:56px;">'
                f'<span style="color:{pc};font-weight:900;font-size:{sz};min-width:24px;text-align:center;">{i}</span>'
                f'<div style="width:42px;height:42px;border-radius:50%;overflow:hidden;'
                f'border:2px solid {tc};flex-shrink:0;background:#080b1a;">'
                f'{img_html}{fallback_html}</div>'
                f'<div style="flex:1;min-width:0;overflow:hidden;">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:.1em;color:{tc};'
                f'text-transform:uppercase;opacity:.85;white-space:nowrap;overflow:hidden;">{eq}</div>'
                f'<div style="font-size:11px;font-weight:400;color:rgba(169,178,214,.65);'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{first}</div>'
                f'<div style="font-size:13px;font-weight:900;color:#e8ecff;letter-spacing:.02em;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{last}</div>'
                f'</div></div>'
            )
    return '<div style="display:flex;flex-direction:column;gap:4px;">' + "".join(rows) + '</div>'


def _make_teams_preview(kp, count):
    """Genera HTML con cards de constructores leyendo session_state."""
    MEDALS = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows = []
    for i in range(1, count + 1):
        team = st.session_state.get(f"{kp}_{i}", "")
        if not team:
            rows.append(
                f'<div style="display:flex;align-items:center;gap:10px;padding:11px 13px;'
                f'background:rgba(255,255,255,.015);border:1px dashed rgba(255,255,255,.09);'
                f'border-radius:9px;min-height:54px;">'
                f'<span style="font-size:22px;">{MEDALS.get(i, str(i)+"°")}</span>'
                f'<span style="color:rgba(169,178,214,.35);font-size:11px;font-style:italic;">'
                f'Sin seleccionar</span></div>'
            )
        else:
            color = TEAM_COLORS.get(team, "#a855f7")
            abbr  = TEAM_LOGOS_SVG.get(team, team[:3])
            car   = TEAM_CARS_MODULE.get(team, "")
            car_html = (
                f'<img src="{car}" style="height:28px;max-width:76px;object-fit:contain;" '
                f'onerror="this.style.display=\'none\'">'
            ) if car else f'<span style="font-size:11px;font-weight:900;color:{color};">{abbr}</span>'
            rows.append(
                f'<div style="display:flex;align-items:center;gap:10px;padding:9px 13px;'
                f'background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);'
                f'border-left:3px solid {color};border-radius:9px;min-height:54px;">'
                f'<span style="font-size:22px;">{MEDALS.get(i, str(i)+"°")}</span>'
                f'<div style="background:rgba(255,255,255,.04);border-radius:6px;padding:3px 7px;'
                f'border:1px solid {color}33;display:flex;align-items:center;justify-content:center;'
                f'min-width:64px;height:34px;flex-shrink:0;">{car_html}</div>'
                f'<div style="flex:1;min-width:0;">'
                f'<div style="font-size:13px;font-weight:800;color:#e8ecff;">{team}</div>'
                f'<div style="font-size:9px;color:{color};font-weight:700;letter-spacing:.08em;'
                f'text-transform:uppercase;opacity:.8;">{abbr}</div>'
                f'</div></div>'
            )
    return '<div style="display:flex;flex-direction:column;gap:5px;">' + "".join(rows) + '</div>'


def _pred_section_label(text):
    return (f'<div style="font-size:10px;font-weight:700;letter-spacing:.13em;'
            f'color:rgba(246,195,73,.65);text-transform:uppercase;margin-bottom:6px;'
            f'margin-top:4px;">{text}</div>')


# ─────────────────────────────────────────────────────────
# 8. FLECHA DORADA MEJORADA
# ─────────────────────────────────────────────────────────
def flecha_arriba():
    components.html("""
    <script>
    (function() {
        try {
            var p = window.parent || window;
            var d = p.document;
            if (!d.getElementById('fw-top-style')) {
                var s = d.createElement('style');
                s.id = 'fw-top-style';
                s.textContent = [
                    '#fw-top-btn{position:fixed!important;right:22px;bottom:30px;',
                    'width:54px;height:54px;border-radius:50%;',
                    'background:linear-gradient(145deg,#ffe896 0%,#d4af37 55%,#9a7a10 100%);',
                    'border:2px solid rgba(255,238,150,.75);',
                    'box-shadow:0 0 0 5px rgba(212,175,55,.12),0 8px 32px rgba(0,0,0,.65);',
                    'display:flex!important;align-items:center;justify-content:center;',
                    'cursor:pointer;z-index:2147483647!important;',
                    'font-size:28px;font-weight:900;color:#1a1000;line-height:1;',
                    'outline:none;border-style:solid;',
                    'transition:transform .2s cubic-bezier(.34,1.56,.64,1);}',
                    '#fw-top-btn:hover{transform:translateY(-4px) scale(1.08);}',
                    '#fw-top-btn:active{transform:scale(.92);}'
                ].join('');
                try { d.head.appendChild(s); } catch(e){}
            }
            var old = d.getElementById('fw-top-btn');
            if (old && old.parentNode) { try { old.parentNode.removeChild(old); } catch(e){} }
            var btn = d.createElement('button');
            btn.id = 'fw-top-btn';
            btn.title = 'Volver al inicio';
            btn.innerHTML = '&#8679;';
            btn.addEventListener('click', function() {
                [
                    d.querySelector('[data-testid="stMain"]'),
                    d.querySelector('[data-testid="stAppViewContainer"]'),
                    d.querySelector('.main > div'),
                    d.querySelector('section.main'),
                    d.querySelector('.block-container'),
                    d.documentElement,
                    d.body
                ].forEach(function(el) {
                    if (el) { try { el.scrollTop = 0; } catch(e){} }
                });
                try { p.scrollTo(0, 0); } catch(e){}
            });
            try { d.body.appendChild(btn); } catch(e){}
        } catch(e) { console.warn('fw-top:', e); }
    })();
    </script>
    """, height=0)


# ─────────────────────────────────────────────────────────
# 8b. MINI BARRA — botón flotante para ocultar/mostrar el menú
# ─────────────────────────────────────────────────────────
def mini_bar():
    components.html("""
    <script>
    (function() {
        try {
            var p = window.parent || window;
            var d = p.document;
            var KEY = 'fw_sb_v4';

            // ── Kill native sidebar toggle forever ──
            if (!d.getElementById('fw-kill-sb-arrow')) {
                var ka=d.createElement('style');ka.id='fw-kill-sb-arrow';
                ka.textContent='[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebarCollapseButton"],[data-testid="stSidebarHeader"] button,button[data-testid="collapsedControl"],[data-testid="baseButton-headerNoPadding"],button[aria-label="Collapse sidebar"],button[aria-label="Expand sidebar"],button[aria-label="Close sidebar"],button[aria-label="Open sidebar"],.st-emotion-cache-1cyp2mc,.st-emotion-cache-czk5ss,.st-emotion-cache-vk3wp9{display:none!important;}';
                d.head.appendChild(ka);
            }
            // ── Inject style once ──
            if (!d.getElementById('fw-mb-style')) {
                var s = d.createElement('style');
                s.id = 'fw-mb-style';
                s.textContent = [
                    '#fw-mb-wrap{position:fixed!important;left:0;top:50%;',
                    'transform:translateY(-50%);z-index:2147483646!important;}',
                    '#fw-mb-btn{background:rgba(7,9,20,.96);',
                    'border:1.5px solid rgba(246,195,73,.6);border-left:none;',
                    'border-radius:0 14px 14px 0;padding:16px 10px 16px 6px;',
                    'cursor:pointer;color:#f6c349;display:flex;flex-direction:column;',
                    'align-items:center;gap:5px;min-width:36px;',
                    'box-shadow:5px 0 24px rgba(0,0,0,.6);',
                    'transition:all .2s ease;outline:none;}',
                    '#fw-mb-btn:hover{background:rgba(246,195,73,.15);',
                    'border-color:rgba(246,195,73,.95);}',
                    '#fw-mb-icon{font-size:18px;line-height:1;}',
                    '#fw-mb-lbl{font-size:7px;letter-spacing:.14em;font-weight:900;',
                    'writing-mode:vertical-rl;opacity:.75;text-transform:uppercase;}'
                ].join('');
                d.head.appendChild(s);
            }

            // ── Inject sidebar dynamic style ──
            var dynStyle = d.getElementById('fw-sb-dyn');
            if (!dynStyle) {
                dynStyle = d.createElement('style');
                dynStyle.id = 'fw-sb-dyn';
                d.head.appendChild(dynStyle);
            }

            // ── Create/recreate button ──
            var wrap = d.getElementById('fw-mb-wrap');
            if (!wrap) {
                wrap = d.createElement('div');
                wrap.id = 'fw-mb-wrap';
                wrap.innerHTML =
                    '<button id="fw-mb-btn">' +
                    '<span id="fw-mb-icon">&#9776;</span>' +
                    '<span id="fw-mb-lbl">MEN&Uacute;</span>' +
                    '</button>';
                d.body.appendChild(wrap);
            }

            var hidden = (p.localStorage.getItem(KEY) === '1');

            function applyState() {
                var icon = d.getElementById('fw-mb-icon');
                var lbl  = d.getElementById('fw-mb-lbl');
                if (hidden) {
                    dynStyle.textContent =
                        'section[data-testid="stSidebar"]{' +
                        'transform:translateX(-120%)!important;' +
                        'transition:transform .35s ease!important;}' +
                        '[data-testid="stSidebarCollapsedControl"]{display:none!important;}' +
                        '.block-container{margin-left:0!important;' +
                        'max-width:100%!important;padding-left:1rem!important;}';
                    if (icon) icon.innerHTML = '&#9776;';
                    if (lbl)  lbl.textContent = 'MEN\u00DA';
                } else {
                    dynStyle.textContent =
                        'section[data-testid="stSidebar"]{' +
                        'transform:translateX(0)!important;' +
                        'transition:transform .35s ease!important;}';
                    if (icon) icon.innerHTML = '&times;';
                    if (lbl)  lbl.textContent = 'CERRAR';
                }
            }

            // Always reattach click handler (button may have been recreated)
            var btn = d.getElementById('fw-mb-btn');
            btn.onclick = function() {
                hidden = !hidden;
                p.localStorage.setItem(KEY, hidden ? '1' : '0');
                applyState();
            };

            applyState();
        } catch(e) { console.warn('fw-mb:', e); }
    })();
    </script>
    """, height=0)


# ─────────────────────────────────────────────────────────
# 9. LOGIN + SIDEBAR
# ─────────────────────────────────────────────────────────
def sidebar_login_block():
    for k,d in [("perfil",None),("usuario",None),("_tok_done",False),("fw_force_nav",None)]:
        if k not in st.session_state: st.session_state[k] = d

    token = qp_get("t")
    if not is_logged_in() and token and not st.session_state["_tok_done"]:
        st.session_state["_tok_done"] = True
        u = auth_user_from_token(token)
        if u:
            with st.spinner("Restaurando sesión..."):
                perfil = _get_perfil(u)
            if perfil:
                st.session_state["perfil"] = perfil
                st.session_state["usuario"] = perfil["usuario"]
                st.rerun()
            else:
                try: st.query_params.clear()
                except: pass

    if is_logged_in() and not qp_get("t"):
        u2 = (st.session_state.get("perfil") or {}).get("usuario","")
        if u2: qp_set("t", auth_create_token(u2))

    if not is_logged_in():
        st.markdown("""
    <style>
    .tabla_historial_dark {
        width: 100%;
        max-width: 900px;
        margin: 10px auto 12px auto;
        border-collapse: collapse;
        background: rgba(7, 10, 25, 0.96);
        color: #e8ecff;
        border: 1px solid rgba(212, 175, 55, 0.25);
        border-radius: 14px;
        overflow: hidden;
        font-size: 14px;
        display: block;
        overflow-x: auto;
    }
    .tabla_historial_dark th {
        background: linear-gradient(90deg, rgba(212,175,55,0.18), rgba(255,255,255,0.03));
        color: #ffdd7a;
        text-align: left;
        padding: 12px 14px;
        border-bottom: 1px solid rgba(212,175,55,0.22);
        font-weight: 800;
    }
    .tabla_historial_dark td {
        padding: 11px 14px;
        color: #e8ecff;
        border-bottom: 1px solid rgba(255,255,255,0.06);
        background: rgba(255,255,255,0.02);
    }
    .tabla_historial_dark tr:hover td { background: rgba(255,221,122,0.05); }
    .hist_car_track {
        position: relative; width: 100%; height: 30px; margin: 4px 0 12px 0;
        overflow: hidden; border-radius: 999px;
        background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(212,175,55,0.08), rgba(255,255,255,0.02));
        border: 1px solid rgba(212,175,55,0.18);
    }
    .hist_car { position: absolute; left: -60px; top: 3px; font-size: 21px; animation: histCarMove 6s linear infinite; }
    @keyframes histCarMove { 0% { left: -60px; } 100% { left: calc(100% + 60px); } }
    .flecha_subir_dorada {
        position: fixed; right: 24px; bottom: 22px; width: 46px; height: 46px;
        border-radius: 50%; display: flex; align-items: center; justify-content: center;
        text-decoration: none; font-size: 22px; font-weight: 900; color: #1a1200;
        background: linear-gradient(180deg, #ffe38a 0%, #d4af37 100%);
        border: 1px solid rgba(255,240,180,0.65); box-shadow: 0 0 18px rgba(212,175,55,0.40); z-index: 9999;
    }
    .flecha_subir_dorada:hover { transform: scale(1.06); box-shadow: 0 0 24px rgba(212,175,55,0.58); }
    section[data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"] { display: none !important; }
    /* LOGIN button — styled by config.toml primaryColor (#D4AF37 golden) */
    
    </style>
    """, unsafe_allow_html=True)

        # ── Inject fullscreen background for login page ─────────────
        try:
            import base64 as _b64_login
            _bg_candidates = ["FORMULEROS.jpg","IMAGENFEFE.jfif","ui/FORMULEROS.jpg","IMAGENCUPULA.jfif"]
            _bg_data = ""
            for _bgf in _bg_candidates:
                if os.path.exists(_bgf):
                    with open(_bgf,"rb") as _bgfile:
                        _ext = "jpeg"
                        _bg_data = f"data:image/jpeg;base64,"+_b64_login.b64encode(_bgfile.read()).decode()
                    break
            if _bg_data:
                st.markdown(f"""<style>
                [data-testid="stAppViewContainer"] > section {{
                    background-image: linear-gradient(rgba(4,8,24,.88), rgba(4,8,24,.94)), url('{_bg_data}') !important;
                    background-size: cover !important;
                    background-position: center top !important;
                    background-attachment: fixed !important;
                }}
                [data-testid="stMain"] {{ position: relative; z-index: 1; }}
                [data-testid="stMainBlockContainer"] {{ padding-top: 1.5rem !important; }}
                </style>""", unsafe_allow_html=True)
        except Exception: pass

        # Login banner — FORMULEROS.jpg (auto F1) como banner compacto
        try:
            import os as _os_li, base64 as _b64_li
            _banner_candidates = ["FORMULEROS.jpg","IMAGENFEFE.jfif","ui/FORMULEROS.jpg"]
            _banner_loaded = False
            for _bc in _banner_candidates:
                if _os_li.path.exists(_bc):
                    with open(_bc,"rb") as _fli:
                        _ext = _bc.split(".")[-1].lower()
                        _mime = "image/jpeg" if _ext in ("jpg","jfif","jpeg") else "image/png"
                        _b64_li_data = _b64_li.b64encode(_fli.read()).decode()
                    st.markdown(
                        f'<div style="max-width:440px;margin:0 auto;border-radius:18px;overflow:hidden;'
                        f'box-shadow:0 8px 30px rgba(0,0,0,.55);border:1px solid rgba(59,130,246,.3);'
                        f'background:#070b1a;">' +
                        f'<img src="data:{_mime};base64,{_b64_li_data}" ' +
                        f'style="width:100%;height:auto;display:block;">' +
                        f'</div>',
                        unsafe_allow_html=True)
                    _banner_loaded = True
                    break
            if not _banner_loaded:
                st.markdown(
                    '<div style="text-align:center;font-size:52px;padding:16px 0;">🏆</div>',
                    unsafe_allow_html=True)
        except Exception:
            st.markdown(
                '<div style="text-align:center;font-size:52px;padding:16px 0;">🏆</div>',
                unsafe_allow_html=True)

        # Professional centered login card
        _,c2,_ = st.columns([0.55,1.9,0.55])
        with c2:
            st.markdown("""
            <style>
            /* ── Professional Login Card ── */
            .login-card-wrap {
                background: linear-gradient(145deg,rgba(6,12,35,.97),rgba(10,18,50,.99));
                border: 1px solid rgba(59,130,246,.25);
                border-radius: 16px;
                padding: 20px 22px 14px;
                box-shadow: 0 12px 40px rgba(0,0,0,.5);
                position: relative;
                overflow: hidden;
                margin-top: 10px;
            }
            .login-badge {
                display: inline-block;
                background: rgba(59,130,246,.1);
                border: 1px solid rgba(59,130,246,.25);
                border-radius: 20px;
                padding: 3px 10px;
                font-size: 9px;
                color: rgba(147,197,253,.7);
                margin: 2px;
                letter-spacing: .06em;
            }
            .stTextInput > div > div > input {
                background: rgba(6,15,40,.8) !important;
                border: 1px solid rgba(59,130,246,.35) !important;
                color: #e8ecff !important;
                border-radius: 8px !important;
                padding: 8px 12px !important;
                font-size: 13px !important;
            }
            .stTextInput > div > div > input:focus {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 2px rgba(59,130,246,.2) !important;
            }
            </style>
            <div class="login-card-wrap">
              <div style="text-align:center;margin-bottom:14px;">
                <div style="font-size:30px;margin-bottom:4px;">🏎️</div>
                <div style="font-size:21px;font-weight:900;letter-spacing:.08em;
                  background:linear-gradient(90deg,#3b82f6,#93c5fd,#D4AF37,#93c5fd,#3b82f6);
                  background-size:300% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  background-clip:text;margin-bottom:3px;">TORNEO FEFE WOLF</div>
                <div style="font-size:10px;color:rgba(169,178,214,.5);letter-spacing:.12em;
                  text-transform:uppercase;margin-bottom:12px;">Temporada 2026 · Formuleros de élite</div>
                <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:4px;">
                  <span class="login-badge">🏁 24 GPs</span>
                  <span class="login-badge">⚡ 6 Sprints</span>
                  <span class="login-badge">🇦🇷 Colapinto</span>
                  <span class="login-badge">🏆 5 Formuleros</span>
                </div>
              </div>
              <div style="font-size:10px;font-weight:700;color:rgba(59,130,246,.7);
                letter-spacing:.1em;text-transform:uppercase;text-align:center;">
                🔐 Acceso exclusivo
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Inject CSS override for primary button (Streamlit primaryColor override)
            st.markdown("""
            <style>
            /* Override Streamlit primaryColor inline style on buttons */
            button[data-testid="baseButton-primary"],
            button[data-testid="baseButton-secondary"],
            .stButton>button {
                background: linear-gradient(135deg,#060f28,#0c1e50) !important;
                background-color: #060f28 !important;
                border: 2px solid #3b82f6 !important;
                color: #D4AF37 !important;
                box-shadow: 0 0 18px rgba(59,130,246,.4) !important;
            }
            button[data-testid="baseButton-primary"] p,
            button[data-testid="baseButton-primary"] span,
            button[data-testid="baseButton-secondary"] p,
            .stButton>button p, .stButton>button span {
                color: #D4AF37 !important;
                font-weight: 900 !important;
            }
            </style>
            """, unsafe_allow_html=True)
            m = _mod_auth()
            if "_error" in m:
                st.error(f"⚠️ Error cargando módulo auth: {m['_error']}")
            else:
                u_in = st.text_input("👤 Formulero", key="li_u", placeholder="Tu nombre completo")
                p_in = st.text_input("🔑 Contraseña", type="password", key="li_p", placeholder="••••••••")

                if st.button("⚡  ENTRAR AL TORNEO", key="li_btn", use_container_width=True):
                    if not u_in or not p_in:
                        st.error("Completá usuario y contraseña.")
                    else:
                        with st.spinner("🔄 Verificando credenciales..."):
                            ok, res = _safe_call(
                                m["login"], u_in, p_in,
                                timeout_sec=60,
                                default=(False, "⏱️ El servidor tardó demasiado. Reintentá en unos segundos.")
                            )
                        if ok:
                            st.session_state["perfil"]  = res
                            st.session_state["usuario"] = res["usuario"]
                            qp_set("t", auth_create_token(res["usuario"]))
                            st.rerun()
                        else:
                            st.error(f"⛔ {res}")

                # Cambiar contraseña sabiendo la actual (sin mother code)
                with st.expander("🔑 Cambiar mi contraseña"):
                    st.caption("Necesitás saber tu contraseña actual. Si la olvidaste, pedile al Comisario que te la resetee.")
                    _cp_u  = st.text_input("Usuario", key="cplogin_u")
                    _cp_old = st.text_input("Contraseña actual", type="password", key="cplogin_old")
                    _cp_n1 = st.text_input("Nueva contraseña", type="password", key="cplogin_n1")
                    _cp_n2 = st.text_input("Repetir nueva contraseña", type="password", key="cplogin_n2")
                    if st.button("Guardar nueva contraseña", key="cplogin_btn"):
                        if not _cp_u.strip() or not _cp_old:
                            st.error("Completá usuario y contraseña actual.")
                        elif _cp_n1 != _cp_n2:
                            st.error("Las contraseñas nuevas no coinciden.")
                        elif len((_cp_n1 or "").strip()) < 4:
                            st.error("La nueva contraseña debe tener al menos 4 caracteres.")
                        else:
                            with st.spinner("Cambiando contraseña..."):
                                _okc, _msgc = _safe_call(m["change_password"], _cp_u.strip(), _cp_n1, _cp_old,
                                                         timeout_sec=30, default=(False,"Tiempo agotado."))
                            if _okc:
                                st.success("✅ Contraseña cambiada. Ya podés iniciar sesión con la nueva.")
                            else:
                                st.error(f"⛔ {_msgc}")

        st.stop()

    # ── LOGUEADO — SIDEBAR ───────────────────────────────
    perfil = st.session_state["perfil"] or {}
    usr   = perfil.get("usuario","")
    rol   = perfil.get("rol","Piloto")
    copas = int(perfil.get("copas",0) or 0)
    color = PILOTO_COLORS.get(usr,"#a855f7")
    trofeos = "🏆"*copas if copas else "—"

    # ── Build rich per-pilot profile tags ──────────────────
    _PILOT_PROFILE_TAGS = {
        "Checo Perez":    [("🏆 Comisario","rgba(212,175,55,.25)","#ffdd7a"),
                           ("👑 Administrador","rgba(212,175,55,.15)","#d4af37"),
                           ("🏎️ Piloto","rgba(255,255,255,.08)","#e8ecff")],
        "Fernando Alonso":[("🏎️ Piloto","rgba(255,68,68,.15)","#FF4444"),
                           ("🔵 FIPF","rgba(21,101,192,.25)","#90caf9")],
        "Lando Norris":   [("🥈 Sub Comisario","rgba(255,165,0,.2)","#FFA500"),
                           ("🏎️ Piloto","rgba(255,255,255,.08)","#e8ecff"),
                           ("🔵 FIPF","rgba(21,101,192,.25)","#90caf9")],
        "Valteri Bottas": [("🏎️ Piloto","rgba(0,207,255,.12)","#00CFFF"),
                           ("🔵 FIPF","rgba(21,101,192,.25)","#90caf9")],
        "Nicki Lauda":    [("🏎️ Piloto","rgba(30,144,255,.15)","#1E90FF"),
                           ("⚫ Formulero","rgba(255,255,255,.08)","#a9b2d6")],
    }
    # Lauda photo for sidebar
    _LAUDA_PHOTO_B64 = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSgd3Dq9OHc2zK46t1QQLXbN_49nouLYDYv1w&s"
    # ── Cargar foto desde perfil de Google Sheets al iniciar sesión ──
    if not st.session_state.get(f"custom_photo_{usr}",""):
        _foto_from_perfil = perfil.get("foto_url","")
        if _foto_from_perfil:
            st.session_state[f"custom_photo_{usr}"] = _foto_from_perfil
    _sidebar_photo = st.session_state.get(f"custom_photo_{usr}","") or (
        _LAUDA_PHOTO_B64 if usr == "Nicki Lauda" else (
        DRIVER_HEADSHOTS.get(usr, DRIVER_PHOTOS.get(usr,""))))

    # Get user's current pts for badge
    _sb_pts = 0
    _sb_rank = "—"
    try:
        _mdb_sb = _mod_db()
        if "_error" not in _mdb_sb:
            _df_sb = _safe_call(_mdb_sb["leer_tabla_posiciones"], PILOTOS_TORNEO, timeout_sec=6, default=None)
            if _df_sb is not None and not _df_sb.empty:
                _df_sb["Puntos"] = pd.to_numeric(_df_sb["Puntos"],errors="coerce").fillna(0)
                _sb_row = _df_sb[_df_sb["Piloto"]==usr]
                if not _sb_row.empty:
                    _sb_pts = int(_sb_row["Puntos"].iloc[0])
                    _sb_rank = int(_df_sb.sort_values("Puntos",ascending=False).reset_index(drop=True).index[_df_sb.sort_values("Puntos",ascending=False).reset_index(drop=True)["Piloto"]==usr].tolist()[0]) + 1
                else: _sb_rank = "—"
    except Exception: _sb_rank = "—"
    _tags  = _PILOT_PROFILE_TAGS.get(usr, [(rol,"rgba(255,255,255,.08)","#e8ecff")])
    _tags_html = "".join(
        f"<div style='display:block;padding:4px 10px;margin:3px auto;border-radius:10px;"
        f"background:{bg};color:{fc};font-size:11px;font-weight:800;"
        f"letter-spacing:.07em;text-align:center;'>{lbl}</div>"
        for lbl,bg,fc in _tags
    )
    _trophy_label = ""
    if copas > 0:
        _cups_anim = "".join(
            f"<span style='animation:trophy-bounce {2+k*0.3}s ease-in-out {k*0.2}s infinite;"
            f"display:inline-block;font-size:28px;filter:drop-shadow(0 0 8px {color}cc);'>🏆</span>"
            for k in range(copas)
        )
        _trophy_label = f"<div style='margin-top:6px;'>{_cups_anim}</div>"\
            f"<div style='font-size:13px;font-weight:900;color:{color};letter-spacing:.05em;"\
            f"margin-top:4px;'>{copas} Título{'s' if copas!=1 else ''}</div>"

    _campeon_badge = ""
    if usr == "Checo Perez":
        _campeon_badge = ('<div style="background:linear-gradient(90deg,#9a7a10,#d4af37,#ffe896,#d4af37,#9a7a10);'
                         'background-size:200% auto;color:#1a1000;border-radius:20px;padding:3px 12px;'
                         'font-size:9px;font-weight:900;letter-spacing:.1em;display:inline-block;'
                         'margin-top:4px;animation:goldShimmer2 3s linear infinite;">👑 VIGENTE CAMPEÓN</div>')

    st.sidebar.markdown(f"""
    <style>
    @keyframes profile-glow {{
      0%,100%{{ box-shadow:0 0 14px {color}44,0 0 0 2px {color}22; }}
      50%{{ box-shadow:0 0 32px {color}88,0 0 0 3px {color}55; }}
    }}
    @keyframes trophy-bounce {{
      0%,100%{{ transform:translateY(0) scale(1); }}
      50%{{ transform:translateY(-5px) scale(1.12); }}
    }}
    @keyframes menu-pulse {{
      0%,100%{{ box-shadow:5px 0 24px rgba(0,0,0,.6); }}
      50%{{ box-shadow:5px 0 28px rgba(246,195,73,.35),0 0 0 2px rgba(246,195,73,.15); }}
    }}
    #fw-mb-btn{{ animation:menu-pulse 3s ease-in-out infinite !important; }}
    </style>
    <div class="sidebar-profile-card" style="border-color:{color}66;
      animation:profile-glow 3s ease-in-out infinite;
      position:relative;overflow:hidden;padding:14px 12px 12px;text-align:center;">
      <div style="position:absolute;top:-20px;right:-20px;width:80px;height:80px;
        border-radius:50%;background:radial-gradient({color}22,transparent 70%);pointer-events:none;"></div>
      {f'<img src="{_sidebar_photo}" style="width:62px;height:62px;border-radius:50%;object-fit:cover;object-position:top;border:3px solid {color};margin-bottom:6px;box-shadow:0 0 16px {color}66;" />' if _sidebar_photo else f'<div style="width:62px;height:62px;border-radius:50%;background:{color}22;border:3px solid {color};display:inline-flex;align-items:center;justify-content:center;font-size:24px;font-weight:900;color:{color};margin-bottom:6px;">{"".join(w[0] for w in usr.split()[:2]).upper()}</div>'}
      <div style="font-size:14px;font-weight:900;color:{color};
        letter-spacing:.08em;margin-bottom:4px;">{usr}</div>
      <div style="text-align:center;margin-bottom:4px;">{_tags_html}</div>
      <div style="display:flex;justify-content:center;gap:8px;margin:6px 0;">
        <div style="background:{color}18;border:1px solid {color}44;border-radius:10px;padding:4px 10px;">
          <div style="font-size:16px;font-weight:900;color:#ffdd7a;">{_sb_pts}</div>
          <div style="font-size:8px;color:rgba(169,178,214,.5);text-transform:uppercase;letter-spacing:.08em;">pts</div>
        </div>
        <div style="background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.2);border-radius:10px;padding:4px 10px;">
          <div style="font-size:16px;font-weight:900;color:#D4AF37;">P{_sb_rank}</div>
          <div style="font-size:8px;color:rgba(169,178,214,.5);text-transform:uppercase;letter-spacing:.08em;">posición</div>
        </div>
      </div>
      {_trophy_label}
      {_campeon_badge}
    </div>""", unsafe_allow_html=True)

    # ── Botón directo a Mi Perfil ──────────────────────────────
    if st.sidebar.button("👤 Mi Perfil", key="sidebar_mi_perfil_btn", use_container_width=True):
        st.session_state["fw_force_nav"] = "👤  Mi Perfil"
        st.session_state["_main_nav"] = "👤  Mi Perfil"
        st.rerun()

    m = _mod_auth()
    if "_error" not in m and "change_password" in m:
        with st.sidebar.expander("🔐 Cambiar contraseña"):
            op=st.text_input("Contraseña actual",type="password",key="cpw_old")
            n1=st.text_input("Nueva contraseña",type="password",key="cpw_n1")
            n2=st.text_input("Repetir nueva",type="password",key="cpw_n2")
            if st.button("Guardar cambio",key="cpw_btn"):
                if n1!=n2: st.sidebar.error("No coinciden.")
                elif len((n1 or "").strip())<4: st.sidebar.error("Mínimo 4 caracteres.")
                else:
                    ok,msg = _safe_call(m["change_password"],usr,n1,op,timeout_sec=10,default=(False,"Timeout"))
                    st.sidebar.success("✅ Actualizada.") if ok else st.sidebar.error(msg)

    st.sidebar.markdown('<div class="sidebar-logout-wrap">', unsafe_allow_html=True)
    if st.sidebar.button("🚪 Cerrar sesión", use_container_width=True, key="btn_logout"):
        logout(); st.rerun()
    st.sidebar.markdown("</div>", unsafe_allow_html=True)

    if os.getenv("FW_SETUP","0")=="1":
        with st.sidebar.expander("🛠️ Bootstrap Admin"):
            bpw=st.text_input("Password",type="password",key="boot_pw")
            bmc=st.text_input("Mother code",type="password",key="boot_mc")
            if st.button("Crear Admin Checo",key="boot_btn") and "_error" not in m:
                found,_=_safe_call(m["get_user_row"],"Checo Perez",timeout_sec=6,default=(False,None))
                if found: st.warning("Ya existe.")
                else:
                    ok,msg=_safe_call(m["bootstrap_user"],"Checo Perez","Comisario | Administrador",bpw,bmc,copas=3,color="gold",timeout_sec=10,default=(False,"Timeout"))
                    st.success(msg) if ok else st.error(msg)

def _notif_ya_enviada(clave):
    """Chequea en la hoja Sessions si una notif ya se envió (evita duplicados entre sesiones)."""
    try:
        from core.database import conectar_google_sheets as _cgs_n
        _ws = _cgs_n("Sessions")
        if not _ws: return False
        _vals = _ws.get_all_values()
        for _r in _vals:
            if _r and len(_r) >= 1 and _r[0].strip() == f"NOTIF::{clave}":
                return True
        return False
    except Exception:
        return False

def _marcar_notif_enviada(clave):
    """Marca en la hoja Sessions que una notif se envió."""
    try:
        from core.database import conectar_google_sheets as _cgs_n
        _ws = _cgs_n("Sessions")
        if not _ws: return
        _ws.append_row([f"NOTIF::{clave}", datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")],
                       value_input_option="USER_ENTERED")
    except Exception:
        pass

def _check_apertura_notificacion():
    """
    Detecta si acaba de abrir el período de predicciones Y si faltan 2h para el cierre.
    Envía email de aviso en ambos casos (una sola vez por sesión).
    """
    try:
        import datetime as _dt
        _tz_arg = None
        try:
            import pytz as _ptz; _tz_arg = _ptz.timezone("America/Argentina/Buenos_Aires")
        except Exception: pass
        ahora = _dt.datetime.now(_tz_arg) if _tz_arg else _dt.datetime.utcnow()

        def _send_email_notif(asunto, cuerpo):
            _gm_u = st.secrets.get("GMAIL_USER","")
            _gm_p = st.secrets.get("GMAIL_APP_PASSWORD","")
            _emails = st.secrets.get("emails",{})
            if not _gm_u or not _gm_p or not _emails: return
            import smtplib; from email.mime.text import MIMEText as _MT
            for _pn, _em in _emails.items():
                if not _em: continue
                try:
                    _mm = _MT(cuerpo.replace("{piloto}",_pn),"plain","utf-8")
                    _mm["Subject"] = asunto; _mm["From"] = f"Torneo Fefe Wolf <{_gm_u}>"; _mm["To"] = _em
                    with smtplib.SMTP_SSL("smtp.gmail.com",465) as _sv:
                        _sv.login(_gm_u,_gm_p); _sv.sendmail(_gm_u,_em,_mm.as_string())
                except Exception: pass

        for gp_n, gp_cierre_str in HORARIOS_CARRERA.items():
            if gp_n in GPS_SUSPENDIDOS: continue
            try:
                cierre_dt = _dt.datetime.fromisoformat(gp_cierre_str)
                if _tz_arg: cierre_dt = _tz_arg.localize(cierre_dt)
                apertura_dt = cierre_dt - _dt.timedelta(days=3)
            except Exception: continue

            import re as _re_n
            _gp_short = _re_n.sub(r'^\d+\.\s*','',gp_n).strip()
            _cierre_str = cierre_dt.strftime("%A %d/%m a las %H:%M hs")

            # ── Notif apertura (ventana amplia: hasta 12h después de abrir) ──
            diff_open = (ahora - apertura_dt).total_seconds() if ahora > apertura_dt else -1
            if 0 <= diff_open <= 43200:  # hasta 12h después de la apertura
                _notif_key = f"notif_apertura_{gp_n}"
                # Persistir en la hoja para no remandar si ya se envió (entre sesiones)
                _ya_enviado = _notif_ya_enviada(f"apertura_{gp_n}")
                if not st.session_state.get(_notif_key, False) and not _ya_enviado:
                    st.session_state[_notif_key] = True
                    _msg = (f"🏎️ TORNEO FEFE WOLF 2026\n\n"
                            f"🟢 ¡ABRIERON LAS PREDICCIONES!\n\n"
                            f"🏁 {_gp_short.upper()}\n⏰ Cierre: {_cierre_str}\n\n"
                            f"Hola {{piloto}}, ya podés cargar tus predicciones:\n"
                            f"torneofefewolf2026.streamlit.app")
                    _send_email_notif(f"🟢 ¡Abrieron predicciones! {_gp_short}", _msg)
                    _marcar_notif_enviada(f"apertura_{gp_n}")

            # ── Alerta 2h antes del cierre ────────────────────────────
            diff_close = (cierre_dt - ahora).total_seconds() if cierre_dt > ahora else -1
            if 0 <= diff_close <= 7200:  # faltan 2h o menos
                _warn_key = f"notif_2h_{gp_n}"
                if not st.session_state.get(_warn_key, False):
                    st.session_state[_warn_key] = True
                    _msg2 = (f"⚠️ TORNEO FEFE WOLF 2026\n\n"
                             f"⏰ FALTAN 2 HORAS PARA EL CIERRE\n\n"
                             f"🏁 {_gp_short.upper()}\n⏰ Cierre: {_cierre_str}\n\n"
                             f"Hola {{piloto}}, si aún no enviaste tus predicciones ¡es ahora o nunca!\n"
                             f"torneofefewolf2026.streamlit.app")
                    _send_email_notif(f"⚠️ ¡Faltan 2h! Cierra {_gp_short}", _msg2)
            break
    except Exception: pass


def pantalla_inicio():
    st.markdown("""
    <div class="hero">
      <div class="hero-title">🏆 TORNEO DE PREDICCIONES</div>
      <div class="hero-subtitle">FEFE WOLF 2026</div>
      <div class="hero-foot">© 2026 Derechos Reservados — Fundado por <b>Checo Perez</b></div>
    </div>""", unsafe_allow_html=True)

    # ── PRÓXIMO GP — AUTOMÁTICO (calendario completo 2026) ───────────
    # Formato: (nombre, flag, circuito, fechas_display, race_utc, close_utc, open_utc, suspendido)
    # Todos los horarios en UTC. Argentina = UTC-3 (sin DST).
    # suspendido=True → se saltea en el countdown y se muestra banner de aviso.
    _CAL_2026 = [
        ("GP Australia",   "🇦🇺", "Melbourne",        "06-08 Mar",    "2026-03-08 05:00", "2026-03-08 04:00", "2026-03-05 04:00", False),
        ("GP China",       "🇨🇳", "Shanghái",         "13-15 Mar",    "2026-03-15 07:00", "2026-03-15 06:00", "2026-03-12 06:00", False),
        ("GP Japón",       "🇯🇵", "Suzuka",           "27-29 Mar",    "2026-03-29 05:00", "2026-03-29 04:00", "2026-03-26 04:00", False),
        ("GP Bahrein",     "🇧🇭", "Sakhir",           "10-12 Abr",    "2026-04-12 15:00", "2026-04-12 14:00", "2026-04-09 14:00", True),
        ("GP Arabia S.",   "🇸🇦", "Jeddah",           "17-19 Abr",    "2026-04-19 17:00", "2026-04-19 16:00", "2026-04-16 16:00", True),
        ("GP Miami",       "🇺🇸", "Miami",            "01-03 May",    "2026-05-03 17:00", "2026-05-03 13:00", "2026-04-30 13:00", False),
        ("GP Canadá",      "🇨🇦", "Montréal",         "22-24 May",    "2026-05-24 20:00", "2026-05-24 18:00", "2026-05-21 18:00", False),
        ("GP Mónaco",      "🇲🇨", "Montecarlo",       "05-07 Jun",    "2026-06-07 13:00", "2026-06-07 12:00", "2026-06-04 12:00", False),
        ("GP España",      "🇪🇸", "Barcelona",        "12-14 Jun",    "2026-06-14 13:00", "2026-06-14 12:00", "2026-06-11 12:00", False),
        ("GP Austria",     "🇦🇹", "Spielberg",        "26-28 Jun",    "2026-06-28 13:00", "2026-06-28 12:00", "2026-06-25 12:00", False),
        ("GP Gran Br.",    "🇬🇧", "Silverstone",      "03-05 Jul",    "2026-07-05 14:00", "2026-07-05 13:00", "2026-07-02 13:00", False),
        ("GP Bélgica",     "🇧🇪", "Spa",              "17-19 Jul",    "2026-07-19 13:00", "2026-07-19 12:00", "2026-07-16 12:00", False),
        ("GP Hungría",     "🇭🇺", "Budapest",         "24-26 Jul",    "2026-07-26 13:00", "2026-07-26 12:00", "2026-07-23 12:00", False),
        ("GP Holanda",     "🇳🇱", "Zandvoort",        "21-23 Ago",    "2026-08-23 13:00", "2026-08-23 12:00", "2026-08-20 12:00", False),
        ("GP Italia",      "🇮🇹", "Monza",            "04-06 Sep",    "2026-09-06 13:00", "2026-09-06 12:00", "2026-09-03 12:00", False),
        ("GP Madrid",      "🇪🇸", "Madrid",           "11-13 Sep",    "2026-09-13 13:00", "2026-09-13 12:00", "2026-09-10 12:00", False),
        ("GP Azerbaiyán",  "🇦🇿", "Bakú",             "25-27 Sep",    "2026-09-27 11:00", "2026-09-27 10:00", "2026-09-24 10:00", False),
        ("GP Singapur",    "🇸🇬", "Marina Bay",       "09-11 Oct",    "2026-10-11 12:00", "2026-10-11 11:00", "2026-10-08 11:00", False),
        ("GP EE.UU.",      "🇺🇸", "Austin",           "23-25 Oct",    "2026-10-25 20:00", "2026-10-25 18:00", "2026-10-22 18:00", False),
        ("GP México",      "🇲🇽", "México DF",        "30-01 Nov",    "2026-11-01 20:00", "2026-11-01 18:00", "2026-10-29 18:00", False),
        ("GP Brasil",      "🇧🇷", "São Paulo",        "06-08 Nov",    "2026-11-08 17:00", "2026-11-08 16:00", "2026-11-05 16:00", False),
        ("GP Las Vegas",   "🇺🇸", "Las Vegas",        "19-21 Nov",    "2026-11-21 06:00", "2026-11-21 05:00", "2026-11-18 05:00", False),
        ("GP Qatar",       "🇶🇦", "Lusail",           "27-29 Nov",    "2026-11-29 14:00", "2026-11-29 13:00", "2026-11-26 13:00", False),
        ("GP Abu Dabi",    "🇦🇪", "Yas Marina",       "04-06 Dic",    "2026-12-06 13:00", "2026-12-06 12:00", "2026-12-03 12:00", False),
    ]

    from datetime import datetime, timezone as _tz_utc, timedelta as _td
    _TZ_ARG = pytz.timezone("America/Argentina/Buenos_Aires")
    _now_utc = datetime.now(_tz_utc.utc)

    # ── Encuentra el próximo GP NO suspendido ────────────────────────────────
    _gp = None
    for _g in _CAL_2026:
        if _g[7]:  # suspendido
            continue
        _race_dt = datetime.strptime(_g[4], "%Y-%m-%d %H:%M").replace(tzinfo=_tz_utc.utc)
        if _now_utc < _race_dt + _td(hours=3):
            _gp = _g; break
    if not _gp:
        _gp = [g for g in _CAL_2026 if not g[7]][-1]  # último GP real si terminó la temporada

    _gp_name, _gp_flag, _gp_venue, _gp_dates, _t_race, _t_close, _t_open, _ = _gp
    _gp_name_upper = _gp_name.upper()

    # ── Conversión UTC → Argentina con pytz (correcto, maneja cruce de medianoche) ──
    def _utc_to_arg_str(utc_str: str) -> str:
        dt_utc = datetime.strptime(utc_str, "%Y-%m-%d %H:%M").replace(tzinfo=_tz_utc.utc)
        dt_arg = dt_utc.astimezone(_TZ_ARG)
        dia_sem = ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][dt_arg.weekday()]
        return f"{dia_sem} {dt_arg.day} · {dt_arg.strftime('%H:%M')} ARG"

    _close_arg_str = _utc_to_arg_str(_t_close)
    _race_arg_str  = _utc_to_arg_str(_t_race)
    _open_arg_str  = _utc_to_arg_str(_t_open)

    # ── Banner GPS suspendidos ────────────────────────────────────────────────
    _suspendidos = [g for g in _CAL_2026 if g[7]]
    if _suspendidos:
        _susp_txt = " · ".join(f"{g[1]} {g[0]}" for g in _suspendidos)
        st.markdown(
            f'<div style="background:rgba(255,80,0,.13);border:1px solid rgba(255,100,0,.4);'
            f'border-radius:12px;padding:10px 16px;margin-bottom:12px;text-align:center;'
            f'font-size:12px;font-weight:700;color:#ffaa55;letter-spacing:.04em;">'
            f'⚠️ GPS SUSPENDIDOS POR LA F1 OFICIAL: {_susp_txt}'
            f'</div>',
            unsafe_allow_html=True
        )

    _chtml = f"""
    <style>
    @keyframes ngpG{{0%,100%{{box-shadow:0 0 26px rgba(212,175,55,.13);}}
      50%{{box-shadow:0 0 48px rgba(212,175,55,.28);}}}}
    .ngp-box{{background:linear-gradient(145deg,rgba(8,11,28,.99),rgba(13,17,42,.99));
      border:1.5px solid rgba(212,175,55,.45);border-radius:20px;
      padding:22px 20px 18px;text-align:center;
      animation:ngpG 3s ease-in-out infinite;position:relative;overflow:hidden;}}
    .ngp-box::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
      background:linear-gradient(90deg,transparent,#d4af37,rgba(255,220,100,.9),#d4af37,transparent);}}
    .ngp-flag{{font-size:26px;display:block;margin-bottom:4px;}}
    .ngp-name{{font-size:38px;font-weight:900;color:#ffdd7a;letter-spacing:.05em;
      text-transform:uppercase;line-height:1.1;text-shadow:0 0 22px rgba(255,221,122,.28);}}
    .ngp-venue{{font-size:11px;color:rgba(169,178,214,.55);margin:4px 0 14px;
      letter-spacing:.1em;text-transform:uppercase;}}
    .ngp-lbl{{font-size:9px;font-weight:900;letter-spacing:.22em;color:rgba(246,195,73,.7);
      text-transform:uppercase;margin-bottom:9px;}}
    .ngp-clock{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;}}
    .ngp-unit{{text-align:center;min-width:62px;}}
    .ngp-num{{font-size:36px;font-weight:900;color:#ffdd7a;
      background:rgba(246,195,73,.09);border:1.5px solid rgba(246,195,73,.38);
      border-radius:12px;padding:7px 13px;display:block;
      font-variant-numeric:tabular-nums;font-family:'Inter',monospace;
      box-shadow:0 0 14px rgba(212,175,55,.14);}}
    .ngp-ul{{font-size:9px;font-weight:700;letter-spacing:.14em;
      color:rgba(169,178,214,.5);text-transform:uppercase;margin-top:5px;}}
    .ngp-sub{{margin-top:12px;font-size:10px;color:rgba(232,236,255,.45);letter-spacing:.05em;}}
    .ngp-sub b{{color:#ffdd7a;}}
    @media(max-width:640px){{.ngp-name{{font-size:26px;}}
      .ngp-num{{font-size:26px;padding:5px 9px;}} .ngp-clock{{gap:8px;}} .ngp-unit{{min-width:52px;}}}}
    </style>
    <div class="ngp-box">
      <span class="ngp-flag">{_gp_flag}</span>
      <div class="ngp-name">{_gp_name_upper}</div>
      <div class="ngp-venue">📍 {_gp_venue} &nbsp;·&nbsp; {_gp_dates} 2026</div>
      <div class="ngp-lbl" id="ngp-top-lbl">⏳ CARGANDO…</div>
      <div class="ngp-clock" id="fw-countdown">
        <div class="ngp-unit"><span class="ngp-num" id="cd-d">--</span><div class="ngp-ul">Días</div></div>
        <div class="ngp-unit"><span class="ngp-num" id="cd-h">--</span><div class="ngp-ul">Horas</div></div>
        <div class="ngp-unit"><span class="ngp-num" id="cd-m">--</span><div class="ngp-ul">Minutos</div></div>
        <div class="ngp-unit"><span class="ngp-num" id="cd-s">--</span><div class="ngp-ul">Segundos</div></div>
      </div>
      <div class="ngp-sub" id="ngp-sub"></div>
    </div>
    <script>
    (function(){{
      var tOpen=new Date("{_t_open} UTC").getTime();
      var tClose=new Date("{_t_close} UTC").getTime();
      var tRace=new Date("{_t_race} UTC").getTime();
      function pad(n){{return String(n).padStart(2,"0");}}
      function upd(ms){{
        var d=Math.floor(ms/86400000),h=Math.floor((ms%86400000)/3600000);
        var m=Math.floor((ms%3600000)/60000),s=Math.floor((ms%60000)/1000);
        ["cd-d","cd-h","cd-m","cd-s"].forEach(function(id,i){{
          var el=document.getElementById(id); if(el)el.textContent=pad([d,h,m,s][i]);
        }});
      }}
      function tick(){{
        var now=Date.now();
        var lbl=document.getElementById("ngp-top-lbl");
        var sub=document.getElementById("ngp-sub");
        if(now<tOpen){{
          upd(tOpen-now);
          if(lbl)lbl.textContent="⏳ FALTAN PARA ABRIR PREDICCIONES";
          if(sub)sub.innerHTML="Abre: <b>{_open_arg_str}</b> &nbsp;&middot;&nbsp; Cierre: <b>{_close_arg_str}</b>";
        }} else if(now<tClose){{
          upd(tClose-now);
          if(lbl)lbl.textContent="⚡ PREDICCIONES ABIERTAS — CIERRAN EN";
          if(sub)sub.innerHTML="Cierre: <b>{_close_arg_str}</b>";
        }} else if(now<tRace){{
          document.getElementById("fw-countdown").innerHTML=
            "<b style='color:#ff6644;font-size:15px;'>🔴 PREDICCIONES CERRADAS</b>";
          if(lbl)lbl.textContent="CARRERA: {_race_arg_str}";
          if(sub)sub.innerHTML="Largada: <b>{_race_arg_str}</b>";
        }} else {{
          document.getElementById("fw-countdown").innerHTML=
            "<b style='color:#4ade80;font-size:15px;'>🏁 {_gp_name_upper} 2026 FINALIZADO</b>";
          if(lbl)lbl.textContent="{_gp_name_upper} 2026"; if(sub)sub.innerHTML="";
        }}
      }}
      tick(); setInterval(tick,1000);
    }})();
    </script>
    """
    components.html(_chtml, height=248, scrolling=False)

    # ── QUICK ACCESS — botones Streamlit reales ───────────────────
    st.markdown("""<style>
    div[data-testid="stHorizontalBlock"] .fw-qb>button{
      background:linear-gradient(145deg,rgba(12,16,38,.98),rgba(7,9,22,.98))!important;
      border:1.5px solid rgba(255,255,255,.1)!important;border-radius:14px!important;
      padding:14px 8px 12px!important;color:#e8ecff!important;
      font-size:11px!important;font-weight:800!important;letter-spacing:.06em!important;
      text-transform:uppercase!important;transition:all .12s!important;
      min-height:68px!important;width:100%!important;
      white-space:pre-line!important;line-height:1.5!important;}
    div[data-testid="stHorizontalBlock"] .fw-qb>button:hover{
      background:linear-gradient(145deg,rgba(212,175,55,.18),rgba(90,60,0,.2))!important;
      border-color:rgba(212,175,55,.55)!important;transform:translateY(-2px)!important;
      box-shadow:0 5px 16px rgba(212,175,55,.22)!important;color:#ffdd7a!important;}
    div[data-testid="stHorizontalBlock"] .fw-qb>button:active{transform:scale(.97)!important;}
    </style>""", unsafe_allow_html=True)
    _q1,_q2,_q3,_q4,_q5 = st.columns(5)
    for _col,_lbl,_nav in [(_q1,"⚡\nPredicción","Predicciones"),
                            (_q2,"📊\nTabla","Posiciones"),
                            (_q3,"💬\nPaddock","Paddock"),
                            (_q4,"🏆\nCampeones","Formuleros_campeones"),
                            (_q5,"👥\nFormuleros","Formuleros_tab")]:
        with _col:
            _ukey = f"qb_{_nav}"
            if st.button(_lbl, use_container_width=True, key=_ukey):
                _dest = "Formuleros" if "Formuleros" in _nav else _nav
                # Si es Campeones, marcar para auto-abrir esa pestaña
                if _nav == "Formuleros_campeones":
                    st.session_state["formuleros_tab_target"] = "Muro de Campeones"
                # Marcar el radio del menú según el destino
                _idx_map = {"Predicciones":1,"Posiciones":2,"Paddock":5,
                            "Formuleros_campeones":4,"Formuleros_tab":4}
                if _nav in _idx_map:
                    st.session_state["fw_sidebar_idx"] = _idx_map[_nav]
                st.session_state["fw_force_nav"] = _dest; st.rerun()

    st.markdown("""<div class="section-title">📜 EL LEGADO DE FEFE WOLF</div>
    <div class="card gold-left">
      <div class="card-title">EN EL PRINCIPIO, HUBO RUIDO DE MOTORES...</div>
      <div class="card-text">
        Corría el año 2021. El mundo estaba cambiando, y la Fórmula 1 vivía una de sus batallas más feroces.
        En ese caos, cinco amigos decidieron que ser espectadores no era suficiente. Necesitaban ser protagonistas.<br><br>
        Bajo la visión fundacional de <b>Checo Perez</b>, se creó este santuario: un lugar donde la amistad se mide en puntos
        y el honor se juega en cada curva.<br><br>
        Pero este torneo no sería posible sin nuestra guía eterna: <b>Fefe Wolf</b>. Aunque no esté físicamente en el paddock,
        su espíritu competitivo impregna cada decisión. Es el líder espiritual que recuerda que nunca hay que levantar el pie.<br><br>
        <b>LOS CINCO ELEGIDOS:</b> Checo, Lauda, Bottas, Lando y Alonso.<br>
        No corremos por dinero. Corremos por el derecho sagrado de decir "te lo dije" el domingo por la tarde.<br><br>
        Hemos visto campeones ascender y caer. Vimos a Lauda y a Fefe Wolf compartir la gloria del 21. Vimos el dominio
        implacable de Checo, actual Tri Campeón. Vimos la sorpresa táctica y caída de Bottas.
        Ahora, en 2026, Audi ruge, Cadillac desafía al sistema y Colapinto lleva la bandera argentina.
        <i>¿Quién tendrá la audacia para reclamar el trono este año?</i>
      </div>
    </div>""", unsafe_allow_html=True)
    st.markdown("<div class='section-title'>👑 EN MEMORIA DEL REY FEFE WOLF</div>", unsafe_allow_html=True)
    _,c2,_ = st.columns([1,2,1])
    with c2:
        try: st.image("IMAGENFEFE.jfif", use_container_width=True)
        except: st.info("Subí 'IMAGENFEFE.jfif' para mostrarla.")
    st.markdown("<div class='section-title'>🏎️ PILOTOS EN PARRILLA</div>", unsafe_allow_html=True)
    # CSS base de cards — sin colores hardcodeados, se inyectan inline por piloto
    st.markdown("""<style>
@keyframes cardFloat{0%,100%{transform:translateY(0) scale(1);}50%{transform:translateY(-7px) scale(1.03);}}
@keyframes engineRev{0%{opacity:.25;width:8%;}60%{opacity:1;width:88%;}100%{opacity:.25;width:8%;}}
.fw-pilot-card{border-radius:18px;padding:20px 8px 16px;text-align:center;position:relative;overflow:hidden;cursor:default;transition:transform .25s ease,box-shadow .3s ease;margin-bottom:4px;}
.fw-pilot-card:hover{transform:translateY(-10px) scale(1.05)!important;animation:none!important;}
.fw-pilot-card::before{content:"";position:absolute;top:0;left:0;right:0;height:2px;border-radius:2px 2px 0 0;}
.fw-pilot-engine{position:absolute;bottom:7px;left:50%;transform:translateX(-50%);height:3px;border-radius:999px;animation:engineRev 2s ease-in-out infinite;}
.fw-pilot-icon{font-size:30px;margin-bottom:8px;display:block;}
.fw-pilot-name{font-size:11px;font-weight:800;letter-spacing:.04em;margin-bottom:3px;line-height:1.3;}
.fw-pilot-role{font-size:8px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;opacity:.55;}
.fw-pilot-pos{position:absolute;top:8px;left:10px;font-size:11px;font-weight:900;opacity:.65;}
.fw-pilot-rank{position:absolute;top:8px;right:10px;font-size:14px;}
</style>""", unsafe_allow_html=True)
    _n_pilotos = len(PILOTOS_TORNEO)
    parrilla_cols = st.columns(_n_pilotos)

    # ── Leer tabla real del torneo ─────────────────────────────────
    _parrilla_df = None
    try:
        _m_db2 = _mod_db()
        if "_error" not in _m_db2:
            _parrilla_df = _safe_call(_m_db2["leer_tabla_posiciones"], PILOTOS_TORNEO,
                                      timeout_sec=15, default=None)
    except Exception: pass

    _MEDAL_MAP = {1:"🥇",2:"🥈",3:"🥉"}
    _ROLE_MAP  = {"Checo Perez":"Comisario","Lando Norris":"Sub Com.",
                  "Fernando Alonso":"FIPF","Valteri Bottas":"FIPF","Nicki Lauda":"Formulero",
                  "Yuki Tsunoda":"Formulero"}

    # Fallback grid (orden por defecto cuando no hay datos) — todos los formuleros
    _FALLBACK_GRID = []
    for _fi, _fp in enumerate(PILOTOS_TORNEO):
        _FALLBACK_GRID.append((_fp, PILOTO_COLORS.get(_fp,"#a855f7"),
                               f"P{_fi+1}", _MEDAL_MAP.get(_fi+1, f"{_fi+1}°"),
                               _ROLE_MAP.get(_fp,"Formulero")))

    if _parrilla_df is not None and not (hasattr(_parrilla_df,"empty") and _parrilla_df.empty):
        try:
            _pdf = _parrilla_df.copy()
            _pdf["Puntos"] = pd.to_numeric(_pdf.get("Puntos", pd.Series([0]*len(_pdf))), errors="coerce").fillna(0)
            _pdf = _pdf.sort_values("Puntos", ascending=False).reset_index(drop=True)
            _pilots_grid = []
            for _ri in range(min(_n_pilotos, len(_pdf))):
                _pn = str(_pdf.iloc[_ri].get("Piloto","?"))
                _pp = f"P{_ri+1}"
                _pr = _MEDAL_MAP.get(_ri+1, f"{_ri+1}°")
                _clr = PILOTO_COLORS.get(_pn,"#a855f7")
                _rl  = _ROLE_MAP.get(_pn,"Formulero")
                _pilots_grid.append((_pn, _clr, _pp, _pr, _rl))
            # Asegurar que todos los formuleros aparezcan (los que no estén en la tabla, al final con 0)
            _en_grid = {g[0] for g in _pilots_grid}
            for _fi, _fp in enumerate(PILOTOS_TORNEO):
                if _fp not in _en_grid:
                    _pos_n = len(_pilots_grid)+1
                    _pilots_grid.append((_fp, PILOTO_COLORS.get(_fp,"#a855f7"),
                                         f"P{_pos_n}", f"{_pos_n}°",
                                         _ROLE_MAP.get(_fp,"Formulero")))
        except Exception:
            _pilots_grid = list(_FALLBACK_GRID)
    else:
        _pilots_grid = list(_FALLBACK_GRID)
    for _pg_col, (_pg_n, _pg_cl, _pg_p, _pg_r, _pg_rl) in zip(parrilla_cols, _pilots_grid):
        _pg_ph = DRIVER_HEADSHOTS.get(_pg_n, DRIVER_PHOTOS.get(_pg_n, ""))
        _delay = {"P1":"0s","P2":"0.45s","P3":"0.9s","P4":"1.35s","P5":"1.8s"}.get(_pg_p,"0s")
        _dur   = {"P1":"2.4s","P2":"2.75s","P3":"3.1s","P4":"3.45s","P5":"3.8s"}.get(_pg_p,"2.5s")
        _card_style = (
            f"background:linear-gradient(145deg,{_pg_cl}1A 0%,{_pg_cl}0A 100%);"
            f"border:1.5px solid {_pg_cl}66;"
            f"box-shadow:0 4px 22px {_pg_cl}22,inset 0 1px 0 {_pg_cl}33;"
            f"animation:cardFloat {_dur} ease-in-out {_delay} infinite;"
        )
        _stripe = f"background:linear-gradient(90deg,transparent,{_pg_cl},transparent);"
        with _pg_col:
            if _pg_ph:
                _pg_img = (
                    f'<img src="{_pg_ph}" style="width:68px;height:68px;'
                    f'border-radius:50%;object-fit:cover;object-position:top;'
                    f'border:2px solid {_pg_cl};margin:0 auto 6px;display:block;">'
                )
            else:
                _pg_img = f'<span class="fw-pilot-icon" style="color:{_pg_cl};">🏎️</span>'
            st.markdown(
                f'<div class="fw-pilot-card" style="{_card_style}">'
                f'<div style="position:absolute;top:0;left:0;right:0;height:1px;border-radius:2px 2px 0 0;{_stripe}"></div>'
                f'<span class="fw-pilot-pos" style="color:{_pg_cl};">{_pg_p}</span>'
                f'<span class="fw-pilot-rank">{_pg_r}</span>'
                + _pg_img +
                f'<div class="fw-pilot-name" style="color:{_pg_cl};">{_pg_n}</div>'
                f'<div class="fw-pilot-role">{_pg_rl}</div>'
                f'<div class="fw-pilot-engine" style="background:{_pg_cl};box-shadow:0 0 8px {_pg_cl}88;"></div>'
                '</div>',
                unsafe_allow_html=True
            )
            if st.button(f"👤 Ver perfil", key=f"ini_pil_{_pg_n}", use_container_width=True):
                st.session_state["fw_force_nav"] = "Formuleros"
                st.session_state["formuleros_perfil_target"] = _pg_n  # Navigate to this pilot
                # Marcar el radio del menú en Formuleros (4 = índice de Formuleros)
                st.session_state["fw_sidebar_idx"] = 4
                st.rerun()

def pantalla_calendario():
    st.markdown('<div class="section-title">📅 CALENDARIO TEMPORADA 2026</div>', unsafe_allow_html=True)
    _,c2,_ = st.columns([1,2,1])
    with c2:
        try: st.image("IMAGENCALENDARIO.jfif", use_container_width=True, caption="")
        except: pass
    # Build table HTML
    _rows_c = ""
    for i_c2, row_c2 in enumerate(CALENDARIO_VISUAL, 1):
        gp_c2 = row_c2.get("Gran Premio",""); circ_c2 = row_c2.get("Circuito","")
        fmt_c2 = row_c2.get("Formato",""); fecha_c2 = row_c2.get("Fecha","")
        susp_c2 = "SUSPENDIDO" in gp_c2 or "⛔" in gp_c2
        sprint_c2 = "SPRINT" in fmt_c2
        row_s2 = 'style="opacity:.5;"' if susp_c2 else ""
        fmt_s2 = "color:#ff7043;" if susp_c2 else ("color:#a855f7;font-weight:800;" if sprint_c2 else "color:rgba(169,178,214,.55);")
        _rows_c += (f'<tr {row_s2}>' +
            f'<td style="color:rgba(169,178,214,.4);font-size:10px;text-align:center;padding:8px 6px;">{i_c2}</td>' +
            f'<td style="font-size:11px;color:rgba(169,178,214,.65);padding:8px 8px;">{fecha_c2}</td>' +
            f'<td style="padding:8px 8px;font-weight:{"700" if not susp_c2 else "400"};">{gp_c2}</td>' +
            f'<td style="color:rgba(169,178,214,.5);font-size:11px;padding:8px 8px;">{circ_c2}</td>' +
            f'<td style="{fmt_s2}padding:8px 8px;">{fmt_c2}</td></tr>')
    st.markdown(
        '<div style="overflow-x:auto;margin:10px 0;">' +
        '<table style="width:100%;border-collapse:collapse;background:rgba(7,10,25,.97);' +
        'border:1px solid rgba(212,175,55,.22);border-radius:14px;overflow:hidden;">' +
        '<thead><tr style="border-bottom:1px solid rgba(212,175,55,.2);">' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;padding:10px 6px;text-align:center;">#</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;padding:10px 8px;">Fecha</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;padding:10px 8px;">Gran Premio</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;padding:10px 8px;">Circuito</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;padding:10px 8px;">Formato</th>' +
        '</tr></thead><tbody style="color:#e8ecff;font-size:12px;">' +
        _rows_c + '</tbody></table></div>',
        unsafe_allow_html=True)
def pantalla_pilotos_y_escuderias():
    st.markdown('<div class="section-title">🏎️ PILOTOS Y EQUIPOS 2026</div>', unsafe_allow_html=True)

    tab_pil, tab_eq = st.tabs(["👤 Pilotos F1 2026", "🏎️ Constructores 2026"])

    with tab_pil:
        all_drivers = []
        for equipo, pilotos in GRILLA_2026.items():
            color = TEAM_COLORS.get(equipo, "#A855F7")
            abbr  = TEAM_LOGOS_SVG.get(equipo, equipo[:3])
            for num_idx, pil in enumerate(pilotos):
                all_drivers.append((pil, equipo, color, abbr, num_idx + 1))

        # Inject improved grid CSS
        st.markdown("""
        <style>
        .f1-drivers-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
          gap: 14px;
          padding: 8px 0 16px;
        }
        .f1d-card {
          background: linear-gradient(145deg, rgba(7,10,25,.97) 0%, rgba(14,18,42,.95) 100%);
          border: 1.5px solid var(--tc, #a855f7);
          border-radius: 16px;
          overflow: hidden;
          position: relative;
          transition: transform .25s ease, box-shadow .25s ease;
          box-shadow: 0 4px 18px rgba(0,0,0,.5);
        }
        .f1d-card:hover {
          transform: translateY(-6px) scale(1.02);
          box-shadow: 0 10px 32px rgba(0,0,0,.7), 0 0 20px var(--tc, #a855f7)33;
        }
        .f1d-top-stripe {
          height: 3px;
          background: var(--tc, #a855f7);
          width: 100%;
        }
        .f1d-logo {
          position:absolute;top:10px;left:8px;
          height:18px;max-width:54px;object-fit:contain;
          opacity:.85;filter:brightness(1.2);z-index:3;
        }
        .f1d-team-badge {
          position: absolute;
          top: 10px;
          right: 10px;
          font-size: 8px;
          font-weight: 900;
          color: var(--tc, #a855f7);
          background: rgba(0,0,0,.6);
          border: 1px solid var(--tc, #a855f7)55;
          border-radius: 6px;
          padding: 2px 6px;
          letter-spacing: .1em;
          z-index: 2;
        }
        .f1d-photo-wrap {
          width: 100%;
          aspect-ratio: 1 / 1.05;
          overflow: hidden;
          background: linear-gradient(180deg, rgba(0,0,0,.1), rgba(0,0,0,.5));
          position: relative;
        }
        .f1d-photo {
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: center 18%;
          display: block;
          transition: transform .3s ease;
        }
        @media (max-width:768px){
          .f1d-photo-wrap { aspect-ratio: 1 / 1.05 !important; background:#08091e !important; }
          .f1d-photo { object-fit: cover !important; object-position: center 18% !important; }
        }
        .f1d-card:hover .f1d-photo { transform: scale(1.04); }
        .f1d-fallback {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 36px;
          font-weight: 900;
          background: rgba(0,0,0,.4);
        }
        .f1d-info {
          padding: 10px 10px 12px;
          background: linear-gradient(0deg, rgba(0,0,0,.85), rgba(0,0,0,.4));
        }
        .f1d-flag { font-size: 14px; margin-bottom: 3px; }
        .f1d-firstname {
          font-size: 9px;
          font-weight: 500;
          color: rgba(232,236,255,.6);
          text-transform: uppercase;
          letter-spacing: .08em;
          line-height: 1.2;
        }
        .f1d-lastname {
          font-size: 13px;
          font-weight: 900;
          color: var(--tc, #e8ecff);
          letter-spacing: .04em;
          line-height: 1.2;
          margin-bottom: 4px;
        }
        .f1d-team-name {
          font-size: 8px;
          color: var(--tc, #a855f7);
          font-weight: 700;
          letter-spacing: .12em;
          text-transform: uppercase;
          opacity: .8;
        }
        </style>
        """, unsafe_allow_html=True)
        cards_html = '<div class="f1-drivers-grid">'  
        for pil, equipo, color, abbr, num in all_drivers:
            photo = DRIVER_PHOTOS.get(pil, "")
            initials = "".join(p[0] for p in pil.split()[:2]).upper()
            nacionalidades = {
                "Lando Norris": "🇬🇧", "Oscar Piastri": "🇦🇺", "Max Verstappen": "🇳🇱",
                "Isack Hadjar": "🇫🇷", "Kimi Antonelli": "🇮🇹", "George Russell": "🇬🇧",
                "Charles Leclerc": "🇲🇨", "Lewis Hamilton": "🇬🇧", "Alex Albon": "🇹🇭",
                "Carlos Sainz": "🇪🇸", "Lance Stroll": "🇨🇦", "Fernando Alonso": "🇪🇸",
                "Liam Lawson": "🇳🇿", "Arvid Lindblad": "🇸🇪", "Oliver Bearman": "🇬🇧",
                "Esteban Ocon": "🇫🇷", "Nico Hulkenberg": "🇩🇪", "Gabriel Bortoleto": "🇧🇷",
                "Pierre Gasly": "🇫🇷", "Franco Colapinto": "🇦🇷",
                "Checo Perez": "🇲🇽", "Valteri Bottas": "🇫🇮",
            }
            logo_url = TEAM_LOGOS_CDN.get(equipo, "")
            flag = nacionalidades.get(pil, "🌍")
            last_name = pil.split()[-1].upper()
            first_name = " ".join(pil.split()[:-1])
            img_html = f'<img src="{photo}" class="f1d-photo" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';" loading="lazy">'
            fallback = f'<div class="f1d-fallback" style="display:none;color:{color};">{initials}</div>'
            cards_html += f"""
            <div class="f1d-card fade-up" style="--tc:{color}">
              <div class="f1d-top-stripe"></div>
              <div class="f1d-team-badge" style="display:flex;align-items:center;gap:4px;"><span>{abbr}</span></div>
              <img src="{logo_url}" class="f1d-logo" onerror="this.style.display='none';" loading="lazy">
              <div class="f1d-photo-wrap">{img_html}{fallback}</div>
              <div class="f1d-info">
                <div class="f1d-flag">{flag}</div>
                <div class="f1d-firstname">{first_name}</div>
                <div class="f1d-lastname">{last_name}</div>
                <div class="f1d-team-name">{equipo}</div>
              </div>
            </div>"""
        cards_html += "</div>"
        st.markdown(cards_html, unsafe_allow_html=True)

    with tab_eq:
        TEAM_DESCRIPTIONS = {
            "MCLAREN":      "El equipo de Woking vuelve como favorito con Norris y Piastri. MCL60 dominó la segunda mitad de 2025.",
            "RED BULL":     "El gigante de Milton Keynes. Verstappen busca su quinto título con el joven Hadjar como compañero.",
            "MERCEDES":     "La flecha plateada renace. Antonelli, la gran apuesta, junto a Russell en el W17.",
            "FERRARI":      "La Scuderia con Hamilton y Leclerc: la alineación más mediática de la historia de la F1.",
            "WILLIAMS":     "Albon y Sainz, una dupla sólida para llevar a Williams de regreso a la lucha por puntos.",
            "ASTON MARTIN": "El millonario proyecto de Lawrence Stroll con Alonso y su hijo Lance. AMR26 promete.",
            "RACING BULLS": "El equipo B de Red Bull. Lawson y Lindblad, dos jóvenes hambrientos de puntos.",
            "HAAS":         "Bearman y Ocon, dos europeos con hambre de demostrar. La escudería americana apuesta al futuro.",
            "AUDI":         "El debutante de lujo. Hulkenberg y Bortoleto encabezan el proyecto más ambicioso de la era moderna.",
            "ALPINE":       "Gasly y Colapinto — el argentino que tiene a toda Latinoamérica de su lado. ¡Vamos Franco!",
            "CADILLAC":     "El regreso de Checo a la grilla, ahora con Bottas. El equipo americano desafía al establishment.",
        }
        teams_list = list(GRILLA_2026.items())
        for i in range(0, len(teams_list), 2):
            cols = st.columns(2, gap="large")
            for j, (equipo, pilotos) in enumerate(teams_list[i:i+2]):
                color = TEAM_COLORS.get(equipo, "#A855F7")
                abbr  = TEAM_LOGOS_SVG.get(equipo, equipo[:3])
                desc  = TEAM_DESCRIPTIONS.get(equipo, "")
                car   = TEAM_CARS_MODULE.get(equipo, "")
                logo  = TEAM_LOGOS_CDN.get(equipo, "")
                p1, p2 = pilotos[0], pilotos[1]
                car_html  = f'<img src="{car}" class="tfc-car-img" loading="lazy" onerror="this.style.display=\'none\'">' if car else ""
                logo_html = f'<img src="{logo}" style="position:absolute;top:10px;right:12px;height:22px;max-width:72px;object-fit:contain;opacity:.85;z-index:3;" loading="lazy" onerror="this.style.display=\'none\'">' if logo else ""
                with cols[j]:
                    st.markdown(f"""
                    <div class="team-full-card fade-up" style="--tc:{color};position:relative;">
                      {logo_html}
                      <div class="tfc-header">
                        <div class="tfc-stripe"></div>
                        <div class="tfc-abbr" style="color:{color}">{abbr}</div>
                        <div class="tfc-name">{equipo}</div>
                      </div>
                      <div class="tfc-car-wrap">{car_html}</div>
                      <div class="tfc-drivers">
                        <div class="tfc-driver">
                          <div class="tfc-num" style="color:{color}">01</div>
                          <div class="tfc-dname">{p1}</div>
                        </div>
                        <div class="tfc-driver">
                          <div class="tfc-num" style="color:{color}">02</div>
                          <div class="tfc-dname">{p2}</div>
                        </div>
                      </div>
                      <div class="tfc-desc">{desc}</div>
                    </div>""", unsafe_allow_html=True)


def pantalla_reglamento():
    st.markdown("""
    <style>
    .reg-art{background:rgba(6,15,40,.7);border:1px solid rgba(59,130,246,.2);
      border-left:4px solid #3b82f6;border-radius:0 12px 12px 0;
      padding:14px 18px;margin-bottom:10px;position:relative;}
    .reg-art-title{font-size:11px;font-weight:900;color:#3b82f6;
      text-transform:uppercase;letter-spacing:.12em;margin-bottom:6px;}
    .reg-art-body{font-size:12px;color:rgba(232,236,255,.75);line-height:1.8;}
    .reg-art-body b{color:#D4AF37;}
    .reg-pts-card{background:rgba(6,15,40,.9);border:1px solid rgba(59,130,246,.25);
      border-radius:10px;padding:10px 12px;margin-bottom:8px;}
    .reg-pts-label{font-size:10px;font-weight:800;color:#3b82f6;
      text-transform:uppercase;letter-spacing:.1em;margin-bottom:6px;}
    .reg-chip{display:inline-block;background:rgba(59,130,246,.1);
      border:1px solid rgba(59,130,246,.3);border-radius:6px;
      padding:2px 8px;font-size:10px;color:#93c5fd;margin:2px 2px 2px 0;}
    .reg-chip-gold{background:rgba(212,175,55,.12)!important;
      border-color:rgba(212,175,55,.4)!important;color:#D4AF37!important;font-weight:900!important;}
    .reg-chip-red{background:rgba(239,68,68,.1)!important;
      border-color:rgba(239,68,68,.35)!important;color:#ef4444!important;}
    .reg-chip-green{background:rgba(74,222,128,.1)!important;
      border-color:rgba(74,222,128,.3)!important;color:#4ade80!important;}
    </style>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="background:linear-gradient(145deg,#04080f,#07122a);' +
        'border:2px solid rgba(59,130,246,.4);border-radius:20px;' +
        'padding:22px 26px;text-align:center;margin-bottom:18px;">' +
        '<div style="font-size:11px;letter-spacing:.2em;color:rgba(59,130,246,.6);' +
        'text-transform:uppercase;margin-bottom:8px;">📜 CÓDIGO DEPORTIVO OFICIAL</div>' +
        '<div style="font-size:22px;font-weight:900;background:linear-gradient(90deg,#3b82f6,#93c5fd,#D4AF37,#93c5fd,#3b82f6);' +
        'background-size:300% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;' +
        'background-clip:text;letter-spacing:.08em;">TORNEO FEFE WOLF 2026</div>' +
        '<div style="font-size:11px;color:rgba(169,178,214,.5);margin-top:6px;">⚔️ Predicciones · Honor · Gloria · Camaradería ⚔️</div>' +
        '</div>', unsafe_allow_html=True)

    _rt1, _rtA, _rt2, _rt3 = st.tabs(["📜 Reglamento Deportivo", "📋 Artículos", "⚔️ Sistema de Puntuación", "🏛️ Cúpula Oficial"])

    with _rt1:
        for _titulo, _cuerpo in [
            ("Artículo 1 — Autoridad Deportiva",
             "La autoridad máxima estará compuesta por la <b>Cúpula Deportiva Oficial</b>.<br>"
             "🏎 <b>Comisario Oficial:</b> Checo Pérez &nbsp;·&nbsp; 🏎 <b>Subcomisario:</b> Lando Norris<br><br>"
             "Sus responsabilidades: interpretar el reglamento, resolver conflictos, supervisar resultados, "
             "aplicar sanciones y garantizar el correcto desarrollo. Las decisiones son <b>definitivas</b>."),
            ("Artículo 2 — Plataforma Oficial",
             "Las predicciones se envían a través de la <b>página web oficial</b> con el PIN personal.<br>"
             "La web registra predicciones, resultados, tabla de posiciones e historial."),
            ("Artículo 3 — Fase de desarrollo del sistema",
             "La web puede estar en mejora continua. En caso de errores técnicos, el comisariado "
             "podrá habilitar predicciones manuales manteniendo siempre equidad deportiva."),
            ("Artículo 4 — Validez de las predicciones",
             "Para ser válida, la predicción debe:<br>"
             "• Enviarse <b>dentro del plazo</b> · Usar el <b>PIN personal</b><br>"
             "• Seleccionar un piloto por puesto y un equipo por posición<br><br>"
             "⏰ <b>Plazos:</b> Qualy y Sprint → hasta <b>1 minuto</b> antes | "
             "Carrera y Constructores → hasta <b>1 hora</b> antes, sin excepción."),
            ("Artículo 5 — Predicciones obligatorias",
             "Todos deberán completar obligatoriamente:<br>"
             "🏆 <b>Campeón de Pilotos</b> &nbsp;·&nbsp; 🏆 <b>Campeón de Constructores</b><br>"
             "La web notificará automáticamente si faltan estas predicciones."),
            ("Artículo 6 — Sanción DNS (Did Not Start)",
             "Si no se envían predicciones para un GP:<br>"
             "🚫 <b>DNS:</b> <span style=\'color:#ef4444;font-weight:900;\'>−25 puntos</span> por cada predicción no enviada.<br>"
             "Esta medida mantiene el compromiso competitivo durante toda la temporada."),
            ("Artículo 7 — Integridad del campeonato",
             "No se permitirá:<br>"
             "• Manipulación de resultados<br>"
             "• Intentos de alterar predicciones luego del cierre<br>"
             "• Conductas que perjudiquen el espíritu del torneo"),
            ("Artículo 8 — Comunicación oficial",
             "El grupo se utilizará para: comunicados oficiales, publicación de resultados, "
             "historial, envío manual en caso de fallo de la web, y debate deportivo."),
            ("Artículo 9 — Espíritu del campeonato",
             "Este torneo no se disputa por dinero. Se compite por algo más grande:<br>"
             "<b>El honor de acertar, la gloria de ganar y mantener viva la llama de este grupo.</b><br>"
             "Cada Gran Premio escribe una nueva historia. Cada predicción puede cambiar el campeonato."),
            ("Artículo 10 — Sanciones internas",
             "🟡 <b>Bandera Amarilla</b> — Advertencia. Requiere disculpas públicas.<br>"
             "🔇 <b>Modo Silencio</b> — Restricción temporal de mensajes por reincidencia.<br>"
             "⚫ <b>Bandera Negra</b> — Sanción máxima. Puede implicar expulsión del campeonato."),
        ]:
            st.markdown(
                f'<div class="reg-art">' +
                f'<div class="reg-art-title">⚖️ {_titulo}</div>' +
                f'<div class="reg-art-body">{_cuerpo}</div></div>',
                unsafe_allow_html=True)

    with _rtA:
        st.markdown(
            '<div style="text-align:center;padding:6px 0 16px;">' +
            '<div style="font-size:13px;font-weight:900;color:#D4AF37;letter-spacing:.1em;">' +
            '⚔️ TORNEO DE PREDICCIONES FEFE WOLF — TEMPORADA 2026 ⚔️</div>' +
            '<div style="font-size:10px;color:rgba(169,178,214,.5);margin-top:6px;line-height:1.7;">' +
            'El Torneo de Predicciones FEFE WOLF nace con el objetivo de reunir a amigos y apasionados ' +
            'de la Fórmula 1 en una competencia basada en estrategia, conocimiento y pasión por el deporte. ' +
            'Este campeonato se disputa por honor, orgullo y gloria deportiva, manteniendo siempre el ' +
            'espíritu de camaradería que dio origen a este grupo.</div></div>',
            unsafe_allow_html=True)
        for _tituloA, _cuerpoA in [
            ("Artículo 1 — Autoridad Deportiva",
             "La autoridad máxima del campeonato estará compuesta por la <b>Cúpula Deportiva Oficial</b> del Torneo.<br>"
             "🏎 <b>Comisario Oficial:</b> Checo Pérez &nbsp;·&nbsp; 🏎 <b>Subcomisario:</b> Lando Norris<br><br>"
             "Sus responsabilidades incluyen:<br>"
             "• Interpretar el reglamento<br>• Resolver conflictos<br>• Supervisar resultados<br>"
             "• Aplicar sanciones cuando corresponda<br>• Garantizar el correcto desarrollo del campeonato<br><br>"
             "Las decisiones del Comisariado serán <b>definitivas</b> dentro del torneo."),
            ("Artículo 2 — Plataforma Oficial",
             "Las predicciones del campeonato deberán enviarse a través de la <b>página web oficial</b> del torneo "
             "utilizando el PIN personal de predicción.<br>"
             "La web será el sistema principal para registrar:<br>"
             "• Predicciones<br>• Resultados<br>• Tabla de posiciones<br>• Historial del campeonato"),
            ("Artículo 3 — Fase de prueba del sistema",
             "Durante la temporada, la página web podrá encontrarse en fase de mejora y desarrollo.<br>"
             "En caso de errores técnicos o fallos del sistema:<br>"
             "• El comisariado podrá habilitar predicciones manuales en el grupo<br>"
             "• Se buscará siempre mantener equidad deportiva entre los participantes"),
            ("Artículo 4 — Validez de las predicciones",
             "Para que una predicción sea considerada válida deberá:<br>"
             "• Ser enviada <b>dentro del plazo</b> permitido<br>"
             "• Utilizar el <b>PIN personal</b> del participante<br>"
             "• Ya no deberán escribir los nombres en las predicciones de piloto ni tampoco en Constructores. "
             "Deberán seleccionar un piloto por puesto, lo mismo para los equipos. "
             "<b>Tienen que verificar que estén los nombres correctamente</b>.<br><br>"
             "⏰ Recordar que podrán enviar hasta que comience oficialmente la predicción que esté en juego: "
             "está permitido enviar hasta <b>1 minuto</b> antes las predicciones de Qualy y Sprint. "
             "Las de Carrera y Constructores se podrán enviar hasta <b>1 hora</b> antes, sin excepción."),
            ("Artículo 5 — Predicciones obligatorias",
             "Todos los participantes deberán completar obligatoriamente:<br>"
             "🏆 <b>Campeón de Pilotos</b> &nbsp;·&nbsp; 🏆 <b>Campeón de Constructores</b><br>"
             "Si estas predicciones no se envían, la web lo notificará automáticamente."),
            ("Artículo 6 — Sanción DNS",
             "Si un participante no envía sus predicciones para un Gran Premio, recibirá la sanción:<br>"
             "🚫 <b>DNS — Did Not Start</b><br><br>"
             "🚫 <span style='color:#ef4444;font-weight:900;'>−25 puntos</span> en la tabla general del "
             "Torneo de Predicciones, descontándose del puntaje total del campeonato.<br><br>"
             "🚫 <span style='color:#ef4444;font-weight:900;'>−2 puntos</span> en la <b>Super Licencia</b> de los Formuleros. "
             "La pérdida de puntos en la Super Licencia será <b>acumulativa</b>.<br><br>"
             "⚫ Todo participante que alcance los <b>20 puntos descontados</b> en su Super Licencia se le aplicará "
             "una <b>Bandera Negra 🏴</b> (Artículo 10) y será <b>expulsado automáticamente</b> del Torneo de "
             "Predicciones FEFE WOLF, quedando sin posibilidad alguna de reincorporarse durante la temporada vigente.<br><br>"
             "Podrá volver a participar únicamente en la temporada siguiente, aunque su historial deportivo "
             "conservará para siempre la mancha del DNS, como antecedente disciplinario dentro de los registros "
             "oficiales de la Cúpula Deportiva.<br><br>"
             "Esta medida busca mantener el compromiso competitivo durante toda la temporada."),
            ("Artículo 7 — Integridad del campeonato",
             "Los participantes deberán actuar con honestidad deportiva. No se permitirá:<br>"
             "• Manipulación de resultados<br>• Intentos de alterar predicciones luego del cierre<br>"
             "• Conductas que perjudiquen el espíritu del torneo<br><br>"
             "El comisariado podrá aplicar sanciones en caso de irregularidades."),
            ("Artículo 8 — Comunicación oficial",
             "El grupo del torneo se utilizará principalmente para:<br>"
             "• Comunicados oficiales<br>• Publicación de resultados<br>• Historiales del campeonato<br>"
             "• Envío manual de predicciones si la web presenta fallos<br>"
             "• Comentar, debatir y realizar cualquier tipo de inquietud que tengan."),
            ("Artículo 9 — Espíritu del campeonato",
             "Este torneo no se disputa por dinero. Se compite por algo mucho más grande:<br>"
             "<b>El honor de acertar, la gloria de ganar y mantener viva la llama de este grupo.</b><br>"
             "Cada Gran Premio escribe una nueva historia. Cada predicción puede cambiar el campeonato."),
            ("Artículo 10 — Sanciones internas del grupo",
             "Las sanciones internas tienen como objetivo mantener el respeto, el orden y el buen ambiente "
             "dentro del grupo del torneo. Estas sanciones no afectan las predicciones ni el sistema de puntos "
             "de la página web, salvo aquellas establecidas expresamente en el reglamento deportivo.<br><br>"
             "El comisariado podrá aplicar las siguientes sanciones:<br><br>"
             "🟡 <b>Bandera Amarilla</b> — Advertencia oficial por conductas que generen desorden, discusiones "
             "innecesarias o incumplimiento de las normas del grupo. Deberá enviar disculpas públicas en el "
             "grupo oficial del torneo.<br><br>"
             "🔇 <b>Modo Silencio</b> — Restricción temporal para enviar mensajes en el grupo en caso de "
             "reiterar conductas inapropiadas.<br><br>"
             "⚫ <b>Bandera Negra</b> — Sanción máxima aplicada en casos graves de falta de respeto o conductas "
             "que perjudiquen el desarrollo del torneo, pudiendo implicar la expulsión del campeonato.<br><br>"
             "Las decisiones del Comisario Oficial y del Subcomisario serán definitivas dentro del torneo."),
        ]:
            st.markdown(
                f'<div class="reg-art">' +
                f'<div class="reg-art-title">⚖️ {_tituloA}</div>' +
                f'<div class="reg-art-body">{_cuerpoA}</div></div>',
                unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;margin-top:10px;padding:14px;">' +
            '<div style="font-size:11px;color:rgba(212,175,55,.6);font-style:italic;">' +
            '⚔️ CÚPULA OFICIAL TORNEO DE PREDICCIONES FEFE WOLF ⚔️</div></div>',
            unsafe_allow_html=True)

    with _rt2:
        _pt1, _pt2 = st.columns(2)
        with _pt1:
            st.markdown("""
<div class="reg-pts-card">
  <div class="reg-pts-label">🏁 Carrera</div>
  <span class="reg-chip">1°→25</span><span class="reg-chip">2°→18</span><span class="reg-chip">3°→15</span>
  <span class="reg-chip">4°→12</span><span class="reg-chip">5°→10</span><span class="reg-chip">6°→8</span>
  <span class="reg-chip">7°→6</span><span class="reg-chip">8°→4</span><span class="reg-chip">9°→2</span>
  <span class="reg-chip">10°→1</span><span class="reg-chip reg-chip-gold">Pleno +5pts</span>
</div>
<div class="reg-pts-card">
  <div class="reg-pts-label">⏱️ Clasificación</div>
  <span class="reg-chip">1°→15</span><span class="reg-chip">2°→10</span><span class="reg-chip">3°→7</span>
  <span class="reg-chip">4°→5</span><span class="reg-chip">5°→3</span>
  <span class="reg-chip reg-chip-gold">Pleno +5pts</span>
</div>
<div class="reg-pts-card">
  <div class="reg-pts-label">⚡ Sprint</div>
  <span class="reg-chip">1°→8</span><span class="reg-chip">2°→7</span><span class="reg-chip">3°→6</span>
  <span class="reg-chip">4°→5</span><span class="reg-chip">5°→4</span><span class="reg-chip">6°→3</span>
  <span class="reg-chip">7°→2</span><span class="reg-chip">8°→1</span>
  <span class="reg-chip reg-chip-gold">Pleno +3pts</span>
</div>
""", unsafe_allow_html=True)
        with _pt2:
            st.markdown("""
<div class="reg-pts-card">
  <div class="reg-pts-label">🛠️ Constructores</div>
  <span class="reg-chip">1°→10</span><span class="reg-chip">2°→5</span><span class="reg-chip">3°→2</span>
  <span class="reg-chip reg-chip-gold">Pleno +3pts</span>
</div>
<div class="reg-pts-card">
  <div class="reg-pts-label">🇦🇷 Regla Colapinto</div>
  <span class="reg-chip reg-chip-green">Qualy exacto +10pts</span>
  <span class="reg-chip reg-chip-green">Carrera exacto +20pts</span>
</div>
<div class="reg-pts-card">
  <div class="reg-pts-label">🏆 Campeones de temporada</div>
  <span class="reg-chip reg-chip-gold">Piloto campeón +50pts</span>
  <span class="reg-chip reg-chip-gold">Constructor campeón +25pts</span>
</div>
<div class="reg-pts-card">
  <div class="reg-pts-label">⛔ Sanciones DNS</div>
  <span class="reg-chip reg-chip-red">Qualy faltante −25pts</span>
  <span class="reg-chip reg-chip-red">Sprint faltante −25pts</span>
  <span class="reg-chip reg-chip-red">Carrera/Const −25pts</span>
</div>
""", unsafe_allow_html=True)
        st.markdown(
            '<div style="background:rgba(212,175,55,.06);border:1px solid rgba(212,175,55,.2);' +
            'border-radius:12px;padding:12px 16px;margin-top:4px;">' +
            '<div style="font-size:10px;font-weight:800;color:#D4AF37;margin-bottom:4px;">⚖️ CRITERIO DE DESEMPATE</div>' +
            '<div style="font-size:11px;color:rgba(169,178,214,.7);">En caso de igualdad de puntos, ' +
            'gana quien haya enviado sus predicciones <b style="color:#ffdd7a;">primero</b>.</div></div>',
            unsafe_allow_html=True)

    with _rt3:
        st.markdown(
            '<div style="text-align:center;padding:10px 0 14px;">' +
            '<div style="font-size:13px;font-weight:900;color:#D4AF37;letter-spacing:.12em;">⚔️ CÚPULA OFICIAL ⚔️</div>' +
            '<div style="font-size:10px;color:rgba(169,178,214,.4);margin-top:3px;">Autoridad máxima · Torneo Fefe Wolf 2026</div>' +
            '</div>', unsafe_allow_html=True)
        try:
            _,_ic,_ = st.columns([1,2,1])
            with _ic: st.image("IMAGENCUPULA.jfif", use_container_width=True)
        except: pass
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        _rc1, _rc2 = st.columns(2)
        for _ccol, _cpil, _ctit, _cbio in [
            (_rc1,"Checo Perez","COMISARIO OFICIAL",
             "Fundador y máxima autoridad. TriCampeón invicto 2022·2023·2025. "
             "Bajo su mandato, las reglas se hacen respetar y el torneo vive su mejor era."),
            (_rc2,"Lando Norris","SUBCOMISARIO",
             "El segundo al mando. Aplica sanciones y vela por la integridad del reglamento en cada GP.")]:
            _cc = PILOTO_COLORS.get(_cpil,"#D4AF37")
            _ph = DRIVER_HEADSHOTS.get(_cpil,DRIVER_PHOTOS.get(_cpil,""))
            with _ccol:
                st.markdown(
                    f'<div style="background:linear-gradient(145deg,rgba(4,8,24,.97),rgba(7,12,32,.98));' +
                    f'border:2px solid {_cc}55;border-radius:16px;padding:18px;text-align:center;">' +
                    (f'<img src="{_ph}" style="width:75px;height:75px;border-radius:50%;object-fit:cover;' +
                     f'object-position:top;border:3px solid {_cc};margin-bottom:10px;' +
                     f'box-shadow:0 0 18px {_cc}44;">' if _ph else "") +
                    f'<div style="font-size:9px;letter-spacing:.18em;color:{_cc};font-weight:900;' +
                    f'text-transform:uppercase;margin-bottom:5px;">{_ctit}</div>' +
                    f'<div style="font-size:15px;font-weight:900;color:#e8ecff;margin-bottom:10px;">{_cpil}</div>' +
                    f'<div style="font-size:10px;color:rgba(169,178,214,.6);line-height:1.7;' +
                    f'font-style:italic;border-top:1px solid {_cc}22;padding-top:10px;">&ldquo;{_cbio}&rdquo;</div></div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div style="text-align:center;margin-top:20px;border-top:1px solid rgba(212,175,55,.1);' +
            'padding-top:12px;font-size:10px;color:rgba(212,175,55,.4);font-style:italic;">' +
            '⚔️ CÚPULA OFICIAL TORNEO DE PREDICCIONES FEFE WOLF ⚔️</div>',
            unsafe_allow_html=True)


def pantalla_tabla_posiciones():
    st.markdown('<div class="section-title">📊 TABLA GENERAL 2026</div>', unsafe_allow_html=True)
    if st.button("🔄 Actualizar tabla", key="btn_ref_tabla"):
        st.cache_data.clear(); st.rerun()

    @st.cache_data(ttl=120, show_spinner="Cargando tabla…")
    def _get():
        m = _mod_db()
        if "_error" in m: return None
        return _safe_call(m["leer_tabla_posiciones"], PILOTOS_TORNEO, timeout_sec=8, default=None)

    df = _get()
    if df is None or (hasattr(df,"empty") and df.empty):
        df = pd.DataFrame({"Piloto":PILOTOS_TORNEO,"Puntos":[0]*len(PILOTOS_TORNEO),
                           "Qualys":[0]*len(PILOTOS_TORNEO),"Sprints":[0]*len(PILOTOS_TORNEO),
                           "Carreras":[0]*len(PILOTOS_TORNEO)})
    # Asegurar que TODOS los formuleros aparezcan (aunque el database.py viejo no los incluya)
    if "Piloto" in df.columns:
        _en_tabla = set(df["Piloto"].astype(str).str.strip())
        _faltan_t = [p for p in PILOTOS_TORNEO if str(p).strip() not in _en_tabla]
        if _faltan_t:
            _cols_t = list(df.columns)
            _nuevas_t = []
            for _pt in _faltan_t:
                _fila_t = {c: 0 for c in _cols_t}
                _fila_t["Piloto"] = _pt
                _nuevas_t.append(_fila_t)
            df = pd.concat([df, pd.DataFrame(_nuevas_t)], ignore_index=True)
    if "Puntos" in df.columns:
        df["Puntos"] = pd.to_numeric(df["Puntos"], errors="coerce").fillna(0)
        df = df.sort_values("Puntos",ascending=False).reset_index(drop=True)
    if len(df)>=3:
        p1,p2,p3 = df.iloc[0],df.iloc[1],df.iloc[2]
        def _ini(n):
            return "".join(w[0] for w in str(n).split()[:2]).upper()
        def _foto_pod(piloto):
            try:
                # Preferir headshot (cara) para que no se corten en el círculo
                _u = DRIVER_HEADSHOTS.get(piloto) or DRIVER_PHOTOS.get(piloto)
                return _u or ""
            except Exception: return ""
        _c1 = PILOTO_COLORS.get(p1["Piloto"],"#D4AF37")
        _c2 = PILOTO_COLORS.get(p2["Piloto"],"#C0C0C0")
        _c3 = PILOTO_COLORS.get(p3["Piloto"],"#CD7F32")
        _pts1,_pts2,_pts3 = int(p1.get("Puntos",0)),int(p2.get("Puntos",0)),int(p3.get("Puntos",0))
        _f1,_f2,_f3 = _foto_pod(p1["Piloto"]),_foto_pod(p2["Piloto"]),_foto_pod(p3["Piloto"])

        def _avatar(foto,color,ini,size,ring):
            if foto:
                return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;overflow:hidden;'
                        f'border:{ring}px solid {color};box-shadow:0 0 18px {color}88;margin:0 auto;">'
                        f'<img src="{foto}" style="width:100%;height:100%;object-fit:cover;object-position:center 12%;" '
                        f'onerror="this.parentElement.innerHTML=\'<div style=&quot;width:100%;height:100%;display:flex;'
                        f'align-items:center;justify-content:center;background:{color}22;color:{color};'
                        f'font-weight:900;font-size:{int(size*0.36)}px;&quot;>{ini}</div>\'"></div>')
            return (f'<div style="width:{size}px;height:{size}px;border-radius:50%;margin:0 auto;'
                    f'border:{ring}px solid {color};box-shadow:0 0 18px {color}88;background:{color}22;'
                    f'display:flex;align-items:center;justify-content:center;color:{color};'
                    f'font-weight:900;font-size:{int(size*0.36)}px;">{ini}</div>')

        _podium_html = f"""
        <style>
        @keyframes podRise{{from{{opacity:0;transform:translateY(20px);}}to{{opacity:1;transform:translateY(0);}}}}
        @keyframes podShine{{0%,100%{{filter:drop-shadow(0 0 6px #D4AF3766);}}50%{{filter:drop-shadow(0 0 16px #D4AF37cc);}}}}
        .fw-podium{{
          display:flex;align-items:flex-end;justify-content:center;gap:10px;
          padding:24px 8px 0;margin-bottom:6px;animation:podRise .6s ease;
          max-width:560px;margin-left:auto;margin-right:auto;
        }}
        .fw-pod-col{{display:flex;flex-direction:column;align-items:center;flex:1;max-width:170px;}}
        .fw-pod-name{{font-weight:900;font-size:13px;letter-spacing:.02em;text-align:center;
          margin:8px 0 2px;line-height:1.15;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;}}
        .fw-pod-pts{{font-size:26px;font-weight:900;line-height:1;}}
        .fw-pod-lbl{{font-size:9px;letter-spacing:.18em;color:rgba(232,236,255,.4);margin-top:1px;}}
        .fw-pod-base{{width:100%;border-radius:12px 12px 0 0;display:flex;align-items:flex-start;
          justify-content:center;padding-top:10px;font-size:38px;font-weight:900;position:relative;
          box-shadow:inset 0 2px 12px rgba(255,255,255,.08);}}
        .fw-pod-crown{{font-size:28px;margin-bottom:2px;animation:podShine 2.5s ease-in-out infinite;}}
        @media (max-width:600px){{
          .fw-podium{{gap:5px;padding:16px 2px 0;}}
          .fw-pod-name{{font-size:10px;}}
          .fw-pod-pts{{font-size:19px;}}
          .fw-pod-base{{font-size:26px;}}
          .fw-pod-crown{{font-size:20px;}}
        }}
        </style>
        <div class="fw-podium">
          <!-- 2nd -->
          <div class="fw-pod-col">
            {_avatar(_f2,_c2,_ini(p2["Piloto"]),64,3)}
            <div class="fw-pod-name" style="color:{_c2};">{p2["Piloto"]}</div>
            <div class="fw-pod-pts" style="color:#e8ecff;">{_pts2}</div>
            <div class="fw-pod-lbl">PUNTOS</div>
            <div class="fw-pod-base" style="height:90px;background:linear-gradient(180deg,rgba(192,192,192,.32),rgba(192,192,192,.08));color:rgba(192,192,192,.85);">2</div>
          </div>
          <!-- 1st -->
          <div class="fw-pod-col">
            <div class="fw-pod-crown">👑</div>
            {_avatar(_f1,_c1,_ini(p1["Piloto"]),84,4)}
            <div class="fw-pod-name" style="color:{_c1};font-size:15px;">{p1["Piloto"]}</div>
            <div class="fw-pod-pts" style="color:#ffdd7a;font-size:30px;">{_pts1}</div>
            <div class="fw-pod-lbl">PUNTOS</div>
            <div class="fw-pod-base" style="height:130px;background:linear-gradient(180deg,rgba(212,175,55,.4),rgba(212,175,55,.1));color:#ffdd7a;border:1px solid rgba(212,175,55,.4);border-bottom:none;">1</div>
          </div>
          <!-- 3rd -->
          <div class="fw-pod-col">
            {_avatar(_f3,_c3,_ini(p3["Piloto"]),58,3)}
            <div class="fw-pod-name" style="color:{_c3};">{p3["Piloto"]}</div>
            <div class="fw-pod-pts" style="color:#e8ecff;">{_pts3}</div>
            <div class="fw-pod-lbl">PUNTOS</div>
            <div class="fw-pod-base" style="height:68px;background:linear-gradient(180deg,rgba(205,127,50,.32),rgba(205,127,50,.08));color:rgba(205,127,50,.9);">3</div>
          </div>
        </div>
        """
        st.markdown(_podium_html, unsafe_allow_html=True)
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        _df_disp = df.copy()
        _dns_map_disp = _dns_counts_todos()
        _df_disp["DNS"] = _df_disp["Piloto"].map(_dns_map_disp).fillna(0).astype(int)
        render_dark_table(_df_disp)

        # ── Solapa DNS — detalle de sanciones (a partir de Gran Bretaña) ──
        with st.expander("⛔ DNS — Detalle de sanciones", expanded=False):
            st.caption(f"Conteo total (incluye base histórica previa + automático desde {DNS_GP_DESDE.split('. ',1)[-1]}).")
            _df_dns_tab = pd.DataFrame({
                "Piloto": PILOTOS_TORNEO,
                "DNS": [_dns_map_disp.get(p, 0) for p in PILOTOS_TORNEO],
            }).sort_values("DNS", ascending=False).reset_index(drop=True)
            render_dark_table(_df_dns_tab)

        # ── GPs ganados reales ─────────────────────────────────────────
        @st.cache_data(ttl=120, show_spinner=False)
        def _get_hist_r():
            mr = _mod_db()
            if "_error" in mr: return pd.DataFrame()
            return _safe_call(mr["leer_historial_df"], timeout_sec=8, default=pd.DataFrame())
        dhr = _get_hist_r()
        if dhr is not None and not (hasattr(dhr,"empty") and dhr.empty) and "piloto" in dhr.columns and "puntos" in dhr.columns:
            dhr2 = dhr.copy(); dhr2["puntos"] = pd.to_numeric(dhr2["puntos"],errors="coerce").fillna(0)
            # Calcular GP ganados reales
            gps_ganados_pos = {p:0 for p in PILOTOS_TORNEO}
            try:
                _agg_p = dhr2.groupby(["gp","piloto"],as_index=False)["puntos"].sum()
                for _gp, _grp in _agg_p.groupby("gp"):
                    _gs = _grp.sort_values("puntos",ascending=False)
                    if len(_gs)>=2 and float(_gs.iloc[0]["puntos"])>0:
                        _winner = str(_gs.iloc[0]["piloto"]).strip()
                        if _winner in gps_ganados_pos: gps_ganados_pos[_winner]+=1
            except Exception: pass
            if any(v>0 for v in gps_ganados_pos.values()):
                st.markdown('<div style="margin-top:14px"></div>'
                            '<div style="font-size:10px;font-weight:700;letter-spacing:.14em;'
                            'color:rgba(246,195,73,.65);text-transform:uppercase;margin-bottom:8px;">'
                            '🏆 GPs GANADOS</div>', unsafe_allow_html=True)
                _rc2 = st.columns(len(PILOTOS_TORNEO))
                for _ri2, pil2 in enumerate(PILOTOS_TORNEO):
                    _c2 = PILOTO_COLORS.get(pil2,"#a855f7")
                    _gw2 = gps_ganados_pos.get(pil2,0)
                    with _rc2[_ri2]:
                            _tc_badge = '<div style="font-size:8px;color:#D4AF37;font-weight:800;">👑 Triple Corona</div>' if _gw2>=3 else ""
                            st.markdown(
                                f'<div style="background:{_c2}11;border:1px solid {_c2}{"44" if _gw2 else "22"};'
                                f'border-radius:12px;padding:10px 6px;text-align:center;">'
                                f'<div style="font-size:9px;font-weight:800;color:{_c2};letter-spacing:.06em;'
                                f'text-transform:uppercase;margin-bottom:4px;">{pil2.split()[0]}</div>'
                                f'<div style="font-size:22px;line-height:1;">{"🏆" if _gw2 else "—"}</div>'
                                f'<div style="font-size:12px;font-weight:900;color:#ffdd7a;margin-top:3px;">{_gw2}</div>'
                                f'{_tc_badge}'
                                f'</div>', unsafe_allow_html=True)

    # ── Liga de Campeones 2026 — auto-genera al final de temporada ─────
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="background:linear-gradient(145deg,rgba(212,175,55,.1),rgba(6,15,40,.98));\n'
        'border:2px solid rgba(212,175,55,.4);border-radius:18px;\n'
        'padding:18px 20px;text-align:center;">\n'
        '<div style="font-size:9px;letter-spacing:.2em;color:rgba(212,175,55,.5);\n'
        'text-transform:uppercase;margin-bottom:6px;">🏆 LIGA DE CAMPEONES</div>\n'
        '<div style="font-size:18px;font-weight:900;color:#D4AF37;">COPA FEFE WOLF 2026</div>\n'
        '<div style="font-size:10px;color:rgba(169,178,214,.5);margin-top:4px;">\n'
        'Premio al formulero más consistente · Se entrega al cierre del Gran Premio de Abu Dabi 2026</div>\n'
        '</div>', unsafe_allow_html=True)

    # Check if season is over (24 GPs played) to show champion
    _n_gps_played = len(df.index) if not df.empty else 0
    _total_gps = 24
    if df is not None and not df.empty and "Puntos" in df.columns:
        # Count actual GPs by looking at historial
        try:
            _mdb_liga = _mod_db()
            if "_error" not in _mdb_liga:
                _df_hist_liga = _safe_call(_mdb_liga["leer_historial_df"], timeout_sec=8, default=pd.DataFrame())
                if _df_hist_liga is not None and not _df_hist_liga.empty and "gp" in _df_hist_liga.columns:
                    _n_gps_played = _df_hist_liga["gp"].nunique()
        except Exception: pass

        _df_liga = df.sort_values("Puntos", ascending=False).reset_index(drop=True)
        if _n_gps_played >= _total_gps and not _df_liga.empty:
            # Season over — show champion
            _campeon = str(_df_liga.iloc[0]["Piloto"])
            _campeon_pts = int(_df_liga.iloc[0]["Puntos"])
            _cc_liga = PILOTO_COLORS.get(_campeon, "#D4AF37")
            _ph_liga = DRIVER_HEADSHOTS.get(_campeon, DRIVER_PHOTOS.get(_campeon,""))
            st.markdown(
                f'<div style="background:linear-gradient(135deg,{_cc_liga}22,{_cc_liga}08);\n'
                f'border:3px solid {_cc_liga};border-radius:16px;\n'
                f'padding:20px;text-align:center;margin-top:12px;">\n'
                f'<div style="font-size:36px;margin-bottom:6px;">🏆</div>\n'
                + (f'<img src="{_ph_liga}" style="width:80px;height:80px;border-radius:50%;object-fit:cover;object-position:top;border:3px solid {_cc_liga};margin-bottom:10px;">\n' if _ph_liga else "")
                + f'<div style="font-size:11px;font-weight:900;color:{_cc_liga};letter-spacing:.2em;text-transform:uppercase;">🏆 CAMPEÓN 2026</div>\n'
                f'<div style="font-size:24px;font-weight:900;color:#ffdd7a;margin:6px 0;">{_campeon}</div>\n'
                f'<div style="font-size:16px;color:#D4AF37;font-weight:900;">{_campeon_pts} puntos</div>\n'
                f'</div>', unsafe_allow_html=True)
        else:
            # Season in progress — show progress bar
            _pct_season = min(100, int(_n_gps_played / _total_gps * 100))
            _gps_rest = _total_gps - _n_gps_played
            st.markdown(
                f'<div style="margin-top:10px;padding:10px 14px;background:rgba(212,175,55,.05);\n'
                f'border:1px solid rgba(212,175,55,.15);border-radius:12px;">\n'
                f'<div style="display:flex;justify-content:space-between;margin-bottom:6px;">\n'
                f'<span style="font-size:10px;color:rgba(169,178,214,.5);">Temporada en curso</span>\n'
                f'<span style="font-size:10px;color:#D4AF37;font-weight:800;">{_n_gps_played}/{_total_gps} GPs · {_gps_rest} restantes</span>\n'
                f'</div>\n'
                f'<div style="background:rgba(255,255,255,.06);border-radius:6px;height:8px;overflow:hidden;">\n'
                f'<div style="height:100%;width:{_pct_season}%;background:linear-gradient(90deg,#3b82f6,#D4AF37);border-radius:6px;"></div>\n'
                f'</div>\n'
                f'<div style="font-size:9px;color:rgba(169,178,214,.4);margin-top:4px;text-align:center;">\n'
                f'Líder actual: <b style="color:#D4AF37;">{str(_df_liga.iloc[0]["Piloto"])} — {int(_df_liga.iloc[0]["Puntos"])} pts</b></div>\n'
                f'</div>', unsafe_allow_html=True)


def pantalla_muro():
    # Fotos de los campeones
    _checo_ph  = DRIVER_HEADSHOTS.get("Checo Perez",  DRIVER_PHOTOS.get("Checo Perez",""))
    _bottas_ph = DRIVER_HEADSHOTS.get("Valteri Bottas",DRIVER_PHOTOS.get("Valteri Bottas",""))
    _lauda_ph  = DRIVER_HEADSHOTS.get("Nicki Lauda",  DRIVER_PHOTOS.get("Nicki Lauda",""))
    # Fefe Wolf — usa IMAGENFEFE.jfif del repo si existe
    _fefe_ph = ""
    try:
        import base64 as _b64, os as _os2
        _fefe_path = "IMAGENFEFE.jfif"
        if _os2.path.exists(_fefe_path):
            with open(_fefe_path,"rb") as _ff: _fefe_ph = "data:image/jpeg;base64,"+_b64.b64encode(_ff.read()).decode()
    except: pass

    def _champ_av(ph, ini, clr, sz=70):
        if ph:
            return (f'<img src="{ph}" style="width:{sz}px;height:{sz}px;border-radius:50%;'
                    f'object-fit:cover;object-position:top;border:3px solid {clr};'
                    f'flex-shrink:0;box-shadow:0 0 18px {clr}55;">')
        return (f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{clr}22;'
                f'border:3px solid {clr};display:flex;align-items:center;justify-content:center;'
                f'font-weight:900;font-size:{sz//3}px;color:{clr};flex-shrink:0;">{ini}</div>')

    st.markdown("""
    <style>
    @keyframes hofGlow{0%,100%{box-shadow:0 0 24px rgba(212,175,55,.2),0 4px 28px rgba(0,0,0,.6);}
      50%{box-shadow:0 0 48px rgba(212,175,55,.45),0 4px 36px rgba(0,0,0,.8);}}
    @keyframes starSpin{0%{transform:rotate(0deg) scale(1);}50%{transform:rotate(12deg) scale(1.12);}
      100%{transform:rotate(0deg) scale(1);}}
    @keyframes hofEntry{from{opacity:0;transform:translateY(28px) scale(.97);}
      to{opacity:1;transform:translateY(0) scale(1);}}
    @keyframes goldShimmer2{0%{background-position:200% center;}100%{background-position:-200% center;}}
    @keyframes avGlow{0%,100%{filter:drop-shadow(0 0 8px rgba(212,175,55,.3));}
      50%{filter:drop-shadow(0 0 18px rgba(212,175,55,.6));}}
    .hof-wrap{
      background:linear-gradient(145deg,rgba(7,9,22,.99),rgba(13,18,42,.99));
      border:1.5px solid rgba(212,175,55,.45);border-radius:24px;
      padding:30px 24px 26px;margin:0 auto 20px;position:relative;overflow:hidden;
      max-width:860px;animation:hofGlow 4s ease-in-out infinite;
    }
    .hof-wrap::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;
      background:linear-gradient(90deg,transparent,#9a7a10,#d4af37,#ffe896,#d4af37,#9a7a10,transparent);}
    .hof-wrap::after{content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
      background:linear-gradient(90deg,transparent,rgba(212,175,55,.3),transparent);}
    .hof-title{font-size:32px;font-weight:900;letter-spacing:.12em;text-align:center;
      background:linear-gradient(90deg,#9a7a10,#d4af37,#ffe896,#d4af37,#9a7a10);
      background-size:200% auto;
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
      animation:goldShimmer2 4s linear infinite;margin-bottom:4px;}
    .hof-sub{text-align:center;font-size:12px;color:rgba(246,195,73,.5);
      letter-spacing:.22em;text-transform:uppercase;margin-bottom:26px;}
    .hof-entry{
      background:linear-gradient(135deg,rgba(212,175,55,.09),rgba(255,255,255,.02));
      border:1px solid rgba(212,175,55,.28);border-radius:18px;
      padding:16px 20px;margin-bottom:12px;
      display:flex;align-items:center;gap:16px;
      animation:hofEntry .6s ease both;
      transition:transform .25s ease,box-shadow .25s ease,border-color .25s;
    }
    .hof-entry:hover{transform:translateX(8px) scale(1.015);
      box-shadow:0 6px 28px rgba(212,175,55,.18);border-color:rgba(212,175,55,.55);}
    .hof-entry.tri{border-color:rgba(212,175,55,.5)!important;
      background:linear-gradient(135deg,rgba(212,175,55,.14),rgba(255,255,255,.04))!important;}
    .hof-entry:nth-child(3){animation-delay:.05s;}
    .hof-entry:nth-child(4){animation-delay:.1s;}
    .hof-entry:nth-child(5){animation-delay:.15s;}
    .hof-entry:nth-child(6){animation-delay:.2s;}
    .hof-crown{font-size:36px;flex-shrink:0;animation:starSpin 6s ease-in-out infinite;}
    .hof-av{flex-shrink:0;animation:avGlow 3s ease-in-out infinite;}
    .hof-info{flex:1;display:flex;flex-direction:column;gap:2px;}
    .hof-name{font-size:17px;font-weight:900;letter-spacing:.06em;color:#ffdd7a;}
    .hof-meta{font-size:11px;color:rgba(232,236,255,.55);letter-spacing:.04em;}
    .hof-stars{font-size:18px;letter-spacing:3px;filter:drop-shadow(0 0 5px #d4af37);margin-top:2px;}
    .hof-badge{background:linear-gradient(90deg,rgba(212,175,55,.25),rgba(212,175,55,.1));
      border:1px solid rgba(212,175,55,.5);border-radius:20px;
      padding:5px 16px;font-size:12px;font-weight:900;color:#ffdd7a;
      white-space:nowrap;flex-shrink:0;text-align:center;
      box-shadow:0 0 12px rgba(212,175,55,.15);}
    </style>
    """, unsafe_allow_html=True)

    # Build champion entries with photos
    entries = [
        (_checo_ph,  "CP", "#B026FF", "tri",  "🏆", "CHECO PEREZ",    "TriCampeón: 2022 · 2023 · 2025", "★★★", "3 TÍTULOS"),
        (_bottas_ph, "VB", "#00CFFF", "",     "🥇", "VALTERI BOTTAS", "Campeón: 2024",                   "★",   "1 TÍTULO"),
        (_fefe_ph,    "FW", "#9B59B6", "",     "🥇", "FEFE WOLF",      "Campeón: 2021",                   "★",   "1 TÍTULO"),
        (_lauda_ph,  "NL", "#1E90FF", "",     "🥇", "NICKI LAUDA",    "Campeón: 2021",                   "★",   "1 TÍTULO"),
    ]

    html = '<div class="hof-wrap"><div class="hof-title">🏆 MURO DE CAMPEONES</div>'
    html += '<div class="hof-sub">👑 Hall of Fame · Torneo Fefe Wolf</div>'
    for ph, ini, clr, extra_cls, crown, name, meta, stars, badge in entries:
        av = _champ_av(ph, ini, clr)
        html += (f'<div class="hof-entry {extra_cls}">'
                 f'<span class="hof-crown">{crown}</span>'
                 f'<div class="hof-av">{av}</div>'
                 f'<div class="hof-info">'
                 f'<div class="hof-name">{name}</div>'
                 f'<div class="hof-meta">{meta}</div>'
                 f'<div class="hof-stars">{stars}</div>'
                 f'</div>'
                 f'<div class="hof-badge">{badge}</div>'
                 f'</div>')
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

    # Honor phrase
    st.markdown(
        '<div style="text-align:center;margin:24px 0 8px;padding:16px;">'
        '<div style="font-size:13px;color:rgba(212,175,55,.6);font-style:italic;line-height:1.8;">'
        '"Pocos tienen el honor de llegar aquí.<br>'
        'Este muro no se construye con suerte,<br>'
        'se construye con pasión, dedicación y amor por la Fórmula 1."</div>'
        '<div style="font-size:10px;color:rgba(169,178,214,.3);margin-top:8px;letter-spacing:.15em;">'
        '— TORNEO FEFE WOLF · DESDE 2021</div>'
        '</div>', unsafe_allow_html=True)

def pantalla_historial_gp():
    usuario = (st.session_state.get("perfil") or {}).get("usuario","")  # FIX: define usuario
    st.markdown('<div class="section-title">📈 HISTORIAL POR GRAN PREMIO</div>', unsafe_allow_html=True)
    st.markdown('<div id="top"></div>', unsafe_allow_html=True)
    if st.button("🔄 Actualizar historial", key="btn_ref_historial"):
        st.cache_data.clear(); st.rerun()

    @st.cache_data(ttl=60, show_spinner="Cargando historial…")
    def _get():
        m = _mod_db()
        if "_error" in m: return pd.DataFrame(), pd.DataFrame()
        h = _safe_call(m["leer_historial_df"], timeout_sec=8, default=pd.DataFrame())
        d = _safe_call(m["leer_historial_detalle_df"], timeout_sec=8, default=pd.DataFrame())
        return h, d

    df_hist, df_det = _get()
    if df_hist is None or (hasattr(df_hist,"empty") and df_hist.empty):
        st.markdown("""<div class="card fade-up" style="text-align:center;padding:40px;">
          <div style="font-size:56px;">🏎️</div>
          <div style="font-weight:900;font-size:20px;color:#ffdd7a;">La temporada 2026 está por comenzar</div>
          <div style="color:rgba(232,236,255,.65);margin-top:10px;font-size:14px;">
            El historial se activa tras el primer cómputo oficial.</div></div>""",
            unsafe_allow_html=True)
        return

    df_hist=df_hist.copy(); df_hist.columns=[c.lower().strip() for c in df_hist.columns]
    df_hist["puntos"]=pd.to_numeric(df_hist["puntos"],errors="coerce").fillna(0).astype(int)
    df_hist["gp"]=df_hist["gp"].astype(str).str.strip()
    df_hist["piloto"]=df_hist["piloto"].astype(str).str.strip()
    df_hist=df_hist.groupby(["gp","piloto"],as_index=False)["puntos"].sum()
    # ── Filtrar GPs donde TODOS tienen 0 pts (son entradas vacías/erróneas) ──
    # OJO: antes se comparaba la SUMA del GP > 0, lo cual descartaba GPs enteros
    # y válidos cuando las sanciones DNS (negativas) hacían que el total diera
    # 0 o negativo. Ahora solo se descarta si TODAS las filas del GP son 0.
    _gp_tiene_datos = df_hist.groupby("gp")["puntos"].apply(lambda s: (s != 0).any())
    _gps_validos = _gp_tiene_datos[_gp_tiene_datos].index.tolist()
    if _gps_validos:
        df_hist = df_hist[df_hist["gp"].isin(_gps_validos)]

    # ── Sección DNS — resumen de sanciones (base histórica + automático desde GB) ──
    with st.expander("⛔ DNS — Sanciones del campeonato", expanded=False):
        _dns_map_hist = _dns_counts_todos()
        _df_dns_hist = pd.DataFrame({
            "Piloto": PILOTOS_TORNEO,
            "DNS": [_dns_map_hist.get(p, 0) for p in PILOTOS_TORNEO],
        }).sort_values("DNS", ascending=False).reset_index(drop=True)
        render_dark_table(_df_dns_hist)
        if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
            try:
                _dd = df_det.copy()
                _dd.columns = [str(c).lower().strip() for c in _dd.columns]
                if {"piloto","etapa","gp"}.issubset(_dd.columns):
                    _dd_dns_rows = _dd[_dd["etapa"].astype(str).str.upper()=="DNS"]
                    if not _dd_dns_rows.empty:
                        st.caption("Detalle de sanciones aplicadas por GP:")
                        st.dataframe(_dd_dns_rows[["gp","piloto"]].reset_index(drop=True),
                                     use_container_width=True)
            except Exception:
                pass
    gp_ord={g:i for i,g in enumerate(GPS_OFICIALES)}
    df_hist["_ord"]=df_hist["gp"].map(gp_ord).fillna(99)
    df_hist=df_hist.sort_values(["_ord","piloto"]).drop(columns="_ord")
    gps_j=[g for g in GPS_OFICIALES if g in df_hist["gp"].values]
    if not gps_j:
        gps_j = sorted(df_hist["gp"].unique().tolist())
    short={g:g.split(". ",1)[-1].strip() if ". " in g else g for g in GPS_OFICIALES}

    _hcol1, _hcol2, _hcol3, _hcol4 = st.columns([2,1,1,1])
    with _hcol2:
        if st.button("🔄 Actualizar", key="hist_refresh", use_container_width=True):
            _get.clear(); st.rerun()
    with _hcol3:
        # Export to Excel
        try:
            import io as _io
            _buf = _io.BytesIO()
            with pd.ExcelWriter(_buf, engine="xlsxwriter") as _xw:
                df_hist.to_excel(_xw, sheet_name="Historial", index=False)
                if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
                    df_det.to_excel(_xw, sheet_name="Detalle", index=False)
            _buf.seek(0)
            st.download_button("📊 Excel", _buf.getvalue(),
                               file_name="torneo_fefe_wolf_2026.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               use_container_width=True, key="dl_excel_hist")
        except Exception: pass
    with _hcol4:
        # WA share for past GPs
        with st.popover("📲 Compartir"):
            st.markdown("**📲 Compartir resumen**")
            _gps_hist_wa = gps_j[-4:] if len(gps_j) >= 4 else gps_j
            _wa_gp_sel = st.selectbox("GP", _gps_hist_wa,
                                      format_func=lambda x: x.split(". ",1)[-1] if ". " in x else x,
                                      key="wa_hist_gp_sel")
            if _wa_gp_sel and st.button("📲 Generar link WA", key="wa_hist_gen", use_container_width=True):
                import urllib.parse as _up_h2, re as _re_h2
                _gp_lbl_wa = _re_h2.sub(r'^\d+\.\s*','',_wa_gp_sel).strip()
                _dgp = df_hist[df_hist["gp"]==_wa_gp_sel].sort_values("puntos",ascending=False).reset_index(drop=True)
                _MED3={0:"🥇",1:"🥈",2:"🥉",3:"4°",4:"5°"}
                _FLAGS3={"Australia":"🇦🇺","China":"🇨🇳","Japón":"🇯🇵","Miami":"🇺🇸","Canadá":"🇨🇦",
                         "Mónaco":"🇲🇨","España":"🇪🇸","Austria":"🇦🇹","Gran Bretaña":"🇬🇧","Italia":"🇮🇹"}
                _fl3=next((v for k,v in _FLAGS3.items() if k.lower() in _gp_lbl_wa.lower()),"🏁")
                _ddet_h = pd.DataFrame()
                if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
                    try:
                        _ddet_h = df_det.copy()
                        _ddet_h.columns=[c.lower().strip() for c in _ddet_h.columns]
                        _ddet_h["puntos"]=pd.to_numeric(_ddet_h["puntos"],errors="coerce").fillna(0)
                        _ddet_h=_ddet_h[_ddet_h.get("gp",pd.Series(dtype=str)).astype(str)==_wa_gp_sel]
                    except Exception: _ddet_h=pd.DataFrame()
                _lines=[f"🏎️ *TORNEO FEFE WOLF 2026*",
                        f"{_fl3} *{_gp_lbl_wa.upper()}* — RESULTADOS","━━━━━━━━━━━━━━━━━━━━━━"]
                for _ri,_rr in _dgp.iterrows():
                    _det=""
                    if not _ddet_h.empty and "piloto" in _ddet_h.columns:
                        _p2=_ddet_h[_ddet_h["piloto"]==_rr["piloto"]]
                        _pts=[]
                        for _et,_short in [("QUALY","Q"),("SPRINT","Spr"),("CARRERA","C"),("CONSTRUCTORES","Const")]:
                            _s2=_p2[_p2.get("etapa",pd.Series(dtype=str)).str.upper()==_et]
                            if not _s2.empty and _s2["puntos"].sum()>0:
                                _pts.append(f"{_short}:{int(_s2['puntos'].sum())}")
                        if _pts: _det=f" _({' · '.join(_pts)})_"
                    _lines.append(f"{_MED3.get(_ri,str(_ri+1)+'°')} *{_rr['piloto']}*: {int(_rr['puntos'])} pts{_det}")
                _lines+=["━━━━━━━━━━━━━━━━━━━━━━","🏁 _torneofefewolf2026.streamlit.app_"]
                _url_h=f"https://wa.me/?text={_up_h2.quote(chr(10).join(_lines))}"
                st.markdown(f'<a href="{_url_h}" target="_blank" style="display:block;text-align:center;'
                            f'background:linear-gradient(135deg,#075e54,#25d366);color:#fff;font-weight:800;'
                            f'font-size:13px;padding:10px;border-radius:12px;text-decoration:none;">'
                            f'📲 Abrir WhatsApp</a>', unsafe_allow_html=True)

    tab_evo,tab_gp,tab_pers,tab_stats,tab_tl,tab_analisis,tab_records,tab_col=st.tabs([
        "📉 Evolución","🏁 Por GP","👤 Personal","🏅 Stats","📅 Timeline","📊 Análisis",
        "🏅 Récords","🇦🇷 Colapinto"
    ])

    with tab_evo:
        pivot=df_hist.pivot_table(index="gp",columns="piloto",values="puntos",fill_value=0)
        pivot=pivot.reindex([g for g in GPS_OFICIALES if g in pivot.index])
        cumdf = pivot.cumsum()
        short_idx = [short.get(g,g) for g in cumdf.index]

        # ── SIMULACIÓN DE CARRERA ANIMADA ─────────────────────
        import json as _json

        gps_disp = short_idx
        if not gps_disp:
            st.info("Sin datos de evolución aún.")
        else:
            gp_sel_evo = st.selectbox(
                "📍 Ver acumulado hasta:",
                gps_disp, index=len(gps_disp)-1, key="evo_gp_selector"
            )
            idx_fin    = gps_disp.index(gp_sel_evo)
            race_data  = {}
            for pil in cumdf.columns:
                race_data[pil] = [int(v) for v in cumdf[pil].values[:idx_fin+1]]
            race_rounds = gps_disp[:idx_fin+1]
            race_colors = {p: PILOTO_COLORS.get(p, "#a855f7") for p in cumdf.columns}

            # ── LINE CHART — evolución acumulada por piloto ────────────
            if _PLOTLY_OK:
                try:
                    import plotly.graph_objects as _pgo
                    _fig_line = _pgo.Figure()
                    _all_rounds_disp = gps_disp[:idx_fin+1]  # full list up to selection
                    for pil in cumdf.columns:
                        _yvals = [int(v) for v in cumdf[pil].values[:idx_fin+1]]
                        _color = PILOTO_COLORS.get(pil, "#a855f7")
                        _fig_line.add_trace(_pgo.Scatter(
                            x=_all_rounds_disp,
                            y=_yvals,
                            mode="markers+text" if len(_all_rounds_disp)==1 else "lines+markers+text",
                            name=pil,
                            line=dict(color=_color, width=3, shape="linear"),
                            marker=dict(color=_color, size=9, symbol="circle",
                                        line=dict(color="#070918", width=1.5)),
                            text=[None]*(len(_yvals)-1) + [f"  <b>{_yvals[-1]}</b>"],
                            textposition="middle right",
                            textfont=dict(color=_color, size=11),
                        ))
                    _fig_line.update_layout(
                        height=max(320, 300),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(5,7,18,.97)",
                        margin=dict(l=10, r=90, t=46, b=60),
                        title=dict(
                            text=f"📈 Evolución acumulada hasta {gp_sel_evo}",
                            font=dict(color="#ffdd7a", size=13, family="Inter"),
                            x=0.5, xanchor="center"
                        ),
                        xaxis=dict(
                            tickfont=dict(color="#a9b2d6", size=9),
                            tickangle=-30,
                            showgrid=True,
                            gridcolor="rgba(246,195,73,.06)",
                            zeroline=False,
                            showline=True,
                            linecolor="rgba(255,255,255,.1)",
                        ),
                        yaxis=dict(
                            tickfont=dict(color="#a9b2d6", size=10),
                            showgrid=True,
                            gridcolor="rgba(255,255,255,.05)",
                            zeroline=False,
                        ),
                        legend=dict(
                            font=dict(color="#e8ecff", size=10),
                            bgcolor="rgba(5,7,18,.8)",
                            bordercolor="rgba(246,195,73,.2)",
                            borderwidth=1,
                            x=1.01, y=1, xanchor="left",
                        ),
                        hovermode="x unified",
                    )
                    st.plotly_chart(_fig_line, use_container_width=True,
                        config={"displayModeBar": False, "staticPlot": True})
                except Exception as _ex:
                    st.warning(f"Gráfico: {_ex}")
            else:
                st.info("Gráfico no disponible.")


            cd=pivot.cumsum().copy(); cd.index=cd.index.map(short); cd.index.name="GP"
            st.markdown(cd.to_html(classes="tabla_historial_dark", border=0), unsafe_allow_html=True)

    with tab_gp:
        _short_cap = short.copy()  # capture for lambda
        # Mostrar todos los GPs que tienen datos, incluso si no matchean exacto con GPS_OFICIALES
        _all_gps_hist = sorted(df_hist["gp"].unique().tolist(),
                               key=lambda g: gp_ord.get(g, 99))
        _gps_show = gps_j if gps_j else _all_gps_hist
        gp_sel=st.selectbox("GP:",_gps_show,key="hist_gp_sel",
                            format_func=lambda x,s=_short_cap:s.get(x, x.split(". ",1)[-1] if ". " in x else x))
        df_gp=df_hist[df_hist["gp"]==gp_sel].sort_values("puntos",ascending=False).reset_index(drop=True)
        if df_gp.empty: st.warning("Sin datos.")
        else:
            gan=df_gp.iloc[0]; cg=PILOTO_COLORS.get(gan["piloto"],"#D4AF37")
            st.markdown(f'<div class="card fade-up" style="text-align:center;border-color:{cg}55;padding:22px;"><div style="font-size:38px;">🏆</div><div style="font-weight:900;font-size:18px;color:{cg};">Ganador: {gan["piloto"]}</div><div style="font-size:32px;font-weight:900;color:#ffdd7a;">{gan["puntos"]} pts</div></div>',unsafe_allow_html=True)
            ds=df_gp[["piloto","puntos"]].rename(columns={"piloto":"Piloto","puntos":"Puntos"}); ds.index=range(1,len(ds)+1)
            st.markdown(ds.to_html(classes="tabla_historial_dark", border=0), unsafe_allow_html=True)
            if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
                ddt=df_det.copy(); ddt.columns=[c.lower().strip() for c in ddt.columns]
                ddt=ddt[ddt["gp"]==gp_sel]
                if not ddt.empty:
                    # Pivot and clean columns
                    pv=ddt.pivot_table(index="piloto",columns="etapa",values="puntos",fill_value=0,aggfunc="sum").reset_index()
                    pv.columns.name = None
                    pv.columns = [str(c).upper() if c != "piloto" else "Piloto" for c in pv.columns]
                    # Define standard columns (exclude CARRERA_CONST)
                    _cols_want = ["Piloto","QUALY","SPRINT","CARRERA","CONSTRUCTORES"]
                    for _c in _cols_want:
                        if _c not in pv.columns: pv[_c] = 0
                    # Filter only the wanted cols that exist
                    _cols_show = [c for c in _cols_want if c in pv.columns]
                    pv = pv[_cols_show].copy()
                    # Sprint: if all zeros, show "No hubo"
                    _es_sprint_gp = gp_sel in GPS_SPRINT
                    if not _es_sprint_gp:
                        pv["SPRINT"] = "No hubo"
                    # Total column (includes DNS)
                    _num_cols = []
                    for _c in _cols_show:
                        if _c == "Piloto": continue
                        try:
                            pd.to_numeric(pv[_c], errors="raise")
                            _num_cols.append(_c)
                        except Exception: pass
                    pv["TOTAL"] = pv[_num_cols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1).astype(int)
                    # Subtract DNS — rows with 0 pts treated as -5, display DNS label
                    _dns_etapas = [str(x).upper() for x in ddt["etapa"].unique()]
                    if "DNS" in _dns_etapas:
                        _dns_sub = ddt[ddt["etapa"].str.upper()=="DNS"][["piloto","puntos"]].copy()
                        _dns_sub["puntos"] = pd.to_numeric(_dns_sub["puntos"],errors="coerce").fillna(0).astype(int)
                        _dns_sub["puntos"] = _dns_sub["puntos"].apply(lambda x: -5 if x == 0 else x)
                        _dns_sub = _dns_sub.groupby("piloto")["puntos"].sum().reset_index()
                        _dns_sub.columns = ["Piloto","_dns_pen"]
                        pv = pv.merge(_dns_sub, on="Piloto", how="left")
                        pv["_dns_pen"] = pv["_dns_pen"].fillna(0).astype(int)
                        pv["DNS"] = pv["_dns_pen"].apply(
                            lambda x: f"DNS ({x})" if x != 0 else "—")
                        pv["TOTAL"] = (pv["TOTAL"] + pv["_dns_pen"]).astype(int)
                        pv = pv.drop(columns=["_dns_pen"])
                    # Style: highlight top scorer
                    _col_map = {"Piloto":"Piloto","QUALY":"Qualy","SPRINT":"Sprint","CARRERA":"Carrera","CONSTRUCTORES":"Constructores","TOTAL":"⚡ TOTAL"}
                    pv = pv.rename(columns=_col_map)
                    # Sort by total desc
                    if "⚡ TOTAL" in pv.columns:
                        _num_mask = pd.to_numeric(pv["⚡ TOTAL"], errors="coerce").notna()
                        pv = pv.sort_values("⚡ TOTAL", ascending=False).reset_index(drop=True)
                    st.markdown(pv.to_html(classes="tabla_historial_dark", border=0, index=False), unsafe_allow_html=True)
            df_gp["Color"]=df_gp["piloto"].map(PILOTO_COLORS).fillna("#a855f7")
            if _PLOTLY_OK:
                try:
                    fig2 = go.Figure(go.Bar(
                        x=df_gp["piloto"], y=df_gp["puntos"],
                        marker_color=df_gp["Color"].tolist(),
                        text=df_gp["puntos"], textposition="outside",
                        textfont=dict(color="#ffdd7a", size=13),
                        cliponaxis=False,
                    ))
                    _ymax_gp = int(df_gp["puntos"].max()) if not df_gp.empty else 10
                    fig2.update_layout(
                        height=270, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=10,r=10,t=48,b=10), showlegend=False,
                        xaxis=dict(tickfont=dict(color="#e8ecff",size=12), showgrid=False),
                        yaxis=dict(tickfont=dict(color="#a9b2d6",size=11), showgrid=True,
                                   gridcolor="rgba(246,195,73,0.08)", zeroline=False,
                                   range=[0, _ymax_gp * 1.25]),
                    )
                    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False, "staticPlot": True})
                except Exception:
                    pass

    with tab_pers:
        usr_d=(st.session_state.get("perfil") or {}).get("usuario","")
        opc=[p for p in PILOTOS_TORNEO if p in df_hist["piloto"].values] or PILOTOS_TORNEO
        idx=opc.index(usr_d) if usr_d in opc else 0
        pil=st.selectbox("Piloto:",opc,index=idx,key="hist_pers")
        cp=PILOTO_COLORS.get(pil,"#a855f7")
        df_p=df_hist[df_hist["piloto"]==pil].copy()
        df_p["gp_s"]=df_p["gp"].map(short).fillna(df_p["gp"]); df_p["acum"]=df_p["puntos"].cumsum()
        total=int(df_p["puntos"].sum()); prom=int(df_p["puntos"].mean()) if not df_p.empty else 0
        mejor=df_p.loc[df_p["puntos"].idxmax()] if not df_p.empty else None
        peor=df_p.loc[df_p["puntos"].idxmin()]  if not df_p.empty else None
        def _sc(col,lbl,val,sub="",c="#ffdd7a"):
            with col: st.markdown(f'<div class="card fade-up" style="text-align:center;padding:12px 8px;"><div style="font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:rgba(169,178,214,.80);margin-bottom:4px;">{lbl}</div><div style="font-size:24px;font-weight:900;color:{c};">{val}</div><div style="font-size:10px;color:rgba(169,178,214,.55);">{sub}</div></div>',unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns(4)
        _sc(c1,"Total Pts",total,f"{len(df_p)} GPs",cp)
        _sc(c2,"Promedio",prom,"pts/GP")
        _sc(c3,"Mejor GP",int(mejor["puntos"]) if mejor is not None else "-",mejor["gp_s"] if mejor is not None else "","#22c55e")
        _sc(c4,"Peor GP", int(peor["puntos"])  if peor  is not None else "-",peor["gp_s"]  if peor  is not None else "","#ef4444")
        if not df_p.empty and _PLOTLY_OK:
            try:
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=df_p["gp_s"].tolist(), y=df_p["puntos"].tolist(),
                    mode="lines+markers", name="GP",
                    line=dict(color=cp, width=2.5),
                    marker=dict(color=cp, size=7),
                ))
                fig3.add_trace(go.Scatter(
                    x=df_p["gp_s"].tolist(), y=df_p["acum"].tolist(),
                    mode="lines+markers", name="Acum.",
                    line=dict(color="#ffdd7a", width=2.5, dash="dot"),
                    marker=dict(color="#ffdd7a", size=6),
                ))
                fig3.update_layout(
                    height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10,r=10,t=10,b=60),
                    xaxis=dict(tickfont=dict(color="#a9b2d6",size=11), tickangle=-42,
                               showgrid=False, zeroline=False),
                    yaxis=dict(tickfont=dict(color="#a9b2d6",size=11),
                               title=dict(text="Puntos", font=dict(color="#ffdd7a")),
                               showgrid=True, gridcolor="rgba(246,195,73,0.08)", zeroline=False),
                    legend=dict(font=dict(color="#e8ecff"), bgcolor="rgba(0,0,0,0.3)"),
                )
                st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False, "staticPlot": True})
            except Exception:
                pass

    with tab_stats:
        mn=df_hist.groupby("piloto")["puntos"].mean().reset_index().sort_values("puntos",ascending=False)
        mx=df_hist.groupby("piloto")["puntos"].max().reset_index().sort_values("puntos",ascending=False)
        wr_l=[grp.loc[grp["puntos"].idxmax(),"piloto"] for _,grp in df_hist.groupby("gp")]
        wr=pd.Series(wr_l).value_counts().reset_index(); wr.columns=["Piloto","Victorias"]
        def _sl(col,ttl,df_in,vc,fmt):
            with col:
                st.markdown(f"#### {ttl}")
                for _,row in df_in.iterrows():
                    pk="piloto" if "piloto" in row else "Piloto"; c=PILOTO_COLORS.get(row[pk],"#a855f7"); v=row[vc]
                    vf=f"{v:.1f}" if isinstance(v,float) and fmt=="f" else str(int(v) if isinstance(v,float) else v)
                    st.markdown(f'<div style="display:flex;justify-content:space-between;padding:8px 12px;border-radius:10px;margin:4px 0;background:rgba(255,255,255,.04);border:1px solid {c}33;"><span style="color:{c};font-weight:700;">{row[pk]}</span><span style="color:#ffdd7a;font-weight:900;">{vf}</span></div>',unsafe_allow_html=True)
        cA,cB,cC=st.columns(3)
        _sl(cA,"🎯 Promedio/GP",mn,"puntos","f")
        _sl(cB,"🚀 Máximo GP",  mx,"puntos","i")
        with cC:
            st.markdown("#### 🏆 GPs ganados")
            for _,row in wr.iterrows():
                c=PILOTO_COLORS.get(row["Piloto"],"#a855f7")
                st.markdown(f'<div style="display:flex;justify-content:space-between;padding:8px 12px;border-radius:10px;margin:4px 0;background:rgba(255,255,255,.04);border:1px solid {c}33;"><span style="color:{c};font-weight:700;">{row["Piloto"]}</span><span style="color:#ffdd7a;font-weight:900;">{row["Victorias"]} 🏆</span></div>',unsafe_allow_html=True)

        # ── Predicciones más acertadas ──────────────────────────────
        if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
            try:
                _dd_acc = df_det.copy(); _dd_acc.columns=[c.lower().strip() for c in _dd_acc.columns]
                _dd_acc["puntos"]=pd.to_numeric(_dd_acc["puntos"],errors="coerce").fillna(0)
                _acc_pcts = {}
                for _pil_a in PILOTOS_TORNEO:
                    _pd_a = _dd_acc[_dd_acc.get("piloto",pd.Series(dtype=str)).astype(str)==_pil_a]
                    if not _pd_a.empty and "etapa" in _pd_a.columns:
                        _et_up = _pd_a["etapa"].astype(str).str.upper()
                        def _safe_mean(_mask):
                            _vals = _pd_a[_mask]["puntos"]
                            return round(float(_vals.mean()),1) if len(_vals)>0 else 0.0
                        _q_a = _safe_mean(_et_up=="QUALY")
                        _c_a = _safe_mean(_et_up=="CARRERA")
                        _s_a = _safe_mean(_et_up=="SPRINT")
                        # Solo incluir si tiene al menos una predicción
                        if (_pd_a["puntos"].notna().any()):
                            _acc_pcts[_pil_a] = {"Qualy":_q_a,"Carrera":_c_a,"Sprint":_s_a}
                if _acc_pcts:
                    st.markdown('<div style="margin-top:18px;font-size:10px;font-weight:700;'
                                'color:rgba(246,195,73,.6);text-transform:uppercase;letter-spacing:.1em;'
                                'margin-bottom:8px;">📐 Promedio de pts por etapa</div>', unsafe_allow_html=True)
                    _acc_sorted = sorted(_acc_pcts.items(), key=lambda x: x[1].get("Carrera",0)+x[1].get("Qualy",0), reverse=True)
                    for _pil_acc, _v_acc in _acc_sorted:
                        _c_acc = PILOTO_COLORS.get(_pil_acc,"#a855f7")
                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:8px;'
                            f'background:{_c_acc}11;border:1px solid {_c_acc}33;'
                            f'border-radius:10px;padding:7px 12px;margin-bottom:5px;">'
                            f'<span style="font-size:12px;font-weight:900;color:{_c_acc};flex:1;">{_pil_acc}</span>'
                            f'<span style="font-size:10px;color:rgba(169,178,214,.6);background:rgba(255,255,255,.05);'
                            f'border-radius:6px;padding:2px 7px;">⏱️ {_v_acc.get("Qualy",0)} Q</span>'
                            f'<span style="font-size:10px;color:rgba(169,178,214,.6);background:rgba(255,255,255,.05);'
                            f'border-radius:6px;padding:2px 7px;">🏁 {_v_acc.get("Carrera",0)} C</span>'
                            + (f'<span style="font-size:10px;color:rgba(169,178,214,.6);background:rgba(255,255,255,.05);'
                               f'border-radius:6px;padding:2px 7px;">⚡ {_v_acc.get("Sprint",0)} S</span>'
                               if _v_acc.get("Sprint",0) > 0 else '') +
                            f'</div>', unsafe_allow_html=True)
            except Exception: pass

        st.markdown('<a href="#top" class="flecha_subir_dorada">↑</a>', unsafe_allow_html=True)

    with tab_tl:
        st.markdown("""<style>
        .tl-wrap{position:relative;padding-left:24px;margin-top:8px;}
        .tl-line{position:absolute;left:10px;top:0;bottom:0;width:2px;
          background:linear-gradient(to bottom,rgba(212,175,55,.6),rgba(212,175,55,.1));}
        .tl-item{position:relative;margin-bottom:16px;padding-left:20px;}
        .tl-dot{position:absolute;left:-19px;top:12px;width:14px;height:14px;border-radius:50%;
          border:2px solid rgba(212,175,55,.7);background:#07091a;
          box-shadow:0 0 8px rgba(212,175,55,.4);}
        .tl-card{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);
          border-radius:14px;padding:14px 16px;transition:border-color .2s;}
        .tl-card:hover{border-color:rgba(212,175,55,.35);}
        .tl-gp-name{font-size:14px;font-weight:900;color:#ffdd7a;margin-bottom:6px;}
        .tl-winner{font-size:11px;color:rgba(232,236,255,.7);}
        .tl-pts-row{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px;}
        .tl-pts-chip{border-radius:8px;padding:3px 9px;font-size:11px;font-weight:700;}
        </style>""", unsafe_allow_html=True)

        st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:.14em;'
                    'color:rgba(246,195,73,.65);text-transform:uppercase;margin-bottom:12px;">'
                    '📅 TEMPORADA 2026 — TIMELINE</div>', unsafe_allow_html=True)

        gps_done = [g for g in GPS_OFICIALES if g in df_hist["gp"].values]
        if not gps_done:
            st.info("Aún no hay GPs completados.")
        else:
            # Incorporar DNS del detalle al total mostrado en cronología
            # NOTA: Las filas DNS en HistorialDetalle tienen puntos vacío/0 → asumir -5 por etapa
            _dns_offset = {}
            if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
                try:
                    _ddet2 = df_det.copy(); _ddet2.columns=[c.lower().strip() for c in _ddet2.columns]
                    _ddet2["puntos"]=pd.to_numeric(_ddet2["puntos"],errors="coerce").fillna(0).astype(int)
                    if "etapa" in _ddet2.columns:
                        _dns_rows = _ddet2[_ddet2["etapa"].str.upper()=="DNS"]
                        for _, _dr in _dns_rows.iterrows():
                            _gk = str(_dr.get("gp","")).strip()
                            _pk = str(_dr.get("piloto","")).strip()
                            _pts_dns = int(_dr["puntos"])
                            # Si la fila DNS tiene 0 o vacío, usar -5 por defecto
                            if _pts_dns == 0: _pts_dns = -5
                            _dns_offset.setdefault(_gk,{})
                            _dns_offset[_gk][_pk] = _dns_offset[_gk].get(_pk,0) + _pts_dns
                except Exception: pass

            tl_html = '<div class="tl-wrap"><div class="tl-line"></div>'
            for gp in gps_done:
                dg = df_hist[df_hist["gp"]==gp].copy().sort_values("puntos",ascending=False)
                gp_label = gp.split(". ",1)[-1] if ". " in gp else gp
                # Apply DNS offset to display
                _gp_dns = _dns_offset.get(gp, {})
                dg["puntos_display"] = dg.apply(
                    lambda r: int(r["puntos"]) + int(_gp_dns.get(r["piloto"],0)), axis=1)
                dg = dg.sort_values("puntos_display",ascending=False)
                winner = dg.iloc[0]["piloto"] if not dg.empty else "—"
                max_pts = int(dg.iloc[0]["puntos_display"]) if not dg.empty else 0
                wclr = PILOTO_COLORS.get(winner,"#a855f7")

                chips = ""
                for _, row in dg.iterrows():
                    clr_c = PILOTO_COLORS.get(row["piloto"],"#666")
                    _dns_pts = int(_gp_dns.get(row["piloto"],0))
                    _dns_lbl = f" (DNS:{_dns_pts})" if _dns_pts < 0 else ""
                    chips += (f'<span class="tl-pts-chip" style="background:{clr_c}18;'
                              f'border:1px solid {clr_c}44;color:{clr_c};">'
                              f'{row["piloto"].split()[0]}: {int(row["puntos_display"])}{_dns_lbl}</span>')

                tl_html += (f'<div class="tl-item">'
                            f'<div class="tl-dot" style="border-color:{wclr};box-shadow:0 0 8px {wclr}66;"></div>'
                            f'<div class="tl-card">'
                            f'<div class="tl-gp-name">🏁 {gp_label}</div>'
                            f'<div class="tl-winner">👑 <b style="color:{wclr};">{winner}</b> — {max_pts} pts</div>'
                            f'<div class="tl-pts-row">{chips}</div>'
                            f'</div></div>')
            tl_html += '</div>'
            st.markdown(tl_html, unsafe_allow_html=True)

    with tab_analisis:
        st.markdown("""<style>
        .ana-hero{background:linear-gradient(145deg,rgba(7,9,22,.99),rgba(20,14,50,.99));
          border:1.5px solid rgba(99,102,241,.4);border-radius:18px;padding:18px 20px 14px;
          margin-bottom:16px;text-align:center;}
        .ana-title{font-size:18px;font-weight:900;color:#a78bfa;letter-spacing:.06em;}
        .ana-sub{font-size:10px;color:rgba(169,178,214,.5);letter-spacing:.12em;margin-top:3px;}
        .ana-card{background:rgba(99,102,241,.06);border:1px solid rgba(99,102,241,.2);
          border-radius:14px;padding:14px 16px;margin-bottom:12px;}
        .ana-cat{font-size:11px;font-weight:800;color:#a78bfa;letter-spacing:.1em;
          text-transform:uppercase;margin-bottom:10px;}
        .ana-bar-row{display:flex;align-items:center;gap:8px;margin-bottom:6px;}
        .ana-pilot-lbl{font-size:11px;color:#e8ecff;min-width:90px;}
        .ana-bar-w{flex:1;height:8px;background:rgba(255,255,255,.06);border-radius:4px;overflow:hidden;}
        .ana-pct-lbl{font-size:11px;font-weight:700;color:#a78bfa;min-width:34px;text-align:right;}
        </style>""", unsafe_allow_html=True)
        st.markdown('<div class="ana-hero">'
                    '<div class="ana-title">📊 ANÁLISIS TEMPORADA 2026</div>'
                    '<div class="ana-sub">Rendimiento acumulado por Formulero y GP</div>'
                    '</div>', unsafe_allow_html=True)

        if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
            _dd = df_det.copy(); _dd.columns=[c.lower().strip() for c in _dd.columns]
            _dd["puntos"]=pd.to_numeric(_dd["puntos"],errors="coerce").fillna(0).astype(int)
            # Excluir DNS y BONUS del análisis de rendimiento (son penalizaciones/extras, no puntos de predicción)
            _ETAPAS_EXCLUIR = {"DNS","BONUS_CHAMP_PILOTO","BONUS_CHAMP_CONST"}
            if "etapa" in _dd.columns:
                _dd_ana = _dd[~_dd["etapa"].str.upper().isin(_ETAPAS_EXCLUIR)].copy()
            else:
                _dd_ana = _dd.copy()

            # ── Top rendimiento por etapa ──────────────────────────────
            for _et, _et_lbl in [("QUALY","⏱️ Clasificación"),("CARRERA","🏁 Carrera"),
                                   ("CONSTRUCTORES","🛠️ Constructores"),("SPRINT","⚡ Sprint")]:
                _sub = _dd_ana[_dd_ana.get("etapa",pd.Series(dtype=str)).str.upper()==_et] if "etapa" in _dd_ana.columns else pd.DataFrame()
                if _sub.empty: continue
                _agg = _sub.groupby("piloto")["puntos"].sum().sort_values(ascending=False)
                if _agg.empty or _agg.max()==0: continue
                _total = max(_agg.sum(),1)
                st.markdown(f'<div class="ana-card"><div class="ana-cat">{_et_lbl} — Puntos acumulados</div>', unsafe_allow_html=True)
                _rows=""
                for _pil,_pts in _agg.items():
                    _pct=_pts/_total*100; _clr=PILOTO_COLORS.get(_pil,"#6366f1")
                    _rows+=(f'<div class="ana-bar-row">'
                            f'<span class="ana-pilot-lbl" style="color:{_clr};font-weight:700;">{_pil.split()[0]}</span>'
                            f'<div class="ana-bar-w"><div style="width:{_pct:.0f}%;height:100%;background:{_clr};border-radius:4px;box-shadow:0 0 5px {_clr}55;"></div></div>'
                            f'<span class="ana-pct-lbl">{_pts}pts</span>'
                            f'</div>')
                st.markdown(_rows+'</div>', unsafe_allow_html=True)

            # ── Tabla resumen por GP (usa historial total, no detalle) ───────
            if df_hist is not None and not (hasattr(df_hist,"empty") and df_hist.empty):
                try:
                    _agg_total = df_hist.copy()
                    _agg_total.columns = [c.lower().strip() for c in _agg_total.columns]
                    _agg_total["puntos"] = pd.to_numeric(_agg_total["puntos"],errors="coerce").fillna(0)
                    _agg_total["gp"] = _agg_total["gp"].astype(str).str.strip()
                    _agg_total = _agg_total.groupby(["gp","piloto"],as_index=False)["puntos"].sum()
                    # Apply DNS corrections from df_det
                    if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
                        try:
                            _dd_dns = df_det.copy(); _dd_dns.columns=[c.lower().strip() for c in _dd_dns.columns]
                            _dd_dns["puntos"]=pd.to_numeric(_dd_dns["puntos"],errors="coerce").fillna(0).astype(int)
                            if "etapa" in _dd_dns.columns:
                                for _,_dr3 in _dd_dns[_dd_dns["etapa"].str.upper()=="DNS"].iterrows():
                                    _g3=str(_dr3.get("gp","")).strip(); _p3=str(_dr3.get("piloto","")).strip()
                                    _v3=int(_dr3["puntos"]); _v3 = _v3 if _v3 != 0 else -5
                                    _mask=(_agg_total["gp"]==_g3)&(_agg_total["piloto"]==_p3)
                                    if _mask.any():
                                        _agg_total.loc[_mask,"puntos"] = _agg_total.loc[_mask,"puntos"] + _v3
                        except Exception: pass
                    if not _agg_total.empty:
                        st.markdown('<div class="ana-cat" style="margin-top:14px;">🏁 Puntos totales por GP (DNS incluido)</div>', unsafe_allow_html=True)
                        _pv2 = _agg_total.pivot_table(index="gp",columns="piloto",values="puntos",fill_value=0,aggfunc="sum")
                        _pv2 = _pv2.reindex([g for g in GPS_OFICIALES if g in _pv2.index])
                        _pv2.index = [g.split(". ",1)[-1] if ". " in g else g for g in _pv2.index]
                        st.markdown(_pv2.to_html(classes="tabla_historial_dark",border=0), unsafe_allow_html=True)
                except Exception: pass
        else:
            st.info("📊 El análisis se activa una vez computado el primer GP.")
        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)

    # ═══════════════ TAB RÉCORDS ════════════════════════════════
    with tab_records:
        st.markdown('<div style="font-size:18px;font-weight:900;color:#ffdd7a;margin-bottom:16px;">🏅 RÉCORDS DE LA TEMPORADA 2026</div>', unsafe_allow_html=True)
        if df_hist is not None and not (hasattr(df_hist,"empty") and df_hist.empty):
            try:
                _rh = df_hist.copy(); _rh.columns=[c.lower().strip() for c in _rh.columns]
                _rh["puntos"]=pd.to_numeric(_rh["puntos"],errors="coerce").fillna(0).astype(int)
                _records_list = []
                if not _rh.empty:
                    _imax = _rh["puntos"].idxmax()
                    _imin = _rh["puntos"].idxmin()
                    _rrow_max = _rh.loc[_imax]
                    _rrow_min = _rh.loc[_imin]
                    _gp_max = str(_rrow_max.get("gp","")).split(". ",1)[-1]
                    _gp_min = str(_rrow_min.get("gp","")).split(". ",1)[-1]
                    _total_by_pil = _rh.groupby("piloto")["puntos"].sum()
                    _avg_by_pil = _rh.groupby("piloto")["puntos"].mean()
                    _records_list = [
                        ("🏆","Mayor puntaje en un GP",f"{_rrow_max.get('piloto','?')} — {int(_rrow_max['puntos'])} pts",f"({_gp_max})"),
                        ("😔","Menor puntaje en un GP",f"{_rrow_min.get('piloto','?')} — {int(_rrow_min['puntos'])} pts",f"({_gp_min})"),
                        ("📈","Mayor acumulado temporada",f"{_total_by_pil.idxmax()} — {int(_total_by_pil.max())} pts",""),
                        ("📉","Menor acumulado temporada",f"{_total_by_pil.idxmin()} — {int(_total_by_pil.min())} pts",""),
                        ("🎯","Mejor promedio/GP",f"{_avg_by_pil.idxmax()} — {_avg_by_pil.max():.1f} pts",""),
                    ]
                    # Sprint record
                    if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
                        try:
                            _dd_r = df_det.copy(); _dd_r.columns=[c.lower().strip() for c in _dd_r.columns]
                            _dd_r["puntos"]=pd.to_numeric(_dd_r["puntos"],errors="coerce").fillna(0).astype(int)
                            if "etapa" in _dd_r.columns:
                                _spr_d = _dd_r[_dd_r["etapa"].str.upper()=="SPRINT"]
                                if not _spr_d.empty:
                                    _si = _spr_d["puntos"].idxmax()
                                    _sr = _spr_d.loc[_si]
                                    _gp_s = str(_sr.get("gp","")).split(". ",1)[-1]
                                    _records_list.append(("⚡","Mejor sprint",f"{_sr.get('piloto','?')} — {int(_sr['puntos'])} pts",f"({_gp_s})"))
                                _q_d = _dd_r[_dd_r["etapa"].str.upper()=="QUALY"]
                                if not _q_d.empty:
                                    _qi = _q_d["puntos"].idxmax()
                                    _qr = _q_d.loc[_qi]
                                    _gp_q = str(_qr.get("gp","")).split(". ",1)[-1]
                                    _records_list.append(("⏱️","Mejor qualy",f"{_qr.get('piloto','?')} — {int(_qr['puntos'])} pts",f"({_gp_q})"))
                        except Exception: pass

                _rec_cols = st.columns(2)
                for _ri, (_ico, _tit, _val, _sub) in enumerate(_records_list):
                    with _rec_cols[_ri % 2]:
                        st.markdown(
                            f'<div style="background:rgba(246,195,73,.06);border:1px solid rgba(246,195,73,.2);'
                            f'border-radius:14px;padding:12px 16px;margin-bottom:10px;">'
                            f'<div style="font-size:22px;margin-bottom:4px;">{_ico}</div>'
                            f'<div style="font-size:10px;font-weight:700;color:rgba(246,195,73,.6);'
                            f'text-transform:uppercase;letter-spacing:.1em;">{_tit}</div>'
                            f'<div style="font-size:14px;font-weight:900;color:#e8ecff;margin-top:3px;">{_val}</div>'
                            f'{"<div style=\"font-size:10px;color:rgba(169,178,214,.45);margin-top:2px;\">"+_sub+"</div>" if _sub else ""}'
                            f'</div>', unsafe_allow_html=True)
            except Exception as _re: st.info(f"Sin datos de récords aún. {_re}")
        else:
            st.info("Los récords aparecen una vez generado el historial.")

    # ═══════════════ TAB COLAPINTO ══════════════════════════════
    with tab_col:
        st.markdown('<div style="font-size:18px;font-weight:900;color:#74b9ff;margin-bottom:8px;">🇦🇷 Franco Colapinto — Predicciones por GP</div>', unsafe_allow_html=True)
        st.caption("Posición predicha por cada formulero para Colapinto en Qualy y Carrera.")

        @st.cache_data(ttl=60, show_spinner="Cargando predicciones Colapinto…")
        def _load_col_preds(gps_list):
            _mdb_col = _mod_db()
            if "_error" in _mdb_col: return []
            # Load official Colapinto results once
            _of_col_map = {}  # gp_label -> {col_q: pos, col_r: pos}
            try:
                from core.database import conectar_google_sheets as _cgs_col
                _ws_col = _cgs_col("Oficial")
                if _ws_col:
                    _col_recs = _ws_col.get_all_records()
                    def _gp_key(_g):
                        _s = str(_g or "").strip()
                        if ". " in _s: _s = _s.split(". ",1)[-1]
                        _s = _s.replace("Gran Premio de ","").replace("Gran Premio del ","").replace("GP ","").replace("GP de ","")
                        return _s.strip().lower()
                    for _rc in _col_recs:
                        _et_c = str(_rc.get("etapa","")).upper()
                        if "COLAPINTO" not in _et_c: continue
                        _gp_c = str(_rc.get("gp","")).strip()
                        _gp_bare = _gp_key(_gp_c)
                        if _gp_bare not in _of_col_map:
                            _of_col_map[_gp_bare] = {}
                        _pos_c = str(_rc.get("pos","")).strip()
                        # "COLAPINTO Q" / "COLAPINTO QUALY" => qualy; resto => carrera
                        if "Q" in _et_c.replace("COLAPINTO","").strip() or "QUALY" in _et_c:
                            _of_col_map[_gp_bare]["col_q"] = _pos_c
                        else:
                            _of_col_map[_gp_bare]["col_r"] = _pos_c
            except Exception: pass
            # Saber si cada GP ya cerró (para no revelar predicciones de GPs abiertos)
            def _gp_cerrado_col(_gp_full):
                try:
                    from datetime import datetime as _dtcc
                    _h = HORARIOS_CARRERA.get(_gp_full, "")
                    if not _h: return True  # sin horario => asumir cerrado (histórico)
                    _dt = _dtcc.fromisoformat(_h)
                    _dt = TZ.localize(_dt) if _dt.tzinfo is None else _dt
                    return _dtcc.now(TZ) > _dt
                except Exception: return True
            _rows = []
            def _gp_key2(_g):
                _s = str(_g or "").strip()
                if ". " in _s: _s = _s.split(". ",1)[-1]
                _s = _s.replace("Gran Premio de ","").replace("Gran Premio del ","").replace("GP ","").replace("GP de ","")
                return _s.strip().lower()

            # ── BULK LOAD: leer sheet1 UNA sola vez y armar lookup ──
            # Evita 6×N llamadas lentas que podían timeoutear y mostrar "—" falso
            _col_pred_map = {}  # (gp_key, piloto_lower) -> {"q":..., "r":...}
            try:
                import re as _re_col
                from core.database import conectar_google_sheets as _cgs_pred
                _ws_pred = _cgs_pred("sheet1")
                if _ws_pred:
                    _all_pred = _ws_pred.get_all_values()
                    if _all_pred and len(_all_pred) > 1:
                        _hdr_p = [h.strip().lower() for h in _all_pred[0]]
                        def _fcol(names, dflt):
                            for nm in names:
                                for _ix,_h in enumerate(_hdr_p):
                                    if _h == nm: return _ix
                            return dflt
                        _ix_usr = _fcol(["usuario","user","nombre"],1)
                        _ix_gp  = _fcol(["gp","gran_premio","gran premio"],2)
                        _ix_et  = _fcol(["etapa","tipo"],3)
                        _ix_d   = _ix_et + 1
                        def _sf(row, ix):
                            return str(row[ix]).strip() if ix < len(row) else ""
                        for _rp in _all_pred[1:]:
                            if len(_rp) <= _ix_et: continue
                            _usr_p = _sf(_rp,_ix_usr)
                            _gp_p  = _sf(_rp,_ix_gp)
                            _et_p  = _sf(_rp,_ix_et).upper()
                            _gpk = _gp_key2(_gp_p)
                            _key = (_gpk, _usr_p.strip().lower())
                            if _key not in _col_pred_map:
                                _col_pred_map[_key] = {"q":"", "r":""}
                            if _et_p == "QUALY":
                                # colapinto_q está en idx_data+5 (después de 5 posiciones)
                                _col_pred_map[_key]["q"] = _sf(_rp, _ix_d + 5)
                            elif _et_p == "CARRERA":
                                # colapinto_r está en idx_data+10 (después de 10 posiciones)
                                _col_pred_map[_key]["r"] = _sf(_rp, _ix_d + 10)
            except Exception: pass

            for _gp_c2 in gps_list:
                _gp_l_c = _gp_c2.split(". ",1)[-1] if ". " in _gp_c2 else _gp_c2
                _of_gp = _of_col_map.get(_gp_key2(_gp_c2), {})
                _cerrado_c = _gp_cerrado_col(_gp_c2)
                _gpk_c = _gp_key2(_gp_c2)
                for _pil_c2 in PILOTOS_TORNEO:
                    try:
                        _pred = _col_pred_map.get((_gpk_c, _pil_c2.strip().lower()), {})
                        _col_q = str(_pred.get("q","")).strip()
                        _col_r = str(_pred.get("r","")).strip()
                        _of_q = _of_gp.get("col_q",""); _of_r = _of_gp.get("col_r","")
                        def _norm_pos(x):
                            return str(x or "").strip().upper().lstrip("P").strip()
                        # ok=None si no hay predicción O no hay resultado oficial (gris, sin ❌)
                        if not _col_q:
                            _q_ok = None
                        elif not _of_q:
                            _q_ok = None
                        else:
                            _q_ok = (_norm_pos(_col_q) == _norm_pos(_of_q))
                        if not _col_r:
                            _r_ok = None
                        elif not _of_r:
                            _r_ok = None
                        else:
                            _r_ok = (_norm_pos(_col_r) == _norm_pos(_of_r))
                        if _cerrado_c:
                            _q_disp = f"P{_col_q}" if _col_q else "—"
                            _r_disp = f"P{_col_r}" if _col_r else "—"
                        else:
                            # GP abierto: ocultar para mantener secreto
                            _q_disp = "🔒" if _col_q else "—"
                            _r_disp = "🔒" if _col_r else "—"
                            _q_ok = None; _r_ok = None
                        _rows.append({
                            "GP": _gp_l_c, "Formulero": _pil_c2,
                            "Qualy": _q_disp, "Carrera": _r_disp,
                            "Qualy_ok": _q_ok, "Carrera_ok": _r_ok,
                            "Oculto": (not _cerrado_c),
                        })
                    except Exception: pass
            return _rows

        if gps_j:
            # Botón de actualizar para forzar recarga
            _cc_ref1, _cc_ref2 = st.columns([4,1])
            with _cc_ref2:
                if st.button("🔄", key="col_refresh", help="Actualizar aciertos Colapinto"):
                    _load_col_preds.clear(); st.rerun()
            _col_rows = _load_col_preds(tuple(gps_j))
            if _col_rows:
                # Styled display — más recientes primero, con Ver/Ocultar
                _col_gps = sorted(set(r["GP"] for r in _col_rows))
                # Ordenar según el orden de gps_j (cronológico) y mostrar el más nuevo arriba
                _orden_gps = [g.split(". ",1)[-1] if ". " in g else g for g in gps_j]
                _col_gps = sorted(_col_gps, key=lambda x: _orden_gps.index(x) if x in _orden_gps else 999, reverse=True)
                _col_open = st.session_state.get("_colapinto_open", False)
                _cc1, _cc2 = st.columns([3,1])
                with _cc2:
                    if st.button("👁️ Ver todos" if not _col_open else "🙈 Ocultar",
                                 key="toggle_colapinto", use_container_width=True):
                        st.session_state["_colapinto_open"] = not _col_open; st.rerun()
                # Si está cerrado: mostrar solo el último GP. Si abierto: todos.
                _gps_a_mostrar = _col_gps if _col_open else _col_gps[:1]
                if not _col_open and len(_col_gps) > 1:
                    st.caption(f"Mostrando el último GP — tocá 👁️ Ver todos para los {len(_col_gps)} GPs")
                for _cgp in _gps_a_mostrar:
                    _cgp_rows = [r for r in _col_rows if r["GP"]==_cgp]
                    st.markdown(f'<div style="font-size:11px;font-weight:800;color:rgba(246,195,73,.7);'
                                f'text-transform:uppercase;letter-spacing:.08em;margin:10px 0 4px;">'
                                f'🏁 {_cgp}</div>', unsafe_allow_html=True)
                    _cgp_cols = st.columns(len(_cgp_rows))
                    for _ci, _cr in enumerate(_cgp_rows):
                        _pclr = PILOTO_COLORS.get(_cr["Formulero"],"#a855f7")
                        with _cgp_cols[_ci]:
                                # Show ✅/❌ if official result available
                                _q_ok5 = _cr.get("Qualy_ok"); _r_ok5 = _cr.get("Carrera_ok")
                                def _col_ok5(ok):
                                    if ok is True: return "#4ade80"
                                    if ok is False: return "#ef4444"
                                    return "rgba(169,178,214,.7)"
                                def _ico_ok5(ok,pts):
                                    if ok is True: return f" ✅(+{pts})"
                                    if ok is False: return " ❌"
                                    return ""
                                st.markdown(
                                f'<div style="background:{_pclr}11;border:1px solid {_pclr}33;'
                                f'border-radius:10px;padding:7px 8px;text-align:center;">'
                                f'<div style="font-size:9px;font-weight:800;color:{_pclr};'
                                f'text-transform:uppercase;margin-bottom:4px;">{_cr["Formulero"].split()[0]}</div>'
                                f'<div style="font-size:10px;color:{_col_ok5(_q_ok5)};margin-bottom:2px;">Q: {_cr["Qualy"]}{_ico_ok5(_q_ok5,10)}</div>'
                                f'<div style="font-size:10px;color:{_col_ok5(_r_ok5)};">C: {_cr["Carrera"]}{_ico_ok5(_r_ok5,20)}</div>'
                                f'</div>', unsafe_allow_html=True)
            else:
                st.info("Sin predicciones de Colapinto registradas.")
        else:
            st.info("Sin GPs completados todavía.")


def _init_slots(kp, count):
    for i in range(1, count+1):
        sk = f"{kp}_{i}"
        if sk not in st.session_state:
            st.session_state[sk] = ""

def _get_sel(kp, count):
    return {i: st.session_state.get(f"{kp}_{i}", "") for i in range(1, count+1)}

def modal_pilot_selector(options, count, kp):
    """Hybrid: photo preview row + native selectbox + X button."""
    _init_slots(kp, count)
    medals = {1:"🥇",2:"🥈",3:"🥉"}

    st.markdown("""
    <style>
    /* Pilot row base (inline styles override these) */
    .qrow{display:flex;align-items:center;gap:7px;padding:5px 8px;
      border-radius:9px;margin-bottom:3px;
      border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.02);}
    .qrow.qfill{background:rgba(255,255,255,.04);}
    </style>""", unsafe_allow_html=True)

    for i in range(1, count+1):
        cur_d = st.session_state.get(f"{kp}_{i}", "")
        photo = DRIVER_HEADSHOTS.get(cur_d,"") if cur_d else ""
        team  = next((t for t,ds in GRILLA_2026.items() if cur_d in ds),"") if cur_d else ""
        tc    = TEAM_COLORS.get(team,"#a855f7") if team else "#666"
        medal = medals.get(i, f"P{i}")
        logo  = TEAM_LOGOS_CDN.get(team,"") if team else ""

        c_row, c_del = st.columns([9, 1])
        with c_row:
            if cur_d and photo:
                st.markdown(
                    f"<div style='display:flex;align-items:center;justify-content:center;"
                    f"gap:10px;padding:8px 14px;"
                    f"border-radius:12px;margin-bottom:3px;position:relative;"
                    f"border:1.5px solid {tc}55;"
                    f"background:linear-gradient(135deg,{tc}12,rgba(0,0,0,.45));'>"
                    f"<div style='width:28px;height:28px;border-radius:50%;display:flex;"
                    f"align-items:center;justify-content:center;font-size:12px;font-weight:900;"
                    f"flex-shrink:0;background:rgba(246,195,73,.1);border:1px solid {tc}44;color:{tc};'>{medal}</div>"
                    f"<img src='{photo}' style='width:44px;height:44px;border-radius:8px;"
                    f"object-fit:cover;object-position:top;border:1.5px solid {tc}55;flex-shrink:0;'>"
                    f"<div style='text-align:center;min-width:0;'>"
                    f"<div style='font-size:12px;font-weight:800;color:{tc};"
                    f"overflow:hidden;white-space:nowrap;text-overflow:ellipsis;'>{cur_d}</div>"
                    f"<div style='font-size:8px;opacity:.5;letter-spacing:.08em;text-transform:uppercase;margin-top:1px;'>{team}</div>"
                    f"</div>"
                    + (f"<img src='{logo}' style='height:20px;max-width:54px;"
                       f"object-fit:contain;opacity:.8;flex-shrink:0;' loading='lazy'>" if logo else "")
                    + "</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='display:flex;align-items:center;justify-content:center;"
                    f"gap:10px;padding:8px 14px;"
                    f"border-radius:9px;margin-bottom:3px;"
                    f"border:1px solid rgba(255,255,255,.07);background:rgba(255,255,255,.02);'>"
                    f"<div style='width:26px;height:26px;border-radius:50%;display:flex;"
                    f"align-items:center;justify-content:center;font-size:11px;font-weight:900;"
                    f"flex-shrink:0;background:rgba(246,195,73,.07);border:1px solid rgba(246,195,73,.2);"
                    f"color:#ffdd7a;'>{medal}</div>"
                    f"<div style='width:36px;height:36px;border-radius:6px;flex-shrink:0;"
                    f"background:rgba(255,255,255,.04);border:1px dashed rgba(255,255,255,.13);"
                    f"display:flex;align-items:center;justify-content:center;"
                    f"font-size:15px;color:rgba(255,255,255,.2);'>?</div>"
                    f"<div style='font-size:11px;font-weight:700;text-align:center;"
                    f"color:rgba(169,178,214,.38);'>Sin piloto seleccionado</div>"
                    f"</div>",
                    unsafe_allow_html=True
                )
        with c_del:
            if cur_d:
                if st.button("✖", key=f"{kp}_x_{i}", use_container_width=True, help="Quitar"):
                    st.session_state[f"{kp}_{i}"] = ""
                    st.rerun()
            else:
                st.write("")

        taken = {st.session_state.get(f"{kp}_{j}","") for j in range(1,count+1) if j!=i}
        avail = [""] + [o for o in options if o not in taken]
        st.selectbox(
            f"",
            avail,
            index=avail.index(cur_d) if cur_d in avail else 0,
            key=f"{kp}_{i}",
            format_func=lambda x: "— Elegí un piloto —" if x=="" else x,
            label_visibility="collapsed"
        )

    return {i: st.session_state.get(f"{kp}_{i}","") for i in range(1,count+1)}



def modal_constructor_selector(teams, count, kp):
    """Constructor selector: centered car image + full name + selectbox."""
    _init_slots(kp, count)
    medals_lbl = {1:"🥇 1° Lugar", 2:"🥈 2° Lugar", 3:"🥉 3° Lugar"}

    st.markdown("""
    <style>
    .crow{display:flex;align-items:center;gap:10px;padding:8px 12px;
      border-radius:12px;margin-bottom:4px;
      border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.02);}
    .crow.cfill{background:rgba(255,255,255,.04);}
    .crow-medal{font-size:16px;flex-shrink:0;}
    .crow-car-wrap{flex:1;display:flex;
      flex-direction:column;align-items:center;justify-content:center;gap:3px;}
    .crow-car{width:100%;max-width:200px;height:58px;object-fit:contain;display:block;}
    .crow-logo{height:22px;max-width:80px;object-fit:contain;opacity:.85;}
    .crow-ph{width:120px;height:46px;border-radius:8px;flex-shrink:0;
      background:rgba(255,255,255,.05);border:1.5px dashed rgba(255,255,255,.15);
      display:flex;align-items:center;justify-content:center;font-size:22px;}
    .crow-info{flex:1;min-width:0;}
    .crow-name{font-size:12px;font-weight:800;overflow:hidden;
      white-space:nowrap;text-overflow:ellipsis;}
    .crow-sub{font-size:9px;opacity:.42;letter-spacing:.06em;text-transform:uppercase;}
    </style>""", unsafe_allow_html=True)

    for i in range(1, count+1):
        cur_t = st.session_state.get(f"{kp}_{i}", "")
        car   = TEAM_CARS_MODULE.get(cur_t,"") if cur_t else ""
        tc    = TEAM_COLORS.get(cur_t,"#a855f7") if cur_t else "rgba(255,255,255,.15)"
        mlbl  = medals_lbl.get(i, f"P{i}")
        medal = ["🥇","🥈","🥉"][i-1]

        c_row, c_del = st.columns([9, 1])
        with c_row:
            if cur_t:
                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:8px;padding:8px 12px;"
                    f"border-radius:12px;margin-bottom:3px;"
                    f"border:1.5px solid {tc}55;"
                    f"background:linear-gradient(135deg,{tc}12,rgba(0,0,0,.5));'>"
                    f"<div style='font-size:15px;flex-shrink:0;'>{medal}</div>"
                    + "<div style='flex:1;display:flex;align-items:center;justify-content:center;min-width:0;'>"
                    + (f"<img style='max-width:190px;height:52px;object-fit:contain;' src='{car}'>" if car else "")
                    + "</div>"
                    + "<div style='flex-shrink:0;min-width:90px;display:flex;flex-direction:column;align-items:flex-end;gap:2px;padding-right:4px;'>"
                    + (f"<img src='" + TEAM_LOGOS_CDN.get(cur_t,"") + "' style='height:18px;max-width:65px;object-fit:contain;opacity:.85;' loading='lazy'>" if TEAM_LOGOS_CDN.get(cur_t,"") else "")
                    + f"<div style='font-size:11px;font-weight:900;color:{tc};white-space:nowrap;text-align:right;'>{cur_t}</div>"
                    + f"<div style='font-size:8px;font-weight:700;color:{tc};opacity:.6;letter-spacing:.06em;text-align:right;'>{mlbl}</div>"
                    + "</div></div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='crow'>"
                    f"<div class='crow-medal' style='opacity:.5;'>{medal}</div>"
                    f"<div class='crow-ph'>🏎️</div>"
                    f"<div class='crow-info' style='text-align:center;'>"
                    f"<div class='crow-name' style='color:rgba(169,178,214,.38);'>Sin equipo seleccionado</div>"
                    f"<div class='crow-sub'>{mlbl} — Elegí abajo ↓</div></div></div>",
                    unsafe_allow_html=True
                )
        with c_del:
            if cur_t:
                if st.button("✖", key=f"{kp}_x_{i}", use_container_width=True, help="Quitar"):
                    st.session_state[f"{kp}_{i}"] = ""
                    st.rerun()
            else:
                st.write("")

        taken = {st.session_state.get(f"{kp}_{j}","") for j in range(1,count+1) if j!=i}
        avail = [""] + [t for t in teams if t not in taken]
        st.selectbox(
            "",
            avail,
            index=avail.index(cur_t) if cur_t in avail else 0,
            key=f"{kp}_{i}",
            format_func=lambda x: "— Sin equipo seleccionado —" if x=="" else x,
            label_visibility="collapsed"
        )

    return {i: st.session_state.get(f"{kp}_{i}","") for i in range(1,count+1)}



def _pantalla_pilotos_grid():
    """Grid de pilotos F1 2026 — tab en Predicciones."""
    all_drivers = []
    for equipo, pilotos in GRILLA_2026.items():
        color = TEAM_COLORS.get(equipo, "#A855F7")
        abbr  = TEAM_LOGOS_SVG.get(equipo, equipo[:3])
        for num_idx, pil in enumerate(pilotos):
            all_drivers.append((pil, equipo, color, abbr, num_idx + 1))

    # Inject improved grid CSS
    st.markdown("""
    <style>
    .f1-drivers-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 14px;
      padding: 8px 0 16px;
    }
    .f1d-card {
      background: linear-gradient(145deg, rgba(7,10,25,.97) 0%, rgba(14,18,42,.95) 100%);
      border: 1.5px solid var(--tc, #a855f7);
      border-radius: 16px;
      overflow: hidden;
      position: relative;
      transition: transform .25s ease, box-shadow .25s ease;
      box-shadow: 0 4px 18px rgba(0,0,0,.5);
    }
    .f1d-card:hover {
      transform: translateY(-6px) scale(1.02);
      box-shadow: 0 10px 32px rgba(0,0,0,.7), 0 0 20px var(--tc, #a855f7)33;
    }
    .f1d-top-stripe {
      height: 3px;
      background: var(--tc, #a855f7);
      width: 100%;
    }
    .f1d-logo {
      position:absolute;top:10px;left:8px;
      height:18px;max-width:54px;object-fit:contain;
      opacity:.85;filter:brightness(1.2);z-index:3;
    }
    .f1d-team-badge {
      position: absolute;
      top: 10px;
      right: 10px;
      font-size: 8px;
      font-weight: 900;
      color: var(--tc, #a855f7);
      background: rgba(0,0,0,.6);
      border: 1px solid var(--tc, #a855f7)55;
      border-radius: 6px;
      padding: 2px 6px;
      letter-spacing: .1em;
      z-index: 2;
    }
    .f1d-photo-wrap {
      width: 100%;
      aspect-ratio: 1 / 1.05;
      overflow: hidden;
      background: linear-gradient(180deg, rgba(0,0,0,.1), rgba(0,0,0,.5));
      position: relative;
    }
    .f1d-photo {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center 18%;
      display: block;
      transition: transform .3s ease;
    }
    @media (max-width:768px){
      .f1d-photo-wrap { aspect-ratio: 1 / 1.05 !important; background:#08091e !important; }
      .f1d-photo { object-fit: cover !important; object-position: center 18% !important; }
    }
    .f1d-card:hover .f1d-photo { transform: scale(1.04); }
    .f1d-fallback {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 36px;
      font-weight: 900;
      background: rgba(0,0,0,.4);
    }
    .f1d-info {
      padding: 10px 10px 12px;
      background: linear-gradient(0deg, rgba(0,0,0,.85), rgba(0,0,0,.4));
    }
    .f1d-flag { font-size: 14px; margin-bottom: 3px; }
    .f1d-firstname {
      font-size: 9px;
      font-weight: 500;
      color: rgba(232,236,255,.6);
      text-transform: uppercase;
      letter-spacing: .08em;
      line-height: 1.2;
    }
    .f1d-lastname {
      font-size: 13px;
      font-weight: 900;
      color: var(--tc, #e8ecff);
      letter-spacing: .04em;
      line-height: 1.2;
      margin-bottom: 4px;
    }
    .f1d-team-name {
      font-size: 8px;
      color: var(--tc, #a855f7);
      font-weight: 700;
      letter-spacing: .12em;
      text-transform: uppercase;
      opacity: .8;
    }
    </style>
    """, unsafe_allow_html=True)
    cards_html = '<div class="f1-drivers-grid">'  
    for pil, equipo, color, abbr, num in all_drivers:
        photo = DRIVER_PHOTOS.get(pil, "")
        initials = "".join(p[0] for p in pil.split()[:2]).upper()
        nacionalidades = {
            "Lando Norris": "🇬🇧", "Oscar Piastri": "🇦🇺", "Max Verstappen": "🇳🇱",
            "Isack Hadjar": "🇫🇷", "Kimi Antonelli": "🇮🇹", "George Russell": "🇬🇧",
            "Charles Leclerc": "🇲🇨", "Lewis Hamilton": "🇬🇧", "Alex Albon": "🇹🇭",
            "Carlos Sainz": "🇪🇸", "Lance Stroll": "🇨🇦", "Fernando Alonso": "🇪🇸",
            "Liam Lawson": "🇳🇿", "Arvid Lindblad": "🇸🇪", "Oliver Bearman": "🇬🇧",
            "Esteban Ocon": "🇫🇷", "Nico Hulkenberg": "🇩🇪", "Gabriel Bortoleto": "🇧🇷",
            "Pierre Gasly": "🇫🇷", "Franco Colapinto": "🇦🇷",
            "Checo Perez": "🇲🇽", "Valteri Bottas": "🇫🇮",
        }
        logo_url = TEAM_LOGOS_CDN.get(equipo, "")
        flag = nacionalidades.get(pil, "🌍")
        last_name = pil.split()[-1].upper()
        first_name = " ".join(pil.split()[:-1])
        img_html = f'<img src="{photo}" class="f1d-photo" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\';" loading="lazy">'
        fallback = f'<div class="f1d-fallback" style="display:none;color:{color};">{initials}</div>'
        cards_html += f"""
        <div class="f1d-card fade-up" style="--tc:{color}">
          <div class="f1d-top-stripe"></div>
          <div class="f1d-team-badge" style="display:flex;align-items:center;gap:4px;"><span>{abbr}</span></div>
          <img src="{logo_url}" class="f1d-logo" onerror="this.style.display='none';" loading="lazy">
          <div class="f1d-photo-wrap">{img_html}{fallback}</div>
          <div class="f1d-info">
            <div class="f1d-flag">{flag}</div>
            <div class="f1d-firstname">{first_name}</div>
            <div class="f1d-lastname">{last_name}</div>
            <div class="f1d-team-name">{equipo}</div>
          </div>
        </div>"""
    cards_html += "</div>"
    st.markdown(cards_html, unsafe_allow_html=True)



def _pantalla_escuderias_grid():
    """Grid de escuderías F1 2026 — tab en Predicciones."""
    TEAM_DESCRIPTIONS = {
        "MCLAREN":      "El equipo de Woking vuelve como favorito con Norris y Piastri. MCL60 dominó la segunda mitad de 2025.",
        "RED BULL":     "El gigante de Milton Keynes. Verstappen busca su quinto título con el joven Hadjar como compañero.",
        "MERCEDES":     "La flecha plateada renace. Antonelli, la gran apuesta, junto a Russell en el W17.",
        "FERRARI":      "La Scuderia con Hamilton y Leclerc: la alineación más mediática de la historia de la F1.",
        "WILLIAMS":     "Albon y Sainz, una dupla sólida para llevar a Williams de regreso a la lucha por puntos.",
        "ASTON MARTIN": "El millonario proyecto de Lawrence Stroll con Alonso y su hijo Lance. AMR26 promete.",
        "RACING BULLS": "El equipo B de Red Bull. Lawson y Lindblad, dos jóvenes hambrientos de puntos.",
        "HAAS":         "Bearman y Ocon, dos europeos con hambre de demostrar. La escudería americana apuesta al futuro.",
        "AUDI":         "El debutante de lujo. Hulkenberg y Bortoleto encabezan el proyecto más ambicioso de la era moderna.",
        "ALPINE":       "Gasly y Colapinto — el argentino que tiene a toda Latinoamérica de su lado. ¡Vamos Franco!",
        "CADILLAC":     "El regreso de Checo a la grilla, ahora con Bottas. El equipo americano desafía al establishment.",
    }
    teams_list = list(GRILLA_2026.items())
    for i in range(0, len(teams_list), 2):
        cols = st.columns(2, gap="large")
        for j, (equipo, pilotos) in enumerate(teams_list[i:i+2]):
            color = TEAM_COLORS.get(equipo, "#A855F7")
            abbr  = TEAM_LOGOS_SVG.get(equipo, equipo[:3])
            desc  = TEAM_DESCRIPTIONS.get(equipo, "")
            car   = TEAM_CARS_MODULE.get(equipo, "")
            logo  = TEAM_LOGOS_CDN.get(equipo, "")
            p1, p2 = pilotos[0], pilotos[1]
            car_html  = f'<img src="{car}" class="tfc-car-img" loading="lazy" onerror="this.style.display=\'none\'">' if car else ""
            logo_html = f'<img src="{logo}" style="position:absolute;top:10px;right:12px;height:22px;max-width:72px;object-fit:contain;opacity:.85;z-index:3;" loading="lazy" onerror="this.style.display=\'none\'">' if logo else ""
            with cols[j]:
                st.markdown(f"""
                <div class="team-full-card fade-up" style="--tc:{color};position:relative;">
                  {logo_html}
                  <div class="tfc-header">
                    <div class="tfc-stripe"></div>
                    <div class="tfc-abbr" style="color:{color}">{abbr}</div>
                    <div class="tfc-name">{equipo}</div>
                  </div>
                  <div class="tfc-car-wrap">{car_html}</div>
                  <div class="tfc-drivers">
                    <div class="tfc-driver">
                      <div class="tfc-num" style="color:{color}">01</div>
                      <div class="tfc-dname">{p1}</div>
                    </div>
                    <div class="tfc-driver">
                      <div class="tfc-num" style="color:{color}">02</div>
                      <div class="tfc-dname">{p2}</div>
                    </div>
                  </div>
                  <div class="tfc-desc">{desc}</div>
                </div>""", unsafe_allow_html=True)



def _pantalla_calendario_tab():
    """Calendario 2026 embebido en tab de Predicciones."""
    _,c2,_ = st.columns([1,2,1])
    with c2:
        try: st.image("IMAGENCALENDARIO.jfif", use_container_width=True, caption="")
        except: pass
    # Build calendar table rows
    _rows_cal = ""
    for i_c, row_c in enumerate(CALENDARIO_VISUAL, 1):
        gp_c = row_c.get("Gran Premio",""); circ_c = row_c.get("Circuito","")
        fmt_c = row_c.get("Formato",""); fecha_c = row_c.get("Fecha","")
        susp_c = "SUSPENDIDO" in gp_c or "⛔" in gp_c
        sprint_c = "SPRINT" in fmt_c
        row_style = 'style="opacity:.5;"' if susp_c else ""
        num_color = "color:rgba(169,178,214,.4);font-size:10px;"
        fecha_color = "font-size:11px;color:rgba(169,178,214,.65);"
        if susp_c:
            fmt_color = "color:#ff7043;font-size:10px;"
        elif sprint_c:
            fmt_color = "color:#a855f7;font-weight:800;"
        else:
            fmt_color = "color:rgba(169,178,214,.55);"
        _rows_cal += (f'<tr {row_style}>' +
            f'<td style="{num_color}">{i_c}</td>' +
            f'<td style="{fecha_color}">{fecha_c}</td>' +
            f'<td style="text-align:left;font-weight:{"700" if not susp_c else "400"};">{gp_c}</td>' +
            f'<td style="color:rgba(169,178,214,.5);font-size:11px;">{circ_c}</td>' +
            f'<td style="{fmt_color}">{fmt_c}</td></tr>')
    st.markdown(
        '<div style="overflow-x:auto;margin:10px 0;">' +
        '<table style="width:100%;border-collapse:collapse;background:rgba(7,10,25,.96);' +
        'border:1px solid rgba(212,175,55,.22);border-radius:14px;overflow:hidden;">' +
        '<thead><tr style="border-bottom:1px solid rgba(212,175,55,.2);">' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;letter-spacing:.1em;padding:10px 8px;">#</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;letter-spacing:.1em;padding:10px 8px;">Fecha</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;letter-spacing:.1em;padding:10px 8px;">Gran Premio</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;letter-spacing:.1em;padding:10px 8px;">Circuito</th>' +
        '<th style="font-size:9px;color:rgba(212,175,55,.7);text-transform:uppercase;letter-spacing:.1em;padding:10px 8px;">Formato</th>' +
        '</tr></thead><tbody style="font-size:12px;color:#e8ecff;">' +
        _rows_cal +
        '</tbody></table></div>',
        unsafe_allow_html=True
    )

def _pantalla_tabla_f1(tipo="pilotos"):
    """Tabla de posiciones F1 2026 oficial — scraping de formula1.com."""
    import requests as _rq_f1
    _url_map = {
        "pilotos": "https://www.formula1.com/en/results/2026/drivers",
        "constructores": "https://www.formula1.com/en/results/2026/team",
    }
    _url = _url_map.get(tipo, _url_map["pilotos"])
    _titulo = "🏆 Campeonato de Pilotos 2026" if tipo=="pilotos" else "🏗️ Campeonato de Constructores 2026"
    st.markdown(f'<div style="font-size:14px;font-weight:900;color:#D4AF37;margin-bottom:10px;">{_titulo}</div>',
                unsafe_allow_html=True)
    st.caption(f"Fuente: formula1.com · [Ver en F1]({_url})")

    @st.cache_data(ttl=1800, show_spinner="Cargando standings F1...")
    def _fetch_f1_standings(url, kind):
        try:
            import requests as _rq, re as _re_f1
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = _rq.get(url, headers=headers, timeout=12)
            if resp.status_code != 200:
                return None
            html = resp.text
            rows_raw = _re_f1.findall(r'<tr[^>]*>(.*?)</tr>', html, _re_f1.DOTALL)
            data = []
            for row in rows_raw:
                cells = _re_f1.findall(r'<td[^>]*>(.*?)</td>', row, _re_f1.DOTALL)
                if len(cells) >= 3:
                    clean = [_re_f1.sub(r'<[^>]+>','',c).strip() for c in cells]
                    clean = [' '.join(c.split()) for c in clean]
                    clean = [c for c in clean if c]
                    if clean and clean[0].isdigit():
                        # F1.com packs: Pos | FirstLast + CODE | Nat | Team | Pts
                        # Fix: separate "Kimi AntonelliANT" → "Kimi Antonelli" + code
                        fixed = list(clean)
                        if kind == "pilotos" and len(fixed) > 1:
                            # Driver name has 3-letter code appended: "Kimi AntonelliANT"
                            name_raw = fixed[1]
                            code_match = _re_f1.search(r'([A-Z]{3})$', name_raw)
                            if code_match:
                                fixed[1] = name_raw[:code_match.start()].strip()
                                # nationality is already next cell
                        data.append(fixed)
            return data if data else None
        except Exception:
            return None

    _data = _fetch_f1_standings(_url, tipo)

    if _data:
        if tipo == "pilotos":
            _cols = ["#","Piloto","Pts"]
        else:
            _cols = ["#","Equipo","Pts"]

        _rows_html = ""
        for i_f1, row_f1 in enumerate(_data[:22]):
            _pos = row_f1[0] if row_f1 else str(i_f1+1)
            _name = row_f1[1] if len(row_f1)>1 else "—"
            # Pts is always the last numeric cell
            _pts = "0"
            for _v in reversed(row_f1):
                try: float(_v.replace(",","")); _pts = _v; break
                except: pass
            _medal = {1:"🥇",2:"🥈",3:"🥉"}.get(int(_pos) if _pos.isdigit() else 99, _pos)
            # Identify team and nat from remaining cells
            _remaining = row_f1[2:] if len(row_f1)>2 else []
            # For pilotos: remaining = [nat_3letter, team_name, pts]
            # For constructores: remaining = [pts]
            _nat = ""
            _team_name = ""
            if tipo == "pilotos" and len(_remaining) >= 2:
                # First remaining that's 2-3 uppercase letters = nationality
                for _rv in _remaining:
                    if len(_rv) in (2,3) and _rv.isupper() and not _rv.isdigit():
                        _nat = _rv; break
                # Team = remaining cell that's not nat and not pts
                for _rv in _remaining:
                    if _rv != _nat and _rv != _pts and len(_rv) > 3:
                        _team_name = _rv; break
            elif tipo == "constructores" and len(row_f1) > 1:
                _team_name = row_f1[1]
            _tc = next((v for k,v in TEAM_COLORS.items() if k.lower() in _team_name.lower() or _team_name.lower() in k.lower()), "#a855f7")
            # Special cases: "Red Bull Racing" -> RED BULL, "Haas F1 Team" -> HAAS etc
            if "red bull" in _team_name.lower(): _tc = TEAM_COLORS.get("RED BULL","#3671C6")
            if "ferrari" in _team_name.lower(): _tc = TEAM_COLORS.get("FERRARI","#DC0000")
            if "mclaren" in _team_name.lower(): _tc = TEAM_COLORS.get("MCLAREN","#FF8000")
            if "mercedes" in _team_name.lower(): _tc = TEAM_COLORS.get("MERCEDES","#00D2BE")
            if "alpine" in _team_name.lower(): _tc = TEAM_COLORS.get("ALPINE","#FF4FD8")
            if "aston" in _team_name.lower(): _tc = TEAM_COLORS.get("ASTON MARTIN","#006F62")
            if "williams" in _team_name.lower(): _tc = TEAM_COLORS.get("WILLIAMS","#005AFF")
            if "haas" in _team_name.lower(): _tc = TEAM_COLORS.get("HAAS","#B6BABD")
            if "racing bulls" in _team_name.lower() or "rb " in _team_name.lower(): _tc = TEAM_COLORS.get("RACING BULLS","#2B4562")
            if "audi" in _team_name.lower(): _tc = TEAM_COLORS.get("AUDI","#00E676")
            if "cadillac" in _team_name.lower(): _tc = TEAM_COLORS.get("CADILLAC","#E6C200")
            if tipo == "pilotos":
                _nat = row_f1[2] if len(row_f1)>2 else ""
                _team_disp = row_f1[3] if len(row_f1)>3 else ""
                # Try to find headshot
                _ph_f1 = next((v for k,v in DRIVER_HEADSHOTS.items()
                               if k.split()[-1].lower() in _name.lower()
                               or _name.lower() in k.lower()), "")
                _ini_f1 = ''.join(w[0] for w in _name.split()[:2]).upper()
                if _ph_f1:
                    _av_f1 = (f'<img src="{_ph_f1}" style="width:44px;height:44px;border-radius:50%;'
                              f'object-fit:cover;object-position:top;border:2px solid {_tc};flex-shrink:0;">')
                else:
                    _av_f1 = (f'<div style="width:44px;height:44px;border-radius:50%;background:{_tc}22;'
                              f'border:2px solid {_tc};display:flex;align-items:center;justify-content:center;'
                              f'font-weight:900;font-size:12px;color:{_tc};flex-shrink:0;">{_ini_f1}</div>')
                _subtitle = " · ".join(filter(None, [_team_disp, _nat]))
                _rows_html += (f'<tr style="border-bottom:1px solid rgba(255,255,255,.05);">'
                               f'<td style="text-align:center;padding:8px 10px;font-size:16px;">{_medal}</td>'
                               f'<td style="padding:8px 12px;">'
                               f'<div style="display:flex;align-items:center;gap:10px;">'
                               f'{_av_f1}'
                               f'<div><div style="font-weight:800;color:{_tc};font-size:13px;">{_name}</div>'
                               f'<div style="font-size:10px;color:rgba(169,178,214,.45);">{_subtitle}</div></div>'
                               f'</div></td>'
                               f'<td style="font-weight:900;color:#ffdd7a;text-align:center;font-size:18px;padding:8px 14px;min-width:60px;">{_pts}</td></tr>')
            else:
                # Constructor — add team logo
                _logo_f1 = next((v for k,v in TEAM_LOGOS_CDN.items()
                                 if k.lower() in _name.lower() or _name.lower() in k.lower()), "")
                _car_f1  = next((v for k,v in TEAM_CARS_MODULE.items()
                                 if k.lower() in _name.lower() or _name.lower() in k.lower()), "")
                _logo_html = (f'<img src="{_logo_f1}" style="height:18px;max-width:64px;object-fit:contain;opacity:.85;">') if _logo_f1 else ""
                if _car_f1:
                    _car_html2 = f'<img src="{_car_f1}" style="height:40px;max-width:140px;object-fit:contain;">'
                else:
                    _car_html2 = f'<div style="width:120px;height:40px;background:{_tc}11;border:1px solid {_tc}33;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:800;color:{_tc};">{_name[:6].upper()}</div>'
                _rows_html += (
                    f'<tr style="border-bottom:1px solid rgba(255,255,255,.05);">'
                    f'<td style="text-align:center;padding:8px 10px;font-size:18px;width:50px;">{_medal}</td>'
                    f'<td style="padding:8px 10px;">'
                    f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
                    f'<div style="background:rgba(255,255,255,.04);border:1px solid {_tc}22;border-radius:8px;padding:6px 10px;display:flex;align-items:center;justify-content:center;flex:1;min-width:120px;max-width:260px;">'
                    f'{_car_html2}</div>'
                    f'<div style="min-width:80px;"><div style="font-weight:800;color:{_tc};font-size:14px;">{_name}</div>'
                    f'{_logo_html}</div></div></td>'
                    f'<td style="font-weight:900;color:#ffdd7a;text-align:center;font-size:20px;padding:8px 12px;width:60px;">{_pts}</td></tr>')



        _head_html = "".join(f'<th style="font-size:9px;letter-spacing:.1em;color:rgba(212,175,55,.7);text-transform:uppercase;padding:8px 10px;">{h}</th>' for h in _cols)
        st.markdown(
            f'<div style="overflow-x:auto;">'
            f'<table style="width:100%;border-collapse:collapse;background:rgba(7,10,25,.96);'
            f'border:1px solid rgba(212,175,55,.22);border-radius:12px;overflow:hidden;">'
            f'<thead><tr style="border-bottom:1px solid rgba(212,175,55,.2);">{_head_html}</tr></thead>'
            f'<tbody style="font-size:12px;">{_rows_html}</tbody></table></div>',
            unsafe_allow_html=True)
        if st.button("🔄 Actualizar standings F1", key=f"ref_f1_{tipo}", use_container_width=False):
            _fetch_f1_standings.clear()
            st.rerun()
    else:
        st.markdown(
            f'<div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.25);'
            f'border-radius:12px;padding:16px;text-align:center;">'
            f'<div style="font-size:20px;margin-bottom:6px;">🌐</div>'
            f'<div style="font-size:12px;color:rgba(169,178,214,.7);">Los standings de F1 se cargan desde formula1.com.<br>'
            f'Si no aparecen, puede ser por restricciones de red en Streamlit Cloud.</div>'
            f'<a href="{_url}" target="_blank" style="display:inline-block;margin-top:10px;'
            f'background:rgba(212,175,55,.15);border:1px solid rgba(212,175,55,.4);'
            f'border-radius:8px;padding:6px 16px;color:#D4AF37;font-size:12px;font-weight:700;text-decoration:none;">'
            f'🔗 Ver en Formula1.com</a></div>',
            unsafe_allow_html=True)
        if st.button("🔄 Reintentar", key=f"retry_f1_{tipo}"):
            _fetch_f1_standings.clear()
            st.rerun()


def pantalla_cargar_predicciones():
    # ── Tabs de sección Predicciones ──────────────────────────────
    _tab_pred, _tab_pil_full, _tab_eq_full, _tab_cal = st.tabs([
        "🔒 Cargar Predicción",
        "👤 Pilotos 2026",
        "🏎️ Escuderías 2026",
        "📅 Calendario 2026",
    ])
    with _tab_cal:
        _pantalla_calendario_tab()
    with _tab_pil_full:
        # F1 standings + grid unificados
        _pantalla_tabla_f1("pilotos")
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:.12em;color:rgba(246,195,73,.6);text-transform:uppercase;margin-bottom:8px;">🏎️ GRILLA COMPLETA 2026</div>', unsafe_allow_html=True)
        _pantalla_pilotos_grid()
    with _tab_eq_full:
        # F1 constructors standings + escuderias grid
        _pantalla_tabla_f1("constructores")
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:.12em;color:rgba(246,195,73,.6);text-transform:uppercase;margin-bottom:8px;">🏎️ EQUIPOS Y AUTOS 2026</div>', unsafe_allow_html=True)
        _pantalla_escuderias_grid()
    with _tab_pred:
        _pantalla_pred_form()

def _pantalla_pred_form():
    # ── WhatsApp share banner (persiste después del rerun) ──
    _wa_p = st.session_state.pop("_wa_pending", None)
    if _wa_p:
        _wa_gp, _wa_tipo, _wa_res, _wa_usr = _wa_p if len(_wa_p) == 4 else (*_wa_p, "")
        st.markdown("""<style>
        .wa-banner{background:linear-gradient(90deg,rgba(18,140,126,.15),rgba(37,211,102,.1));
          border:1.5px solid rgba(37,211,102,.4);border-radius:14px;
          padding:14px 18px;margin-bottom:14px;display:flex;align-items:center;gap:14px;}
        .wa-banner-txt{flex:1;font-size:13px;color:#e8ecff;}
        .wa-banner-txt b{color:#4ade80;}
        </style>""", unsafe_allow_html=True)
        st.markdown('<div class="wa-banner">'
                    '<span style="font-size:28px;">📲</span>'
                    '<div class="wa-banner-txt">'
                    '<b>¡Predicción enviada exitosamente!</b><br>'
                    '<span style="font-size:11px;color:rgba(169,178,214,.7);">Compartila con el grupo:</span>'
                    '</div></div>', unsafe_allow_html=True)
        _wa_share_button(_wa_gp, _wa_tipo, _wa_res, _wa_usr)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    mdb   = _mod_db()
    mcore = _mod_core()
    mauth = _mod_auth()
    if "_error" in mdb or "_error" in mcore or "_error" in mauth:
        st.error("⚠️ Módulos no disponibles."); return

    st.markdown(
        '<div style="background:linear-gradient(135deg,#060f28,#0a1845,#060f28);'
        'border:2px solid rgba(59,130,246,.4);border-radius:18px;'
        'padding:20px 24px;margin-bottom:18px;position:relative;overflow:hidden;">'
        '<div style="position:absolute;top:-20px;right:-20px;width:120px;height:120px;'
        'border-radius:50%;background:radial-gradient(rgba(59,130,246,.15),transparent 70%);"></div>'
        '<div style="font-size:28px;margin-bottom:6px;">🔒</div>'
        '<div style="font-size:20px;font-weight:900;'
        'background:linear-gradient(90deg,#3b82f6,#93c5fd,#D4AF37,#93c5fd,#3b82f6);'
        'background-size:300% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
        'background-clip:text;">SISTEMA DE PREDICCIÓN 2026</div>'
        '<div style="font-size:10px;color:rgba(59,130,246,.6);letter-spacing:.15em;'
        'text-transform:uppercase;margin-top:4px;">Temporada activa · Solo formuleros invitados</div>'
        '</div>', unsafe_allow_html=True)

    # CSS exclusivo para la sección de predicciones — azul y dorado
    st.markdown("""
    <style>
    .pred-preview-title {
        font-size: 10px; font-weight: 700; letter-spacing: .14em;
        color: #3b82f6; text-transform: uppercase;
        margin-bottom: 7px; margin-top: 2px;
        display: flex; align-items: center; gap: 6px;
        border-left: 3px solid #3b82f6; padding-left: 8px;
    }
    .pred-section-header {
        background: linear-gradient(90deg,rgba(59,130,246,.12),transparent);
        border-left: 3px solid #3b82f6;
        border-radius: 0 8px 8px 0;
        padding: 8px 14px; margin: 12px 0 8px;
        font-size: 12px; font-weight: 800; color: #93c5fd;
    }
    .pred-select-container select {
        background: rgba(6,15,40,.9) !important;
        border-color: rgba(59,130,246,.4) !important;
        color: #D4AF37 !important;
    }
    .pred-gold-label { color: #D4AF37; font-weight: 800; }
    </style>
    """, unsafe_allow_html=True)

    usr_log = (st.session_state.get("perfil") or {}).get("usuario", "")
    c1, c2  = st.columns(2)
    usuario = c1.selectbox(
        "Piloto Participante", PILOTOS_TORNEO,
        index=PILOTOS_TORNEO.index(usr_log) if usr_log in PILOTOS_TORNEO else 0,
        key="pred_u"
    )
    # ── Auto-select next upcoming GP by date (cierre futuro más cercano) ──
    _default_gp_idx = 0
    try:
        from datetime import datetime as _dt_gp, timedelta as _td_gp
        _now_gp = _dt_gp.now(TZ)
        _best_idx = None; _best_diff = None
        for _gi, _gn in enumerate(GPS_ACTIVOS):
            _hora_str = HORARIOS_CARRERA.get(_gn, "")
            if not _hora_str: continue
            try:
                _dt_race = _dt_gp.fromisoformat(_hora_str)
                _dt_race = TZ.localize(_dt_race) if _dt_race.tzinfo is None else _dt_race
                # Considerar GP "vigente" hasta 3h después de la carrera
                if _now_gp < _dt_race + _td_gp(hours=3):
                    _diff = (_dt_race - _now_gp).total_seconds()
                    if _best_diff is None or abs(_diff) < abs(_best_diff):
                        _best_diff = _diff; _best_idx = _gi
            except Exception: continue
        if _best_idx is not None:
            _default_gp_idx = _best_idx
        else:
            # Fallback a secrets
            _next_gp_name = st.secrets.get("next_gp_name","")
            if _next_gp_name:
                for _gi, _gn in enumerate(GPS_ACTIVOS):
                    if _next_gp_name.lower() in _gn.lower() or _gn.lower() in _next_gp_name.lower():
                        _default_gp_idx = _gi; break
    except Exception: pass
    gp_actual = c2.selectbox("Seleccionar Gran Premio", GPS_ACTIVOS, index=_default_gp_idx, key="pred_gp")

    # ── Contador de predicciones enviadas para ESTE GP (real) ──────────
    try:
        def _tiene_pred(_res_tuple):
            """True si el formulero tiene alguna predicción con contenido."""
            try:
                _dq, _ds, (_dr, _dc) = _res_tuple
                for _d in (_dq, _ds, _dr, _dc):
                    if isinstance(_d, dict) and any(str(v).strip() for v in _d.values()):
                        return True
            except Exception: pass
            return False
        _cnt_q = 0; _cnt_s = 0; _cnt_r = 0
        _cnt_preds = 0
        _es_sprint_cnt = gp_actual in GPS_SPRINT
        for _pil_cnt in PILOTOS_TORNEO:
            try:
                _r_cnt = _safe_call(mdb["recuperar_predicciones_piloto"], _pil_cnt,
                                    gp_actual, timeout_sec=6,
                                    default=(None,None,(None,None)))
                _dq_c, _ds_c, (_dr_c, _dc_c) = _r_cnt
                _sent_q = isinstance(_dq_c, dict) and any(str(v).strip() for v in _dq_c.values())
                _sent_s = isinstance(_ds_c, dict) and any(str(v).strip() for v in _ds_c.values())
                _sent_r = (isinstance(_dr_c, dict) and any(str(v).strip() for v in _dr_c.values())) or \
                          (isinstance(_dc_c, dict) and any(str(v).strip() for v in _dc_c.values()))
                if _sent_q: _cnt_q += 1
                if _sent_s: _cnt_s += 1
                if _sent_r: _cnt_r += 1
                if _sent_q or _sent_r: _cnt_preds += 1
            except Exception: pass
        _cnt_txt = f"{'🟢'*_cnt_preds}{'⚪'*(len(PILOTOS_TORNEO)-_cnt_preds)}"
        _etapas_txt = f"Q:{_cnt_q}/{len(PILOTOS_TORNEO)}"
        if _es_sprint_cnt: _etapas_txt += f" · Spr:{_cnt_s}/{len(PILOTOS_TORNEO)}"
        _etapas_txt += f" · C:{_cnt_r}/{len(PILOTOS_TORNEO)}"
        st.markdown(
            f'<div style="background:rgba(99,102,241,.08);border:1px solid rgba(99,102,241,.25);'
            f'border-radius:10px;padding:8px 14px;margin:8px 0 6px;">'
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
            f'<span style="font-size:16px;">{_cnt_txt}</span>'
            f'<span style="font-size:12px;color:rgba(169,178,214,.7);">'
            f'<b style="color:#a78bfa;">{_cnt_preds}/{len(PILOTOS_TORNEO)}</b> formuleros con predicciones para este GP</span>'
            f'</div>'
            f'<div style="font-size:11px;color:rgba(169,178,214,.5);">'
            f'📊 {_etapas_txt}</div>'
            f'</div>', unsafe_allow_html=True)
    except Exception: pass

    # ── Circuit preview card with 2025 podium + Wikimedia image ────────
    _CIRCUIT_INFO = {
        "Australia":     {"ciudad":"Albert Park · Melbourne","km":"5.278","vueltas":58,"record":"1:20.235",
                          "p1":"Russell","p2":"Antonelli","p3":"Leclerc","flag":"🇦🇺","color":"#3b82f6",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/a/ad/Albert_Park_Circuit_2021.svg/400px-Albert_Park_Circuit_2021.svg.png"},
        "China":         {"ciudad":"Shanghai International Circuit","km":"5.451","vueltas":56,"record":"1:32.064",
                          "p1":"Russell","p2":"Piastri","p3":"Norris","flag":"🇨🇳","color":"#ef4444",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/5e/Shanghai_Circuit.svg/400px-Shanghai_Circuit.svg.png"},
        "Japón":         {"ciudad":"Suzuka Circuit","km":"5.807","vueltas":53,"record":"1:28.778",
                          "p1":"Verstappen","p2":"Leclerc","p3":"Norris","flag":"🇯🇵","color":"#dc2626",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Suzuka_Circuit_s.svg/400px-Suzuka_Circuit_s.svg.png"},
        "Baréin":        {"ciudad":"Bahrain International Circuit","km":"5.412","vueltas":57,"record":"1:29.179",
                          "p1":"Leclerc","p2":"Piastri","p3":"Norris","flag":"🇧🇭","color":"#D4AF37",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/10/Bahrain_International_Circuit--Grand_Prix_layout.svg/400px-Bahrain_International_Circuit--Grand_Prix_layout.svg.png"},
        "Arabia Saudita":{"ciudad":"Jeddah Corniche Circuit","km":"6.174","vueltas":50,"record":"1:27.653",
                          "p1":"Piastri","p2":"Verstappen","p3":"Leclerc","flag":"🇸🇦","color":"#4ade80",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Jeddah_Corniche_Circuit.svg/400px-Jeddah_Corniche_Circuit.svg.png"},
        "Miami":         {"ciudad":"Miami International Autodrome","km":"5.412","vueltas":57,"record":"1:27.241",
                          "p1":"Piastri","p2":"Norris","p3":"Russell","flag":"🇺🇸","color":"#60a5fa",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/58/Miami_International_Autodrome.svg/400px-Miami_International_Autodrome.svg.png"},
        "Mónaco":        {"ciudad":"Circuit de Monaco","km":"3.337","vueltas":78,"record":"1:12.909",
                          "p1":"Norris","p2":"Leclerc","p3":"Piastri","flag":"🇲🇨","color":"#f97316",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/Circuit_de_Monaco.svg/400px-Circuit_de_Monaco.svg.png"},
        "España":        {"ciudad":"Circuit de Barcelona-Catalunya","km":"4.657","vueltas":66,"record":"1:12.876",
                          "p1":"Norris","p2":"Leclerc","p3":"Piastri","flag":"🇪🇸","color":"#f59e0b",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Circuit_de_Barcelona-Catalunya_%28layout_2007-present%29.svg/400px-Circuit_de_Barcelona-Catalunya_%28layout_2007-present%29.svg.png"},
        "Canadá":        {"ciudad":"Circuit Gilles Villeneuve · Montreal","km":"4.361","vueltas":70,"record":"1:13.078",
                          "p1":"Russell","p2":"Verstappen","p3":"Antonelli","flag":"🇨🇦","color":"#ef4444",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/7/7c/Circuit_Gilles_Villeneuve.svg/400px-Circuit_Gilles_Villeneuve.svg.png"},
        "Gran Bretaña":  {"ciudad":"Silverstone Circuit","km":"5.891","vueltas":52,"record":"1:27.097",
                          "p1":"Norris","p2":"Piastri","p3":"Hulkenberg","flag":"🇬🇧","color":"#3b82f6",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/2/23/Silverstone_Circuit_2010.svg/400px-Silverstone_Circuit_2010.svg.png"},
        "Austria":       {"ciudad":"Red Bull Ring · Spielberg","km":"4.318","vueltas":71,"record":"1:04.204",
                          "p1":"Norris","p2":"Piastri","p3":"Leclerc","flag":"🇦🇹","color":"#ef4444",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/RedBull_Ring_2016.svg/400px-RedBull_Ring_2016.svg.png"},
        "Hungría":       {"ciudad":"Hungaroring · Budapest","km":"4.381","vueltas":70,"record":"1:17.885",
                          "p1":"Russell","p2":"Piastri","p3":"Norris","flag":"🇭🇺","color":"#ef4444",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/a/a5/Hungaroring.svg/400px-Hungaroring.svg.png"},
        "Bélgica":       {"ciudad":"Circuit de Spa-Francorchamps","km":"7.004","vueltas":44,"record":"1:47.765",
                          "p1":"Leclerc","p2":"Piastri","p3":"Norris","flag":"🇧🇪","color":"#f59e0b",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/5/5a/Spa_circuit_2007.svg/400px-Spa_circuit_2007.svg.png"},
        "Países Bajos":  {"ciudad":"Circuit Zandvoort","km":"4.259","vueltas":72,"record":"1:11.097",
                          "p1":"Piastri","p2":"Verstappen","p3":"Hadjar","flag":"🇳🇱","color":"#f97316",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Zandvoort_circuit_2020.svg/400px-Zandvoort_circuit_2020.svg.png"},
        "Italia":        {"ciudad":"Autodromo Nazionale di Monza","km":"5.793","vueltas":53,"record":"1:21.046",
                          "p1":"Leclerc","p2":"Norris","p3":"Piastri","flag":"🇮🇹","color":"#4ade80",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/e7/Monza_track_map.svg/400px-Monza_track_map.svg.png"},
        "Madrid":        {"ciudad":"Circuito de Madrid · Ifema","km":"5.47","vueltas":55,"record":"—",
                          "p1":"—","p2":"—","p3":"—","flag":"🇪🇸","color":"#f97316","img":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/IFEMA_Circuit.svg/400px-IFEMA_Circuit.svg.png"},
        "Azerbaiyán":    {"ciudad":"Baku City Circuit","km":"6.003","vueltas":51,"record":"1:44.407",
                          "p1":"Verstappen","p2":"Russell","p3":"Sainz","flag":"🇦🇿","color":"#60a5fa",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/Baku_Formula_1_circuit.svg/400px-Baku_Formula_1_circuit.svg.png"},
        "Singapur":      {"ciudad":"Marina Bay Street Circuit","km":"4.940","vueltas":62,"record":"1:30.984",
                          "p1":"Verstappen","p2":"Russell","p3":"Norris","flag":"🇸🇬","color":"#ef4444",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Marina_Bay_circuit.svg/400px-Marina_Bay_circuit.svg.png"},
        "Estados Unidos":{"ciudad":"Circuit of the Americas · Austin","km":"5.513","vueltas":56,"record":"1:35.481",
                          "p1":"Verstappen","p2":"Leclerc","p3":"Norris","flag":"🇺🇸","color":"#3b82f6",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/Circuit_of_the_Americas_track_map.svg/400px-Circuit_of_the_Americas_track_map.svg.png"},
        "México":        {"ciudad":"Autodromo Hermanos Rodriguez","km":"4.304","vueltas":71,"record":"1:17.775",
                          "p1":"Verstappen","p2":"Leclerc","p3":"Norris","flag":"🇲🇽","color":"#4ade80",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/9/91/Aut%C3%B3dromo_Hermanos_Rodr%C3%ADguez_circuit.svg/400px-Aut%C3%B3dromo_Hermanos_Rodr%C3%ADguez_circuit.svg.png"},
        "Brasil":        {"ciudad":"Autodromo Jose Carlos Pace · Interlagos","km":"4.309","vueltas":71,"record":"1:10.927",
                          "p1":"Norris","p2":"Antonelli","p3":"Verstappen","flag":"🇧🇷","color":"#f59e0b",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Interlagos_racecircuit.svg/400px-Interlagos_racecircuit.svg.png"},
        "Las Vegas":     {"ciudad":"Las Vegas Strip Circuit","km":"6.201","vueltas":50,"record":"1:33.381",
                          "p1":"Verstappen","p2":"Russell","p3":"Antonelli","flag":"🇺🇸","color":"#a855f7",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/3/31/Las_Vegas_Strip_Circuit.svg/400px-Las_Vegas_Strip_Circuit.svg.png"},
        "Catar":         {"ciudad":"Lusail International Circuit","km":"5.380","vueltas":57,"record":"1:24.319",
                          "p1":"Verstappen","p2":"Piastri","p3":"Sainz","flag":"🇶🇦","color":"#D4AF37",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Losail_International_Circuit.svg/400px-Losail_International_Circuit.svg.png"},
        "Abu Dabi":      {"ciudad":"Yas Marina Circuit","km":"5.281","vueltas":58,"record":"1:23.294",
                          "p1":"Norris","p2":"Piastri","p3":"Leclerc","flag":"🇦🇪","color":"#3b82f6",
                          "img":"https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Yas_Marina_Circuit_2021.svg/400px-Yas_Marina_Circuit_2021.svg.png"},
    }
    _gp_short_ci = gp_actual.split(". ",1)[-1] if ". " in gp_actual else gp_actual
    _gp_short_ci = (_gp_short_ci.replace("Gran Premio de ","").replace("Gran Premio del ","")
                    .replace("Gran Premio ","").replace("Grand Prix","").strip())
    _ci = next((v for k,v in _CIRCUIT_INFO.items()
                if k.lower() in _gp_short_ci.lower() or _gp_short_ci.lower() in k.lower()), None)
    if _ci:
        _ci_clr = _ci.get("color","#3b82f6")
        _ci_img = _ci.get("img","")

        @st.cache_data(ttl=86400, show_spinner=False)
        def _fetch_circuit_img(url):
            try:
                import requests as _rq_ci, base64 as _b64_ci
                _headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "image/png,image/svg+xml,image/*,*/*",
                    "Referer": "https://en.wikipedia.org/"
                }
                _r = _rq_ci.get(url, timeout=12, headers=_headers)
                if _r.status_code == 200 and len(_r.content) > 1000:
                    # Force image/png since Wikimedia thumbnail URLs end in .svg.png
                    _ct = "image/png" if url.endswith(".png") else _r.headers.get("Content-Type","image/png")
                    # Strip charset if present: "image/png; charset=utf-8" -> "image/png"
                    _ct = _ct.split(";")[0].strip()
                    _b64 = _b64_ci.b64encode(_r.content).decode()
                    return f"data:{_ct};base64,{_b64}"
            except Exception: pass
            return ""

        _ci_data = _fetch_circuit_img(_ci_img) if _ci_img else ""
        _img_html = (
            f'<div style="flex:0 0 auto;width:155px;display:flex;align-items:center;' +
            f'justify-content:center;background:rgba(255,255,255,.02);' +
            f'border-left:1px solid {_ci_clr}22;padding:8px;">' +
            f'<img src="{_ci_data}" style="max-height:115px;max-width:145px;' +
            f'object-fit:contain;filter:brightness(0) invert(1) opacity(.7);">' +
            f'</div>'
        ) if _ci_data else ""

        st.markdown(
            f'<div style="background:linear-gradient(135deg,rgba(6,15,40,.92),rgba(10,20,55,.97));' +
            f'border:1px solid {_ci_clr}44;border-radius:12px;margin:8px 0 14px;' +
            f'display:flex;align-items:stretch;overflow:hidden;">' +
            f'<div style="flex:1;padding:12px 16px;">' +
            f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">' +
            f'<span style="font-size:18px;">{_ci["flag"]}</span>' +
            f'<div><div style="font-size:12px;font-weight:900;color:#ffdd7a;">{_ci["ciudad"]}</div>' +
            f'<div style="font-size:9px;color:rgba(169,178,214,.5);">Circuito · Podio 2025</div></div></div>' +
            f'<div style="display:flex;gap:6px;flex-wrap:wrap;">' +
            f'<div style="background:{_ci_clr}12;border:1px solid {_ci_clr}30;border-radius:8px;padding:5px 9px;text-align:center;">' +
            f'<div style="font-size:11px;font-weight:900;color:#e8ecff;">{_ci["km"]} km</div>' +
            f'<div style="font-size:8px;color:rgba(169,178,214,.4);">Longitud</div></div>' +
            f'<div style="background:{_ci_clr}12;border:1px solid {_ci_clr}30;border-radius:8px;padding:5px 9px;text-align:center;">' +
            f'<div style="font-size:11px;font-weight:900;color:#e8ecff;">{_ci["vueltas"]}</div>' +
            f'<div style="font-size:8px;color:rgba(169,178,214,.4);">Vueltas</div></div>' +
            f'<div style="background:{_ci_clr}12;border:1px solid {_ci_clr}30;border-radius:8px;padding:5px 9px;text-align:center;">' +
            f'<div style="font-size:11px;font-weight:900;color:#e8ecff;">{_ci["record"]}</div>' +
            f'<div style="font-size:8px;color:rgba(169,178,214,.4);">Récord vuelta</div></div>' +
            f'<div style="background:rgba(212,175,55,.1);border:1px solid rgba(212,175,55,.3);border-radius:8px;padding:5px 9px;">' +
            f'<div style="font-size:9px;color:rgba(212,175,55,.6);margin-bottom:2px;">🏆 Podio 2025</div>' +
            f'<div style="font-size:10px;font-weight:900;color:#D4AF37;">1° {_ci["p1"]}</div>' +
            f'<div style="font-size:10px;color:#93c5fd;">2° {_ci["p2"]} · 3° {_ci["p3"]}</div>' +
            f'</div></div></div>' +
            _img_html +
            f'</div>', unsafe_allow_html=True)



    estado = _safe_call(
        mcore["obtener_estado_gp"], gp_actual, HORARIOS_CARRERA, TZ,
        timeout_sec=4, default={"habilitado": True, "mensaje": "(sin datos)"}
    )
    if not (estado or {}).get("habilitado", True):
        # ── PREDICCIONES CERRADAS ────────────────────────────────────────
        _gp_short = gp_actual.split(". ",1)[-1] if ". " in gp_actual else gp_actual
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#1a0606,#2d0a0a,#1a0606);'
            f'border:2px solid rgba(239,68,68,.4);border-radius:18px;'
            f'padding:24px;text-align:center;margin:12px 0;">'
            f'<div style="font-size:40px;margin-bottom:10px;">🔴</div>'
            f'<div style="font-size:20px;font-weight:900;color:#ef4444;letter-spacing:.08em;margin-bottom:6px;">'
            f'PREDICCIONES CERRADAS</div>'
            f'<div style="font-size:15px;font-weight:700;color:#D4AF37;margin-bottom:4px;">{_gp_short}</div>'
            f'<div style="font-size:11px;color:rgba(169,178,214,.55);">'
            f'{(estado or {}).get("mensaje","El período de predicciones ha finalizado.")}</div>'
            f'</div>', unsafe_allow_html=True)
        return
    else:
        # ── PREDICCIONES ABIERTAS ────────────────────────────────────────
        _gp_short2 = gp_actual.split(". ",1)[-1] if ". " in gp_actual else gp_actual
        _open_msg = (estado or {}).get("mensaje","")
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#061a0a,#0a2d12,#061a0a);'
            f'border:2px solid rgba(74,222,128,.35);border-radius:14px;'
            f'padding:12px 18px;display:flex;align-items:center;gap:12px;margin-bottom:12px;">'
            f'<div style="width:12px;height:12px;border-radius:50%;background:#4ade80;'
            f'box-shadow:0 0 10px #4ade80;flex-shrink:0;animation:podBounce 1s ease-in-out infinite;"></div>'
            f'<div><div style="font-size:13px;font-weight:900;color:#4ade80;">PREDICCIONES ABIERTAS</div>'
            f'<div style="font-size:10px;color:rgba(169,178,214,.55);">{_gp_short2}'
            f'{" · "+_open_msg if _open_msg else ""}</div></div>'
            f'</div>', unsafe_allow_html=True)

    es_sprint = gp_actual in GPS_SPRINT
    if es_sprint:
        st.markdown(
            '<div style="background:linear-gradient(90deg,rgba(168,85,247,.12),rgba(168,85,247,.05));'
            'border-left:3px solid #a855f7;border-radius:0 10px 10px 0;'
            'padding:10px 16px;margin-bottom:10px;display:flex;align-items:center;gap:8px;">'
            '<span style="font-size:18px;">⚡</span>'
            '<div><div style="font-size:12px;font-weight:900;color:#c084fc;">FIN DE SEMANA SPRINT</div>'
            '<div style="font-size:10px;color:rgba(169,178,214,.5);">Este GP incluye Sprint Race</div></div>'
            '</div>', unsafe_allow_html=True)

    # ── PIN Section ─────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(90deg,rgba(59,130,246,.08),transparent);'
        'border-left:3px solid #3b82f6;border-radius:0 10px 10px 0;'
        'padding:8px 14px;margin:10px 0 6px;">'
        '<div style="font-size:10px;font-weight:800;color:#3b82f6;letter-spacing:.12em;'
        'text-transform:uppercase;">🔐 Verificación de identidad</div></div>', unsafe_allow_html=True)
    pin = st.text_input("Ingresá tu PIN (4 dígitos):", type="password", max_chars=4, key="pred_pin",
                        placeholder="••••")

    nn           = mcore.get("normalizar_nombre", lambda x: x)
    drivers_all  = [d for t in GRILLA_2026.values() for d in t]
    drivers_sprint = drivers_all  # Sprint usa todos los pilotos igual que carrera
    teams_all    = list(GRILLA_2026.keys())

    def _has(d): return isinstance(d, dict) and any(str(v).strip() for v in d.values())

    def ya_envio(u, gp, etapa):
        try:
            res = _safe_call(mdb["recuperar_predicciones_piloto"], u, gp,
                             timeout_sec=6, default=(None, None, (None, None)))
            dq, ds, (dr, dc) = res
            e = (etapa or "").upper()
            if e == "QUALY":   return _has(dq)
            if e == "SPRINT":  return _has(ds)
            if e == "CARRERA": return _has(dr) or _has(dc)
        except: pass
        return False

    def usel(options, count, kp, lp):
        sel = {}
        for i in range(1, count + 1):
            used  = [v for k, v in sel.items() if k < i and v]
            cur   = st.session_state.get(f"{kp}_{i}", "")
            avail = [o for o in options if o not in used or o == cur]
            sel[i] = st.selectbox(
                f"{lp} {i}°", [""] + avail, key=f"{kp}_{i}",
                format_func=lambda x: "— Seleccionar —" if x == "" else x
            )
        return sel

    # ── Prefijos de clave para session_state ──────────────
    kp_q = f"q_{gp_actual}_{usuario}"
    kp_s = f"s_{gp_actual}_{usuario}"
    kp_r = f"r_{gp_actual}_{usuario}"
    kp_c = f"c_{gp_actual}_{usuario}"

    # ── Preload existing predictions once (avoid reloading on every rerun) ─
    _preload_key = f"_pred_preloaded_{gp_actual}_{usuario}"
    if not st.session_state.get(_preload_key) and "_error" not in mdb:
        try:
            _existing = _safe_call(mdb["recuperar_predicciones_piloto"], usuario, gp_actual,
                                   timeout_sec=12, default=(None,None,(None,None)))
            _dq_ex, _ds_ex, (_dr_ex, _dc_ex) = _existing
            # Pre-populate session state if empty
            if _dq_ex and kp_q not in st.session_state:
                st.session_state[kp_q] = _dq_ex
            if _ds_ex and kp_s not in st.session_state:
                st.session_state[kp_s] = _ds_ex
            if _dr_ex and kp_r not in st.session_state:
                st.session_state[kp_r] = _dr_ex
            if _dc_ex and kp_c not in st.session_state:
                st.session_state[kp_c] = _dc_ex
            st.session_state[_preload_key] = True
        except Exception: pass

    if es_sprint:
        tab_q, tab_s, tab_r = st.tabs(["⏱️ Clasificación", "⚡ Sprint", "🏁 Carrera"])
    else:
        tab_q, tab_r = st.tabs(["⏱️ Clasificación", "🏁 Carrera"])
        tab_s = None

    # ═══════════════════════════════════════════════════════
    # TAB QUALY
    # ═══════════════════════════════════════════════════════
    with tab_q:
        st.markdown(
            '<div style="background:linear-gradient(90deg,rgba(212,175,55,.1),transparent);'
            'border-left:3px solid #D4AF37;border-radius:0 10px 10px 0;'
            'padding:10px 16px;margin-bottom:12px;">'
            '<div style="font-size:13px;font-weight:900;color:#D4AF37;">⏱️ CLASIFICACIÓN</div>'
            '<div style="font-size:10px;color:rgba(169,178,214,.5);">'
            '1°→15pts  2°→10pts  3°→7pts  4°→5pts  5°→3pts  |  <span style="color:#D4AF37;">Pleno +5</span></div>'
            '</div>', unsafe_allow_html=True)

        cd = None
        if True:
            q_data = modal_pilot_selector(drivers_all, 5, kp_q)
            st.markdown("---")
            # ── Regla Colapinto ──────────────────────
            _col_photo = DRIVER_HEADSHOTS.get("Franco Colapinto","")
            _col_tc    = TEAM_COLORS.get("ALPINE","#FF4FD8")
            _col_logo = TEAM_LOGOS_CDN.get("ALPINE","")
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:center;"
                f"gap:12px;margin:8px 0;position:relative;"
                f"background:rgba(255,79,216,.08);border:1px solid rgba(255,79,216,.35);"
                f"border-radius:12px;padding:10px 14px;'>"
                f"<img src='{_col_photo}' style='width:48px;height:48px;border-radius:50%;object-fit:cover;border:2px solid {_col_tc};flex-shrink:0;'>"
                f"<div style='text-align:center;'><div style='font-size:12px;font-weight:800;color:#FF4FD8;'>🇦🇷 Franco Colapinto</div>"
                f"<div style='font-size:9px;color:rgba(232,236,255,.6);'>Regla especial</div></div>"
                + (f"<img src='{_col_logo}' style='height:20px;max-width:54px;object-fit:contain;opacity:.85;flex-shrink:0;'>" if _col_logo else "")
                + f"</div>",
                unsafe_allow_html=True
            )
            # ── Colapinto selector ─────────────────────────
            _col_pos_q = st.selectbox(
                "🇦🇷 Posición de Franco Colapinto:",
                list(range(1, 23)),
                index=9,
                key=f"cq-{gp_actual}-{usuario}",
                format_func=lambda x: f"P{x}"
            )
            q_data["colapinto_q"] = _col_pos_q
            if gp_actual == "01. Gran Premio de Australia":
                st.markdown("---")
                st.error("🚨 **EDICIÓN ESPECIAL AUSTRALIA — Campeones 2026**")
                cc1, cc2_a = st.columns(2)
                cp_ = cc1.selectbox(
                    "🏆 Piloto campeón", [""] + drivers_all,
                    key=f"camp_p_{gp_actual}_{usuario}",
                    format_func=lambda x: "— Seleccionar —" if x == "" else x
                )
                ce_ = cc2_a.selectbox(
                    "🏗️ Constructor campeón", [""] + teams_all,
                    key=f"camp_e_{gp_actual}_{usuario}",
                    format_func=lambda x: "— Seleccionar —" if x == "" else x
                )
                cd = {"piloto": (cp_ or "").strip(), "equipo": (ce_ or "").strip()}


        ya_q = ya_envio(usuario, gp_actual, "QUALY")
        if ya_q:
            st.success("✅ Ya enviaste la predicción de **QUALY** para este GP.")
        # ── Resumen visual pre-envío ──────────────────────
        if not ya_q:
            _q_filled = [q_data.get(i,"") for i in range(1,6)]
            if all(_q_filled):
                _q_names = " · ".join([f"**P{i}** {q_data[i]}" for i in range(1,6)])
                st.markdown(
                    f"<div style='background:rgba(0,255,100,.06);border:1px solid rgba(0,255,100,.25);"
                    f"border-radius:10px;padding:8px 12px;font-size:11px;margin-bottom:6px;'>"
                    f"✅ <b>Resumen Qualy:</b> {_q_names}</div>",
                    unsafe_allow_html=True
                )
        if st.button("🚀 ENVIAR QUALY", use_container_width=True,
                     key=f"btn_q-{gp_actual}-{usuario}", disabled=ya_q):
            if not pin or len(str(pin).strip()) < 4:
                st.error("⛔ Ingresá tu PIN de 4 dígitos.")
            elif not _safe_call(mauth["verify_pin"], usuario, pin, timeout_sec=30, default=False):
                st.error("⛔ PIN INCORRECTO — verificá y reintentá.")
            elif any(not q_data.get(i) for i in range(1, 6)):
                st.error("⚠️ Completá las 5 posiciones.")
            elif gp_actual == "01. Gran Premio de Australia" and (
                    not cd or not cd["piloto"] or not cd["equipo"]):
                st.error("⚠️ Completá piloto y constructor campeón.")
            else:
                args = (usuario, gp_actual, "QUALY", q_data, cd) if cd else (usuario, gp_actual, "QUALY", q_data)
                try:
                    ok, msg = mdb["guardar_etapa"](*args)
                except Exception as _ge: ok, msg = False, f"Error al guardar: {_ge}"
                if ok:
                    _q_res = " · ".join([f"P{i} {q_data[i]}" for i in range(1,6)])
                    _q_res += f"\n🇦🇷 Colapinto: P{q_data.get('colapinto_q','?')}"
                    st.success(msg); st.balloons()
                    _send_prediccion_email(usuario, gp_actual, "QUALY", _q_res)
                    st.session_state["_wa_pending"] = (gp_actual, "QUALY", _q_res, usuario)
                    st.rerun()
                else:
                    st.error(msg)
    # ═══════════════════════════════════════════════════════
    if tab_s is not None:
        with tab_s:
            st.markdown(
                '<div style="background:linear-gradient(90deg,rgba(168,85,247,.1),transparent);'
                'border-left:3px solid #a855f7;border-radius:0 10px 10px 0;'
                'padding:10px 16px;margin-bottom:12px;">'
                '<div style="font-size:13px;font-weight:900;color:#c084fc;">⚡ SPRINT RACE</div>'
                '<div style="font-size:10px;color:rgba(169,178,214,.5);">'
                '1°→8pts  2°→7pts  3°→6pts  4°→5pts  5°→4pts  6°→3pts  7°→2pts  8°→1pt  |  <span style="color:#c084fc;">Pleno +3</span></div>'
                '</div>', unsafe_allow_html=True)
            st.info("1°(8)  2°(7)  3°(6)  4°(5)  5°(4)  6°(3)  7°(2)  8°(1)  |  Pleno +3 Pts")

            if True:
                s_data = modal_pilot_selector(drivers_sprint, 8, kp_s)


            ya_s = ya_envio(usuario, gp_actual, "SPRINT")
            if ya_s:
                st.success("✅ Ya enviaste la predicción de **SPRINT**.")
            if not ya_s:
                _s_filled = [s_data.get(i,"") for i in range(1,9)]
                if all(_s_filled):
                    _s_names = " · ".join([f"P{i} {s_data[i]}" for i in range(1,9)])
                    st.markdown(
                        f"<div style='background:rgba(0,255,100,.06);border:1px solid rgba(0,255,100,.25);"
                        f"border-radius:10px;padding:8px 12px;font-size:11px;margin-bottom:6px;'>"
                        f"✅ <b>Resumen Sprint:</b> {_s_names}</div>",
                        unsafe_allow_html=True
                    )
            if st.button("🚀 ENVIAR SPRINT", use_container_width=True,
                         key=f"btn_s-{gp_actual}-{usuario}", disabled=ya_s):
                if not _safe_call(mauth["verify_pin"], usuario, pin, timeout_sec=30, default=False):
                    st.error("⛔ PIN INCORRECTO")
                elif any(not s_data.get(i) for i in range(1, 9)):
                    st.error("⚠️ Completá las 8 posiciones.")
                else:
                    try:
                        ok, msg = mdb["guardar_etapa"](usuario, gp_actual, "SPRINT", s_data)
                    except Exception as _ge: ok, msg = False, f"Error al guardar: {_ge}"
                    if ok:
                        _s_res = " · ".join([f"P{i} {s_data[i]}" for i in range(1,9)])
                        st.success(msg); st.balloons()
                        _send_prediccion_email(usuario, gp_actual, "SPRINT", _s_res)
                        st.session_state["_wa_pending"] = (gp_actual, "SPRINT", _s_res, usuario)
                        st.session_state[f"_sprint_sent_{gp_actual}_{usuario}"] = True
                        st.info("⚡ Sprint enviado. El mensaje de WhatsApp aparecerá al recargar.")
                    else:
                        st.error(msg)
    # ═══════════════════════════════════════════════════════
    with tab_r:
        st.markdown(
            '<div style="background:linear-gradient(90deg,rgba(74,222,128,.1),transparent);'
            'border-left:3px solid #4ade80;border-radius:0 10px 10px 0;'
            'padding:10px 16px;margin-bottom:12px;">'
            '<div style="font-size:13px;font-weight:900;color:#4ade80;">🏁 CARRERA</div>'
            '<div style="font-size:10px;color:rgba(169,178,214,.5);">'
            '1°→25  2°→18  3°→15  4°→12  5°→10  6°→8  7°→6  8°→4  9°→2  10°→1  |  <span style="color:#4ade80;">Pleno +5</span></div>'
            '</div>', unsafe_allow_html=True)

        if True:
            r_top = modal_pilot_selector(drivers_all, 10, kp_r)
            st.markdown("---")
            # ── Regla Colapinto ──────────────────────
            _col_photo2 = DRIVER_HEADSHOTS.get("Franco Colapinto","")
            _col_tc2    = TEAM_COLORS.get("ALPINE","#FF4FD8")
            _col_logo2 = TEAM_LOGOS_CDN.get("ALPINE","")
            st.markdown(
                f"<div style='display:flex;align-items:center;justify-content:center;"
                f"gap:12px;margin:8px 0;position:relative;"
                f"background:rgba(255,79,216,.08);border:1px solid rgba(255,79,216,.35);"
                f"border-radius:12px;padding:10px 14px;'>"
                f"<img src='{_col_photo2}' style='width:48px;height:48px;border-radius:50%;object-fit:cover;border:2px solid {_col_tc2};flex-shrink:0;'>"
                f"<div style='text-align:center;'><div style='font-size:12px;font-weight:800;color:#FF4FD8;'>🇦🇷 Franco Colapinto</div>"
                f"<div style='font-size:9px;color:rgba(232,236,255,.6);'>Regla especial — posición aparte</div></div>"
                + (f"<img src='{_col_logo2}' style='height:20px;max-width:54px;object-fit:contain;opacity:.85;flex-shrink:0;'>" if _col_logo2 else "")
                + f"</div>",
                unsafe_allow_html=True
            )
            # ── Colapinto selector ─────────────────────────
            _col_pos_r = st.selectbox(
                "🇦🇷 Posición de Franco Colapinto:",
                list(range(1, 23)),
                index=9,
                key=f"cr-{gp_actual}-{usuario}",
                format_func=lambda x: f"P{x}"
            )
            col_r = _col_pos_r


        # ── CONSTRUCTORES ────────────────────────────────────
        st.markdown(
            '<hr style="border:none;border-top:1px solid rgba(246,195,73,.18);margin:18px 0;">',
            unsafe_allow_html=True
        )
        st.subheader("🏗️ Constructores")
        st.info("1°(10)  2°(5)  3°(2)  |  Pleno +3 Pts")

        if True:
            c_top = modal_constructor_selector(teams_all, 3, kp_c)


        # ── Combinar datos y enviar ──────────────────────────
        r_data = dict(r_top)
        r_data["colapinto_r"] = col_r
        r_data["c1"], r_data["c2"], r_data["c3"] = c_top[1], c_top[2], c_top[3]

        ya_r = ya_envio(usuario, gp_actual, "CARRERA")
        if ya_r:
            st.success("✅ Ya enviaste la predicción de **CARRERA/CONSTRUCTORES**.")
        if not ya_r:
            _r_filled = [r_top.get(i,"") for i in range(1,11)]
            _c_filled = [c_top.get(j,"") for j in range(1,4)]
            if all(_r_filled) and all(_c_filled):
                _r_names = ", ".join([f"P{i} {r_top[i]}" for i in range(1,11)])
                _c_names = f"1° {c_top.get(1,'?')} · 2° {c_top.get(2,'?')} · 3° {c_top.get(3,'?')}"
                st.markdown(
                    f"<div style='background:rgba(0,255,100,.06);border:1px solid rgba(0,255,100,.25);"
                    f"border-radius:10px;padding:8px 12px;font-size:11px;margin-bottom:6px;'>"
                    f"✅ <b>Carrera:</b> {_r_names}<br>"
                    f"🏗️ <b>Constructores:</b> {_c_names}</div>",
                    unsafe_allow_html=True
                )
        if st.button("🚀 ENVIAR CARRERA Y CONSTRUCTORES", use_container_width=True,
                     key=f"btn_r-{gp_actual}-{usuario}", disabled=ya_r):
            if not _safe_call(mauth["verify_pin"], usuario, pin, timeout_sec=30, default=False):
                st.error("⛔ PIN INCORRECTO")
            elif any(not r_data.get(i) for i in range(1, 11)):
                st.error("⚠️ Completá las 10 posiciones.")
            elif not r_data["c1"] or not r_data["c2"] or not r_data["c3"]:
                st.error("⚠️ Completá top 3 Constructores.")
            else:
                try:
                    ok, msg = mdb["guardar_etapa"](usuario, gp_actual, "CARRERA", r_data)
                except Exception as _ge: ok, msg = False, f"Error al guardar: {_ge}"
                if ok:
                    _r_res  = " · ".join([f"P{i} {r_data[i]}" for i in range(1,11)])
                    _r_res += f"\n🏗️ Constructores: {r_data.get('c1','?')} / {r_data.get('c2','?')} / {r_data.get('c3','?')}"
                    _col_r  = r_data.get("colapinto_r","")
                    if _col_r: _r_res += f"\n🇦🇷 Colapinto: P{_col_r}"
                    st.success(msg); st.balloons()
                    _send_prediccion_email(usuario, gp_actual, "CARRERA", _r_res)
                    st.session_state["_wa_pending"] = (gp_actual, "CARRERA", _r_res, usuario)
                    st.rerun()
                else:
                    st.error(msg)


def _do_wa_email(df_h, oficial, gp_calc, mdb):
    """Genera botones WA con aciertos por piloto y envío de emails."""
    import re as _re_w, urllib.parse as _up_w
    try:
        from core.utils import normalizar_nombre as _nn_w
    except Exception:
        _nn_w = lambda x: str(x or "").strip().lower()

    of_r = {i: oficial.get(f"r{i}","") for i in range(1,11)}
    of_q = {i: oficial.get(f"q{i}","") for i in range(1,6)}
    of_c = {i: oficial.get(f"c{i}","") for i in range(1,4)}
    of_s = {i: oficial.get(f"s{i}","") for i in range(1,9)}
    col_q_r = str(oficial.get("col_q","")).strip()
    col_r_r = str(oficial.get("col_r","")).strip()
    gp_lbl = _re_w.sub(r'^\d+\.\s*','', gp_calc).strip()
    FLAGS = {"Australia":"🇦🇺","China":"🇨🇳","Japón":"🇯🇵","Miami":"🇺🇸","Canadá":"🇨🇦",
             "Mónaco":"🇲🇨","España":"🇪🇸","Austria":"🇦🇹","Gran Bretaña":"🇬🇧","Bélgica":"🇧🇪",
             "Hungría":"🇭🇺","Países Bajos":"🇳🇱","Italia":"🇮🇹","Madrid":"🇪🇸","Azerbaiyán":"🇦🇿",
             "Singapur":"🇸🇬","México":"🇲🇽","Brasil":"🇧🇷","Las Vegas":"🇺🇸","Qatar":"🇶🇦","Abu Dabi":"🇦🇪"}
    fl = next((v for k,v in FLAGS.items() if k.lower() in gp_lbl.lower()),"🏁")
    MED = {0:"🥇",1:"🥈",2:"🥉",3:"4°",4:"5°"}
    ESCALA_Q = {1:15,2:10,3:7,4:5,5:3}
    ESCALA_R = {1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}
    ESCALA_S = {1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1}
    ESCALA_C = {1:10,2:5,3:2}

    # Leer predicciones
    preds = {}
    for pil in PILOTOS_TORNEO:
        try:
            r = _safe_call(mdb["recuperar_predicciones_piloto"], pil, gp_calc,
                           timeout_sec=15, default=(None,None,(None,None)))
            dq,ds,(dr,dc) = r
            flat = {}
            for src_d, key_pfx in [(dq,"q"),(dr,"p"),(dc,"c"),(ds,"spr")]:
                if isinstance(src_d,dict):
                    for k,v in src_d.items():
                        flat[f"{key_pfx}{k}" if str(k).isdigit() else k] = v
            if flat: preds[pil] = flat
        except Exception: pass

    def _msg(pil, total_pts):
        flat = preds.get(pil, {})
        L = [f"🏎️ *TORNEO FEFE WOLF 2026*",
             f"{fl} *{gp_lbl.upper()}* — Predicciones de *{pil}*",
             f"🏆 *TOTAL: {total_pts} pts*",
             f"━━━━━━━━━━━━━━━━━━━━━━"]
        def _sec(titulo, rng, pfx, of_d, esc, pleno_pts=0):
            rows = [(i, str(flat.get(f"{pfx}{i}","")).strip()) for i in rng if flat.get(f"{pfx}{i}","")]
            if not rows: return
            L.append(f"\n{titulo}")
            sub = 0; aciertos = 0
            for i, pv in rows:
                rv = str(of_d.get(i,"")).strip()
                ok = "✅" if (pv and rv and _nn_w(pv)==_nn_w(rv)) else "❌"
                pts = esc.get(i,0) if ok=="✅" else 0; sub += pts
                if ok == "✅": aciertos += 1
                L.append(f"  P{i} {pv} {ok}{(' (+'+str(pts)+')') if pts else ''}")
            # Pleno bonus
            if pleno_pts and aciertos == len(list(rng)):
                sub += pleno_pts
                L.append(f"  🎯 *PLENO PERFECTO! +{pleno_pts} bonus*")
            if sub: L.append(f"  💰 *Subtotal: +{sub} pts*")
        _sec("⏱️ *CLASIFICACIÓN:*", range(1,6), "q", of_q, ESCALA_Q, pleno_pts=5)
        cqp = str(flat.get("colapinto_q","")).strip()
        if cqp: L.append(f"  🇦🇷 Colapinto P{cqp} {'✅ (+10)' if col_q_r and cqp==col_q_r else '❌'}")
        if gp_calc in GPS_SPRINT:
            _sec("⚡ *SPRINT:*", range(1,9), "spr", of_s, ESCALA_S, pleno_pts=3)
        _sec("🏁 *CARRERA:*", range(1,11), "p", of_r, ESCALA_R, pleno_pts=5)
        crp = str(flat.get("colapinto_r","")).strip()
        if crp: L.append(f"  🇦🇷 Colapinto P{crp} {'✅ (+20)' if col_r_r and crp==col_r_r else '❌'}")
        _sec("🏗️ *CONSTRUCTORES:*", range(1,4), "c", of_c, ESCALA_C, pleno_pts=3)
        L += ["","━━━━━━━━━━━━━━━━━━━━━━",
              f"🏆 *TOTAL: {total_pts} pts*", "🏁 _torneofefewolf2026.streamlit.app_"]
        return "\n".join(L)

    sorted_h = df_h.sort_values("Total",ascending=False).reset_index(drop=True)
    # Load detalle for pleno detection
    df_det_for_pleno = None
    try:
        _fn_det_p = mdb.get("leer_historial_detalle_df")
        if callable(_fn_det_p):
            df_det_for_pleno = _safe_call(_fn_det_p, timeout_sec=8, default=None)
    except Exception: pass

    # Resumen general
    gen_lines = [f"🏎️ *TORNEO FEFE WOLF 2026*",
                 f"{fl} *{gp_lbl.upper()}* — TABLA FINAL","━━━━━━━━━━━━━━━━━━━━━━"]
    for ri, rr in sorted_h.iterrows():
        spr = f" Spr:{int(rr.get('Sprint',0))}" if gp_calc in GPS_SPRINT else ""
        gen_lines.append(f"{MED.get(ri,str(ri+1)+'°')} *{rr['Piloto']}*: {int(rr['Total'])} pts"
                         f" _(Q:{int(rr.get('Qualy',0))} C:{int(rr.get('Carrera',0))} "
                         f"Const:{int(rr.get('Const',0))}{spr})_")
    gen_lines += ["━━━━━━━━━━━━━━━━━━━━━━","🏁 _torneofefewolf2026.streamlit.app_"]
    gen_txt = "\n".join(gen_lines)
    gen_url = "https://wa.me/?text=" + _up_w.quote(gen_txt)

    st.markdown("---")
    st.markdown("**📲 Compartir por WhatsApp**")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<a href="{gen_url}" target="_blank" style="display:block;text-align:center;'
                    f'background:linear-gradient(135deg,#075e54,#25d366);color:#fff;font-weight:800;'
                    f'font-size:13px;padding:11px;border-radius:12px;text-decoration:none;">'
                    f'📲 Resumen general</a>', unsafe_allow_html=True)
    with c2:
        gm_u = st.secrets.get("GMAIL_USER",""); gm_p = st.secrets.get("GMAIL_APP_PASSWORD","")
        emails = st.secrets.get("emails",{})
        if st.button("📧 Enviar aciertos por email a todos", key=f"btn_email_{gp_calc}",
                     use_container_width=True):
            if not gm_u or not emails:
                st.warning("Configurá GMAIL_USER y emails en secrets.")
            else:
                import smtplib; from email.mime.text import MIMEText
                sent = 0
                for pil_e, em_e in emails.items():
                    if not em_e: continue
                    row_e = sorted_h[sorted_h["Piloto"]==pil_e]
                    pts_e = int(row_e["Total"].iloc[0]) if not row_e.empty else 0
                    body = _msg(pil_e, pts_e).replace("*","").replace("_","")
                    try:
                        msg = MIMEText(body,"plain","utf-8")
                        msg["Subject"] = f"🏎️ Torneo Fefe Wolf — {gp_lbl} — Tus aciertos"
                        msg["From"] = f"Torneo Fefe Wolf <{gm_u}>"
                        msg["To"] = em_e
                        with smtplib.SMTP_SSL("smtp.gmail.com",465) as sv:
                            sv.login(gm_u,gm_p); sv.sendmail(gm_u,em_e,msg.as_string())
                        sent += 1
                    except Exception as ee: st.warning(f"Error {pil_e}: {ee}")
                st.success(f"✅ {sent} emails enviados con aciertos individuales.")
                # ── Send pleno notifications — solo cuando hubo pleno real ─
                pleno_pils = []
                for _pil_ep in PILOTOS_TORNEO:
                    _row_ep = sorted_h[sorted_h["Piloto"]==_pil_ep]
                    if _row_ep.empty: continue
                    _pts_ep = int(_row_ep["Total"].iloc[0])
                    # Detect pleno: check HistorialDetalle for "PLENO" bonus row
                    if df_det_for_pleno is not None:
                        try:
                            _det_ep = df_det_for_pleno.copy()
                            _det_ep.columns=[c.lower().strip() for c in _det_ep.columns]
                            _pleno_rows = _det_ep[
                                (_det_ep.get("piloto",pd.Series(dtype=str)).astype(str)==_pil_ep) &
                                (_det_ep.get("gp",pd.Series(dtype=str)).astype(str)==gp_calc) &
                                (_det_ep.get("etapa",pd.Series(dtype=str)).str.upper().isin(["PLENO","BONUS_PLENO","PLENO_BONUS"]))
                            ]
                            if not _pleno_rows.empty:
                                pleno_pils.append((_pil_ep, _pts_ep))
                        except Exception: pass
                if pleno_pils and gm_u and emails:
                    for _pp, _pp_pts in pleno_pils:
                        _pp_email = emails.get(_pp,"")
                        if not _pp_email: continue
                        try:
                            _pp_body = (f"🎯 TORNEO FEFE WOLF 2026\n\n"
                                        f"¡¡{_pp.upper()}, TUVISTE PLENO!!\n\n"
                                        f"🏁 {gp_lbl}\n"
                                        f"💰 Sumaste {_pp_pts} pts esta fecha\n\n"
                                        f"torneofefewolf2026.streamlit.app")
                            _pp_msg = MIMEText(_pp_body,"plain","utf-8")
                            _pp_msg["Subject"] = f"🎯 ¡Pleno! {gp_lbl} — Torneo Fefe Wolf"
                            _pp_msg["From"] = f"Torneo Fefe Wolf <{gm_u}>"
                            _pp_msg["To"] = _pp_email
                            with smtplib.SMTP_SSL("smtp.gmail.com",465) as _sv_pp:
                                _sv_pp.login(gm_u,gm_p); _sv_pp.sendmail(gm_u,_pp_email,_pp_msg.as_string())
                        except Exception: pass

                # ── Notificación "rival te superó" ──────────────────────
                if gm_u and emails:
                    try:
                        _mdb_rival = _mod_db()
                        _tabla_rival = _safe_call(_mdb_rival.get("leer_tabla_posiciones", lambda *a: None),
                                                   PILOTOS_TORNEO, timeout_sec=10, default=None)
                        if _tabla_rival is not None and not _tabla_rival.empty:
                            _tr = _tabla_rival.sort_values("Puntos",ascending=False).reset_index(drop=True)
                            _ranking_str = "\n".join(
                                f"  {i+1}° {r['Piloto']} — {int(r['Puntos'])} pts"
                                for i, r in _tr.iterrows())
                            for _ri2, _rrow2 in _tr.iterrows():
                                _pil_r = str(_rrow2["Piloto"])
                                _em_r = emails.get(_pil_r,"")
                                if not _em_r: continue
                                if _ri2 == 0:
                                    _lider_msg = (f"👑 TORNEO FEFE WOLF 2026\n\n"
                                                  f"🏆 ¡{_pil_r.upper()} SIGUE EN LA CIMA!\n\n"
                                                  f"🏁 {gp_lbl}\n\n"
                                                  f"📊 TABLA GENERAL:\n{_ranking_str}\n\n"
                                                  f"torneofefewolf2026.streamlit.app")
                                    _s_r = f"👑 ¡Seguís líder! {gp_lbl}"
                                else:
                                    _rival_delante = str(_tr.iloc[_ri2-1]["Piloto"])
                                    _pts_diff = int(_tr.iloc[_ri2-1]["Puntos"]) - int(_rrow2["Puntos"])
                                    _lider_msg = (f"⚡ TORNEO FEFE WOLF 2026\n\n"
                                                  f"📈 {_rival_delante.upper()} TE SUPERÓ EN LA TABLA\n"
                                                  f"Estás P{_ri2+1} — a {_pts_diff} pts de {_rival_delante}\n\n"
                                                  f"🏁 {gp_lbl}\n\n"
                                                  f"📊 TABLA GENERAL:\n{_ranking_str}\n\n"
                                                  f"torneofefewolf2026.streamlit.app")
                                    _s_r = f"⚡ {_rival_delante} te superó — {gp_lbl}"
                                try:
                                    _rm = MIMEText(_lider_msg,"plain","utf-8")
                                    _rm["Subject"] = _s_r + " — Torneo Fefe Wolf"
                                    _rm["From"] = f"Torneo Fefe Wolf <{gm_u}>"
                                    _rm["To"] = _em_r
                                    with smtplib.SMTP_SSL("smtp.gmail.com",465) as _sv_r:
                                        _sv_r.login(gm_u,gm_p); _sv_r.sendmail(gm_u,_em_r,_rm.as_string())
                                except Exception: pass
                    except Exception: pass

    st.markdown("**📲 Aciertos individuales por piloto**")
    icols = st.columns(len(PILOTOS_TORNEO))
    for pi, pil_i in enumerate(PILOTOS_TORNEO):
        row_i = sorted_h[sorted_h["Piloto"]==pil_i]
        pts_i = int(row_i["Total"].iloc[0]) if not row_i.empty else 0
        txt_i = _msg(pil_i, pts_i)
        url_i = "https://wa.me/?text=" + _up_w.quote(txt_i)
        clr_i = PILOTO_COLORS.get(pil_i,"#a855f7")
        with icols[pi]:
            st.markdown(
                f'<a href="{url_i}" target="_blank" style="display:block;text-align:center;'
                f'background:{clr_i}22;border:1px solid {clr_i}66;color:{clr_i};'
                f'font-weight:800;font-size:11px;padding:8px 4px;border-radius:10px;'
                f'text-decoration:none;">{pil_i.split()[0]}</a>', unsafe_allow_html=True)
    st.markdown("---")


def pantalla_formuleros():
    """Sección de comunidad: Pilotos en parrilla, DMs, salón de la fama."""
    import html as _hf, sqlite3 as _sqf, datetime as _dtf

    usuario = st.session_state.get("usuario","")
    _colors = PILOTO_COLORS
    _heads  = DRIVER_HEADSHOTS
    _photos = DRIVER_PHOTOS

    st.markdown("""
    <style>
    .form-card{background:linear-gradient(145deg,rgba(10,14,36,.97),rgba(7,9,22,.99));
      border:1px solid rgba(255,255,255,.08);border-radius:20px;padding:20px;margin-bottom:16px;}
    .form-dm-bubble{background:rgba(99,102,241,.12);border:1px solid rgba(99,102,241,.25);
      border-radius:14px;padding:10px 14px;margin-bottom:8px;}
    </style>""", unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────
    st.markdown('<div class="section-title">👥 FORMULEROS</div>', unsafe_allow_html=True)

    # Auto-seleccionar pestaña según de dónde venimos
    _tab_target = None
    if st.session_state.get("formuleros_perfil_target"):
        _tab_target = "Parrilla"
    elif st.session_state.get("formuleros_tab_target"):
        _tab_target = st.session_state.pop("formuleros_tab_target")
    if _tab_target:
        import json as _json_tt
        _tt_js = _json_tt.dumps(_tab_target)
        components.html(f"""
        <script>
        (function(){{
            var target = {_tt_js};
            var tries = 0;
            function clickTab(){{
                tries++;
                var doc = window.parent.document;
                var tabs = doc.querySelectorAll('button[data-baseweb="tab"]');
                for (var i=0;i<tabs.length;i++){{
                    if (tabs[i].innerText && tabs[i].innerText.indexOf(target)>=0){{
                        tabs[i].click(); return;
                    }}
                }}
                if (tries < 20) setTimeout(clickTab, 150);
            }}
            setTimeout(clickTab, 200);
        }})();
        </script>""", height=0)

    # ═══ TAB STRUCTURE ══════════════════════════════════════
    _ft2, _ft1, _ft4, _ft3, _ft5 = st.tabs(["💬 Mesa de Formuleros", "🏎️ Parrilla", "🎯 Desafíos", "⚔️ Head to Head", "🏆 Muro de Campeones"])

    # ════ TAB 1: PARRILLA ════════════════════════════════════
    with _ft1:
        st.markdown('<div style="font-size:11px;font-weight:700;letter-spacing:.14em;'
                    'color:rgba(246,195,73,.6);text-transform:uppercase;margin-bottom:12px;">'
                    '🏆 CLASIFICACIÓN DEL TORNEO 2026</div>', unsafe_allow_html=True)

        # Read standings
        _mdb_f = _mod_db()
        _df_pos = None
        if "_error" not in _mdb_f:
            _df_pos = _safe_call(_mdb_f["leer_tabla_posiciones"], PILOTOS_TORNEO,
                                 timeout_sec=15, default=None)

        if _df_pos is not None and not (hasattr(_df_pos,"empty") and _df_pos.empty):
            try:
                _df_pos = _df_pos.copy()
                _df_pos["Puntos"] = pd.to_numeric(_df_pos.get("Puntos",0), errors="coerce").fillna(0)
                _df_pos = _df_pos.sort_values("Puntos", ascending=False).reset_index(drop=True)
            except Exception: pass

        _ROLE_F = {"Checo Perez":"Comisario","Lando Norris":"Sub Comisario",
                   "Fernando Alonso":"FIPF","Valteri Bottas":"FIPF","Nicki Lauda":"Formulero"}
        _MED_F  = {0:"🥇",1:"🥈",2:"🥉"}

        for _ri, pil in enumerate(PILOTOS_TORNEO if _df_pos is None else _df_pos["Piloto"].tolist()):
            _clr = _colors.get(pil,"#a855f7")
            _ph  = _heads.get(pil, _photos.get(pil,""))
            _pts = 0
            if _df_pos is not None:
                _row = _df_pos[_df_pos["Piloto"]==pil]
                if not _row.empty: _pts = int(_row.iloc[0].get("Puntos",0))
            _med = _MED_F.get(_ri, f"{_ri+1}°")
            _role = _ROLE_F.get(pil,"Formulero")
            _campeon_tag = (' <span style="background:linear-gradient(90deg,#9a7a10,#d4af37);'
                           'color:#1a1000;border-radius:10px;padding:1px 7px;font-size:9px;'
                           'font-weight:900;">👑 CAMPEÓN</span>' if pil=="Checo Perez" else "")
            _av = (f'<img src="{_ph}" style="width:48px;height:48px;border-radius:50%;'
                   f'object-fit:cover;object-position:top center;border:2px solid {_clr};">'
                   if _ph else
                   f'<div style="width:48px;height:48px;border-radius:50%;background:{_clr}22;'
                   f'border:2px solid {_clr};display:flex;align-items:center;justify-content:center;'
                   f'font-weight:900;font-size:16px;color:{_clr};">{"".join(w[0] for w in pil.split()[:2]).upper()}</div>')
            _is_me = (pil == usuario)
            _border = f"2px solid {_clr}" if _is_me else f"1px solid {_clr}22"
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:12px;'
                f'background:{"rgba(255,255,255,.04)" if _is_me else "rgba(255,255,255,.02)"};'
                f'border:{_border};border-radius:14px;padding:12px 16px;margin-bottom:6px;">'
                f'<div style="font-size:20px;width:28px;text-align:center;">{_med}</div>'
                f'{_av}'
                f'<div style="flex:1;">'
                f'<div style="font-size:14px;font-weight:900;color:{_clr};">{pil}{_campeon_tag}</div>'
                f'<div style="font-size:11px;color:rgba(169,178,214,.55);">{_role}</div>'
                f'</div>'
                f'<div style="text-align:right;">'
                f'<div style="font-size:20px;font-weight:900;color:#ffdd7a;">{_pts}</div>'
                f'<div style="font-size:9px;color:rgba(169,178,214,.4);">PUNTOS</div>'
                f'</div></div>', unsafe_allow_html=True)
            # Full profile expander — auto-expands if navigated from inicio
            _target_pil = st.session_state.get("formuleros_perfil_target", None)
            _should_expand = (_target_pil == pil)
            if _should_expand:
                st.session_state.pop("formuleros_perfil_target", None)
            with st.expander(f"👤 Ver perfil completo de {pil.split()[0]}", expanded=_should_expand):
                _mdb_fp2 = _mod_db()
                if "_error" in _mdb_fp2:
                    st.error("Error cargando datos.")
                else:
                    # Load full historial (all pilots — needed for logros comparison)
                    _h_fp2 = _safe_call(_mdb_fp2["leer_historial_df"], timeout_sec=12, default=pd.DataFrame())
                    # Load detalle for deeper logros
                    _det_fp2 = _safe_call(_mdb_fp2.get("leer_historial_detalle_df", lambda: pd.DataFrame()), timeout_sec=10, default=pd.DataFrame())
                    if _h_fp2 is not None and not (hasattr(_h_fp2,"empty") and _h_fp2.empty):
                        _hp2_all = _h_fp2.copy()
                        _hp2_all.columns = [c.lower().strip() for c in _hp2_all.columns]
                        _hp2_all["puntos"] = pd.to_numeric(_hp2_all["puntos"],errors="coerce").fillna(0).astype(int)
                        _hp2_pil = _hp2_all[_hp2_all.get("piloto",pd.Series(dtype=str)).astype(str)==pil]
                        if not _hp2_pil.empty:
                            _clr_fp = PILOTO_COLORS.get(pil,"#a855f7")
                            _n_gps  = len(_hp2_pil)
                            _total  = int(_hp2_pil["puntos"].sum())
                            _mejor  = int(_hp2_pil["puntos"].max())
                            _peor   = int(_hp2_pil["puntos"].min())
                            _avg    = _hp2_pil["puntos"].mean()
                            _best_gp_row = _hp2_pil.loc[_hp2_pil["puntos"].idxmax()]
                            _best_gp_lbl = str(_best_gp_row.get("gp","")).split(". ",1)[-1] if ". " in str(_best_gp_row.get("gp","")) else str(_best_gp_row.get("gp",""))
                            # GPs ganados
                            _gps_won = 0
                            try:
                                _agg_fp = _hp2_all.groupby(["gp","piloto"],as_index=False)["puntos"].sum()
                                for _gpf, _grpf in _agg_fp.groupby("gp"):
                                    if _grpf.sort_values("puntos",ascending=False).iloc[0]["piloto"]==pil: _gps_won+=1
                            except Exception: pass

                            # ── Stats cards ─────────────────────────────────────────
                            _sc1,_sc2,_sc3,_sc4 = st.columns(4)
                            with _sc1:
                                st.markdown(f'<div style="text-align:center;background:{_clr_fp}18;border:1px solid {_clr_fp}44;border-radius:10px;padding:8px 4px;">'
                                            f'<div style="font-size:22px;font-weight:900;color:{_clr_fp};">{_total}</div>'
                                            f'<div style="font-size:9px;color:rgba(169,178,214,.55);text-transform:uppercase;letter-spacing:.08em;">Total pts</div></div>', unsafe_allow_html=True)
                            with _sc2:
                                st.markdown(f'<div style="text-align:center;background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.25);border-radius:10px;padding:8px 4px;">'
                                            f'<div style="font-size:22px;font-weight:900;color:#4ade80;">{_n_gps}</div>'
                                            f'<div style="font-size:9px;color:rgba(169,178,214,.55);text-transform:uppercase;letter-spacing:.08em;">GPs jugados</div></div>', unsafe_allow_html=True)
                            with _sc3:
                                st.markdown(f'<div style="text-align:center;background:rgba(255,221,122,.08);border:1px solid rgba(255,221,122,.25);border-radius:10px;padding:8px 4px;">'
                                            f'<div style="font-size:22px;font-weight:900;color:#ffdd7a;">{_mejor} pts</div>'
                                            f'<div style="font-size:9px;color:rgba(169,178,214,.55);text-transform:uppercase;letter-spacing:.08em;">Mejor GP</div>'
                                            f'<div style="font-size:8px;color:rgba(246,195,73,.5);">{_best_gp_lbl}</div></div>', unsafe_allow_html=True)
                            with _sc4:
                                st.markdown(f'<div style="text-align:center;background:rgba(168,85,247,.08);border:1px solid rgba(168,85,247,.25);border-radius:10px;padding:8px 4px;">'
                                            f'<div style="font-size:22px;font-weight:900;color:#a855f7;">{_avg:.1f}</div>'
                                            f'<div style="font-size:9px;color:rgba(169,178,214,.55);text-transform:uppercase;letter-spacing:.08em;">Promedio</div></div>', unsafe_allow_html=True)
                            if _gps_won > 0 or True:
                                _sc5,_sc6 = st.columns(2)
                                with _sc5:
                                    st.markdown(f'<div style="text-align:center;background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.25);border-radius:10px;padding:8px 4px;margin-top:6px;">'
                                                f'<div style="font-size:20px;font-weight:900;color:#D4AF37;">🏆 {_gps_won}</div>'
                                                f'<div style="font-size:9px;color:rgba(169,178,214,.55);text-transform:uppercase;letter-spacing:.08em;">GPs ganados</div></div>', unsafe_allow_html=True)
                                with _sc6:
                                    st.markdown(f'<div style="text-align:center;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.2);border-radius:10px;padding:8px 4px;margin-top:6px;">'
                                                f'<div style="font-size:20px;font-weight:900;color:#ef4444;">{_peor} pts</div>'
                                                f'<div style="font-size:9px;color:rgba(169,178,214,.55);text-transform:uppercase;letter-spacing:.08em;">Menor GP</div></div>', unsafe_allow_html=True)

                            # ── Best GP highlight ────────────────────────────────────
                            st.markdown(
                                f'<div style="background:{_clr_fp}12;border:1px solid {_clr_fp}33;' +
                                f'border-radius:12px;padding:8px 12px;margin:8px 0;display:flex;align-items:center;gap:10px;">' +
                                f'<span style="font-size:20px;">⭐</span>' +
                                f'<div><div style="font-size:10px;color:rgba(169,178,214,.5);">Mejor resultado</div>' +
                                f'<div style="font-size:13px;font-weight:900;color:{_clr_fp};">{_best_gp_lbl} — {_mejor} pts</div></div></div>',
                                unsafe_allow_html=True)

                            # ── History mini-bars ────────────────────────────────────
                            _hist_data = []
                            for _, r in _hp2_pil.sort_values("gp").iterrows():
                                _gn_raw = str(r.get("gp",""))
                                # Remove number prefix and "Gran Premio de/del"
                                _gn_clean = _gn_raw.split(". ",1)[-1] if ". " in _gn_raw else _gn_raw
                                _gn_clean = (_gn_clean.replace("Gran Premio de ","").replace("Gran Premio del ","")
                                             .replace("Gran Premio ","").replace("GP ",""))
                                _hist_data.append((_gn_clean[:14], int(r.get("puntos",0))))
                            if _hist_data:
                                _max_h = max(p for _,p in _hist_data) or 1
                                _bars = ""
                                for _gn, _pts_h in _hist_data:
                                    _pct = int(_pts_h/_max_h*100)
                                    _bc = "#4ade80" if _pts_h == _mejor else _clr_fp
                                    _bars += (f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">'
                                              f'<span style="font-size:9px;color:rgba(212,175,55,.7);min-width:72px;text-align:right;font-weight:600;">{_gn}</span>'
                                              f'<div style="height:16px;width:{max(_pct,4)}%;background:linear-gradient(90deg,{_bc}99,{_bc}dd);border-radius:6px;"></div>'
                                              f'<span style="font-size:10px;color:#ffdd7a;font-weight:900;min-width:28px;">{_pts_h}</span>'
                                              '</div>')
                                st.markdown(f'<div style="margin:8px 0;padding:6px 8px;background:rgba(255,255,255,.02);border-radius:10px;">{_bars}</div>', unsafe_allow_html=True)

                            # ── Logros — load detalle for accurate calculation ────────
                            try:
                                _det_for_logros = None
                                if _det_fp2 is not None and not (hasattr(_det_fp2,"empty") and _det_fp2.empty):
                                    _det_c = _det_fp2.copy()
                                    _det_c.columns = [c.lower().strip() for c in _det_c.columns]
                                    _det_c["puntos"] = pd.to_numeric(_det_c["puntos"],errors="coerce").fillna(0).astype(int)
                                    _det_for_logros = _det_c
                                _lgr2 = _calc_logros(pil, _hp2_all, _det_for_logros, _n_gps)
                                _ulg2 = [(ld,u2,gp2) for ld,u2,gp2 in _lgr2 if u2]
                                st.markdown('<div style="font-size:9px;font-weight:700;color:rgba(246,195,73,.6);text-transform:uppercase;letter-spacing:.1em;margin:10px 0 5px;">🏅 Logros & Medallas</div>', unsafe_allow_html=True)
                                if _ulg2:
                                    _bl2 = "".join(
                                        f'<div title="{ld[3]}" style="display:inline-flex;align-items:center;gap:5px;' +
                                        f'background:rgba(212,175,55,.12);border:1px solid rgba(212,175,55,.3);' +
                                        f'border-radius:20px;padding:4px 10px;margin:2px 3px 2px 0;cursor:help;">' +
                                        f'<span style="font-size:16px;">{ld[1]}</span>' +
                                        f'<div><div style="color:#ffdd7a;font-weight:800;font-size:10px;">{ld[2]}</div>' +
                                        (f'<div style="font-size:8px;color:rgba(74,222,128,.6);">Ganado en: {gp2}</div>' if gp2 else '') +
                                        '</div></div>'
                                        for ld,_,gp2 in _ulg2
                                    )
                                    st.markdown(f'<div style="display:flex;flex-wrap:wrap;">{_bl2}</div>', unsafe_allow_html=True)
                                    st.caption(f"{len(_ulg2)}/{len(_lgr2)} logros desbloqueados")
                                else:
                                    st.caption("Sin logros todavía.")
                                if pil == "Checo Perez":
                                    st.markdown('<div style="background:linear-gradient(90deg,#9a7a10,#d4af37);color:#1a1000;border-radius:12px;padding:6px 14px;text-align:center;font-weight:900;font-size:11px;margin-top:6px;">👑 CAMPEÓN VIGENTE — TORNEO FEFE WOLF</div>', unsafe_allow_html=True)
                            except Exception as _le: st.caption(f"Error logros: {_le}")
                        else:
                            st.info(f"{pil.split()[0]} aún no tiene historial registrado.")
                    else:
                        st.info("Sin datos de historial.")




    # ════ TAB 2: MESA DE FORMULEROS (chat) ══════════════════════════
    with _ft2:
        st.markdown('<div style="font-size:11px;color:rgba(169,178,214,.45);margin-bottom:8px;">'
                    '💬 Mesa exclusiva para debatir F1 entre formuleros. Los mensajes persisten.</div>',
                    unsafe_allow_html=True)
        m_chat = _mod_mesa()
        if "_error" in m_chat:
            st.error(f"Chat no disponible: {m_chat['_error']}")
        else:
            # ── Load messages ─────────────────────────────────────────────
            _mc_limit_f = st.session_state.get("mc_show_limit_f", 40)
            _all_rows_f = m_chat["mc_list_messages"](limit=999) or []
            # ── Si SQLite está vacío, cargar desde GSheets (sobrevive reinicios) ──
            if not _all_rows_f:
                try:
                    from core.database import conectar_google_sheets as _cgs_mc2
                    _ws_mc2 = _cgs_mc2("MesaChica")
                    if _ws_mc2:
                        _vals_mc2 = _ws_mc2.get_all_values()
                        if _vals_mc2 and len(_vals_mc2) > 1:
                            _hdr_mc2 = [h.lower().strip() for h in _vals_mc2[0]]
                            def _col_idx(name, default=None):
                                return _hdr_mc2.index(name) if name in _hdr_mc2 else default
                            _i_id  = _col_idx("id", 0)
                            _i_usr = _col_idx("usuario", 1)
                            _i_txt = _col_idx("texto", 2)
                            _i_ts  = _col_idx("ts", 3)
                            _i_del = _col_idx("deleted", 4)
                            _tmp_rows = []
                            for _r in _vals_mc2[1:]:
                                try:
                                    _del_v = str(_r[_i_del]) if (_i_del is not None and _i_del < len(_r)) else "0"
                                    if _del_v in ("1","True","true"): continue
                                    _txt_v = str(_r[_i_txt]) if _i_txt < len(_r) else ""
                                    if not _txt_v.strip(): continue
                                    _id_v = 0
                                    try: _id_v = int(_r[_i_id]) if _i_id < len(_r) else 0
                                    except Exception: _id_v = 0
                                    _tmp_rows.append((
                                        _id_v,
                                        str(_r[_i_usr]) if _i_usr < len(_r) else "",
                                        _txt_v,
                                        str(_r[_i_ts]) if _i_ts < len(_r) else ""))
                                except Exception: continue
                            _all_rows_f = list(reversed(_tmp_rows))
                except Exception: pass
            rows_f = _all_rows_f[:_mc_limit_f]

            # Input
            _in_col1, _in_col2 = st.columns([9,1])
            with _in_col1:
                _mc_txt_f = st.text_input("", key="mc_input_formuleros",
                                          placeholder="Escribí en la Mesa de Formuleros…",
                                          label_visibility="collapsed", max_chars=400)
            with _in_col2:
                if st.button("📤", key="mc_send_formuleros", use_container_width=True):
                    if _mc_txt_f.strip() and m_chat.get("mc_add_message"):
                        m_chat["mc_add_message"](usuario, _mc_txt_f.strip())
                        # ── Also persist to Google Sheets for Cloud survival ──
                        try:
                            from core.database import conectar_google_sheets as _cgs_mc
                            _ws_mc = _cgs_mc("MesaChica")
                            if _ws_mc:
                                import datetime as _dt_mc, pytz as _ptz_mc
                                _ts_mc = _dt_mc.datetime.now(_ptz_mc.timezone("America/Argentina/Buenos_Aires")).strftime("%Y-%m-%d %H:%M:%S")
                                _mc_recs = _ws_mc.get_all_values()
                                # Asegurar fila de encabezados
                                if not _mc_recs:
                                    _ws_mc.append_row(["id","usuario","texto","ts","deleted","extra"])
                                    _mc_recs = [["id","usuario","texto","ts","deleted","extra"]]
                                _mc_nid = len(_mc_recs)  # header + rows = siguiente id
                                _ws_mc.append_row([_mc_nid, usuario, _mc_txt_f.strip(), _ts_mc, 0, ""])
                        except Exception: pass
                        st.rerun()

            _ref_c1, _ref_c2 = st.columns([1, 4])
            with _ref_c1:
                if st.button("🔄 Actualizar", key="mc_ref_f", use_container_width=True):
                    st.rerun()

            st.markdown('<div style="height:6px"></div>', unsafe_allow_html=True)

            # Messages
            for _row_f in rows_f:
                _mid_f, _u_f, _txt_f, _ts_f = _row_f[:4]
                _clr_f = PILOTO_COLORS.get(_u_f,"#a855f7")
                _ph_f  = DRIVER_HEADSHOTS.get(_u_f, DRIVER_PHOTOS.get(_u_f,""))
                _is_own_f = (_u_f == usuario)
                _is_fipf_f = usuario in {"Checo Perez","Lando Norris","Fernando Alonso","Valteri Bottas"}
                _av_f = (f'<img src="{_ph_f}" style="width:30px;height:30px;border-radius:50%;'
                         f'object-fit:cover;object-position:top;border:2px solid {_clr_f};flex-shrink:0;">'
                         if _ph_f else
                         f'<div style="width:30px;height:30px;border-radius:50%;background:{_clr_f}22;'
                         f'border:1.5px solid {_clr_f};display:flex;align-items:center;justify-content:center;'
                         f'font-weight:900;font-size:9px;color:{_clr_f};flex-shrink:0;">'
                         f'{"".join(w[0] for w in _u_f.split()[:2]).upper()}</div>')
                try: _ts_f2 = __import__("datetime").datetime.fromisoformat(_ts_f.replace("T"," ").split(".")[0]).strftime("%d/%m %H:%M")
                except Exception: _ts_f2 = str(_ts_f)[:16]
                _bg_f = (f"linear-gradient(135deg,{_clr_f}1a,rgba(8,12,30,.97))"
                         if _is_own_f else "rgba(255,255,255,.03)")
                _br_f = "14px 14px 3px 14px" if _is_own_f else "14px 14px 14px 3px"
                _bub_f = (
                    f'<div style="background:{_bg_f};border:1px solid {_clr_f}33;'
                    f'border-radius:{_br_f};padding:8px 12px 5px;max-width:100%;word-break:break-word;">'
                    f'<div style="display:flex;align-items:center;gap:5px;margin-bottom:2px;">'
                    f'<span style="font-size:10px;font-weight:900;color:{_clr_f};">{_u_f.split()[0]}</span>'
                    f'<span style="background:{_clr_f}22;color:{_clr_f};border-radius:20px;padding:1px 6px;'
                    f'font-size:8px;font-weight:800;">{_mc_badge(_u_f)[1]}</span>'
                    f'<span style="font-size:8px;color:rgba(169,178,214,.3);margin-left:auto;">{_ts_f2}</span>'
                    f'</div>'
                    f'<div style="font-size:13px;color:rgba(232,236,255,.9);">{_mc_safe(_txt_f)}</div>'
                    f'</div>'
                )
                if _is_own_f:
                    st.markdown(f'<div style="display:flex;align-items:flex-end;justify-content:flex-end;gap:6px;margin-bottom:2px;">'
                                f'<div style="max-width:70%;">{_bub_f}</div>{_av_f}</div>', unsafe_allow_html=True)
                    if (_is_own_f or _is_fipf_f):
                        _dc1, _dc2, _del_col = st.columns([6,3,1])
                        with _del_col:
                            if st.button("✕", key=f"mcdel_f_{_mid_f}",
                                         help="Borrar"):
                                m_chat["mc_soft_delete_message"](_mid_f, deleted_by=usuario); st.rerun()
                else:
                    st.markdown(f'<div style="display:flex;align-items:flex-end;gap:6px;margin-bottom:2px;">'
                                f'{_av_f}<div style="max-width:70%;">{_bub_f}</div></div>', unsafe_allow_html=True)
                    if _is_fipf_f:
                        _del_col2, _dc3, _dc4 = st.columns([1,3,6])
                        with _del_col2:
                            if st.button("✕", key=f"mcdel_fa_{_mid_f}",
                                         help="Borrar (admin)"):
                                m_chat["mc_soft_delete_message"](_mid_f, deleted_by=usuario); st.rerun()

            if len(_all_rows_f) > _mc_limit_f:
                if st.button(f"📜 Ver más mensajes", key="mc_more_f", use_container_width=True):
                    st.session_state["mc_show_limit_f"] = _mc_limit_f + 30; st.rerun()

    # ════ TAB 3: HEAD TO HEAD ════════════════════════════════
    with _ft3:
        st.markdown('<div style="font-size:12px;color:rgba(169,178,214,.5);margin-bottom:8px;">'
                    '⚔️ Comparación directa entre 2 formuleros del torneo</div>', unsafe_allow_html=True)
        pantalla_head_to_head()

    # ════ TAB 4: DESAFÍOS ═════════════════════════════════════
    with _ft4:
        pantalla_desafios()

    # ════ TAB 5: MURO DE CAMPEONES ════════════════════════════
    with _ft5:
        st.markdown(
            '<div style="background:linear-gradient(145deg,rgba(212,175,55,.08),rgba(7,9,22,.97));' +
            'border:1.5px solid rgba(212,175,55,.35);border-radius:20px;padding:20px;text-align:center;">' +
            '<div style="font-size:32px;margin-bottom:6px;">🏆</div>' +
            '<div style="font-size:20px;font-weight:900;background:linear-gradient(90deg,#9a7a10,#d4af37,#ffe896,#d4af37,#9a7a10);' +
            'background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;' +
            'background-clip:text;letter-spacing:.1em;">MURO DE CAMPEONES</div>' +
            '<div style="font-size:10px;color:rgba(246,195,73,.5);letter-spacing:.2em;text-transform:uppercase;margin-top:3px;">' +
            'Torneo Fefe Wolf · Solo los campeones son inmortalizados aquí</div>' +
            '</div>', unsafe_allow_html=True)
        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        pantalla_muro()



def pantalla_desafios():
    """Sistema de desafíos entre formuleros — EN REDISEÑO, vuelve después de Bélgica."""
    usuario = (st.session_state.get("perfil") or {}).get("usuario","")
    st.markdown(
        '<div style="background:linear-gradient(145deg,rgba(6,15,40,.97),rgba(10,20,55,.98));'
        'border:1.5px solid rgba(59,130,246,.35);border-radius:20px;'
        'padding:36px 26px;text-align:center;">'
        '<div style="font-size:42px;margin-bottom:10px;">🚧</div>'
        '<div style="font-size:20px;font-weight:900;color:#D4AF37;letter-spacing:.06em;">'
        'DESAFÍOS EN RECONSTRUCCIÓN</div>'
        '<div style="font-size:13px;color:rgba(232,236,255,.7);margin-top:10px;line-height:1.7;">'
        'Estamos rediseñando por completo el sistema de Desafíos.<br>'
        'Vuelve a estar disponible <b style="color:#ffdd7a;">a partir del GP de Bélgica</b>.'
        '</div>'
        '<div style="margin-top:16px;font-size:11px;color:rgba(169,178,214,.45);">'
        '⚔️ Gracias por la paciencia, Formulero.</div>'
        '</div>', unsafe_allow_html=True)



def pantalla_admin():
    """Panel centralizado de administración — solo Checo Perez."""
    usuario = (st.session_state.get("perfil") or {}).get("usuario","")
    if usuario != "Checo Perez":
        st.error("🔒 Acceso restringido al Comisario.")
        return

    # Password protection
    if not st.session_state.get("admin_auth", False):
        st.markdown(
            '<div style="text-align:center;padding:30px 0 20px;">'
            '<div style="font-size:36px;margin-bottom:8px;">⚡</div>'
            '<div style="font-size:20px;font-weight:900;color:#D4AF37;">PANEL ADMIN</div>'
            '<div style="font-size:11px;color:rgba(169,178,214,.5);margin-top:4px;">'
            'Protegido por los dioses del torneo</div>'
            '</div>', unsafe_allow_html=True)
        _adm_pwd = st.text_input("🔑 Clave de acceso:", type="password", key="adm_pwd_input")
        if st.button("⚡ Acceder", key="adm_auth_btn", use_container_width=True):
            if _adm_pwd == "2022":
                st.session_state["admin_auth"] = True
                st.rerun()
            else:
                st.error("⛔ Clave incorrecta. Los dioses del torneo te rechazan.")
        return

    st.markdown("""
    <style>
    .admin-card{background:rgba(10,14,36,.97);border:1px solid rgba(212,175,55,.2);
      border-radius:16px;padding:18px 20px;margin-bottom:14px;}
    .admin-title{font-size:10px;font-weight:800;letter-spacing:.18em;
      color:rgba(212,175,55,.6);text-transform:uppercase;margin-bottom:10px;}
    </style>""", unsafe_allow_html=True)

    st.markdown(
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;">'
        '<span style="font-size:28px;">🔐</span>'
        '<div><div style="font-size:22px;font-weight:900;color:#D4AF37;">PANEL ADMIN</div>'
        '<div style="font-size:11px;color:rgba(169,178,214,.5);">Torneo Fefe Wolf 2026 · Solo el Comisario</div>'
        '</div></div>', unsafe_allow_html=True)

    mdb = _mod_db(); madm = _mod_admin(); mcore = _mod_core()
    if "_error" in mdb or "_error" in madm:
        st.error(f"⚠️ Error cargando módulos: {mdb.get('_error','')} {madm.get('_error','')}"); return

    # ── Tabs del panel ─────────────────────────────────────────────────
    _at1,_at2,_at3,_at4,_at5,_at6 = st.tabs([
        "⚡ Resultados & Historial",
        "⛔ Sanciones DNS",
        "👥 Usuarios",
        "🎟️ Invitaciones",
        "📧 Comunicados",
        "📋 Log"
    ])

    # ════ TAB 1: RESULTADOS & HISTORIAL ════════════════════════════════
    with _at1:
        st.markdown('<div class="admin-title">📌 GP a calcular</div>', unsafe_allow_html=True)
        gp_adm = st.selectbox("Gran Premio:", GPS_ACTIVOS, key="adm_gp",
                              format_func=lambda x: x.split(". ",1)[-1] if ". " in x else x)
        es_sprint_adm = gp_adm in GPS_SPRINT

        # Estado del GP
        estado_adm = _safe_call(mcore["obtener_estado_gp"], gp_adm, HORARIOS_CARRERA, TZ,
                                timeout_sec=4, default={"habilitado":True,"mensaje":""})
        _gp_abierto_adm = (estado_adm or {}).get("habilitado", True)
        if _gp_abierto_adm:
            st.warning("⚠️ Las predicciones están ABIERTAS. El historial se calcula después del cierre.")
        else:
            st.success(f"✅ GP cerrado — listo para calcular")

        # Resultados oficiales
        st.markdown('<div class="admin-title" style="margin-top:12px;">📋 Resultados oficiales</div>',
                    unsafe_allow_html=True)
        _oa1,_oa2,_oa3 = st.columns(3)
        oficial_adm = {}
        with _oa1:
            st.markdown("**🏁 Carrera**")
            for i in range(1,11): oficial_adm[f"r{i}"] = st.text_input(f"P{i}", key=f"adm_r{i}_{gp_adm}")
            oficial_adm["col_r"] = st.number_input("Colapinto posición", 1,22,10, key=f"adm_colr_{gp_adm}")
        with _oa2:
            st.markdown("**⏱️ Clasificación**")
            for i in range(1,6): oficial_adm[f"q{i}"] = st.text_input(f"P{i}", key=f"adm_q{i}_{gp_adm}")
            oficial_adm["col_q"] = st.number_input("Colapinto qualy", 1,22,10, key=f"adm_colq_{gp_adm}")
        with _oa3:
            st.markdown("**🛠️ Constructores** (auto)")
            _of_r_adm = {i:oficial_adm.get(f"r{i}","") for i in range(1,11)}
            try:
                top3_adm,_ = calcular_constructores_auto(_of_r_adm, GRILLA_2026, ESCALA_CARRERA_JUEGO)
                if len(top3_adm) >= 3:
                    oficial_adm["c1"],oficial_adm["c2"],oficial_adm["c3"] = top3_adm[0],top3_adm[1],top3_adm[2]
                    st.success(f"1° {top3_adm[0]}\n2° {top3_adm[1]}\n3° {top3_adm[2]}")
            except Exception:
                for i in range(1,4): oficial_adm[f"c{i}"] = st.text_input(f"Constructor {i}°", key=f"adm_c{i}_{gp_adm}")
            if es_sprint_adm:
                st.markdown("**⚡ Sprint**")
                for i in range(1,9): oficial_adm[f"s{i}"] = st.text_input(f"Sprint P{i}", key=f"adm_s{i}_{gp_adm}")

        # Calcular
        # ── Preview de predicciones vs oficial ───────────────────────────
        if st.button("👁️ VER PREVIEW ACIERTOS", key="adm_preview_btn", use_container_width=True):
            st.session_state["_adm_show_preview"] = True

        if st.session_state.get("_adm_show_preview"):
            with st.spinner("Cargando preview de aciertos…"):
                try:
                    import re as _re_prev
                    _nn_prev = lambda x: str(x or "").strip().lower()
                    _ESCALA_PR = {"QUALY":{1:15,2:10,3:7,4:5,5:3},
                                  "SPRINT":{1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1},
                                  "CARRERA":{1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1},
                                  "CONSTRUCTORES":{1:10,2:5,3:2}}

                    # Totales por formulero para vista rápida
                    _totales_prev = {}

                    for _pp in PILOTOS_TORNEO:
                        _r_prev = _safe_call(mdb["recuperar_predicciones_piloto"], _pp, gp_adm,
                                             timeout_sec=10, default=(None,None,(None,None)))
                        _dq_pr, _ds_pr, (_dr_pr, _dc_pr) = _r_prev
                        # dq=Qualy, ds=Sprint, dr=Carrera (con colapinto_r,c1,c2,c3), dc también constructores
                        _pts_total_pr = 0
                        _secciones = []

                        def _check_sec(pred_d, etapa, pfx, n_pos):
                            if not isinstance(pred_d, dict): return [], 0
                            rows_s = []; pts_s = 0; aciertos_s = 0
                            for _pos in range(1, n_pos+1):
                                _pv = str(pred_d.get(_pos, pred_d.get(str(_pos), ""))).strip()
                                if not _pv: continue
                                _rv = str(oficial_adm.get(f"{pfx}{_pos}","")).strip()
                                _ok = bool(_rv and _nn_prev(_pv) == _nn_prev(_rv))
                                _esc = _ESCALA_PR.get(etapa,{}).get(_pos,0)
                                _pts_k = _esc if _ok else 0; pts_s += _pts_k
                                if _ok: aciertos_s += 1
                                rows_s.append({"Piloto":_pp,"Etapa":etapa,"Pos":f"P{_pos}",
                                               "Predicción":_pv,"Real":_rv if _rv else "—",
                                               "Acierto":"✅" if _ok else "❌","Pts":_pts_k})
                            # Pleno bonus
                            _pleno_pts = {5:"QUALY",3:"SPRINT",5:"CARRERA",3:"CONSTRUCTORES"}.get(n_pos,0)
                            if aciertos_s == n_pos and aciertos_s > 0:
                                _pb = {"QUALY":5,"SPRINT":3,"CARRERA":5,"CONSTRUCTORES":3}.get(etapa,0)
                                pts_s += _pb
                                if _pb: rows_s.append({"Piloto":_pp,"Etapa":f"🎯 PLENO {etapa}","Pos":"—",
                                                        "Predicción":"","Real":"","Acierto":"🎯",
                                                        "Pts":_pb})
                            return rows_s, pts_s

                        all_rows_pr = []
                        _rq, _pq = _check_sec(_dq_pr, "QUALY", "q", 5)
                        all_rows_pr += _rq; _pts_total_pr += _pq
                        if gp_adm in GPS_SPRINT:
                            _rs, _ps = _check_sec(_ds_pr, "SPRINT", "s", 8)
                            all_rows_pr += _rs; _pts_total_pr += _ps
                        _rr, _pr = _check_sec(_dr_pr, "CARRERA", "r", 10)
                        all_rows_pr += _rr; _pts_total_pr += _pr
                        # Constructores — puede estar en dr o dc
                        _cons_src = _dc_pr if isinstance(_dc_pr, dict) and _dc_pr else (
                                    {1: _dr_pr.get("c1"), 2: _dr_pr.get("c2"), 3: _dr_pr.get("c3")}
                                    if isinstance(_dr_pr, dict) else {})
                        _rc, _pc = _check_sec(_cons_src, "CONSTRUCTORES", "c", 3)
                        all_rows_pr += _rc; _pts_total_pr += _pc
                        # Colapinto
                        if isinstance(_dq_pr, dict):
                            _cq_pr = str(_dq_pr.get("colapinto_q","")).strip()
                            if _cq_pr:
                                _cq_real = str(oficial_adm.get("col_q","")).strip()
                                _cq_ok = bool(_cq_real and str(_cq_pr)==str(_cq_real))
                                _cq_pts = 10 if _cq_ok else 0; _pts_total_pr += _cq_pts
                                all_rows_pr.append({"Piloto":_pp,"Etapa":"COLAPINTO Q","Pos":"—",
                                                    "Predicción":f"P{_cq_pr}","Real":f"P{_cq_real}" if _cq_real else "—",
                                                    "Acierto":"✅(+10)" if _cq_ok else "❌","Pts":_cq_pts})
                        if isinstance(_dr_pr, dict):
                            _cr_pr = str(_dr_pr.get("colapinto_r","")).strip()
                            if _cr_pr:
                                _cr_real = str(oficial_adm.get("col_r","")).strip()
                                _cr_ok = bool(_cr_real and str(_cr_pr)==str(_cr_real))
                                _cr_pts = 20 if _cr_ok else 0; _pts_total_pr += _cr_pts
                                all_rows_pr.append({"Piloto":_pp,"Etapa":"COLAPINTO R","Pos":"—",
                                                    "Predicción":f"P{_cr_pr}","Real":f"P{_cr_real}" if _cr_real else "—",
                                                    "Acierto":"✅(+20)" if _cr_ok else "❌","Pts":_cr_pts})

                        _totales_prev[_pp] = (_pts_total_pr, all_rows_pr)

                    # ── Mostrar resumen de totales ────────────────────────
                    import pandas as _pd_prev
                    _resumen_prev = [{"Formulero":p,"Pts estimados":t,"¿Tiene preds?":"✅" if r else "🔴"}
                                     for p,(t,r) in sorted(_totales_prev.items(),key=lambda x:-x[1][0])]
                    st.markdown("**📊 Resumen de aciertos estimados:**")
                    st.dataframe(_pd_prev.DataFrame(_resumen_prev), use_container_width=True, height=220)

                    # ── Detalle expandible por formulero ─────────────────
                    for _pil_exp, (_pts_exp, _rows_exp) in sorted(_totales_prev.items(), key=lambda x:-x[1][0]):
                        _clr_exp = PILOTO_COLORS.get(_pil_exp,"#a855f7")
                        with st.expander(f"🔍 {_pil_exp} — {_pts_exp} pts estimados"):
                            if _rows_exp:
                                st.dataframe(_pd_prev.DataFrame(_rows_exp), use_container_width=True, height=300)
                            else:
                                st.warning(f"Sin predicciones cargadas para {_pil_exp}")

                    if st.button("🔄 Cerrar preview", key="adm_close_preview"):
                        st.session_state["_adm_show_preview"] = False; st.rerun()

                except Exception as _ep:
                    st.error(f"Error preview: {_ep}")
                    import traceback; st.code(traceback.format_exc())

        st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)
        if st.button("🧮 CALCULAR HISTORIAL + DNS", key="adm_calc_btn",
                     use_container_width=True, type="primary"):
            with st.spinner("Calculando…"):
                try:
                    df_h_adm = madm["historial"](
                        gp_calc=gp_adm, oficial=oficial_adm,
                        pilotos_torneo=PILOTOS_TORNEO, gps_sprint=GPS_SPRINT)
                    if df_h_adm is not None and not (hasattr(df_h_adm,"empty") and df_h_adm.empty):
                        st.success("✅ Historial generado correctamente")
                        # Save oficial results for exact aciertos in Mi Perfil
                        _saved = _safe_call(mdb.get("guardar_resultados_oficiales",lambda *a:False),
                                           gp_adm, oficial_adm, timeout_sec=15, default=False)
                        if _saved: st.success("📋 Resultados oficiales guardados para aciertos exactos")
                        st.dataframe(df_h_adm, use_container_width=True)
                        _do_wa_email(df_h_adm, oficial_adm, gp_adm, mdb)
                    else:
                        st.error("❌ Error al generar historial")
                except Exception as _e_adm: st.error(f"Error: {_e_adm}")

        # ── Enviar resultados por email ─────────────────────────────────
        st.markdown("---")
        st.markdown("**📧 Enviar resultados por email**")

        # Imagen opcional para el email (URL o subida)
        with st.expander("🖼️ Agregar imagen al email (opcional)", expanded=False):
            _adm_img_mode = st.radio("Origen de la imagen:", ["🔗 URL", "📁 Subir archivo"],
                                     horizontal=True, key="adm_email_img_mode", label_visibility="collapsed")
            _adm_email_img = ""
            if _adm_img_mode == "🔗 URL":
                _adm_email_img = st.text_input("URL de imagen (https://...)", key="adm_email_img_url",
                                               placeholder="https://i.ibb.co/XXXX/foto.jpg").strip()
            else:
                _adm_up_img = st.file_uploader("Subir imagen", type=["jpg","jpeg","png","webp"],
                                               key="adm_email_img_file")
                if _adm_up_img is not None:
                    import base64 as _b64_ae, io as _io_ae
                    _raw_ae = _adm_up_img.read()
                    try:
                        from PIL import Image as _PILae
                        _im_ae = _PILae.open(_io_ae.BytesIO(_raw_ae))
                        if _im_ae.mode in ("RGBA","P","LA"): _im_ae = _im_ae.convert("RGB")
                        _im_ae.thumbnail((900,900))
                        _buf_ae = _io_ae.BytesIO(); _q_ae = 80
                        _im_ae.save(_buf_ae, format="JPEG", quality=_q_ae, optimize=True)
                        while _buf_ae.tell() > 300_000 and _q_ae > 35:
                            _q_ae -= 10; _buf_ae = _io_ae.BytesIO()
                            _im_ae.save(_buf_ae, format="JPEG", quality=_q_ae, optimize=True)
                        _raw_ae = _buf_ae.getvalue()
                    except Exception: pass
                    _adm_email_img = f"data:image/jpeg;base64,{_b64_ae.b64encode(_raw_ae).decode()}"
                    st.image(_raw_ae, caption=f"Preview ({len(_raw_ae)//1024} KB)", width=200)
            st.session_state["_adm_email_img"] = _adm_email_img

        # Step 1: Preview email content
        if st.button("👁️ PREVISUALIZAR EMAIL ANTES DE ENVIAR", key="adm_email_preview_btn", use_container_width=True):
            st.session_state["_adm_show_email_preview"] = True

        if st.session_state.get("_adm_show_email_preview"):
            _gm_u_prev = st.secrets.get("GMAIL_USER","")
            _gm_p_prev = st.secrets.get("GMAIL_APP_PASSWORD","")
            _emails_prev = st.secrets.get("emails",{})
            if not _gm_u_prev or not _gm_p_prev:
                st.error("⚠️ Falta GMAIL_USER o GMAIL_APP_PASSWORD en secrets.toml")
                st.info("""**Para configurar Gmail:**
1. Andá a myaccount.google.com → Seguridad → Verificación en 2 pasos (activala si no la tenés)
2. Buscá "Contraseñas de aplicación" → generá una nueva para "Correo"
3. Copiá la contraseña de 16 caracteres
4. En secrets.toml agregá:
   ```
   GMAIL_USER = "tumail@gmail.com"
   GMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
   ```
5. En Streamlit Cloud: Settings → Secrets → mismo contenido""")
            else:
                st.markdown(f'<div style="background:rgba(74,222,128,.08);border:1px solid rgba(74,222,128,.3);border-radius:10px;padding:8px 14px;margin-bottom:8px;font-size:12px;">'
                            f'📧 <b>Se enviarán desde:</b> {_gm_u_prev} &nbsp;·&nbsp; <b>Destinatarios:</b> {", ".join(k for k,v in _emails_prev.items() if v)}</div>',
                            unsafe_allow_html=True)
            # Build and show preview for each pilot
            _nn_em = lambda x: str(x or "").strip().lower()
            _ESCALA_EM = {"q":{1:15,2:10,3:7,4:5,5:3},"s":{1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1},
                          "r":{1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1},"c":{1:10,2:5,3:2}}

            def _build_email_html_adm(usuario_em):
                _re_em = _safe_call(mdb["recuperar_predicciones_piloto"], usuario_em, gp_adm,
                                    timeout_sec=8, default=(None,None,(None,None)))
                _dq_em, _ds_em, (_dr_em, _dc_em) = _re_em
                _gp_short_em = gp_adm.split(". ",1)[-1] if ". " in gp_adm else gp_adm
                _img_email = st.session_state.get("_adm_email_img","")
                _img_html_email = (f"<img src='{_img_email}' style='width:100%;max-width:560px;"
                                   f"border-radius:10px;margin:10px 0;display:block;'>"
                                   if _img_email else "")
                _lines = [f"<div style='font-family:Arial;max-width:600px;background:#07091a;color:#e8ecff;padding:20px;border-radius:12px;'>",
                          f"<h2 style='color:#D4AF37;margin-bottom:4px;'>🏎️ TORNEO FEFE WOLF 2026</h2>",
                          f"<h3 style='color:#ffdd7a;'>🏁 {_gp_short_em.upper()}</h3>",
                          _img_html_email,
                          f"<p>Hola <b style='color:#D4AF37;'>{usuario_em.split()[0]}</b>, estos son tus aciertos:</p>"]
                _total_em = 0
                # DNS — check from HistorialDetalle
                _dns_pts_em = 0
                try:
                    _fn_det_em = mdb.get("leer_historial_detalle_df")
                    if callable(_fn_det_em):
                        _det_em = _safe_call(_fn_det_em, timeout_sec=8, default=None)
                        if _det_em is not None and not _det_em.empty:
                            _det_em.columns = [c.lower().strip() for c in _det_em.columns]
                            _dns_rows = _det_em[
                                (_det_em.get("piloto",pd.Series(dtype=str)).astype(str)==usuario_em) &
                                (_det_em.get("gp",pd.Series(dtype=str)).astype(str)==gp_adm) &
                                (_det_em.get("etapa",pd.Series(dtype=str)).str.upper()=="DNS")
                            ]
                            if not _dns_rows.empty:
                                _dns_pts_em = int(_dns_rows["puntos"].sum())
                except Exception: pass

                def _sec_html(pred_d, pfx, etapa_lbl, n_pos, pts_dict):
                    if not isinstance(pred_d, dict): return "", 0
                    _sec = [f"<h4 style='color:#93c5fd;margin:12px 0 6px;'>{etapa_lbl}</h4>",
                            "<table style='border-collapse:collapse;width:100%;font-size:13px;'>",
                            "<tr style='background:#1a2040;'><th style='padding:6px 10px;text-align:left;'>Pos</th><th style='padding:6px 10px;'>Tu predicción</th><th style='padding:6px 10px;'>Resultado real</th><th style='padding:6px 10px;'>Acierto</th><th style='padding:6px 10px;'>Pts</th></tr>"]
                    _pts_s = 0; _aciertos_s = 0
                    for _p in range(1, n_pos+1):
                        _pv = str(pred_d.get(_p, pred_d.get(str(_p), ""))).strip()
                        if not _pv: continue
                        _rv = str(oficial_adm.get(f"{pfx}{_p}","")).strip()
                        _ok = bool(_rv and _nn_em(_pv) == _nn_em(_rv))
                        _ep = pts_dict.get(_p,0) if _ok else 0; _pts_s += _ep
                        if _ok: _aciertos_s += 1
                        _bg = "#1a3a1a" if _ok else "#3a1a1a"
                        _ico = "✅" if _ok else "❌"
                        _sec.append(f"<tr style='background:{_bg};'><td style='padding:5px 10px;'>P{_p}</td><td style='padding:5px 10px;'>{_pv}</td><td style='padding:5px 10px;'>{_rv if _rv else '⏳'}</td><td style='padding:5px 10px;text-align:center;'>{_ico}</td><td style='padding:5px 10px;text-align:center;color:#ffdd7a;font-weight:bold;'>{_ep if _ep else ''}</td></tr>")
                    _pleno = {"q":5,"s":3,"r":5,"c":3}.get(pfx,0)
                    if _aciertos_s == n_pos and _aciertos_s > 0 and _pleno:
                        _pts_s += _pleno
                        _sec.append(f"<tr style='background:#2a2a00;'><td colspan=4 style='padding:5px 10px;color:#ffdd7a;font-weight:bold;'>🎯 PLENO PERFECTO!</td><td style='padding:5px 10px;color:#ffdd7a;font-weight:bold;'>+{_pleno}</td></tr>")
                    _sec.append(f"</table><p style='color:#4ade80;font-weight:bold;margin:4px 0;'>Subtotal: +{_pts_s} pts</p>")
                    return "".join(_sec), _pts_s

                _sq, _pq = _sec_html(_dq_em, "q", "⏱️ CLASIFICACIÓN", 5, _ESCALA_EM["q"])
                _lines.append(_sq); _total_em += _pq
                if gp_adm in GPS_SPRINT:
                    _ss, _ps = _sec_html(_ds_em, "s", "⚡ SPRINT", 8, _ESCALA_EM["s"])
                    _lines.append(_ss); _total_em += _ps
                _sr, _pr = _sec_html(_dr_em, "r", "🏁 CARRERA", 10, _ESCALA_EM["r"])
                _lines.append(_sr); _total_em += _pr
                _cons_em = _dc_em if isinstance(_dc_em,dict) and _dc_em else (
                           {1:_dr_em.get("c1"),2:_dr_em.get("c2"),3:_dr_em.get("c3")} if isinstance(_dr_em,dict) else {})
                _sc, _pc = _sec_html(_cons_em, "c", "🏗️ CONSTRUCTORES", 3, _ESCALA_EM["c"])
                _lines.append(_sc); _total_em += _pc
                # Colapinto
                if isinstance(_dq_em,dict):
                    _cq = str(_dq_em.get("colapinto_q","")).strip()
                    if _cq:
                        _cqr = str(oficial_adm.get("col_q","")).strip()
                        _cok = bool(_cqr and str(_cq)==str(_cqr)); _cpts = 10 if _cok else 0; _total_em += _cpts
                        _lines.append(f"<p>🇦🇷 Colapinto Qualy: P{_cq} → {'✅ +10pts' if _cok else '❌'}</p>")
                if isinstance(_dr_em,dict):
                    _cr = str(_dr_em.get("colapinto_r","")).strip()
                    if _cr:
                        _crr = str(oficial_adm.get("col_r","")).strip()
                        _crok = bool(_crr and str(_cr)==str(_crr)); _crpts = 20 if _crok else 0; _total_em += _crpts
                        _lines.append(f"<p>🇦🇷 Colapinto Carrera: P{_cr} → {'✅ +20pts' if _crok else '❌'}</p>")
                # DNS penalty
                if _dns_pts_em != 0:
                    _lines.append(
                        f"<div style='background:#3a0000;border:1px solid #ff4444;border-radius:8px;"
                        f"padding:10px 14px;margin:10px 0;'>"
                        f"<h4 style='color:#ff6644;margin:0 0 4px;'>⛔ SANCIÓN DNS</h4>"
                        f"<p style='color:#ffaaaa;margin:0;'>No enviaste todas las predicciones</p>"
                        f"<p style='color:#ff4444;font-size:18px;font-weight:bold;margin:4px 0 0;'>"
                        f"{_dns_pts_em} pts</p></div>")
                    _total_em += _dns_pts_em
                _lines.append(
                    f"<div style='border-top:2px solid #D4AF37;padding-top:14px;margin-top:14px;'>"
                    f"<h2 style='color:#D4AF37;margin:0;'>🏆 TOTAL ESTE GP: {_total_em} pts</h2>"
                    + (f"<p style='color:#ff6644;font-size:12px;margin:4px 0 0;'>Incluye sanción DNS de {_dns_pts_em} pts</p>" if _dns_pts_em < 0 else "")
                    + f"</div>")
                _lines.append("<p style='font-size:11px;color:#666;margin-top:16px;'>torneofefewolf2026.streamlit.app</p></div>")
                return "".join(_lines), _total_em

            for _pil_em in PILOTOS_TORNEO:
                _html_em, _pts_em = _build_email_html_adm(_pil_em)
                _clr_em = PILOTO_COLORS.get(_pil_em,"#a855f7")
                with st.expander(f"📧 Email para {_pil_em} — {_pts_em} pts"):
                    st.markdown(_html_em, unsafe_allow_html=True)

            # Step 2: Confirm send
            st.markdown("---")
            st.markdown("**¿Todo OK? Confirmá el envío:**")
            if st.button("✅ CONFIRMAR Y ENVIAR EMAILS A TODOS", key="adm_email_confirm_btn",
                         use_container_width=True, type="primary"):
                with st.spinner("Enviando emails…"):
                    try:
                        import smtplib
                        from email.mime.multipart import MIMEMultipart as _MMul2
                        from email.mime.text import MIMEText as _MTr2
                        _gm_u = st.secrets.get("GMAIL_USER","")
                        _gm_p = st.secrets.get("GMAIL_APP_PASSWORD","")
                        _emails_map = st.secrets.get("emails",{})
                        _sent_r = 0
                        for _u_s in PILOTOS_TORNEO:
                            _em_s = str(_emails_map.get(_u_s,""))
                            if not _em_s or not _gm_u: continue
                            try:
                                _html_s, _pts_s = _build_email_html_adm(_u_s)
                                _gp_short_s = gp_adm.split(". ",1)[-1] if ". " in gp_adm else gp_adm
                                _msg_s = _MMul2()
                                _msg_s["From"] = f"Torneo Fefe Wolf <{_gm_u}>"
                                _msg_s["To"] = _em_s
                                _msg_s["Subject"] = f"🏆 Tus aciertos — {_gp_short_s} | Torneo Fefe Wolf 2026"
                                _msg_s.attach(_MTr2(_html_s,"html","utf-8"))
                                try:
                                    with smtplib.SMTP_SSL("smtp.gmail.com",465) as _sv_s:
                                        _sv_s.login(_gm_u,_gm_p); _sv_s.send_message(_msg_s); _sent_r+=1
                                except Exception:
                                    with smtplib.SMTP("smtp.gmail.com",587) as _sv_s2:
                                        _sv_s2.starttls(); _sv_s2.login(_gm_u,_gm_p)
                                        _sv_s2.send_message(_msg_s); _sent_r+=1
                            except Exception as _se: st.warning(f"Error enviando a {_u_s}: {_se}")
                        if _sent_r > 0:
                            st.success(f"✅ {_sent_r}/{len(PILOTOS_TORNEO)} emails enviados correctamente")
                            st.session_state["_adm_show_email_preview"] = False
                        else:
                            st.error("❌ No se pudo enviar ningún email. Verificá GMAIL_USER y GMAIL_APP_PASSWORD en secrets.toml")
                    except Exception as _ee: st.error(f"Error: {_ee}")

            if st.button("✖ Cancelar", key="adm_email_cancel_btn"):
                st.session_state["_adm_show_email_preview"] = False; st.rerun()

        # Calcular y sumar a Posiciones
        if st.button("⚡ CALCULAR + SUMAR A TABLA", key="adm_calc_all_btn",
                     use_container_width=True):
            with st.spinner("Calculando y actualizando tabla… (puede tardar 1-2 min, cada guardado reintenta solo si falla)"):
                try:
                    _res_calc = _safe_call(
                        madm["calcular"],
                        gp_calc=gp_adm, oficial=oficial_adm,
                        pilotos_torneo=PILOTOS_TORNEO, gps_sprint=GPS_SPRINT,
                        timeout_sec=240, default=None)
                    # calcular_y_actualizar_todos puede retornar (ok, msg) o DataFrame
                    if _res_calc is None:
                        st.error("❌ Timeout de la app (240s) esperando la respuesta. Antes de volver a "
                                 "tocar el botón, fijate en la Tabla de Posiciones si los puntos de este GP "
                                 "ya aparecen sumados — el cálculo puede haber terminado igual en segundo plano.")
                    elif isinstance(_res_calc, tuple) and len(_res_calc) == 2:
                        _ok_c, _msg_c = _res_calc
                        if _ok_c: st.success(f"✅ {_msg_c}")
                        else: st.error(f"❌ {_msg_c}")
                    elif hasattr(_res_calc, "empty"):
                        # Es un DataFrame
                        if not _res_calc.empty:
                            _tiene_ok_col = "OK" in _res_calc.columns
                            _fallidos = _res_calc[_res_calc["OK"] == False] if _tiene_ok_col else pd.DataFrame()
                            _exitosos = _res_calc[_res_calc["OK"] != False] if _tiene_ok_col else _res_calc
                            if _tiene_ok_col and not _fallidos.empty and "-" not in _fallidos["Piloto"].values:
                                st.warning(f"⚠️ {len(_exitosos)} formulero(s) sumados correctamente, "
                                           f"pero {len(_fallidos)} tuvieron un error de red y NO se procesaron: "
                                           f"**{', '.join(_fallidos['Piloto'].tolist())}**. "
                                           f"El GP queda SIN bloquear a propósito — volvé a apretar el botón "
                                           f"para reintentar. Es seguro: cada Formulero tiene su propio candado "
                                           f"interno, así que a los que ya sumaron bien NO se les vuelve a sumar.")
                            else:
                                st.success("✅ GP calculado y sumado a la tabla — todos los formuleros OK.")
                            st.dataframe(_res_calc, use_container_width=True)
                        else:
                            st.error("❌ El cálculo no generó resultados. Verificá los resultados oficiales.")
                    else:
                        st.info(f"Resultado: {_res_calc}")
                except Exception as _e2: st.error(f"Error: {_e2}")

    # ════ TAB 2: SANCIONES DNS ═════════════════════════════════════════
    with _at2:
        st.markdown('<div class="admin-title">⛔ Aplicar / Revertir DNS</div>', unsafe_allow_html=True)
        st.caption("⚠️ Solo aplicar UNA vez por piloto/GP. El sistema bloquea duplicados.")
        _ds1,_ds2 = st.columns([2,2])
        with _ds1:
            gp_dns = st.selectbox("GP:", GPS_ACTIVOS, key="adm_dns_gp",
                                  format_func=lambda x: x.split(". ",1)[-1] if ". " in x else x)
            pil_dns = st.selectbox("Formulero:", PILOTOS_TORNEO, key="adm_dns_pil")
            eta_dns = st.selectbox("Etapa:", ["QUALY","SPRINT","CARRERA"], key="adm_dns_etapa")
            pts_dns = st.number_input("Pts (negativo = sanción)", value=-25, step=1,
                                       min_value=-50, max_value=0, key="adm_dns_pts")
        with _ds2:
            st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
            # Check if already applied
            _dns_key = f"dns_applied_{gp_dns}_{pil_dns}_{eta_dns}"
            _ya_aplicado = st.session_state.get(_dns_key, False)
            if _ya_aplicado:
                st.warning(f"⚠️ Ya aplicaste DNS a {pil_dns} en {eta_dns} de este GP en esta sesión.")
                if st.button("🔓 Aplicar de todas formas", key="adm_dns_force", use_container_width=True):
                    st.session_state.pop(_dns_key, None)
                    st.rerun()
            else:
                if st.button("⚡ Aplicar sanción DNS", key="adm_dns_apply", use_container_width=True):
                    with st.spinner("Aplicando DNS... (puede tardar si Google Sheets está ocupado)"):
                        # Retry hasta 3 veces si hay error 429
                        ok_d, msg_d = False, "No se pudo conectar"
                        for _retry_dns in range(3):
                            ok_d, msg_d = _safe_call(mdb["actualizar_tabla_general"], pil_dns, int(pts_dns),
                                                     gp_dns, timeout_sec=40, default=(False,"Timeout"))
                            if ok_d or "429" not in str(msg_d):
                                break
                            import time as _time_dns; _time_dns.sleep(2 + _retry_dns * 2)
                    if ok_d:
                        st.session_state[_dns_key] = True
                        st.success(f"✅ {msg_d} — DNS aplicado a {pil_dns} ({pts_dns} pts)")
                    else:
                        if "429" in str(msg_d):
                            st.error(f"❌ Google Sheets está saturado (cuota). Esperá 1 minuto y reintentá.")
                        else:
                            st.error(f"❌ {msg_d}")

            if st.button("↩️ REVERTIR DNS de este GP", key="adm_dns_revert", use_container_width=True):
                with st.spinner("Revirtiendo..."):
                    try:
                        rev_ok, rev_msg = _safe_call(mdb["revertir_dns_gp"], gp_dns,
                                                      timeout_sec=30, default=(False,"Timeout"))
                        if rev_ok:
                            # Clear all DNS keys for this GP
                            for _k in list(st.session_state.keys()):
                                if f"dns_applied_{gp_dns}" in _k:
                                    del st.session_state[_k]
                        (st.success if rev_ok else st.error)(f"{'✅' if rev_ok else '❌'} {rev_msg}")
                    except Exception as _re: st.error(str(_re))

    # ════ TAB 3: COMUNICADOS ════════════════════════════════════════════
    # Old _at3 = Comunicados → now _at5
    # Old _at4 = Usuarios   → now _at3
    # New _at4 = Invitaciones
    # _at6 = Log

    # ════ TAB 3: USUARIOS ══════════════════════════════════════════════
    with _at3:
        st.markdown('<div class="admin-title">👥 Gestión de Usuarios</div>', unsafe_allow_html=True)
        mauth_adm = _mod_auth()
        if "_error" not in mauth_adm:
            with st.expander("➕ Crear usuario"):
                _nu = st.text_input("Nombre", key="adm_nu")
                _np = st.text_input("Contraseña", type="password", key="adm_np")
                _nr = st.selectbox("Rol", ["Formulero","FIPF","Sub Comisario"], key="adm_nr")
                if st.button("✅ Crear", key="adm_create_btn", use_container_width=True):
                    _nu_clean = (_nu or "").strip()
                    if not _nu_clean:
                        st.error("❌ Poné el nombre completo del usuario.")
                    elif len((_np or "").strip()) < 4:
                        st.error("❌ La contraseña debe tener al menos 4 caracteres.")
                    else:
                        # Limpiar caché para leer la hoja actualizada antes de chequear duplicados
                        try: st.cache_data.clear()
                        except Exception: pass
                        try: st.cache_resource.clear()
                        except Exception: pass
                        # CLAVE: limpiar caché interno de core.auth
                        try:
                            import core.auth as _ca_cr
                            if hasattr(_ca_cr,"_AUTH_CACHE"): _ca_cr._AUTH_CACHE.clear()
                        except Exception: pass
                        # Evitar duplicados: chequear si ya existe
                        _ya_existe_u = False
                        try:
                            _fn_get_c = mauth_adm.get("get_user_row")
                            if callable(_fn_get_c):
                                _f_c, _ = _safe_call(_fn_get_c, _nu_clean, timeout_sec=8, default=(False,None))
                                _ya_existe_u = bool(_f_c)
                        except Exception: pass
                        if _ya_existe_u:
                            st.warning(f"⚠️ '{_nu_clean}' ya existe. No lo creo de nuevo. "
                                       f"Si querés cambiarle la contraseña, usá 🔑 Resetear contraseña.")
                        else:
                            # Color correcto si es un formulero conocido, sino violeta neutro
                            _color_nuevo = PILOTO_COLORS.get(_nu_clean, "#a855f7")
                            # bootstrap_user requiere un mother code — lo generamos solo (no se usa más)
                            _mc_auto = "WOLF" + "".join(str(ord(c)) for c in _nu_clean[:3])
                            ok_u, msg_u = _safe_call(mauth_adm.get("bootstrap_user", lambda *a,**k:(False,"N/A")),
                                                     _nu_clean, _nr, _np, _mc_auto,
                                                     copas=0, color=_color_nuevo,
                                                     timeout_sec=30, default=(False,"Timeout"))
                            if ok_u:
                                st.success(f"✅ Usuario '{_nu_clean}' creado. Ahora seteale el PIN abajo.")
                                try: st.cache_data.clear()
                                except Exception: pass
                                try: st.cache_resource.clear()
                                except Exception: pass
                                try:
                                    import core.auth as _ca_cr2
                                    if hasattr(_ca_cr2,"_AUTH_CACHE"): _ca_cr2._AUTH_CACHE.clear()
                                except Exception: pass
                            else:
                                st.error(f"❌ {msg_u}")
            with st.expander("🔑 Resetear contraseña"):
                _ru = st.selectbox("Usuario:", PILOTOS_TORNEO, key="adm_ru")
                _rp = st.text_input("Nueva contraseña", type="password", key="adm_rp")
                if st.button("🔑 Resetear", key="adm_reset_btn", use_container_width=True):
                    ok_r, msg_r = _safe_call(mauth_adm.get("admin_reset_password", lambda *a,**k:(False,"N/A")),
                                             _ru, _rp, timeout_sec=30, default=(False,"Timeout"))
                    (st.success if ok_r else st.error)(f"{'✅' if ok_r else '❌'} {msg_r}")
            with st.expander("🔐 Setear PIN de envío de predicciones"):
                st.caption("El PIN (4 dígitos) lo usa el formulero para confirmar el envío de sus predicciones.")
                _piu = st.selectbox("Usuario", PILOTOS_TORNEO, key="adm_pin_u")
                _piv = st.text_input("Nuevo PIN (4 dígitos)", type="password", max_chars=4, key="adm_pin_v")
                _pin_c1, _pin_c2 = st.columns([1,1])
                with _pin_c1:
                    _do_set_pin = st.button("Guardar PIN", key="adm_pin_btn", use_container_width=True)
                with _pin_c2:
                    _do_diag = st.button("🔍 Diagnóstico", key="adm_pin_diag", use_container_width=True)

                # Diagnóstico: mostrar qué usuarios ve la hoja Usuarios
                if _do_diag:
                    try:
                        from core.database import conectar_google_sheets as _cgs_diag
                        _ws_diag = _cgs_diag("Usuarios")
                        if _ws_diag:
                            _vals_diag = _ws_diag.get_all_values()
                            if _vals_diag:
                                _hdr_diag = _vals_diag[0]
                                st.write("**Encabezados de la hoja Usuarios:**", _hdr_diag)
                                _nombres = [r[0] for r in _vals_diag[1:] if r and r[0].strip()]
                                st.write("**Usuarios en la hoja (col A):**")
                                for _n in _nombres:
                                    _match = "✅ coincide" if _n.strip()==_piu.strip() else (
                                             f"⚠️ '{_n}' (len={len(_n)})")
                                    st.write(f"- `{_n}` {_match}")
                                if "pin_hash" not in [h.lower().strip() for h in _hdr_diag]:
                                    st.warning("⚠️ No existe la columna 'pin_hash' en la hoja. "
                                               "Hay que agregarla como encabezado.")
                        else:
                            st.error("No se pudo conectar a la hoja Usuarios.")
                    except Exception as _de:
                        st.error(f"Error diagnóstico: {_de}")

                if _do_set_pin:
                    if not (_piv or "").strip().isdigit() or len((_piv or "").strip()) != 4:
                        st.error("❌ El PIN debe ser exactamente 4 dígitos numéricos.")
                    else:
                        try: st.cache_data.clear()
                        except Exception: pass
                        try: st.cache_resource.clear()
                        except Exception: pass
                        # CLAVE: limpiar el caché interno de core.auth (_AUTH_CACHE)
                        # que es lo que hacía que set_pin no encontrara al usuario recién creado
                        try:
                            import core.auth as _ca_mod
                            if hasattr(_ca_mod, "_AUTH_CACHE"):
                                _ca_mod._AUTH_CACHE.clear()
                        except Exception: pass
                        _pin_clean = _piv.strip()
                        _usr_pin = _piu.strip()
                        # Ahora set_pin debería funcionar (caché limpio)
                        ok_p, msg_p = False, ""
                        if "set_pin" in mauth_adm:
                            ok_p, msg_p = _safe_call(mauth_adm["set_pin"], _usr_pin, _pin_clean,
                                                     timeout_sec=30, default=(False,"Timeout"))
                        # Fallback: escribir pin_hash directo con el MISMO formato que auth.py (base64)
                        if not ok_p:
                            try:
                                import hashlib as _hl_pin, os as _os_pin, base64 as _b64_pin
                                from core.database import conectar_google_sheets as _cgs_pin
                                _ws_pin = _cgs_pin("Usuarios")
                                if _ws_pin:
                                    _vals_pin = _ws_pin.get_all_values()
                                    _hdr_pin = [h.strip() for h in _vals_pin[0]]
                                    if "pin_hash" not in _hdr_pin:
                                        _ws_pin.update_cell(1, len(_vals_pin[0])+1, "pin_hash")
                                        _vals_pin = _ws_pin.get_all_values()
                                        _hdr_pin = [h.strip() for h in _vals_pin[0]]
                                    _col_pin = _hdr_pin.index("pin_hash") + 1
                                    _row_idx = None
                                    for _ri, _rr in enumerate(_vals_pin[1:], start=2):
                                        if _rr and _rr[0].strip().lower() == _usr_pin.lower():
                                            _row_idx = _ri; break
                                    if _row_idx:
                                        # MISMO formato que auth.py: pbkdf2$iters$salt_b64$hash_b64
                                        _salt = _os_pin.urandom(16)
                                        _it = 210000
                                        _dk = _hl_pin.pbkdf2_hmac("sha256", _pin_clean.encode("utf-8"),
                                                                  _salt, _it, dklen=32)
                                        _hash_pin = (f"pbkdf2${_it}$"
                                                     f"{_b64_pin.b64encode(_salt).decode('utf-8')}$"
                                                     f"{_b64_pin.b64encode(_dk).decode('utf-8')}")
                                        _ws_pin.update_cell(_row_idx, _col_pin, _hash_pin)
                                        ok_p = True; msg_p = "PIN escrito directo en la hoja"
                                        # limpiar caché auth para que verify_pin lo lea
                                        try:
                                            import core.auth as _ca2
                                            if hasattr(_ca2,"_AUTH_CACHE"): _ca2._AUTH_CACHE.clear()
                                        except Exception: pass
                                    else:
                                        msg_p = f"No encontré la fila de '{_usr_pin}' en la hoja"
                            except Exception as _pe:
                                msg_p = f"Fallback falló: {_pe}"
                        if ok_p:
                            st.success(f"✅ PIN guardado para {_piu}. Ya puede usarlo para enviar predicciones.")
                        else:
                            st.error(f"❌ {msg_p}")
                            st.caption("Tocá 🔍 Diagnóstico para ver cómo está guardado el usuario en la hoja.")
        else:
            st.error("Auth module unavailable.")

    # ════ TAB 4: INVITACIONES ══════════════════════════════════════════
    with _at4:
        st.markdown('<div class="admin-title">🎟️ Códigos de Invitación</div>', unsafe_allow_html=True)
        st.caption("Generá un código único y enviáselo al nuevo formulero. Se registra en secrets.toml → INVITE_CODES.")
        try:
            _cur_codes = st.secrets.get("INVITE_CODES","")
            if _cur_codes:
                st.markdown(f'<div style="background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.25);'
                            f'border-radius:10px;padding:10px 14px;margin-bottom:10px;">'
                            f'<div style="font-size:9px;color:rgba(212,175,55,.6);text-transform:uppercase;letter-spacing:.1em;">Códigos activos</div>'
                            f'<div style="font-size:13px;color:#ffdd7a;font-weight:800;margin-top:4px;">{_cur_codes}</div>'
                            f'</div>', unsafe_allow_html=True)
            else:
                st.info("Sin códigos configurados. Agrega INVITE_CODES en secrets.toml.")
        except Exception: pass
        if st.button("🎲 Generar nuevo código", key="adm_gen_inv", use_container_width=True):
            import random, string as _str_inv
            _new_code = "WOLF-" + "".join(random.choices(_str_inv.ascii_uppercase + _str_inv.digits, k=6))
            st.success(f"✅ Nuevo código: **{_new_code}**")
            st.code(f'INVITE_CODES = "{_new_code}"')
            st.caption("Copiá este código y agregalo a secrets.toml")

    # ════ TAB 5: COMUNICADOS ════════════════════════════════════════════
    with _at5:
        st.markdown('<div class="admin-title">📧 Enviar comunicado a todos</div>', unsafe_allow_html=True)
        _asunto = st.text_input("Asunto", key="adm_com_asunto",
                                placeholder="Ej: Cambio de horario GP Canadá")
        _cuerpo = st.text_area("Mensaje", key="adm_com_cuerpo", height=120,
                               placeholder="Escribí el comunicado oficial aquí…")
        # Imagen opcional
        with st.expander("🖼️ Agregar imagen al comunicado (opcional)", expanded=False):
            _com_img_mode = st.radio("Origen:", ["🔗 URL","📁 Subir archivo"], horizontal=True,
                                     key="adm_com_img_mode", label_visibility="collapsed")
            _com_img = ""
            if _com_img_mode == "🔗 URL":
                _com_img = st.text_input("URL de imagen (https://...)", key="adm_com_img_url",
                                         placeholder="https://i.ibb.co/XXXX/foto.jpg").strip()
            else:
                _com_up = st.file_uploader("Subir imagen", type=["jpg","jpeg","png","webp"], key="adm_com_img_file")
                if _com_up is not None:
                    import base64 as _b64_co, io as _io_co
                    _raw_co = _com_up.read()
                    try:
                        from PIL import Image as _PILco
                        _im_co = _PILco.open(_io_co.BytesIO(_raw_co))
                        if _im_co.mode in ("RGBA","P","LA"): _im_co = _im_co.convert("RGB")
                        _im_co.thumbnail((900,900))
                        _buf_co = _io_co.BytesIO(); _q_co = 80
                        _im_co.save(_buf_co, format="JPEG", quality=_q_co, optimize=True)
                        while _buf_co.tell() > 300_000 and _q_co > 35:
                            _q_co -= 10; _buf_co = _io_co.BytesIO()
                            _im_co.save(_buf_co, format="JPEG", quality=_q_co, optimize=True)
                        _raw_co = _buf_co.getvalue()
                    except Exception: pass
                    _com_img = f"data:image/jpeg;base64,{_b64_co.b64encode(_raw_co).decode()}"
                    st.image(_raw_co, caption=f"Preview ({len(_raw_co)//1024} KB)", width=200)
        if st.button("📧 Enviar comunicado", key="adm_com_send", use_container_width=True):
            _gm_u = st.secrets.get("GMAIL_USER",""); _gm_p = st.secrets.get("GMAIL_APP_PASSWORD","")
            _emails = st.secrets.get("emails",{})
            if not _asunto.strip() or not _cuerpo.strip():
                st.warning("Completá asunto y mensaje.")
            elif not _gm_u or not _gm_p:
                st.warning("Configurá GMAIL_USER y GMAIL_APP_PASSWORD en secrets.")
            else:
                import smtplib
                from email.mime.multipart import MIMEMultipart as _MMc
                from email.mime.text import MIMEText as _MTc
                _img_html_com = (f"<img src='{_com_img}' style='width:100%;max-width:560px;"
                                 f"border-radius:10px;margin:12px 0;display:block;'>" if _com_img else "")
                _body_html = (
                    f"<div style='font-family:Arial;max-width:600px;background:#07091a;color:#e8ecff;padding:22px;border-radius:12px;'>"
                    f"<h2 style='color:#D4AF37;margin-bottom:2px;'>🏎️ TORNEO FEFE WOLF 2026</h2>"
                    f"<div style='font-size:12px;color:#ffdd7a;letter-spacing:.12em;margin-bottom:10px;'>📢 COMUNICADO OFICIAL</div>"
                    f"{_img_html_com}"
                    f"<div style='font-size:14px;line-height:1.6;white-space:pre-wrap;'>{_cuerpo.strip()}</div>"
                    f"<div style='border-top:1px solid #333;margin-top:16px;padding-top:10px;font-size:11px;color:#666;'>"
                    f"🏁 torneofefewolf2026.streamlit.app</div></div>")
                _sent = 0
                for _pn, _em in _emails.items():
                    if not _em: continue
                    try:
                        _mm = _MMc()
                        _mm["Subject"] = f"📢 {_asunto.strip()} — Torneo Fefe Wolf"
                        _mm["From"] = f"Torneo Fefe Wolf <{_gm_u}>"
                        _mm["To"] = _em
                        _mm.attach(_MTc(_body_html,"html","utf-8"))
                        with smtplib.SMTP_SSL("smtp.gmail.com",465) as _sv:
                            _sv.login(_gm_u,_gm_p); _sv.send_message(_mm)
                        _sent += 1
                    except Exception as _ec: st.warning(f"Error {_pn}: {_ec}")
                if _sent: st.success(f"✅ Comunicado enviado a {_sent} formuleros.")
                else: st.error("❌ No se pudo enviar. Verificá GMAIL_APP_PASSWORD.")

    # ════ TAB 6: LOG ════════════════════════════════════════════════════
    with _at6:
        st.markdown('<div class="admin-title">📋 Log de cambios (hoja Audit)</div>', unsafe_allow_html=True)
        if st.button("🔄 Cargar log", key="adm_log_btn", use_container_width=True):
            try:
                from core.database import conectar_google_sheets as _cgs_log
                _ws_log = _cgs_log("Audit")
                if _ws_log:
                    _log_rows = _ws_log.get_all_values()
                    if _log_rows:
                        st.dataframe(pd.DataFrame(_log_rows[1:], columns=_log_rows[0]),
                                     use_container_width=True)
                    else: st.info("Sin registros.")
                else: st.warning("Hoja Audit no encontrada.")
            except Exception as _le: st.error(f"Error: {_le}")


def pantalla_calculadora_puntos():
    mdb=_mod_db(); madm=_mod_admin(); mcore=_mod_core(); mauth=_mod_auth()
    if any("_error" in x for x in [mdb,madm,mcore,mauth]):
        st.error("⚠️ Módulos no disponibles."); return
    st.title("🧮 CENTRO DE CÓMPUTOS")
    st.info("🔒 ÁREA RESTRINGIDA")
    pwd=st.text_input("🔑 Clave de Comisario:",type="password")
    if pwd!="2022": st.stop()
    st.success("✅ ACCESO AUTORIZADO — MODO COMISARIO"); st.divider()
    gp_calc=st.selectbox("Gran Premio:",GPS_OFICIALES,key="gp_calc_main")
    estado=_safe_call(mcore["obtener_estado_gp"],gp_calc,HORARIOS_CARRERA,TZ,timeout_sec=4,default={"habilitado":False,"mensaje":"OK"})
    if (estado or {}).get("habilitado",True): st.error("⛔ El GP sigue habilitado."); st.stop()
    st.success(f"✅ OK para calcular: {(estado or {}).get('mensaje','')}")
    st.subheader("1) RESULTADOS OFICIALES (FIA)")
    oficial={}; c1,c2,c3=st.columns(3)
    with c1:
        st.markdown("**🏁 Carrera (1–10)**")
        for i in range(1,11): oficial[f"r{i}"]=st.text_input(f"Carrera {i}°",key=f"of_r{i}-{gp_calc}")
        oficial["col_r"]=st.number_input("Colapinto (Carrera)",1,22,10,key=f"of_cr-{gp_calc}")
    with c2:
        st.markdown("**⏱️ Qualy (1–5)**")
        for i in range(1,6): oficial[f"q{i}"]=st.text_input(f"Qualy {i}°",key=f"of_q{i}-{gp_calc}")
        oficial["col_q"]=st.number_input("Colapinto (Qualy)",1,22,10,key=f"of_cq-{gp_calc}")
    with c3:
        st.markdown("**🛠️ Constructores**")
        of_r_auto={i:oficial.get(f"r{i}","") for i in ESCALA_CARRERA_JUEGO.keys()}
        top3,tp=calcular_constructores_auto(of_r_auto,GRILLA_2026,ESCALA_CARRERA_JUEGO)
        if len(top3)>=3:
            oficial["c1"],oficial["c2"],oficial["c3"]=top3[0],top3[1],top3[2]
            st.markdown(f'<div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);'
                        f'border-radius:8px;padding:6px 10px;font-size:12px;color:#4ade80;margin-bottom:6px;">'
                        f'🟢 Auto: <b>{top3[0]}</b> / <b>{top3[1]}</b> / <b>{top3[2]}</b></div>',
                        unsafe_allow_html=True)
        else:
            oficial["c1"]=oficial["c2"]=oficial["c3"]=""
            st.markdown('<div style="background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);'
                        'border-radius:8px;padding:6px 10px;font-size:12px;color:#fbbf24;margin-bottom:6px;">'
                        '⚠️ Cargá primero los 10 de carrera.</div>', unsafe_allow_html=True)
        if tp: st.caption(str(tp))
        st.markdown("**✏️ Ajuste manual** (si difiere del FIA):")
        _teams_calc = list(GRILLA_2026.keys())
        _c1_ov = st.selectbox("1° Constructor", ["(Automático)"] + _teams_calc, key=f"c1_ov-{gp_calc}")
        _c2_ov = st.selectbox("2° Constructor", ["(Automático)"] + _teams_calc, key=f"c2_ov-{gp_calc}")
        _c3_ov = st.selectbox("3° Constructor", ["(Automático)"] + _teams_calc, key=f"c3_ov-{gp_calc}")
        if _c1_ov != "(Automático)": oficial["c1"] = _c1_ov
        if _c2_ov != "(Automático)": oficial["c2"] = _c2_ov
        if _c3_ov != "(Automático)": oficial["c3"] = _c3_ov
        st.markdown(f'<div style="font-size:11px;color:rgba(169,178,214,.7);margin-top:4px;">'
                    f'✅ Final: <b style="color:#4ade80">{oficial.get("c1","?")}</b> / '
                    f'<b style="color:#4ade80">{oficial.get("c2","?")}</b> / '
                    f'<b style="color:#4ade80">{oficial.get("c3","?")}</b></div>',
                    unsafe_allow_html=True)
    if gp_calc in GPS_SPRINT:
        st.markdown("### ⚡ Sprint (1–8)"); cs1,cs2=st.columns(2)
        with cs1:
            for i in range(1,5): oficial[f"s{i}"]=st.text_input(f"Sprint {i}°",key=f"of_s{i}-{gp_calc}")
        with cs2:
            for i in range(5,9): oficial[f"s{i}"]=st.text_input(f"Sprint {i}°",key=f"of_s{i}-{gp_calc}")
    gp_done_key=f"GP_DONE::{gp_calc}"
    gp_done=_safe_call(mdb["lock_exists"],gp_done_key,timeout_sec=4,default=False)
    st.divider(); st.subheader("⚡ Calcular y actualizar todo el GP")
    if gp_done: st.warning("🔒 Ya calculado.")
    if st.button("⚡ CALCULAR Y ACTUALIZAR TODOS",use_container_width=True,key=f"btn_auto_{gp_calc}",disabled=gp_done):
        try:
            _res_auto = madm["calcular"](gp_calc=gp_calc,oficial=oficial,pilotos_torneo=PILOTOS_TORNEO,gps_sprint=GPS_SPRINT)
            if isinstance(_res_auto, tuple) and len(_res_auto) == 2:
                _ok_a, _msg_a = _res_auto
                if _ok_a: st.success(f"✅ {_msg_a}")
                else: st.error(f"❌ {_msg_a}")
            elif hasattr(_res_auto, "empty"):
                if not _res_auto.empty:
                    st.success("✅ GP calculado y sumado correctamente.")
                    st.dataframe(_res_auto, use_container_width=True)
                else:
                    st.error("❌ No se generaron resultados. Verificá los datos oficiales.")
            else:
                st.info(f"Resultado: {_res_auto}")
        except Exception as e: st.error(f"❌ {e}"); st.exception(e)
    st.divider(); st.subheader("🧾 Generar historial (sin sumar puntos)")
    st.caption("Úsalo para reconstruir el historial de Google Sheets sin volver a sumar a Posiciones. "
               "Requiere que ya hayas cargado los resultados oficiales arriba.")

    hist_done_key = f"HIST_DONE::{gp_calc}"

    # ── Botón de limpieza de historial con 0 pts (emergencia) ─────────
    with st.expander("🧹 Limpiar historial con 0 pts (GPs con entradas incorrectas)"):
        st.warning("⚠️ Esto elimina de la hoja Historial todas las filas con 0 puntos para el GP seleccionado. "
                   "Útil cuando el DNS se aplicó mal y escribió 0 en vez de los pts reales.")
        if st.button(f"🗑️ Limpiar filas 0-pts de {gp_calc[:30]} en Historial", key=f"clean_hist_{gp_calc}",
                     use_container_width=True):
            with st.spinner("Limpiando..."):
                try:
                    _sh_clean = __import__('core.database', fromlist=['conectar_google_sheets']).conectar_google_sheets("Historial")
                    if _sh_clean:
                        _all_rows_c = _sh_clean.get_all_values()
                        _to_del = []
                        _gp_clean_s = str(gp_calc).strip()
                        import re as _re_clean
                        _gp_clean_bare = _re_clean.sub(r'^\d+\.\s*','',_gp_clean_s)
                        for _ci, _crow in enumerate(_all_rows_c):
                            if _ci == 0: continue
                            _crow_gp = str(_crow[0]).strip() if _crow else ""
                            _crow_gp_bare = _re_clean.sub(r'^\d+\.\s*','',_crow_gp)
                            if (_crow_gp == _gp_clean_s or _crow_gp_bare == _gp_clean_bare):
                                try:
                                    _pts_v = int(float(str(_crow[2]).strip() or "0"))
                                except Exception: _pts_v = 0
                                if _pts_v == 0:
                                    _to_del.append(_ci + 1)
                        for _di in sorted(_to_del, reverse=True):
                            _sh_clean.delete_rows(_di)
                        st.success(f"✅ Eliminadas {len(_to_del)} filas con 0 pts. Ya podés regenerar el historial.")
                        if "clear_lock" in mdb:
                            _safe_call(mdb["clear_lock"], hist_done_key, timeout_sec=6)
                        st.rerun()
                except Exception as _ce: st.error(f"Error: {_ce}")

    hist_done = _safe_call(mdb["lock_exists"], hist_done_key, timeout_sec=4, default=False)
    # Validate that at least carrera P1 is filled
    _of_r1 = (oficial.get("r1","") or "").strip()
    _of_q1 = (oficial.get("q1","") or "").strip()
    _hist_ok = bool(_of_r1 and _of_q1)
    if hist_done:
        st.warning("🔒 Historial ya generado para este GP. Si necesitás rehacerlo contactá al admin.")
        if st.button("🔓 Desbloquear historial (emergencia)", key=f"hist_unlock_{gp_calc}",
                     use_container_width=True):
            try:
                import sqlite3 as _sq2, os as _os3
                # Intentar primero con la función oficial de database.py
                _unlocked = False
                if "clear_lock" in mdb:
                    try:
                        _safe_call(mdb["clear_lock"], hist_done_key, timeout_sec=4)
                        _unlocked = True
                    except Exception: pass
                # Fallback: acceso directo a locks.db con columna 'k'
                if not _unlocked:
                    _lock_db_path = _os3.path.normpath(
                        _os3.path.join(_os3.path.dirname(_os3.path.abspath(__file__)), "..", "locks.db")
                    )
                    for _d in [_lock_db_path, "locks.db", "torneo.db"]:
                        if _os3.path.exists(str(_d)):
                            try:
                                _c = _sq2.connect(str(_d))
                                _c.execute("DELETE FROM locks WHERE k=?", (hist_done_key,))
                                _c.commit(); _c.close()
                                _unlocked = True; break
                            except Exception: pass
                if _unlocked:
                    st.success("✅ Lock eliminado. Completá los resultados oficiales antes de regenerar.")
                else:
                    st.warning("⚠️ Lock no encontrado. Recargá la página e intentá de nuevo.")
                st.rerun()
            except Exception as _he: st.error(str(_he))
    else:
        if not _hist_ok:
            st.warning("⚠️ Los resultados oficiales parecen vacíos — si ya los cargaste arriba ignorá este aviso. "
                       "El botón funciona igual.")
        st.info("ℹ️ El botón genera el historial **y aplica DNS automáticamente** en el mismo paso.")
        if st.button("🧾 HISTORIAL GENERAL + DNS", use_container_width=True,
                     key=f"btn_hist_{gp_calc}"):
            try:
                import time as _time_hist
                # — Paso 1: Generar historial con reintento si hay error 429 —
                _hist_prog = st.progress(0, text="Generando historial...")
                df_h = None
                for _hint in range(3):
                    try:
                        _hist_prog.progress(20 + _hint*25, text=f"Leyendo predicciones... (intento {_hint+1}/3)")
                        df_h = madm["historial"](
                            gp_calc=gp_calc, oficial=oficial,
                            pilotos_torneo=PILOTOS_TORNEO, gps_sprint=GPS_SPRINT
                        )
                        if df_h is not None and not df_h.empty:
                            break
                    except Exception as _eh:
                        if "429" in str(_eh) and _hint < 2:
                            _hist_prog.progress(30, text=f"Google Sheets saturado, esperando 15s... (intento {_hint+1}/3)")
                            _time_hist.sleep(15)
                        else:
                            raise
                _hist_prog.progress(100, text="✅ Listo")
                _hist_prog.empty()
                if df_h is None or df_h.empty:
                    st.error("❌ No se pudo generar el historial. Verificá que los resultados oficiales estén completos y reintentá.")
                    st.stop()
                st.success("✅ Historial generado.")
                st.dataframe(df_h, use_container_width=True)

                # ── WhatsApp + Email: predicciones completas + aciertos ────
                if not df_h.empty:
                    _do_wa_email(df_h, oficial, gp_calc, mdb)

                # — Paso 2: DNS — SOLO si el GP no fue calculado previamente (evitar doble penalización)
                dns_key_hist = f"DNS_DONE::{gp_calc}"
                dns_ya_hecho = _safe_call(mdb["lock_exists"], dns_key_hist, timeout_sec=4, default=False)

                if dns_ya_hecho:
                    st.info("🔒 DNS ya aplicados previamente — no se duplican.")
                elif gp_done:
                    # GP ya calculado → predicciones existieron al momento del cálculo → NO aplicar DNS
                    st.warning("⚠️ El GP ya fue calculado previamente (lock GP_DONE activo). "
                               "**DNS no se aplica** para no penalizar incorrectamente. "
                               "Si necesitás aplicar DNS manualmente, usá el panel de abajo.")
                else:
                    with st.spinner("Aplicando sanciones DNS..."):
                        df_dns = mdb["aplicar_sanciones_dns"](gp_calc, PILOTOS_TORNEO, GPS_SPRINT)
                    _safe_call(mdb["set_lock"], dns_key_hist, timeout_sec=4)
                    st.success("⛔ Sanciones D.N.S. aplicadas automáticamente.")
                    st.dataframe(df_dns, use_container_width=True)

                # — Bloquear historial —
                _safe_call(mdb["set_lock"], hist_done_key, timeout_sec=4)
                st.success("🔒 Historial bloqueado correctamente.")
                # Telegram notification
                import re as _re_tg
                _gp_tg = _re_tg.sub(r'^\d+\.\s*','',gp_calc).strip()
                _sorted_tg = df_h.sort_values("Total",ascending=False).reset_index(drop=True)
                _tg_lines = [f"🏎️ *TORNEO FEFE WOLF 2026*",f"🏁 *{_gp_tg.upper()}* — HISTORIAL GENERADO",""]
                for _ri, _rr in _sorted_tg.iterrows():
                    _med = {0:"🥇",1:"🥈",2:"🥉"}.get(_ri,f"{_ri+1}°")
                    _tg_lines.append(f"{_med} {_rr['Piloto']}: *{int(_rr.get('Total',0))} pts*")
                _tg_lines += ["","🏁 torneofefewolf2026.streamlit.app"]
                if _send_telegram("\n".join(_tg_lines)):
                    st.success("📱 Notificación enviada al grupo de Telegram.")

            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)
    st.divider(); st.subheader("⛔ SANCIONES D.N.S.")

    # ── DNS manual: aplicar -5 a piloto específico ──────────────────
    with st.expander("✏️ Aplicar DNS manualmente (piloto específico)"):
        st.caption("Aplicá -25 pts directamente a un formulero sin correr la detección automática.")
        _dm1, _dm2, _dm3 = st.columns([3,2,2])
        with _dm1: _dns_pil = st.selectbox("Formulero", PILOTOS_TORNEO, key=f"dns_m_pil_{gp_calc}")
        with _dm2: _dns_etapa_m = st.selectbox("Etapa que faltó", ["QUALY","CARRERA","SPRINT"], key=f"dns_m_et_{gp_calc}")
        with _dm3: _dns_pts_m = st.number_input("Puntos (negativo)", value=-25, step=1,
                                                  min_value=-50, max_value=0, key=f"dns_m_pts_{gp_calc}")
        if st.button(f"⚡ Aplicar {_dns_pts_m} pts a {_dns_pil}", key=f"dns_m_btn_{gp_calc}", use_container_width=True):
            with st.spinner("Aplicando..."):
                ok_m, msg_m = _safe_call(mdb["actualizar_tabla_general"], _dns_pil, int(_dns_pts_m), gp_calc,
                                         timeout_sec=30, default=(False,"Timeout"))
            (st.success if ok_m else st.error)(f"{'✅' if ok_m else '❌'} {msg_m}")
    st.info("**Regla**: −25 pts por cada etapa no enviada (QUALY · SPRINT si aplica · CARRERA+CONSTRUCTORES). El sistema detecta automáticamente quién no envió.")
    dns_key=f"DNS_DONE::{gp_calc}"; dns_done=_safe_call(mdb["lock_exists"],dns_key,timeout_sec=4,default=False)

    # — Preview: show who sent what BEFORE applying
    if st.button("🔍 Ver quién envió predicciones", key=f"btn_dns_preview_{gp_calc}", use_container_width=True):
        try:
            from core.database import detectar_faltantes_por_gp
            falt_prev = detectar_faltantes_por_gp(gp_calc, PILOTOS_TORNEO, GPS_SPRINT)
            want_sprint = gp_calc in GPS_SPRINT
            rows_prev = []
            for p in PILOTOS_TORNEO:
                f = falt_prev[p]
                miss = []
                if not f["QUALY"]: miss.append("❌ QUALY")
                if want_sprint and not f["SPRINT"]: miss.append("❌ SPRINT")
                if not f["CARRERA"]: miss.append("❌ CARRERA")
                pen = -25 * len(miss)
                rows_prev.append({
                    "Piloto": p,
                    "QUALY": "✅" if f["QUALY"] else "❌",
                    "SPRINT": ("✅" if f["SPRINT"] else "❌") if want_sprint else "—",
                    "CARRERA": "✅" if f["CARRERA"] else "❌",
                    "Faltantes": ", ".join(miss) if miss else "✅ Todo enviado",
                    "Penalización": f"{pen} pts" if pen != 0 else "Sin sanción"
                })
            import pandas as _pd_dns
            st.dataframe(_pd_dns.DataFrame(rows_prev), use_container_width=True)
        except Exception as _e:
            st.error(f"Error al verificar: {_e}")

    if dns_done:
        st.warning("🔒 Sanciones ya aplicadas para este GP.")
        st.markdown("---")
        st.markdown("**🚨 Zona de emergencia** — Solo usar si las sanciones fueron aplicadas por error:")
        if st.button("🔄 REVERTIR SANCIONES DNS (suma puntos de vuelta)", key=f"btn_dns_undo_{gp_calc}",
                     use_container_width=True):
            with st.spinner("Revirtiendo DNS — leyendo HistorialDetalle y sumando puntos..."):
                df_revert = _safe_call(mdb["revertir_dns_gp"], gp_calc, PILOTOS_TORNEO,
                                       timeout_sec=60, default=pd.DataFrame([{"Error":"Timeout"}]))
            st.dataframe(df_revert, use_container_width=True)
            # Liberar el lock DNS para que se pueda volver a aplicar
            _safe_call(mdb["clear_lock"], dns_key, timeout_sec=10)
            st.success("✅ Puntos revertidos y lock DNS liberado. Revisá la tabla de posiciones.")
            st.rerun()
    else:
        st.warning("⚠️ Asegurate de haber revisado el preview antes de aplicar.")
        if st.button("⛔ APLICAR SANCIONES D.N.S. (−5 pts por etapa faltante)", use_container_width=True, key=f"btn_dns_{gp_calc}", type="primary"):
            df_d=mdb["aplicar_sanciones_dns"](gp_calc,PILOTOS_TORNEO,GPS_SPRINT)
            _safe_call(mdb["set_lock"],dns_key,timeout_sec=4)
            st.success("✅ Sanciones D.N.S. aplicadas correctamente.")
            st.dataframe(df_d, use_container_width=True)
    st.divider(); st.subheader("2) Preview de puntos (piloto individual)")
    pil_calc=st.selectbox("Piloto:",PILOTOS_TORNEO,key=f"pil_calc_{gp_calc}")
    with st.spinner("Leyendo predicciones de Google Sheets..."):
        res_pred=_safe_call(mdb["recuperar_predicciones_piloto"],pil_calc,gp_calc,
                            timeout_sec=30,default=(None,None,(None,None)))
    db_q,db_s,(db_r,db_c)=res_pred
    if db_q or db_r or db_s:
        st.success(f"✅ Predicciones de {pil_calc} encontradas.")
    else:
        st.warning(f"⚠️ {pil_calc} sin predicciones para {gp_calc}.")
        st.info("💡 Si creés que SÍ envió predicciones, usá el botón 🔎 Diagnóstico abajo para ver qué hay en la hoja.")

    # ── Diagnóstico RAW de predicciones ──────────────────────────────
    with st.expander("🔎 Diagnóstico: ver filas RAW en sheet1 para este GP"):
        st.caption("Muestra exactamente qué filas hay en Google Sheets para el GP seleccionado. "
                   "Si ves predicciones aquí pero no las detecta arriba, es un problema de nombres.")
        if st.button("🔍 Leer sheet1 ahora", key=f"raw_diag_{gp_calc}", use_container_width=True):
            with st.spinner("Leyendo Google Sheets directamente..."):
                raw = _safe_call(mdb["leer_predicciones_raw_gp"], gp_calc,
                                 timeout_sec=30, default=[{"error": "Timeout o error de conexión"}])
            if raw:
                import pandas as _pd_raw
                st.dataframe(_pd_raw.DataFrame(raw), use_container_width=True)
                st.caption(f"✅ Se encontraron {len(raw)} fila(s) — incluyendo el header.")
            else:
                st.warning("Sin filas encontradas para este GP en sheet1.")
    if st.button("CALCULAR PREVIEW",use_container_width=True,key=f"btn_calc_{gp_calc}_{pil_calc}"):
        vr=normalizar_keys_num(db_r or {}); vq=normalizar_keys_num(db_q or {})
        vc=normalizar_keys_num(db_c or {}); vs=normalizar_keys_num(db_s or {})
        of_r={i:oficial.get(f"r{i}","") for i in range(1,11)}
        of_q={i:oficial.get(f"q{i}","") for i in range(1,6)}
        of_c={i:oficial.get(f"c{i}","") for i in range(1,4)}
        of_s={i:oficial.get(f"s{i}","") for i in range(1,9)}
        cp=mcore["calcular_puntos"]
        pts_r=cp("CARRERA",vr,of_r,vr.get("colapinto_r"),oficial.get("col_r"))
        pts_q=cp("QUALY",  vq,of_q,vq.get("colapinto_q"),oficial.get("col_q"))
        pts_c=cp("CONSTRUCTORES",vc,of_c)
        pts_s=cp("SPRINT",vs,of_s) if (gp_calc in GPS_SPRINT and db_s) else 0
        total=pts_r+pts_q+pts_c+pts_s
        st.success(f"💰 PUNTOS TOTALES: **{total}**")
        st.info(f"Carrera({pts_r}) + Constructores({pts_c}) + Qualy({pts_q}) + Sprint({pts_s})")
        st.caption("⚠️ Solo preview — no guarda nada.")
    st.divider(); st.subheader("🏆 Bonus Campeones (Final temporada)")
    gp_final=next((g for g in GPS_OFICIALES if g.startswith("24.")),GPS_OFICIALES[-1])
    if gp_calc!=gp_final: st.info(f"Solo en: **{gp_final}**"); return
    if _safe_call(mdb["lock_exists"],f"CHAMP_DONE::{gp_final}",timeout_sec=4,default=False):
        st.warning("🔒 Bonus ya aplicado."); return
    pil_r=st.text_input("Piloto campeón:",key="rcp")
    con_r=st.text_input("Constructor campeón:",key="rcc")
    if st.button("✅ APLICAR BONUS (1 sola vez)",use_container_width=True,key="btn_champ"):
        ok,out=mdb["aplicar_bonus_campeones_final"](gp_final,pil_r,con_r,"01. Gran Premio de Australia",PILOTOS_TORNEO)
        (st.success("✅ Bonus aplicado.") or st.dataframe(out,use_container_width=True)) if ok else st.warning(out)


def pantalla_mesa_chica():
    m = _mod_mesa()
    if "_error" in m:
        st.error(f"⚠️ El Show del Paddock no disponible: {m['_error']}")
        return

    perfil = st.session_state.get("perfil") or {}
    usuario = perfil.get("usuario", "")
    if not usuario:
        st.warning("Tenés que iniciar sesión.")
        st.stop()

    is_mod = _mc_is_mod(usuario)

    if "mc_editing_id" not in st.session_state:
        st.session_state["mc_editing_id"] = None

    st.markdown("""
    <style>
    /* ── MESA CHICA MODERNA ─────────────────── */
    .mc-modern-header {
      background: linear-gradient(135deg,
        rgba(7,9,22,.98) 0%,
        rgba(13,18,42,.98) 50%,
        rgba(7,9,22,.98) 100%);
      border: 1px solid rgba(212,175,55,.35);
      border-radius: 20px;
      padding: 24px 20px 20px;
      text-align: center;
      position: relative;
      overflow: hidden;
      margin-bottom: 16px;
    }
    .mc-modern-header::before {
      content:'';position:absolute;top:0;left:0;right:0;height:2px;
      background: linear-gradient(90deg, transparent, #d4af37, #1565c0, #d4af37, transparent);
    }
    .mc-modern-header::after {
      content:'';position:absolute;bottom:0;left:0;right:0;height:1px;
      background: linear-gradient(90deg, transparent, rgba(212,175,55,.4), transparent);
    }
    .mc-header-f1tag {
      display:inline-flex;align-items:center;gap:6px;
      background:rgba(21,101,192,.25);border:1px solid rgba(21,101,192,.55);
      border-radius:20px;padding:3px 12px;font-size:10px;font-weight:800;
      letter-spacing:.14em;color:#90caf9;margin-bottom:12px;
    }
    .mc-header-title {
      font-size:24px;font-weight:900;letter-spacing:.08em;
      background:linear-gradient(90deg, #d4af37, #ffe896, #d4af37);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;
      background-clip:text;margin-bottom:6px;
    }
    .mc-header-sub {
      font-size:12px;color:rgba(232,236,255,.6);margin-bottom:14px;
    }
    .mc-header-pills {
      display:flex;flex-wrap:wrap;justify-content:center;gap:6px;
    }
    .mc-header-pill {
      background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);
      border-radius:20px;padding:4px 12px;font-size:10px;color:rgba(232,236,255,.7);
      font-weight:600;
    }
    /* Message bubbles — modern chat style */
    .mc-chat-feed { display:flex;flex-direction:column;gap:8px;padding:4px 0; }
    .mc-bubble {
      max-width:68%;display:block;
      animation:fadeIn .2s ease;
    }
    .mc-bubble.mc-left { align-self:flex-start; }
    .mc-bubble.mc-right { align-self:flex-end; }
    .mc-bubble-inner {
      padding:9px 13px 8px;border-radius:16px;position:relative;
      word-break:break-word;line-height:1.55;font-size:13px;
      width:100%;box-sizing:border-box;
    }
    .mc-left .mc-bubble-inner {
      background:linear-gradient(135deg,rgba(21,101,192,.18),rgba(8,12,30,.97));
      border:1px solid rgba(100,180,255,.35);border-bottom-left-radius:4px;
      box-shadow:0 2px 10px rgba(21,101,192,.12);
    }
    .mc-right .mc-bubble-inner {
      background:linear-gradient(135deg,rgba(90,30,180,.18),rgba(8,12,30,.97));
      border:1px solid rgba(180,100,255,.3);border-bottom-right-radius:4px;
      box-shadow:0 2px 10px rgba(123,47,247,.10);
    }
    .mc-bubble-name {
      font-size:10px;font-weight:900;letter-spacing:.04em;margin-bottom:3px;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .mc-bubble-text { color:rgba(232,236,255,.9);font-size:13px; }
    .mc-bubble-time {
      font-size:9px;opacity:.38;letter-spacing:.03em;margin-top:5px;
      text-align:right;
    }
    @keyframes fadeIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
    /* Form button override */
    div[data-testid="stForm"] button[kind="primary"] {
      background: linear-gradient(90deg, #9a7a10, #d4af37, #9a7a10) !important;
      border: 1px solid rgba(255,238,150,.6) !important;
      color: #1a1000 !important;
      font-weight: 900 !important;
      border-radius: 12px !important;
      letter-spacing: .07em;
      box-shadow: 0 0 14px rgba(212,175,55,.25) !important;
    }
    div[data-testid="stForm"] button[kind="primary"]:hover {
      background: linear-gradient(90deg, #d4af37, #ffe896, #d4af37) !important;
      box-shadow: 0 0 22px rgba(212,175,55,.45) !important;
    }
    </style>
    <div class="mc-modern-header">
      <div class="mc-header-f1tag">
        <span style="width:8px;height:8px;border-radius:50%;
          background:#1565c0;display:inline-block;"></span>
        F1 · TEMPORADA 2026
        <span style="width:8px;height:8px;border-radius:50%;
          background:#d4af37;display:inline-block;"></span>
      </div>
      <div class="mc-header-title">EL SHOW DEL PADDOCK F1</div>
      <div class="mc-header-sub">📰 Noticias y novedades del torneo &nbsp;·&nbsp; <b style="color:rgba(232,236,255,.8);">Solo el Comisario y Sub Comisario pueden publicar</b></div>
      <div class="mc-header-pills">
        <span class="mc-header-pill">🏎️ Temporada 2026</span>
        <span class="mc-header-pill">📰 Noticias oficiales</span>
        <span class="mc-header-pill">🏁 24 GPs</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Noticias only (chat moved to Formuleros)

    # ════════════ TAB NOTICIAS ════════════
    if True:  # Noticias section
        _can_pub = "news_can_publish" in m and m["news_can_publish"](usuario)
        st.markdown("""<style>
        .news-card{background:linear-gradient(145deg,rgba(7,9,22,.99),rgba(14,18,42,.99));
          border:1.5px solid rgba(212,175,55,.3);border-radius:18px;
          overflow:hidden;margin-bottom:22px;}
        .news-card:hover{border-color:rgba(212,175,55,.6);}
        .news-banner{width:100%;max-height:340px;object-fit:cover;display:block;}
        .news-body{padding:16px 20px 14px;}
        .news-tag{display:inline-flex;align-items:center;gap:5px;
          background:rgba(212,175,55,.15);border:1px solid rgba(212,175,55,.4);
          border-radius:20px;padding:2px 10px;font-size:9px;font-weight:800;
          letter-spacing:.12em;color:#ffdd7a;margin-bottom:8px;}
        .news-title{font-size:20px;font-weight:900;color:#ffdd7a;line-height:1.25;margin-bottom:6px;}
        .news-meta{font-size:10px;color:rgba(169,178,214,.45);margin-bottom:10px;}
        .news-text{font-size:13px;color:rgba(232,236,255,.85);line-height:1.65;}
        .news-divider{height:1px;background:linear-gradient(90deg,transparent,rgba(212,175,55,.2),transparent);margin:6px 0 12px;}
        </style>""", unsafe_allow_html=True)
        if _can_pub:
            with st.expander("➕ Publicar nueva noticia", expanded=False):
                _nt  = st.text_input("📰 Título *", key="news_titulo", placeholder="Ej: Verstappen gana en Miami")
                _nc  = st.text_area("✍️ Cuerpo (opcional)", key="news_cuerpo", height=90,
                                    placeholder="Desarrollo de la noticia…")
                st.markdown("**🖼️ Imagen (elegí una opción):**")
                _img_mode = st.radio("Modo imagen:", ["🔗 URL directa", "📁 Subir archivo"],
                                     horizontal=True, key="news_img_mode", label_visibility="collapsed")
                _ni = ""
                if _img_mode == "🔗 URL directa":
                    _ni = st.text_input("URL de imagen", key="news_img_url",
                                        placeholder="https://i.imgur.com/XXXXX.jpg  (link directo)")
                    st.caption("💡 En imgbb.com: subí → copiá el 'Direct link'. En imgur: usá i.imgur.com/XXXXX.jpg")
                else:
                    _uploaded_img = st.file_uploader("Subir imagen", type=["jpg","jpeg","png","webp"],
                                                     key="news_img_upload")
                    if _uploaded_img is not None:
                        import base64 as _b64_news, io as _io_news
                        _img_bytes = _uploaded_img.read()
                        _img_mime  = "image/jpeg"
                        # Auto-redimensionar/comprimir para que entre y cargue rápido
                        try:
                            from PIL import Image as _PILImg
                            _im = _PILImg.open(_io_news.BytesIO(_img_bytes))
                            if _im.mode in ("RGBA","P","LA"):
                                _im = _im.convert("RGB")
                            _im.thumbnail((1000, 1000))
                            _buf = _io_news.BytesIO()
                            _q = 80
                            _im.save(_buf, format="JPEG", quality=_q, optimize=True)
                            # bajar calidad si sigue muy pesada
                            while _buf.tell() > 350_000 and _q > 35:
                                _q -= 10; _buf = _io_news.BytesIO()
                                _im.save(_buf, format="JPEG", quality=_q, optimize=True)
                            _img_bytes = _buf.getvalue()
                        except Exception:
                            pass  # Sin PIL: usar bytes originales
                        _ni = f"data:{_img_mime};base64,{_b64_news.b64encode(_img_bytes).decode()}"
                        st.image(_img_bytes, caption="Preview", use_container_width=True)
                        st.success(f"✅ Imagen lista ({len(_img_bytes)//1024} KB tras optimizar)")
                        st.warning("⚠️ Las imágenes SUBIDAS no se guardan al reiniciar la app (límite de Google Sheets). "
                                   "Para que queden PERMANENTES, usá '🔗 URL directa' con imgbb.com (gratis): "
                                   "subí la foto ahí, copiá el 'Direct link' y pegalo. Solo así se ve siempre.")
                if st.button("📤 Publicar noticia", key="news_pub_btn", use_container_width=True):
                    if not _nt.strip():
                        st.error("El título es obligatorio.")
                    else:
                        try:
                            m["news_add"](usuario, _nt.strip(), _nc.strip(), (_ni or "").strip())
                            st.success("✅ Noticia publicada."); st.rerun()
                        except Exception as _ne: st.error(str(_ne))
        try:
            _noticias = m["news_list"](limit=50) if "news_list" in m else []
        except Exception: _noticias = []

        _REAC_EMOJIS = ["👍","👎","👏"]

        if not _noticias:
            st.markdown('<div style="text-align:center;padding:40px 0;color:rgba(169,178,214,.38);">'
                        '<div style="font-size:42px;">📰</div>'
                        '<div style="font-size:13px;margin-top:8px;">Sin noticias todavía.</div>'
                        '</div>', unsafe_allow_html=True)
        else:
            import html as _html2, re as _re2

            def _fix_img(url):
                if not url: return ""
                url = url.strip()
                if url.startswith("data:image/"): return url
                # imgur álbum → no podemos obtener imagen directa, retornar igual para que el browser intente
                m2 = _re2.match(r'https?://(?:www\.)?imgur\.com/(?:a|gallery)/([A-Za-z0-9]+)', url)
                if m2: return url  # dejarlo pasar, el browser puede que lo cargue
                # imgur sin extensión → agregar .jpg
                m3 = _re2.match(r'https?://(?:www\.)?imgur\.com/([A-Za-z0-9]+)$', url)
                if m3: return f"https://i.imgur.com/{m3.group(1)}.jpg"
                # i.imgur.com ya directo
                if "i.imgur.com" in url: return url
                # imgbb direct link
                if "ibb.co" in url or "i.ibb.co" in url: return url
                # cualquier URL https que parezca imagen
                if url.startswith("http"): return url
                return url

            for _nid, _nautor, _ntit, _nimg, _ncuerpo, _nts in _noticias:
                with st.container():
                    try: _nd_str = __import__("datetime").datetime.fromisoformat(_nts).strftime("%d/%m/%Y · %H:%M")
                    except Exception: _nd_str = str(_nts)[:16]
                    _nbadge = "🏆 Comisario" if _nautor == "Checo Perez" else "🥈 Sub Comisario"
                    _img_fixed = _fix_img(_nimg)
                    _img_src = _img_fixed if _img_fixed.startswith("data:image/") else _html2.escape(_img_fixed)
                    _img_html = (f'<img src="{_img_src}" class="news-banner" '
                                 f'onerror="this.style.display=\'none\'" loading="lazy">' if _img_fixed else "")
                    # Detectar si es un link de álbum imgur (no funciona como imagen)
                    import re as _re_img_w
                    _is_imgur_album = bool(_nimg and _re_img_w.search(r'imgur\.com/(?:a|gallery)/', str(_nimg)))
                    _img_warn = ""
                    if _is_imgur_album:
                        _img_warn = (f'<div style="background:rgba(239,68,68,.12);border:1px solid rgba(239,68,68,.4);'
                                     f'border-radius:8px;padding:8px 12px;font-size:11px;color:#fca5a5;margin-bottom:8px;">'
                                     f'⚠️ <b>Link de álbum imgur no funciona como imagen.</b> '
                                     f'Usá imgbb.com → subí → copiá el "Direct link" (termina en .jpg) '
                                     f'o en imgur usá i.imgur.com/XXXXX.jpg</div>')
                    elif _nimg and not _img_fixed:
                        _img_warn = (f'<div style="background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.3);'
                                     f'border-radius:8px;padding:6px 10px;font-size:11px;color:#fbbf24;margin-bottom:6px;">'
                                     f'⚠️ Usá link directo (i.imgur.com/XXXXX.jpg)</div>')
                    _body_html = (f'<div class="news-divider"></div>'
                                  f'<div class="news-text">{_html2.escape(_ncuerpo).replace(chr(10),"<br>")}</div>'
                                  if _ncuerpo else "")
                    st.markdown(
                        f'<div class="news-card">{_img_html}'
                        f'<div class="news-body">{_img_warn}'
                        f'<div class="news-tag">📰 EL SHOW DEL PADDOCK F1</div>'
                        f'<div class="news-title">{_html2.escape(_ntit)}</div>'
                        f'<div class="news-meta">{_nbadge} · {_nautor} · {_nd_str}</div>'
                        f'{_body_html}</div></div>', unsafe_allow_html=True)

                # ── Reacciones ──────────────────────────────────────────
                _reacs  = m.get("news_get_reacciones",    lambda x: {})(_nid) or {}
                _myreac = m.get("news_user_reacciones", lambda x,y: set())(_nid, usuario) or set()
                _total_reac = sum(_reacs.values())
                # Botones de reacción compactos — no ocupan toda la fila
                st.markdown('<style>.fw-reac-row [data-testid="stHorizontalBlock"]{gap:6px;}</style>', unsafe_allow_html=True)
                _n_reac = len(_REAC_EMOJIS)
                # Columnas chicas para los emojis + un gran spacer a la derecha
                _ratios = [1]*_n_reac + ([1] if _can_pub else []) + [6]
                _rcols = st.columns(_ratios)
                for _ri, _em in enumerate(_REAC_EMOJIS):
                    _cnt_r = _reacs.get(_em, 0)
                    _lbl_r = f"{_em} {_cnt_r}" if _cnt_r else _em
                    with _rcols[_ri]:
                        if st.button(_lbl_r, key=f"nr_{_nid}_{_ri}", use_container_width=True):
                            if "news_toggle_reaccion" in m:
                                m["news_toggle_reaccion"](_nid, usuario, _em); st.rerun()
                if _can_pub:
                    with _rcols[_n_reac]:
                        if st.button("🗑️", key=f"news_del_{_nid}", use_container_width=True, help="Eliminar"):
                            m["news_delete"](_nid, deleted_by=usuario); st.rerun()

                # ── Editar (editores) ────────────────────────────────────
                if _can_pub:
                    _ekey = f"news_edit_{_nid}"
                    if st.button("✏️ Editar noticia", key=f"news_edit_btn_{_nid}"):
                        st.session_state[_ekey] = not st.session_state.get(_ekey, False); st.rerun()
                    if st.session_state.get(_ekey, False):
                        _et2 = st.text_input("Título", value=_ntit, key=f"net_{_nid}")
                        _ec2 = st.text_area("Cuerpo", value=_ncuerpo or "", key=f"nec_{_nid}", height=70)
                        _ei_mode = st.radio("Imagen:", ["🔗 URL","📁 Subir archivo","Sin cambios"],
                                            horizontal=True, key=f"neimode_{_nid}", index=2,
                                            label_visibility="collapsed")
                        _ei2 = _nimg or ""
                        if _ei_mode == "🔗 URL":
                            _ei2 = st.text_input("URL imagen", value=_nimg or "", key=f"nei_{_nid}").strip()
                        elif _ei_mode == "📁 Subir archivo":
                            _eup = st.file_uploader("Subir imagen", type=["jpg","jpeg","png","webp"], key=f"neup_{_nid}")
                            if _eup is not None:
                                import base64 as _b64_ne, io as _io_ne
                                _rb = _eup.read()
                                try:
                                    from PIL import Image as _PILne
                                    _imn = _PILne.open(_io_ne.BytesIO(_rb))
                                    if _imn.mode in ("RGBA","P","LA"): _imn = _imn.convert("RGB")
                                    _imn.thumbnail((1000,1000))
                                    _bfn = _io_ne.BytesIO(); _qn=80
                                    _imn.save(_bfn, format="JPEG", quality=_qn, optimize=True)
                                    while _bfn.tell() > 350_000 and _qn > 35:
                                        _qn -= 10; _bfn = _io_ne.BytesIO()
                                        _imn.save(_bfn, format="JPEG", quality=_qn, optimize=True)
                                    _rb = _bfn.getvalue()
                                except Exception: pass
                                _ei2 = f"data:image/jpeg;base64,{_b64_ne.b64encode(_rb).decode()}"
                                st.image(_rb, caption=f"Preview ({len(_rb)//1024} KB)", width=200)
                        if st.button("💾 Guardar", key=f"nsave_{_nid}", use_container_width=True):
                            m["news_update"](_nid, _et2, _ec2, _ei2)
                            st.session_state[_ekey] = False; st.rerun()

                # ── Comentarios ─────────────────────────────────────────
                _coms = m.get("news_get_comentarios", lambda x: [])(_nid) or []
                with st.expander(f"💬 {len(_coms)} comentario{'s' if len(_coms)!=1 else ''}"):
                    for _cid, _caut, _ctxt, _cts in _coms:
                        try: _cdstr = __import__("datetime").datetime.fromisoformat(_cts).strftime("%d/%m %H:%M")
                        except Exception: _cdstr = str(_cts)[:16]
                        _cclr = PILOTO_COLORS.get(_caut, "#a855f7")
                        _cph  = DRIVER_HEADSHOTS.get(_caut, DRIVER_PHOTOS.get(_caut,""))
                        _cav  = (f'<img src="{_cph}" style="width:24px;height:24px;border-radius:50%;'
                                 f'object-fit:cover;object-position:top center;border:1.5px solid {_cclr};">'
                                 if _cph else
                                 f'<div style="width:24px;height:24px;border-radius:50%;background:{_cclr}22;'
                                 f'border:1px solid {_cclr};display:flex;align-items:center;justify-content:center;'
                                 f'font-size:8px;font-weight:900;color:{_cclr};">{_caut[:2].upper()}</div>')
                        st.markdown(
                            f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;'
                            f'padding:8px 10px;background:rgba(255,255,255,.03);border-radius:10px;">'
                            f'{_cav}<div style="flex:1;">'
                            f'<div style="font-size:10px;font-weight:800;color:{_cclr};">{_html2.escape(_caut)}'
                            f'<span style="font-weight:400;color:rgba(169,178,214,.4);"> · {_cdstr}</span></div>'
                            f'<div style="font-size:12px;color:rgba(232,236,255,.85);margin-top:2px;">'
                            f'{_html2.escape(_ctxt)}</div></div></div>', unsafe_allow_html=True)
                        if _can_pub or _caut == usuario:
                            if st.button("🗑️", key=f"nc_del_{_cid}", help="Borrar comentario"):
                                m["news_delete_comentario"](_cid); st.rerun()
                    _com_txt = st.text_input("✍️ Comentar (máx 200 caracteres)", max_chars=200,
                                             key=f"nc_inp_{_nid}", placeholder="Tu comentario…",
                                             label_visibility="collapsed")
                    if st.button("📤 Comentar", key=f"nc_btn_{_nid}", use_container_width=True):
                        if _com_txt.strip():
                            m["news_add_comentario"](_nid, usuario, _com_txt.strip()); st.rerun()
                        else:
                            st.warning("Escribí algo antes de comentar.")

                st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

def pantalla_head_to_head():
    for k in ["h2h_a","h2h_b"]:
        if k not in st.session_state: st.session_state[k]=None
    pa=st.session_state["h2h_a"]; pb=st.session_state["h2h_b"]

    import time as _time_h2h

    # ── Historial — cache en session_state (TTL 600s) ────────────────
    _H2H_HIST_KEY = "_h2h_hist_data"
    _H2H_HIST_TS  = "_h2h_hist_ts"
    if (_H2H_HIST_KEY not in st.session_state or
            _time_h2h.time() - st.session_state.get(_H2H_HIST_TS, 0) > 600):
        _m_h2h = _mod_db()
        if "_error" not in _m_h2h:
            _h2h_raw = _safe_call(_m_h2h["leer_historial_df"], timeout_sec=15, default=pd.DataFrame())
        else:
            _h2h_raw = pd.DataFrame()
        st.session_state[_H2H_HIST_KEY] = _h2h_raw
        st.session_state[_H2H_HIST_TS]  = _time_h2h.time()
    _h2h_df_h = st.session_state.get(_H2H_HIST_KEY, pd.DataFrame())
    _h2h_df_d = pd.DataFrame()  # detalle no se usa en H2H

    st.markdown("""<style>
    @keyframes h2hG{0%,100%{box-shadow:0 0 24px rgba(212,175,55,.13);}
      50%{box-shadow:0 0 46px rgba(212,175,55,.26);}}
    .h2h-hero{background:linear-gradient(145deg,rgba(7,9,22,.99),rgba(13,17,42,.99));
      border:1.5px solid rgba(212,175,55,.45);border-radius:20px;
      padding:20px 18px 16px;text-align:center;margin-bottom:12px;
      animation:h2hG 3.5s ease-in-out infinite;position:relative;overflow:hidden;}
    .h2h-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
      background:linear-gradient(90deg,transparent,#d4af37,rgba(255,220,100,.9),#d4af37,transparent);}
    .h2h-t{font-size:28px;font-weight:900;letter-spacing:.1em;
      background:linear-gradient(90deg,#d4af37,#ffe896,#d4af37);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
    .h2h-sub{font-size:10px;color:rgba(169,178,214,.5);margin-top:3px;letter-spacing:.07em;}
    .h2h-stat{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);
      border-radius:10px;padding:8px 13px;margin-bottom:6px;}
    .h2h-sl{font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
      color:rgba(246,195,73,.5);text-align:center;margin-bottom:5px;}
    div[data-testid="stHorizontalBlock"] .h2hbw{
      position:relative;margin-top:-82px;height:82px;z-index:5;}
    div[data-testid="stHorizontalBlock"] .h2hbw>button{
      position:absolute!important;top:0!important;left:0!important;
      width:100%!important;height:82px!important;
      background:transparent!important;border:none!important;
      box-shadow:none!important;opacity:0!important;
      cursor:pointer!important;z-index:10!important;
      padding:0!important;min-height:0!important;font-size:1px!important;color:transparent!important;}
    </style>""", unsafe_allow_html=True)

    st.markdown('<div class="h2h-hero"><div style="font-size:26px;margin-bottom:3px;">⚔️</div>'
                '<div class="h2h-t">HEAD TO HEAD</div>'
                '<div class="h2h-sub">Seleccioná dos participantes para comparar</div></div>',
                unsafe_allow_html=True)

    cols=st.columns(len(PILOTOS_TORNEO))
    for idx,pil in enumerate(PILOTOS_TORNEO):
        with cols[idx]:
            clr=PILOTO_COLORS.get(pil,"#a855f7")
            ph=DRIVER_HEADSHOTS.get(pil,DRIVER_PHOTOS.get(pil,""))
            ini="".join(w[0] for w in pil.split()[:2]).upper()
            is_a=(pa==pil);is_b=(pb==pil)
            bc="#ffdd7a" if is_a else("#3b82f6" if is_b else "rgba(255,255,255,.2)")
            bw="3px" if(is_a or is_b) else "1.5px"
            shd=f"box-shadow:0 0 14px {clr}55;" if(is_a or is_b) else ""
            tag=(f'<div style="position:absolute;top:-2px;right:calc(50% - 32px);width:16px;height:16px;'
                 f'border-radius:50%;background:{"#ffdd7a" if is_a else "#3b82f6"};color:#000;'
                 f'font-size:9px;font-weight:900;display:flex;align-items:center;justify-content:center;'
                 f'z-index:5;">{"A" if is_a else "B"}</div>') if(is_a or is_b) else ""
            if ph:
                img=(f'<img src="{ph}" style="width:58px;height:58px;border-radius:50%;'
                     f'object-fit:cover;object-position:top;border:{bw} solid {bc};'
                     f'{shd}display:block;margin:0 auto 4px;">')
            else:
                img=(f'<div style="width:58px;height:58px;border-radius:50%;background:{clr}22;'
                     f'border:{bw} solid {bc};{shd}display:flex;align-items:center;justify-content:center;'
                     f'font-weight:900;font-size:15px;color:{clr};margin:0 auto 4px;">{ini}</div>')
            st.markdown(f'<div style="text-align:center;position:relative;">{tag}{img}'
                        f'<div style="font-size:9px;font-weight:800;color:{clr};'
                        f'letter-spacing:.05em;text-transform:uppercase;">{pil.split()[0]}</div></div>',
                        unsafe_allow_html=True)
            if st.button(pil.split()[0], key=f"h2h_{idx}", use_container_width=True, help=f"Sel. {pil}"):
                if pa==pil: st.session_state["h2h_a"]=pb; st.session_state["h2h_b"]=None
                elif pb==pil: st.session_state["h2h_b"]=None
                elif pa is None: st.session_state["h2h_a"]=pil
                else: st.session_state["h2h_b"]=pil
                st.rerun()

    pa=st.session_state["h2h_a"]; pb=st.session_state["h2h_b"]
    if not pa or not pb or pa==pb:
        st.markdown('<div style="text-align:center;padding:26px 0;color:rgba(169,178,214,.38);'
                    'font-size:13px;">Seleccioná dos participantes distintos.</div>', unsafe_allow_html=True)
        return

    # Tabla de posiciones — cacheada en session_state para no re-leer Sheets en cada render
    _h2h_tabla_key = "_h2h_tabla_cache"
    if _h2h_tabla_key not in st.session_state or st.session_state.get("_h2h_tabla_ts",0) < (__import__("time").time() - 300):
        _m2_h2 = _mod_db()
        _dft_raw = _safe_call(_m2_h2["leer_tabla_posiciones"], PILOTOS_TORNEO, timeout_sec=8, default=None) if "_error" not in _m2_h2 else None
        st.session_state[_h2h_tabla_key] = _dft_raw
        st.session_state["_h2h_tabla_ts"] = __import__("time").time()
    dft = st.session_state.get(_h2h_tabla_key)
    if dft is None or (hasattr(dft,"empty") and dft.empty):
        _np5 = len(PILOTOS_TORNEO)
        dft=pd.DataFrame({"Piloto":PILOTOS_TORNEO,"Puntos":[0]*_np5,"Qualys":[0]*_np5,"Sprints":[0]*_np5,"Carreras":[0]*_np5})
    def _rv(n,c):
        if not(hasattr(dft,"empty") and dft.empty):
            r=dft[dft["Piloto"]==n]
            if not r.empty: return int(r.iloc[0].get(c,0) or 0)
        return 0
    ca=PILOTO_COLORS.get(pa,"#a855f7"); cb=PILOTO_COLORS.get(pb,"#3b82f6")
    ph_a=DRIVER_HEADSHOTS.get(pa,DRIVER_PHOTOS.get(pa,"")); ph_b=DRIVER_HEADSHOTS.get(pb,DRIVER_PHOTOS.get(pb,""))
    ini_a="".join(w[0] for w in pa.split()[:2]).upper(); ini_b="".join(w[0] for w in pb.split()[:2]).upper()
    pts_a=_rv(pa,"Puntos"); pts_b=_rv(pb,"Puntos")
    qua_a=_rv(pa,"Qualys"); qua_b=_rv(pb,"Qualys")
    spr_a=_rv(pa,"Sprints"); spr_b=_rv(pb,"Sprints")
    car_a=_rv(pa,"Carreras"); car_b=_rv(pb,"Carreras")
    # ── GPs ganados: usar el historial ya cargado arriba (evita segunda lectura de Sheets) ──
    _df_h2 = _h2h_df_h  # ya cargado con cache TTL=600 en _h2h_load_hist()
    gps_a = 0; gps_b = 0
    if _df_h2 is not None and not (hasattr(_df_h2,"empty") and _df_h2.empty):
        try:
            _dh2c = _df_h2.copy(); _dh2c.columns=[c.lower().strip() for c in _dh2c.columns]
            _dh2c["puntos"]=pd.to_numeric(_dh2c["puntos"],errors="coerce").fillna(0).astype(int)
            _dh2c=_dh2c.groupby(["gp","piloto"],as_index=False)["puntos"].sum()
            for _gp2,_grp2 in _dh2c.groupby("gp"):
                _gs2=_grp2.sort_values("puntos",ascending=False)
                if _gs2.empty: continue
                _w2=_gs2.iloc[0]["piloto"]
                if _w2==pa: gps_a+=1
                elif _w2==pb: gps_b+=1
        except Exception: pass
    win=(pa if pts_a>pts_b else(pb if pts_b>pts_a else None))

    def _av(ph,ini,clr,sz=76):
        if ph:return(f'<img src="{ph}" style="width:{sz}px;height:{sz}px;border-radius:50%;'
                     f'object-fit:cover;object-position:top;border:3px solid {clr};'
                     f'margin:0 auto 6px;display:block;box-shadow:0 0 12px {clr}44;">')
        return(f'<div style="width:{sz}px;height:{sz}px;border-radius:50%;background:{clr}22;'
               f'border:3px solid {clr};display:flex;align-items:center;justify-content:center;'
               f'font-weight:900;font-size:{sz//4}px;color:{clr};margin:0 auto 6px;">{ini}</div>')

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    c1,cV,c2=st.columns([5,1,5])
    def _pc(col,name,ph,ini,clr,pts,isw):
        ldr=(f'<div style="margin-top:5px;"><span style="background:{clr}33;color:{clr};'
             f'border-radius:20px;padding:3px 10px;font-size:10px;font-weight:900;">👑 LIDERA</span></div>'
             ) if isw else ""
        col.markdown(
            f'<div style="background:{clr}0d;border:1.5px solid {clr}44;border-radius:16px;'
            f'padding:16px 12px;text-align:center;">{_av(ph,ini,clr)}'
            f'<div style="font-weight:900;font-size:14px;color:{clr};">{name}</div>'
            f'<div style="font-size:32px;font-weight:900;color:#ffdd7a;margin:4px 0;">{pts}</div>'
            f'<div style="font-size:9px;color:rgba(232,236,255,.4);letter-spacing:.1em;'
            f'text-transform:uppercase;">PUNTOS TOTALES</div>{ldr}</div>', unsafe_allow_html=True)
    _pc(c1,pa,ph_a,ini_a,ca,pts_a,win==pa)
    cV.markdown('<div style="display:flex;align-items:center;justify-content:center;height:100%;padding:8px 0;">'
                '<div style="width:42px;height:42px;border-radius:50%;background:linear-gradient(145deg,#d4af37,#9a7a10);'
                'display:flex;align-items:center;justify-content:center;font-weight:900;font-size:13px;color:#1a1000;'
                'box-shadow:0 0 14px rgba(212,175,55,.35);">VS</div></div>', unsafe_allow_html=True)
    _pc(c2,pb,ph_b,ini_b,cb,pts_b,win==pb)

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
    st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:.14em;'
                'color:rgba(246,195,73,.65);text-transform:uppercase;margin-bottom:6px;">📊 Estadísticas</div>',
                unsafe_allow_html=True)
    def _sb(lbl,va,vb):
        t=max(va+vb,1);pa2=va/t*100;pb2=vb/t*100
        wa="font-weight:900;" if va>vb else"";wb="font-weight:900;" if vb>va else""
        return(f'<div class="h2h-stat"><div class="h2h-sl">{lbl}</div>'
               f'<div style="display:flex;align-items:center;gap:8px;">'
               f'<div style="min-width:32px;text-align:right;font-size:13px;{wa}color:{ca};">{va}</div>'
               f'<div style="flex:1;display:flex;height:9px;border-radius:4px;overflow:hidden;gap:1px;">'
               f'<div style="width:{pa2:.0f}%;background:{ca};border-radius:3px 0 0 3px;box-shadow:0 0 5px {ca}55;"></div>'
               f'<div style="width:{pb2:.0f}%;background:{cb};border-radius:0 3px 3px 0;box-shadow:0 0 5px {cb}55;"></div>'
               f'</div><div style="min-width:32px;font-size:13px;{wb}color:{cb};">{vb}</div>'
               f'</div></div>')
    st.markdown(
        _sb("🏆 Puntos Totales",pts_a,pts_b)+_sb("⏱️ Qualys ganadas",qua_a,qua_b)+
        _sb("⚡ Sprints ganados",spr_a,spr_b)+_sb("🏁 Carreras ganadas",car_a,car_b)+
        _sb("🏆 GPs ganados (total pts)",gps_a,gps_b), unsafe_allow_html=True)

    if _PLOTLY_OK:
        try:
            import plotly.graph_objects as _go
            # Sin "Total" — la barra de puntos totales aplasta las categorías y encima los textos
            cats=["Qualys","Sprints","Carreras"]
            fig=_go.Figure()
            fig.add_trace(_go.Bar(name=pa,x=cats,y=[qua_a,spr_a,car_a],marker_color=ca,
                marker_line_width=0,text=[qua_a,spr_a,car_a],textposition="outside",
                textfont=dict(color=ca,size=12),cliponaxis=False))
            fig.add_trace(_go.Bar(name=pb,x=cats,y=[qua_b,spr_b,car_b],marker_color=cb,
                marker_line_width=0,text=[qua_b,spr_b,car_b],textposition="outside",
                textfont=dict(color=cb,size=12),cliponaxis=False))
            ymax=max(qua_a,qua_b,spr_a,spr_b,car_a,car_b,1)*1.45
            fig.update_layout(height=260,barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=6,r=6,t=42,b=10),
                title=dict(text="📊 Victorias por categoría",font=dict(color="#ffdd7a",size=13),x=0),
                legend=dict(font=dict(color="#e8ecff",size=11),bgcolor="rgba(0,0,0,0)",orientation="h",y=1.18,x=0),
                xaxis=dict(tickfont=dict(color="#e8ecff",size=12),showgrid=False),
                yaxis=dict(tickfont=dict(color="#a9b2d6",size=10),gridcolor="rgba(255,255,255,.04)",
                           zeroline=False,range=[0,ymax],dtick=1))
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"staticPlot":True})
            # Puntos totales aparte (texto, no barra) para no aplastar
            st.markdown(
                f'<div style="display:flex;justify-content:center;gap:24px;margin:4px 0 10px;">'
                f'<div style="text-align:center;"><div style="font-size:10px;color:{ca};font-weight:800;">{pa.split()[0]}</div>'
                f'<div style="font-size:20px;font-weight:900;color:{ca};">{pts_a}</div>'
                f'<div style="font-size:8px;color:rgba(169,178,214,.5);">PTS TOTALES</div></div>'
                f'<div style="text-align:center;"><div style="font-size:10px;color:{cb};font-weight:800;">{pb.split()[0]}</div>'
                f'<div style="font-size:20px;font-weight:900;color:{cb};">{pts_b}</div>'
                f'<div style="font-size:8px;color:rgba(169,178,214,.5);">PTS TOTALES</div></div>'
                f'</div>', unsafe_allow_html=True)
        except Exception: pass

    # ── Radar chart (spider) de categorías ──────────────────────────
    if _PLOTLY_OK and qua_a+qua_b+car_a+car_b > 0:
        try:
            import plotly.graph_objects as _gor
            _cats_r = ["Qualy","Sprint","Carrera","Const","Total"]
            _max_r  = max(qua_a,qua_b,spr_a,spr_b,car_a,car_b,pts_a,pts_b,1)
            def _norm(v): return round(v/_max_r*100,1)
            _va = [_norm(qua_a),_norm(spr_a),_norm(car_a),_norm(pts_a-qua_a-spr_a-car_a),_norm(pts_a)]
            _vb = [_norm(qua_b),_norm(spr_b),_norm(car_b),_norm(pts_b-qua_b-spr_b-car_b),_norm(pts_b)]
            _fig_r = _gor.Figure()
            _fig_r.add_trace(_gor.Scatterpolar(r=_va+[_va[0]],theta=_cats_r+[_cats_r[0]],
                fill="toself",name=pa,line_color=ca,fillcolor=ca.replace("#","rgba(")+"22)" if ca.startswith("#") else ca))
            _fig_r.add_trace(_gor.Scatterpolar(r=_vb+[_vb[0]],theta=_cats_r+[_cats_r[0]],
                fill="toself",name=pb,line_color=cb,fillcolor=cb.replace("#","rgba(")+"22)" if cb.startswith("#") else cb))
            _fig_r.update_layout(height=280,
                polar=dict(radialaxis=dict(visible=True,range=[0,100],
                    gridcolor="rgba(255,255,255,.1)",tickfont=dict(color="rgba(169,178,214,.5)",size=8)),
                    angularaxis=dict(tickfont=dict(color="#e8ecff",size=11),linecolor="rgba(255,255,255,.1)")),
                paper_bgcolor="rgba(0,0,0,0)",margin=dict(l=20,r=20,t=40,b=20),
                legend=dict(font=dict(color="#e8ecff",size=11),bgcolor="rgba(0,0,0,0)",
                            orientation="h",y=1.1,x=0.5,xanchor="center"),
                title=dict(text="🕸️ Radar — Rendimiento por categoría",font=dict(color="#ffdd7a",size=12),x=0))
            st.plotly_chart(_fig_r,use_container_width=True,config={"displayModeBar":False,"staticPlot":True})
        except Exception: pass
    # ── Desafíos Directos entre estos 2 pilotos ──────────────────────
    try:
        # Cache desafíos en session_state (TTL 120s) — evita redefinir @st.cache_data en cada render
        _H2H_DES_KEY = "_h2h_desafios_data"
        _H2H_DES_TS  = "_h2h_desafios_ts"
        if (_H2H_DES_KEY not in st.session_state or
                _time_h2h.time() - st.session_state.get(_H2H_DES_TS, 0) > 120):
            try:
                from core.database import conectar_google_sheets as _cgs_h2d
                _ws_h2 = _cgs_h2d("Desafios")
                if not _ws_h2:
                    _des_raw = []
                else:
                    try:
                        _des_raw = _ws_h2.get_all_records(expected_headers=["id","retador","rival","gp","estado","pts_retador","pts_rival","ganador","ts_creado","ts_resuelto"])
                    except Exception:
                        _v = _ws_h2.get_all_values()
                        if not _v or len(_v)<2:
                            _des_raw = []
                        else:
                            _h2=[h.strip().lower() for h in _v[0]]
                            def _fi2(n):
                                for _i,_hh in enumerate(_h2):
                                    if _hh==n: return _i
                                return None
                            _map2 = {n:_fi2(n) for n in ["id","retador","rival","gp","estado","pts_retador","pts_rival","ganador","ts_creado","ts_resuelto"]}
                            _des_raw=[]
                            for _rr in _v[1:]:
                                if not any(c.strip() for c in _rr): continue
                                _des_raw.append({k: (_rr[i].strip() if i is not None and i<len(_rr) else "") for k,i in _map2.items()})
            except Exception:
                _des_raw = []
            st.session_state[_H2H_DES_KEY] = _des_raw
            st.session_state[_H2H_DES_TS]  = _time_h2h.time()
        _desafios_h2 = st.session_state.get(_H2H_DES_KEY, [])
        _d_ab   = [d for d in _desafios_h2 if d.get("estado")=="RESUELTO" and
                   ((d.get("retador")==pa and d.get("rival")==pb) or
                    (d.get("retador")==pb and d.get("rival")==pa))]
        _d_pend = [d for d in _desafios_h2 if d.get("estado")=="PENDIENTE" and
                   ((d.get("retador")==pa and d.get("rival")==pb) or
                    (d.get("retador")==pb and d.get("rival")==pa))]
        _d_a_wins = sum(1 for d in _d_ab if d.get("ganador")==pa)
        _d_b_wins = sum(1 for d in _d_ab if d.get("ganador")==pb)
        _d_draws  = sum(1 for d in _d_ab if d.get("ganador")=="EMPATE")
        _d_a_score = _d_a_wins + _d_draws
        _d_b_score = _d_b_wins + _d_draws
        _total_d = len(_d_ab)
        _draw_txt = f"🤝 {_d_draws} empate{'s' if _d_draws!=1 else ''} (+1 c/u)" if _d_draws else ""
        _pend_txt = f"⏳ {len(_d_pend)} pendiente(s)" if _d_pend else ""
        st.markdown(
            f'<div style="background:rgba(212,175,55,.06);border:1px solid rgba(212,175,55,.2);'
            f'border-radius:12px;padding:12px 16px;margin-top:14px;">'
            f'<div style="font-size:9px;font-weight:800;color:rgba(212,175,55,.6);'
            f'text-transform:uppercase;letter-spacing:.12em;margin-bottom:10px;">🎯 Desafíos Directos</div>'
            f'<div style="display:flex;align-items:center;justify-content:space-around;">'
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px;font-weight:900;color:{ca};">{_d_a_wins}</div>'
            f'<div style="font-size:10px;color:{ca};font-weight:700;">{pa.split()[0]}</div>'
            f'<div style="font-size:8px;color:rgba(169,178,214,.4);">victorias</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:13px;color:#D4AF37;font-weight:900;">{_d_draws} 🤝</div>'
            f'<div style="font-size:8px;color:#D4AF37;">Empates</div>'
            f'<div style="font-size:8px;color:rgba(169,178,214,.4);">{_total_d} jugados</div></div>'
            f'<div style="text-align:center;">'
            f'<div style="font-size:28px;font-weight:900;color:{cb};">{_d_b_wins}</div>'
            f'<div style="font-size:10px;color:{cb};font-weight:700;">{pb.split()[0]}</div>'
            f'<div style="font-size:8px;color:rgba(169,178,214,.4);">victorias</div></div>'
            f'</div>'
            + (f'<div style="margin-top:6px;text-align:center;font-size:9px;color:rgba(169,178,214,.5);">'
               f'Marcador: <b style="color:{ca};">{_d_a_score}</b> - <b style="color:{cb};">{_d_b_score}</b>'
               f'{" · " + _pend_txt if _pend_txt else ""}</div>' if _total_d > 0 or _d_pend else
               '<div style="font-size:9px;color:rgba(169,178,214,.35);text-align:center;margin-top:4px;">Sin desafíos jugados todavía</div>')
            + f'</div>', unsafe_allow_html=True)
    except Exception: pass
# ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
def _send_telegram(mensaje: str):
    """Envía mensaje al grupo Telegram. Requiere TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en secrets."""
    try:
        import urllib.request as _ur, json as _js
        token = st.secrets.get("TELEGRAM_BOT_TOKEN","")
        chat  = st.secrets.get("TELEGRAM_CHAT_ID","")
        if not token or not chat: return False
        payload = _js.dumps({"chat_id":str(chat),"text":mensaje,"parse_mode":"Markdown"}).encode()
        req = _ur.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                         data=payload, headers={"Content-Type":"application/json"})
        _ur.urlopen(req, timeout=8); return True
    except Exception as _te: print(f"Telegram error: {_te}"); return False


def _get_user_email(usuario: str) -> str:
    """Lee el email del usuario desde st.secrets['emails'] (dict JSON)."""
    try:
        emails = st.secrets.get("emails", {})
        return str(emails.get(usuario, ""))
    except: return ""

def _build_email_body(usuario, gp, tipo, resumen):
    gp_short = gp.replace("Gran Premio de ","GP ").replace("Gran Premio del ","GP ")
    return (
        f"🏆 TORNEO FEFE WOLF 2026\n\n"
        f"✅ PREDICCIÓN CONFIRMADA\n"
        f"{tipo} — {gp_short}\n"
        f"Formulero: {usuario}\n\n"
        f"{resumen}\n\n"
        f"🏁 torneofefewolf2026.streamlit.app"
    ), gp_short

def _send_prediccion_email(usuario: str, gp: str, tipo: str, resumen: str):
    """Envía email vía Gmail SMTP (recomendado) o SendGrid como fallback. Nunca rompe la app."""
    try:
        dest_email = _get_user_email(usuario)
        if not dest_email: return
        body_txt, gp_short = _build_email_body(usuario, gp, tipo, resumen)
        subject = f"🏎️ {tipo} enviado — {gp_short} | Torneo Fefe Wolf 2026"

        # ── Intento 1: Gmail SMTP (recomendado, sin registro externo) ──
        gmail_user = st.secrets.get("GMAIL_USER", "")
        gmail_pass = st.secrets.get("GMAIL_APP_PASSWORD", "")
        if gmail_user and gmail_pass:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"Torneo Fefe Wolf <{gmail_user}>"
            msg["To"] = dest_email
            msg.attach(MIMEText(body_txt, "plain", "utf-8"))
            _email_sent = False
            # Try SSL port 465 first
            try:
                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
                    srv.login(gmail_user, gmail_pass)
                    srv.sendmail(gmail_user, dest_email, msg.as_string())
                    _email_sent = True
            except Exception:
                pass
            # Fallback: TLS port 587
            if not _email_sent:
                try:
                    with smtplib.SMTP("smtp.gmail.com", 587) as srv:
                        srv.ehlo(); srv.starttls(); srv.ehlo()
                        srv.login(gmail_user, gmail_pass)
                        srv.sendmail(gmail_user, dest_email, msg.as_string())
                        _email_sent = True
                except Exception as _em:
                    import sys; print(f"Email TLS error: {_em}", file=sys.stderr)
            return

        # ── Intento 2: SendGrid fallback ──
        api_key = st.secrets.get("SENDGRID_API_KEY", "")
        from_email = st.secrets.get("SENDGRID_FROM", "")
        if api_key and from_email:
            import requests as _req
            payload = {
                "personalizations": [{"to": [{"email": dest_email}]}],
                "from": {"email": from_email, "name": "Torneo Fefe Wolf"},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body_txt}]
            }
            _req.post("https://api.sendgrid.com/v3/mail/send",
                      json=payload, timeout=8,
                      headers={"Authorization": f"Bearer {api_key}",
                               "Content-Type": "application/json"})
    except Exception: pass  # Never crash the app over email

def _wa_share_button(gp: str, tipo: str, resumen: str, usuario: str = "", oficial: dict = None, preds_all: dict = None):
    """
    Muestra botón de WhatsApp con mensaje ultra-profesional.
    - Piloto: su predicción + equipo al lado
    - Admin: predicciones de TODOS + aciertos al lado
    """
    import urllib.parse as _up, re as _rew

    _FLAG_MAP = {
        "Australia":"🇦🇺","China":"🇨🇳","Japón":"🇯🇵","Bahrein":"🇧🇭","Bahréin":"🇧🇭",
        "Arabia":"🇸🇦","Miami":"🇺🇸","Emilia":"🇮🇹","Mónaco":"🇲🇨","España":"🇪🇸",
        "Canadá":"🇨🇦","Austria":"🇦🇹","Gran Bretaña":"🇬🇧","Bélgica":"🇧🇪",
        "Hungría":"🇭🇺","Países Bajos":"🇳🇱","Italia":"🇮🇹","Azerbaiyán":"🇦🇿",
        "Singapur":"🇸🇬","México":"🇲🇽","Brasil":"🇧🇷","Las Vegas":"🇺🇸",
        "Qatar":"🇶🇦","Abu Dabi":"🇦🇪","Abu Dhabi":"🇦🇪",
    }
    gp_clean = _rew.sub(r'^\d+\.\s*','', gp.replace("Gran Premio de ","").replace("Gran Premio del ","").strip())
    bandera = next((v for k,v in _FLAG_MAP.items() if k.lower() in gp_clean.lower()), "🏁")
    gp_short = _rew.sub(r'^\d+\.\s*','', gp.replace("Gran Premio de ","GP ").replace("Gran Premio del ","GP ").strip())
    _MED = {1:"🥇",2:"🥈",3:"🥉",4:"4️⃣",5:"5️⃣",6:"6️⃣",7:"7️⃣",8:"8️⃣",9:"9️⃣",10:"🔟"}

    def _eq(nombre):
        return next((f"({t})" for t,ds in GRILLA_2026.items() if nombre in ds), "")

    def _check(pred_val, real_val):
        """✅ si coincide, ❌ si no"""
        if not pred_val or not real_val: return "❌"
        from core.utils import normalizar_nombre
        return "✅" if normalizar_nombre(pred_val) == normalizar_nombre(real_val) else "❌"

    lines = []

    if tipo == "ADMIN_FULL" and oficial and preds_all:
        # ── MENSAJE COMPLETO DEL ADMIN (todas las predicciones) ─────────
        of_r = {i: oficial.get(f"r{i}","") for i in range(1,11)}
        of_q = {i: oficial.get(f"q{i}","") for i in range(1,6)}
        of_c = {i: oficial.get(f"c{i}","") for i in range(1,4)}
        of_s = {i: oficial.get(f"s{i}","") for i in range(1,9)}

        lines = [
            f"🏎️ *TORNEO FEFE WOLF 2026*",
            f"{bandera} *{gp_short.upper()}* — PREDICCIONES COMPLETAS",
            f"━━━━━━━━━━━━━━━━━━━━━━━━",
            f"",
        ]
        for _pil, _pred in preds_all.items():
            _pil_clr_emoji = next((v for k,v in {"Checo Perez":"🟡","Nicki Lauda":"🔵","Fernando Alonso":"🔴","Lando Norris":"🟠","Valteri Bottas":"🩵"}.items() if k==_pil), "⚪")
            lines.append(f"{_pil_clr_emoji} *{_pil.upper()}*")
            # Qualy
            if any(_pred.get(f"q{i}","") for i in range(1,6)):
                lines.append(f"  ⏱️ *Qualy:*")
                for i in range(1,6):
                    _pv = _pred.get(f"q{i}","") or _pred.get(i,"")
                    if _pv:
                        _rv = of_q.get(i,"")
                        lines.append(f"    P{i} {_pv} {_eq(_pv)} {_check(_pv,_rv)}")
                _col_q = _pred.get("colapinto_q","")
                if _col_q:
                    _rv_col = oficial.get("col_q","")
                    lines.append(f"    🇦🇷 Colapinto P{_col_q} {_check(str(_col_q),str(_rv_col))}")
            # Sprint
            if any(_pred.get(f"spr{i}","") for i in range(1,9)):
                lines.append(f"  ⚡ *Sprint:*")
                for i in range(1,9):
                    _pv = _pred.get(f"spr{i}","")
                    if _pv:
                        _rv = of_s.get(i,"")
                        lines.append(f"    P{i} {_pv} {_eq(_pv)} {_check(_pv,_rv)}")
            # Carrera
            if any(_pred.get(f"p{i}","") for i in range(1,11)):
                lines.append(f"  🏁 *Carrera:*")
                for i in range(1,11):
                    _pv = _pred.get(f"p{i}","")
                    if _pv:
                        _rv = of_r.get(i,"")
                        lines.append(f"    P{i} {_pv} {_eq(_pv)} {_check(_pv,_rv)}")
                _col_r = _pred.get("colapinto_r","")
                if _col_r:
                    _rv_col = oficial.get("col_r","")
                    lines.append(f"    🇦🇷 Colapinto P{_col_r} {_check(str(_col_r),str(_rv_col))}")
            # Constructores
            if any(_pred.get(f"c{i}","") for i in range(1,4)):
                lines.append(f"  🏗️ *Constructores:*")
                for i in range(1,4):
                    _pv = _pred.get(f"c{i}","")
                    if _pv:
                        _rv = of_c.get(i,"")
                        lines.append(f"    {_MED.get(i,str(i)+'°')} {_pv} {_check(_pv,_rv)}")
            lines.append(f"  {'─'*18}")
        lines += ["", f"✅=Acierto ❌=Fallo", f"🏁 _torneofefewolf2026.streamlit.app_"]

    else:
        # ── MENSAJE PERSONAL DEL FORMULERO ─────────────────────────────
        lines = [
            f"🏎️ *TORNEO FEFE WOLF 2026*",
            f"{bandera} *{gp_short.upper()}*",
            f"👤 Predicción de *{usuario}*" if usuario else "",
            f"━━━━━━━━━━━━━━━━━",
            f"",
        ]
        if tipo == "QUALY":
            lines.append("⏱️ *CLASIFICACIÓN*")
            partes = [p.strip() for p in resumen.split("\n")[0].split("·") if p.strip()]
            for ps in partes:
                try:
                    pp = ps.split(" ",1); num = int(pp[0].replace("P",""))
                    nom = pp[1].strip() if len(pp)>1 else ps
                    lines.append(f"  {_MED.get(num,f'P{num}')} {nom} {_eq(nom)}")
                except Exception: lines.append(f"  {ps}")
            col = next((p for p in resumen.split("\n") if "Colapinto" in p),"")
            if col: lines += ["", f"🇦🇷 {col.strip()}"]

        elif tipo == "SPRINT":
            lines.append("⚡ *SPRINT*")
            partes = [p.strip() for p in resumen.split("·") if p.strip()]
            for ps in partes:
                try:
                    pp = ps.split(" ",1); num = int(pp[0].replace("P",""))
                    nom = pp[1].strip() if len(pp)>1 else ps
                    lines.append(f"  {_MED.get(num,f'P{num}')} {nom} {_eq(nom)}")
                except Exception: lines.append(f"  {ps}")

        elif tipo in ("CARRERA","CARRERA+CONSTRUCTORES"):
            lines.append("🏁 *CARRERA*")
            sects = resumen.split("\n")
            for ps in [p.strip() for p in sects[0].split("·") if p.strip()]:
                try:
                    pp = ps.split(" ",1); num = int(pp[0].replace("P",""))
                    nom = pp[1].strip() if len(pp)>1 else ps
                    lines.append(f"  {_MED.get(num,f'P{num}')} {nom} {_eq(nom)}")
                except Exception: lines.append(f"  {ps}")
            col = next((p for p in sects if "Colapinto" in p),"")
            if col: lines += ["", f"🇦🇷 {col.strip()}"]
            con = next((p for p in sects if "Constructores" in p or "Constructor" in p),"")
            if con:
                lines += ["", "🏗️ *CONSTRUCTORES*"]
                cnames = _rew.sub(r'.*:','',con).strip()
                for ci,cn in enumerate([c.strip() for c in cnames.split("/") if c.strip()],1):
                    lines.append(f"  {_MED.get(ci,str(ci)+'°')} {cn}")
        else:
            lines.append(resumen)

        lines += ["", f"🏁 _torneofefewolf2026.streamlit.app_"]

    txt = "\n".join(l for l in lines if l is not None)
    url = "https://wa.me/?text=" + _up.quote(txt)
    st.markdown(
        f'<a href="{url}" target="_blank" style="display:inline-flex;align-items:center;gap:10px;'
        f'background:linear-gradient(135deg,#075e54,#25d366);color:#fff;font-weight:800;'
        f'font-size:13px;padding:11px 22px;border-radius:14px;text-decoration:none;'
        f'box-shadow:0 4px 18px rgba(37,211,102,.4);margin-top:8px;letter-spacing:.03em;'
        f'transition:transform .15s;"> '
        f'<span style="font-size:22px;">📲</span> Compartir por WhatsApp</a>',
        unsafe_allow_html=True
    )


    """
    Muestra botón de WhatsApp con mensaje enriquecido.
    Incluye: bandera del país, tipo de predicción, posiciones con equipo,
    posición de Colapinto y constructores con medallas.
    """
    import urllib.parse as _up

    # ── Bandera del GP ──────────────────────────────────────────────
    _FLAG_MAP = {
        "Australia":"🇦🇺","China":"🇨🇳","Japón":"🇯🇵","Bahrein":"🇧🇭","Bahréin":"🇧🇭",
        "Arabia":"🇸🇦","Miami":"🇺🇸","Emilia":"🇮🇹","Mónaco":"🇲🇨","España":"🇪🇸",
        "Canadá":"🇨🇦","Austria":"🇦🇹","Gran Bretaña":"🇬🇧","Bélgica":"🇧🇪",
        "Hungría":"🇭🇺","Holanda":"🇳🇱","Países Bajos":"🇳🇱","Italia":"🇮🇹",
        "Azerbaiyán":"🇦🇿","Singapur":"🇸🇬","Estados Unidos":"🇺🇸","México":"🇲🇽",
        "Brasil":"🇧🇷","Las Vegas":"🇺🇸","Qatar":"🇶🇦","Abu Dabi":"🇦🇪","Abu Dhabi":"🇦🇪",
    }
    gp_clean = gp.replace("Gran Premio de ","").replace("Gran Premio del ","").replace("Gran Premio","").strip()
    # Quitar numeración tipo "01. "
    if len(gp_clean) > 3 and gp_clean[2] == ".":
        gp_clean = gp_clean[4:].strip()
    bandera = next((v for k, v in _FLAG_MAP.items() if k.lower() in gp_clean.lower()), "🏁")
    gp_short = gp.replace("Gran Premio de ","GP ").replace("Gran Premio del ","GP ")\
                  .replace("01. ","").replace("02. ","").replace("03. ","").replace("04. ","")\
                  .replace("05. ","").replace("06. ","").replace("07. ","").replace("08. ","")\
                  .replace("09. ","").replace("10. ","")
    # Remove leading "NN. " pattern
    import re as _re
    gp_short = _re.sub(r"^\d+\.\s*", "", gp_short)

    # ── Medallas ────────────────────────────────────────────────────
    _MED = {1:"🥇",2:"🥈",3:"🥉"}

    # ── Construir texto según tipo ───────────────────────────────────
    lineas = [
        f"🏎️ *TORNEO FEFE WOLF 2026*",
        f"{bandera} *{gp_short.upper()}* — {tipo}",
        f"👤 Predicción de *{usuario}*" if usuario else "",
        "",
    ]

    # Parsear el resumen para enriquecer con equipos
    def _piloto_con_equipo(nombre: str) -> str:
        """Agrega el equipo entre paréntesis si se conoce."""
        nombre = (nombre or "").strip()
        if not nombre:
            return nombre
        eq = next((t for t, ds in GRILLA_2026.items() if nombre in ds), "")
        return f"{nombre} ({eq})" if eq else nombre

    if tipo == "QUALY":
        # resumen viene como "P1 Piloto · P2 Piloto · ... \n🇦🇷 Colapinto: P?"
        partes = resumen.split("\n")
        posiciones = [p.strip() for p in partes[0].split("·") if p.strip()]
        lineas.append("⏱️ *CLASIFICACIÓN*")
        for pos_str in posiciones:
            # "P1 Max Verstappen"
            try:
                _, num, *nombre_parts = pos_str.split(" ", 2) if " " in pos_str else ("", pos_str, "")
                num_int = int(num.replace("P",""))
                nombre = " ".join(nombre_parts) if nombre_parts else num
                med = _MED.get(num_int, f"P{num_int}")
                lineas.append(f"  {med} {_piloto_con_equipo(nombre)}")
            except Exception:
                lineas.append(f"  {pos_str}")
        # Colapinto
        col_line = next((p for p in partes if "Colapinto" in p), "")
        if col_line:
            lineas.append(f"\n🇦🇷 {col_line.strip()}")

    elif tipo == "SPRINT":
        partes = [p.strip() for p in resumen.split("·") if p.strip()]
        lineas.append("⚡ *SPRINT*")
        for pos_str in partes:
            try:
                parts2 = pos_str.split(" ", 1)
                num_int = int(parts2[0].replace("P",""))
                nombre = parts2[1] if len(parts2) > 1 else pos_str
                med = _MED.get(num_int, f"P{num_int}")
                lineas.append(f"  {med} {_piloto_con_equipo(nombre)}")
            except Exception:
                lineas.append(f"  {pos_str}")

    elif tipo == "CARRERA":
        partes = resumen.split("\n")
        # Primera línea: posiciones de carrera separadas por " · "
        posiciones = [p.strip() for p in partes[0].split("·") if p.strip()]
        lineas.append("🏁 *CARRERA*")
        for pos_str in posiciones:
            try:
                parts2 = pos_str.split(" ", 1)
                num_int = int(parts2[0].replace("P",""))
                nombre = parts2[1] if len(parts2) > 1 else pos_str
                med = _MED.get(num_int, f"P{num_int}")
                lineas.append(f"  {med} {_piloto_con_equipo(nombre)}")
            except Exception:
                lineas.append(f"  {pos_str}")
        # Colapinto
        col_line = next((p for p in partes if "Colapinto" in p), "")
        if col_line:
            lineas.append(f"🇦🇷 {col_line.strip()}")
        # Constructores
        con_line = next((p for p in partes if "Constructores" in p), "")
        if con_line:
            lineas.append("")
            lineas.append("🏗️ *CONSTRUCTORES*")
            # "🏗️ Constructores: MCLAREN / RED BULL / FERRARI"
            con_names = con_line.replace("🏗️ Constructores:","").replace("Constructores:","").strip()
            con_list = [c.strip() for c in con_names.split("/") if c.strip()]
            for idx, con in enumerate(con_list, 1):
                lineas.append(f"  {_MED.get(idx, str(idx)+'°')} {con}")

    else:
        lineas.append(resumen)

    lineas += ["", "🏁 _torneofefewolf2026.streamlit.app_"]
    txt = "\n".join(l for l in lineas if l is not None)

    url = "https://wa.me/?text=" + _up.quote(txt)
    st.markdown(
        f"""<a href="{url}" target="_blank" style="display:inline-flex;align-items:center;gap:10px;
        background:linear-gradient(90deg,#128c7e,#25d366);color:#fff;font-weight:800;
        font-size:13px;padding:10px 20px;border-radius:12px;text-decoration:none;
        box-shadow:0 0 16px rgba(37,211,102,.35);margin-top:8px;letter-spacing:.03em;">
        <span style="font-size:22px;">📲</span> Compartir por WhatsApp</a>""",
        unsafe_allow_html=True
    )

def pantalla_perfil():
    """Perfil personal del usuario logueado — stats completas."""
    perfil  = st.session_state.get("perfil") or {}
    usuario = perfil.get("usuario","")
    rol     = perfil.get("rol","Piloto")
    copas   = int(perfil.get("copas",0) or 0)
    clr     = PILOTO_COLORS.get(usuario,"#a855f7")
    ph      = DRIVER_HEADSHOTS.get(usuario, DRIVER_PHOTOS.get(usuario,""))
    ph_full = DRIVER_PHOTOS.get(usuario,"")
    ini     = "".join(w[0] for w in usuario.split()[:2]).upper()

    st.markdown(f"""<style>
    @keyframes profG{{0%,100%{{box-shadow:0 0 28px {clr}28;}}50%{{box-shadow:0 0 52px {clr}55;}}}}
    @keyframes profShimmer{{0%{{background-position:200% center;}}100%{{background-position:-200% center;}}}}
    .prof-wrap{{background:linear-gradient(145deg,rgba(7,9,22,.99),rgba(13,17,42,.99));
      border:1.5px solid {clr}66;border-radius:24px;overflow:hidden;
      position:relative;margin-bottom:18px;animation:profG 4s ease-in-out infinite;}}
    .prof-wrap::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
      background:linear-gradient(90deg,transparent,{clr},rgba(255,255,255,.6),{clr},transparent);
      animation:profShimmer 3s linear infinite;background-size:200% auto;}}
    .prof-body{{display:flex;align-items:center;gap:22px;padding:22px 24px 18px;}}
    .prof-av{{flex-shrink:0;}}
    .prof-info{{flex:1;}}
    .prof-name{{font-size:26px;font-weight:900;color:#ffdd7a;letter-spacing:.06em;line-height:1;}}
    .prof-roles{{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 8px;}}
    .prof-role-tag{{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
      border-radius:20px;padding:3px 10px;font-size:10px;font-weight:700;
      color:rgba(232,236,255,.7);letter-spacing:.08em;text-transform:uppercase;}}
    .prof-copas{{font-size:20px;letter-spacing:2px;}}
    .prof-stat-row{{display:flex;gap:0;border-top:1px solid rgba(255,255,255,.06);}}
    .prof-stat{{flex:1;text-align:center;padding:14px 8px;
      border-right:1px solid rgba(255,255,255,.05);}}
    .prof-stat:last-child{{border-right:none;}}
    .prof-stat-val{{font-size:24px;font-weight:900;}}
    .prof-stat-lbl{{font-size:9px;color:rgba(169,178,214,.5);text-transform:uppercase;
      letter-spacing:.12em;margin-top:3px;}}
    .prof-stat-det{{font-size:10px;color:rgba(232,236,255,.4);margin-top:2px;}}
    .prof-sec-title{{font-size:10px;font-weight:700;letter-spacing:.14em;
      color:rgba(246,195,73,.65);text-transform:uppercase;margin:14px 0 8px;}}
    .prof-gp-row{{display:flex;align-items:center;gap:10px;padding:8px 13px;
      background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);
      border-radius:11px;margin-bottom:5px;transition:border-color .15s;}}
    .prof-gp-row:hover{{border-color:rgba(255,255,255,.14);}}
    .prof-gp-name{{flex:1;font-size:12px;color:#e8ecff;}}
    .prof-gp-bar-wrap{{flex:2;height:7px;background:rgba(255,255,255,.06);
      border-radius:4px;overflow:hidden;}}
    .prof-gp-pts{{min-width:34px;text-align:right;font-size:13px;font-weight:900;}}
    </style>""", unsafe_allow_html=True)

    # ── Foto de perfil — load from Sheets if not in session ─────────
    _photo_key = f"custom_photo_{usuario}"
    if not st.session_state.get(_photo_key):
        _foto_from_perfil = (st.session_state.get("perfil") or {}).get("foto_url","")
        if _foto_from_perfil:
            st.session_state[_photo_key] = _foto_from_perfil
    _custom_ph = st.session_state.get(_photo_key, "")
    if _custom_ph: ph = _custom_ph

    # ── Hero card ──────────────────────────────────────────
    if ph:
        av = (f'<div style="position:relative;width:96px;height:96px;">'
              f'<img src="{ph}" style="width:96px;height:96px;border-radius:50%;'
              f'object-fit:cover;object-position:center 12%;border:3px solid {clr};'
              f'box-shadow:0 0 24px {clr}66;">'
              f'</div>')
    else:
        av = (f'<div style="width:96px;height:96px;border-radius:50%;background:{clr}22;'
              f'border:3px solid {clr};display:flex;align-items:center;justify-content:center;'
              f'font-size:30px;font-weight:900;color:{clr};box-shadow:0 0 24px {clr}44;">{ini}</div>')

    _roles = [r.strip() for r in rol.split("|")] if "|" in rol else [rol]
    _roles_html = "".join(f'<span class="prof-role-tag">{r}</span>' for r in _roles if r)
    _copas_html = "🏆" * copas if copas else ""

    # ── Cargo historial ──────────────────────────────────────
    m = _mod_db()
    if "_error" in m:
        st.warning("⚠️ No se pudo cargar el historial."); return

    @st.cache_data(ttl=60, show_spinner=False)
    def _prof_hist(): return _safe_call(m["leer_historial_df"], timeout_sec=20, default=pd.DataFrame())
    @st.cache_data(ttl=60, show_spinner=False)
    def _prof_tabla(): return _safe_call(m["leer_tabla_posiciones"], PILOTOS_TORNEO, timeout_sec=8, default=None)

    h   = _prof_hist()
    dft = _prof_tabla()

    # Parsing historial
    df_p = None
    try:
        if h is not None and not (hasattr(h,"empty") and h.empty):
            if "piloto" in h.columns:
                _cg = next((c for c in h.columns if "gran" in c.lower() or c.lower()=="gp"), None)
                _cp = next((c for c in h.columns if "punt" in c.lower()), None)
                if _cg and _cp:
                    sub = h[h["piloto"]==usuario][[_cg,_cp]].copy(); sub.columns=["gp","pts"]; df_p=sub
            if df_p is None and usuario in h.columns:
                _gc = h.columns[0]
                df_p = pd.DataFrame({"gp":h[_gc],"pts":pd.to_numeric(h[usuario],errors="coerce").fillna(0)})
            if df_p is None:
                _ix = h.set_index(h.columns[0])
                if usuario in _ix.index:
                    row = _ix.loc[usuario]
                    df_p = pd.DataFrame({"gp":row.index.tolist(),"pts":pd.to_numeric(row.values,errors="coerce").tolist()})
    except Exception: pass

    if df_p is not None:
        df_p["pts"] = pd.to_numeric(df_p["pts"],errors="coerce").fillna(0)
        df_p = df_p[df_p["pts"].notna()].reset_index(drop=True)  # keep all, even 0

    if df_p is None or df_p.empty:
        if is_admin():
            st.info("📋 Sin historial en Google Sheets. Usá la 🧮 Calculadora → 'Generar Historial + DNS' para cada GP ya computado (Australia, China, Japón).", icon="ℹ️")
        if st.button("🔄 Recargar historial", key="prof_reload_hist"):
            _prof_hist.clear(); st.rerun()

    # Stats
    total_pts, n_gps, prom, mejor_pts, peor_pts = 0, 0, 0.0, 0, 0
    mejor_gp_lbl, peor_gp_lbl = "—", "—"
    pos_actual = "—"
    if df_p is not None and not df_p.empty:
        total_pts = int(df_p["pts"].sum())
        n_gps     = len(df_p)
        prom      = round(df_p["pts"].mean(),1)
        mejor_pts = int(df_p["pts"].max()); peor_pts = int(df_p["pts"].min())
        mejor_gp_lbl = str(df_p.loc[df_p["pts"].idxmax(),"gp"]).replace("Gran Premio de ","").replace("Gran Premio del ","")[:18]
        peor_gp_lbl  = str(df_p.loc[df_p["pts"].idxmin(),"gp"]).replace("Gran Premio de ","").replace("Gran Premio del ","")[:18]

    # Posición en tabla
    if dft is not None and not (hasattr(dft,"empty") and dft.empty):
        try:
            _dt2 = dft.copy()
            _pt_col = next((c for c in _dt2.columns if "punt" in str(c).lower()), None)
            if _pt_col:
                _dt2[_pt_col] = pd.to_numeric(_dt2[_pt_col],errors="coerce").fillna(0)
                _dt2 = _dt2.sort_values(_pt_col,ascending=False).reset_index(drop=True)
                _pil_col = next((c for c in _dt2.columns if "piloto" in str(c).lower() or "nombre" in str(c).lower()), _dt2.columns[0])
                _row_u = _dt2[_dt2[_pil_col]==usuario]
                if not _row_u.empty:
                    pos_actual = f"P{_row_u.index[0]+1}"
        except Exception: pass

    st.markdown(
        f'<div class="prof-wrap">'
        f'<div class="prof-body">'
        f'<div class="prof-av">{av}</div>'
        f'<div class="prof-info">'
        f'<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        f'<div class="prof-name">{usuario}</div>'
        + (f'<span style="background:{clr}22;border:1px solid {clr}66;color:{clr};'
           f'border-radius:20px;padding:3px 12px;font-size:12px;font-weight:900;'
           f'letter-spacing:.04em;">{pos_actual} · {total_pts} pts</span>' if pos_actual != "—" else
           f'<span style="background:rgba(169,178,214,.1);border:1px solid rgba(169,178,214,.25);'
           f'color:rgba(169,178,214,.7);border-radius:20px;padding:3px 12px;font-size:11px;'
           f'font-weight:800;">🆕 Listo para competir</span>')
        + f'</div>'
        f'<div class="prof-roles">{_roles_html}</div>'
        f'<div class="prof-copas">{_copas_html}</div>'
        f'</div></div>'
        f'<div class="prof-stat-row">'
        f'<div class="prof-stat"><div class="prof-stat-val" style="color:{clr};">{total_pts}</div>'
        f'<div class="prof-stat-lbl">Total pts</div><div class="prof-stat-det">{n_gps} GPs</div></div>'
        f'<div class="prof-stat"><div class="prof-stat-val" style="color:{clr};">{prom}</div>'
        f'<div class="prof-stat-lbl">Promedio</div><div class="prof-stat-det">pts / GP</div></div>'
        f'<div class="prof-stat"><div class="prof-stat-val" style="color:#4ade80;">{mejor_pts}</div>'
        f'<div class="prof-stat-lbl">Mejor GP</div><div class="prof-stat-det">{mejor_gp_lbl}</div></div>'
        f'<div class="prof-stat"><div class="prof-stat-val" style="color:#ef4444;">{peor_pts}</div>'
        f'<div class="prof-stat-lbl">Peor GP</div><div class="prof-stat-det">{peor_gp_lbl}</div></div>'
        f'<div class="prof-stat"><div class="prof-stat-val" style="color:#ffdd7a;">{pos_actual}</div>'
        f'<div class="prof-stat-lbl">Posición</div><div class="prof-stat-det">tabla gral.</div></div>'
        f'<div class="prof-stat"><div class="prof-stat-val" style="color:#ffdd7a;">{copas}</div>'
        f'<div class="prof-stat-lbl">Títulos</div><div class="prof-stat-det">campeonatos</div></div>'
        f'<div class="prof-stat"><div class="prof-stat-val" style="color:#ef4444;">{_dns_count(usuario)}</div>'
        f'<div class="prof-stat-lbl">DNS</div><div class="prof-stat-det">sanciones</div></div>'
        f'</div></div>', unsafe_allow_html=True)

    if df_p is None or df_p.empty:
        st.info("📋 Sin puntos registrados todavía. Una vez generado el historial aparecerán tus stats y logros.")
        # Still show logros section (all locked) even without history

    # ── Cambiar foto — SOLO por URL (permanente). Upload eliminado: no persistía. ──
    with st.expander("📸 Cambiar mi foto de perfil", expanded=False):
        st.caption("Pegá una URL pública de tu foto. Subila gratis a imgbb.com → copiá el 'Direct link' (termina en .jpg/.png).")
        _foto_url_direct = st.text_input(
            "🔗 URL de foto",
            key="foto_url_direct_inp",
            placeholder="https://i.ibb.co/XXXXX/foto.jpg")
        _cfu1, _cfu2 = st.columns([3,1])
        with _cfu1:
            if st.button("💾 Guardar foto", key="save_foto_url_btn", use_container_width=True):
                _url_clean = (_foto_url_direct or "").strip()
                if not _url_clean.lower().startswith(("http://","https://")):
                    st.error("Pegá una URL válida que empiece con http:// o https://")
                else:
                    try:
                        _mfu = _mod_auth()
                        if "_error" not in _mfu and "save_foto_url" in _mfu:
                            _ok_fu, _ = _safe_call(_mfu["save_foto_url"], usuario, _url_clean,
                                                   timeout_sec=12, default=(False,""))
                            if _ok_fu:
                                if st.session_state.get("perfil"):
                                    st.session_state["perfil"]["foto_url"] = _url_clean
                                st.session_state[_photo_key] = _url_clean
                                try: _get_perfil.clear()
                                except: pass
                                st.success("✅ Foto guardada permanentemente"); st.rerun()
                            else:
                                st.error("No se pudo guardar la URL")
                    except Exception as _fue: st.error(str(_fue))
        with _cfu2:
            if st.session_state.get(_photo_key,""):
                if st.button("🗑️ Quitar", key="prof_photo_del", use_container_width=True):
                    st.session_state.pop(_photo_key, None)
                    if "perfil" in st.session_state and st.session_state["perfil"]:
                        st.session_state["perfil"]["foto_url"] = ""
                    try:
                        _m_foto2 = _mod_auth()
                        if "_error" not in _m_foto2 and "save_foto_url" in _m_foto2:
                            _safe_call(_m_foto2["save_foto_url"], usuario, "", timeout_sec=10, default=(False,""))
                    except Exception: pass
                    st.rerun()

    # ── Initialize df_det early (used below before loading section) ──────
    df_det = pd.DataFrame(columns=["gp","piloto","etapa","puntos"])

    # ── % Aciertos por etapa ──────────────────────────────────────────
    if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
        try:
            _dd_prof = df_det.copy()
            _dd_prof.columns = [c.lower().strip() for c in _dd_prof.columns]
            _dd_prof["puntos"] = pd.to_numeric(_dd_prof["puntos"], errors="coerce").fillna(0)
            _dd_u = _dd_prof[_dd_prof.get("piloto", pd.Series(dtype=str)).astype(str)==usuario] if "piloto" in _dd_prof.columns else _dd_prof

            # Load oficial to calculate exact aciertos
            _m_stats = _mod_db()
            _aciert_etapa = {}
            _total_etapa = {}
            if "_error" not in _m_stats:
                _fn_of_s = _m_stats.get("leer_resultados_oficiales")
                if callable(_fn_of_s) and df_p is not None and not df_p.empty:
                    for _gp_s in df_p.get("gp", pd.Series(dtype=str)).values:
                        try:
                            _of_s = _safe_call(_fn_of_s, _gp_s, timeout_sec=5, default={}) or {}
                            if not _of_s: continue
                            _rp_s = _safe_call(_m_stats["recuperar_predicciones_piloto"], usuario, _gp_s, timeout_sec=8, default=(None,None,(None,None)))
                            _dq_s,_ds_s,(_dr_s,_dc_s) = _rp_s
                            for _et, _pred, _pfx, _n in [("Qualy",_dq_s,"q",5),("Carrera",_dr_s,"r",10),("Sprint",_ds_s,"s",8)]:
                                if not _pred: continue
                                for _pp in range(1,_n+1):
                                    _pv = str(_pred.get(_pp,"")).strip()
                                    _rv = str(_of_s.get(f"{_pfx}{_pp}","")).strip()
                                    if _pv and _rv:
                                        _total_etapa[_et] = _total_etapa.get(_et,0)+1
                                        if _rv.lower() in _pv.lower() or _pv.lower() in _rv.lower():
                                            _aciert_etapa[_et] = _aciert_etapa.get(_et,0)+1
                        except Exception: pass

            if _aciert_etapa:
                st.markdown(
                    '<div class="prof-sec-title" style="margin-top:16px;">🎯 PORCENTAJE DE ACIERTOS</div>',
                    unsafe_allow_html=True)
                _pct_cols = st.columns(len(_aciert_etapa))
                for _ci, (_et, _hits) in enumerate(_aciert_etapa.items()):
                    _tot = _total_etapa.get(_et,1)
                    _pct = int(_hits/_tot*100)
                    _clr_pct = "#4ade80" if _pct>=40 else ("#D4AF37" if _pct>=25 else "#ef4444")
                    with _pct_cols[_ci]:
                        st.markdown(
                            f'<div style="text-align:center;background:{_clr_pct}12;'
                            f'border:1px solid {_clr_pct}33;border-radius:10px;padding:8px 4px;">'
                            f'<div style="font-size:20px;font-weight:900;color:{_clr_pct};">{_pct}%</div>'
                            f'<div style="font-size:8px;color:rgba(169,178,214,.5);text-transform:uppercase;">{_et}</div>'
                            f'<div style="font-size:9px;color:rgba(169,178,214,.4);">{_hits}/{_tot}</div>'
                            f'</div>', unsafe_allow_html=True)
        except Exception: pass
        if _PLOTLY_OK:
            try:
                import plotly.graph_objects as _go2
                df_p["acum"] = df_p["pts"].cumsum()
                gp_lbs = [g.replace("Gran Premio de ","GP ").replace("Gran Premio del ","GP ").replace("0","").replace("1. ","").replace("2. ","").replace("3. ","") for g in df_p["gp"]]
                fig = _go2.Figure()
                fig.add_trace(_go2.Bar(name="Pts GP",x=gp_lbs,y=df_p["pts"],
                    marker_color=clr,marker_line_width=0,
                    text=df_p["pts"],textposition="outside",
                    textfont=dict(color=clr,size=11),cliponaxis=False))
                fig.add_trace(_go2.Scatter(name="Acumulado",x=gp_lbs,y=df_p["acum"],
                    mode="lines+markers+text",line=dict(color="#ffdd7a",width=2,dash="dot"),
                    marker=dict(size=7,color="#ffdd7a"),
                    text=df_p["acum"],textposition="top center",
                    textfont=dict(color="#ffdd7a",size=10)))
                ymax = max(df_p["acum"].max(),df_p["pts"].max(),1)*1.28
                fig.update_layout(height=260,barmode="overlay",
                    paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=4,r=4,t=38,b=4),
                    title=dict(text="📊 Puntos por GP & Acumulado",font=dict(color="#ffdd7a",size=12),x=0),
                    legend=dict(font=dict(color="#e8ecff",size=10),bgcolor="rgba(0,0,0,0)",orientation="h",y=1.14,x=0),
                    xaxis=dict(tickfont=dict(color="#e8ecff",size=9),showgrid=False),
                    yaxis=dict(tickfont=dict(color="#a9b2d6",size=9),gridcolor="rgba(255,255,255,.04)",zeroline=False,range=[0,ymax]))
                st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"staticPlot":True})
            except Exception: pass

        # ── Detalle por GP ──────────────────────────────────────
        st.markdown('<div class="prof-sec-title">📋 Detalle por GP</div>', unsafe_allow_html=True)
        _max_pts = max(df_p["pts"].max(),1)
        for _, row in df_p.sort_values("pts",ascending=False).iterrows():
            gp_lbl = str(row["gp"]).replace("Gran Premio de ","GP ").replace("Gran Premio del ","GP ")
            pts_v  = int(row["pts"])
            pct    = pts_v/_max_pts*100
            bclr   = "#4ade80" if pts_v==mejor_pts else ("#ef4444" if pts_v==peor_pts else clr)
            st.markdown(
                f'<div class="prof-gp-row">'
                f'<div class="prof-gp-name">{gp_lbl}</div>'
                f'<div class="prof-gp-bar-wrap">'
                f'<div style="width:{pct:.0f}%;height:100%;background:{bclr};border-radius:4px;'
                f'box-shadow:0 0 5px {bclr}55;"></div></div>'
                f'<div class="prof-gp-pts" style="color:{bclr};">{pts_v}</div>'
                f'</div>', unsafe_allow_html=True)

    # ── Logros / Achievements ────────────────────────────────
    # Count unlocked for the header badge
    try:
        _n_unlocked = sum(1 for _x in logros_calc if _x[1]) if 'logros_calc' in dir() else 0
    except Exception: _n_unlocked = 0

    _lg_col1, _lg_col2 = st.columns([3,1])
    with _lg_col1:
        st.markdown('<div class="prof-sec-title" style="margin-top:18px;">🏅 LOGROS & MEDALLAS</div>',
                    unsafe_allow_html=True)
    with _lg_col2:
        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        _lg_open = st.session_state.get("_perfil_logros_open", False)
        if st.button("👁️ Ver" if not _lg_open else "🙈 Ocultar",
                     key="toggle_logros_perfil", use_container_width=True):
            st.session_state["_perfil_logros_open"] = not _lg_open
            st.rerun()

    st.markdown("""<style>
    .logro-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px;}
    @media(max-width:640px){.logro-grid{grid-template-columns:repeat(2,1fr);}}
    .logro-card{border-radius:14px;padding:14px 10px;text-align:center;position:relative;
      transition:transform .2s;}
    .logro-card.on{background:rgba(212,175,55,.1);border:1px solid rgba(212,175,55,.4);}
    .logro-card.off{background:rgba(255,255,255,.02);border:1px solid rgba(255,255,255,.07);
      filter:grayscale(0.8);opacity:.5;}
    .logro-card:hover{transform:translateY(-3px);}
    .logro-emo{font-size:28px;display:block;margin-bottom:5px;}
    .logro-name{font-size:11px;font-weight:800;color:#ffdd7a;margin-bottom:3px;line-height:1.2;}
    .logro-desc{font-size:9px;color:rgba(169,178,214,.6);}
    .logro-lock{position:absolute;top:8px;right:8px;font-size:12px;opacity:.4;}
    </style>""", unsafe_allow_html=True)

    # Load detalle for achievements — fully protected against any column issues
    df_det_l  = pd.DataFrame(columns=["gp","piloto","etapa","puntos"])
    df_det    = df_det_l  # alias — always available
    _df_logro = pd.DataFrame()
    logros_calc = [(_l, False, "") for _l in _LOGROS_DEF]
    try:
        m2 = _mod_db()
        if "_error" not in m2:
            _fn_det = m2.get("leer_historial_detalle_df")
            if callable(_fn_det):
                try:
                    _res_det = _safe_call(_fn_det, timeout_sec=15, default=None)
                    if _res_det is not None and isinstance(_res_det, pd.DataFrame) and not _res_det.empty:
                        _res_det = _res_det.copy()
                        _res_det.columns = [c.lower().strip() for c in _res_det.columns]
                        # Keep only expected columns, ignore anything else
                        for _req_c in ["gp","piloto","etapa","puntos"]:
                            if _req_c not in _res_det.columns:
                                _res_det[_req_c] = "" if _req_c != "puntos" else 0
                        _res_det["puntos"] = pd.to_numeric(_res_det["puntos"],errors="coerce").fillna(0).astype(int)
                        # ONLY keep the 4 required cols to avoid any KeyError
                        df_det_l = _res_det[["gp","piloto","etapa","puntos"]].copy()
                    df_det = df_det_l  # update alias with loaded data
                except Exception as _det_e:
                    print(f"ERROR loading detalle for logros: {_det_e}")

        if df_p is not None and not df_p.empty:
            _df_logro = df_p.rename(columns={"pts":"puntos"}).copy()
            _df_logro["piloto"] = usuario
            for _req in ["gp","puntos","piloto"]:
                if _req not in _df_logro.columns: _df_logro[_req] = 0 if _req == "puntos" else ""

        # For Triple Corona we need ALL users' historial
        _df_logro_all = None
        try:
            if h is not None and not (hasattr(h,"empty") and h.empty):
                _h_copy = h.copy()
                _h_copy.columns = [c.lower().strip() for c in _h_copy.columns]
                _cn_gp  = next((c for c in _h_copy.columns if c in ["gp","gran_premio"]), None)
                _cn_pil = next((c for c in _h_copy.columns if c in ["piloto","usuario"]), None)
                _cn_pts = next((c for c in _h_copy.columns if c in ["puntos","pts","points"]), None)
                if _cn_gp and _cn_pil and _cn_pts:
                    _df_logro_all = _h_copy[[_cn_gp,_cn_pil,_cn_pts]].copy()
                    _df_logro_all.columns = ["gp","piloto","puntos"]
                    _df_logro_all["puntos"] = pd.to_numeric(_df_logro_all["puntos"],errors="coerce").fillna(0).astype(int)
        except Exception: pass

        n_gps_total = len(df_p) if (df_p is not None and not df_p.empty) else 0
        logros_calc = _calc_logros(usuario, _df_logro_all if _df_logro_all is not None else _df_logro,
                                   df_det_l, n_gps_total)
    except Exception as _le:
        print(f"ERROR loading logros: {_le}")
        logros_calc = [(_l, False, "") for _l in _LOGROS_DEF]

    cards_html = '<div class="logro-grid">'
    import html as _html_logro
    for logro_def, desbloqueado, _gp_logro in logros_calc:
        lid, emo, name, desc, _ = logro_def
        cls = "on" if desbloqueado else "off"
        lock = "" if desbloqueado else '<span class="logro-lock">🔒</span>'
        name_s = _html_logro.escape(str(name))
        desc_s = _html_logro.escape(str(desc))
        emo_s  = str(emo)
        gp_badge = (f'<div style="font-size:8px;color:rgba(74,222,128,.7);margin-top:3px;">'
                    f'Ganado en: {_html_logro.escape(_gp_logro)}</div>') if _gp_logro and desbloqueado else ""
        cards_html += (f'<div class="logro-card {cls}">{lock}'
                       f'<span class="logro-emo">{emo_s}</span>'
                       f'<div class="logro-name">{name_s}</div>'
                       f'<div class="logro-desc">{desc_s}</div>'
                       f'{gp_badge}</div>')
    cards_html += '</div>'

    # Summary badge always visible; grid only if toggled open
    _n_on = sum(1 for _x in logros_calc if _x[1])
    st.markdown(
        f'<div style="background:rgba(212,175,55,.08);border:1px solid rgba(212,175,55,.25);'
        f'border-radius:10px;padding:8px 14px;margin-bottom:8px;font-size:12px;color:rgba(255,221,122,.85);">'
        f'🏅 <b>{_n_on}/{len(logros_calc)}</b> logros desbloqueados'
        + ('' if st.session_state.get("_perfil_logros_open") else ' — tocá <b>👁️ Ver</b> arriba para verlos todos')
        + '</div>', unsafe_allow_html=True)

    # Render in chunks of 7 to avoid Streamlit truncation — solo si está abierto
    _logro_chunks = [logros_calc[i:i+7] for i in range(0, len(logros_calc), 7)] if st.session_state.get("_perfil_logros_open") else []
    for _chunk in _logro_chunks:
        _chunk_html = '<div class="logro-grid">'
        for logro_def, desbloqueado, _gp_logro in _chunk:
            lid, emo, name, desc, _ = logro_def
            cls2 = "on" if desbloqueado else "off"
            lock2 = "" if desbloqueado else '<span class="logro-lock">🔒</span>'
            name_s2 = _html_logro.escape(str(name))
            desc_s2 = _html_logro.escape(str(desc))
            gp_badge2 = (f'<div style="font-size:8px;color:rgba(74,222,128,.7);margin-top:3px;">'
                         f'Ganado en: {_html_logro.escape(_gp_logro)}</div>') if _gp_logro and desbloqueado else ""
            _chunk_html += (f'<div class="logro-card {cls2}">{lock2}'
                            f'<span class="logro-emo">{str(emo)}</span>'
                            f'<div class="logro-name">{name_s2}</div>'
                            f'<div class="logro-desc">{desc_s2}</div>'
                            f'{gp_badge2}</div>')
        _chunk_html += '</div>'
        st.markdown(_chunk_html, unsafe_allow_html=True)

    # Racha personal
    if df_p is not None and not df_p.empty:
        _ra = _racha_actual(df_p.rename(columns={"pts":"puntos"}))
        _rm = _racha_calc(df_p.rename(columns={"pts":"puntos"}))
        if _ra >= 1:
            fire = "🔥"*min(_ra,5)
            st.markdown(
                f'<div style="background:rgba(255,140,0,.08);border:1px solid rgba(255,140,0,.3);'
                f'border-radius:12px;padding:10px 16px;display:flex;align-items:center;gap:12px;">'
                f'<span style="font-size:28px;">{fire}</span>'
                f'<div><div style="font-size:14px;font-weight:900;color:#ffdd7a;">Racha activa: {_ra} GP{"s" if _ra!=1 else ""}</div>'
                f'<div style="font-size:11px;color:rgba(169,178,214,.55);">Mejor racha histórica: {_rm} GPs</div>'
                f'</div></div>', unsafe_allow_html=True)



    # ── Historial de predicciones propias ────────────────────
    st.markdown('<div id="fw-preds-anchor"></div>'
                '<div class="prof-sec-title" style="margin-top:22px;">📋 PREDICCIONES TEMPORADA COMPLETA</div>',
                unsafe_allow_html=True)
    _cap_c1, _cap_c2 = st.columns([2, 3])
    with _cap_c1:
        if st.button("📋 Cargar mis predicciones", key="prof_all_preds_btn", use_container_width=True):
            st.session_state["prof_load_all_preds"] = True
            st.session_state["_scroll_to_preds"] = True
    # Si se acaba de cargar, scrollear de vuelta a la sección (evita el salto arriba)
    if st.session_state.get("_scroll_to_preds"):
        components.html("""<script>
        function _fwScroll(tries){
            try{
                var doc = window.parent.document;
                var el = doc.getElementById('fw-preds-anchor');
                if(el){ el.scrollIntoView({behavior:'smooth', block:'start'}); return; }
            }catch(e){}
            if(tries>0){ setTimeout(function(){_fwScroll(tries-1);}, 200); }
        }
        _fwScroll(15);
        </script>""", height=0)
        st.session_state["_scroll_to_preds"] = False
    if st.session_state.get("prof_load_all_preds", False):
        _m_pa = _mod_db()
        if "_error" not in _m_pa:
            _gps_done_pa = [g for g in GPS_ACTIVOS
                            if df_p is not None and g in df_p.get("gp",pd.Series(dtype=str)).values]
            if not _gps_done_pa:
                st.info("Sin GPs computados todavía.")
            else:
                _ESCALA_Q2={1:15,2:10,3:7,4:5,5:3}
                _ESCALA_R2={1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}
                _ESCALA_S2={1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1}
                _ESCALA_C2={1:10,2:5,3:2}

                def _row_pa(pos, pv, esc, pts_remaining_ref, acerto_flag):
                    if not pv: return ""
                    if acerto_flag:
                        bg="rgba(74,222,128,.1)"; brd="rgba(74,222,128,.35)"; nc="#D4AF37"
                        tick=f'<span style="color:#4ade80;font-size:10px;font-weight:900;">✅+{esc}pts</span>'
                    else:
                        bg="rgba(255,255,255,.02)"; brd="rgba(255,255,255,.06)"; nc="rgba(232,236,255,.6)"
                        tick='<span style="color:rgba(239,68,68,.5);font-size:10px;">❌</span>'
                    return (f'<div style="display:flex;align-items:center;gap:6px;background:{bg};'
                            f'border:1px solid {brd};border-radius:8px;padding:4px 9px;margin-bottom:2px;">'
                            f'<span style="font-size:9px;color:rgba(169,178,214,.4);min-width:20px;">P{pos}</span>'
                            f'<span style="font-size:11px;font-weight:800;color:{nc};flex:1;">{pv}</span>'
                            f'{tick}</div>')

                def _guess_aciertos(pred_d, esc, pts_total, oficial_d=None, pfx="r"):
                    """Compare each prediction against official result. Falls back to greedy if no official."""
                    res = {}
                    if oficial_d:
                        # Real comparison against official results
                        try:
                            from core.utils import normalizar_nombre as _nn_ag
                        except Exception:
                            _nn_ag = lambda x: str(x or "").strip().lower()
                        for p in sorted(esc.keys()):
                            v = pred_d.get(p, pred_d.get(str(p), ""))
                            if not v: res[p]=None; continue
                            rv = str(oficial_d.get(f"{pfx}{p}","")).strip()
                            res[p] = bool(rv and _nn_ag(str(v)) == _nn_ag(rv))
                        return res
                    # Fallback greedy
                    rem = pts_total
                    for p in sorted(esc.keys()):
                        v = pred_d.get(p,"")
                        if not v: res[p]=None; continue
                        if rem >= esc[p]: res[p]=True; rem-=esc[p]
                        else: res[p]=False
                    return res

                for _gp_pa in _gps_done_pa:
                    _gp_lpa = _gp_pa.split(". ",1)[-1] if ". " in _gp_pa else _gp_pa
                    _rpa = _safe_call(_m_pa["recuperar_predicciones_piloto"], usuario, _gp_pa,
                                      timeout_sec=12, default=(None,None,(None,None)))
                    _dqpa,_dspa,(_drpa,_dcpa) = _rpa
                    if not any([_dqpa, _dspa, _drpa]): continue

                    # Get pts for this GP
                    _row_pa_pts = df_p[df_p.get("gp",pd.Series(dtype=str)).astype(str)==_gp_pa] if df_p is not None else pd.DataFrame()
                    _total_pa = int(_row_pa_pts["pts"].iloc[0]) if not _row_pa_pts.empty else 0

                    # Get pts per etapa
                    _pa_etapa = {"QUALY":0,"CARRERA":0,"SPRINT":0,"CONSTRUCTORES":0}
                    if df_det is not None and not (hasattr(df_det,"empty") and df_det.empty):
                        try:
                            _dp = df_det.copy(); _dp.columns=[c.lower().strip() for c in _dp.columns]
                            _dp["puntos"]=pd.to_numeric(_dp["puntos"],errors="coerce").fillna(0)
                            _dp2 = _dp[(_dp.get("gp",pd.Series(dtype=str)).astype(str)==_gp_pa) &
                                       (_dp.get("piloto",pd.Series(dtype=str)).astype(str)==usuario)]
                            if not _dp2.empty and "etapa" in _dp2.columns:
                                for _ek in ["QUALY","CARRERA","SPRINT","CONSTRUCTORES"]:
                                    _pa_etapa[_ek]=float(_dp2[_dp2["etapa"].str.upper()==_ek]["puntos"].sum())
                        except Exception: pass

                    _clr_pa = PILOTO_COLORS.get(usuario,"#a855f7")

                    # Load oficial for exact aciertos — read from Oficial sheet directly
                    _oficial_pa = {}
                    try:
                        from core.database import conectar_google_sheets as _cgs_pa
                        _ws_of_pa = _cgs_pa("Oficial")
                        if _ws_of_pa:
                            _of_recs_pa = _ws_of_pa.get_all_records()
                            _gp_pa_bare = (_gp_pa.split(". ",1)[-1] if ". " in _gp_pa else _gp_pa).lower()
                            _gp_pa_bare = _gp_pa_bare.replace("gran premio de ","").replace("gran premio del ","").replace("gran premio ","")
                            for _r_of in _of_recs_pa:
                                _r_gp = str(_r_of.get("gp","")).strip()
                                _r_gp_b = (_r_gp.split(". ",1)[-1] if ". " in _r_gp else _r_gp).lower()
                                _r_gp_b = _r_gp_b.replace("gran premio de ","").replace("gran premio del ","").replace("gran premio ","")
                                if _gp_pa_bare[:6] in _r_gp_b or _r_gp_b[:6] in _gp_pa_bare:
                                    _et_of = str(_r_of.get("etapa","")).upper()
                                    _pos_of = _r_of.get("pos", _r_of.get("posicion",""))
                                    _pil_of = str(_r_of.get("piloto","")).strip()
                                    try:
                                        _p_int = int(_pos_of)
                                        if _et_of == "CARRERA": _oficial_pa[f"r{_p_int}"] = _pil_of
                                        elif _et_of == "QUALY": _oficial_pa[f"q{_p_int}"] = _pil_of
                                        elif _et_of == "CONSTRUCTORES": _oficial_pa[f"c{_p_int}"] = _pil_of
                                        elif _et_of == "SPRINT": _oficial_pa[f"s{_p_int}"] = _pil_of
                                    except: pass
                                    if "COLAPINTO" in _et_of:
                                        if "Q" in _et_of: _oficial_pa["col_q"] = str(_pos_of)
                                        else: _oficial_pa["col_r"] = str(_pos_of)
                    except Exception: pass

                    with st.expander(
                        f"🏁 {_gp_lpa}{'  ⚡' if _gp_pa in GPS_SPRINT else ''}  —  {_total_pa} pts",
                        expanded=False):

                        _pc1,_pc2 = st.columns(2)
                        with _pc1:
                            if _dqpa:
                                _ac_qpa = _guess_aciertos(_dqpa, _ESCALA_Q2, _pa_etapa["QUALY"],
                                                              oficial_d=_oficial_pa, pfx="q")
                                st.markdown(f'<div style="font-size:10px;font-weight:800;color:rgba(246,195,73,.7);margin-bottom:4px;">⏱️ QUALY <span style="color:#4ade80;">+{int(_pa_etapa["QUALY"])}pts</span></div>', unsafe_allow_html=True)
                                _h = "".join(_row_pa(i,_dqpa.get(i,""),_ESCALA_Q2.get(i,0),None,_ac_qpa.get(i,False)) for i in range(1,6))
                                if _h: st.markdown(_h, unsafe_allow_html=True)
                                # Colapinto qualy
                                _cq_pa = str(_dqpa.get("colapinto_q","")).strip()
                                if _cq_pa:
                                    _cqr = str(_oficial_pa.get("col_q","")).strip()
                                    _cq_ok = bool(_cqr and str(_cq_pa)==str(_cqr))
                                    _cq_pts_disp = " (+10pts)" if _cq_ok else ""
                                    _cq_col = "#4ade80" if _cq_ok else "rgba(169,178,214,.5)"
                                    _cq_bg = "background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);" if _cq_ok else ""
                                    st.markdown(f'<div style="font-size:11px;color:{_cq_col};padding:4px 8px;border-radius:8px;{_cq_bg}margin-top:4px;">' +
                                                f'🇦🇷 Colapinto Qualy: P{_cq_pa} {"✅"+_cq_pts_disp if _cq_ok else "❌ (esperado: P"+_cqr+")" if _cqr else "⏳"}</div>',
                                                unsafe_allow_html=True)
                            if _dspa and _gp_pa in GPS_SPRINT:
                                _ac_spa = _guess_aciertos(_dspa, _ESCALA_S2, _pa_etapa["SPRINT"],
                                                              oficial_d=_oficial_pa, pfx="s")
                                st.markdown(f'<div style="font-size:10px;font-weight:800;color:rgba(246,195,73,.7);margin:6px 0 4px;">⚡ SPRINT <span style="color:#4ade80;">+{int(_pa_etapa["SPRINT"])}pts</span></div>', unsafe_allow_html=True)
                                _h = "".join(_row_pa(i,_dspa.get(i,""),_ESCALA_S2.get(i,0),None,_ac_spa.get(i,False)) for i in range(1,9))
                                if _h: st.markdown(_h, unsafe_allow_html=True)
                        with _pc2:
                            if _drpa:
                                _ac_rpa = _guess_aciertos(_drpa, _ESCALA_R2, _pa_etapa["CARRERA"],
                                                              oficial_d=_oficial_pa, pfx="r")
                                st.markdown(f'<div style="font-size:10px;font-weight:800;color:rgba(246,195,73,.7);margin-bottom:4px;">🏁 CARRERA <span style="color:#4ade80;">+{int(_pa_etapa["CARRERA"])}pts</span></div>', unsafe_allow_html=True)
                                _h = "".join(_row_pa(i,_drpa.get(i,""),_ESCALA_R2.get(i,0),None,_ac_rpa.get(i,False)) for i in range(1,11))
                                if _h: st.markdown(_h, unsafe_allow_html=True)
                                # Colapinto carrera
                                _cr_pa = str(_drpa.get("colapinto_r","")).strip()
                                if _cr_pa:
                                    _crr = str(_oficial_pa.get("col_r","")).strip()
                                    _cr_ok = bool(_crr and str(_cr_pa)==str(_crr))
                                    _cr_pts_disp = " (+20pts)" if _cr_ok else ""
                                    _cr_col = "#4ade80" if _cr_ok else "rgba(169,178,214,.5)"
                                    _cr_bg = "background:rgba(74,222,128,.1);border:1px solid rgba(74,222,128,.3);" if _cr_ok else ""
                                    st.markdown(f'<div style="font-size:11px;color:{_cr_col};padding:4px 8px;border-radius:8px;{_cr_bg}margin-top:4px;">' +
                                                f'🇦🇷 Colapinto Carrera: P{_cr_pa} {"✅"+_cr_pts_disp if _cr_ok else "❌ (esperado: P"+_crr+")" if _crr else "⏳"}</div>',
                                                unsafe_allow_html=True)
                            if _dcpa:
                                _ac_cpa = _guess_aciertos(_dcpa, _ESCALA_C2, _pa_etapa["CONSTRUCTORES"],
                                                              oficial_d=_oficial_pa, pfx="c")
                                st.markdown(f'<div style="font-size:10px;font-weight:800;color:rgba(246,195,73,.7);margin:6px 0 4px;">🏗️ CONSTRUCTORES <span style="color:#4ade80;">+{int(_pa_etapa["CONSTRUCTORES"])}pts</span></div>', unsafe_allow_html=True)
                                _h = "".join(_row_pa(i,_dcpa.get(i,""),_ESCALA_C2.get(i,0),None,_ac_cpa.get(i,False)) for i in range(1,4))
                                if _h: st.markdown(_h, unsafe_allow_html=True)

    # ── Exportar historial completo ──────────────────────────────────
    st.markdown('<div class="prof-sec-title" style="margin-top:22px;">📥 EXPORTAR MIS DATOS</div>',
                unsafe_allow_html=True)
    st.caption("Excel: hoja por GP con predicciones, resultado oficial, ✅/❌ y puntos. Incluye Colapinto.")
    try:
        import io as _io_exp
        _exp_key = f"export_buf_{usuario}"
        _col_exp1, _col_exp2 = st.columns([2,3])
        with _col_exp1:
            if st.button("📊 Generar Excel", key="prof_dl_btn", use_container_width=True):
                _m_exp = _mod_db()
                if "_error" not in _m_exp:
                    with st.spinner("Generando Excel..."):
                        _buf_exp = _io_exp.BytesIO()
                        _EQ={1:15,2:10,3:7,4:5,5:3}; _ER={1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}
                        _ES={1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1}; _EC={1:10,2:5,3:2}
                        _sheets = 0
                        with pd.ExcelWriter(_buf_exp, engine="openpyxl") as _xw:
                            if df_p is not None and not df_p.empty:
                                _res_df = df_p.rename(columns={"gp":"GP","pts":"Puntos"}).copy()
                                _res_df["GP"] = _res_df["GP"].apply(lambda x: str(x).split(". ",1)[-1] if ". " in str(x) else str(x))
                                _res_df.insert(0,"Formulero",usuario)
                                _res_df.to_excel(_xw, sheet_name="Resumen", index=False)
                            # Load ALL official results from Oficial sheet ONCE (much faster)
                            _of_all_xl = {}  # dict: gp_bare -> {r1:piloto, q1:piloto, ...}
                            try:
                                from core.database import conectar_google_sheets as _cgs_xl2
                                _ws_xl2 = _cgs_xl2("Oficial")
                                if _ws_xl2:
                                    for _rxl in _ws_xl2.get_all_records():
                                        _gp_xl = str(_rxl.get("gp","")).strip()
                                        _gp_xl_b = (_gp_xl.split(". ",1)[-1] if ". " in _gp_xl else _gp_xl).lower()
                                        if _gp_xl_b not in _of_all_xl: _of_all_xl[_gp_xl_b] = {}
                                        _et_xl2 = str(_rxl.get("etapa","")).upper()
                                        _pos_xl2 = _rxl.get("pos",""); _pil_xl2 = str(_rxl.get("piloto","")).strip()
                                        try:
                                            _p2 = int(_pos_xl2)
                                            if _et_xl2=="CARRERA": _of_all_xl[_gp_xl_b][f"r{_p2}"] = _pil_xl2
                                            elif _et_xl2=="QUALY": _of_all_xl[_gp_xl_b][f"q{_p2}"] = _pil_xl2
                                            elif _et_xl2=="CONSTRUCTORES": _of_all_xl[_gp_xl_b][f"c{_p2}"] = _pil_xl2
                                            elif _et_xl2=="SPRINT": _of_all_xl[_gp_xl_b][f"s{_p2}"] = _pil_xl2
                                        except: pass
                                        if "COLAPINTO" in _et_xl2:
                                            if "Q" in _et_xl2: _of_all_xl[_gp_xl_b]["col_q"] = str(_pos_xl2)
                                            else: _of_all_xl[_gp_xl_b]["col_r"] = str(_pos_xl2)
                            except Exception: pass
                            # Use ALL GPS_ACTIVOS that have predictions (not just those in df_p)
                            _gps_x = [g for g in GPS_ACTIVOS if g not in GPS_SUSPENDIDOS]
                            for _gp_x in _gps_x:
                                _gp_lx = _gp_x.split(". ",1)[-1] if ". " in _gp_x else _gp_x
                                _sn = _gp_lx[:25].replace("/","-").replace("?","")
                                try:
                                    _rp = _safe_call(_m_exp["recuperar_predicciones_piloto"], usuario, _gp_x, timeout_sec=8, default=(None,None,(None,None)))
                                    _dq,_ds,(_dr,_dc) = _rp
                                    if not any([_dq, _ds, _dr, _dc]): continue  # skip empty GPs
                                    # Get oficial from pre-loaded dict — flexible matching
                                    _gp_lx_low = _gp_lx.lower()
                                    # Strip common prefixes for matching
                                    _gp_bare_xl = (_gp_lx_low
                                        .replace("gran premio de ","").replace("gran premio del ","")
                                        .replace("gran premio ","").replace("grand prix ","").strip())
                                    _of = {}
                                    for _k_of, _v_of in _of_all_xl.items():
                                        _k_bare = (_k_of
                                            .replace("gran premio de ","").replace("gran premio del ","")
                                            .replace("gran premio ","").replace("grand prix ","").strip())
                                        if (_gp_bare_xl[:6] in _k_bare or _k_bare[:6] in _gp_bare_xl
                                                or _gp_lx_low[:8] in _k_of or _k_of[:8] in _gp_lx_low):
                                            _of = _v_of; break
                                    _rows = []
                                    def _axr(pd2, esc, lab, pfx, n, od):
                                        if not pd2: return
                                        for _p in range(1,n+1):
                                            # Try both int key and str key
                                            _pv = str(pd2.get(_p, pd2.get(str(_p), ""))).strip()
                                            if not _pv: continue
                                            _rv = str(od.get(f"{pfx}{_p}","")).strip()
                                            _ok = bool(_rv and (_rv.lower() in _pv.lower() or _pv.lower() in _rv.lower()))
                                            _rows.append({"GP":_gp_lx,"Etapa":lab,"Pos":f"P{_p}",
                                                          "Tu predicción":_pv,
                                                          "Resultado real":_rv if _rv else "Pendiente",
                                                          "Acierto":"✅" if _ok else ("❌" if _rv else "Sin datos"),
                                                          "Puntos":esc.get(_p,0) if _ok else 0})
                                    _axr(_dq,_EQ,"QUALY","q",5,_of)
                                    # Sprint: normalize keys and include if GP is sprint
                                    if _gp_x in GPS_SPRINT:
                                        _ds_norm = {}
                                        if isinstance(_ds, dict) and _ds:
                                            for _k,_v in _ds.items():
                                                try: _ds_norm[int(_k)] = _v
                                                except:
                                                    try: _ds_norm[int(str(_k))] = _v
                                                    except: pass
                                        if _ds_norm:
                                            _axr(_ds_norm, _ES, "SPRINT", "s", 8, _of)
                                    _axr(_dr,_ER,"CARRERA","r",10,_of)
                                    _axr(_dc,_EC,"CONSTRUCTORES","c",3,_of)
                                    for _cetapa,_cfield,_crkey,_cpts in [("COLAPINTO Q","colapinto_q","col_q",10),("COLAPINTO R","colapinto_r","col_r",20)]:
                                        _psrc2 = _dq if "Q" in _cetapa else _dr
                                        if _psrc2:
                                            _cv2 = str(_psrc2.get(_cfield,"") or _psrc2.get(_crkey,"")).strip()
                                            _cr3 = str(_of.get(_crkey,"")).strip()
                                            if _cv2:
                                                _cok2 = "✅" if (_cr3 and _cv2==_cr3) else ("❌" if _cr3 else "Sin datos")
                                                _rows.append({"GP":_gp_lx,"Etapa":_cetapa,"Pos":"—",
                                                              "Tu predicción":f"P{_cv2}",
                                                              "Resultado real":f"P{_cr3}" if _cr3 else "Pendiente",
                                                              "Acierto":_cok2,"Puntos":_cpts if _cok2=="✅" else 0})
                                    if _rows:
                                        _df_x = pd.DataFrame(_rows)
                                        _total = _df_x["Puntos"].sum()
                                        _total_row = pd.DataFrame([{"GP":"","Etapa":"","Pos":"","Tu predicción":"","Resultado real":"TOTAL","Acierto":"→","Puntos":int(_total)}])
                                        pd.concat([_df_x,_total_row],ignore_index=True).to_excel(_xw,sheet_name=_sn,index=False)
                                        _sheets += 1
                                except Exception: pass
                        _buf_exp.seek(0)
                        st.session_state[_exp_key] = _buf_exp.getvalue()
                    st.success(f"✅ Excel listo: {_sheets} GPs + hoja Resumen")
                    if _sheets == 0:
                        st.warning("⚠️ No se pudo escribir ningún GP. Posibles causas:\n"
                                   "1. La hoja 'Oficial' no tiene datos — corré cargar_resultados_oficiales.py\n"
                                   "2. El nombre del GP en Oficial no coincide con las predicciones")
        with _col_exp2:
            if st.session_state.get(_exp_key):
                st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
                st.download_button("⬇️ Bajar", st.session_state[_exp_key],
                    file_name=f"FefeWolf_{usuario.replace(' ','_')}_2026.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True, key="prof_dl_hist")
    except Exception as _exp_e:
        st.caption(f"Export no disponible: {_exp_e}")

def _check_and_send_reminders():
    """
    Recordatorios automáticos por email — 4 ventanas:
      · Apertura  : predicciones ABIERTAS (72h antes del cierre = open_str)
      · 12h antes : quedan 12 horas
      · 1h antes  : cierre inminente (1h)
      · cierre exacto: último aviso (0.25h)
    Requiere en secrets.toml:
      next_gp_name       = "GP Japón"
      next_gp_close_utc  = "2026-03-28 01:00"   # cierre UTC (1h antes de la carrera)
      next_gp_open_utc   = "2026-03-25 01:00"    # apertura UTC (72h antes)
      emails             = {usuario: email, ...}
      GMAIL_USER / GMAIL_APP_PASSWORD  (preferido)
      o SENDGRID_API_KEY / SENDGRID_FROM
    """
    try:
        from datetime import datetime, timezone
        import smtplib
        from email.mime.text import MIMEText

        emails    = st.secrets.get("emails", {})
        gp_name   = st.secrets.get("next_gp_name", "GP siguiente")
        close_str = st.secrets.get("next_gp_close_utc", "")
        open_str  = st.secrets.get("next_gp_open_utc", "")
        gm_u  = st.secrets.get("GMAIL_USER", "")
        gm_p  = st.secrets.get("GMAIL_APP_PASSWORD", "")
        api_k = st.secrets.get("SENDGRID_API_KEY", "")
        from_em = st.secrets.get("SENDGRID_FROM", "")

        if not close_str or not emails: return
        if not gm_u and not api_k: return

        now = datetime.now(timezone.utc)
        t_close = datetime.strptime(close_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        diff_h  = (t_close - now).total_seconds() / 3600

        # ── Detectar qué ventana aplica ──────────────────────────────────
        send_open = False
        if open_str:
            try:
                t_open = datetime.strptime(open_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                diff_open_h = (now - t_open).total_seconds() / 3600
                # Ventana: hasta 1.5h después de la apertura
                send_open = 0 <= diff_open_h <= 1.5
            except Exception: pass

        send_12 = 11.5 <= diff_h <= 12.5
        send_1  = 0.75 <= diff_h <= 1.25

        if not send_open and not send_12 and not send_1: return

        if send_open:
            tag = "open"; asunto_lbl = "🟢 ¡YA ABRIERON las predicciones"
            cuerpo_lbl = "Las predicciones están ABIERTAS. ¡Entrá y cargá tu pronóstico!"
            icon = "🟢"; color_border = "rgba(34,197,94,.4)"; color_title = "#4ade80"
        elif send_12:
            tag = "12h"; asunto_lbl = "⏰ Quedan 12 horas"
            cuerpo_lbl = "Faltan solo 12 horas para que cierren las predicciones."
            icon = "⏰"; color_border = "rgba(251,191,36,.4)"; color_title = "#fbbf24"
        else:
            tag = "1h"; asunto_lbl = "🔴 ¡ÚLTIMO AVISO! Queda 1 hora"
            cuerpo_lbl = "Las predicciones cierran en <b>1 HORA</b>. ¡Es ahora o nunca!"
            icon = "🔴"; color_border = "rgba(255,64,64,.4)"; color_title = "#fca5a5"

        flag_key = f"_rem_sent_{tag}_{close_str[:10]}"
        if st.session_state.get(flag_key): return
        st.session_state[flag_key] = True

        def _send_one(dest_email, usr):
            subject = f"{asunto_lbl} — {gp_name} | Torneo Fefe Wolf 2026"
            body_html = f"""<div style="background:#07091a;padding:24px;font-family:Inter,sans-serif;
              border-radius:14px;max-width:500px;margin:auto;">
              <div style="text-align:center;margin-bottom:16px;">
                <span style="font-size:32px;">{icon}</span>
                <div style="font-size:20px;font-weight:900;color:#ffdd7a;margin-top:6px;">TORNEO FEFE WOLF 2026</div>
              </div>
              <div style="background:rgba(255,255,255,.04);border:1px solid {color_border};
                border-radius:12px;padding:16px;margin-bottom:14px;">
                <div style="font-size:17px;font-weight:900;color:{color_title};">{asunto_lbl}</div>
                <div style="font-size:13px;color:rgba(232,236,255,.85);margin-top:8px;">
                  Hola <b style="color:#ffdd7a;">{usr}</b>,<br>{cuerpo_lbl}<br><br>
                  Gran Premio: <b style="color:#ffdd7a;">{gp_name}</b><br>
                  Cierre: <b>{close_str} UTC</b>
                </div>
              </div>
              <div style="text-align:center;margin-top:16px;">
                <a href="https://torneofefewolf2026.streamlit.app" target="_blank"
                  style="background:linear-gradient(90deg,#8a6c0a,#d4af37);color:#1a1000;
                  font-weight:900;padding:10px 28px;border-radius:10px;text-decoration:none;
                  font-size:14px;display:inline-block;">🏎️ Cargar predicción</a>
              </div>
              <div style="text-align:center;margin-top:14px;font-size:10px;color:rgba(169,178,214,.35);">
                🏁 Torneo Fefe Wolf 2026 · torneofefewolf2026.streamlit.app
              </div></div>"""
            body_txt = f"{asunto_lbl}\n\nHola {usr},\n{cuerpo_lbl}\n\nGP: {gp_name}\nCierre: {close_str} UTC\n\nhttps://torneofefewolf2026.streamlit.app"
            try:
                if gm_u and gm_p:
                    _m = MIMEText(body_txt, "plain", "utf-8")
                    _m["Subject"] = subject
                    _m["From"]    = f"Torneo Fefe Wolf <{gm_u}>"
                    _m["To"]      = dest_email
                    _sent = False
                    try:
                        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as _srv:
                            _srv.login(gm_u, gm_p); _srv.sendmail(gm_u, dest_email, _m.as_string())
                        _sent = True
                    except Exception: pass
                    if not _sent:
                        with smtplib.SMTP("smtp.gmail.com", 587) as _srv2:
                            _srv2.ehlo(); _srv2.starttls(); _srv2.ehlo()
                            _srv2.login(gm_u, gm_p); _srv2.sendmail(gm_u, dest_email, _m.as_string())
                elif api_k and from_em:
                    import requests as _rq
                    _rq.post("https://api.sendgrid.com/v3/mail/send",
                        json={"personalizations":[{"to":[{"email":dest_email}]}],
                              "from":{"email":from_em,"name":"Torneo Fefe Wolf"},
                              "subject":subject,
                              "content":[{"type":"text/html","value":body_html}]},
                        timeout=5,
                        headers={"Authorization":f"Bearer {api_k}","Content-Type":"application/json"})
            except Exception: pass

        for usr, em in emails.items():
            if em: _send_one(str(em), str(usr))
    except Exception: pass  # Never crash the app




# ─────────────────────────────────────────────────────────
# LOGROS / ACHIEVEMENTS
# ─────────────────────────────────────────────────────────
_LOGROS_DEF = [
    # Umbrales calibrados: ~80-95pts por GP es un buen resultado
    # ── QUALY ────────────────────────────────────────────────────────────
    ("maestro_pole",  "⏱️", "Maestro de la Pole",
     "20+ pts en Qualy en un solo GP (top 5 perfecto + bonus + Colapinto)",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and any(d[d["etapa"].str.upper()=="QUALY"]["puntos"] >= 20))),
    ("qualy_flawless","🎯", "Francotirador",
     "25+ pts en Qualy en 3 GPs distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="QUALY") & (d["puntos"] >= 25)]) >= 3)),
    ("qualy_pro",     "📐", "Especialista de Clasificación",
     "15+ pts de Qualy en 6 GPs distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="QUALY") & (d["puntos"] >= 15)]) >= 6)),
    # ── CARRERA ──────────────────────────────────────────────────────────
    ("visionario",    "🔮", "Visionario",
     "55+ pts en Carrera en un solo GP (predijo casi todo el top 10)",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and any(d[d["etapa"].str.upper()=="CARRERA"]["puntos"] >= 55))),
    ("race_pro",      "🏎️", "El Estratega",
     "40+ pts de Carrera en 5 GPs distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="CARRERA") & (d["puntos"] >= 40)]) >= 5)),
    ("podio_hunter",  "🎪", "Cazador de Podios",
     "30+ pts de Carrera en 10 GPs distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="CARRERA") & (d["puntos"] >= 30)]) >= 10)),
    # ── SPRINT ───────────────────────────────────────────────────────────
    ("rey_sprint",    "⚡", "Rey del Sprint",
     "18+ pts de Sprint en un GP (casi top 8 exacto)",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and any(d[d["etapa"].str.upper()=="SPRINT"]["puntos"] >= 18))),
    ("sprint_master", "⚡🏆","Maestro del Sprint",
     "14+ pts de Sprint en 4 GPs de Sprint distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="SPRINT") & (d["puntos"] >= 14)]) >= 4)),
    # ── CONSTRUCTORES ────────────────────────────────────────────────────
    ("guru_const",    "🛠️", "Gurú de Constructores",
     "15+ pts de Constructores en un GP (pleno + bonus)",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and any(d[d["etapa"].str.upper()=="CONSTRUCTORES"]["puntos"] >= 15))),
    ("const_elite",   "🏗️", "Arquitecto de Equipos",
     "12+ pts de Constructores en 7 GPs distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="CONSTRUCTORES") & (d["puntos"] >= 12)]) >= 7)),
    # ── RACHAS ───────────────────────────────────────────────────────────
    ("hat_trick",     "🎩", "Tres en Raya",
     "5+ GPs consecutivos con 60+ pts cada uno",
     lambda h,d,n: bool(h is not None and len(h) >= 5 and
                   any(all(h.sort_values("gp")["puntos"].iloc[i:i+5] >= 60)
                       for i in range(max(1,len(h)-4))))),
    ("racha5",        "🔥", "Fuego Sagrado",
     "Racha histórica de 8+ GPs consecutivos",
     lambda h,d,n: bool(h is not None and not h.empty and _racha_calc(h) >= 8)),
    ("racha10",       "🌋", "Volcán Inagotable",
     "Racha histórica de 15+ GPs consecutivos",
     lambda h,d,n: bool(h is not None and not h.empty and _racha_calc(h) >= 15)),
    ("en_llamas",     "🔥🔥","En Llamas",
     "Racha ACTIVA de 5+ GPs seguidos con 50+ pts c/u",
     lambda h,d,n: bool(h is not None and len(h) >= 5 and
                   _racha_actual(h) >= 5 and
                   all(h.sort_values("gp")["puntos"].tail(5) >= 50))),
    # ── PUNTOS TOTALES ────────────────────────────────────────────────────
    ("century",       "💯", "El Centenario",
     "Superó los 200 puntos acumulados en la temporada",
     lambda h,d,n: bool(h is not None and not h.empty and h["puntos"].sum() >= 200)),
    ("double_c",      "🏅", "Doble Centuria",
     "Superó los 400 puntos acumulados",
     lambda h,d,n: bool(h is not None and not h.empty and h["puntos"].sum() >= 400)),
    ("triple_c",      "💎", "Triple Centuria",
     "Superó los 600 puntos — dominio absoluto",
     lambda h,d,n: bool(h is not None and not h.empty and h["puntos"].sum() >= 600)),
    ("top1",          "👑", "Líder Indiscutible",
     "300+ puntos acumulados — territorio del campeón",
     lambda h,d,n: bool(h is not None and not h.empty and h["puntos"].sum() >= 300)),
    # ── GP INDIVIDUAL ────────────────────────────────────────────────────
    ("comeback",      "🚀", "GP Perfecto",
     "95+ pts en un solo GP (actuación casi sin fallas)",
     lambda h,d,n: bool(h is not None and not h.empty and h["puntos"].max() >= 95)),
    ("cazador",       "🎲", "El Supremo",
     "115+ pts en un solo GP (prácticamente imposible)",
     lambda h,d,n: bool(h is not None and not h.empty and h["puntos"].max() >= 115)),
    # ── CONSISTENCIA ─────────────────────────────────────────────────────
    ("sin_cero",      "✨", "Sin Piedad",
     "Nunca menos de 40 pts en ningún GP — 10+ GPs",
     lambda h,d,n: bool(h is not None and not h.empty and len(h) >= 10 and all(h["puntos"] >= 40))),
    ("mejora",        "📈", "En Ascenso",
     "Sus últimos 4 GPs superan en promedio a los 4 anteriores",
     lambda h,d,n: bool(h is not None and len(h) >= 8
                   and h.sort_values("gp")["puntos"].iloc[-4:].mean()
                   > h.sort_values("gp")["puntos"].iloc[-8:-4].mean())),
    ("constante",     "📊", "El Más Constante",
     "No faltó a ningún GP Y promedio 65+ pts por GP",
     lambda h,d,n: bool(n > 0 and h is not None and not h.empty and
                   len(h) >= n and h["puntos"].mean() >= 65)),
    # ── PARTICIPACIÓN ────────────────────────────────────────────────────
    ("maratonista",   "🏃", "Maratonista",
     "Participó en 14+ GPs de la temporada",
     lambda h,d,n: bool(h is not None and not h.empty and len(h) >= 14)),
    ("veterano",      "🎖️", "Veterano de Pista",
     "Completó los 22 GPs de la temporada completa",
     lambda h,d,n: bool(h is not None and not h.empty and len(h) >= 22)),
    # ── DOMINIO TOTAL ────────────────────────────────────────────────────
    ("all_rounder",   "⭐", "Todo Terreno",
     "Sumó pts en Qualy+Carrera+Const en 4 GPs distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns and "gp" in d.columns
                   and len([_gp for _gp in d["gp"].unique()
                       if len(set(d[d["gp"]==_gp]["etapa"].str.upper().tolist()) & {"QUALY","CARRERA","CONSTRUCTORES"}) >= 3]) >= 4)),
    ("dominator",     "👑", "Dominador Total",
     "500+ pts acumulados Y 90+ pts en el mejor GP",
     lambda h,d,n: bool(h is not None and not h.empty
                   and h["puntos"].sum() >= 500 and h["puntos"].max() >= 90)),
    # ── 4 LOGROS NUEVOS ──────────────────────────────────────────────────
    ("hat_trick_gps", "🎖️🎖️","Triple Corona",
     "Fue el máximo anotador en 3+ GPs de la temporada",
     lambda h,d,n: False),  # Calculado en _calc_logros con gps_ganados >= 3
    ("perfecto_qualy","🔮⏱️","Qualy Infalible",
     "30+ pts en Qualy en un mismo GP (top 5 + bonus + Colapinto exacto)",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and any(d[d["etapa"].str.upper()=="QUALY"]["puntos"] >= 30))),
    ("sprint_streak", "⚡⚡","Sprint Devastador",
     "Puntos de Sprint en 5 GPs de Sprint consecutivos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="SPRINT") & (d["puntos"] > 0)]) >= 5)),
    ("perfecto",      "💎🏁","Ronda Perfecta",
     "Pleno exacto en Qualy+Carrera en el mismo GP — asignado por el Comisario",
     lambda h,d,n: False),
    # ── STICKERS ESPECIALES ───────────────────────────────────────────
    ("sniper",        "🎯🔫","Sniper",
     "Acertó exactamente 3+ posiciones en un mismo GP — precisión brutal",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and any(d[d["etapa"].str.upper()=="QUALY"]["puntos"] >= 21))),
    ("vidente",       "🔮✨","El Vidente",
     "Predijo correctamente el ganador de Carrera en 3 GPs distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="CARRERA") & (d["puntos"] >= 25)]) >= 3)),
    ("sprint_king",   "⚡👑","Sprint King",
     "Mejor puntuación en Sprint en 4 GPs de Sprint distintos",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="SPRINT") & (d["puntos"] >= 12)]) >= 4)),
    ("constructor",   "🏗️🏆","Arquitecto Supremo",
     "Acertó el top 3 de Constructores completo en 3 GPs",
     lambda h,d,n: bool(d is not None and not d.empty and "etapa" in d.columns
                   and len(d[(d["etapa"].str.upper()=="CONSTRUCTORES") & (d["puntos"] >= 15)]) >= 3)),
    ("colap_fan",     "🇦🇷⭐","Fan de Colapinto",
     "Predijo la posición exacta de Colapinto en 5+ predicciones",
     lambda h,d,n: False),  # Requiere datos de aciertos Colapinto
    # ── DESAFÍOS ──────────────────────────────────────────────────────
    ("desafio_win5",  "⚔️", "Duelista",
     "Ganó 5 desafíos contra otros formuleros",
     lambda h,d,n: False),  # Calculado con datos de Desafios
    ("desafio_win10", "⚔️👑","Gladiador Invicto",
     "Ganó 10 desafíos sin perder ninguno, o 10 victorias seguidas",
     lambda h,d,n: False),  # Calculado con datos de Desafios
    ("desafio_play5", "🤝", "Retador Nato",
     "Participó en 5 desafíos (ganados o perdidos)",
     lambda h,d,n: False),  # Calculado con datos de Desafios
    ("desafio_play10","🔥⚔️","Guerrero de Pista",
     "Participó en 10 desafíos — nunca le esquiva a un duelo",
     lambda h,d,n: False),  # Calculado con datos de Desafios
    ("desafio_reject","🐔", "El Gallina",
     "Rechazó un desafío — la marca de los que no aceptan el duelo",
     lambda h,d,n: False),  # Calculado con datos de Desafios (medalla negativa)
]


def _racha_calc(df_user):
    """Calcula racha máxima de GPs consecutivos con puntos > 0."""
    if df_user is None or df_user.empty: return 0
    pts = list(df_user.sort_values("gp")["puntos"])
    best = cur = 0
    for p in pts:
        if p > 0: cur += 1; best = max(best,cur)
        else: cur = 0
    return best

def _racha_actual(df_user):
    """Calcula racha actual (últimos GPs consecutivos > 0)."""
    if df_user is None or df_user.empty: return 0
    pts = list(df_user.sort_values("gp")["puntos"])[::-1]
    cur = 0
    for p in pts:
        if p > 0: cur += 1
        else: break
    return cur

def _calc_desafio_stats(usuario):
    """Cuenta victorias, participaciones, rechazos, derrotas y mejor racha de victorias."""
    _wins = 0; _played = 0; _rejected = 0; _losses = 0
    _resueltos = []
    try:
        from core.database import conectar_google_sheets as _cgs_des
        _ws_des = _cgs_des("Desafios")
        if _ws_des:
            # Usar get_all_values para evitar error de headers duplicados
            _vals_des = _ws_des.get_all_values()
            if _vals_des and len(_vals_des) > 1:
                _hdr_des = [h.strip().lower() for h in _vals_des[0]]
                def _fi(name):
                    for _i,_h in enumerate(_hdr_des):
                        if _h == name: return _i
                    return None
                _i_ret = _fi("retador"); _i_riv = _fi("rival")
                _i_est = _fi("estado"); _i_gan = _fi("ganador")
                _i_ts  = _fi("ts_resuelto") or _fi("ts_creado")
                if _i_ret is None or _i_riv is None: raise ValueError("headers not found")
                for _rp in _vals_des[1:]:
                    if not any(c.strip() for c in _rp): continue
                    def _sv(ix): return _rp[ix].strip() if ix is not None and ix < len(_rp) else ""
                    _ret = _sv(_i_ret); _riv = _sv(_i_riv)
                    _est = _sv(_i_est).upper(); _gan = _sv(_i_gan)
                    _ts  = _sv(_i_ts)
                    if _ret != str(usuario).strip() and _riv != str(usuario).strip(): continue
                    if _est == "RESUELTO":
                        _played += 1
                        _es_gano = (_gan == str(usuario).strip())
                        _es_empate = (_gan in ("EMPATE",""))
                        if _es_gano: _wins += 1
                        elif not _es_empate: _losses += 1
                        if not _es_empate: _resueltos.append((_ts, _es_gano))
                    if _est == "RECHAZADO" and _riv == str(usuario).strip():
                        _rejected += 1
    except Exception: pass
    _best_streak = 0; _cur_streak = 0
    try:
        for _ts, _gano in sorted(_resueltos, key=lambda x: x[0]):
            if _gano: _cur_streak += 1; _best_streak = max(_best_streak, _cur_streak)
            else: _cur_streak = 0
    except Exception: pass
    return _wins, _played, _rejected, _losses, _best_streak

def _calc_logros(usuario, df_hist_all, df_det_all, n_gps_total):
    """Devuelve lista de (logro_def, desbloqueado:bool, gp_ganado:str)."""
    # Stats de desafíos (independientes del historial de GPs)
    _des_wins, _des_played, _des_rejected, _des_losses, _des_streak = _calc_desafio_stats(usuario)

    def _desafio_unlock(key):
        if key == "desafio_win5":  return _des_wins >= 5
        if key == "desafio_win10": return (_des_wins >= 10 and _des_losses == 0) or _des_streak >= 10
        if key == "desafio_play5": return _des_played >= 5
        if key == "desafio_play10":return _des_played >= 10
        if key == "desafio_reject":return _des_rejected >= 1
        return None

    if df_hist_all is None or df_hist_all.empty:
        # Sin historial de GPs, pero igual evaluamos los logros de desafíos
        _out = []
        for _l in _LOGROS_DEF:
            _du = _desafio_unlock(_l[0])
            _out.append((_l, bool(_du) if _du is not None else False, ""))
        return _out
    h = df_hist_all[df_hist_all["piloto"]==usuario].copy() if "piloto" in df_hist_all.columns else pd.DataFrame()
    d = df_det_all[df_det_all["piloto"]==usuario].copy() if (df_det_all is not None and not df_det_all.empty and "piloto" in df_det_all.columns) else None

    # Sort by GP to find when logros were first unlocked
    h_sorted = h.sort_values("gp") if not h.empty else h

    # GPs ganados para Triple Corona
    gps_ganados = 0
    gps_ganados_list = []
    try:
        if ("piloto" in df_hist_all.columns and "gp" in df_hist_all.columns
                and "puntos" in df_hist_all.columns):
            _df_all_pts = df_hist_all.copy()
            _df_all_pts["puntos"] = pd.to_numeric(_df_all_pts["puntos"],errors="coerce").fillna(0)
            _agg_all = _df_all_pts.groupby(["gp","piloto"],as_index=False)["puntos"].sum()
            for _gp_all, _grp_all in _agg_all.groupby("gp"):
                if len(_grp_all) < 2: continue
                _gs = _grp_all.sort_values("puntos",ascending=False)
                if float(_gs.iloc[0]["puntos"]) <= 0: continue
                if str(_gs.iloc[0]["piloto"]).strip() == str(usuario).strip():
                    gps_ganados += 1
                    gps_ganados_list.append(str(_gp_all))
    except Exception: pass

    def _gp_label(gp_str):
        s = str(gp_str)
        return s.split(". ",1)[-1] if ". " in s else s

    result = []
    for logro in _LOGROS_DEF:
        desbloqueado = False; gp_ganado = ""
        try:
            if logro[0] == "hat_trick_gps":
                desbloqueado = gps_ganados >= 3
                if desbloqueado and len(gps_ganados_list) >= 3:
                    gp_ganado = _gp_label(gps_ganados_list[2])
            elif logro[0] == "desafio_win5":
                desbloqueado = _des_wins >= 5
            elif logro[0] == "desafio_win10":
                desbloqueado = (_des_wins >= 10 and _des_losses == 0) or _des_streak >= 10
            elif logro[0] == "desafio_play5":
                desbloqueado = _des_played >= 5
            elif logro[0] == "desafio_play10":
                desbloqueado = _des_played >= 10
            elif logro[0] == "desafio_reject":
                desbloqueado = _des_rejected >= 1
            else:
                # Check each GP cumulatively to find first unlock
                for _i_gp in range(1, len(h_sorted)+1):
                    _h_partial = h_sorted.iloc[:_i_gp]
                    _d_partial = None
                    if d is not None and not d.empty and "gp" in d.columns:
                        _gps_so_far = set(_h_partial["gp"].astype(str).values)
                        _d_partial = d[d["gp"].astype(str).isin(_gps_so_far)]
                    try:
                        _unlocked = logro[4](_h_partial, _d_partial, _i_gp)
                    except Exception: _unlocked = False
                    if _unlocked:
                        desbloqueado = True
                        gp_ganado = _gp_label(_h_partial.iloc[-1]["gp"])
                        break
        except Exception: desbloqueado = False
        result.append((logro, desbloqueado, gp_ganado))
    return result


# ─────────────────────────────────────────────────────────
# ENCUESTA PRE-CARRERA
# ─────────────────────────────────────────────────────────
def pantalla_encuesta():
    usuario = (st.session_state.get("perfil") or {}).get("usuario","")
    m = _mod_db()

    st.markdown("""
    <style>
    @keyframes encG{0%,100%{box-shadow:0 0 20px rgba(99,102,241,.15);}50%{box-shadow:0 0 38px rgba(99,102,241,.3);}}
    .enc-hero{background:linear-gradient(145deg,rgba(7,9,22,.99),rgba(20,14,50,.99));
      border:1.5px solid rgba(99,102,241,.5);border-radius:22px;padding:26px 22px 20px;
      margin-bottom:18px;text-align:center;position:relative;overflow:hidden;
      animation:encG 3.5s ease-in-out infinite;}
    .enc-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
      background:linear-gradient(90deg,transparent,#6366f1,#a78bfa,#6366f1,transparent);}
    .enc-title{font-size:26px;font-weight:900;letter-spacing:.08em;
      background:linear-gradient(90deg,#a78bfa,#6366f1,#a78bfa);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
    .enc-sub{font-size:11px;color:rgba(169,178,214,.55);letter-spacing:.16em;margin-top:4px;}
    .enc-card{background:rgba(99,102,241,.07);border:1px solid rgba(99,102,241,.25);
      border-radius:16px;padding:18px 18px 14px;margin-bottom:14px;}
    .enc-q{font-size:14px;font-weight:800;color:#e8ecff;margin-bottom:12px;letter-spacing:.02em;}
    .enc-bar-wrap{height:10px;background:rgba(255,255,255,.06);border-radius:5px;overflow:hidden;flex:1;}
    .enc-result-row{display:flex;align-items:center;gap:10px;margin-bottom:7px;}
    .enc-opt-lbl{font-size:12px;color:#e8ecff;min-width:90px;}
    .enc-pct{font-size:12px;font-weight:800;color:#a78bfa;min-width:36px;text-align:right;}
    .enc-yours{font-size:10px;color:#ffdd7a;margin-left:4px;}
    </style>
    <div class="enc-hero">
      <div style="font-size:28px;margin-bottom:6px;">🗳️</div>
      <div class="enc-title">MINI-ENCUESTA PRE-CARRERA</div>
      <div class="enc-sub">¿Qué crees que pasará en el próximo GP?</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Preguntas dinámicas: 7 preguntas de predicción ───────────────
    preguntas = [
        {"id":"pole",  "q":"¿Quién sale desde la Pole Position?",
         "opts":["Verstappen","Norris","Russell","Leclerc","Piastri","Otro"]},
        {"id":"win",   "q":"¿Quién gana la carrera?",
         "opts":["Verstappen","Norris","Russell","Leclerc","Piastri","Otro"]},
        {"id":"podio3","q":"¿Qué equipo completa el podio? (3er lugar)",
         "opts":["Red Bull","Ferrari","McLaren","Mercedes","Aston Martin","Otro"]},
        {"id":"col",   "q":"¿Cómo termina Colapinto?",
         "opts":["Top 10","Top 6","Puntos justos (11-15)","Fuera de puntos","Abandono"]},
        {"id":"sc",    "q":"¿Habrá Safety Car en la carrera?",
         "opts":["Sí, 1 vez","Sí, 2+ veces","No","Solo VSC"]},
        {"id":"ret",   "q":"¿Cuántos abandonos habrá en total?",
         "opts":["0","1","2-3","4+"]},
        {"id":"fastest","q":"¿Quién marcará la vuelta rápida?",
         "opts":["Verstappen","Norris","Russell","Hamilton","Piastri","Otro"]},
    ]

    # Lee votos actuales de Google Sheets si está disponible
    def _leer_votos():
        try:
            if "_error" in m: return {}
            df = _safe_call(m.get("leer_encuesta", lambda: pd.DataFrame()), timeout_sec=5, default=pd.DataFrame())
            if df is None or (hasattr(df,"empty") and df.empty): return {}
            votos = {}
            for _, row in df.iterrows():
                key = f"{row.get('pregunta','')}||{row.get('opcion','')}"
                votos[key] = int(row.get("votos",0))
            return votos
        except Exception: return {}

    def _guardar_voto(pregunta_id, opcion, usuario):
        try:
            if "_error" in m or "guardar_voto_encuesta" not in m: return False
            return _safe_call(m["guardar_voto_encuesta"], pregunta_id, opcion, usuario, timeout_sec=5, default=False)
        except Exception: return False

    # Carga votos del session state (proxy si no hay backend)
    _svk = "enc_votos_local"
    if _svk not in st.session_state: st.session_state[_svk] = {}
    _my_votes = st.session_state.get("enc_mis_votos", {})

    for preg in preguntas:
        pid = preg["id"]; q = preg["q"]; opts = preg["opts"]
        my_vote = _my_votes.get(pid)

        with st.container():
            st.markdown(f"""<div class="enc-card"><div class="enc-q">🏎️ {q}</div></div>""",
                        unsafe_allow_html=True)

            if my_vote is None:
                _cols = st.columns(len(opts))
                for i, opt in enumerate(opts):
                    _opt_key = f"enc_v_{pid}_{i}"
                    with _cols[i]:
                        if st.button(opt, key=_opt_key, use_container_width=True):
                            if "enc_mis_votos" not in st.session_state:
                                st.session_state["enc_mis_votos"] = {}
                            st.session_state["enc_mis_votos"][pid] = opt
                            _lk = f"{pid}||{opt}"
                            st.session_state[_svk][_lk] = st.session_state[_svk].get(_lk,0)+1
                            _guardar_voto(pid, opt, usuario)
                            st.rerun()
            else:
                all_v = {o: st.session_state[_svk].get(f"{pid}||{o}",0) for o in opts}
                if all_v[my_vote] == 0: all_v[my_vote] = 1
                total = max(sum(all_v.values()),1)
                rows_html = ""
                for opt, cnt in all_v.items():
                    pct = cnt/total*100
                    is_mine = "✓ Tu voto" if opt==my_vote else ""
                    bar_clr = "#6366f1" if opt!=my_vote else "#a78bfa"
                    rows_html += (f'<div class="enc-result-row">'
                                  f'<span class="enc-opt-lbl">{opt}</span>'
                                  f'<div class="enc-bar-wrap"><div style="width:{pct:.0f}%;height:100%;background:{bar_clr};border-radius:5px;box-shadow:0 0 6px {bar_clr}66;"></div></div>'
                                  f'<span class="enc-pct">{pct:.0f}%</span>'
                                  f'<span class="enc-yours">{is_mine}</span></div>')
                st.markdown(rows_html, unsafe_allow_html=True)
                if st.button("🔄 Cambiar voto", key=f"enc_rst_{pid}"):
                    st.session_state["enc_mis_votos"].pop(pid, None); st.rerun()

            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    st.markdown('<div style="text-align:center;font-size:10px;color:rgba(169,178,214,.4);margin-top:8px;">'
                '🗳️ Los votos son anónimos y reinician cada GP</div>', unsafe_allow_html=True)



# ─────────────────────────────────────────────────────────
# SIMULADOR DE GP
# ─────────────────────────────────────────────────────────
def pantalla_simulador():
    PTS_CARRERA = {1:25,2:18,3:15,4:12,5:10,6:8,7:6,8:4,9:2,10:1}
    PTS_QUALY   = {1:15,2:10,3:7,4:5,5:3}
    PTS_SPRINT  = {1:8,2:7,3:6,4:5,5:4,6:3,7:2,8:1}
    PTS_CONST   = {1:10,2:5,3:2}

    st.markdown("""<style>
    @keyframes simG{0%,100%{box-shadow:0 0 24px rgba(59,130,246,.15);}50%{box-shadow:0 0 44px rgba(59,130,246,.3);}}
    .sim-hero{background:linear-gradient(145deg,rgba(7,9,22,.99),rgba(10,18,50,.99));
      border:1.5px solid rgba(59,130,246,.45);border-radius:22px;padding:24px 22px 18px;
      margin-bottom:18px;text-align:center;position:relative;overflow:hidden;animation:simG 3.5s ease-in-out infinite;}
    .sim-hero::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;
      background:linear-gradient(90deg,transparent,#3b82f6,#60a5fa,#3b82f6,transparent);}
    .sim-title{font-size:26px;font-weight:900;letter-spacing:.08em;
      background:linear-gradient(90deg,#3b82f6,#60a5fa,#3b82f6);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
    .sim-sub{font-size:11px;color:rgba(169,178,214,.55);letter-spacing:.14em;margin-top:3px;}
    .sim-rt{width:100%;border-collapse:collapse;}
    .sim-rt th{background:rgba(59,130,246,.15);color:#93c5fd;font-size:10px;font-weight:700;
      letter-spacing:.1em;text-transform:uppercase;padding:10px 12px;text-align:left;}
    .sim-rt td{padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.05);font-size:13px;color:#e8ecff;}
    .sim-rt tr:last-child td{border-bottom:none;}
    .smd{font-size:12px;font-weight:800;} .smd.up{color:#4ade80;} .smd.dn{color:#ef4444;} .smd.eq{color:rgba(169,178,214,.5);}
    </style>""", unsafe_allow_html=True)
    st.markdown('<div class="sim-hero">'
                '<div style="font-size:28px;margin-bottom:6px;">🔬</div>'
                '<div class="sim-title">SIMULADOR DE GP</div>'
                '<div class="sim-sub">Ingresá el resultado oficial y calculamos los puntos de cada Formulero</div>'
                '</div>', unsafe_allow_html=True)

    m = _mod_db(); mcore = _mod_core()
    gp_sim = st.selectbox("Gran Premio a simular:", GPS_ACTIVOS, key="sim_gp",
                          format_func=lambda x: x.split(". ",1)[-1] if ". " in x else x)
    es_sprint = gp_sim in GPS_SPRINT

    # ── Verificar si el GP está abierto ──────────────────
    gp_abierto = True
    try:
        if "_error" not in mcore:
            _est = _safe_call(mcore["obtener_estado_gp"], gp_sim, HORARIOS_CARRERA, TZ,
                             timeout_sec=4, default={"habilitado": True}) or {"habilitado": True}
            gp_abierto = _est.get("habilitado", True)
    except Exception: pass

    if gp_abierto and not is_admin():
        st.warning("⚠️ Las predicciones están **ABIERTAS** — el simulador es modo *previsualización* y no muestra las predicciones de los demás para no spoilear.")
        # Still allow simulation in preview mode (only shows own predictions)

    # ── Leer predicciones reales del GP usando recuperar_predicciones_piloto ──
    preds_all = {}
    try:
        if "_error" not in m and "recuperar_predicciones_piloto" in m:
            for _pil in PILOTOS_TORNEO:
                try:
                    _res = _safe_call(m["recuperar_predicciones_piloto"], _pil, gp_sim,
                                      timeout_sec=20, default=(None,None,(None,None)))
                    _dq, _ds, (_dr, _dc) = _res
                    _pred_flat = {}
                    # Qualy
                    if isinstance(_dq, dict):
                        for _ki,_vi in _dq.items():
                            try: _pred_flat[f"q{int(_ki)}"] = _vi
                            except Exception: _pred_flat[str(_ki)] = _vi
                    # Carrera
                    if isinstance(_dr, dict):
                        for _ki,_vi in _dr.items():
                            try: _pred_flat[f"p{int(_ki)}"] = _vi
                            except Exception: _pred_flat[str(_ki)] = _vi
                    # Constructores
                    if isinstance(_dc, dict):
                        for _ki,_vi in _dc.items():
                            try: _pred_flat[f"c{int(_ki)}"] = _vi
                            except Exception: _pred_flat[str(_ki)] = _vi
                    # Sprint
                    if isinstance(_ds, dict):
                        for _ki,_vi in _ds.items():
                            try: _pred_flat[f"spr{int(_ki)}"] = _vi
                            except Exception: _pred_flat[str(_ki)] = _vi
                    if _pred_flat:
                        preds_all[_pil] = _pred_flat
                except Exception: pass
    except Exception: pass

    if not preds_all:
        st.info("ℹ️ No hay predicciones guardadas para este GP. Verificá que los Formuleros las hayan enviado.")
        # Don't return — still show the simulator for manual entry

    # ── Tabla actual ──────────────────────────────────────
    @st.cache_data(ttl=60, show_spinner=False)
    def _sim_tabla():
        if "_error" in m: return None
        return _safe_call(m["leer_tabla_posiciones"], PILOTOS_TORNEO, timeout_sec=8, default=None)
    df_actual = _sim_tabla()
    if df_actual is None or (hasattr(df_actual,"empty") and df_actual.empty):
        df_actual = pd.DataFrame({"Piloto":PILOTOS_TORNEO,"Puntos":[0]*len(PILOTOS_TORNEO)})
    df_actual = df_actual.copy()
    if "Puntos" in df_actual.columns:
        df_actual["Puntos"] = pd.to_numeric(df_actual["Puntos"],errors="coerce").fillna(0).astype(int)
    else: df_actual["Puntos"] = 0

    st.markdown(f'<div style="background:rgba(59,130,246,.08);border:1px solid rgba(59,130,246,.25);'
                f'border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:12px;">'
                f'✅ <b style="color:#60a5fa;">Predicciones cargadas:</b> '
                f'{", ".join(preds_all.keys())} ({len(preds_all)}/{len(PILOTOS_TORNEO)} Formuleros)'
                f'</div>', unsafe_allow_html=True)

    st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:.14em;'
                'color:rgba(59,130,246,.8);text-transform:uppercase;margin-bottom:8px;">'
                '🏁 RESULTADO OFICIAL DEL GP</div>', unsafe_allow_html=True)

    if "sim_state" not in st.session_state: st.session_state["sim_state"] = {}
    ss = st.session_state["sim_state"]
    all_pilots = list(dict.fromkeys([d for t in GRILLA_2026.values() for d in t]))
    all_teams  = list(GRILLA_2026.keys())
    medals_sel = {1:"🥇",2:"🥈",3:"🥉"}

    def _sel(etapa, pts_map, pilots):
        sk = f"sim_{etapa}_{gp_sim}"
        if sk not in ss: ss[sk] = {i:"" for i in range(1, len(pts_map)+1)}
        sel = ss[sk]
        _, cr = st.columns([5,1])
        with cr:
            if st.button("🔄", key=f"rst_{etapa}_{gp_sim}", help="Reset"):
                ss[sk] = {i:"" for i in range(1, len(pts_map)+1)}; st.rerun()
        for pos in range(1, len(pts_map)+1):
            taken = {v for k,v in sel.items() if k != pos and v}
            avail = ["— Sin asignar —"] + [p for p in pilots if p not in taken]
            ci = avail.index(sel[pos]) if sel[pos] in avail else 0
            clr = PILOTO_COLORS.get(sel[pos], "rgba(255,255,255,.2)") if sel[pos] else "rgba(255,255,255,.12)"
            ph  = DRIVER_HEADSHOTS.get(sel[pos], "") if sel[pos] else ""
            av  = (f'<img src="{ph}" style="width:26px;height:26px;border-radius:50%;object-fit:cover;'
                   f'object-position:top;border:2px solid {clr};margin-right:6px;vertical-align:middle;">'
                   if ph else '<span style="font-size:16px;margin-right:6px;">❓</span>')
            st.markdown(f'<div style="display:flex;align-items:center;gap:6px;margin-bottom:1px;">'
                        f'<span style="font-size:13px;min-width:26px;">{medals_sel.get(pos,f"P{pos}")}</span>'
                        f'{av}<span style="font-size:11px;color:{clr};font-weight:700;flex:1;">'
                        f'{sel[pos] if sel[pos] else "Sin asignar"}</span>'
                        f'<span style="font-size:10px;color:rgba(212,175,55,.6);">+{pts_map[pos]}pts</span>'
                        f'</div>', unsafe_allow_html=True)
            ns = st.selectbox(f"P{pos}", avail, index=ci, key=f"sim_{etapa}_{gp_sim}_p{pos}", label_visibility="collapsed")
            ss[sk][pos] = "" if ns.startswith("—") else ns
        return ss[sk]

    _tl = ["🏁 Carrera"]  # Simulador SOLO carrera (para el vivo)

    # ── OpenF1 en vivo ─────────────────────────────────────────────────
    _f1_col1, _f1_col2 = st.columns([3,1])
    with _f1_col1:
        _load_live = st.button("🔴 Cargar posiciones F1 en vivo (openf1.org)",
                               key="sim_load_live", use_container_width=True,
                               help="Carga las posiciones actuales de la carrera de F1 en vivo")
    with _f1_col2:
        if st.button("🔄 Limpiar", key="sim_clear_all", use_container_width=True,
                     help="Borra todas las posiciones para simular desde cero"):
            for _k in list(ss.keys()):
                if str(gp_sim) in str(_k): del ss[_k]
            st.rerun()

    if _load_live:
        with st.spinner("🔴 Conectando a openf1.org..."):
            try:
                import urllib.request as _ur_f1, json as _js_f1, urllib.error as _ue_f1
                def _get_json(_url):
                    _req = _ur_f1.Request(_url, headers={"User-Agent":"Mozilla/5.0 TorneoFefeWolf"})
                    try:
                        return _js_f1.loads(_ur_f1.urlopen(_req, timeout=15).read())
                    except Exception: return []

                _year_f1 = __import__("datetime").datetime.now().year
                _sess_data = []
                for _yq in (_year_f1, _year_f1-1):
                    try:
                        _url_s = f"https://api.openf1.org/v1/sessions?session_type=Race&year={_yq}"
                        _d = _get_json(_url_s)
                        if _d:
                            _sess_data = _d
                            break
                    except Exception: continue

                if not _sess_data:
                    st.warning("⚠️ openf1.org no respondió o no hay carreras disponibles. "
                               "Ingresá los resultados manualmente usando el panel de abajo.")
                else:
                    from datetime import datetime as _dtf1, timezone as _tzf1
                    def _parse_dt(s):
                        try: return _dtf1.fromisoformat(str(s).replace("Z","+00:00"))
                        except Exception: return _dtf1.min.replace(tzinfo=_tzf1.utc)
                    _now_f1 = _dtf1.now(_tzf1.utc)
                    _sess_sorted = sorted(_sess_data, key=lambda x: _parse_dt(x.get("date_start","")))
                    _started = [s for s in _sess_sorted if _parse_dt(s.get("date_start","")) <= _now_f1]
                    _target = _started[-1] if _started else _sess_sorted[-1]
                    _sk_f1 = _target.get("session_key","")
                    _gp_nombre_f1 = _target.get("country_name","") or _target.get("circuit_short_name","") or "?"
                    _es_vivo = (_now_f1 - _parse_dt(_target.get("date_start",""))).total_seconds() < 4*3600

                    _pos_data = _get_json(f"https://api.openf1.org/v1/position?session_key={_sk_f1}")
                    _drv_data = _get_json(f"https://api.openf1.org/v1/drivers?session_key={_sk_f1}")

                    if not _drv_data:
                        st.warning(f"⚠️ No hay datos de pilotos para {_gp_nombre_f1} en openf1. "
                                   "La carrera puede no estar disponible todavía. Ingresá los resultados manualmente.")
                    elif not _pos_data:
                        st.warning(f"⚠️ No hay posiciones para {_gp_nombre_f1} todavía. "
                                   "Si la carrera ya terminó, probá en unos minutos. Mientras tanto, ingresá manualmente.")
                    else:
                        _drv_map = {d.get("driver_number"): (d.get("full_name") or d.get("broadcast_name",""))
                                    for d in _drv_data}
                        _latest = {}
                        for _p in _pos_data:
                            _dn = _p.get("driver_number","")
                            if _dn not in _latest or str(_p.get("date","")) > str(_latest[_dn].get("date","")):
                                _latest[_dn] = _p
                        _sorted_pos = sorted(_latest.values(), key=lambda x: x.get("position") or 99)
                        _sk_car = f"sim_car_{gp_sim}"
                        if _sk_car not in ss: ss[_sk_car] = {}
                        _cargados = 0
                        for _entry in _sorted_pos[:10]:
                            _pos_n = _entry.get("position",99)
                            _drv_name = _drv_map.get(_entry.get("driver_number",""),"")
                            if _pos_n and _pos_n <= 10 and _drv_name:
                                _matched = next((d for d in all_pilots if any(
                                    part.lower() in _drv_name.lower()
                                    for part in d.split() if len(part)>2)), "")
                                if _matched:
                                    ss[_sk_car][_pos_n] = _matched; _cargados += 1
                        if _cargados:
                            _estado_f1 = "🔴 EN VIVO" if _es_vivo else "🏁 Última sesión"
                            st.success(f"{_estado_f1} — {_cargados}/10 posiciones cargadas ({_gp_nombre_f1})")
                            if _cargados < 5:
                                st.caption("⚠️ Solo se cargaron pocas posiciones. Completá el resto manualmente.")
                            st.rerun()
                        else:
                            st.warning(f"⚠️ Se encontraron datos de {_gp_nombre_f1} pero ningún piloto "
                                       f"coincide con la grilla del torneo. Posibles pilotos disponibles: "
                                       f"{', '.join(list(_drv_map.values())[:5])}. Ingresá manualmente.")
            except Exception as _f1e:
                st.warning(f"⚠️ No se pudo conectar a openf1.org: {_f1e}. "
                           "Ingresá los resultados manualmente en el panel de abajo.")

    st.markdown('<div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.3);'
                'border-radius:10px;padding:8px 14px;margin-bottom:10px;font-size:12px;color:#fca5a5;">'
                '🔴 Simulador exclusivo de <b>CARRERA</b> — pensado para seguir el resultado en vivo.</div>',
                unsafe_allow_html=True)
    sel_r = _sel("car", PTS_CARRERA, all_pilots)

    # Posición de Colapinto en Carrera (para el bonus +20pts)
    st.markdown('<div style="background:rgba(255,79,216,.08);border:1px solid rgba(255,79,216,.3);'
                'border-radius:10px;padding:8px 14px;margin:8px 0;font-size:12px;">'
                '🇦🇷 <b style="color:#FF4FD8;">Posición de Colapinto en Carrera</b> (para calcular bonus +20pts)</div>',
                unsafe_allow_html=True)
    _col_sim_pos = st.selectbox("Colapinto posición:", ["(Sin resultado)"] + [f"P{i}" for i in range(1,23)],
                                key=f"sim_col_r_{gp_sim}", label_visibility="collapsed")
    _col_r_real = str(_col_sim_pos).replace("P","").strip() if _col_sim_pos != "(Sin resultado)" else ""

    # Sin Qualy/Sprint/Constructores en el simulador (solo carrera)
    sel_q = {}; sel_c = {}; sel_s = {}

    st.markdown("---")
    if not any(sel_r.get(i) for i in PTS_CARRERA):
        st.info("👆 Ingresá al menos los 10 primeros de Carrera para calcular la proyección.")
        return

    def _pts_for(pred, rcar, rqua, rspr, rcon, col_r_real=""):
        """Calcula pts de una predicción vs resultado simulado. Usa normalización de nombres."""
        try:
            from core.utils import normalizar_nombre as _nn
        except Exception:
            _nn = lambda x: str(x or "").strip().lower()

        def _match(a, b):
            return bool(a and b and _nn(str(a)) == _nn(str(b)))

        pts = 0
        # QUALY (vacío en simulador)
        aq = 0
        for p in PTS_QUALY:
            pq = (pred.get(f"q{p}") or "")
            if _match(pq, rqua.get(p,"")): pts += PTS_QUALY[p]; aq += 1
        if aq == len(PTS_QUALY) and aq > 0: pts += 5
        # CARRERA
        ar = 0
        for p in PTS_CARRERA:
            pr = (pred.get(f"p{p}") or "")
            if _match(pr, rcar.get(p,"")): pts += PTS_CARRERA[p]; ar += 1
        if ar == len(PTS_CARRERA): pts += 5
        # Colapinto Carrera (+20pts si acertó la posición exacta)
        if col_r_real:
            try:
                _col_pred = str(pred.get("colapinto_r","")).strip()
                if _col_pred and _col_pred == str(col_r_real).strip():
                    pts += 20
            except Exception: pass
        # SPRINT (vacío en simulador)
        if rspr:
            asc = 0
            for p in PTS_SPRINT:
                ps = (pred.get(f"spr{p}") or "")
                if _match(ps, rspr.get(p,"")): pts += PTS_SPRINT[p]; asc += 1
            if asc == len(PTS_SPRINT): pts += 3
        # CONSTRUCTORES (vacío en simulador)
        ac = 0
        for p in PTS_CONST:
            pc = (pred.get(f"c{p}") or "")
            if _match(pc, rcon.get(p,"")): pts += PTS_CONST[p]; ac += 1
        if ac == len(PTS_CONST) and ac > 0: pts += 3
        return pts

    rows = []; medals_t = {1:"🥇",2:"🥈",3:"🥉"}
    for f in PILOTOS_TORNEO:
        base = int(df_actual[df_actual["Piloto"]==f]["Puntos"].values[0]) if f in df_actual["Piloto"].values else 0
        sim  = _pts_for(preds_all.get(f,{}), sel_r, sel_q, sel_s, sel_c, col_r_real=_col_r_real)
        rows.append({"Piloto":f,"Actual":base,"Sim":sim,"Total":base+sim,
                     "_clr":PILOTO_COLORS.get(f,"#a855f7"),"_ok":f in preds_all})
    df_p = pd.DataFrame(rows).sort_values("Total",ascending=False).reset_index(drop=True)
    df_o = pd.DataFrame(rows).sort_values("Actual",ascending=False).reset_index(drop=True)

    st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:.14em;'
                'color:rgba(59,130,246,.8);text-transform:uppercase;margin-bottom:10px;">'
                '📊 PROYECCIÓN FINAL</div>', unsafe_allow_html=True)

    # ── Modo En Vivo ──────────────────────────────────────────────────
    _en_vivo = st.toggle("🔴 Modo En Vivo (auto-actualiza cada 60 seg)", key="sim_en_vivo")
    if _en_vivo:
        import time as _tv
        st.markdown(
            '<div style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);'
            'border-radius:10px;padding:8px 14px;display:flex;align-items:center;gap:8px;margin-bottom:8px;">'
            '<span style="font-size:18px;animation:blink 1s infinite;">🔴</span>'
            '<div><div style="font-size:12px;font-weight:900;color:#ef4444;">EN VIVO</div>'
            '<div style="font-size:10px;color:rgba(169,178,214,.6);">La tabla se actualiza automáticamente · '
            'Usá "Cargar F1 en vivo" para traer posiciones reales</div></div></div>',
            unsafe_allow_html=True)
        # Show live alerts if there are predictions loaded
        if preds_all:
            _alert_html = ""
            for _pil_v, _pred_v in preds_all.items():
                _clr_v = PILOTO_COLORS.get(_pil_v,"#a855f7")
                _pts_v = _pts_for(_pred_v, sel_r if 'sel_r' in dir() else {}, sel_q if 'sel_q' in dir() else {}, sel_s if 'sel_s' in dir() else {}, sel_c if 'sel_c' in dir() else {})
                if _pts_v > 0:
                    _alert_html += (f'<div style="display:flex;align-items:center;gap:8px;'
                                    f'background:{_clr_v}11;border:1px solid {_clr_v}33;'
                                    f'border-radius:10px;padding:6px 12px;margin-bottom:4px;">'
                                    f'<span style="color:{_clr_v};font-weight:800;font-size:12px;">{_pil_v}</span>'
                                    f'<span style="color:#ffdd7a;font-weight:900;font-size:14px;margin-left:auto;">'
                                    f'{_pts_v} pts</span></div>')
            if _alert_html:
                st.markdown(_alert_html, unsafe_allow_html=True)
        _tv.sleep(60); st.rerun()

    tbl = ('<table class="sim-rt"><thead><tr><th>Pos</th><th>Formulero</th>'
           '<th>Actual</th><th>+ GP</th><th>TOTAL</th><th>Δ</th><th>Pred</th></tr></thead><tbody>')
    for i, row in df_p.iterrows():
        pn = i+1; po = df_o[df_o["Piloto"]==row["Piloto"]].index[0]+1; dp = po-pn
        dh = (f'<span class="smd up">↑{dp}</span>' if dp>0
              else f'<span class="smd dn">↓{abs(dp)}</span>' if dp<0
              else '<span class="smd eq">—</span>')
        clr = row["_clr"]
        ph  = DRIVER_HEADSHOTS.get(row["Piloto"],"")
        av  = (f'<img src="{ph}" style="width:20px;height:20px;border-radius:50%;object-fit:cover;'
               f'object-position:top;border:1.5px solid {clr};margin-right:5px;vertical-align:middle;">' if ph else "")
        sim_s = (f'<span style="color:#4ade80;font-weight:800;">+{row["Sim"]}</span>' if row["Sim"]>0
                 else '<span style="color:rgba(169,178,214,.4);">0</span>')
        tbl += (f'<tr><td style="font-weight:900;color:{clr};font-size:15px;">{medals_t.get(pn,str(pn))}</td>'
                f'<td>{av}<b style="color:{clr};">{row["Piloto"]}</b></td>'
                f'<td style="color:rgba(169,178,214,.7);">{row["Actual"]}</td>'
                f'<td>{sim_s}</td>'
                f'<td style="font-weight:900;font-size:15px;color:#ffdd7a;">{row["Total"]}</td>'
                f'<td>{dh}</td>'
                f'<td>{"✅" if row["_ok"] else "🔴"}</td></tr>')
    tbl += '</tbody></table>'
    st.markdown(f'<div style="overflow-x:auto;">{tbl}</div>', unsafe_allow_html=True)

    if _PLOTLY_OK and df_p["Total"].max() > 0:
        try:
            import plotly.graph_objects as _gs
            fig = _gs.Figure()
            fig.add_trace(_gs.Bar(name="Actual", x=df_p["Piloto"], y=df_p["Actual"],
                marker_color=[PILOTO_COLORS.get(p,"#666")+"55" for p in df_p["Piloto"]], marker_line_width=0))
            fig.add_trace(_gs.Bar(name="+ Este GP", x=df_p["Piloto"], y=df_p["Sim"],
                marker_color=[PILOTO_COLORS.get(p,"#a855f7") for p in df_p["Piloto"]], marker_line_width=0,
                text=df_p["Sim"], textposition="outside", textfont=dict(color="#4ade80",size=11), cliponaxis=False))
            fig.update_layout(height=240, barmode="stack",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=4,r=4,t=36,b=4),
                title=dict(text="📊 Actual + Puntos proyectados",font=dict(color="#60a5fa",size=12),x=0),
                legend=dict(font=dict(color="#e8ecff",size=10),bgcolor="rgba(0,0,0,0)",orientation="h",y=1.14,x=0),
                xaxis=dict(tickfont=dict(color="#e8ecff",size=10),showgrid=False),
                yaxis=dict(tickfont=dict(color="#a9b2d6",size=9),gridcolor="rgba(255,255,255,.04)",zeroline=False))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False,"staticPlot":True})
        except Exception: pass

    st.markdown('<div style="text-align:center;font-size:10px;color:rgba(169,178,214,.35);margin-top:6px;">'
                '⚠️ Plenos exactos y Regla Colapinto calculados manualmente.</div>', unsafe_allow_html=True)


def pantalla_api_test():
    st.title("🧪 Test API F1")
    year=st.number_input("Año",2000,2100,2026,step=1)
    if st.button("Probar constructors"):
        try:
            data=requests.get(f"{API_BASE}/f1/constructors",params={"year":int(year)},timeout=8).json()
            st.success("API OK ✅"); st.json(data)
        except Exception as e: st.error(f"Falló: {e}")


# ─────────────────────────────────────────────────────────
# 11. MAIN
# ─────────────────────────────────────────────────────────
def _pantalla_espectador():
    """Vista pública de solo lectura — acceso via ?modo=espectador"""
    st.markdown("""
    <style>
    #MainMenu{visibility:hidden}footer{visibility:hidden}
    div[data-testid="stSidebar"]{display:none!important}
    </style>""", unsafe_allow_html=True)
    st.markdown(
        '<div style="text-align:center;padding:16px 0 8px;">'
        '<div style="font-size:24px;font-weight:900;color:#ffdd7a;letter-spacing:.1em;">'
        '🏎️ TORNEO FEFE WOLF 2026</div>'
        '<div style="font-size:11px;color:rgba(169,178,214,.5);margin-top:4px;">'
        'Modo espectador — solo lectura</div></div>', unsafe_allow_html=True)

    _mdb_e = _mod_db()
    _tab_a, _tab_b = st.tabs(["📊 Tabla de posiciones", "📅 Cronología"])

    with _tab_a:
        if "_error" not in _mdb_e:
            _df_e = _safe_call(_mdb_e["leer_tabla_posiciones"], PILOTOS_TORNEO,
                               timeout_sec=12, default=None)
            if _df_e is not None and not (hasattr(_df_e,"empty") and _df_e.empty):
                _df_e2 = _df_e.sort_values("Puntos",ascending=False).reset_index(drop=True)
                for _ri2, _row2 in _df_e2.iterrows():
                    _pil2 = str(_row2["Piloto"]); _pts2 = int(_row2.get("Puntos",0))
                    _clr2 = PILOTO_COLORS.get(_pil2,"#a855f7")
                    _ph2  = DRIVER_HEADSHOTS.get(_pil2,DRIVER_PHOTOS.get(_pil2,""))
                    _med2 = {0:"🥇",1:"🥈",2:"🥉"}.get(_ri2,f"{_ri2+1}°")
                    _av2  = (f'<img src="{_ph2}" style="width:36px;height:36px;border-radius:50%;'
                             f'object-fit:cover;object-position:top;border:2px solid {_clr2};">'
                             if _ph2 else f'<div style="width:36px;height:36px;border-radius:50%;'
                             f'background:{_clr2}22;border:2px solid {_clr2};display:flex;'
                             f'align-items:center;justify-content:center;font-weight:900;'
                             f'font-size:10px;color:{_clr2};">{"".join(w[0] for w in _pil2.split()[:2])}</div>')
                    st.markdown(
                        f'<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;'
                        f'background:rgba(255,255,255,.03);border:1px solid {_clr2}22;'
                        f'border-radius:12px;margin-bottom:6px;">'
                        f'<span style="font-size:18px;">{_med2}</span>{_av2}'
                        f'<span style="font-size:14px;font-weight:900;color:{_clr2};flex:1;">{_pil2}</span>'
                        f'<span style="font-size:20px;font-weight:900;color:#ffdd7a;">{_pts2}</span>'
                        f'<span style="font-size:9px;color:rgba(169,178,214,.4);"> pts</span>'
                        f'</div>', unsafe_allow_html=True)

    with _tab_b:
        if "_error" not in _mdb_e:
            _df_h_e = _safe_call(_mdb_e["leer_historial_df"], timeout_sec=12, default=pd.DataFrame())
            if _df_h_e is not None and not (hasattr(_df_h_e,"empty") and _df_h_e.empty):
                _dfhe2 = _df_h_e.copy(); _dfhe2.columns=[c.lower().strip() for c in _dfhe2.columns]
                _dfhe2["puntos"]=pd.to_numeric(_dfhe2["puntos"],errors="coerce").fillna(0).astype(int)
                for _gp_e in GPS_OFICIALES:
                    if _gp_e not in _dfhe2.get("gp",pd.Series()).values: continue
                    _grp_e = _dfhe2[_dfhe2["gp"]==_gp_e].sort_values("puntos",ascending=False)
                    _gp_l_e = _gp_e.split(". ",1)[-1] if ". " in _gp_e else _gp_e
                    _chips_e = "".join(
                        f'<span style="background:{PILOTO_COLORS.get(r["piloto"],"#666")}22;'
                        f'color:{PILOTO_COLORS.get(r["piloto"],"#aaa")};border-radius:20px;'
                        f'padding:2px 8px;font-size:10px;font-weight:700;margin-right:4px;">'
                        f'{r["piloto"].split()[0]}: {int(r["puntos"])}</span>'
                        for _, r in _grp_e.iterrows()
                    )
                    st.markdown(f'<div style="margin-bottom:6px;">'
                                f'<span style="font-size:11px;font-weight:700;color:rgba(246,195,73,.7);">{_gp_l_e}</span>'
                                f'<div style="margin-top:3px;">{_chips_e}</div></div>', unsafe_allow_html=True)

    st.markdown('<div style="text-align:center;margin-top:20px;font-size:11px;'
                'color:rgba(169,178,214,.35);">torneofefewolf2026.streamlit.app</div>', unsafe_allow_html=True)


def main():
    _check_apertura_notificacion()  # envía notif si acaba de abrir el período

    # ── URL Navigation via query_params ──────────────────────────────
    # Supports: /?s=perfil, /?s=predicciones, /?s=formuleros, /?s=tabla, etc.
    _URL_MAP = {
        "perfil": "👤  Mi Perfil",
        "predicciones": "⚡  Predicciones",
        "formuleros": "👥  Formuleros",
        "tabla": "📊  Tabla de Posiciones",
        "historial": "📈  Historial GP",
        "paddock": "💬  El Show del Paddock F1",
        "reglamento": "📜  Reglamento Oficial",
        "calendario": "📅  Calendario 2026",
        "pilotos": "🏎️  Pilotos y Escuderías",
        "simulador": "🔬  Simulador GP",
        "inicio": "🏠  Inicio & Historia",
        "admin": "🔐  Panel Admin",
    }
    try:
        _qs = st.query_params
        if _qs.get("modo","") == "espectador":
            _pantalla_espectador(); return
        _s_param = _qs.get("s","").lower().strip()
        if _s_param and _s_param in _URL_MAP:
            st.session_state["fw_force_nav"] = _URL_MAP[_s_param]
    except Exception: pass

    sidebar_login_block()

    st.sidebar.markdown("""
    <style>
    /* Sidebar container */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #07091a 0%, #0a0d24 50%, #070918 100%) !important;
        border-right: 1px solid rgba(212,175,55,.15) !important;
    }
    /* Hide default radio labels */
    section[data-testid="stSidebar"] .stRadio label {
        background: rgba(255,255,255,.03) !important;
        border: 1px solid rgba(255,255,255,.07) !important;
        border-radius: 10px !important;
        padding: 8px 12px !important;
        margin: 2px 0 !important;
        cursor: pointer !important;
        transition: all .18s ease !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        color: rgba(232,236,255,.75) !important;
        display: flex !important;
        align-items: center !important;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(212,175,55,.08) !important;
        border-color: rgba(212,175,55,.3) !important;
        color: #D4AF37 !important;
        transform: translateX(3px) !important;
    }
    section[data-testid="stSidebar"] .stRadio [data-checked="true"] label,
    section[data-testid="stSidebar"] .stRadio input:checked + label {
        background: linear-gradient(90deg, rgba(212,175,55,.12), rgba(212,175,55,.04)) !important;
        border-color: rgba(212,175,55,.5) !important;
        color: #ffdd7a !important;
        font-weight: 800 !important;
    }
    /* Hide radio circles */
    section[data-testid="stSidebar"] .stRadio input[type="radio"] {
        display: none !important;
    }
    section[data-testid="stSidebar"] hr {
        border-color: rgba(212,175,55,.15) !important;
        margin: 8px 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.sidebar.markdown(
        '<div style="text-align:center;padding:4px 0 10px;">'
        '<div style="font-size:9px;font-weight:900;letter-spacing:.25em;'
        'color:rgba(212,175,55,.55);text-transform:uppercase;">⚡ MENÚ PRINCIPAL</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # ── Next GP mini-countdown in sidebar ─────────────────────
    try:
        _ngp_name = st.secrets.get("next_gp_name","Canadá")
        _ngp_close = st.secrets.get("next_gp_close_utc","")
        if _ngp_close:
            from datetime import datetime, timezone as _tz2
            _now_utc = datetime.now(_tz2.utc)
            _close_dt = datetime.fromisoformat(_ngp_close.replace("Z","")).replace(tzinfo=_tz2.utc)
            _diff_sec = int((_close_dt - _now_utc).total_seconds())
            if _diff_sec > 0:
                _dd = _diff_sec//86400; _hh = (_diff_sec%86400)//3600; _mm = (_diff_sec%3600)//60
                _countdown_str = f"{_dd}d {_hh}h {_mm}m" if _dd > 0 else f"{_hh}h {_mm}m"
                st.sidebar.markdown(
                    f'<div style="background:rgba(74,222,128,.07);border:1px solid rgba(74,222,128,.2);' +
                    f'border-radius:10px;padding:8px 10px;margin:4px 2px 8px;text-align:center;">' +
                    f'<div style="font-size:8px;color:rgba(169,178,214,.5);letter-spacing:.12em;text-transform:uppercase;">🏁 PRÓXIMO GP</div>' +
                    f'<div style="font-size:12px;font-weight:800;color:#ffdd7a;margin:2px 0;">{_ngp_name}</div>' +
                    f'<div style="font-size:15px;font-weight:900;color:#4ade80;">⏱️ {_countdown_str}</div>' +
                    f'<div style="font-size:8px;color:rgba(169,178,214,.4);">para cierre de predicciones</div></div>',
                    unsafe_allow_html=True)
    except Exception: pass

    # ── Check unread messages ─────────────────────────────────
    _usr_nav = (st.session_state.get("perfil") or {}).get("usuario","")
    _unread_badge = ""
    try:
        _m_chat_nav = _mod_mesa()
        if "_error" not in _m_chat_nav:
            _last_seen = st.session_state.get("formuleros_last_seen_id", 0)
            _all_msgs = _m_chat_nav["mc_list_messages"](limit=5) or []
            if _all_msgs and _all_msgs[0][0] > _last_seen:
                _unread_count = sum(1 for r in _all_msgs if r[0] > _last_seen and r[1] != _usr_nav)
                if _unread_count > 0:
                    _unread_badge = " ✉️"
    except Exception: pass

    # ── Nav opciones (categorizadas via CSS ::before) ─────────
    opciones = [
        "🏠  Inicio & Historia",
        "⚡  Predicciones",
        "📊  Tabla de Posiciones",
        "📈  Historial GP",
        f"👥  Formuleros{_unread_badge}",
        "💬  El Show del Paddock F1",
        "🔬  Simulador GP",
        "👤  Mi Perfil",
        "📜  Reglamento Oficial",
    ]
    if (st.session_state.get("perfil") or {}).get("usuario","") == "Checo Perez":
        opciones.append("🔐  Panel Admin")

    _check_and_send_reminders()  # Recordatorio automático silencioso

    # ── Sidebar nav sync with fw_force_nav ──
    if "fw_sidebar_idx" not in st.session_state:
        st.session_state["fw_sidebar_idx"] = 0
    _nav_pre = st.session_state.get("fw_force_nav", None)
    if _nav_pre:
        _nav_map = {"Predicciones":"⚡  Predicciones","Posiciones":"Posiciones",
                    "Paddock":"Paddock","Campeones":"Campeones","Head":"Head",
                    "Perfil":"Perfil","Historial":"Historial","Calendario":"Calendario"}
        _kw = _nav_map.get(_nav_pre, _nav_pre)
        for _oi, _op in enumerate(opciones):
            if _kw in _op:
                st.session_state["fw_sidebar_idx"] = _oi; break

    # Key changes with index so Streamlit forces the radio to update
    _radio_key = f"fw_sidebar_radio_{st.session_state['fw_sidebar_idx']}"
    opcion = st.sidebar.radio("", opciones,
        index=st.session_state.get("fw_sidebar_idx", 0),
        label_visibility="collapsed",
        key=_radio_key)
    st.sidebar.markdown(
        '<div style="margin-top:6px;padding:10px 8px;'
        'background:rgba(212,175,55,.04);border-radius:10px;'
        'border:1px solid rgba(212,175,55,.1);text-align:center;">'
        '<div style="font-size:14px;margin-bottom:2px;">🏁</div>'
        '<div style="font-size:10px;font-weight:800;color:rgba(212,175,55,.7);">TORNEO FEFE WOLF</div>'
        '<div style="font-size:9px;color:rgba(169,178,214,.35);">Temporada 2026</div>'
        '</div>',
        unsafe_allow_html=True
    )
    # QR Code para compartir
    try:
        import qrcode as _qrc_mod, io as _qrc_io, base64 as _qrc_b64
        _qr_url = "https://torneofefewolf2026.streamlit.app"
        _qr = _qrc_mod.QRCode(box_size=3, border=1)
        _qr.add_data(_qr_url); _qr.make(fit=True)
        _qr_img = _qr.make_image(fill_color="#3b82f6", back_color="#070918")
        _qr_buf = _qrc_io.BytesIO(); _qr_img.save(_qr_buf, "PNG"); _qr_buf.seek(0)
        _qr_b64 = _qrc_b64.b64encode(_qr_buf.read()).decode()
        st.sidebar.markdown(
            f'<div style="text-align:center;margin-top:6px;">'
            f'<div style="font-size:8px;color:rgba(169,178,214,.3);margin-bottom:3px;">📱 Escaneá para compartir</div>'
            f'<img src="data:image/png;base64,{_qr_b64}" style="width:70px;height:70px;border-radius:6px;'
            f'border:1px solid rgba(59,130,246,.2);">'
            f'</div>', unsafe_allow_html=True)
        # Botón de compartir por WhatsApp con mensaje
        _share_msg = ("🏎️ Sumate al *Torneo de Predicciones Fefe Wolf 2026*! "
                      "Pedile tu código de acceso al Comisario 👉 " + _qr_url)
        import urllib.parse as _upqr
        _wa_share_url = "https://wa.me/?text=" + _upqr.quote(_share_msg)
        st.sidebar.markdown(
            f'<a href="{_wa_share_url}" target="_blank" style="text-decoration:none;">'
            f'<div style="text-align:center;margin-top:8px;background:linear-gradient(135deg,#075E54,#128C7E);'
            f'border-radius:10px;padding:9px 12px;border:1px solid rgba(37,211,102,.4);'
            f'box-shadow:0 2px 12px rgba(37,211,102,.25);">'
            f'<span style="color:#fff;font-weight:800;font-size:12px;letter-spacing:.04em;">'
            f'📲 Compartir invitación</span></div></a>',
            unsafe_allow_html=True)
        # Colaboración con los formuleros (alias) — dorado brillante
        st.sidebar.markdown(
            '<style>@keyframes fwAliasShine{0%,100%{text-shadow:0 0 6px rgba(212,175,55,.5),0 0 12px rgba(212,175,55,.3);}'
            '50%{text-shadow:0 0 12px rgba(255,215,0,.9),0 0 22px rgba(255,215,0,.6),0 0 30px rgba(212,175,55,.4);}}'
            '.fw-alias-gold{background:linear-gradient(95deg,#b8860b,#ffd700,#fff3b0,#ffd700,#b8860b);'
            'background-size:200% auto;-webkit-background-clip:text;-webkit-text-fill-color:transparent;'
            'background-clip:text;animation:fwAliasShine 2.5s ease-in-out infinite;font-weight:900;}</style>'
            '<div style="text-align:center;margin-top:10px;background:rgba(212,175,55,.1);'
            'border:1px solid rgba(212,175,55,.45);border-radius:10px;padding:10px 12px;'
            'box-shadow:0 0 16px rgba(212,175,55,.15);">'
            '<div style="font-size:9px;color:rgba(255,215,0,.8);font-weight:800;'
            'letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px;">💛 Colaborá con los formuleros</div>'
            '<div class="fw-alias-gold" style="font-size:17px;letter-spacing:.06em;">'
            'Alias: GENGAR22</div>'
            '<div style="font-size:8px;color:rgba(169,178,214,.45);margin-top:4px;">'
            'Uso exclusivo para la página</div>'
            '</div>', unsafe_allow_html=True)
    except ImportError: pass
    except Exception: pass

    _nav = st.session_state.pop("fw_force_nav", None)
    if _nav:
        opcion = _nav
    else:
        # Store current index for next rerun
        try:
            st.session_state["fw_sidebar_idx"] = opciones.index(opcion)
        except: pass
    if   "Inicio"       in opcion: pantalla_inicio()
    elif "Predicciones" in opcion: pantalla_cargar_predicciones()
    elif "Posiciones"   in opcion: pantalla_tabla_posiciones()
    elif "Historial"    in opcion: pantalla_historial_gp()
    elif "Admin"        in opcion: pantalla_admin()
    elif "Reglamento"   in opcion: pantalla_reglamento()
    elif "Formuleros"   in opcion:
        # Mark as seen
        try:
            _m_seen = _mod_mesa()
            if "_error" not in _m_seen:
                _msgs_seen = _m_seen["mc_list_messages"](limit=1) or []
                if _msgs_seen: st.session_state["formuleros_last_seen_id"] = _msgs_seen[0][0]
        except Exception: pass
        pantalla_formuleros()
    elif "Paddock"      in opcion: pantalla_mesa_chica()
    elif "Simulador"     in opcion: pantalla_simulador()
    elif "Perfil"       in opcion: pantalla_perfil()
    elif "Test"         in opcion: pantalla_api_test()

    # ── Elementos flotantes globales ──────────────────────
    mini_bar()      # Botón ☰ para ocultar/mostrar el menú lateral
    flecha_arriba() # Flecha dorada ↑ para volver al inicio
    # ── Auto scroll al top en cada cambio de página ──
    components.html("""<script>(function(){try{var p=window.parent||window,d=p.document;[d.querySelector('[data-testid="stMain"]'),d.querySelector('[data-testid="stAppViewContainer"]'),d.querySelector('.main > div'),d.documentElement,d.body].forEach(function(el){if(el)try{el.scrollTop=0}catch(e){}});try{p.scrollTo(0,0)}catch(e){}}catch(e){}})();</script>""", height=0)


main()
