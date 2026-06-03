"""
app.py — App principal de MetroControl
========================================
Punto de entrada de la aplicación. Gestiona la navegación
entre todos los módulos de los distintos grupos.

Para correr la aplicación:
    streamlit run app.py

⚠️  COORDINACIÓN CON OTROS GRUPOS:
    - Solo este archivo llama a st.set_page_config()
    - Cada grupo agrega su módulo en la sección MÓDULOS más abajo
    - No modificar la paleta de colores ni el CSS global sin avisar
"""

import streamlit as st
import sys, os

# Agregar la raíz del proyecto al path para que los imports funcionen
# independientemente de desde dónde se corra el comando streamlit run
RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

# ── Importar módulos disponibles ──────────────────────────────────────────────
# ⚠️  COORDINACIÓN: Cada grupo descomenta su línea cuando su módulo esté listo.
#     El nombre de la función debe ser mostrar_<nombre>() por convención.

from modulos.intervalos_cal import mostrar_intervalos

# from modulos.ficha_equipos   import mostrar_ficha        # ← Grupo Ficha
# from modulos.mantenimiento   import mostrar_mantenimiento # ← Grupo Mantenimiento
# from modulos.regla_decision  import mostrar_regla         # ← Grupo Regla decisión
# from modulos.condiciones_uso import mostrar_condiciones   # ← Grupo Condiciones

# ── Configuración global ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="MetroControl",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS global ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  html, body, [class*="css"] { font-family: sans-serif; }

  [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #0b2c40 0%, #0a453c 100%);
  }
  [data-testid="stSidebar"] * { color: #e8f5e9 !important; }

  .logo-sidebar {
      text-align: center;
      padding: 1.2rem 0.5rem 0.5rem;
      border-bottom: 1px solid #2dc19733;
      margin-bottom: 1rem;
  }
  .logo-sidebar h2 { color: #2dc197 !important; font-size: 1.4rem; margin: 0; }
  .logo-sidebar p  { color: #a5d6a7 !important; font-size: 0.75rem; margin: 0.2rem 0 0; }

  .badge-plus {
      background: #238d93;
      color: white !important;
      font-size: 0.65rem;
      border-radius: 4px;
      padding: 1px 5px;
      margin-left: 4px;
      vertical-align: middle;
  }
  .badge-wip {
      background: #ff9800;
      color: white !important;
      font-size: 0.65rem;
      border-radius: 4px;
      padding: 1px 5px;
      margin-left: 4px;
  }
</style>
""", unsafe_allow_html=True)

# ── Navegación lateral ────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="logo-sidebar">
        <h2>🔬 MetroControl</h2>
        <p>Gestión metrológica integral</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**Plan Base**")

    # ⚠️  COORDINACIÓN: Agregar cada módulo aquí cuando esté listo.
    #     Marcar con 🔒 los que aún no están disponibles.

    paginas_base = {
        "🏠 Inicio":              "inicio",
        "📋 Ficha de equipos":    "ficha",       # ← Grupo Ficha (pendiente)
        "🔧 Mantenimiento":       "mantenimiento", # ← Grupo Mantenimiento (pendiente)
    }

    paginas_plus = {
        "📐 Intervalos de calibración": "intervalos",  # ← NUESTRO MÓDULO ✓
        "⚖️  Regla de decisión":         "regla",       # ← Otro grupo (pendiente)
    }

    seleccion = st.radio("Navegar a:", list(paginas_base.keys()) + ["---"] + list(paginas_plus.keys()),
                         label_visibility="collapsed")

    st.divider()
    st.caption("v1.0 · ILAC-G24 · ISO 17025")

# ── Renderizar la página seleccionada ─────────────────────────────────────────

if seleccion == "🏠 Inicio":
    # ── Pantalla de inicio ────────────────────────────────────────────────────
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #063d7d 0%, #238d93 60%, #0a453c 100%);
        border-radius: 16px; padding: 2.5rem 3rem; margin-bottom: 2rem; color: white;
    ">
        <h1 style="color:white; margin:0; font-size:2.2rem;">🔬 MetroControl</h1>
        <p style="margin:0.5rem 0 0; opacity:0.9; font-size:1.05rem;">
            Plataforma integral de gestión y control metrológico
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Módulos disponibles")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**📋 Ficha de equipos**\n\nRegistro completo de instrumentos, "
                "clase metrológica, proveedor y documentación técnica.\n\n🔒 Próximamente")
    with col2:
        st.info("**🔧 Control de mantenimiento**\n\nProgramación y seguimiento de "
                "mantenimientos preventivos y correctivos.\n\n🔒 Próximamente")
    with col3:
        st.success("**📐 Intervalos de calibración**\n\nDeterminación del intervalo "
                   "según ILAC-G24. Métodos: Escalera y Cartas de control.\n\n✅ Disponible")

    col4, col5 = st.columns(2)
    with col4:
        st.info("**⚖️ Regla de decisión**\n\nEvaluación de conformidad con "
                "incertidumbre. ISO 14253.\n\n🔒 Próximamente")
    with col5:
        st.markdown("""
        <div style="background:#063d7d22; border-radius:8px; padding:1rem; border:1px solid #063d7d55;">
        <strong>ℹ️ Sobre la plataforma</strong><br><br>
        MetroControl cumple con los requisitos de la norma ISO/IEC 17025
        para el aseguramiento del control metrológico de instrumentos de medición.
        </div>
        """, unsafe_allow_html=True)

elif seleccion == "📐 Intervalos de calibración":
    mostrar_intervalos()

elif seleccion == "📋 Ficha de equipos":
    st.warning("⏳ Módulo en desarrollo por otro grupo. Disponible próximamente.")
    # ⚠️  COORDINACIÓN: Cuando el grupo de Ficha tenga su módulo listo,
    #     reemplazar la línea anterior por:
    #         mostrar_ficha()

elif seleccion == "🔧 Mantenimiento":
    st.warning("⏳ Módulo en desarrollo por otro grupo. Disponible próximamente.")
    # ⚠️  COORDINACIÓN: mostrar_mantenimiento()

elif seleccion == "⚖️  Regla de decisión":
    st.warning("⏳ Módulo en desarrollo por otro grupo. Disponible próximamente.")
    # ⚠️  COORDINACIÓN: mostrar_regla()

else:
    st.info("Seleccione una sección en el menú lateral.")
