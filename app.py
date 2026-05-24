import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import datetime
import urllib.request
import re

# ==========================================
# 0. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="Prode F1", page_icon="🏆", layout="wide")

# CSS personalizado basado en la interfaz "Pit Wall Command"
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,600;0,700;1,700&family=JetBrains+Mono:wght@400;500;700&display=swap');

    /* Fondo principal con textura Fibra de Carbono y color de texto base */
    .stApp {
        background-color: #0d0d0d;
        background-image: url('data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSI0IiBoZWlnaHQ9IjQiIHZpZXdCb3g9IjAgMCA0IDQiPjxyZWN0IHdpZHRoPSIyIiBoZWlnaHQ9IjIiIGZpbGw9IiNmZmZmZmYwNSIvPjwvc3ZnPg==');
        background-repeat: repeat;
        color: #e0e0e0;
    }
    
    /* Tipografías para Títulos */
    h1 {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-size: 42px !important;
        color: #ff1e1e !important;
        text-transform: uppercase;
        font-style: italic;
        letter-spacing: -0.02em;
    }
    h2, h3 {
        font-family: 'Barlow Condensed', sans-serif !important;
        color: #ffffff !important;
        text-transform: uppercase;
        letter-spacing: 0.02em;
    }

    /* Estilo de la Tabla Principal (Glass Panel) */
    .styled-table { 
        width: 100%; 
        border-collapse: collapse; 
        margin-top: 15px; 
        font-size: 14px; 
        text-align: center; 
        font-family: 'JetBrains Mono', monospace; 
        background-color: #141414;
        border: 1px solid #262626;
        border-radius: 4px;
    }
    .styled-table th { 
        background-color: #1a1a1a; 
        color: #00f2ff; 
        padding: 12px 4px; 
        font-weight: 600; 
        text-align: center; 
        text-transform: uppercase;
        border-bottom: 1px solid #262626;
        font-size: 12px;
        letter-spacing: 0.05em;
    }
    .styled-table td { 
        padding: 10px 4px; 
        border-bottom: 1px solid #262626; 
        color: #e0e0e0;
        vertical-align: middle;
    }
    .styled-table tr:hover { 
        background-color: #1a1a1a; 
    }
    
    /* Personalización de los Tabs (Pestañas) */
    .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
    .stTabs [data-baseweb="tab"] { 
        font-family: 'JetBrains Mono', monospace; 
        color: #8c8c8c; 
        text-transform: uppercase;
        font-size: 14px;
    }
    .stTabs [aria-selected="true"] { 
        color: #00f2ff !important; 
        border-bottom-color: #00f2ff !important; 
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🏆 Prode F1 Mundial")

PUNTOS_POLE = 3
PUNTOS_COLAPINTO = 3
PUNTOS_PODIO_PERFECTO = 3

# Colores originales para gráficas
colores_graficas = {
    "Juan": "#E80020", "Lencioni": "#3671C6", "Santoni": "#27F4D2",
    "Facu": "#FF8700", "Cristian": "#229971", "Jota": "#0093CC",
    "Matias": "#B6BABD", "Ochoa": "#52E252"
}

# Colores con opacidad
colores_celdas = {
    "Juan": "#E8002033", "Lencioni": "#3671C633", "Santoni": "#27F4D233",
    "Facu": "#FF870033", "Cristian": "#22997133", "Jota": "#0093CC33",
    "Matias": "#B6BABD33", "Ochoa": "#52E25233"
}

# ==========================================
# 1. CARGA DE DATOS DESDE GOOGLE SHEETS
# ==========================================
@st.cache_data(ttl=60)
def cargar_datos():
    url_pred = "https://docs.google.com/spreadsheets/d/11gBnVys8KZY3hFZPn4CgYyNxQi-2oi2PrkumdSfq08o/export?format=csv&gid=899122525"
    url_res = "https://docs.google.com/spreadsheets/d/11gBnVys8KZY3hFZPn4CgYyNxQi-2oi2PrkumdSfq08o/export?format=csv&gid=850884406"
    df_p = pd.read_csv(url_pred)
    df_r = pd.read_csv(url_res)
    return df_p, df_r

try:
    df_pred, df_res = cargar_datos()
except Exception as e:
    st.error("Error al cargar los datos desde Google Sheets. Verifica los permisos del archivo.")
    st.stop()

# ==========================================
# 2. LIMPIEZA Y VALIDACIÓN
# ==========================================
df_pred.columns = df_pred.columns.str.strip()
df_res.columns = df_res.columns.str.strip()

for col in df_pred.columns:
    if df_pred[col].dtype == 'object':
        df_pred[col] = df_pred[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
for col in df_res.columns:
    if df_res[col].dtype == 'object':
        df_res[col] = df_res[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

if 'Posición Colapinto' in df_pred.columns:
    df_pred['Posición Colapinto'] = df_pred['Posición Colapinto'].astype(str).str.replace('.0', '', regex=False).str.strip().replace('nan', '')
if 'Posición Colapinto' in df_res.columns:
    df_res['Posición Colapinto'] = df_res['Posición Colapinto'].astype(str).str.replace('.0', '', regex=False).str.strip().replace('nan', '')

df_res['Fecha Cierre'] = pd.to_datetime(df_res['Fecha Cierre'], dayfirst=True, errors='coerce')
col_fecha = 'Marca temporal' if 'Marca temporal' in df_pred.columns else df_pred.columns[0]
df_pred[col_fecha] = pd.to_datetime(df_pred[col_fecha], dayfirst=True, errors='coerce')

cierres_dict = df_res.dropna(subset=['Fecha Cierre']).set_index('Carrera')['Fecha Cierre'].to_dict()
df_pred = df_pred.sort_values(col_fecha)

def validar_tiempo(row):
    gp = row['Carrera']
    if gp in cierres_dict: return row[col_fecha] > cierres_dict[gp]
    return False

df_pred['Fuera_de_Plazo'] = df_pred.apply(validar_tiempo, axis=1)

COLUMNA_CORREO = 'Dirección de correo electrónico' if 'Dirección de correo electrónico' in df_pred.columns else 'Correo'
if COLUMNA_CORREO not in df_pred.columns: COLUMNA_CORREO = df_pred.columns[1]

if COLUMNA_CORREO in df_pred.columns:
    df_pred[COLUMNA_CORREO] = df_pred[COLUMNA_CORREO].fillna('').astype(str).str.strip()
    correos_oficiales = df_pred[df_pred[COLUMNA_CORREO] != ''].groupby('Nombre')[COLUMNA_CORREO].first().to_dict()
    def check_impostor(row):
        correo_actual = row[COLUMNA_CORREO]
        correo_oficial = correos_oficiales.get(row['Nombre'])
        if not correo_oficial or not correo_actual: return False
        return correo_actual != correo_oficial
    df_pred['Es_Impostor'] = df_pred.apply(check_impostor, axis=1)
else:
    df_pred['Es_Impostor'] = False

mask_candidatos = ~df_pred['Fuera_de_Plazo'] & ~df_pred['Es_Impostor']
indices_validos = df_pred[mask_candidatos].drop_duplicates(subset=['Nombre', 'Carrera'], keep='last').index

def clasificar_estado(row):
    if row['Es_Impostor']: return "Suplantación de Identidad"
    if row['Fuera_de_Plazo']: return "Fuera de Plazo"
    if row.name in indices_validos: return "Válido"
    else: return "Envío Duplicado (Se tomó una versión posterior)"

df_pred['Estado_VAR'] = df_pred.apply(clasificar_estado, axis=1)
df_rechazados = df_pred[df_pred['Estado_VAR'] != "Válido"].copy()
df_validas = df_pred[df_pred['Estado_VAR'] == "Válido"].copy()

# ==========================================
# 3. MOTOR DE CÁLCULO DE PUNTOS
# ==========================================
columnas_carrera = ['Ganador', 'Segundo (2do)', 'Tercero (3ro)', 'Cuarto (4to)', 'Quinto (5to)', 'Sexto (6to)', 'Septimo (7mo)', 'Octavo (8vo)', 'Noveno (9no)', 'Decimo (10mo)']

def calcular_puntos(row, df_resultados):
    carrera_actual = row['Carrera']
    resultado_oficial = df_resultados[df_resultados['Carrera'] == carrera_actual]
    if resultado_oficial.empty: return 0 
    resultado_oficial = resultado_oficial.iloc[0]
    puntos_jugador = 0
    top10_real = {resultado_oficial.get(col): i for i, col in enumerate(columnas_carrera, start=1) if pd.notna(resultado_oficial.get(col)) and str(resultado_oficial.get(col)).strip() != '-'}
            
    for i, col in enumerate(columnas_carrera, start=1):
        pred = row.get(col)
        if pd.notna(pred) and pred in top10_real:
            dif = abs(i - top10_real[pred])
            if dif == 0: puntos_jugador += 3
            elif dif == 1: puntos_jugador += 2
            else: puntos_jugador += 1
                
    if pd.notna(row.get('Pole Position')) and row.get('Pole Position') == resultado_oficial.get('Pole Position'):
        puntos_jugador += PUNTOS_POLE
    if pd.notna(row.get('Posición Colapinto')) and str(row.get('Posición Colapinto')) == str(resultado_oficial.get('Posición Colapinto')):
        puntos_jugador += PUNTOS_COLAPINTO
    if (pd.notna(row.get('Ganador')) and row.get('Ganador') == resultado_oficial.get('Ganador') and
        pd.notna(row.get('Segundo (2do)')) and row.get('Segundo (2do)') == resultado_oficial.get('Segundo (2do)') and
        pd.notna(row.get('Tercero (3ro)')) and row.get('Tercero (3ro)') == resultado_oficial.get('Tercero (3ro)')) and (str(resultado_oficial.get('Ganador')).strip() != '-'):
        puntos_jugador += PUNTOS_PODIO_PERFECTO

    return puntos_jugador

def evaluar_podio_perfecto(row, df_resultados):
    carrera_actual = row['Carrera']
    resultado_oficial = df_resultados[df_resultados['Carrera'] == carrera_actual]
    if resultado_oficial.empty: return '-' 
    resultado_oficial = resultado_oficial.iloc[0]
    if pd.isna(resultado_oficial.get('Ganador')) or str(resultado_oficial.get('Ganador')).strip() == '-': return '-'
    if (pd.notna(row.get('Ganador')) and row.get('Ganador') == resultado_oficial.get('Ganador') and
        pd.notna(row.get('Segundo (2do)')) and row.get('Segundo (2do)') == resultado_oficial.get('Segundo (2do)') and
        pd.notna(row.get('Tercero (3ro)')) and row.get('Tercero (3ro)') == resultado_oficial.get('Tercero (3ro)')):
        return 'Sí'
    return 'No'

if not df_validas.empty:
    df_validas['Puntos_Obtenidos'] = df_validas.apply(lambda row: calcular_puntos(row, df_res), axis=1)
    df_validas['Podio Perfecto'] = df_validas.apply(lambda row: evaluar_podio_perfecto(row, df_res), axis=1)

# ==========================================
# 4. INTERFAZ GRÁFICA Y GENERACIÓN HTML
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["🏁 RESULTADOS", "📈 GRAFICAS", "🚨 VAR", "📅 CALENDARIO"])

carreras_iniciales = ['Australia', 'China | Sprint', 'China', 'Japón', 'Bahréin', 'Arabia Saudita', 'Miami | Sprint', 'Miami', 'Canada | Sprint', 'Canada', 'Monaco', 'Barcelona', 'Austria', 'Reino Unido | Sprint', 'Reino Unido', 'Bélgica', 'Hungría', 'Paises Bajos | Sprint', 'Paises Bajos', 'Italia', 'Madrid', 'Azerbaijan', 'Singapur | Sprint', 'Singapur', 'Austin', 'México', 'Brasil', 'Qatar', 'Abu Dhabi']
carreras_disponibles = [c for c in carreras_iniciales if c in df_validas['Carrera'].unique()]

def getBgColor(nombre):
    for k, v in colores_celdas.items():
        if k in str(nombre) or str(nombre) in k: return v
    return ''

renames = {
    'Segundo (2do)': 'P 2', 'Tercero (3ro)': 'P 3', 'Cuarto (4to)': 'P 4', 'Quinto (5to)': 'P 5',
    'Sexto (6to)': 'P 6', 'Septimo (7mo)': 'P 7', 'Octavo (8vo)': 'P 8', 'Noveno (9no)': 'P 9',
    'Decimo (10mo)': 'P 10', 'Posición Colapinto': 'Colapinto',
    'Podio Perfecto': 'Podio<br>Perf.', 'Puntos_Obtenidos': 'Total<br>PTS'
}
columnas_carrera_html = [renames.get(c, c) for c in columnas_carrera]

# --- HOJA 1: RESULTADOS ---
with tab1:
    st.header("🏁 PUNTOS POR FECHA")
    if carreras_disponibles:
        carrera_seleccionada = st.selectbox("Seleccionar Gran Premio:", carreras_disponibles)
        df_mostrar = df_validas[df_validas['Carrera'] == carrera_seleccionada].copy()
        cols_mostrar_orig = ['Nombre', 'Pole Position'] + columnas_carrera + ['Posición Colapinto', 'Podio Perfecto', 'Puntos_Obtenidos']
        df_mostrar = df_mostrar[cols_mostrar_orig].sort_values('Puntos_Obtenidos', ascending=False)
        
        oficial_row = df_res[df_res['Carrera'] == carrera_seleccionada]
        top10_real = {}
        oficial_data = pd.Series(dtype=object)
        
        fila_oficial = {col: '-' for col in cols_mostrar_orig}
        if not oficial_row.empty:
            oficial_data = oficial_row.iloc[0]
            fila_oficial['Nombre'] = '⭐ RESULTADO OFICIAL'
            for col in cols_mostrar_orig:
                if col in oficial_data.index:
                    fila_oficial[col] = oficial_data[col]
            for i, col in enumerate(columnas_carrera, start=1):
                piloto = oficial_data.get(col)
                if pd.notna(piloto) and str(piloto).strip() != '-' and str(piloto).strip() != '':
                    top10_real[piloto] = i
        else:
            fila_oficial['Nombre'] = '⏳ ESPERANDO RESULTADOS'
            
        fila_oficial['Puntos_Obtenidos'] = '-'
        fila_oficial['Podio Perfecto'] = '-'
        
        df_mostrar = pd.concat([pd.DataFrame([fila_oficial]), df_mostrar], ignore_index=True)
        df_mostrar = df_mostrar.rename(columns=renames)
        
        def aplicar_colores(row):
            styles = [''] * len(row)
            if 'OFICIAL' in row['Nombre'] or 'ESPERANDO' in row['Nombre']:
                return ['background-color: #1a1a1a; font-weight: bold; color: #ffffff; border-bottom: 2px solid #00f2ff;'] * len(row)
            for i, col in enumerate(row.index):
                val = row[col]
                if col == 'Nombre':
                    bg = getBgColor(val)
                    if bg: styles[i] = f'background-color: {bg}; font-weight: bold; color: #ffffff;'
                    continue
                if pd.isna(val) or val == '-': continue
                if not oficial_row.empty:
                    if col in columnas_carrera_html:
                        orig_col = [k for k, v in renames.items() if v == col]
                        orig_col = orig_col[0] if orig_col else col
                        col_idx = columnas_carrera.index(orig_col) + 1
                        pos_real = top10_real.get(val)
                        if pos_real is not None:
                            dif = abs(col_idx - pos_real)
                            if dif == 0: styles[i] = 'background-color: rgba(0, 255, 136, 0.15); color: #00ff88; border: 1px solid rgba(0, 255, 136, 0.3);' 
                            elif dif == 1: styles[i] = 'background-color: rgba(255, 204, 0, 0.15); color: #ffcc00; border: 1px solid rgba(255, 204, 0, 0.3);' 
                        else:
                            styles[i] = 'background-color: rgba(255, 51, 51, 0.15); color: #ff3333; border: 1px solid rgba(255, 51, 51, 0.3);' 
                    elif col in ['Pole Position', 'Colapinto']:
                        orig_col = 'Posición Colapinto' if 'Colapinto' in col else 'Pole Position'
                        if str(val) == str(oficial_data.get(orig_col)): styles[i] = 'background-color: rgba(0, 255, 136, 0.15); color: #00ff88; border: 1px solid rgba(0, 255, 136, 0.3);'
                        else: styles[i] = 'background-color: rgba(255, 51, 51, 0.15); color: #ff3333; border: 1px solid rgba(255, 51, 51, 0.3);'
                    elif col == 'Podio<br>Perf.':
                        if val == 'Sí': styles[i] = 'background-color: rgba(0, 255, 136, 0.15); font-weight: bold; color: #00ff88;'
                        elif val == 'No': styles[i] = 'color: #ff3333;'
                if col == 'Total<br>PTS':
                    styles[i] = 'background-color: #1a1a1a; font-weight: bold; color: #00f2ff; font-size: 16px; border-left: 1px solid #262626;'
            return styles

        df_estilizado = df_mostrar.style.apply(aplicar_colores, axis=1).hide(axis="index")
        html_tabla_1 = df_estilizado.to_html(escape=False, table_attributes='class="styled-table"')
        st.markdown(html_tabla_1, unsafe_allow_html=True)
        
        st.divider()
        st.header("🏆 DRIVERS STANDING (ACUMULADO)")
        df_puntos_carrera = df_validas.pivot_table(index='Nombre', columns='Carrera', values='Puntos_Obtenidos', aggfunc='sum', fill_value=0)
        df_puntos_carrera = df_puntos_carrera[[c for c in carreras_iniciales if c in df_puntos_carrera.columns]]
        df_puntos_carrera['TOTAL ACUMULADO'] = df_puntos_carrera.sum(axis=1)
        df_puntos_carrera = df_puntos_carrera.sort_values('TOTAL ACUMULADO', ascending=False).reset_index()
        
        def aplicar_colores_acumulado(row):
            styles = [''] * len(row)
            for i, col in enumerate(row.index):
                if col == 'Nombre':
                    bg = getBgColor(row['Nombre'])
                    if bg: styles[i] = f'background-color: {bg}; font-weight: bold; color: #ffffff;'
                elif col == 'TOTAL ACUMULADO':
                    styles[i] = 'background-color: #1a1a1a; font-weight: bold; color: #00f2ff; font-size: 16px;'
            return styles
            
        df_acum_estilizado = df_puntos_carrera.style.apply(aplicar_colores_acumulado, axis=1).hide(axis="index")
        html_tabla_2 = df_acum_estilizado.to_html(escape=False, table_attributes='class="styled-table"')
        st.markdown(html_tabla_2, unsafe_allow_html=True)
        
    else:
        st.info("Aún no hay predicciones válidas cargadas.")

# --- HOJA 2: GRÁFICAS ---
with tab2:
    st.header("📈 Graficas")
    if not df_validas.empty and len(carreras_disponibles) > 0:
        df_puntos_carrera = df_validas.pivot_table(index='Nombre', columns='Carrera', values='Puntos_Obtenidos', aggfunc='sum', fill_value=0)
        df_puntos_carrera = df_puntos_carrera[[c for c in carreras_iniciales if c in df_puntos_carrera.columns]]
        df_acumulados = df_puntos_carrera.cumsum(axis=1)
        
        def getColorLine(nombre):
            for k, v in colores_graficas.items():
                if k in nombre or nombre in k: return v
            return '#e0e0e0'

        layout_dark = dict(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8c8c8c', family='JetBrains Mono'),
            xaxis=dict(showgrid=True, gridcolor='#262626'),
            yaxis=dict(showgrid=True, gridcolor='#262626')
        )

        st.subheader("1. Puntos por Fecha (Individual)")
        fig1 = go.Figure()
        for jugador in df_puntos_carrera.index:
            fig1.add_trace(go.Scatter(x=df_puntos_carrera.columns, y=df_puntos_carrera.loc[jugador], mode='lines+markers', name=jugador, line=dict(color=getColorLine(jugador), width=3)))
        fig1.update_layout(**layout_dark)
        st.plotly_chart(fig1, use_container_width=True, key="grafico_1")

        st.divider()
        st.subheader("2. Campeonato Filtrado")
        col1, col2 = st.columns(2)
        with col1: carrera_inicio = st.selectbox("Desde:", carreras_disponibles, index=0)
        with col2: carrera_fin = st.selectbox("Hasta:", carreras_disponibles, index=len(carreras_disponibles)-1)

        idx_inicio = carreras_disponibles.index(carrera_inicio)
        idx_fin = carreras_disponibles.index(carrera_fin)
        if idx_inicio > idx_fin: idx_inicio, idx_fin = idx_fin, idx_inicio
        carreras_filtradas = carreras_disponibles[idx_inicio:idx_fin+1]

        fig2 = go.Figure()
        for jugador in df_acumulados.index:
            y_data = df_acumulados.loc[jugador, carreras_filtradas]
            fig2.add_trace(go.Scatter(x=carreras_filtradas, y=y_data, mode='lines+markers', name=jugador, line=dict(color=getColorLine(jugador), width=3)))
        fig2.update_layout(**layout_dark)
        st.plotly_chart(fig2, use_container_width=True, key="grafico_2")

        st.divider()
        st.subheader("3. Total Histórico")
        fig3 = go.Figure()
        for jugador in df_acumulados.index:
            fig3.add_trace(go.Scatter(x=df_acumulados.columns, y=df_acumulados.loc[jugador], mode='lines+markers', name=jugador, line=dict(color=getColorLine(jugador), width=3)))
        fig3.update_layout(**layout_dark)
        st.plotly_chart(fig3, use_container_width=True, key="grafico_3")
    else:
        st.info("Faltan datos para generar las gráficas.")

# --- HOJA 3: VAR ---
with tab3:
    st.header("🚨 VAR CONTROL ROOM")
    if not df_rechazados.empty:
        st.error("Las siguientes predicciones fueron anuladas:")
        cols_var = [col_fecha, 'Nombre', COLUMNA_CORREO, 'Carrera', 'Estado_VAR']
        st.dataframe(df_rechazados[cols_var].sort_values(col_fecha, ascending=False), use_container_width=True, hide_index=True)
    else:
        st.success("✅ No hay predicciones rechazadas. Todos en regla.")

# --- HOJA 4: CALENDARIO EN VIVO (CORREGIDO PARA 2026) ---
with tab4:
    st.header("📅 CALENDARIO OFICIAL F1")
    
    @st.cache_data(ttl=3600)
    def obtener_calendario_f1():
        url = "https://ics.ecal.com/ecal-sub/6a12e5911ae22c0002d2636a/Formula%201.ics"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as respuesta:
            datos = respuesta.read().decode('utf-8')
            
        eventos = []
        for bloque in datos.split('BEGIN:VEVENT')[1:]:
            # Extraer SUMMARY y DTSTART usando expresiones regulares
            summary_match = re.search(r'SUMMARY:(.*)', bloque)
            dtstart_match = re.search(r'DTSTART:(\d{8}T\d{6}Z)', bloque)
            
            if summary_match and dtstart_match:
                fecha_str = dtstart_match.group(1)
                try:
                    dt = datetime.datetime.strptime(fecha_str, "%Y%m%dT%H%M%SZ")
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                    eventos.append({'SUMMARY': summary_match.group(1).strip(), 'DTSTART': dt})
                except:
                    continue
        return sorted(eventos, key=lambda x: x['DTSTART'])

    calendario_oficial = obtener_calendario_f1()
    ahora_utc = datetime.datetime.now(datetime.timezone.utc)
    tz_arg = datetime.timezone(datetime.timedelta(hours=-3))
    
    proximos_eventos = [e for e in calendario_oficial if e['DTSTART'] > ahora_utc]
    
    if proximos_eventos:
        siguiente = proximos_eventos[0]
        faltan = siguiente["DTSTART"] - ahora_utc
        dias = faltan.days
        horas = faltan.seconds // 3600
        minutos = (faltan.seconds % 3600) // 60
        
        st.markdown(f'''
        <div style="background-color: #141414; padding: 25px; border-radius: 4px; border: 1px solid #262626; border-left: 4px solid #00f2ff; text-align: center; margin-bottom: 30px;">
            <p style="color: #00f2ff; margin:0; font-family: 'JetBrains Mono', monospace; font-size: 14px; letter-spacing: 2px; text-transform: uppercase;">PRÓXIMA SESIÓN • {siguiente['SUMMARY']}</p>
            <h1 style="color: #ffffff; margin:10px 0 0 0; font-size: 56px; font-family: 'Barlow Condensed', sans-serif; font-style: italic; line-height: 1;">
                {dias}D {horas}H {minutos}M
            </h1>
        </div>
        ''', unsafe_allow_html=True)
        
        st.markdown('''
        <a href="webcal://ics.ecal.com/ecal-sub/6a12e5911ae22c0002d2636a/Formula%201.ics" target="_blank" style="display: block; width: 100%; background-color: #ff1e1e; color: white; text-align: center; padding: 12px; border-radius: 4px; font-family: 'JetBrains Mono', monospace; font-weight: bold; font-size: 16px; text-decoration: none; text-transform: uppercase; margin-bottom: 40px; border-bottom: 3px solid #cc0000; transition: 0.3s;">
            🔗 SINCRONIZAR CALENDARIO (iOS / ANDROID)
        </a>
        ''', unsafe_allow_html=True)
        
        st.subheader("🏁 Cronograma Completo (Hora Argentina)")
        
        for c in proximos_eventos[:15]:
            fecha_arg = c["DTSTART"].astimezone(tz_arg)
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"<span style='font-family: JetBrains Mono; color: {'#00f2ff' if 'Race' in c['SUMMARY'] else '#e0e0e0'}; font-size: 15px;'>{c['SUMMARY']}</span>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<span style='font-family: JetBrains Mono; color: #8c8c8c; text-align: right; display: block;'>{fecha_arg.strftime('%d/%m %H:%M')}</span>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 8px 0; border-color: #262626;'>", unsafe_allow_html=True)
    else:
        st.info("No se detectaron sesiones futuras en el calendario oficial.")