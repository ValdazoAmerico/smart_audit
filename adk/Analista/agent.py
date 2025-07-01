import os
from dotenv import load_dotenv
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.cloud import bigquery
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.run_config import RunConfig
from typing import Dict, Any
from datetime import date, datetime
from google import genai
from google.genai import types

import google.generativeai as genai
from pydantic import BaseModel
import json

# Cargar variables de entorno desde .env
load_dotenv()

from datetime import datetime

def obtener_fecha():
    return datetime.now().strftime("%Y-%m-%d")

# Establecer variables de entorno necesarias
os.environ['GOOGLE_API_KEY'] = os.getenv("GOOGLE_API_KEY")
os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Inicializar cliente de BigQuery - ACTUALIZA CON TU PROJECT ID
client_bq = bigquery.Client(project="uma-datascience-dev")  # Cambia por tu project ID

class SQLResult(BaseModel):
    consulta_sql: str

# Definir función para generar SQL
def generar_sql(pregunta: str) -> Dict[str, Any]:
    """
    Genera una consulta SQL basada en la pregunta del usuario.
    """
    prompt = f"""
Sos un asistente experto en análisis de datos médicos/administrativos que responde preguntas en lenguaje natural
transformándolas en consultas SQL para BigQuery.

Tabla disponible: `uma-datascience-dev.Bigquery_Dataset.evaluaciones_auditoria`

Columnas disponibles:
- Fecha (DATE): Fecha del registro
- Practica_solicitada (STRING): Descripción de la práctica médica solicitada
- DNI (INTEGER): Documento Nacional de Identidad del paciente
- Profesional (STRING): Nombre del profesional médico
- Estado (STRING): Estado actual del registro/solicitud

🔎 Valores posibles para la columna `Estado`:
- "aprobado"
- "rechazado"

(No existen otros estados. No inventes valores como "pendiente", "en revisión", etc.)

Algunos valores de la columna 'practica_solicitada' son:

Análisis de sangre
Colonoscopia
Ecografía abdominal
Electrocardiograma
Endoscopia digestiva alta
Mamografía
Radiografía de cráneo
Radiografía de rodilla
Resonancia de cerebro
Resonancia de columna lumbar
Tomografía de tórax


⚠️ Importante:
- Siempre usá nombres de tabla completamente calificados: `uma-datascience-dev.Bigquery_Dataset.evaluaciones_auditoria`
- Usá comillas invertidas para referenciar tablas y campos cuando sea necesario
- Para fechas, usá el formato DATE en las consultas (ej: DATE('2024-01-01'))
- Si la pregunta es ambigua, asumí una interpretación razonable y explícita
- No inventes campos que no existen en el schema

📘 Ejemplos de preguntas y sus consultas SQL:

- Pregunta: ¿Cuántas prácticas se solicitaron este mes?

Esperamos una respuesta tipo:

SELECT COUNT(*) AS total_practicas FROM `uma-datascience-dev.Bigquery_Dataset.evaluaciones_auditoria` WHERE EXTRACT(MONTH FROM Fecha) = EXTRACT(MONTH FROM CURRENT_DATE()) AND EXTRACT(YEAR FROM Fecha) = EXTRACT(YEAR FROM CURRENT_DATE())


- Pregunta: ¿Cuántas prácticas se aprobaron este año?

Esperamos una respuesta tipo:

SELECT COUNT(*) AS total_aprobadas FROM `uma-datascience-dev.Bigquery_Dataset.evaluaciones_auditoria` WHERE Estado = 'aprobado' AND EXTRACT(YEAR FROM Fecha) = EXTRACT(YEAR FROM CURRENT_DATE())

---

Ejemplos de consultas típicas:
- "¿Cuántas prácticas se solicitaron este mes?" 
- "¿Qué profesionales han atendido más pacientes?"
- "¿Cuáles son los estados más comunes?"
- "¿Qué prácticas se solicitan más frecuentemente?"

La fecha de hoy es: {obtener_fecha()}


---


Consulta del usuario: {pregunta}

Genera una consulta SQL precisa y eficiente.


"""

    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite",
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": SQLResult
        }
    )   
    response = model.generate_content(prompt)
    consulta_sql = json.loads(response.text)
    print("Consulta SQL generada:", consulta_sql)
    return consulta_sql

# Definir función para ejecutar SQL
def ejecutar_sql(consulta_sql: str) -> Dict[str, Any]:
    """
    Ejecuta una consulta SQL en BigQuery y devuelve los resultados.
    """
    try:
        print("⏳ Ejecutando SQL:")
        print(consulta_sql)

        query_job = client_bq.query(consulta_sql)

        print("✅ Query enviada, esperando resultados...")
        results = query_job.result()

        resultados = []
        for row in results:
            row_dict = {}
            for key, value in row.items():
                if isinstance(value, date):
                    row_dict[key] = value.isoformat()
                elif isinstance(value, datetime):
                    row_dict[key] = value.isoformat()
                else:
                    row_dict[key] = value
            resultados.append(row_dict)

        print("✅ Resultados obtenidos:", resultados)
        return {"resultados": resultados, "total_filas": len(resultados)}

    except Exception as e:
        print("❌ Error al ejecutar la consulta SQL:", str(e))
        return {"error": str(e), "resultados": []}


# Envolver funciones como herramientas de ADK
tool_generar_sql = FunctionTool(func=generar_sql)
tool_ejecutar_sql = FunctionTool(func=ejecutar_sql)

# Definir el agente
root_agent = LlmAgent(
    name="analista_datos_medicos",
    model="gemini-2.5-flash",
    instruction="""
Eres un asistente experto en análisis de datos médicos/administrativos. Tu trabajo consiste en interpretar preguntas en lenguaje natural y responderlas con datos reales almacenados en BigQuery.

Tu tabla contiene información sobre:
- Fechas de solicitudes médicas
- Prácticas médicas solicitadas
- DNI de pacientes
- Profesionales médicos
- Estados de las solicitudes

Para responder preguntas:
1. Usa la herramienta `generar_sql` para transformar la pregunta del usuario en una consulta SQL válida
2. Luego usa la herramienta `ejecutar_sql` para ejecutar esa consulta y obtener los resultados
3. Interpreta y presenta los resultados de manera clara y útil

Hazlo automáticamente sin pedir confirmación al usuario. Si encuentras errores, explica qué ocurrió y sugiere alternativas.

Ejemplos de preguntas que puedes responder:
- "¿Cuántas prácticas se solicitaron esta semana?"
- "¿Qué profesional ha atendido más casos?"
- "¿Cuáles son las prácticas más solicitadas?"
- "¿Cómo se distribuyen los estados de las solicitudes?"
- "¿Cuántos pacientes únicos hay en el sistema?"
""",
    tools=[generar_sql, ejecutar_sql],
    generate_content_config=types.GenerationConfig(
        temperature=0.0
    )
)