# Aclaraciones sobre la consigna y criterios de validación

## K1, K2, K3
Solo deben ser **> 0**. No hay relación de orden obligatoria entre ellas (no se exige K1 > K2 > K3).

## Parámetro `prob_queda` (% Se Queda a Leer)
Se mantiene como el complemento del enunciado: el enunciado dice "60% se retira", por lo tanto el parámetro es "40% se queda a leer". El label en la UI dice "% Se Queda a Leer" = 40, lo cual es correcto y no se modifica.

## Capacidad máxima
Solo se valida que sea un **entero > 0**, sin tope máximo. El usuario es responsable de no poner valores absurdos que generen miles de columnas visuales.

## Parámetro `j` (desde_reloj) vs `X` (tiempo_simulacion)
Se valida que `j < X`. Si el inicio de la ventana de visualización está después del fin de la simulación, no se mostraría ninguna fila intermedia, por lo que se muestra un error.
