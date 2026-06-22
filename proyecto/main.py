# =============================================================
# SIMULADOR DE EVENTOS DISCRETOS - BIBLIOTECA
# Motor: SimPy (backend estadístico) + Tkinter (frontend visual)
# Arquitectura: Buffer de Estado por Instante de Tiempo (Snapshot)
# =============================================================
# "pip install simpy" o "python -m pip install simpy" para poder correr
#
# Este archivo es la versión modularizada de tp-5-4.0.py.
# El mismo código, separado en módulos para que sea más legible:
#
#   simulacion/
#     utils.py      → formato_hora (conversión decimal → HH:MM:SS)
#     modelos.py    → ClienteSimpy (ficha de cada cliente en el sistema)
#     euler.py      → calcular_euler (algoritmo numérico de integración)
#     simulador.py  → simular_sistema (motor SimPy + buffer de snapshots)
#   gui/
#     ventana.py    → VentanaSimulacion (interfaz Tkinter completa)

import tkinter as tk  # [COMANDO]: Importa la librería base para interfaces de escritorio nativas en Python.

from gui import VentanaSimulacion

# ==========================================
# PUNTO DE ENTRADA AL PROGRAMA
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()  # Levanta el lienzo gráfico interactuando con Windows/OS.
    app = VentanaSimulacion(root)
    root.mainloop()  # Atrapa el programa en un loop infinito para que la ventana no se cierre sola.
