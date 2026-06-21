# Trabajo Práctico 4 — Consigna

## A) Análisis y definiciones del sistema

Entregar un documento con el análisis y las definiciones del sistema asignado para el TP4. Las mismas son:

### 1. Identificación de objetos

Para cada objeto del sistema, indicar:

- **Nombre**
- **Características** (permanente / temporal)
- **Atributos**:
  - Nombre
  - Estado (y sus valores posibles)
  - Resto de atributos necesarios, cada uno con sus valores posibles

### 2. Determinación de eventos

Listar todos los eventos que pueden ocurrir en el sistema.

### 3. Colas existentes en el sistema

Identificar las colas presentes y describir sus características (capacidad, disciplina de atención, etc.).

### 4. Variables aleatorias del sistema

¿Cuáles son las variables aleatorias de este sistema? Indicar la fórmula que se utiliza para generar valores para cada variable, **reemplazando la fórmula teórica por la que corresponda en cada caso** (es decir, la fórmula ya aplicada con los parámetros concretos del enunciado, no la fórmula genérica de la distribución).

---

## B) Desarrollo del aplicativo de simulación

Desarrollar un aplicativo que efectúe la simulación del sistema definido, con las siguientes pautas:

### Alcance y corte de la simulación

- Se deberá simular **X** tiempo (parámetro solicitado al inicio), generando **N** cantidad de iteraciones en total.
- El aplicativo debe permitir simular **hasta 100.000 iteraciones** del vector de estado **o hasta el tiempo X**, lo que ocurra primero.

### Visualización del vector de estado

- Se mostrará en el vector de estado **i** iteraciones a partir de una hora **j** (valores `i` y `j` ingresados por parámetro).
- También se mostrará en el vector de estado la **última fila de simulación**, es decir, la fila correspondiente al instante **X**.
  - En esta fila **no es necesario mostrar los objetos temporales**.

### Parametrización

- **Todos los valores en rojo deben ser parametrizables.**

### Contenido mínimo del vector de estado

El vector de estado debe mostrar como mínimo la siguiente información:

- Número de fila
- Hora simulada
- Nombre del evento simulado
- Próximos eventos a ejecutarse
- **Objetos** considerados en la simulación, cada uno con sus atributos:
  - Nombre (por ser estático, podrá estar en el encabezado)
  - Estado
  - Otros atributos necesarios
- **Variables auxiliares** (acumuladores, contadores, etc.)

### Variables aleatorias

Para cada variable aleatoria de la simulación se debe mostrar el **número aleatorio** que se usó para determinar su valor.

> El Vector de Estado que se muestre como resultado de la construcción del aplicativo debe permitir conocer, a partir de una hora **j** y durante **i** iteraciones, en cualquier instante de ese intervalo (fila seleccionada), el valor de **todos los atributos de los objetos presentes en el sistema en ese instante** (no es necesario mostrar los objetos que ya dejaron de existir en el sistema).

### Integración numérica (parte continua)

- El valor que asume en cada caso la variable aleatoria resultante de la integración numérica debe ser mostrado en el vector de estado.
- Además, la integración numérica de la parte continua también debe ser mostrada en la aplicación, **o** se puede bajar a Excel y mostrarse desde ahí — siempre con alguna referencia que permita identificar a qué instancia de la variable aleatoria corresponde cada integración.
- **Método de integración:** Euler, con **h parametrizable**.

### Resultados esperados

- Plantear las fórmulas necesarias para responder lo que se desea averiguar con la simulación.
- Informar el resultado obtenido para la simulación efectuada.
