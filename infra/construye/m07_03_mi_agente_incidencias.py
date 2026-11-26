"""Constrúyelo tú (M07-03): tu propio agente de incidencias.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m07_03_mi_agente_incidencias.py
"""
import json
import re
import time

import httpx

# --- PASO 1: preguntar a Prometheus (ya está hecho) --------------------------
def promql(consulta):
    r = httpx.get("http://prometheus:9090/api/v1/query", params={"query": consulta}, timeout=10)
    return r.json()["data"]["result"]

alertas = httpx.get("http://prometheus:9090/api/v1/alerts", timeout=10).json()["data"]["alerts"]
activas = [a["labels"]["alertname"] for a in alertas if a["state"] == "firing"]
print("alertas activas:", activas or "ninguna")

# --- PASO 2: las herramientas de lectura ---------------------------------------
# (pega aquí el bloque del paso 2)
def estado_servicios():
    return {r["metric"]["job"]: "vivo" if r["value"][1] == "1" else "caído" for r in promql("up")}

def segundos_sin_guardar():
    r = promql("time() - archivador_ultimo_registro_timestamp_seconds")
    return {"segundos_sin_guardar": round(float(r[0]["value"][1])) if r else "sin dato"}

def perdidas_ultimo_minuto():
    r = promql("sum(increase(estacion_piezas_fabricadas_total[1m])) - sum(increase(archivador_registros_guardados_total[1m]))")
    return {"carcasas_perdidas_ultimo_minuto": round(float(r[0]["value"][1])) if r else "sin dato"}

HERRAMIENTAS = {"estado_servicios": estado_servicios, "segundos_sin_guardar": segundos_sin_guardar,
                "perdidas_ultimo_minuto": perdidas_ultimo_minuto}
for nombre, herramienta in HERRAMIENTAS.items():
    print(f"{nombre}: {herramienta()}")


# --- PASO 3: el plan: qué herramientas para cada alerta ------------------------
# (pega aquí el bloque del paso 3)
PLAN = {
    "ArchivadorCaido": ["estado_servicios"],
    "HistoricoSinDatos": ["estado_servicios", "segundos_sin_guardar", "perdidas_ultimo_minuto"],
    "RegistrosPerdidos": ["segundos_sin_guardar", "perdidas_ultimo_minuto"],
}

def reunir(alerta):
    hechos = {}
    for herramienta in PLAN.get(alerta, ["estado_servicios"]):
        hechos.update(HERRAMIENTAS[herramienta]())
    return hechos

print("datos que reuniría para HistoricoSinDatos:", reunir("HistoricoSinDatos"))


# --- PASO 4: la sección del runbook --------------------------------------------
# (pega aquí el bloque del paso 4)
RUNBOOK = open("/opt/linea/docs/runbook-est01.md", encoding="utf-8").read()     # infra/linea/docs/

def procedimiento(alerta):
    for seccion in RUNBOOK.split("\n## ")[1:]:
        titulo, _, cuerpo = seccion.partition("\n")
        if titulo.strip() == alerta:
            return cuerpo.strip()
    return "No hay entrada en el runbook para esta alerta."

print("runbook de HistoricoSinDatos:", procedimiento("HistoricoSinDatos")[:160], "...")


# --- PASO 5: el diagnóstico y su comprobación ----------------------------------
# (pega aquí el bloque del paso 5)
def diagnosticar(alerta, hechos):
    mensajes = [{"role": "system", "content": "Eres el asistente de mantenimiento. Usa solo los datos y el runbook. No inventes cifras."},
                {"role": "user", "content": f"Alerta: {alerta}\nDatos: {json.dumps(hechos, ensure_ascii=False)}\n"
                                            f"Runbook: {procedimiento(alerta)}\n\nEn dos frases: qué pasa y qué propone el runbook."}]
    r = httpx.post("http://llm:8088/v1/chat/completions", json={"messages": mensajes, "max_tokens": 120}, timeout=60)
    return r.json()["choices"][0]["message"]["content"].strip()

def cifras_inventadas(texto, hechos):
    medidas = set(re.findall(r"\d+", json.dumps(hechos)))
    return sorted(set(re.findall(r"\d+", texto)) - medidas)

for alerta in activas:
    hechos = reunir(alerta)
    diagnostico = diagnosticar(alerta, hechos)
    inventadas = cifras_inventadas(diagnostico, hechos)
    informe = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "alerta": alerta, "hechos": hechos,
               "diagnostico": diagnostico, "cifras_sin_respaldo": inventadas,
               "estado": "REVISAR: cifras sin respaldo" if inventadas else "propuesta pendiente de una persona"}
    with open("/data/mis_incidencias.jsonl", "a") as f:
        f.write(json.dumps(informe, ensure_ascii=False) + "\n")
    print(json.dumps(informe, ensure_ascii=False, indent=1))
if not activas:
    print("sin alertas activas: el agente no hace nada")

