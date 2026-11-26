"""Constrúyelo tú (M08-01): tu propio inventario de riesgos.

Lo construyes paso a paso: en cada PASO del lab te dan un bloque de código.
Pégalo debajo del comentario de ese paso, guarda y ejecuta desde infra/:

    docker compose --profile lab run --rm --no-deps --entrypoint python lab -W ignore /construye/m08_01_mi_inventario.py

Este programa SOLO LEE: no escribe en el autómata ni publica órdenes.
"""
import asyncio
import socket

import paho.mqtt.client as mqtt
from asyncua import Client
from pymodbus.client import ModbusTcpClient

# --- PASO 1: los servicios de la línea (ya está hecho) -----------------------
SERVICIOS = {"broker MQTT": ("mosquitto", 1883), "autómata Modbus": ("modbus", 1502), "servidor OPC-UA": ("opcua", 4840),
             "modelo de lenguaje": ("llm", 8088), "API de inferencia": ("api", 8000), "Prometheus": ("prometheus", 9090),
             "panel": ("panel", 8501)}
hallazgos = []                                       # (servicio, qué se ha visto, riesgo, medida)
print(f"servicios a revisar: {len(SERVICIOS)}")

# --- PASO 2: ¿quién contesta? --------------------------------------------------
# (pega aquí el bloque del paso 2)
def contesta(host, puerto):
    try:
        socket.create_connection((host, puerto), timeout=1).close()
        return True
    except OSError:
        return False

for nombre, (host, puerto) in SERVICIOS.items():
    print(f"{nombre:20s} {host}:{puerto}  {'CONTESTA' if contesta(host, puerto) else 'no contesta'}")


# --- PASO 3: ¿el broker acepta a cualquiera? -----------------------------------
# (pega aquí el bloque del paso 3)
cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
codigo = cliente.connect("mosquitto", 1883)          # sin usuario ni contraseña
cliente.loop_start()
aceptado = cliente.publish("pruebas/inventario", "solo una prueba").wait_for_publish(timeout=5) is None
cliente.loop_stop()
cliente.disconnect()
anonimo = codigo == 0
print(f"broker sin credenciales: {'ACEPTA' if anonimo else 'rechaza'} la conexión y la publicación")
if anonimo:
    hallazgos.append(("broker MQTT", "acepta a cualquiera", "dictámenes y consignas falsos", "usuarios y permisos por tema"))



# --- PASO 4: ¿el autómata se deja leer sin credenciales? -----------------------
# (pega aquí el bloque del paso 4)
plc = ModbusTcpClient("modbus", port=1502)
plc.connect()
paro = plc.read_holding_registers(10, 1, slave=1)
plc.close()
if not paro.isError():
    print(f"registro de paro leído sin credenciales: {paro.registers[0]}")
    hallazgos.append(("autómata Modbus", "se lee sin credenciales; Modbus tampoco protege la escritura",
                      "alguien podría escribir el paro", "red de control separada y cortafuegos"))


# --- PASO 5: ¿las variables opc-ua se pueden escribir? -------------------------
# (pega aquí el bloque del paso 5)
async def permisos_opcua():
    async with Client(url="opc.tcp://opcua:4840/linea/server") as c:
        estacion = await c.nodes.objects.get_child(["2:Estacion"])
        resultado = {}
        for var in await estacion.get_children():
            nivel = (await var.read_attribute(18)).Value.Value      # atributo 18: nivel de acceso del usuario
            resultado[(await var.read_browse_name()).Name] = bool(nivel & 2)   # el bit 2 es «se puede escribir»
        return resultado

escribibles = [n for n, w in asyncio.run(permisos_opcua()).items() if w]
print(f"variables OPC-UA que cualquiera puede escribir: {escribibles}")
if escribibles:
    hallazgos.append(("servidor OPC-UA", f"{len(escribibles)} variables escribibles sin usuario",
                      "valores falsos en el SCADA", "variables de proceso en solo lectura; usuarios"))


# --- PASO 6: la tabla de riesgos -----------------------------------------------
# (pega aquí el bloque del paso 6)
print(f"\n{'servicio':18s} | {'visto':45s} | {'riesgo':33s} | medida")
for servicio, visto, riesgo, medida in hallazgos:
    print(f"{servicio:18s} | {visto[:45]:45s} | {riesgo:33s} | {medida}")

