import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components

# ==============================================================================
# 1. TRUCOS DE MAGIA (SCROLL MÓVIL - VERSIÓN ULTRA NUCLEAR)
# ==============================================================================

def scroll_to_top():
    """
    Fuerza el scroll hacia arriba.
    Versión compatible: Usa concatenación (+) para evitar errores de sintaxis en VS Code.
    """
    # Generamos un ID único basado en la hora actual
    unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    
    # Creamos el script sumando textos para que Python no se confunda con los corchetes {}
    js = """
    <script>
        // ID unico para forzar recarga: """ + unique_id + """
        function forceScroll() {
            var viewContainer = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
            if (viewContainer) {
                viewContainer.scrollTop = 0;
            }
            window.parent.scrollTo(0, 0);
        }
        
        // Intento 1: Inmediato
        forceScroll();
        
        // Intento 2: A los 50ms 
        setTimeout(forceScroll, 50);
        
        // Intento 3: A los 200ms (carga de textos)
        setTimeout(forceScroll, 200);

        // Intento 4: A los 500ms (carga de imágenes lentas)
        setTimeout(forceScroll, 500);
    </script>
    """
    components.html(js, height=0)

# ==============================================================================
# 2. CONEXIÓN Y BASE DE DATOS
# ==============================================================================

def conectar_google_sheets(nombre_hoja="sheet1"):
    """
    Conecta con la API de Google Sheets.
    Permite elegir entre la hoja de 'Predicciones' (sheet1) o 'Posiciones'.
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
            
        client = gspread.authorize(creds)
        
        # Selección de hoja con manejo de errores
        try:
            if nombre_hoja == "Posiciones":
                return client.open("TorneoFefe2026_DB").worksheet("Posiciones")
            else:
                return client.open("TorneoFefe2026_DB").sheet1
        except gspread.WorksheetNotFound:
            return None
            
    except Exception as e:
        return None

def guardar_etapa(usuario, gp, etapa, datos, camp_data=None):
    """
    Guarda las predicciones en la hoja principal (sheet1).
    """
    sheet = conectar_google_sheets("sheet1")
    if sheet is None:
        return False, "Error CRÍTICO: No se pudo conectar con la Base de Datos."

    # --- VERIFICAR DUPLICADOS ---
    try:
        registros = sheet.get_all_values()
        for fila in registros[1:]:
            if len(fila) > 3:
                if fila[1] == usuario and fila[2] == gp and fila[3] == etapa:
                    return False, f"⛔ ERROR DE SEGURIDAD: Ya enviaste la fase de {etapa} para el {gp}. No se permiten reenvíos."
    except Exception as e:
        return False, f"Error técnico validando duplicados: {e}"

    # --- PREPARACIÓN DE DATOS ---
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_hora = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # Estructura base: [Fecha, Usuario, GP, Etapa]
    row = [fecha_hora, usuario, gp, etapa]
    
    # LÓGICA DE COLUMNAS (Mantiene compatibilidad con tu DB actual)
    if etapa == "QUALY":
        # Indices 4 a 8: Q1-Q5
        row.extend([datos.get(i, "") for i in range(1, 6)])
        # Indice 9: Colapinto Q
        row.append(datos.get("colapinto_q", ""))
        # Relleno hasta el final
        row.extend([""] * 16)

    elif etapa == "SPRINT":
        # Indices 4 a 9 vacíos (lugar de Qualy)
        row.extend([""] * 6)
        # Indices 10 a 14: S1-S5
        row.extend([datos.get(i, "") for i in range(1, 6)])
        # Relleno hasta el final
        row.extend([""] * 11)

    elif etapa == "CARRERA":
        # Indices 4 a 14 vacíos (lugar de Qualy + Sprint)
        row.extend([""] * 11)
        # Indices 15 a 19: R1-R5
        row.extend([datos.get(i, "") for i in range(1, 6)])
        # Indice 20: Colapinto R
        row.append(datos.get("colapinto_r", ""))
        # Indices 21 a 23: Constructores
        row.extend([datos.get(f"c{i}", "") for i in range(1, 4)])
        
        # Indices 24-25: Campeones (Solo Australia)
        if camp_data:
            row.append(camp_data.get("piloto", ""))
            row.append(camp_data.get("equipo", ""))
        else:
            row.extend(["", ""])

    # --- GUARDADO ---
    try:
        sheet.append_row(row)
        return True, f"¡Excelente! Tu predicción de {etapa} ha sido guardada."
    except Exception as e:
        return False, f"Error al escribir en Google Sheets: {e}"

def recuperar_predicciones_piloto(usuario, gp):
    """
    NUEVA FUNCIÓN V4.0 (CORREGIDA):
    Lee la base de datos y busca qué votó el piloto.
    """
    sheet = conectar_google_sheets("sheet1")
    
    # SI FALLA LA CONEXION, DEVOLVER VACÍOS SEGUROS
    if not sheet: 
        return None, None, (None, None)
    
    try:
        registros = sheet.get_all_values()
    except:
        return None, None, (None, None)
    
    data_q = {}
    data_s = {}
    data_r = {}
    data_c = {}
    
    found_q = False
    found_s = False
    found_r = False
    
    # Recorremos la DB buscando filas que coincidan con Usuario + GP
    for row in registros[1:]:
        if len(row) > 3 and row[1] == usuario and row[2] == gp:
            etapa = row[3]
            
            if etapa == "QUALY":
                # Qualy está en indices 4 a 8 (Columnas E,F,G,H,I)
                # Colapinto Q en indice 9 (Columna J)
                for i in range(1, 6): 
                    if len(row) > 3+i: data_q[i] = row[3+i] 
                if len(row) > 9: data_q["col"] = row[9]
                found_q = True
                
            elif etapa == "SPRINT":
                # Sprint está en indices 10 a 14 (Columnas K,L,M,N,O)
                for i in range(1, 6): 
                    if len(row) > 9+i: data_s[i] = row[9+i]
                found_s = True
                
            elif etapa == "CARRERA":
                # Carrera está en indices 15 a 19 (Columnas P,Q,R,S,T)
                for i in range(1, 6): 
                    if len(row) > 14+i: data_r[i] = row[14+i]
                if len(row) > 20: data_r["col"] = row[20]
                
                # Constructores en indices 21 a 23 (Columnas V,W,X)
                if len(row) > 21: data_c[1] = row[21]
                if len(row) > 22: data_c[2] = row[22]
                if len(row) > 23: data_c[3] = row[23]
                found_r = True
    
    # RETORNOS SEGUROS
    res_q = data_q if found_q else None
    res_s = data_s if found_s else None
    res_r = (data_r, data_c) if found_r else (None, None)
                
    return res_q, res_s, res_r

def actualizar_tabla_general(piloto, puntos_nuevos, gano_qualy, gano_sprint, gano_carrera):
    """
    Suma los puntos calculados a la Tabla General ('Posiciones').
    """
    sheet = conectar_google_sheets("Posiciones")
    if sheet is None: return False, "Error al conectar con hoja Posiciones."
    
    try:
        registros = sheet.get_all_records()
        # Verificar si la hoja está vacía o mal formateada
        if not registros and len(sheet.get_all_values()) < 2:
             return False, "La hoja Posiciones parece vacía o sin títulos."

        cell = sheet.find(piloto)
        if not cell:
            return False, f"No se encontró al piloto {piloto} en la hoja Posiciones."
            
        fila = cell.row
        
        # Leer valores actuales (Celdas B, C, D, E)
        try: pts_actuales = int(sheet.cell(fila, 2).value or 0)
        except: pts_actuales = 0
        
        try: qualy_actual = int(sheet.cell(fila, 3).value or 0)
        except: qualy_actual = 0
        
        try: sprint_actual = int(sheet.cell(fila, 4).value or 0)
        except: sprint_actual = 0
        
        try: carrera_actual = int(sheet.cell(fila, 5).value or 0)
        except: carrera_actual = 0
        
        # Sumar lo nuevo
        nuevo_pts = pts_actuales + puntos_nuevos
        nueva_qualy = qualy_actual + (1 if gano_qualy else 0)
        nueva_sprint = sprint_actual + (1 if gano_sprint else 0)
        nueva_carrera = carrera_actual + (1 if gano_carrera else 0)
        
        # Guardar
        sheet.update_cell(fila, 2, nuevo_pts)
        sheet.update_cell(fila, 3, nueva_qualy)
        sheet.update_cell(fila, 4, nueva_sprint)
        sheet.update_cell(fila, 5, nueva_carrera)
        
        return True, f"✅ {piloto} ACTUALIZADO: +{puntos_nuevos} Pts (Total acumulado: {nuevo_pts})"
        
    except Exception as e:
        return False, f"Error actualizando tabla: {e}"

# ==============================================================================
# 3. LÓGICA DE TIEMPOS Y PUNTOS
# ==============================================================================

HORARIOS_CARRERA = {
    "01. Gran Premio de Australia": "2026-03-08 01:00",
    "02. Gran Premio de China": "2026-03-15 04:00",
    "03. Gran Premio de Japón": "2026-03-29 02:00",
    "04. Gran Premio de Baréin": "2026-04-12 12:00",
    "05. Gran Premio de Arabia Saudita": "2026-04-19 14:00",
    "06. Gran Premio de Miami": "2026-05-03 17:00",
    "07. Gran Premio de Canadá": "2026-05-24 17:00",
    "08. Gran Premio de Mónaco": "2026-06-07 10:00",
    "09. Gran Premio de Barcelona": "2026-06-14 10:00",
    "10. Gran Premio de Austria": "2026-06-28 10:00",
    "11. Gran Premio de Gran Bretaña": "2026-07-05 11:00",
    "12. Gran Premio de Bélgica": "2026-07-19 10:00",
    "13. Gran Premio de Hungría": "2026-07-26 10:00",
    "14. Gran Premio de los Países Bajos": "2026-08-23 10:00",
    "15. Gran Premio de Italia": "2026-09-06 10:00",
    "16. Gran Premio de Madrid": "2026-09-13 10:00",
    "17. Gran Premio de Azerbaiyán": "2026-09-27 08:00",
    "18. Gran Premio de Singapur": "2026-10-11 09:00",
    "19. Gran Premio de los Estados Unidos": "2026-10-25 17:00",
    "20. Gran Premio de México": "2026-11-01 17:00",
    "21. Gran Premio de Brasil": "2026-11-08 14:00",
    "22. Gran Premio de Las Vegas": "2026-11-21 01:00",
    "23. Gran Premio de Qatar": "2026-11-29 13:00",
    "24. Gran Premio de Abu Dabi": "2026-12-06 10:00"
}

def verificar_estado_gp(gp_seleccionado):
    """
    Verifica si estamos dentro del tiempo permitido (Desde 72hs antes hasta 1 hora antes).
    """
    if gp_seleccionado not in HORARIOS_CARRERA:
        return "ABIERTO (SIN FECHA)", True 
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_carrera = tz.localize(datetime.strptime(HORARIOS_CARRERA[gp_seleccionado], "%Y-%m-%d %H:%M"))
    ahora = datetime.now(tz)
    limite_apertura = fecha_carrera - timedelta(hours=72)
    limite_cierre = fecha_carrera - timedelta(hours=1)
    if ahora < limite_apertura:
        return "PRÓXIMAMENTE (Abre 72hs antes del evento)", False
    elif ahora > limite_cierre:
        return "TIEMPO AGOTADO (Cerrado 1 hora antes)", False
    else:
        return f"ABIERTO (Cierra: {limite_cierre.strftime('%d/%m %H:%M')})", True

def calcular_puntos(tipo, prediccion, oficial, colapinto_pred=None, colapinto_real=None):
    """
    Motor matemático para calcular los puntos en la calculadora.
    """
    puntos = 0
    aciertos = 0
    
    if tipo == "SPRINT":
        escala = {1: 8, 2: 7, 3: 6, 4: 5, 5: 4}
        bonus_perfecto = 3
    elif tipo == "CARRERA":
        escala = {1: 25, 2: 18, 3: 15, 4: 12, 5: 10}
        bonus_perfecto = 5
    elif tipo == "QUALY":
        escala = {1: 15, 2: 10, 3: 7, 4: 5, 5: 3}
        bonus_perfecto = 5 
    elif tipo == "CONSTRUCTORES":
        escala = {1: 10, 2: 5, 3: 2}
        bonus_perfecto = 3
    
    max_pos = 3 if tipo == "CONSTRUCTORES" else 5
    
    for i in range(1, max_pos + 1):
        # Conversión a string y strip para evitar errores si viene un None
        p_user = str(prediccion.get(i, "")).strip().lower()
        p_real = str(oficial.get(i, "")).strip().lower()
        
        if p_user and p_user == p_real:
            puntos += escala.get(i, 0)
            aciertos += 1
            
    if aciertos == max_pos:
        puntos += bonus_perfecto
        
    if colapinto_pred and colapinto_real and str(colapinto_pred) and str(colapinto_real):
        try:
            if int(colapinto_pred) == int(colapinto_real):
                puntos += (10 if tipo == "QUALY" else 20)
        except: pass
    return puntos

# ==============================================================================
# 4. CONFIGURACIÓN VISUAL Y ESTÉTICA (CSS COMPLETO)
# ==============================================================================

st.set_page_config(
    page_title="Torneo de Predicciones Fefe Wolf 2026",
    layout="wide",
    page_icon="🏆"
)

st.markdown("""
    <style>
    /* 1. FONDO GENERAL */
    .stApp { background-color: #0e1117; }
    header[data-testid="stHeader"] { background-color: #0e1117; }
    
    /* 2. TEXTOS */
    .stMarkdown, .stText, p, li, label, h1, h2, h3, h4, h5, h6, span, div { 
        color: #E0E0E0 !important; 
        font-family: 'Segoe UI', sans-serif; 
    }
    
    /* 3. TÍTULOS */
    h1, h2, h3 { 
        text-shadow: 0 0 10px #BF00FF; 
        color: #FFD700 !important; 
        font-family: 'Orbitron', sans-serif; 
        text-transform: uppercase;
    }

    /* 4. MENÚ LATERAL */
    section[data-testid="stSidebar"] { 
        background-color: #000000; 
        border-right: 2px solid #FFD700; 
    }

    /* 5. INPUTS */
    .stTextInput input, .stNumberInput input {
        background-color: #001f3f !important; 
        color: #FFD700 !important; 
        border: 1px solid #FFD700 !important;
    }

    /* 6. SELECTBOX */
    div[data-baseweb="select"] > div {
        background-color: #001f3f !important; 
        border: 1px solid #FFD700 !important;
        color: #FFD700 !important;
    }
    div[data-testid="stSelectbox"] div[class*="SingleValue"] {
        color: #FFD700 !important;
    }
    ul[data-baseweb="menu"] {
        background-color: #001f3f !important; 
        border: 1px solid #BF00FF !important;
    }
    li[data-baseweb="option"] {
        color: #FFD700 !important;
        background-color: #001f3f !important;
    }
    li[data-baseweb="option"]:hover, li[aria-selected="true"] {
        background-color: #BF00FF !important; 
        color: #FFFFFF !important;
    }
    
    /* 7. PLACEHOLDERS */
    ::placeholder { color: #FFD70080 !important; }

    /* 8. TABLAS */
    div[data-testid="stDataFrame"] { background-color: #0e1117; }
    thead tr th { 
        background-color: #001f3f !important; 
        color: #FFD700 !important; 
        border-bottom: 2px solid #BF00FF !important; 
    }
    tbody tr td { 
        background-color: #111 !important; 
        color: #E0E0E0 !important; 
        border: 1px solid #333 !important; 
    }

    /* 9. EXPANDERS */
    .streamlit-expanderHeader {
        background-color: #001f3f !important;
        border: 1px solid #333;
        color: #FFD700 !important;
    }
    .streamlit-expanderHeader p { color: #FFD700 !important; }
    
    /* 10. BOTONES */
    div.stButton > button { 
        background-color: #001f3f; 
        color: #FFD700; 
        border: 2px solid #FFD700; 
        border-radius: 12px; 
        font-weight: bold; 
        width: 100%;
    }
    div.stButton > button:hover { 
        background-color: #FFD700; 
        color: #000000; 
    }

    /* 11. LINK REINICIO */
    .reset-link { 
        display: block; 
        text-align: center; 
        padding: 10px; 
        background-color: #BF00FF; 
        color: white !important; 
        text-decoration: none; 
        border-radius: 8px; 
        margin-bottom: 20px; 
        font-weight: bold; 
        border: 1px solid white;
        transition: 0.3s;
    }
    .reset-link:hover { 
        background-color: #FFD700; 
        color: black !important; 
        border-color: #BF00FF;
    }
    </style>
    """, unsafe_allow_html=True)


# ==============================================================================
# 5. DATOS DEL TORNEO
# ==============================================================================

CREDENCIALES = {
    "Checo Perez": "2022", 
    "Nicki Lauda": "9595", 
    "Valteri Bottas": "9876",
    "Lando Norris": "4444", 
    "Fernando Alonso": "9292"
}
PILOTOS_TORNEO = list(CREDENCIALES.keys())

GPS_OFICIALES = list(HORARIOS_CARRERA.keys())

GPS_SPRINT = [
    "02. Gran Premio de China", 
    "06. Gran Premio de Miami", 
    "07. Gran Premio de Canadá", 
    "11. Gran Premio de Gran Bretaña", 
    "14. Gran Premio de los Países Bajos", 
    "18. Gran Premio de Singapur"
]

GRILLA_2026 = {
    "MCLAREN": ["Lando Norris", "Oscar Piastri"],
    "RED BULL": ["Max Verstappen", "Isack Hadjar"],
    "MERCEDES": ["Kimi Antonelli", "George Russell"],
    "FERRARI": ["Charles Leclerc", "Lewis Hamilton"],
    "WILLIAMS": ["Alex Albon", "Carlos Sainz"],
    "ASTON MARTIN": ["Lance Stroll", "Fernando Alonso"],
    "RACING BULLS": ["Liam Lawson", "Arvid Lindblad"],
    "HAAS": ["Oliver Bearman", "Esteban Ocon"],
    "AUDI": ["Nico Hulkenberg", "Gabriel Bortoleto"],
    "ALPINE": ["Pierre Gasly", "Franco Colapinto"],
    "CADILLAC": ["Checo Pérez", "Valtteri Bottas"],
}

CALENDARIO_VISUAL = [
    {
        "Fecha": "06-08 Mar", 
        "Gran Premio": "GP Australia", 
        "Circuito": "Melbourne", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "13-15 Mar", 
        "Gran Premio": "GP China", 
        "Circuito": "Shanghai", 
        "Formato": "⚡ SPRINT"
    },
    {
        "Fecha": "27-29 Mar", 
        "Gran Premio": "GP Japón", 
        "Circuito": "Suzuka", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "10-12 Abr", 
        "Gran Premio": "GP Bahréin", 
        "Circuito": "Sakhir", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "17-19 Abr", 
        "Gran Premio": "GP Arabia Saudita", 
        "Circuito": "Jeddah", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "01-03 May", 
        "Gran Premio": "GP Miami", 
        "Circuito": "Miami", 
        "Formato": "⚡ SPRINT"
    },
    {
        "Fecha": "22-24 May", 
        "Gran Premio": "GP Canadá", 
        "Circuito": "Montreal", 
        "Formato": "⚡ SPRINT"
    },
    {
        "Fecha": "05-07 Jun", 
        "Gran Premio": "GP Mónaco", 
        "Circuito": "Montecarlo", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "12-14 Jun", 
        "Gran Premio": "GP España", 
        "Circuito": "Barcelona", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "26-28 Jun", 
        "Gran Premio": "GP Austria", 
        "Circuito": "Spielberg", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "03-05 Jul", 
        "Gran Premio": "GP Reino Unido", 
        "Circuito": "Silverstone", 
        "Formato": "⚡ SPRINT"
    },
    {
        "Fecha": "17-19 Jul", 
        "Gran Premio": "GP Bélgica", 
        "Circuito": "Spa", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "24-26 Jul", 
        "Gran Premio": "GP Hungría", 
        "Circuito": "Budapest", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "21-23 Ago", 
        "Gran Premio": "GP Países Bajos", 
        "Circuito": "Zandvoort", 
        "Formato": "⚡ SPRINT"
    },
    {
        "Fecha": "04-06 Sep", 
        "Gran Premio": "GP Italia", 
        "Circuito": "Monza", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "11-13 Sep", 
        "Gran Premio": "GP Madrid", 
        "Circuito": "Madrid", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "25-27 Sep", 
        "Gran Premio": "GP Azerbaiyán", 
        "Circuito": "Bakú", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "09-11 Oct", 
        "Gran Premio": "GP Singapur", 
        "Circuito": "Marina Bay", 
        "Formato": "⚡ SPRINT"
    },
    {
        "Fecha": "23-25 Oct", 
        "Gran Premio": "GP Estados Unidos", 
        "Circuito": "Austin", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "30-01 Nov", 
        "Gran Premio": "GP México", 
        "Circuito": "Hermanos Rodríguez", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "06-08 Nov", 
        "Gran Premio": "GP Brasil", 
        "Circuito": "Interlagos", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "19-21 Nov", 
        "Gran Premio": "GP Las Vegas", 
        "Circuito": "Las Vegas", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "27-29 Nov", 
        "Gran Premio": "GP Qatar", 
        "Circuito": "Lusail", 
        "Formato": "Clásico"
    },
    {
        "Fecha": "04-06 Dic", 
        "Gran Premio": "GP Abu Dabi", 
        "Circuito": "Yas Marina", 
        "Formato": "Clásico"
    },
]


# ==============================================================================
# 6. APLICACIÓN PRINCIPAL
# ==============================================================================

def main():
    st.sidebar.title("🏁 MENU PRINCIPAL")
    
    # BOTÓN DE REINICIO
    st.sidebar.markdown('<a href="/" target="_self" class="reset-link">🔄 REINICIAR / HOME</a>', unsafe_allow_html=True)
    
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/3/33/F1.svg", width=50)
    st.sidebar.markdown("---")
    
    opcion = st.sidebar.radio("Navegación:", [
        "🏠 Inicio & Historia", 
        "📅 Calendario Oficial 2026",
        "🔒 Cargar Predicciones", 
        "📊 Tabla de Posiciones",
        "🧮 Calculadora de Puntos",
        "🏎️ Pilotos y Escuderías 2026",
        "🌍 Historial por GP", 
        "📜 Reglamento Oficial",
        "🏆 Muro de Campeones"
    ])

    # ACTIVAR SCROLL AUTOMÁTICO (Nueva Versión V3.1)
    scroll_to_top()

    # --- INICIO ---
    if opcion == "🏠 Inicio & Historia":
        st.markdown("<h1 style='text-align: center; color: #FFD700;'>🏆 TORNEO DE PREDICCIONES FEFE WOLF 2026🏆</h1>", unsafe_allow_html=True)
        st.markdown("<div style='text-align: center;'><b>© 2026 Derechos Reservados - Fundado por Checo Perez</b></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown("<h2 style='text-align: center; color: #FFD700;'>📜 EL LEGADO DE FEFE WOLF</h2>", unsafe_allow_html=True)
        
        # TEXTO COMPLETO RESTAURADO (VERSIÓN LARGA)
        st.markdown("""
        <div style='background-color: #111; padding: 20px; border-left: 5px solid #FFD700; border-radius: 10px;'>
        
        **EN EL PRINCIPIO, HUBO RUIDO DE MOTORES...**
        
        Corría el año 2021. El mundo estaba cambiando, y la Fórmula 1 vivía una de sus batallas más feroces. 
        En ese caos, cinco amigos decidieron que ser espectadores no era suficiente. Necesitaban ser protagonistas.
        
        Bajo la visión fundacional de **Checo Perez**, se creó este santuario. Un lugar donde la amistad se mide en puntos y el honor se juega en cada curva.
        Pero este torneo no sería posible sin nuestra guía eterna: **Fefe Wolf**. Aunque no esté físicamente en el paddock, su espíritu competitivo 
        y su sabiduría estratégica impregnan cada decisión que tomamos. Él es el "Líder Espiritual" que nos recuerda que, en la pista y en la vida, nunca hay que levantar el pie del acelerador.
        
        **LOS CINCO ELEGIDOS**
        Cinco nombres escribieron la historia. Cinco voluntades se enfrentaron a la estadistica, al azar, y a sí mismos. Somos los **Formuleros: Checo, Lauda, Bottas, Lando y Alonso**. 
        No corremos por dinero. Corremos por el derecho sagrado de decir "te lo dije" el domingo por la tarde. Cinco caminos distintos, un solo destino: *La eternidad.*
        
        Hemos visto campeones ascender y caer. Vimos a Lauda y a **Fefe Wolf** compartir la gloria del 21. Vimos el dominio implacable de Checo, actual TriCampeón. Vimos la sorpresa táctica de Bottas.
        
        Ahora, en **2026**, la era híbrida evoluciona. Audi ruge, Cadillac desafía al sistema, y Colapinto lleva la bandera argentina. Nuevos autos, nuevo reglamento, la historia continúa.
        Las cartas están echadas. La historia nos observa.
        
        *¿Quién tendrá la audacia para reclamar el trono este año?*
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>👑 EN MEMORIA DEL REY FEFE WOLF 👑</h3>", unsafe_allow_html=True)
        c_img1, c_img2, c_img3 = st.columns([1, 2, 1])
        with c_img2:
            try: st.image("IMAGENFEFE.jfif") 
            except: st.error("⚠️ Error: No se encontró 'IMAGENFEFE.jfif'")

        st.divider()
        
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>🏛️ LA CÚPULA OFICIAL DEL TORNEO 2026</h3>", unsafe_allow_html=True)
        c_img1b, c_img2b, c_img3b = st.columns([1, 2, 1])
        with c_img2b:
            try: st.image("IMAGENCUPULA.jfif")
            except: st.error("⚠️ Error: No se encontró 'IMAGENCUPULA.jfif'")
        
        st.divider()
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>👤 PILOTOS EN PARRILLA</h3>", unsafe_allow_html=True)
        col_space1, col_center, col_space2 = st.columns([1, 2, 1])
        with col_center:
            for p in PILOTOS_TORNEO:
                st.warning(f"🏎️ {p}")

    # --- CALENDARIO ---
    elif opcion == "📅 Calendario Oficial 2026":
        st.title("📅 CALENDARIO TEMPORADA 2026")
        
        c_cal1, c_cal2, c_cal3 = st.columns([1, 2, 1])
        with c_cal2:
            try:
                st.image("IMAGENCALENDARIO.jfif", caption="Mapa de la Temporada")
            except:
                st.info("ℹ️ Si quieres ver una imagen aquí, sube un archivo llamado 'IMAGENCALENDARIO.jfif'")
            
        st.divider()
        st.markdown("Todas las fechas, circuitos y formatos de la nueva era.")
        
        df_cal = pd.DataFrame(CALENDARIO_VISUAL)
        st.dataframe(
            df_cal, 
            hide_index=True, 
            width='stretch',
            column_config={
                "Fecha": st.column_config.TextColumn("Fecha", width="medium"),
                "Gran Premio": st.column_config.TextColumn("Gran Premio", width="medium"),
                "Circuito": st.column_config.TextColumn("Circuito", width="medium"),
                "Formato": st.column_config.TextColumn("Formato", width="medium"),
            }
        )

    # --- CARGA DE PREDICCIONES ---
    elif opcion == "🔒 Cargar Predicciones":
        st.title("SISTEMA DE PREDICCIÓN 2026")
        
        c1, c2 = st.columns(2)
        usuario = c1.selectbox("Piloto Participante", PILOTOS_TORNEO)
        gp_actual = c2.selectbox("Seleccionar Gran Premio", GPS_OFICIALES)
        
        mensaje_estado, habilitado = verificar_estado_gp(gp_actual)
        
        if not habilitado:
            st.error(f"🔴 **PREDICCIONES CERRADAS PARA: {gp_actual}**")
            st.warning(f"ESTADO: {mensaje_estado}")
            st.stop()
        else:
            st.success(f"🟢 **HABILITADO** | {mensaje_estado}")
        
        ES_SPRINT = gp_actual in GPS_SPRINT
        if ES_SPRINT:
            st.info("⚡ **¡ATENCIÓN! ESTE ES UN FIN DE SEMANA SPRINT** ⚡")
            
        camp_piloto, camp_equipo = "", ""
        if "Australia" in gp_actual:
            st.markdown("---")
            st.error("🚨 **EDICIÓN ESPECIAL AUSTRALIA**")
            st.write("**Puntos:** Piloto Campeón (50 pts) | Constructor Campeón (25 pts)")
            col_camp1, col_camp2 = st.columns(2)
            camp_piloto = col_camp1.text_input("🏆 Tu Predicción: PILOTO CAMPEÓN")
            camp_equipo = col_camp2.text_input("🏗️ Tu Predicción: CONSTRUCTOR CAMPEÓN")
        
        st.markdown("---")
        st.subheader("🔐 Validación")
        pin = st.text_input("Ingresa tu PIN Secreto:", type="password")
        st.markdown("---")
        
        if ES_SPRINT:
            tabs = st.tabs(["⏱️ CLASIFICACIÓN", "⚡ SPRINT", "🏁 CARRERA Y CONSTRUCTORES"])
            tab_qualy, tab_sprint, tab_race = tabs[0], tabs[1], tabs[2]
        else:
            tabs = st.tabs(["⏱️ CLASIFICACIÓN", "🏁 CARRERA Y CONSTRUCTORES"])
            tab_qualy, tab_race = tabs[0], tabs[1]
            tab_sprint = None

        with tab_qualy:
            st.subheader(f"Qualy - {gp_actual}")
            st.info("1°(15) - 2°(10) - 3°(7) - 4°(5) - 5°(3) | Pleno: +5 Pts")
            c_q1, c_q2 = st.columns(2)
            q_data = {}
            with c_q1:
                for i in range(1, 6): q_data[i] = st.text_input(f"Posición {i}° (Qualy)", key=f"q{i}")
            with c_q2:
                st.markdown("#### 🇦🇷 Regla Colapinto (Qualy)")
                st.write("**Acierto Exacto:** +10 Puntos")
                q_data["colapinto_q"] = st.number_input("Posición Franco Colapinto", 1, 22, 10, key="cq")
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 ENVIAR SOLO QUALY", width='stretch', key="btn_q"):
                if pin == CREDENCIALES.get(usuario):
                    with st.spinner("Enviando..."):
                        exito, msg = guardar_etapa(usuario, gp_actual, "QUALY", q_data)
                    if exito: st.success(msg); st.balloons()
                    else: st.error(msg)
                else: st.error("⛔ PIN INCORRECTO")

        if tab_sprint:
            with tab_sprint:
                st.subheader(f"Sprint - {gp_actual}")
                st.info("1°(8) - 2°(7) - 3°(6) - 4°(5) - 5°(4) | Pleno: +3 Pts")
                s_data = {}
                for i in range(1, 6): s_data[i] = st.text_input(f"Posición {i}° (Sprint)", key=f"s{i}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 ENVIAR SOLO SPRINT", width='stretch', key="btn_s"):
                    if pin == CREDENCIALES.get(usuario):
                        with st.spinner("Enviando..."):
                            exito, msg = guardar_etapa(usuario, gp_actual, "SPRINT", s_data)
                        if exito: st.success(msg); st.balloons()
                        else: st.error(msg)
                    else: st.error("⛔ PIN INCORRECTO")

        with tab_race:
            cr, cc = st.columns(2)
            r_data = {}
            with cr:
                st.subheader(f"Carrera - {gp_actual}")
                st.info("1°(25) - 2°(18) - 3°(15) - 4°(12) - 5°(10) | Pleno: +5 Pts")
                for i in range(1, 6): r_data[i] = st.text_input(f"Posición {i}° (Carrera)", key=f"r{i}")
                st.markdown("#### 🇦🇷 Regla Colapinto (Carrera)")
                st.write("**Acierto Exacto:** +20 Puntos")
                r_data["colapinto_r"] = st.number_input("Posición Franco Colapinto", 1, 22, 10, key="cr")

            with cc:
                st.subheader("Constructores")
                st.info("1°(10) - 2°(5) - 3°(2) | Pleno: +3 Pts")
                for i in range(1, 4): r_data[f"c{i}"] = st.text_input(f"Equipo {i}°", key=f"c{i}")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🚀 ENVIAR CARRERA Y CONSTRUCTORES", width='stretch', key="btn_r"):
                if pin == CREDENCIALES.get(usuario):
                    if "Australia" in gp_actual and (not camp_piloto or not camp_equipo):
                        st.error("⚠️ En Australia debes llenar los Campeones antes de enviar la Carrera.")
                    else:
                        with st.spinner("Enviando..."):
                            cd = {"piloto": camp_piloto, "equipo": camp_equipo} if "Australia" in gp_actual else None
                            exito, msg = guardar_etapa(usuario, gp_actual, "CARRERA", r_data, cd)
                        if exito: st.success(msg); st.balloons()
                        else: st.error(msg)
                else: st.error("⛔ PIN INCORRECTO")

    # --- CALCULADORA (CENTRO DE CÓMPUTOS V5.0 - PRIVACIDAD) ---
    elif opcion == "🧮 Calculadora de Puntos":
        st.title("🧮 CENTRO DE CÓMPUTOS")
        
        st.info("🔒 ÁREA RESTRINGIDA: Para evitar espionaje, se requiere autorización del Comisario.")
        
        # 1. GATEKEEPER (CANDADO)
        pwd = st.text_input("🔑 Ingrese Clave de Comisario:", type="password")
        
        if pwd == "2022": # CLAVE MAESTRA
            st.success("✅ ACCESO AUTORIZADO")
            st.divider()
            
            # --- AQUÍ EMPIEZA LA CALCULADORA REAL (SOLO VISIBLE SI CLAVE OK) ---
            
            # 1. SELECCIÓN DE GP Y RESULTADOS OFICIALES
            gp_calc = st.selectbox("Gran Premio a Calcular:", GPS_OFICIALES)
            
            st.subheader("1. RESULTADOS OFICIALES (FIA)")
            oficial = {}; col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                st.markdown("**🏁 Carrera**")
                for i in range(1, 6): oficial[f"r{i}"] = st.text_input(f"Oficial Carrera {i}°", key=f"of_r{i}")
                oficial["col_r"] = st.number_input("Oficial Colapinto (Carrera)", 1, 22, 10, key="of_cr")
            with col_res2:
                st.markdown("**⏱️ Qualy**")
                for i in range(1, 6): oficial[f"q{i}"] = st.text_input(f"Oficial Qualy {i}°", key=f"of_q{i}")
                oficial["col_q"] = st.number_input("Oficial Colapinto (Qualy)", 1, 22, 10, key="of_cq")
            with col_res3:
                st.markdown("**🛠️ Constructores**")
                for i in range(1, 4): oficial[f"c{i}"] = st.text_input(f"Oficial Const {i}°", key=f"of_c{i}")
            
            st.divider()
            
            # 2. SELECCIÓN DE PILOTO Y RECUPERACIÓN AUTOMÁTICA
            st.subheader("2. CALCULAR PUNTOS DE PILOTO")
            c_user, c_pin = st.columns(2)
            piloto_calc = c_user.selectbox("Seleccionar Piloto:", PILOTOS_TORNEO)
            
            # BUSCAR DATOS AUTOMÁTICAMENTE (CON FUNCIÓN BLINDADA V4.0)
            db_qualy, db_sprint, (db_race, db_const) = recuperar_predicciones_piloto(piloto_calc, gp_calc)
            
            if db_qualy or db_race:
                st.success(f"✅ Se encontraron predicciones guardadas de {piloto_calc}")
            else:
                st.warning(f"⚠️ {piloto_calc} NO ha enviado predicciones para {gp_calc} (o no se pudieron leer).")

            # MOSTRAR PREDICCIONES
            st.markdown(f"**Predicciones recuperadas de la Base de Datos para {piloto_calc}:**")
            c_pred1, c_pred2, c_pred3 = st.columns(3)
            
            # Usamos valores por defecto si no hay datos
            val_r = db_race if db_race else {}
            val_q = db_qualy if db_qualy else {}
            val_c = db_const if db_const else {}
            val_s = db_sprint if db_sprint else {}
            
            with c_pred1:
                st.write(f"**Carrera:** {val_r.get(1,'-')}, {val_r.get(2,'-')}, {val_r.get(3,'-')}, {val_r.get(4,'-')}, {val_r.get(5,'-')}")
                st.write(f"**Colapinto R:** {val_r.get('col','-')}")
            with c_pred2:
                st.write(f"**Qualy:** {val_q.get(1,'-')}, {val_q.get(2,'-')}, {val_q.get(3,'-')}, {val_q.get(4,'-')}, {val_q.get(5,'-')}")
                st.write(f"**Colapinto Q:** {val_q.get('col','-')}")
            with c_pred3:
                st.write(f"**Const:** {val_c.get(1,'-')}, {val_c.get(2,'-')}, {val_c.get(3,'-')}")
            
            if db_sprint:
                st.info(f"⚡ Sprint: {val_s.get(1,'-')}, {val_s.get(2,'-')}, ...")
            
            # 3. OPCIONES EXTRAS
            st.divider()
            col_ex1, col_ex2 = st.columns(2)
            with col_ex1:
                aplicar_sancion = st.checkbox(f"❌ Sancionar a {piloto_calc} (-5 Pts)", value=False)
            with col_ex2:
                st.markdown("**¿Ganó alguna sesión?**")
                gano_qualy = st.checkbox("🥇 Ganó Qualy", key="gq")
                gano_sprint = st.checkbox("🥇 Ganó Sprint", key="gs")
                gano_carrera = st.checkbox("🥇 Ganó Carrera", key="gr")

            # 4. BOTÓN CALCULAR
            if st.button("CALCULAR TOTAL AUTOMÁTICO", width='stretch'):
                # Preparar diccionarios oficiales
                of_r = {i: oficial[f"r{i}"] for i in range(1, 6)}
                of_q = {i: oficial[f"q{i}"] for i in range(1, 6)}
                of_c = {i: oficial[f"c{i}"] for i in range(1, 4)}
                
                # Calcular usando lo recuperado de la DB
                pts_carrera = calcular_puntos("CARRERA", val_r, of_r, val_r.get('col'), oficial["col_r"])
                pts_qualy = calcular_puntos("QUALY", val_q, of_q, val_q.get('col'), oficial["col_q"])
                pts_const = calcular_puntos("CONSTRUCTORES", val_c, of_c)
                pts_sprint = 0 # Agregar lógica sprint si fuese necesario
                
                total = pts_carrera + pts_qualy + pts_const + pts_sprint
                if aplicar_sancion: total -= 5
                
                st.success(f"💰 PUNTOS TOTALES DE {piloto_calc}: **{total}**")
                st.info(f"Desglose: Carrera ({pts_carrera}) + Qualy ({pts_qualy}) + Const ({pts_const})")
                
                # Guardar en estado para el botón de confirmar
                st.session_state['total_calc'] = total
                st.session_state['piloto_calc'] = piloto_calc

            # 5. BOTÓN GUARDAR
            if 'total_calc' in st.session_state:
                st.divider()
                if st.button(f"💾 GUARDAR {st.session_state['total_calc']} PTS EN TABLA"):
                    with st.spinner("Actualizando posiciones..."):
                        ok, msg = actualizar_tabla_general(st.session_state['piloto_calc'], st.session_state['total_calc'], gano_qualy, gano_sprint, gano_carrera)
                    if ok: st.success(msg); st.balloons()
                    else: st.error(msg)
        
        elif pwd:
            st.error("⛔ ACCESO DENEGADO.")
            st.stop()

    # --- TABLA DE POSICIONES (V3.0 LEÍDA DE DB) ---
    elif opcion == "📊 Tabla de Posiciones":
        st.title("TABLA GENERAL 2026")
        
        sheet = conectar_google_sheets("Posiciones")
        df_pos = pd.DataFrame() # Start empty
        
        if sheet:
            try:
                data = sheet.get_all_records()
                if data:
                    df_pos = pd.DataFrame(data)
            except:
                pass
        
        # If empty (connection failed or empty sheet), create default table with 0s
        if df_pos.empty:
            df_pos = pd.DataFrame({
                "Piloto": PILOTOS_TORNEO,
                "Puntos": [0] * 5,
                "Qualys": [0] * 5,
                "Sprints": [0] * 5,
                "Carreras": [0] * 5
            })

        # Display
        if not df_pos.empty:
            if "Puntos" in df_pos.columns:
                df_pos = df_pos.sort_values(by="Puntos", ascending=False)
                
            st.dataframe(
                df_pos, 
                hide_index=True, 
                width='stretch',
                column_config={
                    "Puntos": st.column_config.NumberColumn("🏆 Puntos", format="%d"),
                    "Qualys": st.column_config.NumberColumn("⏱️ Polemans", format="%d"),
                    "Sprints": st.column_config.NumberColumn("⚡ Sprints", format="%d"),
                    "Carreras": st.column_config.NumberColumn("🏁 Victorias", format="%d")
                }
            )
            
        st.info("ℹ️ Esta tabla se actualiza automáticamente los domingos tras la carrera.")

    # --- PARRILLA ---
    elif opcion == "🏎️ Pilotos y Escuderías 2026":
        st.title("PARRILLA OFICIAL F1 2026")
        for equipo, pilotos in GRILLA_2026.items():
            with st.expander(f"🛡️ {equipo}", expanded=False):
                c1, c2 = st.columns(2)
                c1.warning(f"🏎️ {pilotos[0]}")
                c2.warning(f"🏎️ {pilotos[1]}")

    # --- REGLAMENTO ---
    elif opcion == "📜 Reglamento Oficial":
        st.title("REGLAMENTO OFICIAL 2026")
        st.markdown("""
        ### ⚠️ REGLA DE ESCRITURA
        **LOS NOMBRES DE PILOTOS Y EQUIPOS DEBEN ESCRIBIRSE EXACTAMENTE IGUAL A LA SECCIÓN 'PILOTOS Y ESCUDERÍAS'.**
        SI UN NOMBRE ESTÁ MAL ESCRITO, EL SISTEMA NO DETECTARÁ EL ACIERTO Y **NO SUMARÁ PUNTOS**.
        
        ---
        
        ### ⚔️ SISTEMA DE PUNTUACIÓN OFICIAL ⚔️
        
        **🏁 CARRERA PRINCIPAL:**
        * 1° (25), 2° (18), 3° (15), 4° (12), 5° (10).
        * **Pleno (5 Aciertos):** +5 Puntos.
        * **Total Máx:** 85 Puntos.
        
        **⏱️ CLASIFICACIÓN:**
        * 1° (15), 2° (10), 3° (7), 4° (5), 5° (3).
        * **Pleno:** +5 Puntos.
        * **Total Máx:** 45 Puntos.
        
        **⚡ SPRINT (Si hay):**
        * 1° (8), 2° (7), 3° (6), 4° (5), 5° (4).
        * **Pleno:** +3 Puntos.
        * **Total Máx:** 33 Puntos.
        
        **🛠️ CONSTRUCTORES:**
        * 1° (10), 2° (5), 3° (2).
        * **Pleno:** +3 Puntos.
        * **Total Máx:** 20 Puntos.
        * *Nota: Se basa en los puntos sumados por equipo según FIA.*
        
        **🇦🇷 REGLA COLAPINTO:**
        * Acierto Exacto en Qualy: **+10 Puntos**.
        * Acierto Exacto en Carrera: **+20 Puntos**.
        
        ---
        
        ### ⛔ SANCIONES POR NO ENVÍO (D.N.S.)
        Si un piloto no envía su predicción a tiempo:
        
        * **FALTA EN CLASIFICACIÓN:** -5 Puntos.
        * **FALTA EN SPRINT (Si hay):** -5 Puntos.
        * **FALTA EN CARRERA + CONSTRUCTORES:** -5 Puntos.
          *(Carrera y Constructores cuentan como un bloque único. Si faltan ambos, la sanción es de 5 puntos en total, NO de 10).*
        
        **OTRAS REGLAS:**
        * **Desempate:** Gana quien envió primero.
        """)

    # --- MURO DE CAMPEONES ---
    elif opcion == "🏆 Muro de Campeones":
        st.header("🧱 MURO DE CAMPEONES")
        
        c_muro1, c_muro2, c_muro3 = st.columns([1, 2, 1])
        with c_muro2:
            try: st.image("IMAGENMURO.jfif")
            except: st.error("⚠️ Error: No se encontró 'IMAGENMURO.jfif'")
        
        st.divider()
        st.subheader("👑 HALL OF FAME")
        
        st.markdown("""
        <div style='background-color: #001f3f; padding: 15px; border-radius: 10px; border: 1px solid #FFD700; margin-bottom: 15px; text-align: center;'>
            <h3 style='color: #FFD700; margin:0; text-shadow: 0 0 5px #BF00FF;'>🥇 CHECO PEREZ</h3>
            <p style='color: #FFD700; font-size: 24px; margin: 5px 0;'>⭐⭐⭐</p>
            <p style='color: #E0E0E0; font-size: 16px; margin:0;'>Tricampeón: 2022, 2023, 2025</p>
        </div>
        
        <div style='background-color: #001f3f; padding: 15px; border-radius: 10px; border: 1px solid #FFD700; margin-bottom: 15px; text-align: center;'>
            <h3 style='color: #FFD700; margin:0; text-shadow: 0 0 5px #BF00FF;'>🥇 VALTERI BOTTAS</h3>
            <p style='color: #FFD700; font-size: 24px; margin: 5px 0;'>⭐</p>
            <p style='color: #E0E0E0; font-size: 16px; margin:0;'>Campeón 2024</p>
        </div>

        <div style='background-color: #001f3f; padding: 15px; border-radius: 10px; border: 1px solid #FFD700; margin-bottom: 15px; text-align: center;'>
            <h3 style='color: #FFD700; margin:0; text-shadow: 0 0 5px #BF00FF;'>🥇 FEFE WOLF</h3>
            <p style='color: #FFD700; font-size: 24px; margin: 5px 0;'>⭐</p>
            <p style='color: #E0E0E0; font-size: 16px; margin:0;'>Campeón 2021</p>
        </div>

        <div style='background-color: #001f3f; padding: 15px; border-radius: 10px; border: 1px solid #FFD700; margin-bottom: 15px; text-align: center;'>
            <h3 style='color: #FFD700; margin:0; text-shadow: 0 0 5px #BF00FF;'>🥇 NICKI LAUDA</h3>
            <p style='color: #FFD700; font-size: 24px; margin: 5px 0;'>⭐</p>
            <p style='color: #E0E0E0; font-size: 16px; margin:0;'>Campeón 2021</p>
        </div>
        """, unsafe_allow_html=True)

    # --- HISTORIAL ---
    elif opcion == "🌍 Historial por GP":
        st.title("HISTORIAL DE RESULTADOS")
        gp_view = st.selectbox("Seleccionar GP", GPS_OFICIALES)
        st.write(f"Viendo estadísticas de: **{gp_view}**")
        st.warning("Sin datos.")

if __name__ == "__main__":
    main()