# =============================================================
# SIMULADOR DE EVENTOS DISCRETOS - BIBLIOTECA
# Motor: SimPy (backend estadístico) + Tkinter (frontend visual)
# =============================================================
#"pip install "simpy" o "python -m pip install simpy" para poder correr

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
        'acum_permanencia': 0.0, 'leyendo': 0, 'emp1': "Libre", 'emp2': "Libre"
    }

    capacidad = params['capacidad']
    slots_clientes = [None] * capacidad  # [ALGORITMO]: Array de longitud fija para representar físicamente el local.
    datos_grilla = []  # Almacenará las tuplas finales que van a la UI Principal.

    # [COMANDO]: simpy.Environment() crea el "reloj global" y maneja la agenda de eventos ocultos.
    env = simpy.Environment()
    # [COMANDO]: simpy.Resource(capacity=2) crea una "ventanilla" con 2 empleados.
    # [POR QUÉ]: SimPy hace la lógica de la fila FIFO automáticamente sin que nosotros armemos listas (append/pop).
    empleados = simpy.Resource(env, capacity=2)

    def registrar_fila(evento_str, rnd_tipo="", tipo_atenc="", rnd_atenc="", t_atenc="", rnd_queda="", se_queda="",
                       rnd_pag="", paginas="", k_aplicado="", t_lect="", forzar=False):
        """
        [ALGORITMO]: "Snapshot" o auditoría del sistema con AGRUPACIÓN POR INSTANTE.
        """
        reloj = env.now  # Obtiene el minuto exacto actual.

        if forzar or (reloj >= params['desde_reloj'] and len(datos_grilla) < params['filas_mostrar']):
            prom_perm = round((estado['acum_permanencia'] / estado['salidas']), 2) if estado['salidas'] > 0 else 0.0
            porc_rechazos = round((estado['rechazos'] / estado['llegadas']) * 100, 2) if estado['llegadas'] > 0 else 0.0

            r_rnd_tipo = round(rnd_tipo, 4) if isinstance(rnd_tipo, float) else rnd_tipo
            r_rnd_atenc = round(rnd_atenc, 4) if isinstance(rnd_atenc, float) else rnd_atenc
            r_t_atenc = round(t_atenc, 2) if isinstance(t_atenc, float) else t_atenc
            r_rnd_queda = round(rnd_queda, 4) if isinstance(rnd_queda, float) else rnd_queda
            r_rnd_pag = round(rnd_pag, 4) if isinstance(rnd_pag, float) else rnd_pag
            r_paginas = int(paginas) if isinstance(paginas, float) else paginas
            r_t_lect = round(t_lect, 2) if isinstance(t_lect, float) else t_lect

            datos_slots = []
            for s in slots_clientes:
                if s is None:
                    datos_slots.extend(["", "", "", ""])
                else:
                    datos_slots.extend([s.id, formato_hora(s.llegada), s.estado, s.fin_lect])

            # Creamos la fila "candidata" con los datos más actualizados
            fila = (
                       estado['num_evento'], evento_str, formato_hora(reloj),
                       r_rnd_tipo, tipo_atenc, r_rnd_atenc, r_t_atenc, r_rnd_queda, se_queda,
                       r_rnd_pag, r_paginas, k_aplicado, r_t_lect,
                       estado['emp1'], estado['emp2'], len(empleados.queue), estado['leyendo'],
                       estado['llegadas'], estado['rechazos'], porc_rechazos, estado['salidas'], prom_perm
                   ) + tuple(datos_slots)

            # =========================================================================
            # [NUEVA LÓGICA]: COMBINADOR DE EVENTOS SIMULTÁNEOS (Pedido del Profesor)
            # =========================================================================
            hora_actual_str = formato_hora(reloj)

            # Comparamos si el reloj de esta fila es idéntico al de la última fila guardada
            if len(datos_grilla) > 0 and datos_grilla[-1][2] == hora_actual_str and not forzar:

                # 1. Recuperamos la fila anterior para fusionarla
                ultima_fila = datos_grilla[-1]
                fila_lista = list(fila)

                # 2. Mantenemos el N° de Evento original (para que no salte)
                fila_lista[0] = ultima_fila[0]

                # 3. Concatenamos los nombres de los eventos (Ej: "Llegada (Ped) + Inicia Atenc")
                fila_lista[1] = ultima_fila[1] + " + " + fila_lista[1]

                # 4. Rescatamos los RNDs: Si la fila nueva no trajo un RND (porque es el evento
                # de inicio de atención), rescatamos el RND de la llegada que estaba en la fila vieja.
                # (Las columnas del 3 al 12 son estrictamente las de las variables aleatorias)
                for i in range(3, 13):
                    if (fila_lista[i] == "" or fila_lista[i] == "-") and ultima_fila[i] != "" and ultima_fila[i] != "-":
                        fila_lista[i] = ultima_fila[i]

                # 5. Las columnas de Estado (Empleados, Colas, Contadores y Clientes) no se rescatan,
                # se dejan las de la nueva 'fila' porque representan la foto final actualizada de ese instante.

                # 6. Sobrescribimos la última fila en la grilla en lugar de hacer .append()
                datos_grilla[-1] = tuple(fila_lista)

            else:
                # Si el reloj sí avanzó un minuto distinto, guardamos una fila totalmente nueva normal
                datos_grilla.append(fila)
                if not forzar:
                    estado['num_evento'] += 1

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
        # env.now: Es una propiedad del entorno de SimPy que devuelve un número flotante con el minuto exacto actual de la simulación.
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

        # f"..." (f-string): Te permite inyectar variables de Python directamente adentro de un texto usando llaves {}.[:3] (Slicing):
        # Es una herramienta nativa de Python para recortar cadenas de texto (strings). Le dice al programa: "agarrá la palabra guardada en
        # la variable tipo y traeme solo desde el inicio hasta la posición 3".
        cliente.estado = f"Fila ({tipo[:3]})"
        # Le avisa a la grilla que la fila que está por generar corresponde al evento "Llegada (Pedir)" o "Llegada (Consultar)
        # Al pasarle rnd_tipo=rnd_t y tipo_atenc=tipo, le estás entregando a la grilla el número aleatorio exacto que sorteaste renglones más arriba y su resultado.
        registrar_fila(f"Llegada ({tipo})", rnd_tipo=rnd_t, tipo_atenc=tipo)

        # empleados.request() genera un evento de solicitud sobre el objeto Resource (que tiene capacidad = 2). La cláusula with ... as
        # peticion es un Gestor de Contexto (Context Manager); su función principal es asegurar que el empleado se asigne al entrar al bloque
        # y se libere automáticamente apenas el código salga de la sangría, pase lo que pase.
        # Aquí se activa el mecanismo de Lógica de Eventos Discretos. El comando yield peticion convierte a la función en un generador pausable.
        # Si los dos empleados están ocupados atendiendo a otros clientes, SimPy frena la ejecución de
        # este cliente en esta línea exacta y lo mete en una lista de espera FIFO (empleados.queue).
        # El proceso queda "suspendido en el tiempo" sin consumir ciclos de CPU de forma redundante.
        # Cuando un empleado se desocupa, el motor de SimPy busca al cliente más antiguo de la cola y lo "despierta" para que continúe a la línea siguiente.
        with empleados.request() as peticion:

            yield peticion
            # Para SimPy, el recurso empleados es solo un contador abstracto (sabe que hay 2 unidades de capacidad, pero no les pone nombre).
            # Sin embargo, el esquema del Vector de Estado tradicional exige identificar exactamente qué puesto está ocupado y por quién. Este bloque
            # traduce la capacidad abstracta de SimPy en "Empleado 1" o "Empleado 2" para que la grilla visual muestre correctamente quién está atendiendo a quién.
            if estado['emp1'] == "Libre":
                estado['emp1'] = f"Ocup (ID {id_cliente})";
                id_emp = 1
            else:
                estado['emp2'] = f"Ocup (ID {id_cliente})";
                id_emp = 2

            cliente.estado = f"Atend. (E{id_emp})"

            # implementación del tiempo de atención
            rnd_a = random.random()
            if tipo == "Pedir":
                # [ALGORITMO]: Transformada Inversa (Distribución Exponencial). F(x) = -Media * ln(1-RND)
                t_at = -params['m_pedir'] * math.log(1 - rnd_a)
            elif tipo == "Devolver":
                # [ALGORITMO]: Distribución Uniforme Continua. random.uniform() aplica la fórmula: a + RND * (b - a)
                t_at = params['u_dev_a'] + rnd_a * (params['u_dev_b'] - params['u_dev_a'])
            else:
                t_at = params['u_cons_a'] + rnd_a * (params['u_cons_b'] - params['u_cons_a'])

            registrar_fila(f"Inicia Atenc ({tipo})", rnd_atenc=rnd_a, t_atenc=t_at)

            # env.timeout(t_at) crea un evento retrasado programado para ejecutarse en el instante: Reloj Actual + t_at
            # Este es el comando que efectivamente "mueve" el reloj de la simulación. El proceso de este cliente específico
            # se congela durante los minutos que dio el mostrador (t_at). Mientras este cliente está congelado en su atención,
            # el motor de SimPy aprovecha para procesar otros eventos del sistema (como la llegada de nuevos clientes o la
            # salida de lectores) que ocurran dentro de ese intervalo de tiempo.
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
            else:
                estado['emp2'] = "Libre"
            registrar_fila(f"Fin Atenc ({tipo})", rnd_queda=rnd_q, se_queda=se_queda)

        # Si entra acá, se sienta a leer.
        if tipo == "Pedir" and se_queda == "Sí":
            estado['leyendo'] += 1

            # [EULER]: Generación de la variable continua
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
            h = params['h']
            t_euler = 0.0  # Unidades de integración transcurridas
            p_actual = 0.0  # Páginas leídas hasta el momento

            while p_actual < paginas_target:
                dp_dt = k / 5.0  # La derivada dada por la cátedra
                p_siguiente = p_actual + h * dp_dt
                p_actual = p_siguiente
                t_euler += h

            # Convierte el resultado final matemático (unidades de integración) a tiempo físico real (minutos)
            t_lect = t_euler * 10.0

            # Configura el inicio del estado de lectura. Al registrar la fila, se vuelcan en la grilla visual los datos
            # analíticos del libro (páginas, constante $K$ y tiempo calculado). El comando yield le avisa a SimPy que
            # este proceso no interactúa con nadie más ni consume empleados mientras lee; simplemente "duerme" hasta que el reloj alcance el tiempo estipulado.
            cliente.fin_lect = formato_hora(env.now + t_lect)
            cliente.estado = "Leyendo"
            registrar_fila("Inicia Lectura", rnd_pag=rnd_p, paginas=paginas_target, k_aplicado=k, t_lect=t_lect)

            yield env.timeout(t_lect)

            # Cuando el yield anterior expira, el cliente "despierta". Físicamente se levantó de la silla de lectura. Es crítico poner cliente.fin_lect = "" porque, de
            # lo contrario, cuando el cliente pase a la fila del mostrador, la columna de la grilla visual seguiría mostrando una hora de lectura vieja, provocando un
            # error de consistencia visual. El evento registrado es "Fin Lectura".
            estado['leyendo'] -= 1
            cliente.fin_lect = ""
            registrar_fila("Fin Lectura")

            cliente.estado = "Fila (Dev)"
            # Este bloque resuelve la regla de negocio que dicta que un lector no puede irse sin devolver el libro en ventanilla. El proceso
            # vuelve a competir por un empleado en igualdad de condiciones con los clientes que recién entran de la calle. Si los empleados están
            # ocupados con trámites de consulta o pedidos, yield req_dev obligará a este lector a esperar en la cola FIFO. Una vez atendido,
            # bloquea el recurso por un tiempo uniforme t_at2 y finalmente lo libera.
            with empleados.request() as req_dev:
                yield req_dev

                if estado['emp1'] == "Libre":
                    estado['emp1'] = f"Ocup (ID {id_cliente})";
                    id_emp = 1
                else:
                    estado['emp2'] = f"Ocup (ID {id_cliente})";
                    id_emp = 2
                cliente.estado = "Atend. (Dev)"

                rnd_a2 = random.random()
                t_at2 = params['u_dev_a'] + rnd_a2 * (params['u_dev_b'] - params['u_dev_a'])
                registrar_fila("Inicia Atenc (Dev Post-Lect)", rnd_atenc=rnd_a2, t_atenc=t_at2)
                yield env.timeout(t_at2)

                if id_emp == 1:
                    estado['emp1'] = "Libre"
                else:
                    estado['emp2'] = "Libre"
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
        # El while es un ciclo que valida dos condiciones de corte de la rúbrica: que no nos hayamos pasado del tiempo X (tiempo_simulacion) y
        # que no hayamos excedido la cantidad de llegadas N (limite_iteraciones).env.process(...): Agarra la función proceso_cliente, le pasa el
        # id_gen (ej: Cliente 1, Cliente 2) y la "suelta" en el entorno de SimPy para que empiece a vivir su propia vida en paralelo.yield env.timeout(...):
        # Hace el checkpoint y pausa exclusivamente a esta fábrica.
        while env.now <= params['tiempo_simulacion'] and id_gen <= params['limite_iteraciones']:
            # [COMANDO]: env.process() inyecta la función cliente como un hilo independiente.
            env.process(proceso_cliente(id_gen))
            id_gen += 1
            yield env.timeout(params['t_llegada'])

    # Registramos la fábrica y encendemos el motor de SimPy.
    env.process(generador_llegadas())
    # [COMANDO]: env.run(until=X) corre el reloj saltando evento por evento hasta tocar el límite X.
    # env.run bloquea el código de Python. Tu programa se va a quedar clavado en esta línea calculando absolutamente
    # todas las iteraciones, sorteando todos los RNDs y haciendo saltar el reloj desde 0 hasta el tiempo máximo (ej. 100.000).
    # El programa recién va a pasar a la siguiente línea de código cuando el reloj de SimPy alcance ese tope.
    env.run(until=params['tiempo_simulacion'])

    # Forzamos la captura visual del instante final, exigido por la rúbrica.
    registrar_fila("FIN SIMULACIÓN", forzar=True)

    # Armado estático de los encabezados de la tabla
    columnas_base = [
        "N° Evento", "Evento", "Reloj",
        "RND Tipo", "Tipo Atenc (RND)", "RND Atenc", "T. Atenc", "RND Queda", "¿Se Queda?",
        "RND Pág", "Páginas", "Valor K", "T. Lectura (min)",
        "Emp 1", "Emp 2", "Cola (Q)", "Leyendo (Q)",
        "Llegadas", "Rechazos", "% Rechazos", "Salidas", "Prom Perm"
    ]

    # En lugar de escribir a mano las cabeceras para 20 clientes (ej: "C1_ID", "C1_Lleg", "C2_ID"... y así hasta 20),
    # este bucle for lee la capacidad máxima del sistema y genera automáticamente los 4 títulos necesarios
    # para cada espacio. Si mañana te piden que la biblioteca tenga capacidad para 50 personas, el código se adapta
    # solo sin que tengas que agregar 120 columnas a mano.
    # [COMANDO] f"..." (f-strings): Permite inyectar variables matemáticas dentro de un texto.
    # Como c arranca en 0, usa {c + 1} para que visualmente la primera columna se llame "C1" y no "C0".
    columnas_slots = []
    for c in range(capacidad):
        columnas_slots.extend([f"C{c + 1}_ID", f"C{c + 1}_Lleg", f"C{c + 1}_Est", f"C{c + 1}_FinLect"])

    # Fusión de Listas: Agarra la lista de cabeceras estáticas (Reloj, Evento, Emp 1, etc.) y le pega
    # al final la lista gigante de cabeceras dinámicas de clientes que acabamos de generar arriba.
    columnas_principal = tuple(columnas_base + columnas_slots)

    # Cálculos Finales (KPIs): Calcula el Porcentaje de Rechazos y el Promedio de Permanencia de toda la simulación.
    # Esto es una medida de seguridad crítica. Si corrías la simulación y, por cosas del azar o parámetros extremos,
    # nadie llegó o nadie salió del sistema, los contadores estarían en cero. Hacer una división por cero (acum_permanencia / 0)
    # haría que el programa crashee instantáneamente (lanzando un ZeroDivisionError). Al poner el if ... > 0 else 0, nos
    # aseguramos de que si no hubo llegadas o salidas, el promedio devuelva simplemente 0.
    p_rech = (estado['rechazos'] / estado['llegadas']) * 100 if estado['llegadas'] > 0 else 0
    p_perm = (estado['acum_permanencia'] / estado['salidas']) if estado['salidas'] > 0 else 0

    return columnas_principal, datos_grilla, p_rech, p_perm


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

        # [COMANDO]: ttk.Frame agrupa widgets invisiblemente. .pack(fill=tk.X) lo apila y lo estira a lo ancho.
        self.panel_res = ttk.Frame(self.root, padding=5)
        self.panel_res.pack(fill=tk.X)

        # [COMANDO]: ttk.Label muestra texto estático (sin edición).
        self.lbl_res1 = ttk.Label(self.panel_res, text="Esperando ejecución...", font=("Arial", 11, "bold"))
        self.lbl_res1.pack()
        self.lbl_res2 = ttk.Label(self.panel_res, text="")
        self.lbl_res2.pack()

        # Frame inferior para la tabla gigante. expand=True le permite absorber todo el espacio libre de la ventana.
        self.frame_grilla = ttk.Frame(self.root)
        self.frame_grilla.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # [COMANDO]: ttk.Scrollbar genera la barra.
        self.scroll_y = ttk.Scrollbar(self.frame_grilla, orient=tk.VERTICAL)
        self.scroll_x = ttk.Scrollbar(self.frame_grilla, orient=tk.HORIZONTAL)

        # [COMANDO]: ttk.Treeview es la tabla bidimensional nativa.
        # xscrollcommand vincula el movimiento del mouse en la barra a la tabla.
        self.tree = ttk.Treeview(self.frame_grilla, show="headings",
                                 yscrollcommand=self.scroll_y.set,
                                 xscrollcommand=self.scroll_x.set, selectmode="extended")

        # Acción inversa: avisa a la barra si el usuario scrollea con la ruedita directo en la tabla.
        self.scroll_y.config(command=self.tree.yview)
        self.scroll_x.config(command=self.tree.xview)

        self.scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self.scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # [COMANDO]: root.bind() escucha al teclado en cualquier momento (event-listener global).
        self.root.bind("<Control-a>", self.seleccionar_todo)
        self.root.bind("<Control-c>", self.copiar_a_excel)

        ttk.Label(self.root,
                  text="Atajos: Seleccioná las filas con el mouse (o Ctrl+A) y presioná Ctrl+C para llevarlas a Excel").pack(
            side=tk.BOTTOM)

    def construir_panel_parametros(self):
        # [COMANDO]: LabelFrame es un Frame con un bordecito y un título descriptivo arriba a la izquierda.
        panel = ttk.LabelFrame(self.root, text="Panel de Parámetros y Validaciones", padding=10)
        panel.pack(fill=tk.X, padx=10, pady=5)

        # Estructura matricial para no repetir código visual al instanciar cajas de texto.
        configs = [
            ("Lógica de Corte y Visual.", [
                ("Max. Llegadas (N)", "limite_iteraciones", 100000),
                ("Simular hasta min. (X)", "tiempo_simulacion", 100000),
                ("Mostrar desde min. (j)", "desde_reloj", 0),
                ("Cant. filas a mostrar (i)", "filas_mostrar", 100),
                ("Capacidad Max", "capacidad", 20),
                ("Paso Euler (h)", "h", 0.1)  # [NUEVO EULER]: Agregamos el parámetro h obligatorio
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
            # [COMANDO]: .grid() ubica los elementos en fila y columna (Row/Column).
            ttk.Label(panel, text=seccion, font=("Arial", 9, "bold"), foreground="darkblue").grid(row=0,
                                                                                                  column=col_offset,
                                                                                                  columnspan=2, pady=2)
            row_idx = 1
            for label_text, var_name, default_val in campos:
                # tk.W alinea el texto a la izquierda ("West").
                ttk.Label(panel, text=label_text).grid(row=row_idx, column=col_offset, sticky=tk.W, padx=5)
                entry = ttk.Entry(panel, width=8)
                entry.insert(0, str(default_val))
                entry.grid(row=row_idx, column=col_offset + 1, padx=5, pady=2)
                # Guarda el widget en un diccionario dinámico para leer su valor en el futuro.
                self.vars[var_name] = entry
                row_idx += 1
            col_offset += 2

        btn_frame = ttk.Frame(panel)
        btn_frame.grid(row=1, column=col_offset, rowspan=5, padx=20)
        # [COMANDO]: command= ejecuta una función de Python cuando el botón se clickea.
        ttk.Button(btn_frame, text="▶ INICIAR MOTOR SIMPY", command=self.ejecutar_simulacion, width=25).pack(ipady=10)

    def obtener_parametros(self):
        try:
            # [COMANDO]: .get() extrae la string tipeada. float() la convierte en número con decimales.
            p_pedir = float(self.vars['prob_pedir'].get())
            p_dev = float(self.vars['prob_devolver'].get())
            p_cons = float(self.vars['prob_consultar'].get())
            p_queda = float(self.vars['prob_queda'].get())

            # [ALGORITMO]: Validación de Integridad de Monte Carlo.
            # [POR QUÉ]: Si esto no suma 100, la distribución de probabilidad acumulada se desfasa,
            # dejando probabilidades en el aire o pisándose.
            if (p_pedir + p_dev + p_cons) != 100.0:
                # [COMANDO]: messagebox.showerror detiene todo y saca un cartel de alerta del OS.
                messagebox.showerror("Error", "Las probabilidades deben sumar EXACTAMENTE 100%.")
                return None

            return {
                'tiempo_simulacion': float(self.vars['tiempo_simulacion'].get()),
                'limite_iteraciones': int(self.vars['limite_iteraciones'].get()),
                'desde_reloj': float(self.vars['desde_reloj'].get()),
                'filas_mostrar': int(self.vars['filas_mostrar'].get()),
                'h': float(self.vars['h'].get()),  # [NUEVO EULER]: Extraemos la variable h
                'capacidad': int(self.vars['capacidad'].get()),
                't_llegada': float(self.vars['t_llegada'].get()),
                'p_pedir': p_pedir / 100.0,
                'p_dev': p_dev / 100.0,
                'p_queda': p_queda / 100.0,
                'm_pedir': float(self.vars['media_pedir'].get()),
                'u_dev_a': float(self.vars['unif_dev_a'].get()),
                'u_dev_b': float(self.vars['unif_dev_b'].get()),
                'u_cons_a': float(self.vars['unif_cons_a'].get()),
                'u_cons_b': float(self.vars['unif_cons_b'].get()),
                'u_pag_a': float(self.vars['unif_pag_a'].get()),
                'u_pag_b': float(self.vars['unif_pag_b'].get()),
                'k1': float(self.vars['k1'].get()),
                'k2': float(self.vars['k2'].get()),
                'k3': float(self.vars['k3'].get())
            }
        except ValueError:
            messagebox.showerror("Error", "Ingresaste texto donde va un número.")
            return None

    def ejecutar_simulacion(self):
        params = self.obtener_parametros()
        if not params: return

        # [COMANDO]: root.update() interrumpe todo para que Tkinter alcance a pintar en pantalla
        # el mensaje "Procesando..." antes de que Python congele la interfaz resolviendo la simulación pesada.
        self.lbl_res1.config(text="Procesando simulación híbrida (SimPy + Euler)...")
        self.root.update()

        columnas, datos, p_rechazos, p_permanencia = simular_sistema(params)

        self.lbl_res1.config(
            text=f"Promedio de permanencia: {p_permanencia:.2f} min | Filas mostradas en grilla: {len(datos)}")
        self.lbl_res2.config(text=f"Porcentaje de rechazos global (Fin Simulación): {p_rechazos:.2f}%")

        # [COMANDO]: *tree.get_children() desempaca un array con todos los IDs de filas de la tabla
        # para pasárselos como argumentos infinitos a .delete() y borrar todo de golpe.
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = columnas

        for col in columnas:
            self.tree.heading(col, text=col)
            # Estética manual: asignamos anchos en píxeles fijos (w) según qué tan largo sea el texto típico de esa celda.
            if "_ID" in col:
                w = 40
            elif "Emp" in col:
                w = 110
            elif "Fila" in col or "Leyendo" in col or "Cola" in col:
                w = 60
            elif "% Rech" in col:
                w = 85
            elif "Evento" in col:
                w = 150
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

            # [COMANDO]: tk.CENTER formatea el texto en el medio de la columna.
            self.tree.column(col, width=w, anchor=tk.CENTER, stretch=False)

        # [COMANDO]: .insert() carga la tupla simulada finalmente a la UI gráfica en el final de la lista (tk.END).
        for fila in datos: self.tree.insert("", tk.END, values=fila)

    def seleccionar_todo(self, event):
        # [COMANDO]: .selection_set() resalta en azul las filas para copiarlas.
        self.tree.selection_set(self.tree.get_children())
        return "break"

    def copiar_a_excel(self, event):
        """
        [ALGORITMO]: Exportación de Tabla a Excel mediante el Portapapeles (Clipboard).
        [POR QUÉ]: Excel interpreta el carácter especial de tabulación (\t) como "Saltar a la columna derecha"
        y el salto de línea (\n) como "Saltar a la fila de abajo". Esto formatea la data nativamente.
        """
        seleccion = self.tree.selection()
        if not seleccion: seleccion = self.tree.get_children()

        # Arma la primera fila uniendo los nombres de columna (headers) separados por \t.
        texto = "\t".join([self.tree.heading(c)["text"] for c in self.tree["columns"]]) + "\n"

        # Concatena cada fila seleccionada formateando sus celdas con \t.
        for item in seleccion: texto += "\t".join(str(v) for v in self.tree.item(item, "values")) + "\n"

        # [COMANDO]: API del SO. Borra lo que tenías copiado y le inyecta la tabla al portapapeles.
        self.root.clipboard_clear()
        self.root.clipboard_append(texto)
        self.root.update()

        # Lógica cosmética: cambia el título de la ventana y a los 2000 milisegundos (2s) lo devuelve a la normalidad.
        titulo = self.root.title()
        self.root.title("¡Filas copiadas! Listas para pegar en Excel (Ctrl+V)")
        self.root.after(2000, lambda: self.root.title(titulo))

        return "break"  # Impide que se ejecuten copias por defecto de Tkinter que ensucien la acción.


# ==========================================
# PUNTO DE ENTRADA AL PROGRAMA
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()  # Levanta el lienzo gráfico interactuando con Windows/OS.
    app = VentanaSimulacion(root)
    root.mainloop()  # Atrapa el programa en un loop infinito para que la ventana no se cierre sola.