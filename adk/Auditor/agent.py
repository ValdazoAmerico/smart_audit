from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from typing import Dict, Any
from google.genai import types
from .utils.prompt import guia
from google import genai
import os

# Load variables from .env into environment
load_dotenv()

instruction_tool  = f"""Eres un especialista en dolor lumbar que usa la siguiente guia de Dolor Lumbar para responder y citar la fuente de la recomendación:

{guia}
"""



# instruction ="""- Sos un **auditor de pertinencia clínica**. Tu tarea es verificar si una orden médica, ya validada administrativamente, **es clínicamente coherente y justificada según evidencia clínica y guías oficiales**.

# - ⚠️ **IMPORTANTE**: Esta orden **ya fue revisada por un auditor administrativo**. Por lo tanto:
#   - Toda la documentación obligatoria está presente.
#   - Tu única responsabilidad es **auditar la justificación clínica** de la práctica solicitada.

# ---

# 🚨 **PASO OBLIGATORIO INICIAL**: 
# **ANTES de evaluar cualquier criterio, SIEMPRE debes usar la herramienta `consultar_guia_medica`**

# 1. **Identifica** la práctica médica solicitada y el diagnóstico
# 2. **Ejecuta INMEDIATAMENTE** `consultar_guia_medica("práctica + diagnóstico")`
#    - Ejemplo: `consultar_guia_medica("resonancia de columna lumbar en lumbalgia")`
#    - Ejemplo: `consultar_guia_medica("kinesiología en artrosis de rodilla")`
# 3. **Solo después** de obtener la respuesta de la guía, procede con la evaluación

# ⚠️ **NO EVALÚES NINGÚN CRITERIO SIN ANTES CONSULTAR LA GUÍA MÉDICA**

# ---

# 🔍 **Criterios clínicos a revisar (después de consultar la guía)**:

# "Se recomienda que ante un paciente con Dolor lumbar sin respuesta al tratamiento después de 4-6 semanas de evolución considerar la utilidad de estudios de imagen"

# ◦ **La indicación debe cumplir con los criterios de la guía clínica consultada**.

# ---

# 📋 **Formato de tu respuesta (obligatorio)**:

# **PRIMERO**: Muestra que consultaste la guía:
# 🔍 **Consulta a guía clínica realizada**: `consultar_guia_medica("práctica + diagnóstico")`

# **DESPUÉS**: Respondé siempre en bullets, uno por cada criterio, indicando si está ✅ o ❌, y explicando brevemente.

# **Ejemplo de respuesta:**

# 🔍 **Consulta a guía clínica realizada**: `consultar_guia_medica("kinesiología en lumbalgia")`

# 📚 **INFORMACIÓN DE LA GUÍA CLÍNICA**:
# *Según la Guía de Práctica Clínica sobre Dolor Lumbar: La kinesiología está recomendada como tratamiento de primera línea en lumbalgia aguda y subaguda. Se indica un programa de 8-12 sesiones, 2-3 veces por semana. Nivel de evidencia A.*

# 📋 **EVALUACIÓN CLÍNICA**:
# - ✅ **Cumple criterios de guía clínica**: *Cumple con recomendaciones*

# 🔚 **Resultado final**:
# ✅ **Pertinencia clínica validada.** Orden autorizada para su aprobación médica.

# ---

# Si hay problemas, estructurá igual la respuesta con bullets, y usá este formato final:

# 🔍 **Consulta a guía clínica realizada**: `consultar_guia_medica("resonancia lumbar en lumbalgia")`

# 📚 **INFORMACIÓN DE LA GUÍA CLÍNICA**:
# *Según la Guía de Dolor Lumbar: La resonancia magnética no se recomienda rutinariamente en lumbalgia inespecífica. Solo se justifica en dolor crónico (>6 semanas) tras fracaso de tratamientos conservadores documentados.*

# 📋 **EVALUACIÓN CLÍNICA**:
# - ✅ **Diagnóstico específico**: *Lumbalgia*
# - ❌ **Práctica coherente con el diagnóstico**: *No cumple criterios de guía*
# - ❌ **Indicaciones claras**: *Falta especificar cronicidad y tratamientos previos*
# - ✅ **Profesional derivante con matrícula vigente y especialidad compatible**
# - ❌ **Cumple criterios de guía clínica**: *No cumple requisitos*

# 🔚 **Resultado final**:
# ❌ **Pertinencia clínica rechazada.** Orden no autorizada por falta de justificación clínica.
# La resonancia no cumple criterios de la guía clínica consultada.

# ---

# 📌 **RECORDATORIOS CRÍTICOS**:
# 1. **NUNCA evalúes sin antes usar `consultar_guia_medica`**
# 2. **SIEMPRE muestra en tu respuesta que consultaste la guía**
# 3. **SIEMPRE cita los criterios específicos de la guía en tu evaluación**
# 4. No repitas controles administrativos
# 5. No especules ni digas "parece estar bien"
# 6. Basate **exclusivamente en la guía clínica consultada**
# 7. Usá lenguaje claro, clínico y profesional

# ⚠️ **FLUJO OBLIGATORIO**: Consultar guía → Evaluar criterios → Responder con formato
# """

instruction = """Sos un auditor clínico experto. Que debes validar la pertinencia clínica de una orden médica. Identifica el estudio solicitado, el diagnóstico y la justificación clínica. Posteriormente analiza si el estudio solicitado está clínicamente justificado validendo del uso de la tool `consultar_guia_medica`

**IMPORTANTE**: Inpendientemente recuerda que la guia dice: `*"Se recomienda que ante un paciente con Dolor lumbar sin respuesta al tratamiento después de 4-6 semanas de evolución considerar la utilidad de estudios de imagen`. El tratamiento con paracetamol es insuficiente para justificar estudios de imagen.


Formato de respuesta en bullets:

**Evaluación de pertinencia clínica**: [observaciones]

**Resultado**: [✅ Aprobado | ❌ Rechazado]

**Notas para el médico solicitante (Solo en el caso de rechazo)**: - [información]

Fuente: (Ministerio de Salud Pública. Dolor lumbar: Guía Práctica Clínica (GPC). Primera Edición. Quito: Dirección Nacional de Normatización; 2015)

IMPORTANTE_ Siempre debes citar la fuente."""
def consultar_guia_medica(consulta: str) -> str:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"""Responde la siguiente consulta en base a la guia de Dolor Lumbar y cita la fuente de la recomendación:

{consulta}
"""
        )
        print("RESPONSE", response)
        return response.candidates[0].content.parts[0].text
    except Exception as e:
        print(e)
        #return """La Guía de Práctica Clínica sobre Dolor Lumbar establece que no se recomienda la solicitud de estudios de imagen —incluyendo resonancia magnética (RM)— de forma rutinaria en pacientes con lumbalgia aguda inespecífica, especialmente en ausencia de signos de alarma (Recomendación A).

# Sin embargo, se justifica la solicitud de una resonancia magnética en pacientes con dolor lumbar crónico (más de 6 semanas de evolución) cuando han fracasado tratamientos conservadores adecuados, como medicación analgésica y fisioterapia (Recomendación B).

# En particular, la indicación de estudios de imagen puede considerarse pertinente si el paciente presenta síntomas persistentes tras un abordaje no invasivo documentado, como sesiones de kinesiología por al menos 4 a 6 semanas, y persiste con mal control del dolor a pesar del uso de analgésicos escalonados (paracetamol, codeína u otros).

# La guía también señala que ante pacientes con dolor lumbar sin mejoría tras un tratamiento conservador completo, debe realizarse una reevaluación clínica que incluya factores de evolución temporal, respuesta a tratamientos previos y evaluación del uso racional de estudios complementarios (ü/R).

# Por el contrario, la indicación de resonancia magnética en casos de dolor lumbar crónico sin detalles sobre evolución clínica ni tratamientos realizados previamente no cumple con los criterios de pertinencia establecidos por la guía (Recomendación D).

# """
    # except Exception as e:
    #     return f"⚠️ Error en la consulta a Gemini: {e}"

#guardar_evaluacion_tool = FunctionTool(func=guardar_evaluacion)


# Now you can access them
# api_key = os.getenv("GOOGLE_API_KEY")
# vertexai = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")

# os.environ['GOOGLE_API_KEY'] = api_key
# os.environ['GOOGLE_GENAI_USE_VERTEXAI'] = vertexai

MODEL_NAME = "gemini-2.5-flash"

root_agent = LlmAgent(
    model=MODEL_NAME,
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
    ),
    name="Agente_especialista",
    instruction=instruction,
    description="Agente especialista en dolor lumbar",
    tools=[consultar_guia_medica]
)
# import vertexai

# PROJECT_ID = "uma-datascience-dev"
# LOCATION = "us-central1"
# STAGING_BUCKET = "gs://uma-datascience-dev-ia"

# vertexai.init(
#     project=PROJECT_ID,
#     location=LOCATION,
#     staging_bucket=STAGING_BUCKET,
# )

# from vertexai.preview import reasoning_engines

# app = reasoning_engines.AdkApp(
#     agent=root_agent,
#     enable_tracing=False,
# )

# from vertexai import agent_engines

# remote_app = agent_engines.create(
#     agent_engine=root_agent,
#     requirements=[
#         "google-cloud-aiplatform[adk,agent_engines]"   
#     ]
# )
# print("RESOURCE")
# print(remote_app.resource_name)
# )
# from vertexai import agent_engines


# adk_app = agent_engines.get('4348058314458791936')

# #agent_engine = agent_engines.get('projects/145741847476/locations/us-central1/reasoningEngines/2789812843388600320')

# # RESOURCE_ID=''
# # from vertexai import agent_engines

# # adk_app = agent_engines.get(RESOURCE_ID)

# remote_session = adk_app.create_session(user_id="USER_ID3")
# print(remote_session)


# for event in adk_app.stream_query(
#     user_id="USER_ID3",
#     session_id=remote_session["id"],#  # Optional
#     message="hola",
# ):
#   print(event)




#print(remote_app.resource_name)
# # Agent Interaction
# APP_NAME = "predoc_app"
# USER_ID = "user_1"
# SESSION_ID = "session_001"

# # Session and Runner
# session_service = InMemorySessionService()
# session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
# runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


# def call_agent(query):
#   content = types.Content(role='user', parts=[types.Part(text=query)])
#   events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

#   for event in events:
#       if event.is_final_response():
#           final_response = event.content.parts[0].text
#           print("Agent Response: ", final_response)

# call_agent("hola")