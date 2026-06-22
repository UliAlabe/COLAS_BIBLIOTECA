def formato_hora(minutos):
    """Convierte minutos decimales (ej: 13.5) a formato HH:MM:SS legible."""
    if minutos == float('inf') or minutos == "":
        return "-"

    h = int(minutos // 60)
    m = int(minutos % 60)
    s = int(round((minutos * 60) % 60))

    if s == 60: s = 0; m += 1
    if m == 60: m = 0; h += 1

    return f"{h:02d}:{m:02d}:{s:02d}"
