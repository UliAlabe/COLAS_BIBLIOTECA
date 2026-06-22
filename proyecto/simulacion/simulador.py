import random
import math
import simpy

from .utils import formato_hora
from .modelos import ClienteSimpy, DatosAleatorios
from .euler import calcular_euler
from .buffer import BufferSnapshot


class SimuladorBiblioteca:
    """
    Motor de simulación de eventos discretos para la biblioteca.

    Cada cliente que llega se modela como un proceso independiente (generador de Python).
    SimPy se encarga de pausar y reanudar cada proceso en el momento correcto,
    sin necesidad de avanzar el reloj minuto a minuto.
    """

    def __init__(self, params):
        self.params = params
        self.env = simpy.Environment()
        # Ventanilla con 2 empleados: SimPy maneja la cola FIFO automáticamente
        self.empleados = simpy.Resource(self.env, capacity=2)
        self.buffer = BufferSnapshot(params)

        # Contadores y estado global del sistema
        self.num_llegadas = 0
        self.num_rechazos = 0
        self.num_salidas = 0
        self.acum_permanencia = 0.0
        self.clientes_leyendo = 0
        self.estado_emp1 = "Libre"
        self.estado_emp2 = "Libre"
        self.hora_fin_emp1 = ""
        self.hora_fin_emp2 = ""
        self.proxima_llegada = params['t_llegada']

        # Array de longitud fija: cada posición es un lugar físico en la sala
        self.clientes_en_sala = [None] * params['capacidad']

    # ------------------------------------------------------------------
    # Helpers de empleados
    # ------------------------------------------------------------------

    def _asignar_empleado(self, id_cliente):
        """
        Marca como ocupado el primer empleado libre y devuelve su número (1 o 2).
        El else de fallback existe porque el rastreo manual puede desincronizarse
        levemente con el contador interno de SimPy en casos de concurrencia.
        """
        if self.estado_emp1 == "Libre":
            self.estado_emp1 = f"Ocup (ID {id_cliente})"
            return 1
        elif self.estado_emp2 == "Libre":
            self.estado_emp2 = f"Ocup (ID {id_cliente})"
            return 2
        else:
            self.estado_emp1 = f"Ocup (ID {id_cliente})"
            return 1

    def _liberar_empleado(self, numero_empleado):
        """Deja al empleado indicado como libre y borra su hora de fin de atención."""
        if numero_empleado == 1:
            self.estado_emp1 = "Libre"
            self.hora_fin_emp1 = ""
        else:
            self.estado_emp2 = "Libre"
            self.hora_fin_emp2 = ""

    def _generar_tiempo_devolucion(self):
        """Tiempo de atención para una devolución (distribución uniforme). Devuelve (rnd, tiempo)."""
        rnd = random.random()
        tiempo = self.params['u_dev_a'] + rnd * (self.params['u_dev_b'] - self.params['u_dev_a'])
        return rnd, tiempo

    # ------------------------------------------------------------------
    # Comunicación con el buffer
    # ------------------------------------------------------------------

    def _estado_actual(self):
        """Devuelve un diccionario con el estado del sistema en este instante."""
        return {
            'emp1': str(self.estado_emp1),
            'fin_atenc_emp1': self.hora_fin_emp1,
            'emp2': str(self.estado_emp2),
            'fin_atenc_emp2': self.hora_fin_emp2,
            'queue_len': len(self.empleados.queue),
            'leyendo': self.clientes_leyendo,
            'llegadas': self.num_llegadas,
            'rechazos': self.num_rechazos,
            'salidas': self.num_salidas,
            'acum_permanencia': self.acum_permanencia,
            'proxima_llegada': self.proxima_llegada,
        }

    def _registrar(self, evento_str, datos=None):
        """Informa al buffer de un evento ocurrido en el instante actual."""
        if datos is None:
            datos = DatosAleatorios()
        self.buffer.agregar_evento(
            self.env.now, evento_str, datos,
            self._estado_actual(), self.clientes_en_sala
        )

    # ------------------------------------------------------------------
    # Procesos SimPy
    # ------------------------------------------------------------------

    def proceso_cliente(self, id_cliente):
        """
        Describe la vida completa de un cliente desde que llega hasta que se va.
        Cada 'yield' pausa este proceso y cede el control a SimPy, que lo
        reanuda cuando el tiempo de espera transcurrió.
        """
        hora_llegada_cliente = self.env.now

        # Verificamos si hay lugar en la biblioteca (mostrador + cola + mesas de lectura)
        personas_adentro = self.empleados.count + len(self.empleados.queue) + self.clientes_leyendo
        self.num_llegadas += 1

        if personas_adentro >= self.params['capacidad']:
            # Sin lugar: el cliente es rechazado y no entra al sistema
            self.num_rechazos += 1
            self._registrar("Llegada (Rechazo)")
            return

        lugar_libre = self.clientes_en_sala.index(None)
        cliente = ClienteSimpy(id_cliente, hora_llegada_cliente, lugar_libre)
        self.clientes_en_sala[lugar_libre] = cliente

        # Monte Carlo: determinamos qué vino a hacer el cliente
        rnd_tipo_atencion = random.random()
        if rnd_tipo_atencion < self.params['p_pedir']:
            tipo = "Pedir"
        elif rnd_tipo_atencion < (self.params['p_pedir'] + self.params['p_dev']):
            tipo = "Devolver"
        else:
            tipo = "Consultar"

        # El 'with' pide el recurso antes de registrar la llegada,
        # así el cliente ya está en la cola matemática de SimPy al momento del evento
        with self.empleados.request() as peticion:
            cliente.estado = f"Fila ({tipo[:3]})"
            self._registrar(
                f"Llegada ({tipo})",
                DatosAleatorios(rnd_tipo=rnd_tipo_atencion, tipo_atencion=tipo)
            )

            # Pausa hasta que un empleado quede libre
            yield peticion

            numero_empleado = self._asignar_empleado(id_cliente)
            cliente.estado = f"Atend. ({tipo[:3]})"

            # Tiempo de atención según el tipo de trámite
            if tipo == "Pedir":
                rnd_tiempo_atencion = random.random()
                # Transformada inversa: distribución exponencial negativa
                tiempo_atencion = -self.params['m_pedir'] * math.log(1 - rnd_tiempo_atencion)
            elif tipo == "Devolver":
                rnd_tiempo_atencion, tiempo_atencion = self._generar_tiempo_devolucion()
            else:
                rnd_tiempo_atencion = random.random()
                tiempo_atencion = self.params['u_cons_a'] + rnd_tiempo_atencion * (self.params['u_cons_b'] - self.params['u_cons_a'])

            hora_fin_atencion = self.env.now + tiempo_atencion
            if numero_empleado == 1:
                self.hora_fin_emp1 = hora_fin_atencion
            else:
                self.hora_fin_emp2 = hora_fin_atencion

            self._registrar(
                f"Inicia Atenc ({tipo})",
                DatosAleatorios(rnd_tiempo=rnd_tiempo_atencion, tiempo_atencion=tiempo_atencion)
            )

            # Pausa durante el tiempo de atención
            yield self.env.timeout(tiempo_atencion)

            # Si pidió un libro, decidimos si se queda a leer
            rnd_decision_quedarse = ""
            cliente_se_queda_a_leer = ""
            if tipo == "Pedir":
                rnd_decision_quedarse = random.random()
                cliente_se_queda_a_leer = "Sí" if rnd_decision_quedarse < self.params['p_queda'] else "No"

            self._liberar_empleado(numero_empleado)
            self._registrar(
                f"Fin Atenc ({tipo})",
                DatosAleatorios(rnd_quedarse=rnd_decision_quedarse, se_queda=cliente_se_queda_a_leer)
            )

        # Flujo de lectura: el cliente se sienta, lee y luego devuelve el libro
        if tipo == "Pedir" and cliente_se_queda_a_leer == "Sí":
            self.clientes_leyendo += 1

            # Generamos la cantidad de páginas del libro (distribución uniforme)
            rnd_paginas = random.random()
            paginas_totales = self.params['u_pag_a'] + rnd_paginas * (self.params['u_pag_b'] - self.params['u_pag_a'])

            # La constante K depende del rango de páginas del libro
            if paginas_totales <= 200:
                k = self.params['k1']
            elif paginas_totales <= 300:
                k = self.params['k2']
            else:
                k = self.params['k3']

            # Solo se guardan filas de auditoría Euler si el cliente cae en la ventana visible
            es_auditable = (
                self.env.now >= self.params['desde_reloj'] and
                len(self.buffer.filas_vector_estado) < self.params['filas_mostrar']
            )

            tiempo_lectura, filas_euler = calcular_euler(
                paginas_totales, k, self.params['paso_euler'],
                id_cliente, formato_hora(self.env.now), es_auditable
            )

            self.buffer.filas_euler_auditoria.extend(filas_euler)

            cliente.hora_fin_lectura = formato_hora(self.env.now + tiempo_lectura)
            cliente.estado = "Leyendo"
            self._registrar(
                "Inicia Lectura",
                DatosAleatorios(rnd_paginas=rnd_paginas, paginas=paginas_totales, k_aplicado=k, tiempo_lectura=tiempo_lectura)
            )

            # Pausa durante el tiempo de lectura
            yield self.env.timeout(tiempo_lectura)

            self.clientes_leyendo -= 1
            cliente.hora_fin_lectura = ""
            self._registrar("Fin Lectura")

            # El lector debe devolver el libro antes de irse (regla de negocio)
            with self.empleados.request() as peticion_devolucion:
                cliente.estado = "Fila (Dev)"
                self._registrar("Pasa a Fila (Dev)")

                yield peticion_devolucion

                numero_empleado = self._asignar_empleado(id_cliente)
                cliente.estado = "Atend. (Dev)"

                rnd_tiempo_devolucion, tiempo_devolucion = self._generar_tiempo_devolucion()

                hora_fin_devolucion = self.env.now + tiempo_devolucion
                if numero_empleado == 1:
                    self.hora_fin_emp1 = hora_fin_devolucion
                else:
                    self.hora_fin_emp2 = hora_fin_devolucion

                self._registrar(
                    "Inicia Atenc (Dev Post-Lect)",
                    DatosAleatorios(rnd_tiempo=rnd_tiempo_devolucion, tiempo_atencion=tiempo_devolucion)
                )

                yield self.env.timeout(tiempo_devolucion)

                self._liberar_empleado(numero_empleado)
                self._registrar("Fin Atenc (Post-Lect)")

        # El cliente se va: actualizamos métricas y liberamos su lugar en sala
        self.num_salidas += 1
        self.acum_permanencia += (self.env.now - hora_llegada_cliente)
        self.clientes_en_sala[cliente.lugar_en_sala] = None
        self._registrar("Sale Sistema")

    def generador_llegadas(self):
        """
        Fábrica de clientes: lanza uno cada 't_llegada' minutos
        hasta alcanzar el tiempo o la cantidad máxima de llegadas.
        """
        id_proximo_cliente = 1
        while (self.env.now <= self.params['tiempo_simulacion'] and
               id_proximo_cliente <= self.params['limite_iteraciones']):
            self.proxima_llegada = self.env.now + self.params['t_llegada']
            self.env.process(self.proceso_cliente(id_proximo_cliente))
            id_proximo_cliente += 1
            yield self.env.timeout(self.params['t_llegada'])

    # ------------------------------------------------------------------
    # Punto de entrada
    # ------------------------------------------------------------------

    def ejecutar(self):
        """Corre la simulación completa y devuelve los datos para la UI."""
        self.env.process(self.generador_llegadas())
        self.env.run(until=self.params['tiempo_simulacion'])
        # Forzamos la captura del instante final con la fila FIN SIMULACIÓN
        self.buffer.commit_final(self._estado_actual(), self.clientes_en_sala)
        return self._armar_resultado()

    def _armar_resultado(self):
        """Empaqueta columnas y datos en la estructura que espera la interfaz."""
        columnas_base = [
            "N° Evento", "Evento", "Reloj", "Próx Llegada",
            "RND Tipo", "Tipo Atenc (RND)", "RND Atenc", "T. Atenc", "RND Queda", "¿Se Queda?",
            "RND Pág", "Páginas", "Valor K", "T. Lectura (min)",
            "Emp 1", "Fin Atenc 1", "Emp 2", "Fin Atenc 2", "Cola (Q)", "Leyendo (Q)",
            "Llegadas", "Rechazos", "% Rechazos", "Salidas", "Acum Perm", "Prom Perm"
        ]

        columnas_euler = [
            "Entidad - Integración", "Iteración", "Reloj Sistema", "Estado Método",
            "Var. Tiempo (t)", "Var. Acumuladora (P)", "Derivada (dP/dt)"
        ]

        # Una columna por cada lugar físico de la sala (4 campos por cliente)
        columnas_slots = []
        for c in range(self.params['capacidad']):
            columnas_slots.extend([f"C{c+1}_ID", f"C{c+1}_Lleg", f"C{c+1}_Est", f"C{c+1}_FinLect"])

        columnas_principal = tuple(columnas_base + columnas_slots)

        porcentaje_rechazos = (self.num_rechazos / self.num_llegadas) * 100 if self.num_llegadas > 0 else 0
        promedio_permanencia = (self.acum_permanencia / self.num_salidas) if self.num_salidas > 0 else 0

        return (
            columnas_principal,
            self.buffer.filas_vector_estado,
            columnas_euler,
            self.buffer.filas_euler_auditoria,
            porcentaje_rechazos,
            promedio_permanencia
        )


def simular_sistema(params):
    """Punto de entrada público. Corre la simulación y devuelve los resultados."""
    return SimuladorBiblioteca(params).ejecutar()
