"""
intervalos_cal.py — Módulo de Intervalos de Calibración
=========================================================
Implementa los 3 métodos del ILAC-G24 / OIML D10:2007:
  1. Escalera (Error medio)
  2. Escalera (Error con incertidumbre)
  3. Cartas de control (Gráfica de deriva)

Diseñado para funcionar:
  - De forma independiente (el usuario ingresa todo manualmente)
  - Integrado con la app principal (recibe el equipo desde session_state)

Paleta de colores MetroControl:
  Verde principal : #23c057   Verde oscuro  : #15924a
  Azul marino     : #063d7d   Teal          : #238d93
  Verde profundo  : #0a453c   Azul medio    : #1469aa
  Verde menta     : #15795a   Aqua          : #2dc197
  Azul noche      : #0b2c40

Autor: Grupo [NOMBRE DEL GRUPO]
Fecha: 2025
"""

import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional
import sys
import os

# ── Importar el gestor de datos compartido ────────────────────────────────────
# ⚠️  COORDINACIÓN: Si la estructura de carpetas cambia al integrar con otros
#     grupos, actualizar esta ruta.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
from utils.data_manager import (
    cargar_equipos, buscar_equipo_por_id,
    actualizar_resultado_ic, equipos_demo
)

# ── Paleta de colores MetroControl ────────────────────────────────────────────
COLOR = {
    "verde":       "#23c057",
    "verde_osc":   "#15924a",
    "azul_marino": "#063d7d",
    "teal":        "#238d93",
    "verde_prof":  "#0a453c",
    "azul_med":    "#1469aa",
    "verde_menta": "#15795a",
    "aqua":        "#2dc197",
    "azul_noche":  "#0b2c40",
}

# ── CSS personalizado ─────────────────────────────────────────────────────────
CSS = """
<style>
  [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #0b2c40 0%, #0a453c 100%);
  }
  [data-testid="stSidebar"] * { color: #e8f5e9 !important; }

  .ic-header {
      background: linear-gradient(135deg, #063d7d 0%, #238d93 100%);
      border-radius: 12px;
      padding: 1.4rem 2rem;
      margin-bottom: 1.5rem;
      color: white;
  }
  .ic-header h1 { margin: 0; font-size: 1.6rem; color: white; }
  .ic-header p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 0.9rem; }

  .equipo-card {
      background: #0a453c33;
      border-left: 4px solid #23c057;
      border-radius: 8px;
      padding: 0.9rem 1.2rem;
      margin-bottom: 1rem;
  }

  .resultado-box {
      border-radius: 10px;
      padding: 1rem 1.4rem;
      margin-top: 0.8rem;
  }
  .resultado-ok   { background: #23c05722; border-left: 4px solid #23c057; }
  .resultado-warn { background: #ff980022; border-left: 4px solid #ff9800; }
  .resultado-bad  { background: #f4433622; border-left: 4px solid #f44336; }

  .stDataFrame { border-radius: 8px; overflow: hidden; }

  .stButton > button {
      background: #15795a;
      color: white;
      border: none;
      border-radius: 8px;
      font-weight: 600;
  }
  .stButton > button:hover { background: #23c057; }
</style>
"""


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE CÁLCULO
# ══════════════════════════════════════════════════════════════════════════════

def calcular_intervalo_anios(fecha_ant: date, fecha_act: date) -> float:
    """Calcula el intervalo en años entre dos fechas."""
    delta = fecha_act - fecha_ant
    return delta.days / 365.25


def fecha_desde_intervalo(fecha_base: date, intervalo_anios: float) -> date:
    """Calcula la fecha futura sumando un intervalo en años."""
    dias = int(intervalo_anios * 365.25)
    return fecha_base + timedelta(days=dias)


def escalera_error_medio(
    error_medio: float,
    emp: float,
    intervalo_anterior_anios: float,
    fue_ajustado: bool
) -> dict:
    """
    Método de Escalera usando el error medio.
    Referencia: ILAC-G24 sección 4.4.1

    Retorna dict con: recomendacion, intervalo_nuevo, tipo (ok/warn/bad)
    """
    if fue_ajustado:
        return {
            "recomendacion": "El equipo fue ajustado recientemente. Use el intervalo recomendado por el fabricante.",
            "intervalo_nuevo": None,
            "tipo": "warn"
        }

    limite_control = 0.80 * emp   # 80% del EMP

    if abs(error_medio) > emp:
        return {
            "recomendacion": "El error medio supera el EMP. Se recomienda ajuste mecánico y calibración inmediata.",
            "intervalo_nuevo": None,
            "tipo": "bad"
        }
    elif abs(error_medio) <= limite_control:
        nuevo = intervalo_anterior_anios * 1.50   # ampliar 50%
        return {
            "recomendacion": f"El error medio ({error_medio:.5f}) está dentro del límite de control ({limite_control:.5f}). "
                             f"Se amplía el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "ok"
        }
    else:
        nuevo = intervalo_anterior_anios * 0.50   # reducir 50%
        return {
            "recomendacion": f"El error medio ({error_medio:.5f}) supera el límite de control ({limite_control:.5f}). "
                             f"Se reduce el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "warn"
        }


def escalera_error_incertidumbre(
    error: float,
    incertidumbre: float,
    emp: float,
    intervalo_anterior_anios: float,
    fue_ajustado: bool
) -> dict:
    """
    Método de Escalera usando el error con incertidumbre expandida (error ± U).
    Referencia: ILAC-G24 sección 4.4.2

    La comparación se hace con |error| + U vs límites de control.
    """
    if fue_ajustado:
        return {
            "recomendacion": "El equipo fue ajustado recientemente. Use el intervalo recomendado por el fabricante.",
            "intervalo_nuevo": None,
            "tipo": "warn"
        }

    limite_control = 0.80 * emp
    error_con_u = abs(error) + incertidumbre   # peor caso

    if error_con_u > emp:
        return {
            "recomendacion": f"El error ± U ({error_con_u:.5f}) supera el EMP ({emp:.5f}). "
                             "Se recomienda ajuste mecánico y calibración inmediata.",
            "intervalo_nuevo": None,
            "tipo": "bad"
        }
    elif error_con_u <= limite_control:
        nuevo = intervalo_anterior_anios * 1.50
        return {
            "recomendacion": f"El error ± U ({error_con_u:.5f}) está dentro del límite de control ({limite_control:.5f}). "
                             "Se amplía el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "ok"
        }
    else:
        nuevo = intervalo_anterior_anios * 0.50
        return {
            "recomendacion": f"El error ± U ({error_con_u:.5f}) supera el límite de control ({limite_control:.5f}). "
                             "Se reduce el intervalo en un 50%.",
            "intervalo_nuevo": nuevo,
            "tipo": "warn"
        }


def cartas_control(
    fechas: list,          # lista de date
    errores: list,         # lista de float (uno por fecha, para un punto dado)
    emp: float,
    fue_ajustado: bool,
    fecha_ajuste: Optional[date] = None
) -> dict:
    """
    Método de Cartas de Control: analiza la deriva del error a lo largo del tiempo.
    Referencia: ILAC-G24 sección 4.4.3

    Calcula la tasa de deriva (mm/año) y estima cuándo el error llegará al
    80% del EMP, definiendo así el intervalo de calibración.

    Retorna dict con: deriva_anual, intervalo_nuevo, recomendacion, tipo,
                      datos_grafica (para graficar externamente)
    """
    if len(fechas) < 2:
        return {
            "recomendacion": "Se necesitan al menos 2 fechas de calibración.",
            "intervalo_nuevo": None,
            "tipo": "warn",
            "deriva_anual": None,
            "datos_grafica": None
        }

    # Convertir fechas a años desde la primera fecha
    fecha_ref = fechas[0]
    tiempos_anios = [(f - fecha_ref).days / 365.25 for f in fechas]

    # Si hubo ajuste, el error en esa fecha es 0
    if fue_ajustado and fecha_ajuste:
        # Filtrar solo los datos posteriores al ajuste
        datos_filtrados = [
            (t, e) for t, e, f in zip(tiempos_anios, errores, fechas)
            if f >= fecha_ajuste
        ]
        if len(datos_filtrados) < 2:
            return {
                "recomendacion": "Con ajuste reciente, se necesitan al menos 2 calibraciones post-ajuste.",
                "intervalo_nuevo": None,
                "tipo": "warn",
                "deriva_anual": None,
                "datos_grafica": None
            }
        tiempos_anios = [d[0] for d in datos_filtrados]
        errores_calc = [d[1] for d in datos_filtrados]
        # El error en el ajuste es 0
        tiempos_anios = [0.0] + tiempos_anios
        errores_calc  = [0.0] + errores_calc
    else:
        errores_calc = errores

    # Regresión lineal para calcular deriva
    t = np.array(tiempos_anios)
    e = np.array(errores_calc)

    if len(t) < 2:
        return {
            "recomendacion": "Datos insuficientes para calcular deriva.",
            "intervalo_nuevo": None,
            "tipo": "warn",
            "deriva_anual": None,
            "datos_grafica": None
        }

    pendiente, intercepto = np.polyfit(t, e, 1)
    deriva_anual = abs(pendiente)   # mm/año (o unidad del instrumento / año)

    limite_control = 0.80 * emp

    if deriva_anual == 0:
        return {
            "recomendacion": "No se detectó deriva entre las calibraciones. "
                             "Use el intervalo recomendado por el fabricante.",
            "intervalo_nuevo": None,
            "tipo": "warn",
            "deriva_anual": 0,
            "datos_grafica": {
                "tiempos": list(t), "errores": list(e),
                "pendiente": pendiente, "intercepto": intercepto,
                "limite_control": limite_control, "emp": emp
            }
        }

    # Tiempo para llegar al 80% del EMP desde el error actual
    error_actual = abs(intercepto + pendiente * t[-1])
    margen = limite_control - error_actual

    if margen <= 0:
        return {
            "recomendacion": f"La deriva ({deriva_anual:.5f} {''}/año) ya supera el 80% del EMP. "
                             "Se recomienda calibración inmediata.",
            "intervalo_nuevo": None,
            "tipo": "bad",
            "deriva_anual": deriva_anual,
            "datos_grafica": {
                "tiempos": list(t), "errores": list(e),
                "pendiente": pendiente, "intercepto": intercepto,
                "limite_control": limite_control, "emp": emp
            }
        }

    intervalo = margen / deriva_anual
    return {
        "recomendacion": f"Deriva estimada: {deriva_anual:.5f}/año. "
                         f"El instrumento alcanzará el 80% del EMP en {intervalo:.2f} años.",
        "intervalo_nuevo": intervalo,
        "tipo": "ok",
        "deriva_anual": deriva_anual,
        "datos_grafica": {
            "tiempos": list(t), "errores": list(e),
            "pendiente": pendiente, "intercepto": intercepto,
            "limite_control": limite_control, "emp": emp
        }
    }


# ══════════════════════════════════════════════════════════════════════════════
# FUNCIONES DE GRÁFICAS
# ══════════════════════════════════════════════════════════════════════════════

def grafica_escalera(error_val: float, emp: float, unidad: str, con_incertidumbre: bool = False, incertidumbre: float = 0.0):
    """Genera la gráfica de evaluación para los métodos de Escalera."""
    fig, ax = plt.subplots(figsize=(7, 4))
    fig.patch.set_facecolor("#0b2c40")
    ax.set_facecolor("#0b2c40")

    limite = 0.80 * emp
    x_centro = 0

    # Zonas de color
    ax.axhspan(-emp,     -limite, alpha=0.15, color="#f44336")
    ax.axhspan(-limite,   limite, alpha=0.15, color="#23c057")
    ax.axhspan( limite,   emp,   alpha=0.15, color="#f44336")

    # Líneas de referencia
    ax.axhline(y= emp,    color="#f44336", linestyle="--", linewidth=1.2, label=f"+EMP ({emp:.4f})")
    ax.axhline(y=-emp,    color="#f44336", linestyle="--", linewidth=1.2, label=f"−EMP (−{emp:.4f})")
    ax.axhline(y= limite, color="#ff9800", linestyle=":",  linewidth=1.2, label=f"+80% EMP ({limite:.4f})")
    ax.axhline(y=-limite, color="#ff9800", linestyle=":",  linewidth=1.2, label=f"−80% EMP (−{limite:.4f})")
    ax.axhline(y=0,       color="white",   linestyle="-",  linewidth=0.5, alpha=0.3)

    # Punto del error
    color_punto = COLOR["verde"] if abs(error_val) <= limite else ("#ff9800" if abs(error_val) <= emp else "#f44336")
    if con_incertidumbre and incertidumbre > 0:
        ax.errorbar(x_centro, error_val, yerr=incertidumbre,
                    fmt="o", color=color_punto, markersize=10,
                    capsize=6, capthick=2, elinewidth=2, label=f"Error ± U")
    else:
        ax.scatter(x_centro, error_val, color=color_punto, s=120, zorder=5, label=f"Error medio")

    # Estética
    ax.set_xlim(-1, 1)
    ax.set_xticks([])
    ax.set_ylabel(f"Error ({unidad})", color="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#2dc19733")
    legend = ax.legend(loc="upper right", fontsize=7.5, framealpha=0.2,
                       labelcolor="white", facecolor="#0a453c")
    ax.set_title("Evaluación — Método de Escalera", color="white", fontsize=11, pad=10)
    fig.tight_layout()
    return fig


def grafica_cartas_control(datos: dict, unidad: str):
    """Genera la gráfica de cartas de control con la línea de deriva."""
    if not datos:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor("#0b2c40")
    ax.set_facecolor("#0b2c40")

    t = np.array(datos["tiempos"])
    e = np.array(datos["errores"])
    m = datos["pendiente"]
    b = datos["intercepto"]
    lc = datos["limite_control"]
    emp = datos["emp"]

    t_ext = np.linspace(0, max(t) * 1.5, 200)

    # Zonas
    ax.axhspan(-emp, -lc,  alpha=0.12, color="#f44336")
    ax.axhspan(-lc,   lc,  alpha=0.12, color="#23c057")
    ax.axhspan( lc,   emp, alpha=0.12, color="#f44336")

    # Líneas de referencia
    ax.axhline(y= emp, color="#f44336", linestyle="--", lw=1.2, label=f"+EMP ({emp:.4f})")
    ax.axhline(y=-emp, color="#f44336", linestyle="--", lw=1.2, label=f"−EMP")
    ax.axhline(y= lc,  color="#ff9800", linestyle=":",  lw=1.2, label=f"+80% EMP ({lc:.4f})")
    ax.axhline(y=-lc,  color="#ff9800", linestyle=":",  lw=1.2, label=f"−80% EMP")

    # Línea de deriva (regresión)
    ax.plot(t_ext, m * t_ext + b, color=COLOR["aqua"], lw=1.8,
            linestyle="-.", label="Tendencia (deriva)")

    # Puntos reales
    ax.scatter(t, e, color=COLOR["verde"], s=80, zorder=5, label="Calibraciones")
    ax.plot(t, e, color=COLOR["verde"], lw=1, alpha=0.5)

    ax.set_xlabel("Tiempo desde primera calibración (años)", color="white")
    ax.set_ylabel(f"Error ({unidad})", color="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#2dc19733")
    ax.legend(loc="upper left", fontsize=7.5, framealpha=0.2,
              labelcolor="white", facecolor="#0a453c")
    ax.set_title("Cartas de Control — Deriva del error", color="white", fontsize=11, pad=10)
    fig.tight_layout()
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# INTERFAZ PRINCIPAL DEL MÓDULO
# ══════════════════════════════════════════════════════════════════════════════

def mostrar_intervalos():
    """
    Función principal del módulo. La app principal la llama así:
        from modulos.intervalos_cal import mostrar_intervalos
        mostrar_intervalos()

    ⚠️  NO llamar st.set_page_config() aquí. Solo en app.py.
    """
    st.markdown(CSS, unsafe_allow_html=True)

    # ── Encabezado ────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="ic-header">
        <h1>📐 Intervalos de Calibración</h1>
        <p>Determinación y ajuste del intervalo de calibración según ILAC-G24 / OIML D10:2007</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Sección 1: Selección del equipo ───────────────────────────────────────
    st.subheader("1 · Equipo a evaluar")

    # ⚠️  COORDINACIÓN: Cuando la app principal esté lista, el equipo
    #     seleccionado llegará por st.session_state["equipo_seleccionado"].
    #     Por ahora se carga de los datos demo o se ingresa manualmente.

    modo = st.radio(
        "Modo de ingreso:",
        ["Seleccionar equipo registrado", "Ingresar datos manualmente"],
        horizontal=True,
        help="Cuando los otros módulos estén listos, 'Seleccionar equipo' "
             "cargará el equipo que el usuario ya eligió en la ficha de equipos."
    )

    equipo = None   # objeto equipo que se usará en los cálculos

    if modo == "Seleccionar equipo registrado":
        # ⚠️  COORDINACIÓN: Esta sección se simplifica cuando exista el módulo
        #     de Ficha de Equipos. En ese caso, reemplazar el bloque siguiente
        #     por:
        #         equipo_id = st.session_state.get("equipo_seleccionado")
        #         equipo = buscar_equipo_por_id(equipo_id) if equipo_id else None
        #
        #     Por ahora cargamos del JSON (o datos demo si el JSON no existe).

        equipos_disponibles = cargar_equipos()
        if not equipos_disponibles:
            st.info("No hay equipos registrados aún. Usando equipos de demostración.")
            equipos_disponibles = equipos_demo()

        opciones = {f"[{e['id']}] {e['nombre']}": e for e in equipos_disponibles}
        seleccion = st.selectbox("Seleccione el equipo:", list(opciones.keys()))
        equipo = opciones[seleccion]

        # Mostrar resumen del equipo seleccionado
        st.markdown(f"""
        <div class="equipo-card">
            <strong>{equipo['nombre']}</strong> &nbsp;|&nbsp;
            Tipo: {equipo.get('tipo', '—')} &nbsp;|&nbsp;
            Área: {equipo.get('area', '—')} &nbsp;|&nbsp;
            Clase: {equipo.get('clase_metrologica', '—')} &nbsp;|&nbsp;
            Estado: {equipo.get('estado', '—')}
        </div>
        """, unsafe_allow_html=True)

    # Parámetros técnicos: desde el equipo o ingresados manualmente
    st.markdown("**Parámetros del instrumento:**")
    col1, col2, col3 = st.columns(3)

    with col1:
        # Unidad: se pre-llena si el equipo la tiene
        unidad_default = equipo.get("unidad", "") if equipo else ""
        unidad = st.text_input("Unidad de medida", value=unidad_default,
                               placeholder="mm, kg, °C…")

    with col2:
        # Tolerancia/EMP: se pre-llena si el equipo la tiene
        emp_default = equipo.get("tolerancia_emp") if equipo else None
        emp = st.number_input(
            f"Tolerancia / EMP ({unidad or 'unidad'})",
            min_value=0.0, value=float(emp_default) if emp_default else 0.02,
            format="%.5f", step=0.001
        )
        if emp <= 0:
            st.error("La tolerancia debe ser mayor que cero.")
            return

    with col3:
        # Intervalo del fabricante: referencia para el método escalera
        fab_default = equipo.get("intervalo_fabricante_anios") if equipo else None
        intervalo_fabricante = st.number_input(
            "Intervalo fabricante (años)",
            min_value=0.1, value=float(fab_default) if fab_default else 1.0,
            format="%.2f", step=0.25
        )

    st.divider()

    # ── Sección 2: Selección del método ───────────────────────────────────────
    st.subheader("2 · Método de evaluación")

    METODOS = {
        "Escalera — Error medio":
            "Compara el **error medio** del punto con el 80% del EMP. "
            "No aplica si el equipo fue ajustado recientemente.",
        "Escalera — Error con incertidumbre":
            "Compara el **error ± incertidumbre expandida** con el 80% del EMP. "
            "Aplica la regla de decisión de conformidad.",
        "Cartas de control":
            "Analiza la **deriva del error** a lo largo de varias calibraciones. "
            "Requiere historial de al menos 2 fechas."
    }

    metodo = st.selectbox("Seleccione el método:", list(METODOS.keys()))
    st.info(METODOS[metodo])

    st.divider()

    # ── Sección 3: Formulario de datos según método ───────────────────────────
    st.subheader("3 · Datos de calibración")

    resultado_calculo = None   # se llenará con el resultado del método elegido
    fecha_cal_actual  = None   # para calcular la fecha próxima

    # ────────────────────────────────────────────────────────────────────────
    # MÉTODO 1 Y 2: Escalera
    # ────────────────────────────────────────────────────────────────────────
    if metodo in ("Escalera — Error medio", "Escalera — Error con incertidumbre"):

        fue_ajustado = st.selectbox(
            "¿El equipo fue ajustado mecánicamente en la última calibración?",
            ["No", "Sí"]
        ) == "Sí"

        col_a, col_b = st.columns(2)
        with col_a:
            fecha_cal_ant = st.date_input("Fecha calibración anterior",
                                          value=date.today().replace(year=date.today().year - 1))
        with col_b:
            fecha_cal_actual = st.date_input("Fecha calibración actual (vigente)",
                                              value=date.today())

        if fecha_cal_actual <= fecha_cal_ant:
            st.error("La fecha actual debe ser posterior a la anterior.")
            return

        intervalo_anterior = calcular_intervalo_anios(fecha_cal_ant, fecha_cal_actual)
        st.caption(f"Intervalo anterior calculado: **{intervalo_anterior:.3f} años**")

        error_medio = st.number_input(
            f"Error medio del punto ({unidad})",
            value=0.01, format="%.5f", step=0.001
        )

        incertidumbre = 0.0
        if metodo == "Escalera — Error con incertidumbre":
            incertidumbre = st.number_input(
                f"Incertidumbre expandida U ({unidad})",
                min_value=0.0, value=0.002, format="%.5f", step=0.001
            )
            if incertidumbre < 0:
                st.error("La incertidumbre no puede ser negativa.")
                return

        # Calcular
        if st.button("Calcular intervalo", type="primary"):
            if metodo == "Escalera — Error medio":
                resultado_calculo = escalera_error_medio(
                    error_medio, emp, intervalo_anterior, fue_ajustado
                )
                fig = grafica_escalera(error_medio, emp, unidad or "unidad")
            else:
                resultado_calculo = escalera_error_incertidumbre(
                    error_medio, incertidumbre, emp, intervalo_anterior, fue_ajustado
                )
                fig = grafica_escalera(error_medio, emp, unidad or "unidad",
                                       con_incertidumbre=True, incertidumbre=incertidumbre)

            st.session_state["ic_resultado"]  = resultado_calculo
            st.session_state["ic_fecha_base"] = fecha_cal_actual
            st.session_state["ic_metodo"]     = metodo
            st.session_state["ic_fig"]        = fig
            st.session_state["ic_error"]      = error_medio
            st.session_state["ic_u"]          = incertidumbre

    # ────────────────────────────────────────────────────────────────────────
    # MÉTODO 3: Cartas de control
    # ────────────────────────────────────────────────────────────────────────
    else:
        fue_ajustado_cc = st.selectbox(
            "¿El equipo fue ajustado en alguna de las calibraciones del historial?",
            ["No", "Sí"]
        ) == "Sí"

        fecha_ajuste_cc = None
        if fue_ajustado_cc:
            fecha_ajuste_cc = st.date_input("Fecha del ajuste mecánico")

        n_puntos = st.number_input("Cantidad de puntos críticos a evaluar",
                                    min_value=1, max_value=10, value=1, step=1)
        n_fechas = st.number_input("Cantidad de calibraciones en el historial",
                                    min_value=2, max_value=20, value=3, step=1)

        st.markdown("**Fechas de calibración:**")
        fechas_cc = []
        cols_fechas = st.columns(min(int(n_fechas), 4))
        for i in range(int(n_fechas)):
            with cols_fechas[i % 4]:
                default_f = date.today().replace(year=date.today().year - int(n_fechas) + i)
                f = st.date_input(f"Fecha {i+1}", value=default_f, key=f"cc_fecha_{i}")
                fechas_cc.append(f)

        # Verificar orden cronológico
        if fechas_cc != sorted(fechas_cc):
            st.error("Las fechas deben estar en orden cronológico.")
            return

        fecha_cal_actual = fechas_cc[-1]

        # Errores por punto
        st.markdown("**Errores por punto crítico:**")
        errores_por_punto = []

        for p in range(int(n_puntos)):
            with st.expander(f"Punto {p+1}", expanded=(p == 0)):
                val_nominal = st.number_input(
                    f"Valor nominal P{p+1} ({unidad})",
                    min_value=0.0001, value=10.0, format="%.4f",
                    key=f"vn_{p}"
                )
                errores_p = []
                for i, f in enumerate(fechas_cc):
                    # Si hubo ajuste, el error en esa fecha es 0 (bloqueado)
                    es_ajuste = fue_ajustado_cc and fecha_ajuste_cc and f == fecha_ajuste_cc
                    if es_ajuste:
                        st.caption(f"  Fecha {i+1} ({f}) — Ajuste: error = 0.00000 (automático)")
                        errores_p.append(0.0)
                    else:
                        err = st.number_input(
                            f"Error en {f} ({unidad})",
                            value=0.0, format="%.5f", step=0.001,
                            key=f"err_{p}_{i}"
                        )
                        errores_p.append(err)
                errores_por_punto.append({"nominal": val_nominal, "errores": errores_p})

        if st.button("Calcular intervalo", type="primary"):
            # Calcular para cada punto y tomar el más restrictivo
            resultados_puntos = []
            for p_data in errores_por_punto:
                res = cartas_control(
                    fechas_cc, p_data["errores"], emp,
                    fue_ajustado_cc, fecha_ajuste_cc
                )
                resultados_puntos.append({"nominal": p_data["nominal"], **res})

            # El intervalo final es el MÍNIMO entre todos los puntos
            intervalos_validos = [r["intervalo_nuevo"] for r in resultados_puntos
                                  if r["intervalo_nuevo"] is not None]

            if intervalos_validos:
                intervalo_final = min(intervalos_validos)
                tipo_final = "ok"
            else:
                intervalo_final = None
                tipo_final = "bad" if any(r["tipo"] == "bad" for r in resultados_puntos) else "warn"

            resultado_calculo = {
                "recomendacion": f"Intervalo más restrictivo entre {int(n_puntos)} punto(s): "
                                 f"{intervalo_final:.2f} años." if intervalo_final else
                                 "No se pudo calcular un intervalo válido. Revise los datos.",
                "intervalo_nuevo": intervalo_final,
                "tipo": tipo_final,
                "por_punto": resultados_puntos
            }

            # Gráfica del primer punto como referencia
            if resultados_puntos and resultados_puntos[0].get("datos_grafica"):
                fig = grafica_cartas_control(
                    resultados_puntos[0]["datos_grafica"], unidad or "unidad"
                )
            else:
                fig = None

            st.session_state["ic_resultado"]  = resultado_calculo
            st.session_state["ic_fecha_base"] = fecha_cal_actual
            st.session_state["ic_metodo"]     = metodo
            st.session_state["ic_fig"]        = fig

    # ── Sección 4: Resultados ─────────────────────────────────────────────────
    if "ic_resultado" in st.session_state and st.session_state["ic_resultado"]:
        st.divider()
        st.subheader("4 · Resultados")

        res       = st.session_state["ic_resultado"]
        fig_res   = st.session_state.get("ic_fig")
        fecha_base = st.session_state.get("ic_fecha_base")
        met_usado  = st.session_state.get("ic_metodo", metodo)

        # Clase CSS según tipo de resultado
        clase = {
            "ok":   "resultado-ok",
            "warn": "resultado-warn",
            "bad":  "resultado-bad"
        }.get(res["tipo"], "resultado-warn")

        icono = {"ok": "✅", "warn": "⚠️", "bad": "🚨"}.get(res["tipo"], "ℹ️")

        st.markdown(f"""
        <div class="resultado-box {clase}">
            <strong>{icono} {res['recomendacion']}</strong>
        </div>
        """, unsafe_allow_html=True)

        if res["intervalo_nuevo"] is not None and fecha_base:
            intervalo_r = res["intervalo_nuevo"]
            fecha_proxima = fecha_desde_intervalo(fecha_base, intervalo_r)

            col_r1, col_r2 = st.columns(2)
            col_r1.metric("Intervalo recomendado", f"{intervalo_r:.2f} años")
            col_r2.metric("Próxima calibración", fecha_proxima.strftime("%d/%m/%Y"))

        # Resultados por punto (Cartas de control)
        if res.get("por_punto"):
            st.markdown("**Detalle por punto:**")
            filas = []
            for p in res["por_punto"]:
                filas.append({
                    "Nominal": p["nominal"],
                    "Deriva/año": f"{p.get('deriva_anual', 0):.5f}" if p.get("deriva_anual") else "—",
                    "IC recomendado (años)": f"{p['intervalo_nuevo']:.2f}" if p["intervalo_nuevo"] else "—",
                    "Estado": {"ok": "✅ OK", "warn": "⚠️ Atención", "bad": "🚨 Crítico"}.get(p["tipo"], "—")
                })
            st.dataframe(pd.DataFrame(filas), use_container_width=True)

        # Gráfica
        if fig_res:
            st.markdown("**Visualización:**")
            st.pyplot(fig_res)
            plt.close(fig_res)

        # ── Sección 5: Guardar resultado ──────────────────────────────────────
        st.divider()
        st.subheader("5 · Guardar resultado")

        # ⚠️  COORDINACIÓN: Esta sección guarda los resultados en el JSON
        #     compartido. Solo funciona si hay un equipo seleccionado de la BD.
        #     Si el módulo está en modo manual, no hay ID de equipo para guardar.

        if equipo and equipo.get("id") and res["intervalo_nuevo"] is not None and fecha_base:
            fecha_proxima_str = fecha_desde_intervalo(fecha_base, res["intervalo_nuevo"]).strftime("%Y-%m-%d")

            if st.button("💾 Guardar en historial del equipo"):
                entrada = {
                    "resumen": {
                        "ultimo_intervalo_calculado_anios": res["intervalo_nuevo"],
                        "fecha_proxima_calibracion": fecha_proxima_str,
                        "metodo_usado": met_usado,
                        "fecha_calculo": date.today().strftime("%Y-%m-%d"),
                        "recomendacion": res["recomendacion"]
                    },
                    "entrada_historial": {
                        "fecha": fecha_base.strftime("%Y-%m-%d") if hasattr(fecha_base, "strftime") else str(fecha_base),
                        "fue_ajustado": False,
                        "errores_por_punto": [],
                        "metodo_ic_usado": met_usado,
                        "intervalo_calculado_anios": res["intervalo_nuevo"],
                        "fecha_proxima_calibracion": fecha_proxima_str,
                        "calculado_por": "IC"
                    }
                }
                ok = actualizar_resultado_ic(equipo["id"], entrada)
                if ok:
                    st.success(f"Resultado guardado para el equipo {equipo['nombre']}.")
                else:
                    st.warning("No se pudo guardar en el archivo de datos. "
                               "Verifique que el archivo JSON existe y tiene permisos de escritura.")
        elif not equipo:
            st.info("En modo manual no se guarda en la base de datos. "
                    "Cuando la app esté integrada con Ficha de Equipos, "
                    "el resultado se guardará automáticamente.")

        # ── Sección 6: Exportar ───────────────────────────────────────────────
        st.divider()
        st.subheader("6 · Exportar reporte")

        if res["intervalo_nuevo"] is not None and fecha_base:
            fecha_proxima = fecha_desde_intervalo(fecha_base, res["intervalo_nuevo"])
            reporte_txt = f"""REPORTE DE INTERVALO DE CALIBRACIÓN
====================================
Equipo       : {equipo['nombre'] if equipo else 'Ingreso manual'}
ID           : {equipo['id'] if equipo else '—'}
Unidad       : {unidad}
EMP          : {emp}
Método       : {met_usado}
Fecha cálculo: {date.today().strftime('%d/%m/%Y')}

RESULTADO
---------
Intervalo recomendado : {res['intervalo_nuevo']:.2f} años
Próxima calibración   : {fecha_proxima.strftime('%d/%m/%Y')}
Recomendación         : {res['recomendacion']}

Generado por MetroControl — Módulo de Intervalos de Calibración (ILAC-G24)
"""
            st.download_button(
                label="📄 Descargar reporte (.txt)",
                data=reporte_txt,
                file_name=f"IC_{equipo['id'] if equipo else 'manual'}_{date.today()}.txt",
                mime="text/plain"
            )

        # ── Sección 7: Historial del equipo ───────────────────────────────────
        if equipo and equipo.get("historial_calibraciones"):
            st.divider()
            st.subheader("7 · Historial de calibraciones")

            hist = equipo["historial_calibraciones"]
            filas_hist = []
            for h in hist:
                filas_hist.append({
                    "Fecha": h.get("fecha", "—"),
                    "Método IC": h.get("metodo_ic_usado") or "—",
                    "IC calculado (años)": h.get("intervalo_calculado_anios") or "—",
                    "Próxima calibración": h.get("fecha_proxima_calibracion") or "—",
                    "Registrado por": h.get("calculado_por", "—")
                })
            st.dataframe(pd.DataFrame(filas_hist), use_container_width=True)


# ── Punto de entrada cuando se corre el módulo de forma independiente ─────────
if __name__ == "__main__":
    # ⚠️  COORDINACIÓN: Este bloque solo se usa para desarrollo independiente.
    #     En la app integrada, app.py llama a mostrar_intervalos() directamente.
    st.set_page_config(
        page_title="Intervalos de Calibración — MetroControl",
        page_icon="📐",
        layout="wide"
    )
    mostrar_intervalos()
