# Biblioteca

A una biblioteca pública llegan personas cada **4 minutos**.

En el mostrador de atención al público hay **dos empleados**, ambos se dedican a recibir libros o a prestarlos, según lo que necesite la persona que se presenta.

De las personas que vienen al mostrador:

- un **45%** viene a pedir libros,
- un **45%** a devolverlos,
- y un **10%** a consultar las condiciones para hacerse socio.

Las consultas son resueltas entre **2 y 5 minutos**.

Cualquiera de los empleados demora una cantidad de tiempo que responde a una **EXP(-) de media 6'** en buscar un libro, tomar los datos de la persona que lo pide y entregárselo.

Además, se sabe que demoran un tiempo de **2' ± 0,5'** en recibir un libro que se devuelve y registrar que la persona que lo había llevado ya lo devolvió.

De las personas que piden libros prestados, el **60%** se retira de la biblioteca, y el resto se queda a leer el libro en las instalaciones de la misma.

Las personas que utilizan las instalaciones **se quedan el tiempo que necesitan para la lectura** y luego devuelven el libro, antes de retirarse (haciendo cola si es necesario).

## Tiempo de lectura

El tiempo de lectura está determinado por la cantidad de páginas del libro. La tasa de lectura está dada por:

$$\frac{dP}{dt} = \frac{K}{5}$$

Donde **K** depende de la cantidad de páginas totales del libro:

| Páginas del libro | K |
|---|---|
| Entre 100 y 200 | 100 |
| Entre 200 y 300 | 90 |
| Más de 300 | 70 |

La cantidad de páginas de los libros está dada por **U[100 - 350]**.

> Una unidad de integración equivale a **10 min**.
>
> (Se debe poder ingresar como parámetro el K para los diferentes rangos de páginas del libro)

## Política de la biblioteca

- Se presta **solo un libro por persona**.
- La biblioteca **cierra** cuando en su interior se encuentren **20 personas**. Luego, se vuelve a abrir.

## Se solicita

Plantear una fórmula (cuyos datos se extraerían del vector de estado) para establecer:

1. El **promedio de permanencia** de las personas en la biblioteca.
2. Qué **porcentaje de personas** llegan y encuentran la biblioteca cerrada por tener su capacidad completa.

---

## Variables del sistema

Se distinguen dos grupos: las **generales** (exigidas por la consigna del TP para cualquier sistema) y las **propias del dominio** (los valores marcados en rojo en este enunciado).

### Variables generales (de la consigna del TP)

| Variable | Qué representa | Valor por defecto | Regla |
|---|---|---|---|
| **N** | Cantidad máxima de iteraciones (filas del vector de estado) a simular | 100.000 | La simulación corta al llegar a N filas **o** al llegar al tiempo X, lo que ocurra primero |
| **X** | Tiempo total a simular | A definir por el usuario al inicio | > 0 |
| **i** | Cantidad de filas a mostrar en el vector de estado | A definir por el usuario | > 0, y entero |
| **j** | Hora a partir de la cual se muestran las *i* filas | A definir por el usuario | ≥ 0 |
| **h** | Paso de integración para el método de Euler | A definir por el usuario (ej. 0,1) | > 0 |

> Estas 5 no aparecen en rojo en el enunciado de la biblioteca porque son pedidas en la consigna general del TP, no en el dominio puntual. Pero igual deben ser parametrizables.

### Variables propias del dominio (marcadas en rojo en el enunciado)

| Variable | Qué representa | Valor por defecto | Regla |
|---|---|---|---|
| **Tiempo entre llegadas** | Cada cuánto llega una persona a la biblioteca (es un valor **constante**, no aleatorio) | 4 minutos | > 0 |
| **% Pedir / % Devolver / % Consultar** | Probabilidad de que la persona que llega venga por cada motivo | 45% / 45% / 10% | La suma de los tres debe ser exactamente 100% |
| **Tiempo de consulta (a, b)** | Límites de la distribución Uniforme con que se resuelve una consulta | a = 2, b = 5 minutos | a < b |
| **Media de búsqueda/préstamo** | Media de la distribución Exponencial negativa con que el empleado busca y entrega un libro | 6 minutos | > 0 |
| **Tiempo de recepción de devolución** | Tiempo en que el empleado recibe un libro devuelto y registra el movimiento. El enunciado lo expresa como "2' ± 0,5'" | media = 2, desviación = 0,5 (o, si se interpreta como Uniforme, a = 1,5 y b = 2,5) | Si es Uniforme: a < b. Si es Normal: desviación > 0 |
| **% Retiro tras pedir libro** | Porcentaje de personas que, tras pedir un libro, se retiran sin leerlo en el lugar | 60% | Entre 0% y 100% |
| **K1, K2, K3** | Constantes de la tasa de lectura `dP/dt = K/5`, una por cada rango de páginas (100-200 / 200-300 / +300) | K1 = 100, K2 = 90, K3 = 70 | Cada una > 0. *El enunciado pide explícitamente que estas tres sean parametrizables* |
| **Rango de páginas del libro (a, b)** | Límites de la distribución Uniforme con que se genera la cantidad de páginas de cada libro | a = 100, b = 350 | a < b |
| **Capacidad máxima** | Cantidad de personas que, al alcanzarse, hace que la biblioteca cierre sus puertas hasta que baje | 20 personas | > 0, entero |

> ⚠️ Notá que el **tiempo entre llegadas** es el único valor de esta lista que **no se genera con un número aleatorio** (no es una variable aleatoria, es una constante de 4 minutos fija). Es parametrizable, pero no necesita columna de RND en el vector de estado como sí la necesitan el resto.
