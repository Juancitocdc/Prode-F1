import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 0. CONFIGURACIÓN DE LA PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(page_title="Prode F1", page_icon="🏆", layout="wide")

# CSS personalizado para recrear la tabla HTML compacta original
st.markdown("""
    <style>
    .styled-table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; text-align: center; font-family: 'Segoe UI', Arial, sans-serif; background-color: white;}
    .styled-table th { background-color: #222; color: white; padding: 10px 4px; font-weight: 600; text-align: center; vertical-align: middle; line-height: 1.2;}
    .styled-table td { padding: 8px 4px; border-bottom: 1px solid #eee; vertical-align: middle; color: #111;}
    .styled-table tr:hover { background-color: #f9f9f9; }
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

# Colores con opacidad al 30% (Agregando 4D al HEX) para fondos de celdas legibles
colores_celdas = {
    "Juan": "#E800204D", "Lencioni": "#3671C64D", "Santoni": "#27F4D24D",
    "Facu": "#FF87004D", "Cristian": "#2299714D", "Jota": "#0093CC4D",
    "Matias": "#B6BABD4D", "Ochoa": "#52E2524D"
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
tab1, tab2, tab3 = st.tabs(["📊 Resultados y Puntos", "📈 Gráficas y Evolución", "🚨 Auditoría / VAR"])

carreras_iniciales = ['Australia', 'China | Sprint', 'China', 'Japón', 'Bahréin', 'Arabia Saudita', 'Miami | Sprint', 'Miami', 'Canada | Sprint', 'Canada', 'Monaco', 'Barcelona', 'Austria', 'Reino Unido | Sprint', 'Reino Unido', 'Bélgica', 'Hungría', 'Paises Bajos | Sprint', 'Paises Bajos', 'Italia', 'Madrid', 'Azerbaijan', 'Singapur | Sprint', 'Singapur', 'Austin', 'México', 'Brasil', 'Qatar', 'Abu Dhabi']
carreras_disponibles = [c for c in carreras_iniciales if c in df_validas['Carrera'].unique()]

# Función para obtener color de celda (Opaco)
def getBgColor(nombre):
    for k, v in colores_celdas.items():
        if k in str(nombre) or str(nombre) in k: return v
    return ''

# Renombrar columnas para forzar el salto de línea (HTML <br>)
renames = {
    'Segundo (2do)': 'Segundo<br>(2do)', 'Tercero (3ro)': 'Tercero<br>(3ro)',
    'Cuarto (4to)': 'Cuarto<br>(4to)', 'Quinto (5to)': 'Quinto<br>(5to)',
    'Sexto (6to)': 'Sexto<br>(6to)', 'Septimo (7mo)': 'Septimo<br>(7mo)',
    'Octavo (8vo)': 'Octavo<br>(8vo)', 'Noveno (9no)': 'Noveno<br>(9no)',
    'Decimo (10mo)': 'Decimo<br>(10mo)', 'Posición Colapinto': 'Posición<br>Colapinto',
    'Podio Perfecto': 'Podio<br>Perfecto', 'Puntos_Obtenidos': 'Puntos<br>Totales'
}

columnas_carrera_html = [renames.get(c, c) for c in columnas_carrera]

# --- HOJA 1: RESULTADOS ---
with tab1:
    st.header("🏁 Puntos por Fecha")
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
        
        # Motor de colores
        def aplicar_colores(row):
            styles = [''] * len(row)
            if 'OFICIAL' in row['Nombre'] or 'ESPERANDO' in row['Nombre']:
                return ['background-color: #e3f2fd; font-weight: bold; color: #111;'] * len(row)
                
            for i, col in enumerate(row.index):
                val = row[col]
                
                # Pintar el Nombre con la Escudería
                if col == 'Nombre':
                    bg = getBgColor(val)
                    if bg: styles[i] = f'background-color: {bg}; font-weight: bold; color: #111;'
                    continue
                
                if pd.isna(val) or val == '-': continue
                    
                if not oficial_row.empty:
                    if col in columnas_carrera_html:
                        # Buscar indice original
                        orig_col = [k for k, v in renames.items() if v == col]
                        orig_col = orig_col[0] if orig_col else col
                        col_idx = columnas_carrera.index(orig_col) + 1
                        
                        pos_real = top10_real.get(val)
                        if pos_real is not None:
                            dif = abs(col_idx - pos_real)
                            if dif == 0: styles[i] = 'background-color: #c8e6c9; color: #111;' 
                            elif dif == 1: styles[i] = 'background-color: #fff9c4; color: #111;' 
                        else:
                            styles[i] = 'background-color: #ffcdd2; color: #111;' 
                    elif col in ['Pole Position', 'Posición<br>Colapinto']:
                        orig_col = 'Posición Colapinto' if 'Colapinto' in col else 'Pole Position'
                        if str(val) == str(oficial_data.get(orig_col)): styles[i] = 'background-color: #c8e6c9; color: #111;'
                        else: styles[i] = 'background-color: #ffcdd2; color: #111;'
                    elif col == 'Podio<br>Perfecto':
                        if val == 'Sí': styles[i] = 'background-color: #c8e6c9; font-weight: bold; color: #2e7d32;'
                        elif val == 'No': styles[i] = 'color: #b71c1c;'
                        
                if col == 'Puntos<br>Totales':
                    styles[i] = 'background-color: #f0f0f0; font-weight: bold; color: #111; font-size: 16px;'
                    
            return styles

        df_estilizado = df_mostrar.style.apply(aplicar_colores, axis=1).hide(axis="index")
        html_tabla_1 = df_estilizado.to_html(escape=False, table_attributes='class="styled-table"')
        st.markdown(html_tabla_1, unsafe_allow_html=True)
        
        st.divider()
        st.header("🏆 Campeonato General Acumulado")
        df_puntos_carrera = df_validas.pivot_table(index='Nombre', columns='Carrera', values='Puntos_Obtenidos', aggfunc='sum', fill_value=0)
        df_puntos_carrera = df_puntos_carrera[[c for c in carreras_iniciales if c in df_puntos_carrera.columns]]
        df_puntos_carrera['TOTAL ACUMULADO'] = df_puntos_carrera.sum(axis=1)
        df_puntos_carrera = df_puntos_carrera.sort_values('TOTAL ACUMULADO', ascending=False).reset_index()
        
        def aplicar_colores_acumulado(row):
            styles = [''] * len(row)
            for i, col in enumerate(row.index):
                if col == 'Nombre':
                    bg = getBgColor(row['Nombre'])
                    if bg: styles[i] = f'background-color: {bg}; font-weight: bold; color: #111;'
                elif col == 'TOTAL ACUMULADO':
                    styles[i] = 'background-color: #222; font-weight: bold; color: white; font-size: 16px;'
            return styles
            
        df_acum_estilizado = df_puntos_carrera.style.apply(aplicar_colores_acumulado, axis=1).hide(axis="index")
        html_tabla_2 = df_acum_estilizado.to_html(escape=False, table_attributes='class="styled-table"')
        st.markdown(html_tabla_2, unsafe_allow_html=True)
        
    else:
        st.info("Aún no hay predicciones válidas cargadas.")

# --- HOJA 2: GRÁFICAS ---
with tab2:
    st.header("📈 Análisis del Campeonato")
    if not df_validas.empty and len(carreras_disponibles) > 0:
        df_puntos_carrera = df_validas.pivot_table(index='Nombre', columns='Carrera', values='Puntos_Obtenidos', aggfunc='sum', fill_value=0)
        df_puntos_carrera = df_puntos_carrera[[c for c in carreras_iniciales if c in df_puntos_carrera.columns]]
        df_acumulados = df_puntos_carrera.cumsum(axis=1)
        
        def getColorLine(nombre):
            for k, v in colores_graficas.items():
                if k in nombre or nombre in k: return v
            return '#000000'

        st.subheader("1. Puntos Obtenidos por Fecha (Individual)")
        fig1 = go.Figure()
        for jugador in df_puntos_carrera.index:
            fig1.add_trace(go.Scatter(x=df_puntos_carrera.columns, y=df_puntos_carrera.loc[jugador], mode='lines+markers', name=jugador, line=dict(color=getColorLine(jugador), width=3)))
        fig1.update_layout(xaxis_title="Gran Premio", yaxis_title="Puntos")
        st.plotly_chart(fig1, use_container_width=True)

        st.divider()

        st.subheader("2. Evolución del Campeonato (Filtrada)")
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
        fig2.update_layout(xaxis_title="Gran Premio", yaxis_title="Puntos Acumulados")
        st.plotly_chart(fig2, use_container_width=True)

        st.divider()

        st.subheader("3. Evolución del Campeonato (Total Histórico)")
        fig3 = go.Figure()
        for jugador in df_acumulados.index:
            fig3.add_trace(go.Scatter(x=df_acumulados.columns, y=df_acumulados.loc[jugador], mode='lines+markers', name=jugador, line=dict(color=getColorLine(jugador), width=3)))
        fig3.update_layout(xaxis_title="Gran Premio", yaxis_title="Puntos Totales")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Faltan datos para generar las gráficas.")

# --- HOJA 3: VAR ---
with tab3:
    st.header("🚨 El VAR del Prode")
    if not df_rechazados.empty:
        st.error("Las siguientes predicciones fueron anuladas:")
        cols_var = [col_fecha, 'Nombre', COLUMNA_CORREO, 'Carrera', 'Estado_VAR']
        st.dataframe(df_rechazados[cols_var].sort_values(col_fecha, ascending=False), use_container_width=True, hide_index=True)
    else:
        st.success("✅ No hay predicciones rechazadas. ¡Todos jugaron limpio por ahora!")