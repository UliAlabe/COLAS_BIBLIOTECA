from dataclasses import dataclass


class ClienteSimpy:
    """Ficha de datos de cada persona presente en la biblioteca."""
    def __init__(self, id_cliente, hora_llegada, lugar_en_sala):
        self.id = id_cliente
        self.llegada = hora_llegada
        self.lugar_en_sala = lugar_en_sala
        self.estado = "En Cola"
        self.hora_fin_lectura = ""


@dataclass
class DatosAleatorios:
    """Contiene los números aleatorios y valores calculados para un evento."""
    rnd_tipo: object = ""
    tipo_atencion: str = ""
    rnd_tiempo: object = ""
    tiempo_atencion: object = ""
    rnd_quedarse: object = ""
    se_queda: str = ""
    rnd_paginas: object = ""
    paginas: object = ""
    k_aplicado: object = ""
    tiempo_lectura: object = ""
