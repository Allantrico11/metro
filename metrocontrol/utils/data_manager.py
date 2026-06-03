"""
data_manager.py — Gestor de datos compartido para MetroControl
================================================================
Este archivo es el puente entre todos los módulos de la aplicación.
Define la estructura estándar de un equipo y las funciones para
leer y guardar datos.

⚠️  COORDINACIÓN CON OTROS GRUPOS:
    Este archivo debe ser el MISMO para todos los grupos.
    Si otro grupo modifica la estructura de `equipo_vacio()`,
    debe notificar a todos para actualizar sus módulos.
"""

import json
import os
from datetime import datetime
from typing import Optional

# ── Ruta del archivo de datos compartido ──────────────────────────────────────
# ⚠️  COORDINACIÓN: Esta ruta debe ser igual en todos los módulos.
#     Si la app principal cambia la ubicación del archivo, actualizar aquí.
RUTA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "equipos.json")


def equipo_vacio() -> dict:
    """
    Retorna la estructura base de un equipo con todos sus campos en blanco.

    ⚠️  COORDINACIÓN CON OTROS GRUPOS:
        Cualquier campo nuevo que un grupo necesite debe agregarse aquí
        y comunicarse al resto. NO renombrar campos existentes sin avisar.

    Campos que usa el módulo de Intervalos de Calibración (IC):
        - id, nombre, unidad, tolerancia_emp
        - historial_calibraciones (lista de calibraciones pasadas)
        - intervalo_fabricante_anios
        - resultado_ic (donde IC guarda su resultado para otros módulos)

    Campos que probablemente usen otros grupos:
        - tipo, marca, modelo, serie       → Ficha de equipos
        - ubicacion, area, responsable     → Ficha de equipos
        - clase_metrologica                → Ficha de equipos
        - proveedor_calibracion            → Ficha de equipos
        - condiciones_ambientales          → Ficha de equipos / Condiciones de uso
        - historial_mantenimientos         → Control de mantenimiento
        - estado                           → Control de mantenimiento / Dashboard
    """
    return {
        # ── Identificación ────────────────────────────────────────────────────
        # ⚠️  "id" es el campo clave. Todos los módulos lo usan para
        #     identificar al equipo. NO cambiar el nombre de este campo.
        "id": "",
        "nombre": "",
        "tipo": "",
        "marca": "",
        "modelo": "",
        "serie": "",

        # ── Clasificación metrológica ─────────────────────────────────────────
        # ⚠️  COORDINACIÓN: El grupo de Ficha de Equipos define estos valores.
        "clase_metrologica": "",
        "unidad": "",              # Ej: "mm", "kg", "°C", "Pa"

        # ── Parámetros técnicos (críticos para IC) ────────────────────────────
        # ⚠️  COORDINACIÓN: Estos campos los llena el grupo de Ficha de Equipos.
        #     IC los lee directamente. Si no están llenos, IC pide al usuario
        #     que los ingrese manualmente.
        "tolerancia_emp": None,             # Error Máximo Permitido (float)
        "intervalo_fabricante_anios": None, # Intervalo recomendado por fabricante

        # ── Ubicación y responsables ──────────────────────────────────────────
        "ubicacion": "",
        "area": "",
        "responsable": "",
        "proveedor_calibracion": "",

        # ── Condiciones de uso ────────────────────────────────────────────────
        # ⚠️  COORDINACIÓN: IC las muestra como referencia, no las modifica.
        "condiciones_ambientales": {
            "temperatura_min": None,
            "temperatura_max": None,
            "humedad_min": None,
            "humedad_max": None
        },
        "instructivo_uso": "",

        # ── Estado del equipo ─────────────────────────────────────────────────
        # ⚠️  COORDINACIÓN: Valores posibles acordados entre grupos:
        #     "Operativo", "En mantenimiento", "Fuera de servicio", "En calibración"
        "estado": "Operativo",

        # ── Historial de calibraciones (IC lee y escribe aquí) ────────────────
        # Cada elemento: {
        #   "fecha": "YYYY-MM-DD",
        #   "fue_ajustado": False,
        #   "errores_por_punto": [
        #       {"valor_nominal": 10.0, "error": 0.01, "incertidumbre": 0.005}
        #   ],
        #   "metodo_ic_usado": "Escalera (Error medio)",
        #   "intervalo_calculado_anios": 1.5,
        #   "fecha_proxima_calibracion": "YYYY-MM-DD",
        #   "calculado_por": "IC"
        # }
        "historial_calibraciones": [],

        # ── Historial de mantenimientos ───────────────────────────────────────
        # ⚠️  COORDINACIÓN: Lo gestiona el grupo de Mantenimiento.
        #     IC no lo modifica.
        "historial_mantenimientos": [],

        # ── Resultado del módulo IC (para que otros módulos lo lean) ──────────
        # ⚠️  COORDINACIÓN: IC escribe aquí. El Dashboard y Mantenimiento
        #     pueden leer estos campos para mostrar alertas de calibración.
        "resultado_ic": {
            "ultimo_intervalo_calculado_anios": None,
            "fecha_proxima_calibracion": None,
            "metodo_usado": None,
            "fecha_calculo": None,
            "recomendacion": None
        },

        # ── Metadatos ─────────────────────────────────────────────────────────
        "fecha_registro": datetime.now().strftime("%Y-%m-%d"),
        "fecha_ultima_modificacion": datetime.now().strftime("%Y-%m-%d")
    }


def cargar_equipos() -> list:
    """Carga la lista de equipos desde el archivo JSON compartido."""
    if not os.path.exists(RUTA_DATOS):
        return []
    try:
        with open(RUTA_DATOS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def guardar_equipos(equipos: list) -> bool:
    """
    Guarda la lista completa de equipos en el archivo JSON compartido.
    ⚠️  COORDINACIÓN: IC solo actualiza resultado_ic e historial_calibraciones.
    """
    try:
        os.makedirs(os.path.dirname(RUTA_DATOS), exist_ok=True)
        with open(RUTA_DATOS, "w", encoding="utf-8") as f:
            json.dump(equipos, f, ensure_ascii=False, indent=2)
        return True
    except IOError:
        return False


def buscar_equipo_por_id(equipo_id: str) -> Optional[dict]:
    """Busca y retorna un equipo por su ID. Retorna None si no existe."""
    equipos = cargar_equipos()
    return next((e for e in equipos if e.get("id") == equipo_id), None)


def actualizar_resultado_ic(equipo_id: str, resultado: dict) -> bool:
    """
    Actualiza resultado_ic e historial_calibraciones de un equipo.
    Es la única función que el módulo IC usa para escribir datos.
    """
    equipos = cargar_equipos()
    for equipo in equipos:
        if equipo.get("id") == equipo_id:
            equipo["resultado_ic"] = resultado.get("resumen", {})
            equipo["fecha_ultima_modificacion"] = datetime.now().strftime("%Y-%m-%d")
            entrada = resultado.get("entrada_historial")
            if entrada:
                equipo["historial_calibraciones"].append(entrada)
            return guardar_equipos(equipos)
    return False


def equipos_demo() -> list:
    """
    Genera equipos de demostración para pruebas del módulo IC.
    ⚠️  COORDINACIÓN: Solo para desarrollo. Cuando el grupo de Ficha de Equipos
        esté listo, esta función se desactiva y se usa el JSON real.
    """
    base = equipo_vacio()
    demo = [
        {
            **base,
            "id": "EQ-001",
            "nombre": "Vernier digital #1",
            "tipo": "Vernier",
            "marca": "Mitutoyo",
            "modelo": "500-196-30",
            "unidad": "mm",
            "tolerancia_emp": 0.02,
            "intervalo_fabricante_anios": 1.0,
            "clase_metrologica": "Clase II",
            "area": "Producción",
            "responsable": "Juan Pérez",
            "estado": "Operativo",
            "historial_calibraciones": [
                {
                    "fecha": "2023-01-15",
                    "fue_ajustado": False,
                    "errores_por_punto": [
                        {"valor_nominal": 10.0, "error": 0.005, "incertidumbre": 0.002},
                        {"valor_nominal": 50.0, "error": 0.008, "incertidumbre": 0.002}
                    ],
                    "metodo_ic_usado": None,
                    "intervalo_calculado_anios": None,
                    "fecha_proxima_calibracion": None,
                    "calculado_por": "Externo"
                },
                {
                    "fecha": "2024-02-10",
                    "fue_ajustado": False,
                    "errores_por_punto": [
                        {"valor_nominal": 10.0, "error": 0.009, "incertidumbre": 0.002},
                        {"valor_nominal": 50.0, "error": 0.012, "incertidumbre": 0.002}
                    ],
                    "metodo_ic_usado": None,
                    "intervalo_calculado_anios": None,
                    "fecha_proxima_calibracion": None,
                    "calculado_por": "Externo"
                }
            ]
        },
        {
            **base,
            "id": "EQ-002",
            "nombre": "Balanza analítica #3",
            "tipo": "Balanza",
            "marca": "Ohaus",
            "modelo": "Pioneer PA214",
            "unidad": "g",
            "tolerancia_emp": 0.001,
            "intervalo_fabricante_anios": 0.5,
            "clase_metrologica": "Clase I",
            "area": "Laboratorio",
            "responsable": "María González",
            "estado": "Operativo",
            "historial_calibraciones": []
        },
        {
            **base,
            "id": "EQ-003",
            "nombre": "Termómetro de contacto #2",
            "tipo": "Termómetro",
            "marca": "Fluke",
            "modelo": "51-II",
            "unidad": "°C",
            "tolerancia_emp": 0.5,
            "intervalo_fabricante_anios": 2.0,
            "clase_metrologica": "Clase III",
            "area": "Control de calidad",
            "responsable": "Carlos Mora",
            "estado": "Operativo",
            "historial_calibraciones": []
        }
    ]
    return demo
