import requests
import os
from typing import Dict, Any, List
from google.adk.tools import ToolContext, FunctionTool

diagnostico_url = os.getenv('DIAGNOSTICO_URL')
medicamento_url = os.getenv('MEDICAMENTO_URL')

def update_user_prescription(key: str, value: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Actualiza el estado de la receta que se va recopilando durante la conversación."""

    print("TOOL STATE (before update):", tool_context.state.to_dict())
    # ADK tool_context.state is already a mutable object, no need for .to_dict() and reassign
    # preferences = tool_context.state.to_dict() # Not needed

    if key == "medicamento":
        # Si ya hay una lista de medicamentos, la actualizamos
        medicamentos = tool_context.state.get("medicamento", [])
        # Ensure it's treated as a list, even if the initial state was wrong or empty
        if not isinstance(medicamentos, list):
             print(f"Warning: 'medicamento' state was not a list ({type(medicamentos).__name__}), converting.")
             medicamentos = [medicamentos] if medicamentos is not None else []

        medicamentos.append(value)
        tool_context.state["medicamento"] = medicamentos
        print(f"Tool: Appended '{value}' to 'medicamento' list.")
    else:
        # Para el resto de los campos, reemplaza normalmente
        tool_context.state[key] = value
        print(f"Tool: Updated state key '{key}' to '{value}'.")

    print("TOOL STATE (after update):", tool_context.state.to_dict())

    return {"status": "success", "updated_key": key, "updated_value": value}


def buscar_diagnostico(query: str) -> Dict[str, Any]:
    """Busca diagnósticos similares a la consulta del usuario y retorna resultados estructurados.

    Realiza una búsqueda de diagnóstico usando una API externa.
    Retorna un diccionario que indica si se encontró una coincidencia exacta o
    una lista de opciones similares encontradas."""
    url = diagnostico_url
    try:
        resp = requests.post(url, json={"text": query, "country": "AR"}, headers={"Content-Type": "application/json"})
        resp.raise_for_status()
        results = resp.json().get('output', [])[:10]

        if not results:
            print(f"Tool: No diagnostics found for query '{query}'.")
            return {"status": "no_results", "exact_match_term": None, "options": None}

        # Check for exact match
        exact_match = None
        options_list = []
        for d in results:
            options_list.append(d['snomed_term']) # Include all results in options
            if d.get('snomed_term', '').lower() == query.lower():
                exact_match = d.get('snomed_term')

        if exact_match:
            print(f"Tool: Exact diagnostic match found: '{exact_match}'.")
            return {"status": "exact_match", "exact_match_term": exact_match, "options": options_list}
        else:
            print(f"Tool: Found {len(options_list)} similar diagnostics for query '{query}'.")
            return {"status": "options_found", "exact_match_term": None, "options": options_list}

    except requests.exceptions.RequestException as e:
        print(f"Tool Error (validar_diagnostico): Network or API error: {e}")
        # Return an error status in the dict
        return {"status": "error", "error_message": f"Error searching diagnostics: {e}"}
    except Exception as e:
        print(f"Tool Error (validar_diagnostico): An unexpected error occurred: {e}")
         # Return an error status in the dict
        return {"status": "error", "error_message": f"An unexpected error occurred: {e}"}


def buscar_medicamento(query: str) -> Dict[str, Any]:
    """Busca información sobre un medicamento utilizando una API externa y retorna resultados estructurados.

    Realiza búsquedas por nombre de producto, droga o dosis numérica.
    Retorna un diccionario que contiene una lista de resultados de medicamentos encontrados para mostrarle al usuario."""
    url = medicamento_url
    if not url:
        print("Tool Error (buscar_medicamento): API_VADEMECUM_URL is not defined.")
        return {"status": "error", "error_message": "Configuration error: API URL not defined."}

    try:
        response = requests.post(
            url,
            json={"text": query, "country": "AR"},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        results = response.json().get('output', [])[:20]

        if not results:
            print(f"Tool: No medication results found for query '{query}'.")
            return {"status": "no_results", "results": None}

        # Structure results as a list of dicts
        structured_results = []
        for item in results:
             # Basic cleaning/structuring, removing internal info like alfabetRegisterNum if not needed by LLM
             # Or keep it if the LLM needs to reference it for some reason
             structured_results.append({
                'Acción farmacológica': item.get('accion_farmacologica'),
                'Nombre del producto': item.get('productName'),
                'Droga': item.get('drugName'),
                'Presentación': item.get('presentationName'),
                'Dosis': item.get('dosis'), # Note: this might be string
                'Laboratorio': item.get('laboratorio'),
                # 'alfabetRegisterNum': item.get('alfabetRegisterNum') # Often remove internal IDs
            })

        print(f"Tool: Found {len(structured_results)} medication results for query '{query}'.")
        return {"status": "results_found", "results": structured_results}

    except requests.exceptions.RequestException as e:
        print(f"Tool Error (buscar_medicamento): Network or API error: {e}")
        return {"status": "error", "error_message": f"Error searching medication: {e}"}
    except ValueError:
        print("Tool Error (buscar_medicamento): Malformed JSON response.")
        return {"status": "error", "error_message": "Error processing API response."}
    except Exception as e:
        print(f"Tool Error (buscar_medicamento): An unexpected error occurred: {e}")
        return {"status": "error", "error_message": f"An unexpected error occurred: {e}"}


def guardar_evaluacion(
    timestamp: str,
    estado: str,  # "ROJO", "AMARILLO" o "VERDE"
    nombre_paciente: str,
    nro_afiliado: str,
    estudio: str,
    url_documentos: list[str],  # URLs a los archivos subidos
    observaciones: str,
) -> Dict[str, Any]:
    """
    Guarda una evaluación de autorización de kinesiología en BigQuery.

    Campos:
    - timestamp: fecha y hora de la evaluación
    - estado: ROJO, AMARILLO o VERDE
    - nombre_paciente: extraído del documento
    - nro_afiliado: número del carnet o credencial
    - estudio: siempre "Tratamiento de kinesiología"
    - documentos: lista de nombres de los archivos recibidos
    - observaciones: justificación detallada de la evaluación
    """
    return {"status":"success"}
 # Implementación específica según cliente BigQuery


update_user_prescription_tool = FunctionTool(func=update_user_prescription)
buscar_diagnostico_tool = FunctionTool(func=buscar_diagnostico)
guardar_evaluacion_tool = FunctionTool(func=guardar_evaluacion)
buscar_medicamento_tool = FunctionTool(func=buscar_medicamento)