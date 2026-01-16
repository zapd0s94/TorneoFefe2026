import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
import gspread
from google.oauth2.service_account import Credentials
import streamlit.components.v1 as components  # NECESARIO PARA EL SCROLL

# ==============================================================================
# 1. TRUCOS DE MAGIA (JAVASCRIPT) PARA MÓVIL
# ==============================================================================

def scroll_to_top():
    """
    Inyecta un script invisible que fuerza al navegador a subir
    al inicio de la página cada vez que se carga una sección.
    Ayuda a que el menú no tape el contenido en celulares.
    """
    js = """
    <script>
        var body = window.parent.document.querySelector(".main");
        console.log(body);
        body.scrollTop = 0;
    </script>
    """
    components.html(js, height=0)

# ==============================================================================
# 2. CONFIGURACIÓN Y CONEXIÓN CON GOOGLE SHEETS
# ==============================================================================

def conectar_google_sheets():
    """
    Conecta con la API de Google Sheets usando el archivo credentials.json
    o los Secrets de Streamlit Cloud.
    """
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # INTENTO 1: Buscar en la Caja Fuerte de la Nube (Streamlit Secrets)
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        # INTENTO 2: Buscar archivo local (Tu PC)
        else:
            creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
            
        client = gspread.authorize(creds)
        # Abre la hoja por su nombre EXACTO
        sheet = client.open("TorneoFefe2026_DB").sheet1
        return sheet
    except Exception as e:
        return None

def guardar_etapa(usuario, gp, etapa, datos, camp_data=None):
    """
    Guarda los datos en Google Sheets verificando que no existan duplicados.
    """
    sheet = conectar_google_sheets()
    if sheet is None:
        return False, "Error CRÍTICO: No se pudo conectar con la Base de Datos. Revisa 'credentials.json'."

    # --- PASO DE SEGURIDAD: VERIFICAR DUPLICADOS ---
    try:
        registros = sheet.get_all_values()
        
        # Recorremos las filas (saltando la primera que son los títulos)
        # Columna B (índice 1) es PILOTO, Columna C (índice 2) es GP, Columna D (índice 3) es ETAPA
        for fila in registros[1:]:
            if len(fila) > 3: # Verificar que la fila tenga datos suficientes
                piloto_guardado = fila[1]
                gp_guardado = fila[2]
                etapa_guardada = fila[3]
                
                if piloto_guardado == usuario and gp_guardado == gp and etapa_guardada == etapa:
                    return False, f"⛔ ERROR DE SEGURIDAD: Ya enviaste la fase de {etapa} para el {gp}. No se permiten reenvíos."
    except Exception as e:
        return False, f"Error técnico validando duplicados: {e}"

    # --- PREPARACIÓN DE LA FECHA ---
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    fecha_hora = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    # --- ARMADO DE LA FILA PARA EXCEL ---
    # Orden: [Fecha, Piloto, GP, Etapa, ...]
    row = [fecha_hora, usuario, gp, etapa]
    
    # LÓGICA SEGÚN LA ETAPA QUE SE ESTÁ ENVIANDO
    if etapa == "QUALY":
        # Guardamos Q1-Q5 (5 columnas)
        row.extend([datos.get(i, "") for i in range(1, 6)])
        # Guardamos Colapinto Qualy (1 columna)
        row.append(datos.get("colapinto_q", ""))
        
        # Rellenamos con VACÍO todo el resto (Sprint, Carrera, Constructores, Campeones)
        row.extend([""] * 16)

    elif etapa == "SPRINT":
        # Dejamos espacio de Qualy (6 columnas) vacíos
        row.extend([""] * 6)
        
        # Guardamos Sprint (5 columnas)
        row.extend([datos.get(i, "") for i in range(1, 6)])
        
        # Rellenamos el resto vacíos (11 columnas)
        row.extend([""] * 11)

    elif etapa == "CARRERA":
        # Dejamos espacio Qualy(6) + Sprint(5) = 11 vacíos
        row.extend([""] * 11)
        
        # Guardamos Carrera (5 columnas)
        row.extend([datos.get(i, "") for i in range(1, 6)])
        # Guardamos Colapinto Carrera (1 columna)
        row.append(datos.get("colapinto_r", ""))
        
        # Guardamos Constructores (3 columnas)
        row.extend([datos.get(f"c{i}", "") for i in range(1, 4)])
        
        # Guardamos Campeones (Solo si es Australia)
        if camp_data:
            row.append(camp_data.get("piloto", ""))
            row.append(camp_data.get("equipo", ""))
        else:
            row.extend(["", ""])

    # --- ESCRITURA FINAL EN LA NUBE ---
    try:
        sheet.append_row(row)
        return True, f"¡Excelente! Tu predicción de {etapa} ha sido guardada en la base de datos oficial."
    except Exception as e:
        return False, f"Error al escribir en Google Sheets: {e}"


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

    fecha_carrera_str = HORARIOS_CARRERA[gp_seleccionado]
    tz = pytz.timezone('America/Argentina/Buenos_Aires')
    
    fecha_carrera = datetime.strptime(fecha_carrera_str, "%Y-%m-%d %H:%M")
    fecha_carrera = tz.localize(fecha_carrera)
    
    ahora = datetime.now(tz)
    
    limite_apertura = fecha_carrera - timedelta(hours=72) # Abre 3 días antes
    limite_cierre = fecha_carrera - timedelta(hours=1)    # Cierra 1 hora antes
    
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
        p_user = str(prediccion.get(i, "")).strip().lower()
        p_real = str(oficial.get(i, "")).strip().lower()
        
        if p_user and p_user == p_real:
            puntos += escala.get(i, 0)
            aciertos += 1
            
    if aciertos == max_pos:
        puntos += bonus_perfecto
        
    if colapinto_pred and colapinto_real:
        if int(colapinto_pred) == int(colapinto_real):
            if tipo == "QUALY":
                puntos += 10
            elif tipo == "CARRERA":
                puntos += 20
                
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
    
    /* 2. TEXTOS (Siempre visibles, color gris claro para contraste) */
    .stMarkdown, .stText, p, li, label, h1, h2, h3, h4, h5, h6, span, div { 
        color: #E0E0E0 !important; 
        font-family: 'Segoe UI', sans-serif; 
    }
    
    /* 3. TÍTULOS CON NEÓN DORADO/VIOLETA */
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

    /* 5. INPUTS DE TEXTO Y NÚMEROS (FONDO AZUL OSCURO, SIN BLANCOS) */
    .stTextInput input, .stNumberInput input {
        background-color: #001f3f !important; 
        color: #FFD700 !important; 
        border: 1px solid #FFD700 !important;
    }

    /* 6. MENÚS DESPLEGABLES (SELECTBOX) */
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

    /* 9. EXPANDERS (ESCUDERIAS) */
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

    /* 11. ESTILO PARA EL LINK DE REINICIO (NUEVO) */
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
    {"Fecha": "06-08 Mar", "Gran Premio": "GP Australia", "Circuito": "Melbourne", "Formato": "Clásico"},
    {"Fecha": "13-15 Mar", "Gran Premio": "GP China", "Circuito": "Shanghai", "Formato": "⚡ SPRINT"},
    {"Fecha": "27-29 Mar", "Gran Premio": "GP Japón", "Circuito": "Suzuka", "Formato": "Clásico"},
    {"Fecha": "10-12 Abr", "Gran Premio": "GP Bahréin", "Circuito": "Sakhir", "Formato": "Clásico"},
    {"Fecha": "17-19 Abr", "Gran Premio": "GP Arabia Saudita", "Circuito": "Jeddah", "Formato": "Clásico"},
    {"Fecha": "01-03 May", "Gran Premio": "GP Miami", "Circuito": "Miami", "Formato": "⚡ SPRINT"},
    {"Fecha": "22-24 May", "Gran Premio": "GP Canadá", "Circuito": "Montreal", "Formato": "⚡ SPRINT"},
    {"Fecha": "05-07 Jun", "Gran Premio": "GP Mónaco", "Circuito": "Montecarlo", "Formato": "Clásico"},
    {"Fecha": "12-14 Jun", "Gran Premio": "GP España", "Circuito": "Barcelona", "Formato": "Clásico"},
    {"Fecha": "26-28 Jun", "Gran Premio": "GP Austria", "Circuito": "Spielberg", "Formato": "Clásico"},
    {"Fecha": "03-05 Jul", "Gran Premio": "GP Reino Unido", "Circuito": "Silverstone", "Formato": "⚡ SPRINT"},
    {"Fecha": "17-19 Jul", "Gran Premio": "GP Bélgica", "Circuito": "Spa", "Formato": "Clásico"},
    {"Fecha": "24-26 Jul", "Gran Premio": "GP Hungría", "Circuito": "Budapest", "Formato": "Clásico"},
    {"Fecha": "21-23 Ago", "Gran Premio": "GP Países Bajos", "Circuito": "Zandvoort", "Formato": "⚡ SPRINT"},
    {"Fecha": "04-06 Sep", "Gran Premio": "GP Italia", "Circuito": "Monza", "Formato": "Clásico"},
    {"Fecha": "11-13 Sep", "Gran Premio": "GP Madrid", "Circuito": "Madrid", "Formato": "Clásico"},
    {"Fecha": "25-27 Sep", "Gran Premio": "GP Azerbaiyán", "Circuito": "Bakú", "Formato": "Clásico"},
    {"Fecha": "09-11 Oct", "Gran Premio": "GP Singapur", "Circuito": "Marina Bay", "Formato": "⚡ SPRINT"},
    {"Fecha": "23-25 Oct", "Gran Premio": "GP Estados Unidos", "Circuito": "Austin", "Formato": "Clásico"},
    {"Fecha": "30-01 Nov", "Gran Premio": "GP México", "Circuito": "Hermanos Rodríguez", "Formato": "Clásico"},
    {"Fecha": "06-08 Nov", "Gran Premio": "GP Brasil", "Circuito": "Interlagos", "Formato": "Clásico"},
    {"Fecha": "19-21 Nov", "Gran Premio": "GP Las Vegas", "Circuito": "Las Vegas", "Formato": "Clásico"},
    {"Fecha": "27-29 Nov", "Gran Premio": "GP Qatar", "Circuito": "Lusail", "Formato": "Clásico"},
    {"Fecha": "04-06 Dic", "Gran Premio": "GP Abu Dabi", "Circuito": "Yas Marina", "Formato": "Clásico"},
]


# ==============================================================================
# 6. APLICACIÓN PRINCIPAL
# ==============================================================================

def main():
    st.sidebar.title("🏁 MENU PRINCIPAL")
    
    # --- BOTÓN DE REINICIO/HOME (SOLUCIÓN MÓVIL) ---
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

    # --- ACTIVAR SCROLL AUTOMÁTICO (SOLUCIÓN MÓVIL) ---
    # Esto fuerza al navegador a subir cada vez que Streamlit recarga
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
        # IMAGEN CON COLUMNAS PARA ACHICAR
        c_img1, c_img2, c_img3 = st.columns([1, 2, 1])
        with c_img2:
            try: st.image("IMAGENFEFE.jfif") 
            except: st.error("⚠️ Error: No se encontró 'IMAGENFEFE.jfif'")

        st.divider()
        
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>🏛️ LA CÚPULA OFICIAL DEL TORNEO 2026</h3>", unsafe_allow_html=True)
        # IMAGEN CON COLUMNAS PARA ACHICAR
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

    # --- CALENDARIO (CON IMAGEN ACHICADA) ---
    elif opcion == "📅 Calendario Oficial 2026":
        st.title("📅 CALENDARIO TEMPORADA 2026")
        
        # IMAGEN CON COLUMNAS PARA ACHICAR
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
        
        # VERIFICACIÓN DE TIEMPO
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
            
        # Variables Campeon (Australia)
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

        # --- PESTAÑA QUALY ---
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

        # --- PESTAÑA SPRINT ---
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

        # --- PESTAÑA CARRERA ---
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
                    # Validar campeones si es Australia
                    if "Australia" in gp_actual and (not camp_piloto or not camp_equipo):
                        st.error("⚠️ En Australia debes llenar los Campeones antes de enviar la Carrera.")
                    else:
                        with st.spinner("Enviando..."):
                            cd = {"piloto": camp_piloto, "equipo": camp_equipo} if "Australia" in gp_actual else None
                            exito, msg = guardar_etapa(usuario, gp_actual, "CARRERA", r_data, cd)
                        if exito: st.success(msg); st.balloons()
                        else: st.error(msg)
                else: st.error("⛔ PIN INCORRECTO")

    # --- CALCULADORA ---
    elif opcion == "🧮 Calculadora de Puntos":
        st.title("🧮 CALCULADORA OFICIAL DEL COMISARIO")
        st.markdown("Utiliza esta herramienta el domingo para calcular los puntos exactos.")
        
        st.subheader("1. RESULTADOS OFICIALES (FIA)")
        oficial = {}
        col_res1, col_res2, col_res3 = st.columns(3)
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
        st.subheader("2. EVALUAR PILOTO")
        
        aplicar_sancion = st.checkbox("❌ PILOTO NO ENVIÓ A TIEMPO (Sanción -5 Pts)", value=False)
        st.caption("Si marcas esto, se descontarán 5 puntos del total automáticamente.")

        pred = {}
        c_pred1, c_pred2, c_pred3 = st.columns(3)
        with c_pred1:
            st.markdown("Predicción Carrera")
            pred_r = {i: st.text_input(f"Pred {i}° Carrera", key=f"pr_r{i}") for i in range(1, 6)}
            col_r_pred = st.number_input("Pred Colapinto Carrera", 1, 22, 10, key="pr_cr")
        with c_pred2:
            st.markdown("Predicción Qualy")
            pred_q = {i: st.text_input(f"Pred {i}° Qualy", key=f"pr_q{i}") for i in range(1, 6)}
            col_q_pred = st.number_input("Pred Colapinto Qualy", 1, 22, 10, key="pr_cq")
        with c_pred3:
            st.markdown("Predicción Constructores")
            pred_c = {i: st.text_input(f"Pred {i}° Const", key=f"pr_c{i}") for i in range(1, 4)}

        if st.button("CALCULAR PUNTOS TOTALES", width='stretch'):
            oficial_r_dict = {i: oficial[f"r{i}"] for i in range(1, 6)}
            oficial_q_dict = {i: oficial[f"q{i}"] for i in range(1, 6)}
            oficial_c_dict = {i: oficial[f"c{i}"] for i in range(1, 4)}
            
            pts_carrera = calcular_puntos("CARRERA", pred_r, oficial_r_dict, col_r_pred, oficial["col_r"])
            pts_qualy = calcular_puntos("QUALY", pred_q, oficial_q_dict, col_q_pred, oficial["col_q"])
            pts_const = calcular_puntos("CONSTRUCTORES", pred_c, oficial_c_dict)
            
            total = pts_carrera + pts_qualy + pts_const
            
            msg_sancion = ""
            if aplicar_sancion:
                total -= 5
                msg_sancion = " (Incluye -5 de Sanción)"
            
            st.success(f"💰 RESULTADO FINAL: **{total} PUNTOS** {msg_sancion}")
            st.info(f"Desglose: Carrera ({pts_carrera}) + Qualy ({pts_qualy}) + Constructores ({pts_const})")

    # --- TABLA DE POSICIONES ---
    elif opcion == "📊 Tabla de Posiciones":
        st.title("TABLA GENERAL 2026")
        
        data_posiciones = {
            "Piloto": PILOTOS_TORNEO,
            "Puntos": [0, 0, 0, 0, 0], 
            "Qualys Ganadas": [0, 0, 0, 0, 0],
            "Sprints Ganadas": [0, 0, 0, 0, 0],
            "Carreras Ganadas": [0, 0, 0, 0, 0],
            "Constructores Ganados": [0, 0, 0, 0, 0],
            "envio_oculto": [5, 4, 3, 2, 1] 
        }
        
        df_pos = pd.DataFrame(data_posiciones)
        df_pos = df_pos.sort_values(by=["Puntos", "envio_oculto"], ascending=[False, True])
        
        st.dataframe(
            df_pos, hide_index=True, width='stretch',
            column_order=["Piloto", "Puntos", "Qualys Ganadas", "Sprints Ganadas", "Carreras Ganadas", "Constructores Ganados"],
            column_config={"Puntos": st.column_config.NumberColumn("🏆 Puntos", format="%d")})
        st.info("ℹ️ Desempate: Se define por orden de llegada de la predicción.")

    # --- PARRILLA ---
    elif opcion == "🏎️ Pilotos y Escuderías 2026":
        st.title("PARRILLA OFICIAL F1 2026")
        for equipo, pilotos in GRILLA_2026.items():
            with st.expander(f"🛡️ {equipo}", expanded=False):
                c1, c2 = st.columns(2)
                c1.warning(f"🏎️ {pilotos[0]}")
                c2.warning(f"🏎️ {pilotos[1]}")

    # --- REGLAMENTO (ACTUALIZADO CON -5 PTS) ---
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

    # --- MURO DE CAMPEONES (CON IMAGEN ACHICADA) ---
    elif opcion == "🏆 Muro de Campeones":
        st.header("🧱 MURO DE CAMPEONES")
        
        # IMAGEN CON COLUMNAS PARA ACHICAR
        c_muro1, c_muro2, c_muro3 = st.columns([1, 2, 1])
        with c_muro2:
            try: st.image("IMAGENMURO.jfif")
            except: st.error("⚠️ Error: No se encontró 'IMAGENMURO.jfif'")
        
        st.divider()
        st.subheader("👑 SALON DE LA FAMA")
        
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