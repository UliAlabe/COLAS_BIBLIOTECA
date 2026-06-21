## Cambios realizados

### 1. Corrección del chequeo de suma de probabilidades

**Antes:** `(p_pedir + p_dev + p_cons) != 100.0`

**Ahora:** `abs(p_pedir + p_dev + p_cons - 100.0) > 0.01`

**Por qué:** Python representa los decimales en punto flotante (IEEE 754), lo que genera errores de precisión microscópicos. Por ejemplo, `33.3 + 33.3 + 33.4` no da exactamente `100.0` en la RAM, sino `99.99999...`. La comparación exacta con `!=` tiraba un falso error en valores perfectamente válidos. Se reemplazó por una tolerancia de 0.01%.

---

### 2. Validación de parámetros de corte y visualización

| Parámetro | Regla | Por qué |
|---|---|---|
| X (tiempo a simular) | > 0 | Si X ≤ 0, `env.run(until=X)` termina sin ejecutar ningún evento. La simulación produce un vector de estado vacío. |
| N (máx. llegadas) | > 0 | El generador de llegadas corta cuando `id_gen > N`. Con N ≤ 0, ningún cliente entraría al sistema. |
| i (filas a mostrar) | > 0 | Con i ≤ 0, el filtro `len(datos_grilla) < i` nunca dejaría pasar ninguna fila al vector de estado. |
| j (mostrar desde min.) | >= 0 | El tiempo de simulación es siempre positivo; un j negativo no tiene significado físico. |
| j (mostrar desde min.) | < X | Si j ≥ X, la ventana de visualización empieza después de que la simulación terminó: se mostrarían cero filas intermedias, lo que haría pensar que el sistema falló. |

---

### 3. Validación del paso de integración de Euler

| Parámetro | Regla | Por qué |
|---|---|---|
| h (paso Euler) | > 0 | El método de Euler avanza la variable continua `P(t)` sumando `h * dP/dt` en cada iteración. Con `h = 0`, la variable nunca avanza y el `while p_actual < paginas_target` se vuelve un bucle infinito que cuelga el programa. Con `h < 0`, la variable retrocedería indefinidamente. |

---

### 4. Validación de la llegada de clientes

| Parámetro | Regla | Por qué |
|---|---|---|
| Llegadas (Cte) — t_llegada | > 0 | El generador de llegadas hace `yield env.timeout(t_llegada)` para espaciar los clientes. Con t_llegada = 0, SimPy lanzaría infinitos clientes en el instante 0. Con t_llegada < 0, `env.timeout` lanza una excepción interna de SimPy. |

---

### 5. Validación de la distribución Exponencial negativa

| Parámetro | Regla | Por qué |
|---|---|---|
| Media Pedir Exp(-) | > 0 | La fórmula de la transformada inversa es `t = -media * ln(1 - RND)`. Con media = 0 el tiempo de atención siempre sería 0. Con media < 0 el resultado sería negativo, haciendo que `env.timeout` falle. |

---

### 6. Validación de distribuciones Uniformes (a < b)

| Parámetro | Regla | Por qué |
|---|---|---|
| Unif. Dev (a, b) — devolución | a < b | La fórmula es `t = a + RND * (b - a)`. Si `a = b`, el tiempo de devolución es siempre exactamente `a` (la distribución colapsa a un valor fijo). Si `a > b`, `(b - a)` es negativo y los tiempos generados serían menores que `a`, lo que invierte el rango de la distribución. |
| Unif. Cons (a, b) — consulta | a < b | Mismo razonamiento: la distribución Uniforme pierde sentido si el límite inferior supera al superior. |
| Unif. Pág (a, b) — páginas del libro | a < b | La cantidad de páginas generada con `a > b` produciría libros con menos páginas que el mínimo esperado, cambiando qué constante K se aplica y, por ende, el tiempo de lectura calculado por Euler. |

---

### 7. Validación de la probabilidad de quedarse a leer

| Parámetro | Regla | Por qué |
|---|---|---|
| % Se Queda a Leer | 0% a 100% | Es una probabilidad: no puede ser negativa ni superar el 100%. Un valor fuera de ese rango generaría que `rnd_q < p_queda` se evalúe contra un número imposible, rompiendo la lógica Monte Carlo. |

---

### 8. Validación de la capacidad máxima

| Parámetro | Regla | Por qué |
|---|---|---|
| Capacidad máxima | > 0, entero | Es el tope de personas dentro de la biblioteca. Con capacidad ≤ 0, todos los clientes serían rechazados de inmediato (el sistema nunca atiende a nadie). Debe ser entero porque representa un conteo físico de personas. |

---

### 9. Validación de las constantes de integración K

| Parámetro | Regla | Por qué |
|---|---|---|
| K1, K2, K3 | > 0 | K es la tasa de lectura: `dP/dt = K/5`. Con K = 0, la derivada es cero y la integración de Euler nunca avanza (bucle infinito). Con K < 0, el lector "desleería" páginas, lo que no tiene sentido físico. |

---

## Comportamiento del sistema de validación

Todos los errores se acumulan en una lista antes de mostrarse. Si el usuario ingresó varios valores inválidos al mismo tiempo, el mensaje de error los lista todos juntos en un solo cuadro de diálogo, evitando que tenga que corregir y volver a ejecutar de a uno por vez.
