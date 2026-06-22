# Expone la API pública del paquete gui.
# Gracias a esto, desde afuera se puede hacer:
#   from gui import VentanaSimulacion
# en lugar de:
#   from gui.ventana import VentanaSimulacion

from .ventana import VentanaSimulacion
