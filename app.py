import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 0. CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="Prode F1", page_icon="🏆", layout="wide")
st.title("🏆 Prode F1 Mundial")

PUNTOS_POLE = 2
PUNTOS_COLAPINTO = 2
PUNTOS_PODIO_PERFECTO = 3

colores_graficas = {
    "Juan": "#E80020", "Lencioni": "#3671C6", "Santoni": "#27F4D2",
    "Facu": "#FF8700", "Cristian": "#229971", "Jota": "#0093CC",
    "Matias": "#B6BABD", "Ochoa": "#52E252"
}

# ==========================================
# 1. CARGA DE DATOS DESDE GOOGLE SHEETS
# ==========================================
# Usamos cache para que la web cargue rápido, pero se actualice cada 60 segundos
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
# 2. LIMPIEZA Y VALIDACIÓN (MOTOR INTACTO)
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
# NOTA: En Google Forms la columna suele llamarse 'Marca temporal'
col_fecha = 'Marca temporal' if 'Marca temporal' in df_pred.columns else df_pred.columns[0]
df_pred[col_fecha] = pd.to_datetime(df_pred[col_fecha], dayfirst=True, errors='coerce')

cierres_dict = df_res.dropna(subset=['Fecha Cierre']).set_index('Carrera')['Fecha Cierre'].to_dict()
df_pred = df_pred.sort_values(col_fecha)

def validar_tiempo(row):
    gp = row['Carrera']
    if gp in cierres_dict:
        return row[col_fecha] > cierres_dict[gp]
    return False

df_pred['Fuera_de_Plazo'] = df_pred.apply(validar_tiempo, axis=1)

COLUMNA_CORREO = 'Dirección de correo electrónico' if 'Dirección de correo electrónico' in df_pred.columns else 'Correo'
if COLUMNA_CORREO not in df_pred.columns:
    COLUMNA_CORREO = df_pred.columns[1] # Respaldo por si cambia el nombre

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
    top10_real = {resultado_oficial.get(col): i for i, col in enumerate(columnas_carrera, start=1) if pd.notna(resultado_oficial.get(col)) and resultado_oficial.get(col) != '-'}
            
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
        pd.notna(row.get('Tercero (3ro)')) and row.get('Tercero (3ro)') == resultado_oficial.get('Tercero (3ro)')) and (resultado_oficial.get('Ganador') != '-'):
        puntos_jugador += PUNTOS_PODIO_PERFECTO

    return puntos_jugador

def evaluar_podio_perfecto(row, df_resultados):
    carrera_actual = row['Carrera']
    resultado_oficial = df_resultados[df_resultados['Carrera'] == carrera_actual]
    if resultado_oficial.empty: return '-' 
    resultado_oficial = resultado_oficial.iloc[0]
    if pd.isna(resultado_oficial.get('Ganador')) or resultado_oficial.get('Ganador') == '-': return '-'
    if (pd.notna(row.get('Ganador')) and row.get('Ganador') == resultado_oficial.get('Ganador') and
        pd.notna(row.get('Segundo (2do)')) and row.get('Segundo (2do)') == resultado_oficial.get('Segundo (2do)') and
        pd.notna(row.get('Tercero (3ro)')) and row.get('Tercero (3ro)') == resultado_oficial.get('Tercero (3ro)')):
        return 'Sí'
    return 'No'

if not df_validas.empty:
    df_validas['Puntos Obtenidos'] = df_validas.apply(lambda row: calcular_puntos(row, df_res), axis=1)
    df_validas['Podio Perfecto'] = df_validas.apply(lambda row: evaluar_podio_perfecto(row, df_res), axis=1)

# ==========================================
# 4. INTERFAZ GRÁFICA (STREAMLIT)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 Resultados y Puntos", "📈 Gráficas y Evolución", "🚨 Auditoría / VAR"])

carreras_iniciales = ['Australia', 'China | Sprint', 'China', 'Japón', 'Bahréin', 'Arabia Saudita', 'Miami | Sprint', 'Miami', 'Canada | Sprint', 'Canada', 'Monaco', 'Barcelona', 'Austria', 'Reino Unido | Sprint', 'Reino Unido', 'Bélgica', 'Hungría', 'Paises Bajos | Sprint', 'Paises Bajos', 'Italia', 'Madrid', 'Azerbaijan', 'Singapur | Sprint', 'Singapur', 'Austin', 'México', 'Brasil', 'Qatar', 'Abu Dhabi']
carreras_disponibles = [c for c in carreras_iniciales if c in df_validas['Carrera'].unique()]

# --- HOJA 1: RESULTADOS ---
with tab1:
    st.header("🏁 Puntos por Fecha")
    if carreras_disponibles:
        carrera_seleccionada = st.selectbox("Seleccionar Gran Premio:", carreras_disponibles)
        
        # Filtrar datos de la carrera
        df_mostrar = df_validas[df_validas['Carrera'] == carrera_seleccionada].copy()
        cols_mostrar = ['Nombre', 'Pole Position'] + columnas_carrera + ['Posición Colapinto', 'Podio Perfecto', 'Puntos Obtenidos']
        df_mostrar = df_mostrar[cols_mostrar].sort_values('Puntos Obtenidos', ascending=False)
        
        # Resultado oficial
        oficial_row = df_res[df_res['Carrera'] == carrera_seleccionada]
        if not oficial_row.empty:
            st.success("⭐ Resultados Oficiales Cargados")
        else:
            st.warning("⏳ Esperando Resultados Oficiales...")
            
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        st.divider()
        st.header("🏆 Campeonato General Acumulado")
        df_puntos_carrera = df_validas.pivot_table(index='Nombre', columns='Carrera', values='Puntos Obtenidos', aggfunc='sum', fill_value=0)
        df_puntos_carrera = df_puntos_carrera[[c for c in carreras_iniciales if c in df_puntos_carrera.columns]]
        df_puntos_carrera['TOTAL ACUMULADO'] = df_puntos_carrera.sum(axis=1)
        df_puntos_carrera = df_puntos_carrera.sort_values('TOTAL ACUMULADO', ascending=False)
        st.dataframe(df_puntos_carrera, use_container_width=True)
    else:
        st.info("Aún no hay predicciones válidas cargadas.")

# --- HOJA 2: GRÁFICAS ---
with tab2:
    st.header("📈 Análisis del Campeonato")
    if not df_validas.empty and len(carreras_disponibles) > 0:
        df_puntos_carrera = df_validas.pivot_table(index='Nombre', columns='Carrera', values='Puntos Obtenidos', aggfunc='sum', fill_value=0)
        df_puntos_carrera = df_puntos_carrera[[c for c in carreras_iniciales if c in df_puntos_carrera.columns]]
        df_acumulados = df_puntos_carrera.cumsum(axis=1)
        
        def getColor(nombre):
            for k, v in colores_graficas.items():
                if k in nombre or nombre in k: return v
            return '#000000'

        # Gráfico 1: Puntos por Fecha
        fig1 = go.Figure()
        for jugador in df_puntos_carrera.index:
            fig1.add_trace(go.Scatter(x=df_puntos_carrera.columns, y=df_puntos_carrera.loc[jugador], mode='lines+markers', name=jugador, line=dict(color=getColor(jugador), width=3)))
        fig1.update_layout(title="Puntos Obtenidos por Fecha (Individual)", xaxis_title="Gran Premio", yaxis_title="Puntos")
        st.plotly_chart(fig1, use_container_width=True)

        # Gráfico 2: Acumulado Total
        fig2 = go.Figure()
        for jugador in df_acumulados.index:
            fig2.add_trace(go.Scatter(x=df_acumulados.columns, y=df_acumulados.loc[jugador], mode='lines+markers', name=jugador, line=dict(color=getColor(jugador), width=3)))
        fig2.update_layout(title="Evolución del Campeonato (Acumulado Histórico)", xaxis_title="Gran Premio", yaxis_title="Puntos Totales")
        st.plotly_chart(fig2, use_container_width=True)
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