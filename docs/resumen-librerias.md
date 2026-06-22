# Resumen de librerías — COLAS_BIBLIOTECA

Cómo se usan BufferSnapshot, SimPy y Tkinter en este proyecto.

---

## 1. BufferSnapshot — mecanismo de acumulación y commit

### Métodos

| Método | Quién lo llama | Parámetros | Qué hace | ¿Genera fila al vector de estado? |
|---|---|---|---|---|
| **`agregar_evento(reloj, evento, rnds, estado, clientes)`** | `SimuladorBiblioteca._registrar()` | `reloj` = `env.now`, `evento` = string como `"Llegada (Pedir)"`, `rnds` = `DatosAleatorios`, `estado` = dict con contadores, `clientes` = lista de `ClienteSimpy` | ① Si el reloj avanzó respecto al buffer anterior → llama a `_commit()` y abre buffer nuevo. ② Acumula string del evento. ③ Fusiona RNDs nuevos (sin borrar los del mismo instante). ④ Si el instante está dentro de la ventana `[j, j+i]` → guarda snapshot congelado. | No — solo acumula |
| **`_commit()`** (automático) | Se llama desde `agregar_evento()` cuando detecta que el reloj avanzó | Ninguno (usa `self._datos_buffer` y `self._reloj_buffer`) | ① Verifica si el instante está dentro de la ventana visible. Si no → incrementa contador y sale. ② Filtra eventos: solo "Llegada", "Fin Atenc", "Fin Lectura" en columna Evento, unidos con `" + "`. ③ Llama a `_construir_fila()`. | **Sí** — una fila por cada instante dentro de la ventana |
| **`commit_final(estado, clientes)`** | `SimuladorBiblioteca.ejecutar()` después de `env.run()` | Estado actual + clientes en sala | ① Toma el último snapshot o construye uno nuevo. ② Genera fila `"FIN SIMULACIÓN"` con `ocultar_próxima_llegada=True`. ③ No incrementa el contador de eventos. | **Sí** — la última fila |
| **`_construir_fila(snap, evento_str, rnds, ocultar=False)`** | `_commit()` y `commit_final()` | snapshot congelado, string del evento, RNDs acumulados, flag para ocultar próx llegada | ① Calcula `% Rechazos` y `Prom Perm`. ② Redondea valores. ③ Convierte tiempos float a HH:MM:SS. ④ Empaqueta slots de clientes (4 columnas cada uno). ⑤ Devuelve tupla de ~26 + 4×capacidad columnas. | — (arma la fila) |

### Diagrama de flujo

```
agregar_evento()  →  acumula en buffer
       |
       ├─ ¿cambió el reloj? → _commit() → escribe fila en vector_estado
       |                                    y abre buffer nuevo
       |
       └─ guarda evento + RNDs + snapshot en buffer actual

commit_final()  →  _construir_fila("FIN SIMULACIÓN")  →  fila final
```

### Condiciones de visibilidad

| Parámetro | Rol en BufferSnapshot |
|---|---|
| `j` (desde_reloj) | Si `reloj < j`, el snapshot ni se construye (ahorra memoria) |
| `i` (filas_mostrar) | Si ya se generaron `i` filas, el snapshot deja de construirse |
| Ambos | Se evalúan en `agregar_evento()` y en `_commit()` |

---

## 2. SimPy — las 5 funciones que usás en el proyecto

| Función / Constructo | Línea(s) en simulador.py | Qué le decís a SimPy | Lo que SimPy hace |
|---|---|---|---|
| **`simpy.Environment()`** | 22 | "Creame un universo de simulación con su propio reloj y agenda" | Crea el `env`. `env.now` arranca en `0.0`. Internamente tiene una cola de eventos ordenada por tiempo. |
| **`simpy.Resource(env, capacity=2)`** | 24 | "Los empleados son un recurso compartido con 2 unidades. Cuando alguien pida uno y estén todos ocupados, ponelo en una cola FIFO" | Crea un contador de capacidad 2. Mantiene una cola de procesos esperando. |
| **`env.process(funcion(args))`** | 273 | "Registrá `proceso_cliente(1)` como un proceso vivo. No lo corras ahora, solo tenelo listo" | Agrega el generador a la lista de procesos activos. No arranca hasta `env.run()`. |
| **`env.run(until=X)`** | 284 | "Prendé el motor. Avanzá el reloj saltando de evento en evento hasta llegar al minuto X y ahi frená" | Saca eventos de la agenda en orden, avanza `env.now`, ejecuta procesos en el momento exacto, duerme los que corresponda. Cuando el próximo evento supera `X`, corta. |
| **`with recurso.request() as p: yield p`** | 139-147, 231-235 | "Necesito un empleado. Si no hay, dormime hasta que se libere uno" | `request()` crea un token. `yield p` pausa el proceso. SimPy lo pone en la cola del recurso. Cuando otro proceso libera el empleado (saliendo del `with`), SimPy despierta al primero en la cola. |
| **`yield env.timeout(t)`** | 174, 224, 253, 275 | "Despertame dentro de `t` minutos exactos" | Agenda un evento en `env.now + t`. Cuando el reloj llega a ese instante, reanuda el proceso justo después del `yield`. Mientras tanto, otros procesos pueden correr. |

### Cómo interactúan

```
env.run() arranca
  │
  ▼
generador_llegadas() se ejecuta
  │  yield env.timeout(4)   ← duerme 4 min
  │  env.process(cliente)   ← lanza un cliente
  │
  ▼ (se repite cada 4 min)
  │
  ▼
proceso_cliente(n):
  │  yield empleados.request()   ← espera empleado (cola FIFO)
  │  yield env.timeout(atencion) ← espera atención
  │  yield env.timeout(lectura)  ← espera lectura (si aplica)
  │  yield empleados.request()   ← espera empleado para devolver
  │  yield env.timeout(devol)    ← espera devolución
  │
  ▼
env.run() termina al llegar a X
```

Los **yield** en tu proyecto:

| Línea | `yield` | Qué hace |
|---|---|---|
| 147 | `yield peticion` | Espera en la cola de empleados hasta que uno se libere |
| 174 | `yield env.timeout(t_atencion)` | Espera que pase el tiempo de atención |
| 224 | `yield env.timeout(t_lectura)` | Espera que termine la lectura |
| 235 | `yield peticion_devolucion` | Espera empleado para devolver el libro |
| 253 | `yield env.timeout(t_devolucion)` | Espera que terminen la devolución |
| 275 | `yield env.timeout(t_llegada)` | El generador espera 4 min antes de crear el próximo cliente |

Los procesos **no corren en paralelo real**. Es cooperativo: uno hace `yield` → se pausa → SimPy despierta al siguiente que tenga evento programado.

---

## 3. Tkinter — componentes usados en `ventana.py`

| Widget | Línea(s) | Qué muestra / hace | Vinculación en el proyecto |
|---|---|---|---|
| **`tk.Tk()`** | `VentanaSimulacion.__init__` recibe `root` | Ventana del SO, título "Simulador Eventos Discretos UTN...", tamaño 1500×800 | Es el `root` que `main.py` crea. De acá cuelga todo. |
| **`ttk.LabelFrame(root, text="...")`** | 71 | Marco con borde y título. Agrupa los inputs del usuario. | `panel.pack(fill=tk.X)` — ocupa todo el ancho. |
| **`ttk.Label(parent, text="...")`** | 66, 108, 113, 21, 23 | Texto fijo: títulos de sección, etiquetas de campos, atajos, resultados | `.grid()` en el panel o `.pack()` en el frame de resultados. |
| **`ttk.Entry(parent, width=8)`** | 114 | Cada campo de entrada numérica. 17 en total. | Se guardan en `self.vars[var_name]`. Se leen con `.get()` en `obtener_parametros()`. |
| **`ttk.Button(btn_frame, text="▶ INICIAR...", command=...)`** | 123-125 | Botón que dispara la simulación. Se desactiva mientras corre. | `command=self.ejecutar_simulacion`. `config(state="disabled"/"normal")` para threading. |
| **`ttk.Notebook(root)`** | 26 | Grupo de pestañas. Dos solapas: "Vector de Estado Principal" y "Auditoría Ecuaciones Euler". | `self.notebook.select()` → pestaña activa. `self.notebook.index(tab_id)` → 0 o 1 (para Ctrl+A/Ctrl+C). |
| **`ttk.Treeview(tab, show="headings", selectmode="extended")`** | 36-39, 54-56 | **La tabla principal.** Columnas dinámicas. | `tree["columns"] = tupla`, `heading(col, text=col)`, `column(col, width=w)`, `insert("", tk.END, values=fila)`. |
| **`ttk.Scrollbar(tab, orient=VERTICAL/HORIZONTAL)`** | 33-34, 52 | Barras de scroll para la tabla. | Vinculadas con `yscrollcommand` / `xscrollcommand` del Treeview. |

### Métodos de `root` (ventana Tk) que usás

| Método | Línea(s) | Qué hace | Uso concreto |
|---|---|---|---|
| **`.title("...")`** | 11, 332-333 | Cambia el texto de la barra de título | Muestra "¡Filas copiadas!" por 2 segundos, luego vuelve al original |
| **`.geometry("1500x800")`** | 12 | Tamaño inicial de la ventana | Pantallazo inicial |
| **`.bind("<Control-a>", fn)`** | 62 | Atajo de teclado global | Ctrl+A → selecciona todas las filas de la pestaña activa |
| **`.bind("<Control-c>", fn)`** | 63 | Atajo de teclado global | Ctrl+C → copia las filas seleccionadas como TSV al portapapeles |
| **`.clipboard_clear()`** | 327 | Borra el portapapeles del SO | Antes de copiar los datos de la tabla |
| **`.clipboard_append(texto)`** | 328 | Agrega texto al portapapeles | Pega el contenido TSV (Excel-ready) |
| **`.after(2000, lambda)`** | 333 | Programa función para ejecutarse después de 2000 ms | Restaura el título original después de mostrar "¡Copiado!" |

### Flujo de la GUI

```
1. main.py → tk.Tk() → VentanaSimulacion(root)
2. __init__() construye:
     ├─ LabelFrame con 17 Entry + 1 Button
     ├─ Label de resultados
     ├─ Notebook con 2 tabs
     │   ├─ Tab1: Treeview (Vector Estado) + 2 Scrollbars
     │   └─ Tab2: Treeview (Euler Auditoría) + 1 Scrollbar
     └─ bindings Ctrl+A y Ctrl+C
3. Usuario completa parámetros y aprieta "▶ INICIAR..."
4. VentanaSimulacion.ejecutar_simulacion():
     ├─ obtener_parametros() → valida y devuelve dict
     ├─ desactiva botón
     ├─ threading.Thread(target=simular_sistema).start()  ← no congela la UI
     └─ root.after(0, mostrar_resultados)  ← actualiza tablas desde el hilo principal
5. mostrar_resultados():
     ├─ calcula métricas finales
     ├─ tree_principal.delete() + insert()
     └─ tree_euler.delete() + insert()
```
