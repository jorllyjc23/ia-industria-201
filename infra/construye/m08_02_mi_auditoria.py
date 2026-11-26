"""Constrúyelo tú (M08-02): tu propia auditoría del rastro de dictámenes.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m08_02_mi_auditoria.py
"""
import hashlib
import json
from collections import Counter

# --- PASO 1: leer el rastro (ya está hecho) ----------------------------------
lineas = open("/data/predicciones.jsonl", encoding="utf-8").read().splitlines()   # infra/data/predicciones.jsonl
rastro = [json.loads(l) for l in lineas]
print(f"dictámenes en el rastro: {len(rastro)}  primero: {rastro[0]['ts']}  último: {rastro[-1]['ts']}")

# --- PASO 2: resumir por modelo ------------------------------------------------
# (pega aquí el bloque del paso 2)
por_modelo = Counter((d.get("version"), d.get("huella_modelo")) for d in rastro)
print("versión        huella        dictámenes  revisar")
for (version, huella), n in por_modelo.items():
    revisar = sum(1 for d in rastro if d.get("version") == version and d.get("huella_modelo") == huella and d["dictamen"] == "revisar")
    print(f"{str(version):14s} {str(huella):12s}  {n:10d}  {revisar:7d}")


# --- PASO 3: comprobar contra el modelo instalado ------------------------------
# (pega aquí el bloque del paso 3)
huella_instalada = hashlib.sha256(open("/data/modelo_defecto.joblib", "rb").read()).hexdigest()[:12]
otros = [d for d in rastro if d.get("huella_modelo") != huella_instalada]
print(f"huella del modelo instalado: {huella_instalada}")
print(f"dictámenes tomados con otro modelo (o sin huella): {len(otros)} de {len(rastro)}")


# --- PASO 4: buscar líneas incompletas -----------------------------------------
# (pega aquí el bloque del paso 4)
OBLIGATORIOS = ["pieza_id", "ts", "version", "huella_modelo", "entrada", "dictamen"]
incompletas = [(i, [c for c in OBLIGATORIOS if c not in d]) for i, d in enumerate(rastro) if any(c not in d for c in OBLIGATORIOS)]
print(f"líneas incompletas: {len(incompletas)}", incompletas[:3])


# --- PASO 5: sellar el rastro --------------------------------------------------
# (pega aquí el bloque del paso 5)
def sellar(lineas):
    sello = ""
    for linea in lineas:
        sello = hashlib.sha256((sello + linea).encode()).hexdigest()   # cada sello depende del anterior
    return sello[:16]

sello = sellar(lineas)
open("/data/sello_rastro.txt", "w").write(f"{len(lineas)} {sello}\n")
print(f"sello de las {len(lineas)} líneas: {sello} (guardado en sello_rastro.txt)")

# Una copia manipulada: un «revisar» pasa a «seguir» (o al revés) en la línea del medio
copia = list(lineas)
i = len(copia) // 2
d = json.loads(copia[i])
d["dictamen"] = "seguir" if d["dictamen"] == "revisar" else "revisar"
copia[i] = json.dumps(d, ensure_ascii=False)
print(f"línea {i} cambiada a «{d['dictamen']}»: sello original={sello}  sello de la copia={sellar(copia)}")

# Reto 1: ¿qué hace el sistema con sus dictámenes?
print("valores de dictamen en el rastro:", dict(Counter(d["dictamen"] for d in rastro)))
campos = set().union(*(d.keys() for d in rastro))
print("campos del rastro:", sorted(campos))


