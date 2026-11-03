"""
Convierte el perfil del usuario en instrucciones de personalización para el LLM.

Minimización de datos: a Gemini NO se le envían el correo, la fecha de nacimiento ni
la edad exacta. El nombre va como la etiqueta [USUARIO] (se reemplaza por el nombre
real recién cuando la respuesta vuelve a Kira) y la edad como un tramo.
"""

from backend.services.privacidad import tramo_de_edad


def armar_contexto_usuario(perfil: dict, nombre_visible: str | None = None) -> str:
    """nombre_visible: cómo se nombra a la persona ante el LLM (por defecto "[USUARIO]")."""
    if not perfil or not isinstance(perfil, dict):
        return ""

    nombre = (perfil.get("nombre") or "").strip()
    if nombre:
        nombre = nombre_visible or "[USUARIO]"
    edad = perfil.get("edad")
    tramo = tramo_de_edad(edad)
    consolas = perfil.get("consolas") or []
    generos = perfil.get("generos") or []

    if not (nombre or edad or consolas or generos):
        return ""

    lineas = ["CONTEXTO DEL USUARIO CON QUIEN HABLAS AHORA:"]
    if nombre:
        lineas.append(f"- Nombre: {nombre} (etiqueta de privacidad: escríbela tal cual si lo nombras)")
    if tramo:
        lineas.append(f"- Edad: {tramo}")
    if consolas:
        lineas.append(f"- Plataformas favoritas: {', '.join(consolas)}")
    if generos:
        lineas.append(f"- Géneros favoritos: {', '.join(generos)}")

    lineas += ["", "INSTRUCCIONES DE PERSONALIZACIÓN:"]
    if nombre:
        lineas.append(f"- Llama a la persona por su nombre ({nombre}) de forma natural, no forzada, no en cada frase.")
    if consolas:
        lineas.append(
            f"- Al recomendar juegos, prioriza los disponibles en sus plataformas "
            f"({', '.join(consolas)}). Si mencionas un juego que NO está en ninguna de "
            f"esas plataformas, adviértelo."
        )
    if generos:
        lineas.append(
            f"- Al sugerir juegos, prioriza sus géneros favoritos ({', '.join(generos)}), "
            f"pero puedes mencionar excepciones si son muy relevantes."
        )
    if edad is not None:
        if edad < 13:
            lineas.append(
                "- Es una persona menor de 13. Usa un tono especialmente amable y ejemplos apropiados. "
                "NO recomiendes juegos con clasificación M (Mature) o AO. "
                "Prioriza juegos E (Everyone) y E10+."
            )
        elif edad < 18:
            lineas.append(
                "- Es menor de edad (entre 13 y 17 años). Evita recomendar juegos con clasificación M (17+) o AO (18+). "
                "Si te preguntan directamente por uno, menciona la clasificación y sugiere alternativas apropiadas."
            )
        else:
            lineas.append(
                "- Es mayor de edad. Puedes recomendar cualquier juego, "
                "incluyendo títulos con clasificación M."
            )

    return "\n".join(lineas) + "\n"
