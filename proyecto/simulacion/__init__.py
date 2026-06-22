# Expone la API pública del paquete simulacion.
# Gracias a esto, desde afuera se puede hacer:
#   from simulacion import simular_sistema
# en lugar de:
#   from simulacion.simulador import simular_sistema

from .simulador import simular_sistema
