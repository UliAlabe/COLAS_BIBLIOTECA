# =============================================================
# SIMULADOR DE EVENTOS DISCRETOS - BIBLIOTECA
# Motor: SimPy (backend estadístico) + Tkinter (frontend visual)
# Arquitectura: Buffer de Estado por Instante de Tiempo (Snapshot)
# =============================================================
# "pip install "simpy" o "python -m pip install simpy" para poder correr

import tkinter as tk  # [COMANDO]: Importa la librería base para interfaces de escritorio nativas en Python.
from tkinter import ttk, messagebox  # [COMANDO]: Importa widgets estilizados (Treeview, botones) y ventanas de alerta.
import random  # [LIBRERÍA]: Motor estadístico base. Genera números pseudoaleatorios entre 0 y 1.
import math  # [LIBRERÍA]: Funciones matemáticas en C. Acá se usa para el logaritmo natural (ln).
import simpy  # [LIBRERÍA]: Framework de simulación discreta. Reemplaza el bucle de "salto de reloj" manual.


# El sistema es un conjunto de procesos individuales durmiendo. SimPy solo gasta energía en despertar a la persona que le
# toca actuar, deja que haga su movimiento, le saca una foto al tablero completo para tu grilla, y la vuelve a mandar a dormir.
# El mecanismo de "Checkpoints" (SimPy + Python)
# La Pausa (yield de Python):
# Cuando el código lee la palabra yield, Python congela la función del cliente en esa línea exacta. Hace un "checkpoint" en la
# RAM guardando todas las variables (id, rnd, etc.) tal cual están y libera el procesador.

# La Agenda (Motor SimPy):
# Al hacer yield env.timeout(15), el cliente le avisa a SimPy: "Anotame en tu agenda y despertame dentro de 15 minutos". El cliente queda dormido.
#
# El Salto Temporal (Eficiencia):
# SimPy no avanza el reloj minuto a minuto. Mira su agenda oculta, saltea  el tiempo muerto donde no pasa nada, y hace que el reloj salte
# directamente al instante del próximo evento programado.
#
# El Despertar (Resume):
# Cuando el reloj global llega al minuto anotado, SimPy va a la RAM, carga el checkpoint de ese cliente específico, y la función
# arranca exactamente en la línea debajo del yield, con todos sus datos intactos.
#
# ==========================================
# 1. LÓGICA DE SIMULACIÓN (BACKEND)
# ==========================================

def formato_hora(minutos_float):
    """
    [ALGORITMO]: Conversión de formato continuo (decimal) a sexagesimal (HH:MM:SS).
    [POR QUÉ]: SimPy maneja el tiempo como un número de punto flotante (ej: 13.5 minutos),
    pero la rúbrica exige que el Vector de Estado sea legible para un humano.
    """
    if minutos_float == float('inf') or minutos_float == "":
        return "-"

    # [COMANDO]: '//' hace división entera (cuántas horas completas).
    h = int(minutos_float // 60)
    # [COMANDO]: '%' devuelve el resto (los minutos que no llegaron a formar una hora).
    m = int(minutos_float % 60)
    # [COMANDO]: round() redondea para corregir la basura de la precisión flotante de Python.
    s = int(round((minutos_float * 60) % 60))

    if s == 60: s = 0; m += 1
    if m == 60: m = 0; h += 1

    # [COMANDO]: f"{x:02d}" interpola la variable 'x' forzando a que tenga al menos 2 dígitos (ej: 0 -> "00").
    return f"{h:02d}:{m:02d}:{s:02d}"


class ClienteSimpy:
    """
    [ALGORITMO]: Programación Orientada a Objetos (POO).
    [POR QUÉ]: En vez de tener 20 arrays sueltos rastreando la llegada, estado y fin de cada persona,
    creamos un objeto "Ficha" por cliente. Cuando el cliente se bloquea en una cola de SimPy,
    el objeto retiene sus atributos para que la grilla pueda imprimirlos.
    """

    def __init__(self, id_cliente, hora_llegada, slot):
        self.id = id_cliente
        self.llegada = hora_llegada
        self.slot = slot  # Índice de la columna visual que ocupará (0 a 19).
        self.estado = "En Cola"
        self.fin_lect = ""


def simular_sistema(params):
    # Diccionario para mantener los contadores acumulativos vivos durante toda la ejecución.
    estado = {
        'num_evento': 1, 'llegadas': 0, 'rechazos': 0, 'salidas': 0,
        'acum_permanencia': 0.0, 'leyendo': 0,
        'emp1': "Libre", 'fin_atenc_emp1': "",
        'emp2': "Libre", 'fin_atenc_emp2': "",
        'proxima_llegada': params['t_llegada']  # Arranca con la primera llegada programada
    }

    capacidad = params['capacidad']
    slots_clientes = [None] * capacidad  # [ALGORITMO]: Array de longitud fija para representar físicamente el local.

    datos_grilla = []  # Almacenará las tuplas finales que van a la UI Principal (Vector Estado).
    datos_euler = []  # [EULER AUDITORÍA]: Almacenará las iteraciones continuas paso a paso para la pestaña 2.

    # [COMANDO]: simpy.Environment() crea el "reloj global" y maneja la agenda de eventos ocultos.
    env = simpy.Environment()
    # [COMANDO]: simpy.Resource(capacity=2) crea una "ventanilla" con 2 empleados.
    # [POR QUÉ]: SimPy hace la lógica de la fila FIFO automáticamente sin que nosotros armemos listas (append/pop).
    empleados = simpy.Resource(env, capacity=2)

    # =========================================================================================
    # Variables para el Buffer de Instantes (Vector de Estado Estricto)
    # [POR QUÉ]: Si 3 eventos ocurren en el min 14:00, SimPy los procesa uno por uno.
    # Con este buffer acumulamos los 3, sacamos una sola "foto" de la RAM y la guardamos junta.
    # =========================================================================================
    buffer_reloj = -1.0
    buffer_fila = None

    def_rnds = {
        'rnd_tipo': "", 'tipo_atenc': "", 'rnd_atenc': "", 't_atenc': "",
        'rnd_queda': "", 'se_queda': "", 'rnd_pag': "", 'paginas': "",
        'k_aplicado': "", 't_lect': ""
    }

    def commitear_buffer_a_grilla(forzar=False):
        """
        Esta función agarra el buffer lleno (la suma de todos los eventos
        que ocurrieron en un mismo instante) y recién ahí genera la fila final para la grilla.
        """
        nonlocal buffer_fila
        if buffer_fila is None and not forzar: return

        # [ALGORITMO]: Filtro de Memoria O(1) (Parámetros i, j).
        if forzar or (buffer_reloj >= params['desde_reloj'] and len(datos_grilla) < params['filas_mostrar']):

            # Usamos el estado congelado en el snapshot (la última y definitiva foto del milisegundo)
            snap = buffer_fila['estado_snapshot'] if buffer_fila else estado

            acum_perm = round(snap.get('acum_permanencia', 0.0), 2)
            prom_perm = round((snap['acum_permanencia'] / snap['salidas']), 2) if snap.get('salidas', 0) > 0 else 0.0
            porc_rechazos = round((snap['rechazos'] / snap['llegadas']) * 100, 2) if snap.get('llegadas',
                                                                                              0) > 0 else 0.0

            rnds = buffer_fila['rnds'] if buffer_fila else def_rnds

            r_rnd_tipo = round(rnds['rnd_tipo'], 4) if isinstance(rnds['rnd_tipo'], float) else rnds['rnd_tipo']
            r_rnd_atenc = round(rnds['rnd_atenc'], 4) if isinstance(rnds['rnd_atenc'], float) else rnds['rnd_atenc']
            r_t_atenc = round(rnds['t_atenc'], 2) if isinstance(rnds['t_atenc'], float) else rnds['t_atenc']
            r_rnd_queda = round(rnds['rnd_queda'], 4) if isinstance(rnds['rnd_queda'], float) else rnds['rnd_queda']
            r_rnd_pag = round(rnds['rnd_pag'], 4) if isinstance(rnds['rnd_pag'], float) else rnds['rnd_pag']
            r_paginas = int(rnds['paginas']) if isinstance(rnds['paginas'], float) else rnds['paginas']
            r_t_lect = round(rnds['t_lect'], 2) if isinstance(rnds['t_lect'], float) else rnds['t_lect']

            # Formateo visual para Próxima Llegada y Fin de Atención
            p_llegada = snap.get('proxima_llegada', "")
            p_llegada_str = formato_hora(p_llegada) if isinstance(p_llegada, float) else p_llegada

            f_at1 = snap.get('fin_atenc_emp1', "")
            f_at1_str = formato_hora(f_at1) if isinstance(f_at1, float) else f_at1

            f_at2 = snap.get('fin_atenc_emp2', "")
            f_at2_str = formato_hora(f_at2) if isinstance(f_at2, float) else f_at2

            # Empaquetado dinámico de los slots usando el snapshot congelado
            datos_slots = []
            slots_congelados = snap.get('slots', [None] * capacidad)
            for s in slots_congelados:
                if s is None:
                    datos_slots.extend(["", "", "", ""])
                else:
                    datos_slots.extend([s[0], formato_hora(s[1]), s[2], s[3]])

            # ====================================================================================
            # [FILTRO ESTRICTO DE EVENTOS PRIMARIOS]: Lista blanca absoluta.
            # Solo permitimos en la columna de texto aquellos eventos que hacen saltar el reloj.
            # ====================================================================================
            if buffer_fila and not forzar:
                eventos_lista = buffer_fila['eventos']
                eventos_primarios = []

                for e in eventos_lista:
                    if "Llegada" in e or "Fin Atenc" in e or "Fin Lectura" in e:
                        eventos_primarios.append(e)

                if not eventos_primarios:
                    eventos_primarios = eventos_lista

                eventos_unidos = " + ".join(eventos_primarios)
            else:
                eventos_unidos = "FIN SIMULACIÓN"

                # [OCULTAR PRÓXIMA LLEGADA]: Limpiamos la hora en la última fila del sistema
                p_llegada_str = "-"

            fila = (
                       estado['num_evento'], eventos_unidos, formato_hora(buffer_reloj), p_llegada_str,
                       r_rnd_tipo, rnds['tipo_atenc'], r_rnd_atenc, r_t_atenc, r_rnd_queda, rnds['se_queda'],
                       r_rnd_pag, r_paginas, rnds['k_aplicado'], r_t_lect,
                       snap.get('emp1', "Libre"), f_at1_str, snap.get('emp2', "Libre"), f_at2_str,
                       snap.get('queue_len', 0), snap.get('leyendo', 0),
                       snap.get('llegadas', 0), snap.get('rechazos', 0), porc_rechazos, snap.get('salidas', 0),
                       acum_perm, prom_perm
                   ) + tuple(datos_slots)

            datos_grilla.append(fila)

        # Suma 1 al contador de eventos. El if not forzar está para que "FIN SIMULACIÓN" no gaste un número.
        if not forzar:
            estado['num_evento'] += 1

    def registrar_fila(evento_str, rnd_tipo="", tipo_atenc="", rnd_atenc="", t_atenc="", rnd_queda="", se_queda="",
                       rnd_pag="", paginas="", k_aplicado="", t_lect=""):
        """
        Acumula la info en el buffer,
        y hace 'commit' solo cuando el reloj de SimPy da el salto al próximo evento.
        """
        nonlocal buffer_reloj, buffer_fila
        reloj_actual = env.now

        # Si el reloj avanzó, significa que el instante temporal anterior ya terminó de procesar TODO. Commiteamos.
        if reloj_actual > buffer_reloj and buffer_fila is not None:
            commitear_buffer_a_grilla(forzar=False)
            buffer_fila = None  # Limpiamos el buffer para la nueva hora

        buffer_reloj = reloj_actual

        # Inicializamos el buffer para el nuevo instante si está vacío
        if buffer_fila is None:
            buffer_fila = {'eventos': [], 'rnds': def_rnds.copy(), 'estado_snapshot': {}}

        # Acumulamos el string del evento (para que queden sumados con un '+')
        buffer_fila['eventos'].append(evento_str)

        # Acumulamos las variables aleatorias sin borrar las que aportaron los eventos anteriores de este minuto
        if rnd_tipo != "": buffer_fila['rnds']['rnd_tipo'] = rnd_tipo
        if tipo_atenc != "": buffer_fila['rnds']['tipo_atenc'] = tipo_atenc
        if rnd_atenc != "": buffer_fila['rnds']['rnd_atenc'] = rnd_atenc
        if t_atenc != "": buffer_fila['rnds']['t_atenc'] = t_atenc
        if rnd_queda != "": buffer_fila['rnds']['rnd_queda'] = rnd_queda
        if se_queda != "": buffer_fila['rnds']['se_queda'] = se_queda
        if rnd_pag != "": buffer_fila['rnds']['rnd_pag'] = rnd_pag
        if paginas != "": buffer_fila['rnds']['paginas'] = paginas
        if k_aplicado != "": buffer_fila['rnds']['k_aplicado'] = k_aplicado
        if t_lect != "": buffer_fila['rnds']['t_lect'] = t_lect

        # Congelamos la foto del sistema al momento de este evento.
        buffer_fila['estado_snapshot'] = {
            'emp1': str(estado['emp1']), 'fin_atenc_emp1': estado['fin_atenc_emp1'],
            'emp2': str(estado['emp2']), 'fin_atenc_emp2': estado['fin_atenc_emp2'],
            'queue_len': len(empleados.queue),
            'leyendo': estado['leyendo'], 'llegadas': estado['llegadas'], 'rechazos': estado['rechazos'],
            'salidas': estado['salidas'], 'acum_permanencia': estado['acum_permanencia'],
            'proxima_llegada': estado['proxima_llegada'],
            'slots': [(s.id, s.llegada, s.estado, s.fin_lect) if s else None for s in slots_clientes]
        }

    def proceso_cliente(id_cliente):
        """
        [ALGORITMO]: Enfoque Orientado a Procesos (Generators en Python).
        [POR QUÉ]: A diferencia de un while que mueve el reloj minuto a minuto, este bloque
        describe la "vida" de 1 cliente. Se usa 'yield' para pausar la ejecución de esta
        función cuando el cliente debe esperar, dejando que otros procesos avancen.
        """
        # Modela la restricción física del sistema. Si la biblioteca (mostrador + cola + mesas de lectura)
        # llegó al tope de 20 personas, no podemos dejar que la variable entre al sistema porque desbordaría
        # la matriz visual. Al tirar un return, el cliente virtual "muere" y no consume más procesador.
        reloj_llegada = env.now

        # [COMANDO]: empleados.count (ocupados) + len(empleados.queue) (en fila FIFO oculta).
        personas_adentro = empleados.count + len(empleados.queue) + estado['leyendo']

        estado['llegadas'] += 1
        if personas_adentro >= capacidad:
            estado['rechazos'] += 1
            registrar_fila("Llegada (Rechazo)")
            return  # [COMANDO]: return corta la ejecución del proceso. El cliente no entra.

        # .index() busca la primera columna disponible en la UI.
        idx_vacio = slots_clientes.index(None)
        cliente = ClienteSimpy(id_cliente, reloj_llegada, idx_vacio)
        slots_clientes[idx_vacio] = cliente

        # [ALGORITMO]: Monte Carlo puro.
        # random.random() tira un número entre 0 y 0.999... y lo evaluamos contra las probabilidades acumuladas.
        rnd_t = random.random()
        if rnd_t < params['p_pedir']:
            tipo = "Pedir"
        elif rnd_t < (params['p_pedir'] + params['p_dev']):
            tipo = "Devolver"
        else:
            tipo = "Consultar"

        # ====================================================================================
        # El bloque "with" de petición ahora envuelve a la llegada.
        # Al pedir el recurso ANTES de registrar la fila, el cliente ingresa a la cola
        # matemática de SimPy al instante, solucionando el desfase numérico de la columna Q.
        # ====================================================================================
        with empleados.request() as peticion:

            # f"..." (f-string): Te permite inyectar variables de Python directamente adentro de un texto.
            cliente.estado = f"Fila ({tipo[:3]})"

            # Le avisa a la grilla que la fila que está por generar corresponde a una Llegada.
            registrar_fila(f"Llegada ({tipo})", rnd_tipo=rnd_t, tipo_atenc=tipo)

            # Si los dos empleados están ocupados atendiendo a otros clientes, SimPy frena la ejecución de
            # este cliente en esta línea exacta y lo mete en una lista de espera FIFO.
            yield peticion

            # Para SimPy, el recurso empleados es solo un contador abstracto.
            # Este bloque traduce la capacidad usando un "elif" estricto, para que Python asigne de manera
            # excluyente el puesto que realmente está vacío y no se pise.
            if estado['emp1'] == "Libre":
                estado['emp1'] = f"Ocup (ID {id_cliente})"
                id_emp = 1
            elif estado['emp2'] == "Libre":
                estado['emp2'] = f"Ocup (ID {id_cliente})"
                id_emp = 2
            else:
                id_emp = 1
                estado['emp1'] = f"Ocup (ID {id_cliente})"

            cliente.estado = f"Atend. ({tipo[:3]})"

            # implementación del tiempo de atención
            if tipo == "Pedir":
                rnd_a = random.random()
                # [ALGORITMO]: Transformada Inversa (Distribución Exponencial). F(x) = -Media * ln(1-RND)
                t_at = -params['m_pedir'] * math.log(1 - rnd_a)
            elif tipo == "Devolver":
                rnd_a = random.random()
                # [ALGORITMO]: Distribución Uniforme Continua. random.uniform() aplica la fórmula: a + RND * (b - a)
                t_at = params['u_dev_a'] + rnd_a * (params['u_dev_b'] - params['u_dev_a'])
            else:
                rnd_a = random.random()
                t_at = params['u_cons_a'] + rnd_a * (params['u_cons_b'] - params['u_cons_a'])

            # Calculamos el tiempo de fin de atención exacto para la matriz
            fin_at = env.now + t_at
            if id_emp == 1:
                estado['fin_atenc_emp1'] = fin_at
            else:
                estado['fin_atenc_emp2'] = fin_at

            registrar_fila(f"Inicia Atenc ({tipo})", rnd_atenc=rnd_a, t_atenc=t_at)

            # env.timeout(t_at) crea un evento retrasado programado para ejecutarse en el instante: Reloj Actual + t_at
            # Este es el comando que efectivamente "mueve" el reloj de la simulación.
            yield env.timeout(t_at)

            # Bloque de lógica condicional para asignación de variables de control internas (rnd_q, se_queda) y restauración del estado del empleado a "Libre".
            rnd_q = "";
            se_queda = ""
            if tipo == "Pedir":
                rnd_q = random.random()
                if rnd_q < params['p_queda']:
                    se_queda = "Sí"
                else:
                    se_queda = "No"

            if id_emp == 1:
                estado['emp1'] = "Libre"
                estado['fin_atenc_emp1'] = ""  # Blanqueamos el tiempo cuando termina.
            else:
                estado['emp2'] = "Libre"
                estado['fin_atenc_emp2'] = ""  # Blanqueamos el tiempo cuando termina.
            registrar_fila(f"Fin Atenc ({tipo})", rnd_queda=rnd_q, se_queda=se_queda)

        # Si entra acá, se sienta a leer.
        if tipo == "Pedir" and se_queda == "Sí":
            estado['leyendo'] += 1

            # [EULER LECTURA]: Generación de la variable continua
            rnd_p = random.random()
            paginas_target = params['u_pag_a'] + rnd_p * (params['u_pag_b'] - params['u_pag_a'])

            if paginas_target <= 200:
                k = params['k1']
            elif paginas_target <= 300:
                k = params['k2']
            else:
                k = params['k3']

            # --- ALGORITMO NUMÉRICO: EULER ---
            # Aproxima la integral avanzando en pasos "h" (parametrizables en la UI).
            es_auditable = (env.now >= params['desde_reloj'] and len(datos_grilla) < params['filas_mostrar'])

            h = params['h']
            t_euler = 0.0  # Unidades de integración transcurridas
            p_actual = 0.0  # Páginas leídas hasta el momento
            iteracion_euler = 1

            # [EULER AUDITORÍA]: Guardamos la Fila 0 (Condiciones Iniciales)
            if es_auditable:
                datos_euler.append((
                    f"ID {id_cliente} - Lectura", iteracion_euler, formato_hora(env.now),
                    f"Meta: {int(paginas_target)} Pág", round(t_euler, 4), round(p_actual, 4), "-"
                ))
                iteracion_euler += 1

            while p_actual < paginas_target:
                dp_dt = k / 5.0  # La derivada dada por la cátedra
                p_siguiente = p_actual + h * dp_dt

                # [EULER AUDITORÍA]: Guardamos cada paso de lectura
                if es_auditable:
                    datos_euler.append((
                        f"ID {id_cliente} - Lectura", iteracion_euler, formato_hora(env.now),
                        "Integración", round(t_euler, 4), round(p_actual, 4), round(dp_dt, 4)
                    ))
                    iteracion_euler += 1

                p_actual = p_siguiente
                t_euler += h

            # [EULER AUDITORÍA]: Guardamos la fila final de lectura
            if es_auditable:
                datos_euler.append((
                    f"ID {id_cliente} - Lectura", iteracion_euler, formato_hora(env.now),
                    "Meta Cumplida", round(t_euler, 4), round(p_actual, 4), f"P >= {int(paginas_target)}", "-"
                ))

            # Convierte el resultado final matemático a tiempo físico real (minutos)
            t_lect = t_euler * 10.0

            # Configura el inicio del estado de lectura. Al registrar la fila, se vuelcan en la grilla visual los datos
            # analíticos del libro (páginas, constante $K$ y tiempo calculado).
            cliente.fin_lect = formato_hora(env.now + t_lect)
            cliente.estado = "Leyendo"
            registrar_fila("Inicia Lectura", rnd_pag=rnd_p, paginas=paginas_target, k_aplicado=k, t_lect=t_lect)

            yield env.timeout(t_lect)

            # Cuando el yield anterior expira, el cliente "despierta". Físicamente se levantó de la silla de lectura.
            estado['leyendo'] -= 1
            cliente.fin_lect = ""
            registrar_fila("Fin Lectura")

            # Este bloque resuelve la regla de negocio que dicta que un lector no puede irse sin devolver el libro en ventanilla.
            with empleados.request() as req_dev:

                cliente.estado = "Fila (Dev)"
                registrar_fila("Pasa a Fila (Dev)")

                yield req_dev

                if estado['emp1'] == "Libre":
                    estado['emp1'] = f"Ocup (ID {id_cliente})"
                    id_emp = 1
                elif estado['emp2'] == "Libre":
                    estado['emp2'] = f"Ocup (ID {id_cliente})"
                    id_emp = 2
                else:
                    id_emp = 1
                    estado['emp1'] = f"Ocup (ID {id_cliente})"

                cliente.estado = "Atend. (Dev)"

                rnd_a2 = random.random()
                t_at2 = params['u_dev_a'] + rnd_a2 * (params['u_dev_b'] - params['u_dev_a'])

                # Calculamos el tiempo de fin de atención para la etapa Post-Lectura
                fin_at2_total = env.now + t_at2
                if id_emp == 1:
                    estado['fin_atenc_emp1'] = fin_at2_total
                else:
                    estado['fin_atenc_emp2'] = fin_at2_total

                registrar_fila("Inicia Atenc (Dev Post-Lect)", rnd_atenc=rnd_a2, t_atenc=t_at2)

                yield env.timeout(t_at2)

                if id_emp == 1:
                    estado['emp1'] = "Libre"
                    estado['fin_atenc_emp1'] = ""
                else:
                    estado['emp2'] = "Libre"
                    estado['fin_atenc_emp2'] = ""
                registrar_fila("Fin Atenc (Post-Lect)")

        # calculos de metricas en la "destrucción" de un cliente
        estado['salidas'] += 1
        estado['acum_permanencia'] += (env.now - reloj_llegada)
        slots_clientes[cliente.slot] = None  # Libera visualmente el espacio fisico para otra persona
        registrar_fila("Sale Sistema")

    def generador_llegadas():
        """
        [ALGORITMO]: Fábrica infinita de clientes.
        [POR QUÉ]: Mantiene el sistema alimentado de entidades. Llama a un cliente, se frena 4 minutos,
        llama a otro, y así sucesivamente.
        """
        id_gen = 1
        # El while es un ciclo que valida dos condiciones de corte de la rúbrica.
        while env.now <= params['tiempo_simulacion'] and id_gen <= params['limite_iteraciones']:
            # Calculamos y guardamos la próxima llegada ANTES de lanzar al cliente,
            estado['proxima_llegada'] = env.now + params['t_llegada']

            # [COMANDO]: env.process() inyecta la función cliente como un hilo independiente.
            env.process(proceso_cliente(id_gen))
            id_gen += 1
            yield env.timeout(params['t_llegada'])

    # Registramos la fábrica y encendemos el motor de SimPy.
    env.process(generador_llegadas())
    # [COMANDO]: env.run(until=X) corre el reloj saltando evento por evento hasta tocar el límite X.
    env.run(until=params['tiempo_simulacion'])

    # [NUEVA ARQUITECTURA]: Forzamos la captura visual del instante final.
    commitear_buffer_a_grilla(forzar=True)

    # Armado estático de los encabezados de la tabla principal
    columnas_base = [
        "N° Evento", "Evento", "Reloj", "Próx Llegada",
        "RND Tipo", "Tipo Atenc (RND)", "RND Atenc", "T. Atenc", "RND Queda", "¿Se Queda?",
        "RND Pág", "Páginas", "Valor K", "T. Lectura (min)",
        "Emp 1", "Fin Atenc 1", "Emp 2", "Fin Atenc 2", "Cola (Q)", "Leyendo (Q)",
        "Llegadas", "Rechazos", "% Rechazos", "Salidas", "Acum Perm", "Prom Perm"
    ]

    # Armado estático de los encabezados de la tabla secundaria (Euler)
    # [EULER AUDITORÍA]: Cabeceras para la pestaña 2
    columnas_euler = [
        "Entidad - Integración", "Iteración", "Reloj Sistema", "Estado Método",
        "Var. Tiempo (t)", "Var. Acumuladora (P)", "Derivada (dP/dt)"
    ]

    columnas_slots = []
    for c in range(capacidad):
        columnas_slots.extend([f"C{c + 1}_ID", f"C{c + 1}_Lleg", f"C{c + 1}_Est", f"C{c + 1}_FinLect"])

    columnas_principal = tuple(columnas_base + columnas_slots)

    p_rech = (estado['rechazos'] / estado['llegadas']) * 100 if estado['llegadas'] > 0 else 0
    p_perm = (estado['acum_permanencia'] / estado['salidas']) if estado['salidas'] > 0 else 0

    return columnas_principal, datos_grilla, columnas_euler, datos_euler, p_rech, p_perm


# ==========================================
# 2. INTERFAZ GRÁFICA (FRONTEND)
# ==========================================

class VentanaSimulacion:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador Eventos Discretos UTN - Frontend Tkinter + SimPy + Euler")
        self.root.geometry("1500x800")

        self.vars = {}
        self.construir_panel_parametros()

        self.panel_res = ttk.Frame(self.root, padding=5)
        self.panel_res.pack(fill=tk.X)

        self.lbl_res1 = ttk.Label(self.panel_res, text="Esperando ejecución...", font=("Arial", 11, "bold"))
        self.lbl_res1.pack()
        self.lbl_res2 = ttk.Label(self.panel_res, text="")
        self.lbl_res2.pack()

        # =========================================================================
        # [NUEVA PESTAÑA]: Implementación del Notebook (Pestañas en Tkinter)
        # =========================================================================
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # ---- Pestaña 1: Vector de Estado ----
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text="Vector de Estado Principal")

        self.scroll_y_1 = ttk.Scrollbar(self.tab1, orient=tk.VERTICAL)
        self.scroll_x_1 = ttk.Scrollbar(self.tab1, orient=tk.HORIZONTAL)

        self.tree_principal = ttk.Treeview(self.tab1, show="headings",
                                           yscrollcommand=self.scroll_y_1.set,
                                           xscrollcommand=self.scroll_x_1.set, selectmode="extended")

        self.scroll_y_1.config(command=self.tree_principal.yview)
        self.scroll_x_1.config(command=self.tree_principal.xview)

        self.scroll_y_1.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_x_1.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree_principal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ---- Pestaña 2: Auditoría Euler ----
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text="Auditoría Ecuaciones Euler")

        self.scroll_y_2 = ttk.Scrollbar(self.tab2, orient=tk.VERTICAL)

        self.tree_euler = ttk.Treeview(self.tab2, show="headings",
                                       yscrollcommand=self.scroll_y_2.set, selectmode="extended")

        self.scroll_y_2.config(command=self.tree_euler.yview)
        self.scroll_y_2.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_euler.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bindings globales
        self.root.bind("<Control-a>", self.seleccionar_todo)
        self.root.bind("<Control-c>", self.copiar_a_excel)

        ttk.Label(self.root,
                  text="Atajos: Seleccioná las filas de la tabla activa (o Ctrl+A) y presioná Ctrl+C para llevarlas a Excel").pack(
            side=tk.BOTTOM)

    def construir_panel_parametros(self):
        panel = ttk.LabelFrame(self.root, text="Panel de Parámetros y Validaciones", padding=10)
        panel.pack(fill=tk.X, padx=10, pady=5)

        configs = [
            ("Lógica de Corte y Visual.", [
                ("Max. Llegadas (N)", "limite_iteraciones", 100000),
                ("Simular hasta min. (X)", "tiempo_simulacion", 100000),
                ("Mostrar desde min. (j)", "desde_reloj", 0),
                ("Cant. filas a mostrar (i)", "filas_mostrar", 100),
                ("Capacidad Max", "capacidad", 20),
                ("Paso Euler (h)", "h", 0.1)
            ]),
            ("Probabilidades (%)", [
                ("% Pedir Libro", "prob_pedir", 45),
                ("% Devolver Libro", "prob_devolver", 45),
                ("% Consultar", "prob_consultar", 10),
                ("% Se Queda a Leer", "prob_queda", 40),
                ("Llegadas (Cte)", "t_llegada", 4.0)
            ]),
            ("Tiempos de Atención (min)", [
                ("Media Pedir Exp(-)", "media_pedir", 6.0),
                ("Unif. Dev A", "unif_dev_a", 1.5),
                ("Unif. Dev B", "unif_dev_b", 2.5),
                ("Unif. Cons A", "unif_cons_a", 2.0),
                ("Unif. Cons B", "unif_cons_b", 5.0),
                ("Unif. Pág A", "unif_pag_a", 100),
                ("Unif. Pág B", "unif_pag_b", 350),
            ]),
            ("Constantes Integración K", [
                ("K (Pág < 200)", "k1", 100),
                ("K (Pág < 300)", "k2", 90),
                ("K (Pág >= 300)", "k3", 70)
            ])
        ]

        col_offset = 0
        for seccion, campos in configs:
            ttk.Label(panel, text=seccion, font=("Arial", 9, "bold"), foreground="darkblue").grid(row=0,
                                                                                                  column=col_offset,
                                                                                                  columnspan=2, pady=2)
            row_idx = 1
            for label_text, var_name, default_val in campos:
                ttk.Label(panel, text=label_text).grid(row=row_idx, column=col_offset, sticky=tk.W, padx=5)
                entry = ttk.Entry(panel, width=8)
                entry.insert(0, str(default_val))
                entry.grid(row=row_idx, column=col_offset + 1, padx=5, pady=2)
                self.vars[var_name] = entry
                row_idx += 1
            col_offset += 2

        btn_frame = ttk.Frame(panel)
        btn_frame.grid(row=1, column=col_offset, rowspan=5, padx=20)
        ttk.Button(btn_frame, text="▶ INICIAR MOTOR SIMPY", command=self.ejecutar_simulacion, width=25).pack(ipady=10)

    def obtener_parametros(self):
        try:
            tiempo_simulacion = float(self.vars['tiempo_simulacion'].get())
            limite_iteraciones = int(self.vars['limite_iteraciones'].get())
            desde_reloj = float(self.vars['desde_reloj'].get())
            filas_mostrar = int(self.vars['filas_mostrar'].get())
            h = float(self.vars['h'].get())
            capacidad = int(self.vars['capacidad'].get())
            t_llegada = float(self.vars['t_llegada'].get())
            p_pedir = float(self.vars['prob_pedir'].get())
            p_dev = float(self.vars['prob_devolver'].get())
            p_cons = float(self.vars['prob_consultar'].get())
            p_queda = float(self.vars['prob_queda'].get())
            m_pedir = float(self.vars['media_pedir'].get())
            u_dev_a = float(self.vars['unif_dev_a'].get())
            u_dev_b = float(self.vars['unif_dev_b'].get())
            u_cons_a = float(self.vars['unif_cons_a'].get())
            u_cons_b = float(self.vars['unif_cons_b'].get())
            u_pag_a = float(self.vars['unif_pag_a'].get())
            u_pag_b = float(self.vars['unif_pag_b'].get())
            k1 = float(self.vars['k1'].get())
            k2 = float(self.vars['k2'].get())
            k3 = float(self.vars['k3'].get())
        except ValueError:
            messagebox.showerror("Error", "Ingresaste texto donde va un número.")
            return None

        errores = []

        if tiempo_simulacion <= 0:
            errores.append("X (tiempo a simular) debe ser > 0.")
        if limite_iteraciones <= 0:
            errores.append("N (máx. llegadas) debe ser > 0.")
        if filas_mostrar <= 0:
            errores.append("i (cant. filas a mostrar) debe ser > 0.")
        if desde_reloj < 0:
            errores.append("j (mostrar desde min.) debe ser >= 0.")
        if desde_reloj >= tiempo_simulacion:
            errores.append("j (mostrar desde min.) debe ser menor que X (tiempo a simular).")
        if h <= 0:
            errores.append("h (paso Euler) debe ser > 0.")
        if capacidad <= 0:
            errores.append("Capacidad máxima debe ser > 0.")
        if t_llegada <= 0:
            errores.append("Llegadas (Cte) debe ser > 0.")
        if abs(p_pedir + p_dev + p_cons - 100.0) > 0.01:
            errores.append("Las probabilidades (% Pedir + % Devolver + % Consultar) deben sumar exactamente 100%.")
        if not (0 <= p_queda <= 100):
            errores.append("% Se Queda a Leer debe estar entre 0% y 100%.")
        if m_pedir <= 0:
            errores.append("Media Pedir Exp(-) debe ser > 0.")
        if u_dev_a >= u_dev_b:
            errores.append("Unif. Dev: A debe ser menor que B.")
        if u_cons_a >= u_cons_b:
            errores.append("Unif. Cons: A debe ser menor que B.")
        if u_pag_a >= u_pag_b:
            errores.append("Unif. Pág: A debe ser menor que B.")
        if k1 <= 0:
            errores.append("K (Pág < 200) debe ser > 0.")
        if k2 <= 0:
            errores.append("K (Pág < 300) debe ser > 0.")
        if k3 <= 0:
            errores.append("K (Pág >= 300) debe ser > 0.")

        if errores:
            messagebox.showerror("Error de validación", "\n".join(errores))
            return None

        return {
            'tiempo_simulacion': tiempo_simulacion,
            'limite_iteraciones': limite_iteraciones,
            'desde_reloj': desde_reloj,
            'filas_mostrar': filas_mostrar,
            'h': h,
            'capacidad': capacidad,
            't_llegada': t_llegada,
            'p_pedir': p_pedir / 100.0,
            'p_dev': p_dev / 100.0,
            'p_queda': p_queda / 100.0,
            'm_pedir': m_pedir,
            'u_dev_a': u_dev_a,
            'u_dev_b': u_dev_b,
            'u_cons_a': u_cons_a,
            'u_cons_b': u_cons_b,
            'u_pag_a': u_pag_a,
            'u_pag_b': u_pag_b,
            'k1': k1,
            'k2': k2,
            'k3': k3
        }

    def ejecutar_simulacion(self):
        params = self.obtener_parametros()
        if not params: return

        self.lbl_res1.config(text="Procesando simulación híbrida (SimPy + Euler + Snapshot)...")
        self.root.update()

        # Recibimos también las columnas y datos de la tabla de Euler
        cols_prin, datos_prin, cols_eul, datos_eul, p_rechazos, p_permanencia = simular_sistema(params)

        self.lbl_res1.config(
            text=f"Promedio de permanencia: {p_permanencia:.2f} min | Filas Vector Estado: {len(datos_prin)} | Filas Euler: {len(datos_eul)}")
        self.lbl_res2.config(text=f"Porcentaje de rechazos global (Fin Simulación): {p_rechazos:.2f}%")

        # ---- Carga Tabla Principal (Pestaña 1) ----
        self.tree_principal.delete(*self.tree_principal.get_children())
        self.tree_principal["columns"] = cols_prin

        for col in cols_prin:
            self.tree_principal.heading(col, text=col)
            if "_ID" in col:
                w = 40
            elif "Emp" in col:
                w = 110
            elif "Fin Atenc" in col:
                w = 85
            elif "Próx Llegada" in col:
                w = 85
            elif "Fila" in col or "Leyendo" in col or "Cola" in col:
                w = 60
            elif "% Rech" in col:
                w = 85
            elif "Acum Perm" in col:
                w = 85
            elif "Evento" in col:
                w = 320
            elif "RND" in col:
                w = 70
            elif "Tipo Atenc" in col:
                w = 100
            elif "T. Atenc" in col:
                w = 70
            elif "¿Se Queda?" in col:
                w = 75
            elif "Páginas" in col or "Valor K" in col:
                w = 65
            elif "T. Lectura" in col:
                w = 75
            else:
                w = 80
            self.tree_principal.column(col, width=w, anchor=tk.CENTER, stretch=False)

        for fila in datos_prin: self.tree_principal.insert("", tk.END, values=fila)

        # ---- Carga Tabla Euler (Pestaña 2) ----
        self.tree_euler.delete(*self.tree_euler.get_children())
        self.tree_euler["columns"] = cols_eul

        for col in cols_eul:
            self.tree_euler.heading(col, text=col)
            if "Entidad" in col:
                w = 180
            elif "Iteración" in col:
                w = 80
            elif "Reloj" in col:
                w = 100
            elif "Estado" in col:
                w = 130
            else:
                w = 120
            self.tree_euler.column(col, width=w, anchor=tk.CENTER, stretch=False)

        for fila in datos_eul: self.tree_euler.insert("", tk.END, values=fila)

    def seleccionar_todo(self, event):
        # Ahora selecciona la tabla que esté actualmente visible en la pestaña activa
        tab_id = self.notebook.select()
        if self.notebook.index(tab_id) == 0:
            self.tree_principal.selection_set(self.tree_principal.get_children())
        else:
            self.tree_euler.selection_set(self.tree_euler.get_children())
        return "break"

    def copiar_a_excel(self, event):
        # Copia al portapapeles los datos de la pestaña que tengas abierta
        tab_id = self.notebook.select()
        tree_activo = self.tree_principal if self.notebook.index(tab_id) == 0 else self.tree_euler

        seleccion = tree_activo.selection()
        if not seleccion: seleccion = tree_activo.get_children()

        texto = "\t".join([tree_activo.heading(c)["text"] for c in tree_activo["columns"]]) + "\n"
        for item in seleccion: texto += "\t".join(str(v) for v in tree_activo.item(item, "values")) + "\n"

        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self.root.update()

        titulo = self.root.title()
        self.root.title("¡Filas copiadas! Listas para pegar en Excel (Ctrl+V)")
        self.root.after(2000, lambda: self.root.title(titulo))

        return "break"


# ==========================================
# PUNTO DE ENTRADA AL PROGRAMA
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()  # Levanta el lienzo gráfico interactuando con Windows/OS.
    app = VentanaSimulacion(root)
    root.mainloop()  # Atrapa el programa en un loop infinito para que la ventana no se cierre sola.