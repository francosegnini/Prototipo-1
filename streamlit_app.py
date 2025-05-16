# streamlit_app.py
import streamlit as st
import pandas as pd
import pytesseract
import speech_recognition as sr
from PIL import Image
from datetime import datetime
import os
import sqlite3

DB_FILE = "procedimientos.db"
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS procedimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        nombre_paciente TEXT,
        documento TEXT,
        fecha_nacimiento TEXT,
        anio_residencia TEXT,
        hospital TEXT,
        rol_residente TEXT,
        instructor TEXT,
        procedimiento_codigo TEXT,
        procedimiento_nombre TEXT,
        metodo_registro TEXT
    )
''')
conn.commit()

codigo_excel = "codigos_procedimientos.xlsx"

@st.cache_data
def cargar_tabla_codigos():
    df = pd.read_excel(codigo_excel)
    if "Codigo" not in df.columns or "Nombre" not in df.columns or "Habilitado" not in df.columns:
        st.error("El archivo de procedimientos debe contener las columnas 'Codigo', 'Nombre' y 'Habilitado'.")
        st.stop()
    return df[df["Habilitado"] == "SI"]

codigos_df = cargar_tabla_codigos()

st.title("🧠 Registro Inteligente de Procedimientos Médicos")

modo = st.radio("Selecciona el modo de registro", ["📷 Imagen", "🎙️ Audio"])
registro = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "metodo_registro": modo
}

if modo == "📷 Imagen":
    imagen = st.file_uploader("Sube o toma una foto del documento del paciente", type=["jpg", "jpeg", "png"])
    if imagen:
        img = Image.open(imagen)
        st.image(img, caption="Imagen cargada", use_column_width=True)

        texto_extraido = pytesseract.image_to_string(img, lang='spa')
        texto_area = st.text_area("Texto detectado (editable)", value=texto_extraido, height=200)

        registro["nombre_paciente"] = next((line.split(":")[-1].strip() for line in texto_area.splitlines() if "nombre" in line.lower()), "")
        registro["documento"] = next((line.split(":")[-1].strip() for line in texto_area.splitlines() if "documento" in line.lower()), "")
        registro["fecha_nacimiento"] = next((line.split(":")[-1].strip() for line in texto_area.splitlines() if "nacimiento" in line.lower() or "edad" in line.lower()), "")

elif modo == "🎙️ Audio":
    st.info("Usa una grabación de voz clara donde menciones los campos uno a uno")
    audio_file = st.file_uploader("Sube una grabación de audio", type=["wav", "mp3"])

    if audio_file:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            try:
                texto = recognizer.recognize_google(audio_data, language="es-ES")
                texto_area = st.text_area("Texto reconocido (editable)", value=texto, height=150)

                registro["nombre_paciente"] = next((seg.strip() for seg in texto_area.split(" ") if "paciente" in seg.lower()), "")
                registro["documento"] = next((seg.strip() for seg in texto_area.split(" ") if seg.isdigit()), "")
                registro["fecha_nacimiento"] = ""

            except sr.UnknownValueError:
                st.error("No se pudo entender el audio")

st.subheader("📝 Datos del procedimiento")
registro["anio_residencia"] = st.selectbox("Año de residencia", ["1", "2", "3", "4", "5"])
registro["hospital"] = st.text_input("Hospital")
registro["rol_residente"] = st.selectbox("Rol", ["Cirujano Principal", "Ayudante 1", "Ayudante 2"])
registro["instructor"] = st.text_input("Instructor responsable")

codigo_sel = st.selectbox("Procedimiento realizado", codigos_df["Nombre"].sort_values())
registro["procedimiento_nombre"] = codigo_sel
registro["procedimiento_codigo"] = codigos_df[codigos_df["Nombre"] == codigo_sel]["Codigo"].values[0]

if st.button("Registrar procedimiento"):
    valores = [
        registro["timestamp"], registro.get("nombre_paciente", ""), registro.get("documento", ""),
        registro.get("fecha_nacimiento", ""), registro["anio_residencia"], registro["hospital"],
        registro["rol_residente"], registro["instructor"],
        registro["procedimiento_codigo"], registro["procedimiento_nombre"], registro["metodo_registro"]
    ]
    c.execute('''INSERT INTO procedimientos (
        timestamp, nombre_paciente, documento, fecha_nacimiento, anio_residencia,
        hospital, rol_residente, instructor, procedimiento_codigo, procedimiento_nombre,
        metodo_registro
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', valores)
    conn.commit()
    st.success("✅ Procedimiento registrado exitosamente")

    df = pd.read_sql_query("SELECT * FROM procedimientos ORDER BY id DESC LIMIT 1", conn)
    st.dataframe(df)

    df_total = pd.read_sql_query("SELECT * FROM procedimientos ORDER BY id DESC", conn)
    excel_output = "procedimientos_exportados.xlsx"
    df_total.to_excel(excel_output, index=False)
    st.info(f"📁 Archivo actualizado: {excel_output}")
    with open(excel_output, "rb") as f:
        st.download_button("📤 Descargar Excel actualizado", f, file_name=excel_output, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
