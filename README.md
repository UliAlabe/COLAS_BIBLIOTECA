# 📚 Simulador Híbrido de Eventos Discretos y Continuos - Biblioteca UTN

Este repositorio contiene un simulador estocástico híbrido desarrollado en Python para modelar el flujo de atención y permanencia de clientes en una biblioteca universitaria. El proyecto combina la **Simulación de Eventos Discretos (DES)** para la gestión de colas en el mostrador con la **Integración Numérica Continua** para modelar el tiempo de lectura de los usuarios.

## ⚙️ Arquitectura Técnica

El simulador está construido bajo una arquitectura que separa la lógica matemática de la interfaz visual:
* **Backend (Motor Estadístico):** Construido sobre el framework `SimPy`, operando mediante programación orientada a procesos (Generadores y el comando `yield`) para gestionar el reloj virtual y la Lista de Eventos Futuros con alta eficiencia de memoria.
* **Frontend (Interfaz de Usuario):** Desarrollado con `Tkinter` nativo. Proporciona un panel de control interactivo para parametrizar el modelo y visualización en pestañas mediante `Treeview`.

## 🧮 Lógica del Modelo y Algoritmos Implementados

El sistema resuelve el comportamiento de la biblioteca aplicando los siguientes métodos numéricos y estadísticos:

1. **Método de Monte Carlo:** Se utiliza la generación de números pseudoaleatorios (RND) para determinar las rutas de transición de los clientes (Pedir, Devolver o Consultar libros) y la decisión de permanecer en la sala de lectura.
2. **Transformada Inversa y Muestreo Continuo:** * Los tiempos de arribo y de atención de tipo "Pedir Libro" están modelados mediante una **Distribución Exponencial Negativa** (t = -Media * ln(1-RND)).
   * Los tiempos de devolución, consulta y la cantidad de páginas de un libro se modelan mediante una **Distribución Uniforme Continua**.
3. **Gestión de Colas (Teoría de Colas):** Implementación de una política FIFO automática y control de concurrencia mediante el Gestor de Contexto de servidores con capacidad parametrizable.
4. **Integración Numérica (Método de Euler):** Para el tiempo de lectura, se aproxima la ecuación diferencial de la tasa de lectura $dP/dt = K/5$ utilizando el método iterativo de Euler con un paso temporal $h$ parametrizable por el usuario, transformando las variables de integración a minutos reales del sistema.

## ✨ Características Principales

* **Vector de Estado Optimizado:** Renderizado de la grilla de eventos con filtros paramétricos ($i$, $j$) para evitar el desbordamiento de RAM en simulaciones de hasta 100.000 iteraciones (O(1) de memoria visual).
* **Desglose Numérico Aislado:** Pestaña dedicada para auditar cada iteración paso a paso del método de Euler, garantizando la trazabilidad matemática de la variable continua.
* **Integración Nativa con Excel:** Soporte para atajos de teclado (`Ctrl+A`, `Ctrl+C`) que copian las tablas directamente al portapapeles del Sistema Operativo con formateo delimitado por tabulaciones (`\t`), listas para pegar en hojas de cálculo.
* **Prevención de Errores (Safe Math):** Validaciones estáticas de integridad de probabilidades previas a la ejecución y protección contra errores de división por cero en el cálculo dinámico de KPIs nulos.

## 🚀 Tecnologías
* `Python 3.x`
* `SimPy` (Framework de simulación)
* `Tkinter` (GUI nativa)
* `random`, `math` (Librerías estándar C-core)
