from .utils import formato_hora
from .modelos import DatosAleatorios


class BufferSnapshot:
    """
    Acumula los eventos que ocurren en el mismo instante de tiempo y genera
    una única fila para el vector de estado cuando el reloj avanza.

    El flujo es:
      1. agregar_evento() se llama por cada evento del simulador.
      2. Cuando el reloj avanza, el buffer anterior se "committea" (se guarda
         como fila en el vector de estado) y se abre uno nuevo.
      3. Al terminar la simulación, commit_final() genera la fila de cierre.
    """

    def __init__(self, params):
        self.params = params
        self.filas_vector_estado = []     # Filas que se muestran en la pestaña principal
        self.filas_euler_auditoria = []   # Filas que se muestran en la pestaña Euler
        self._reloj_buffer = -1.0         # Reloj del instante que está acumulando
        self._datos_buffer = None         # Eventos + RNDs + snapshot del instante actual
        self._num_evento = 1              # Contador incremental de filas visibles

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def agregar_evento(self, reloj_actual, evento_str, datos_rnds, estado_snapshot, clientes_en_sala):
        """
        Registra un evento. Si el reloj avanzó respecto al buffer actual,
        committea ese buffer antes de abrir uno nuevo.
        """
        # Si el reloj cambió, el instante anterior cerró: lo persistimos
        if reloj_actual > self._reloj_buffer and self._datos_buffer is not None:
            self._commit()
            self._datos_buffer = None

        self._reloj_buffer = reloj_actual

        # Inicializamos el buffer para este nuevo instante
        if self._datos_buffer is None:
            self._datos_buffer = {
                'eventos': [],
                'rnds': DatosAleatorios(),
                'snapshot': None
            }

        self._datos_buffer['eventos'].append(evento_str)
        self._fusionar_rnds(datos_rnds)

        # Solo construimos el snapshot si este instante va a generar una fila visible
        # (filtro por parámetros j e i). Evita armar copias costosas para eventos fuera de ventana.
        necesita_snapshot = (
            reloj_actual >= self.params['desde_reloj'] and
            len(self.filas_vector_estado) < self.params['filas_mostrar']
        )
        if necesita_snapshot:
            self._datos_buffer['snapshot'] = self._empaquetar_snapshot(
                estado_snapshot, clientes_en_sala
            )

    def commit_final(self, estado_snapshot, clientes_en_sala):
        """
        Genera la fila especial de FIN SIMULACIÓN al terminar la corrida.
        Usa el snapshot del último buffer pendiente si existe;
        de lo contrario captura el estado actual del sistema.
        """
        if self._datos_buffer is not None and self._datos_buffer.get('snapshot') is not None:
            snap = self._datos_buffer['snapshot']
        else:
            snap = self._empaquetar_snapshot(estado_snapshot, clientes_en_sala)

        fila = self._construir_fila(snap, "FIN SIMULACIÓN", DatosAleatorios(), ocultar_proxima_llegada=True)
        self.filas_vector_estado.append(fila)
        # La fila FIN SIMULACIÓN no incrementa el contador de eventos (igual que en el original)

    # ------------------------------------------------------------------
    # Lógica interna
    # ------------------------------------------------------------------

    def _commit(self):
        """
        Toma el buffer acumulado y genera la fila en el vector de estado,
        pero solo si el instante cae dentro de la ventana visible (j, i).
        """
        fuera_de_ventana = (
            self._reloj_buffer < self.params['desde_reloj'] or
            len(self.filas_vector_estado) >= self.params['filas_mostrar']
        )
        if fuera_de_ventana:
            self._num_evento += 1
            return

        snap = self._datos_buffer.get('snapshot')
        if snap is None:
            self._num_evento += 1
            return

        # De todos los eventos del instante, solo mostramos los "primarios"
        # (los que realmente hacen avanzar el reloj de simulación)
        eventos_primarios = [
            e for e in self._datos_buffer['eventos']
            if "Llegada" in e or "Fin Atenc" in e or "Fin Lectura" in e
        ]
        if not eventos_primarios:
            eventos_primarios = self._datos_buffer['eventos']
        evento_str = " + ".join(eventos_primarios)

        fila = self._construir_fila(snap, evento_str, self._datos_buffer['rnds'])
        self.filas_vector_estado.append(fila)
        self._num_evento += 1

    def _fusionar_rnds(self, nuevos):
        """
        Actualiza el acumulador de datos aleatorios del buffer actual.
        Solo sobreescribe los campos que el evento entrante realmente aportó,
        para no borrar los datos de eventos anteriores del mismo instante.
        """
        rnds = self._datos_buffer['rnds']
        if nuevos.rnd_tipo != "":        rnds.rnd_tipo = nuevos.rnd_tipo
        if nuevos.tipo_atencion != "":   rnds.tipo_atencion = nuevos.tipo_atencion
        if nuevos.rnd_tiempo != "":      rnds.rnd_tiempo = nuevos.rnd_tiempo
        if nuevos.tiempo_atencion != "": rnds.tiempo_atencion = nuevos.tiempo_atencion
        if nuevos.rnd_quedarse != "":    rnds.rnd_quedarse = nuevos.rnd_quedarse
        if nuevos.se_queda != "":        rnds.se_queda = nuevos.se_queda
        if nuevos.rnd_paginas != "":     rnds.rnd_paginas = nuevos.rnd_paginas
        if nuevos.paginas != "":         rnds.paginas = nuevos.paginas
        if nuevos.k_aplicado != "":      rnds.k_aplicado = nuevos.k_aplicado
        if nuevos.tiempo_lectura != "":  rnds.tiempo_lectura = nuevos.tiempo_lectura

    def _empaquetar_snapshot(self, estado_snapshot, clientes_en_sala):
        """Combina el estado del sistema con la lista de clientes en sala en un dict."""
        return {
            **estado_snapshot,
            'slots': [
                (c.id, c.llegada, c.estado, c.hora_fin_lectura) if c else None
                for c in clientes_en_sala
            ]
        }

    def _construir_fila(self, snap, evento_str, rnds, ocultar_proxima_llegada=False):
        """Arma la tupla final que se inserta en el vector de estado."""
        acum_perm = round(snap.get('acum_permanencia', 0.0), 2)
        prom_perm = round(snap['acum_permanencia'] / snap['salidas'], 2) if snap.get('salidas', 0) > 0 else 0.0
        porc_rechazos = round((snap['rechazos'] / snap['llegadas']) * 100, 2) if snap.get('llegadas', 0) > 0 else 0.0

        # Redondeo de cada campo numérico para la visualización
        r_rnd_tipo = round(rnds.rnd_tipo, 4) if isinstance(rnds.rnd_tipo, float) else rnds.rnd_tipo
        r_rnd_tiempo = round(rnds.rnd_tiempo, 4) if isinstance(rnds.rnd_tiempo, float) else rnds.rnd_tiempo
        r_tiempo_atencion = round(rnds.tiempo_atencion, 2) if isinstance(rnds.tiempo_atencion, float) else rnds.tiempo_atencion
        r_rnd_quedarse = round(rnds.rnd_quedarse, 4) if isinstance(rnds.rnd_quedarse, float) else rnds.rnd_quedarse
        r_rnd_paginas = round(rnds.rnd_paginas, 4) if isinstance(rnds.rnd_paginas, float) else rnds.rnd_paginas
        r_paginas = int(rnds.paginas) if isinstance(rnds.paginas, float) else rnds.paginas
        r_tiempo_lectura = round(rnds.tiempo_lectura, 2) if isinstance(rnds.tiempo_lectura, float) else rnds.tiempo_lectura

        proxima_llegada = snap.get('proxima_llegada', "")
        if ocultar_proxima_llegada:
            proxima_llegada_str = "-"
        else:
            proxima_llegada_str = formato_hora(proxima_llegada) if isinstance(proxima_llegada, float) else proxima_llegada

        hora_fin_emp1 = snap.get('fin_atenc_emp1', "")
        hora_fin_emp1_str = formato_hora(hora_fin_emp1) if isinstance(hora_fin_emp1, float) else hora_fin_emp1

        hora_fin_emp2 = snap.get('fin_atenc_emp2', "")
        hora_fin_emp2_str = formato_hora(hora_fin_emp2) if isinstance(hora_fin_emp2, float) else hora_fin_emp2

        # Empaquetado de los slots: cada cliente ocupa 4 columnas (ID, llegada, estado, fin lectura)
        datos_slots = []
        for s in snap.get('slots', []):
            if s is None:
                datos_slots.extend(["", "", "", ""])
            else:
                datos_slots.extend([s[0], formato_hora(s[1]), s[2], s[3]])

        return (
            self._num_evento, evento_str, formato_hora(self._reloj_buffer), proxima_llegada_str,
            r_rnd_tipo, rnds.tipo_atencion, r_rnd_tiempo, r_tiempo_atencion,
            r_rnd_quedarse, rnds.se_queda,
            r_rnd_paginas, r_paginas, rnds.k_aplicado, r_tiempo_lectura,
            snap.get('emp1', "Libre"), hora_fin_emp1_str,
            snap.get('emp2', "Libre"), hora_fin_emp2_str,
            snap.get('queue_len', 0), snap.get('leyendo', 0),
            snap.get('llegadas', 0), snap.get('rechazos', 0), porc_rechazos, snap.get('salidas', 0),
            acum_perm, prom_perm
        ) + tuple(datos_slots)
