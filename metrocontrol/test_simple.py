import streamlit as st

st.set_page_config(page_title="Test", layout="wide")

st.title("✅ MetroControl funciona")
st.write("Si ves esto, Streamlit está bien.")

import sys, os
RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

try:
    from utils.data_manager import equipos_demo
    equipos = equipos_demo()
    st.success(f"✅ data_manager OK — {len(equipos)} equipos cargados")
except Exception as e:
    st.error(f"❌ data_manager falló: {e}")

try:
    from modulos.intervalos_cal import mostrar_intervalos
    st.success("✅ intervalos_cal importado OK")
    mostrar_intervalos()
except Exception as e:
    st.error(f"❌ intervalos_cal falló: {e}")
    import traceback
    st.code(traceback.format_exc())
