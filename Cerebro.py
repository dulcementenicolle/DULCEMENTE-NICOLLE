import json
import os
import io
import base64
import calendar
import datetime
import streamlit as st
from PIL import Image
from google import genai
from google.genai import types

# Librerías para Google Calendar
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Librerías para generar el PDF elegante
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import gspread
from google.oauth2.service_account import Credentials

# --- CONEXIÓN A GOOGLE SHEETS ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@st.cache_resource
def conectar_sheets():
  credenciales = Credentials.from_service_account_info(
      st.secrets["gcp_service_account"], scopes=SCOPES
  )
  cliente = gspread.authorize(credenciales)
  return cliente.open_by_url(
      "https://docs.google.com/spreadsheets/d/1Hw8ZAjvRUvGvRbZodN-kZeECD329KIM_jAcTR-8SpHo/edit"
  )

def cargar_desde_nube(nombre_pestana):
  try:
    hoja = conectar_sheets().worksheet(nombre_pestana)
    registros = hoja.get_all_records()
    for fila in registros:
      for k, v in fila.items():
        if isinstance(v, str) and (v.startswith("[") or v.startswith("{")):
          try:
            fila[k] = json.loads(v)
          except Exception:
            pass
    return registros
  except Exception as e:
    st.error(f"Error al leer {nombre_pestana}: {e}")
    return []

def guardar_en_nube(nombre_pestana, lista_datos):
  try:
    hoja = conectar_sheets().worksheet(nombre_pestana)
    hoja.clear()
    if lista_datos:
      encabezados = list(lista_datos[0].keys())
      filas = [encabezados] + [
          [
              json.dumps(v, ensure_ascii=False)
              if isinstance(v, (dict, list))
              else v
              for v in item.values()
          ]
          for item in lista_datos
      ]
      hoja.update(filas)
  except Exception as e:
    st.error(f"Error al guardar en {nombre_pestana}: {e}")
# Configuración de la página web para celular/PC
st.set_page_config(page_title="Dulcemente Nicolle - Costos & Pedidos", page_icon="🧁", layout="centered")

# --- ESTÉTICA Y PALETA DE COLORES PASTELERÍA ---
st.markdown("""
    <style>
    .stApp {
        background-color: #FFF0F5;
    }
    h1, h2, h3, h4, h5, h6, label, p, .stMarkdown {
        color: #4A2311 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stButton>button {
        background-color: #E91E63 !important;
        color: #FFFFFF !important;
        border-radius: 10px;
        font-weight: bold;
        border: none;
        padding: 0.5rem 0.8rem;
    }
    .stButton>button:hover {
        background-color: #C2185B !important;
    }
    .stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input, .stTimeInput input {
        background-color: #FFFFFF !important;
        color: #4A2311 !important;
        border: 1.5px solid #F48FB1 !important;
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# Configuración de la API de Gemini
os.environ["GEMINI_API_KEY"] = "TU_API_KEY_DE_GEMINI_AQUI"
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

ARCHIVO_PEDIDOS = "historial_pedidos.json"
ARCHIVO_INSUMOS = "insumos_bd.json"
ARCHIVO_RECETAS = "recetas_bd.json"
ARCHIVO_CATALOGO = "catalogo_bd.json"
ARCHIVO_PROMPT = "prompt_ia.txt"
CARPETA_FOTOS = "fotos_catalogo"
ARCHIVO_CREDENCIALES_CALENDAR = "credenciales_google.json"
CALENDAR_ID = "primary"

os.makedirs(CARPETA_FOTOS, exist_ok=True)

insumos_default = [
    {"nombre": "Harina 0000", "costo_unitario": 1200},
    {"nombre": "Azucar 1kl", "costo_unitario": 1800},
    {"nombre": "Aceite 1.5l", "costo_unitario": 6500},
    {"nombre": "Huevos x30", "costo_unitario": 200},
    {"nombre": "Leche liquida", "costo_unitario": 2200},
    {"nombre": "Mantequilla 5kl", "costo_unitario": 30000},
    {"nombre": "Dulce de Leche 4kl", "costo_unitario": 20000},
    {"nombre": "Ganache de Chocolate 500gr", "costo_unitario": 5500},
    {"nombre": "Caja de torta", "costo_unitario": 2200},
    {"nombre": "Relleno", "costo_unitario": 2200},
    {"nombre": "bandeja", "costo_unitario": 3500},
    {"nombre": "Cacao 180gr", "costo_unitario": 4800},
]

recetas_default = [
    {
        "nombre_producto": "Torta de Chocolate Clásica (Base 2kg)",
        "ingredientes_necesarios": [
            {"nombre": "Harina 0000", "cantidad": 0.400},
            {"nombre": "Azucar 1kl", "cantidad": 1.000},
            {"nombre": "Aceite 1.5l", "cantidad": 0.350},
            {"nombre": "Huevos x30", "cantidad": 11},
            {"nombre": "Dulce de Leche 4kl", "cantidad": 0.350},
            {"nombre": "Ganache de Chocolate 500gr", "cantidad": 0.350},
            {"nombre": "Leche liquida", "cantidad": 0.350},
            {"nombre": "Mantequilla 5kl", "cantidad": 0.300},
            {"nombre": "Caja de torta", "cantidad": 1},
            {"nombre": "bandeja", "cantidad": 1},
            {"nombre": "Cacao 180gr", "cantidad": 0.090},
        ]
    }
]

def cargar_insumos():
  datos = cargar_desde_nube("insumos")
  if datos:
    return datos
  guardar_insumos(insumos_default)
  return insumos_default


def guardar_insumos(insumos):
  guardar_en_nube("insumos", insumos)


def cargar_recetas():
  datos = cargar_desde_nube("recetas")
  if datos:
    return datos
  guardar_recetas(recetas_default)
  return recetas_default


def guardar_recetas(recetas):
  guardar_en_nube("recetas", recetas)


def cargar_gastos():
  datos = cargar_desde_nube("gastos")
  if datos:
    return datos
  return []


def guardar_gastos(gastos):
  guardar_en_nube("gastos", gastos)


def cargar_catalogo():
  if os.path.exists(ARCHIVO_CATALOGO):
    try:
      with open(ARCHIVO_CATALOGO, "r", encoding="utf-8") as f:
        return json.load(f)
    except Exception:
      return []
  return []


def guardar_catalogo(catalogo):
  with open(ARCHIVO_CATALOGO, "w", encoding="utf-8") as f:
    json.dump(catalogo, f, indent=2, ensure_ascii=False)


def guardar_pedido_en_disco(nuevo_pedido):
  pedidos_existentes = consultar_historial()
  pedidos_existentes.append(nuevo_pedido)
  guardar_en_nube("pedidos", pedidos_existentes)


def consultar_historial():
  return cargar_desde_nube("pedidos")


def eliminar_pedido_por_indice(indice_real):
  pedidos_existentes = consultar_historial()
  if 0 <= indice_real < len(pedidos_existentes):
    pedidos_existentes.pop(indice_real)
    guardar_en_nube("pedidos", pedidos_existentes)

def agendar_en_google_calendar(cliente, telefono, resumen, receta, precio_final, fecha_entrega, hora_entrega):
    if not os.path.exists(ARCHIVO_CREDENCIALES_CALENDAR):
        return False, "No se encontró el archivo 'credenciales_google.json' en la carpeta del proyecto."

    try:
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = service_account.Credentials.from_service_account_file(
            ARCHIVO_CREDENCIALES_CALENDAR, scopes=SCOPES
        )
        service = build('calendar', 'v3', credentials=creds)

        inicio_dt = datetime.datetime.combine(fecha_entrega, hora_entrega)
        fin_dt = inicio_dt + datetime.timedelta(hours=1)

        evento = {
            'summary': f"🎂 Pedido: {cliente} - {receta}",
            'description': (
                f"Cliente: {cliente}\n"
                f"Teléfono: {telefono}\n"
                f"Detalle: {resumen}\n"
                f"Total a cobrar: ${precio_final}"
            ),
            'start': {
                'dateTime': inicio_dt.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'end': {
                'dateTime': fin_dt.isoformat(),
                'timeZone': 'America/Argentina/Buenos_Aires',
            },
            'colorId': '4',
        }

        evento_creado = service.events().insert(calendarId=CALENDAR_ID, body=evento).execute()
        return True, evento_creado.get('htmlLink')
    except Exception as e:
        return False, str(e)

def quitar_fondo_blanco(imagen):
    img = imagen.convert("RGBA")
    datas = img.getdata()
    nueva_data = [(255, 255, 255, 0) if item[0] > 230 and item[1] > 230 and item[2] > 230 else item for item in datas]
    img.putdata(nueva_data)
    return img

def obtener_logo_base64(imagen_pil):
    if imagen_pil is None:
        return None
    buffered = io.BytesIO()
    imagen_pil.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def calcular_costo_offline(mensaje, recetas, insumos):
    precios = {i['nombre']: i['costo_unitario'] for i in insumos}
    msg_l = mensaje.lower()

    receta = recetas[0]
    for r in recetas:
        palabras_clave = [p for p in r['nombre_producto'].lower().split() if len(p) > 3 and p not in ["torta", "base", "para"]]
        if any(palabra in msg_l for palabra in palabras_clave):
            receta = r
            break

    factor = 1.0
    if "4kg" in msg_l or "4 kg" in msg_l:
        factor = 2.0
    elif "3kg" in msg_l or "3 kg" in msg_l:
        factor = 1.5
    elif "1kg" in msg_l or "1 kg" in msg_l:
        factor = 0.5

    costo_total = 0
    lineas = []
    for ing in receta["ingredientes_necesarios"]:
        nombre = ing["nombre"]
        cant = round(ing["cantidad"] * factor, 3)
        pu = precios.get(nombre, 0)
        sub = cant * pu
        costo_total += sub
        lineas.append(f"- {nombre}: {cant} (Unid. x ${pu}) = ${int(sub)}")

    costo_final = int(costo_total)
    precio_sugerido = int(costo_final * 2.5)

    return {
        "resumen": f"Pedido interpretado: {mensaje[:100]}...",
        "receta_utilizada": f"{receta['nombre_producto']}",
        "desglose_detallado": "\n".join(lineas),
        "costo_materiales": costo_final,
        "precio_sugerido": precio_sugerido
    }

def generar_pdf_presupuesto(cliente, telefono, resumen, receta, precio_final, fecha_entrega=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, textColor=colors.HexColor("#4A2311"), spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle', parent=styles['Normal'], fontName='Helvetica-Oblique', fontSize=11, textColor=colors.HexColor("#E91E63"), spaceAfter=15
    )
    body_style = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=11, textColor=colors.HexColor("#333333"), leading=16
    )
    header_box_style = ParagraphStyle(
        'HeaderBoxStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#4A2311")
    )

    logo_path = None
    for n in ["logo.jpg", "Logo.jpg", "logo.png", "Logo.png"]:
        if os.path.exists(n):
            logo_path = n
            break

    if logo_path:
        try:
            img = Image.open(logo_path)
            img_clean = quitar_fondo_blanco(img)
            temp_logo = "temp_logo_pdf.png"
            img_clean.save(temp_logo)
            logo_rl = RLImage(temp_logo, width=80, height=80)
        except Exception:
            logo_rl = Paragraph("🧁", title_style)
    else:
        logo_rl = Paragraph("🧁", title_style)

    header_text = [
        Paragraph("Dulcemente Nicolle", title_style),
        Paragraph("Pastelería Artesanal & Repostería Creativa", subtitle_style)
    ]

    table_header = Table([[logo_rl, header_text]], colWidths=[90, 430])
    table_header.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (0,0), (0,0), 'LEFT')]))
    story.append(table_header)
    story.append(Spacer(1, 15))

    fecha_texto = f"<br/><b>Fecha de Entrega:</b> {fecha_entrega}" if fecha_entrega else ""
    info_data = [
        [Paragraph(f"<b>Cliente:</b> {cliente}{fecha_texto}", header_box_style),
         Paragraph(f"<b>Teléfono:</b> {telefono}", header_box_style)]
    ]
    info_table = Table(info_data, colWidths=[300, 220])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFF0F5")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#F48FB1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>Detalle del Presupuesto:</b>", ParagraphStyle('Sub', parent=title_style, fontSize=14)))
    story.append(Spacer(1, 5))
    story.append(Paragraph(f"<b>Descripción:</b> {resumen}", body_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"<b>Producto / Base:</b> {receta}", body_style))
    story.append(Spacer(1, 25))

    total_data = [
        [Paragraph("<b>TOTAL A PAGAR:</b>", ParagraphStyle('TotText', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor("#4A2311"))),
         Paragraph(f"<b>${precio_final}</b>", ParagraphStyle('TotNum', fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor("#E91E63"), alignment=2))]
    ]
    total_table = Table(total_data, colWidths=[320, 200])
    total_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFE4E1")),
        ('PADDING', (0,0), (-1,-1), 12),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor("#E91E63")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(total_table)

    story.append(Spacer(1, 40))
    story.append(Paragraph("<i>¡Gracias por confiar en Dulcemente Nicolle para tus momentos especiales! 💖</i>", ParagraphStyle('Pie', fontName='Helvetica-Oblique', fontSize=9, textColor=colors.HexColor("#777777"), alignment=1)))

    doc.build(story)
    buffer.seek(0)
    return buffer

nombres_posibles = ["logo.jpg", "Logo.jpg", "logo.png", "Logo.png", "Logo_2.jpg", "logo_2.jpg"]
logo_cargado = None

for nombre in nombres_posibles:
    if os.path.exists(nombre):
        try:
            img_raw = Image.open(nombre)
            logo_cargado = quitar_fondo_blanco(img_raw)
            break
        except Exception:
            pass

logo_b64 = obtener_logo_base64(logo_cargado)

col_logo, col_texto = st.columns([1, 3])
with col_logo:
    if logo_cargado:
        st.image(logo_cargado, width="stretch")
    else:
        st.warning("⚠️ Logo no encontrado.")

with col_texto:
    st.markdown("<h2 style='margin-bottom: 0px;'>Dulcemente Nicolle</h2>", unsafe_allow_html=True)
    st.write("AGENDA DE PEDIDOS- CONTROL DE COSTOS- RECETAS")

st.markdown("---")

menu = st.radio(
    "Selecciona una opción:",
    [
        "Nuevo Pedido (WhatsApp)",
        "Calendario de Pedidos",
        "Recetas Base",
        "Catálogo de Fotos",
        "Editar Precios / Insumos",
        "Gastos & Ganancias",
        "Historial de Pedidos"
    ]
)

insumos_bd = cargar_insumos()
recetas_bd = cargar_recetas()

if menu == "Nuevo Pedido (WhatsApp)":
    st.subheader("📩 Analizar mensaje de cliente")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        nombre_input = st.text_input("Nombre del cliente:", placeholder="Ej: María Gómez")
    with col_c2:
        telefono_cliente = st.text_input("Teléfono del cliente:", placeholder="Ej: 5491122334455")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        fecha_entrega = st.date_input("📅 Fecha de entrega:", value=datetime.date.today() + datetime.timedelta(days=2))
    with col_f2:
        hora_entrega = st.time_input("⏰ Hora de entrega:", value=datetime.time(16, 0))

    mensaje_texto = st.text_area("Pega aquí el mensaje de WhatsApp del cliente:", placeholder="Hola, quiero encargar una torta de chocolate...")

    if st.button("🚀 Calcular Costos con Receta Exacta"):
        if mensaje_texto.strip() == "":
            st.warning("Por favor, ingresa el texto del mensaje.")
        else:
            with st.spinner("Procesando presupuesto..."):
                datos_pedido = None
                modo_offline = False

                try:
                    if os.path.exists(ARCHIVO_PROMPT):
                        with open(ARCHIVO_PROMPT, "r", encoding="utf-8") as pf:
                            plantilla_prompt = pf.read()
                    else:
                        plantilla_prompt = "Eres un pastelero. Mensaje: {mensaje_texto}. Recetas: {recetas_str}. Insumos: {insumos_str}."

                    prompt = plantilla_prompt.format(
                        mensaje_texto=mensaje_texto,
                        recetas_str=json.dumps(recetas_bd, ensure_ascii=False),
                        insumos_str=json.dumps(insumos_bd, ensure_ascii=False)
                    )

                    respuesta = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                        config=types.GenerateContentConfig(response_mime_type="application/json"),
                    )
                    datos_pedido = json.loads(respuesta.text)

                except Exception as e:
                    modo_offline = True
                    datos_pedido = calcular_costo_offline(mensaje_texto, recetas_bd, insumos_bd)

                cliente_final = nombre_input if nombre_input.strip() != "" else "Cliente Anónimo"

                reporte_final = {
                    "nombre_cliente": cliente_final,
                    "telefono": telefono_cliente if telefono_cliente.strip() != "" else "Sin teléfono",
                    "fecha_entrega": fecha_entrega.strftime("%d/%m/%Y"),
                    "hora_entrega": hora_entrega.strftime("%H:%M"),
                    "detalle": datos_pedido
                }

                st.session_state['ultimo_calculo'] = reporte_final

                if modo_offline:
                    st.warning("⚠️ Límite o error de conexión con IA. Cálculo realizado mediante el **motor offline de respaldo**.")
                else:
                    st.success("¡Presupuesto base calculado con IA!")

    if 'ultimo_calculo' in st.session_state:
        calc = st.session_state['ultimo_calculo']
        det = calc['detalle']

        st.markdown("---")
        st.subheader("⚙️ Ajustes Finales del Pedido (Delivery & Adicionales)")

        col_deliv1, col_deliv2 = st.columns([1, 1])
        with col_deliv1:
            incluir_delivery = st.checkbox("🚚 ¿Incluye Delivery?", value=False)
        with col_deliv2:
            costo_delivery = st.number_input("Costo de Delivery ($)", min_value=0, value=2500, step=500) if incluir_delivery else 0

        st.markdown("#### ✨ Ítems Adicionales (Toppers, Impresión de Arroz, etc.)")
        col_ad_desc, col_ad_precio = st.columns([2, 1])
        with col_ad_desc:
            desc_adicional = st.text_input("Descripción del adicional", placeholder="Ej: Topper personalizado y lámina comestible")
        with col_ad_precio:
            precio_adicional = st.number_input("Costo Adicional ($)", min_value=0, value=0, step=200)

        agendar_calendar = st.checkbox("📅 Agendar automáticamente en Google Calendar al guardar", value=True)

        precio_base = det.get('precio_sugerido', 0)
        precio_total_final = precio_base + costo_delivery + precio_adicional

        st.markdown("---")
        st.info(f"**Cliente:** {calc['nombre_cliente']} | **Tel:** {calc['telefono']} | **Entrega:** {fecha_entrega.strftime('%d/%m/%Y')} {hora_entrega.strftime('%H:%M')} hs")
        st.write(f"**Receta base:** {det.get('receta_utilizada')}")
        st.write(f"**Resumen:** {det.get('resumen')}")
        with st.expander("🔍 Ver desglose de costos de materiales"):
            st.text(det.get('desglose_detallado', ''))
            st.write(f"**Costo puro de insumos:** ${det.get('costo_materiales', 0)}")

        if desc_adicional.strip() != "" and precio_adicional > 0:
            st.write(f"**Adicional incluido:** {desc_adicional} (+${precio_adicional})")
        if incluir_delivery:
            st.write(f"**Delivery incluido:** (+${costo_delivery})")

        st.metric(label="PRECIO FINAL TOTAL A COBRAR", value=f"${precio_total_final}")

        calc_final_guardar = {
            "nombre_cliente": calc['nombre_cliente'],
            "telefono": calc['telefono'],
            "fecha_entrega": f"{fecha_entrega.strftime('%d/%m/%Y')} {hora_entrega.strftime('%H:%M')}",
            "receta": det.get('receta_utilizada'),
            "precio_final": precio_total_final,
            "detalle": {
                "resumen": f"{det.get('resumen')} | Extras: {desc_adicional} (${precio_adicional}) | Delivery: ${costo_delivery}" if desc_adicional else f"{det.get('resumen')} | Delivery: ${costo_delivery}",
                "receta_utilizada": det.get('receta_utilizada'),
                "desglose_detallado": det.get('desglose_detallado'),
                "costo_materiales": det.get('costo_materiales'),
                "precio_sugerido": precio_total_final
            }
        }

        st.markdown("---")
        st.markdown("#### 📄 Confirmar y Guardar Pedido")

        col_q1, col_q2 = st.columns([1, 1])
        with col_q1:
            generar_pdf_si = st.button("✅ Confirmar, Agendar y Generar PDF")
        with col_q2:
            guardar_historial_btn = st.button("💾 Confirmar y Agendar (sin PDF)")

        if generar_pdf_si or guardar_historial_btn:
            guardar_pedido_en_disco(calc_final_guardar)

            if agendar_calendar:
                exito_cal, resp_cal = agendar_en_google_calendar(
                    cliente=calc_final_guardar['nombre_cliente'],
                    telefono=calc_final_guardar['telefono'],
                    resumen=calc_final_guardar['detalle']['resumen'],
                    receta=calc_final_guardar['detalle']['receta_utilizada'],
                    precio_final=precio_total_final,
                    fecha_entrega=fecha_entrega,
                    hora_entrega=hora_entrega
                )
                if exito_cal:
                    st.success(f"📅 ¡Evento agendado en Google Calendar! [Ver en Calendar]({resp_cal})")
                else:
                    st.warning(f"⚠️ Pedido guardado localmente, pero no se pudo agendar en Google Calendar: {resp_cal}")

            if generar_pdf_si:
                pdf_buffer = generar_pdf_presupuesto(
                    cliente=calc_final_guardar['nombre_cliente'],
                    telefono=calc_final_guardar['telefono'],
                    resumen=calc_final_guardar['detalle']['resumen'],
                    receta=calc_final_guardar['detalle']['receta_utilizada'],
                    precio_final=precio_total_final,
                    fecha_entrega=calc_final_guardar['fecha_entrega']
                )
                st.success("¡Pedido guardado y PDF listo para descargar!")
                st.download_button(
                    label="📥 Descargar PDF Definitivo",
                    data=pdf_buffer,
                    file_name=f"Presupuesto_{calc_final_guardar['nombre_cliente'].replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
            else:
                st.success("¡Pedido guardado exitosamente en el Historial!")

elif menu == "Calendario de Pedidos":
    st.subheader("🗓️ Calendario Mensual de Entregas")
    st.write("Haz clic directamente sobre cualquier día con tu logo de fondo para ver los datos del pedido.")

    historial = consultar_historial()
    hoy = datetime.date.today()

    meses_es = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    col_mes, col_anio = st.columns([2, 1])
    with col_mes:
        mes_seleccionado_nombre = st.selectbox("Mes:", meses_es, index=hoy.month - 1)
        mes_num = meses_es.index(mes_seleccionado_nombre) + 1
    with col_anio:
        anio_num = st.number_input("Año:", min_value=2024, max_value=2035, value=hoy.year, step=1)

    pedidos_por_fecha = {}
    for idx, p in enumerate(historial):
        f_str = p.get('fecha_entrega', '')
        solo_fecha = f_str.split(" ")[0] if " " in f_str else f_str
        if solo_fecha:
            pedidos_por_fecha.setdefault(solo_fecha, []).append((idx, p))

    dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    cols_header = st.columns(7)
    for idx_d, d_nom in enumerate(dias_semana):
        with cols_header[idx_d]:
            st.markdown(f"<div style='text-align:center; font-weight:bold; color:#E91E63;'>{d_nom}</div>", unsafe_allow_html=True)

    logo_watermark_b64 = None
    if logo_cargado:
        logo_wm = logo_cargado.copy().convert("RGBA")
        r, g, b, a = logo_wm.split()
        a = a.point(lambda p: int(p * 0.30))
        logo_wm = Image.merge("RGBA", (r, g, b, a))
        logo_watermark_b64 = obtener_logo_base64(logo_wm)

    estilos_botones = ["<style>"]
    matriz_mes = calendar.monthcalendar(int(anio_num), mes_num)

    for semana in matriz_mes:
        for dia in semana:
            if dia != 0:
                fecha_clave = f"{dia:02d}/{mes_num:02d}/{int(anio_num)}"
                tiene_pedidos = len(pedidos_por_fecha.get(fecha_clave, [])) > 0
                if tiene_pedidos and logo_watermark_b64:
                    estilos_botones.append(
                        f"div.st-key-dia_{dia} button {{"
                        f"background-color: #FFFFFF !important;"
                        f"color: #4A2311 !important;"
                        f"border: 2px solid #E91E63 !important;"
                        f"height: 68px !important;"
                        f"font-size: 18px !important;"
                        f"font-weight: 900 !important;"
                        f"background-image: url('data:image/png;base64,{logo_watermark_b64}') !important;"
                        f"background-size: 48px 48px !important;"
                        f"background-repeat: no-repeat !important;"
                        f"background-position: center !important;"
                        f"}}"
                    )
                elif tiene_pedidos:
                    estilos_botones.append(
                        f"div.st-key-dia_{dia} button {{"
                        f"background-color: #FFE4E1 !important;"
                        f"color: #E91E63 !important;"
                        f"border: 2px solid #E91E63 !important;"
                        f"height: 68px !important;"
                        f"font-size: 18px !important;"
                        f"font-weight: 900 !important;"
                        f"}}"
                    )
                else:
                    estilos_botones.append(
                        f"div.st-key-dia_{dia} button {{"
                        f"background-color: #FFFFFF !important;"
                        f"color: #4A2311 !important;"
                        f"border: 1px solid #F48FB1 !important;"
                        f"height: 68px !important;"
                        f"font-size: 16px !important;"
                        f"font-weight: normal !important;"
                        f"}}"
                    )
    estilos_botones.append("</style>")
    st.markdown("\n".join(estilos_botones), unsafe_allow_html=True)

    for semana in matriz_mes:
        cols_sem = st.columns(7)
        for i, dia in enumerate(semana):
            with cols_sem[i]:
                if dia == 0:
                    st.write("")
                else:
                    fecha_clave = f"{dia:02d}/{mes_num:02d}/{int(anio_num)}"
                    pedidos_dia = pedidos_por_fecha.get(fecha_clave, [])
                    tiene_pedidos = len(pedidos_dia) > 0

                    if st.button(f"{dia}", key=f"dia_{dia}", use_container_width=True):
                        if tiene_pedidos:
                            st.session_state['fecha_cal_seleccionada'] = fecha_clave
                        else:
                            st.session_state['fecha_cal_seleccionada'] = None
                            st.toast(f"No hay pedidos agendados para el {fecha_clave}")

    if st.session_state.get('fecha_cal_seleccionada'):
        f_sel = st.session_state['fecha_cal_seleccionada']
        pedidos_mostrar = pedidos_por_fecha.get(f_sel, [])

        if pedidos_mostrar:
            st.markdown("---")
            col_tit_det, col_cerrar_det = st.columns([4, 1])
            with col_tit_det:
                st.markdown(f"### 🎂 Pedidos programados para el día {f_sel}")
            with col_cerrar_det:
                if st.button("✖ Cerrar"):
                    st.session_state['fecha_cal_seleccionada'] = None
                    st.rerun()

            for idx_real, ped in pedidos_mostrar:
                det_p = ped.get('detalle', {})
                with st.container():
                    st.info(f"**Cliente:** {ped.get('nombre_cliente')} | **Tel:** {ped.get('telefono')} | **Entrega:** {ped.get('fecha_entrega')}")
                    st.write(f"**Producto / Receta:** {det_p.get('receta_utilizada', 'No especificada')}")
                    st.write(f"**Detalle completo:** {det_p.get('resumen', '')}")
                    st.write(f"**Total a cobrar:** ${det_p.get('precio_sugerido', 0)}")

                    pdf_cal = generar_pdf_presupuesto(
                        cliente=ped.get('nombre_cliente', 'Cliente'),
                        telefono=ped.get('telefono', ''),
                        resumen=det_p.get('resumen', ''),
                        receta=det_p.get('receta_utilizada', ''),
                        precio_final=det_p.get('precio_sugerido', 0),
                        fecha_entrega=ped.get('fecha_entrega', '')
                    )
                    st.download_button(
                        label="📥 Descargar PDF de este pedido",
                        data=pdf_cal,
                        file_name=f"Presupuesto_{ped.get('nombre_cliente', 'Cliente').replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"pdf_cal_{idx_real}_{f_sel}"
                    )
                    st.markdown("---")

elif menu == "Recetas Base":
    st.subheader("📖 Gestor de Recetas Base")
    st.write("Crea nuevas recetas seleccionando tus insumos cargados. Tanto la IA como el cálculo offline las usarán automáticamente.")

    if 'ingredientes_nueva_receta' not in st.session_state:
        st.session_state['ingredientes_nueva_receta'] = []

    st.markdown("#### ➕ Crear Nueva Receta")
    nombre_nueva_receta = st.text_input("Nombre de la Receta (incluye el peso o porciones base):", placeholder="Ej: Torta Red Velvet (Base 2kg) o Box 12 Cupcakes")

    nombres_insumos_disponibles = [i['nombre'] for i in insumos_bd]

    col_ing1, col_ing2, col_ing3 = st.columns([2, 1, 1])
    with col_ing1:
        ing_seleccionado = st.selectbox("Insumo:", nombres_insumos_disponibles)
    with col_ing2:
        cant_ing = st.number_input("Cantidad (ej: 0.500 o 2):", min_value=0.001, value=0.500, step=0.050, format="%.3f")
    with col_ing3:
        st.write("")
        st.write("")
        if st.button("➕ Añadir"):
            encontrado = False
            for item in st.session_state['ingredientes_nueva_receta']:
                if item['nombre'] == ing_seleccionado:
                    item['cantidad'] = round(item['cantidad'] + cant_ing, 3)
                    encontrado = True
                    break
            if not encontrado:
                st.session_state['ingredientes_nueva_receta'].append({
                    "nombre": ing_seleccionado,
                    "cantidad": cant_ing
                })

    if st.session_state['ingredientes_nueva_receta']:
        st.markdown("**Ingredientes agregados a esta receta:**")
        precios_map = {i['nombre']: i['costo_unitario'] for i in insumos_bd}
        costo_estimado_receta = 0

        for idx_temp, ing_temp in enumerate(st.session_state['ingredientes_nueva_receta']):
            sub = ing_temp['cantidad'] * precios_map.get(ing_temp['nombre'], 0)
            costo_estimado_receta += sub
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"• **{ing_temp['nombre']}**: {ing_temp['cantidad']} unid/kg — *Costo aprox: ${int(sub)}*")
            with c2:
                if st.button("❌", key=f"quitar_temp_{idx_temp}"):
                    st.session_state['ingredientes_nueva_receta'].pop(idx_temp)
                    st.rerun()

        st.info(f"💰 **Costo total estimado de materiales para esta receta:** ${int(costo_estimado_receta)}")

        if st.button("💾 Guardar Receta en Base de Datos"):
            if nombre_nueva_receta.strip() == "":
                st.error("Por favor, escribe un nombre para la receta antes de guardar.")
            else:
                nueva_receta_obj = {
                    "nombre_producto": nombre_nueva_receta.strip(),
                    "ingredientes_necesarios": st.session_state['ingredientes_nueva_receta']
                }
                recetas_bd.append(nueva_receta_obj)
                guardar_recetas(recetas_bd)
                st.session_state['ingredientes_nueva_receta'] = []
                st.success(f"¡Receta '{nombre_nueva_receta}' guardada con éxito!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 Recetas Guardadas Actualmente:")
    precios_map = {i['nombre']: i['costo_unitario'] for i in insumos_bd}

    for idx_r, rec in enumerate(recetas_bd):
        costo_rec = sum(ing['cantidad'] * precios_map.get(ing['nombre'], 0) for ing in rec['ingredientes_necesarios'])
        with st.expander(f"🍰 {rec['nombre_producto']} (Costo base: ${int(costo_rec)})"):
            for ing in rec['ingredientes_necesarios']:
                st.write(f"- {ing['nombre']}: {ing['cantidad']}")
            if len(recetas_bd) > 1:
                if st.button("🗑️ Eliminar receta", key=f"del_rec_{idx_r}"):
                    recetas_bd.pop(idx_r)
                    guardar_recetas(recetas_bd)
                    st.success("Receta eliminada.")
                    st.rerun()

elif menu == "Catálogo de Fotos":
    st.subheader("🖼️ Catálogo de Productos y Tortas")
    st.write("Agrega fotos de tus trabajos para mostrárselos a los clientes o elimina los que ya no estén disponibles.")

    catalogo = cargar_catalogo()

    with st.form("form_nuevo_producto", clear_on_submit=True):
        st.markdown("#### ➕ Agregar Nuevo Producto al Catálogo")
        nombre_prod = st.text_input("Nombre de la Torta / Producto")
        precio_prod = st.number_input("Precio estimativo ($)", min_value=0, step=100)
        desc_prod = st.text_area("Descripción breve (tamaño, sabores, temática)")
        imagen_subida = st.file_uploader("Sube la foto del producto", type=["jpg", "jpeg", "png"])

        btn_agregar = st.form_submit_button("Guardar en el Catálogo")

        if btn_agregar:
            if nombre_prod.strip() == "" or imagen_subida is None:
                st.error("Por favor, ingresa al menos el nombre y selecciona una imagen.")
            else:
                ruta_imagen = os.path.join(CARPETA_FOTOS, imagen_subida.name)
                with open(ruta_imagen, "wb") as f:
                    f.write(imagen_subida.getbuffer())

                nuevo_item = {
                    "nombre": nombre_prod,
                    "precio": precio_prod,
                    "descripcion": desc_prod,
                    "imagen": ruta_imagen
                }

                catalogo.append(nuevo_item)
                guardar_catalogo(catalogo)
                st.success("¡Producto agregado al catálogo con éxito!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 Productos Actuales en Catálogo:")

    if not catalogo:
        st.info("Aún no hay fotos cargadas en el catálogo.")
    else:
        for idx, item in enumerate(catalogo):
            with st.container():
                col_img, col_info = st.columns([1, 2])
                with col_img:
                    if os.path.exists(item['imagen']):
                        st.image(item['imagen'], width="stretch")
                    else:
                        st.warning("Imagen no encontrada")
                with col_info:
                    st.markdown(f"### {item['nombre']}")
                    st.write(f"**Precio de referencia:** ${item['precio']}")
                    st.write(f"**Descripción:** {item['descripcion']}")

                    if st.button("🗑️ Eliminar del catálogo", key=f"del_cat_{idx}"):
                        try:
                            if os.path.exists(item['imagen']):
                                os.remove(item['imagen'])
                        except Exception:
                            pass

                        catalogo.pop(idx)
                        guardar_catalogo(catalogo)
                        st.success("¡Producto eliminado del catálogo!")
                        st.rerun()
                st.markdown("---")

elif menu == "Editar Precios / Insumos":
    st.subheader("🛒 Gestor de Insumos y Precios")
    st.write("Modifica el precio de cualquier ingrediente o agrega nuevos insumos si suben de precio a último minuto.")

    insumos_actuales = cargar_insumos()
    nuevos_insumos = []

    with st.form("form_insumos"):
        st.markdown("#### Lista de Insumos:")
        for idx, item in enumerate(insumos_actuales):
            col_nom, col_precio = st.columns([2, 1])
            with col_nom:
                nombre = st.text_input(f"Insumo #{idx+1}", value=item['nombre'], key=f"nom_{idx}")
            with col_precio:
                precio = st.number_input("Precio ($)", value=int(item['costo_unitario']), step=50, key=f"prec_{idx}")
            nuevos_insumos.append({"nombre": nombre, "costo_unitario": precio})

        st.markdown("---")
        st.markdown("#### ➕ Agregar Nuevo Insumo:")
        col_nuevo_nom, col_nuevo_prec = st.columns([2, 1])
        with col_nuevo_nom:
            nuevo_nombre = st.text_input("Nombre del nuevo ingrediente", key="nuevo_nom")
        with col_nuevo_prec:
            nuevo_precio = st.number_input("Precio ($)", value=0, step=50, key="nuevo_prec")

        guardar_cambios = st.form_submit_button("💾 Guardar Cambios de Precios")

        if guardar_cambios:
            if nuevo_nombre.strip() != "" and nuevo_precio > 0:
                nuevos_insumos.append({"nombre": nuevo_nombre.strip(), "costo_unitario": nuevo_precio})

            guardar_insumos(nuevos_insumos)
            st.success("¡Base de datos de precios actualizada correctamente!")
            st.rerun()

elif menu == "Gastos & Ganancias":
    st.subheader("💰 Control de Gastos y Ganancias")

    with st.form("form_nuevo_gasto"):
        st.write("Registrar nuevo gasto operativo (servicios, empaques, transporte, etc.)")
        desc_gasto = st.text_input("Descripción del gasto", placeholder="Ej: Luz, Gas, Delivery")
        monto_gasto = st.number_input("Monto ($)", min_value=0.0, step=100.0)
        fecha_gasto = st.date_input("Fecha del gasto", value=datetime.date.today())

        submitted_gasto = st.form_submit_button("Guardar Gasto")
        if submitted_gasto:
            gastos_actuales = cargar_gastos()
            nuevo_gasto = {
                "descripcion": desc_gasto,
                "monto": monto_gasto,
                "fecha": str(fecha_gasto),
            }
            gastos_actuales.append(nuevo_gasto)
            guardar_gastos(gastos_actuales)
            st.success("¡Gasto registrado con éxito en la nube!")
            st.rerun()

    st.markdown("### 📊 Resumen Financiero")
    pedidos_reg = consultar_historial()
    gastos_reg = cargar_gastos()

    total_ingresos = sum(float(p.get("precio_final", 0) or 0) for p in pedidos_reg)
    total_gastos = sum(float(g.get("monto", 0) or 0) for g in gastos_reg)
    ganancia_neta = total_ingresos - total_gastos

    col1, col2, col3 = st.columns(3)
    col1.metric("Ingresos Totales (Pedidos)", f"${total_ingresos:,.2f}")
    col2.metric("Gastos Operativos", f"${total_gastos:,.2f}")
    col3.metric("Balance / Ganancia Neta", f"${ganancia_neta:,.2f}")

    if gastos_reg:
        st.markdown("#### Historial de Gastos")
        st.dataframe(gastos_reg, use_container_width=True)

elif menu == "Historial de Pedidos":
    st.subheader("📂 Registro Histórico de Ventas y Desglose de Insumos")
    historial = consultar_historial()

    if not historial:
        st.info("Aún no hay pedidos guardados.")
    else:
        for idx, pedido in enumerate(reversed(historial)):
            indice_real = len(historial) - 1 - idx
            nombre_c = pedido.get('nombre_cliente', 'Sin nombre')
            tel_c = pedido.get('telefono', 'Sin teléfono')
            fecha_e = pedido.get('fecha_entrega', 'No especificada')
            det = pedido.get('detalle', {})

            with st.expander(f"Pedido #{indice_real + 1} - {nombre_c} | Entrega: {fecha_e}"):
                st.write(f"**Teléfono:** {tel_c}")
                st.write(f"**Resumen:** {det.get('resumen')}")
                if "receta_utilizada" in det:
                    st.write(f"**Receta:** {det.get('receta_utilizada')}")
                st.write(f"**Precio Final Total:** ${det.get('precio_sugerido')}")

                st.markdown("---")
                st.markdown("### 🛒 Insumos calculados para este pedido:")
                
                recetas_disponibles = cargar_recetas()
                receta_nombre = pedido.get("receta", "")
                if not receta_nombre and "receta_utilizada" in det:
                    receta_nombre = det.get("receta_utilizada")

                receta_encontrada = next(
                    (r for r in recetas_disponibles if r.get("nombre_producto") == receta_nombre),
                    None,
                )

                if receta_encontrada and "ingredientes_necesarios" in receta_encontrada:
                    ingredientes = receta_encontrada["ingredientes_necesarios"]
                    if isinstance(ingredientes, str):
                        try:
                            ingredientes = json.loads(ingredientes)
                        except:
                            ingredientes = []

                    for ing in ingredientes:
                        st.text(f"• {ing.get('nombre', 'Insumo')}: {ing.get('cantidad', 0)} unidades/kg")
                else:
                    st.info("No se encontró el desglose automático de ingredientes para esta receta.")

                st.markdown("---")
                col_btn1, col_btn2 = st.columns([1, 1])
                with col_btn1:
                    pdf_hist = generar_pdf_presupuesto(
                        cliente=nombre_c,
                        telefono=tel_c,
                        resumen=det.get('resumen', ''),
                        receta=det.get('receta_utilizada', ''),
                        precio_final=det.get('precio_sugerido', 0),
                        fecha_entrega=fecha_e
                    )
                    st.download_button(
                        label="📄 Descargar PDF",
                        data=pdf_hist,
                        file_name=f"Presupuesto_{nombre_c.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{indice_real}"
                    )
                with col_btn2:
                    if st.button(f"🗑️ Borrar pedido", key=f"eliminar_{indice_real}"):
                        eliminar_pedido_por_indice(indice_real)
                        st.success("¡Pedido eliminado correctamente!")
                        st.rerun()
