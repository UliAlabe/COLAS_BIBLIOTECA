# Algoritmo numérico de Euler para aproximar el tiempo de lectura de un cliente.
# La ecuación diferencial que resuelve es: dP/dt = k/5
# donde P es la cantidad de páginas leídas y t es la variable de integración.
# Una unidad de t equivale a 10 minutos reales de lectura.

def calcular_euler(paginas_totales, k, paso_euler, id_cliente, reloj_hora_str, es_auditable):
    """
    Aproxima cuántas unidades de tiempo tarda el cliente en leer su libro,
    avanzando de a 'paso_euler' por iteración.

    es_auditable controla si se guardan filas para la pestaña de auditoría.
    El loop siempre corre (el cálculo del tiempo es siempre correcto);
    solo se omite el guardado de filas cuando el cliente está fuera de la ventana visible.
    """
    filas_euler = []
    tiempo_integracion = 0.0  # Unidades de integración transcurridas (1 unidad = 10 min reales)
    paginas_leidas = 0.0
    iteracion = 1

    # Fila de condiciones iniciales (t=0, P=0)
    if es_auditable:
        filas_euler.append((
            f"ID {id_cliente} - Lectura", iteracion, reloj_hora_str,
            f"Meta: {int(paginas_totales)} Pág", round(tiempo_integracion, 4), round(paginas_leidas, 4), "-"
        ))
    iteracion += 1

    # Loop principal: avanza en pasos h hasta alcanzar la meta de páginas
    while paginas_leidas < paginas_totales:
        velocidad_lectura = k / 5.0  # dP/dt = k/5 (constante dada por la cátedra)
        paginas_leidas_siguiente = paginas_leidas + paso_euler * velocidad_lectura

        if es_auditable:
            filas_euler.append((
                f"ID {id_cliente} - Lectura", iteracion, reloj_hora_str,
                "Integración", round(tiempo_integracion, 4), round(paginas_leidas, 4), round(velocidad_lectura, 4)
            ))
        iteracion += 1

        paginas_leidas = paginas_leidas_siguiente
        tiempo_integracion += paso_euler

    # Fila final: se alcanzó la meta
    if es_auditable:
        filas_euler.append((
            f"ID {id_cliente} - Lectura", iteracion, reloj_hora_str,
            "Meta Cumplida", round(tiempo_integracion, 4), round(paginas_leidas, 4),
            f"P >= {int(paginas_totales)}", "-"
        ))

    # Conversión de unidades de integración a minutos reales
    tiempo_lectura = tiempo_integracion * 10.0

    return tiempo_lectura, filas_euler
