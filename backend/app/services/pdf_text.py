import io

import PyPDF2
from PyPDF2.errors import DependencyError, PdfReadError

MOTIVO_ILEGIBLE = "ilegible"
MOTIVO_PROTEGIDO = "protegido"
MOTIVO_CIFRADO_NO_SOPORTADO = "cifrado_no_soportado"
MOTIVO_SIN_PAGINAS = "sin_paginas"
MOTIVO_SIN_TEXTO = "sin_texto"


class PdfNoClasificable(Exception):
    def __init__(self, codigo: str, mensaje: str) -> None:
        super().__init__(mensaje)
        self.codigo = codigo
        self.mensaje = mensaje


def _abrir_reader(raw: bytes, nombre: str) -> PyPDF2.PdfReader:
    try:
        return PyPDF2.PdfReader(io.BytesIO(raw))
    except PdfReadError:
        raise PdfNoClasificable(
            MOTIVO_ILEGIBLE,
            f"'{nombre}' está dañado o no es un PDF válido.",
        )


def _desbloquear(reader: PyPDF2.PdfReader, nombre: str) -> None:
    if not reader.is_encrypted:
        return

    try:
        desbloqueado = bool(reader.decrypt(""))
    except DependencyError:
        raise PdfNoClasificable(
            MOTIVO_CIFRADO_NO_SOPORTADO,
            f"'{nombre}' usa un cifrado AES que este servidor todavía no puede abrir.",
        )

    if not desbloqueado:
        raise PdfNoClasificable(
            MOTIVO_PROTEGIDO,
            f"'{nombre}' está protegido con contraseña. "
            "Quita la contraseña y vuelve a subirlo.",
        )


def _extraer_texto(reader: PyPDF2.PdfReader, nombre: str) -> str:
    try:
        if len(reader.pages) == 0:
            raise PdfNoClasificable(
                MOTIVO_SIN_PAGINAS,
                f"'{nombre}' no contiene páginas.",
            )
        return reader.pages[0].extract_text() or ""
    except DependencyError:
        raise PdfNoClasificable(
            MOTIVO_CIFRADO_NO_SOPORTADO,
            f"'{nombre}' usa un cifrado AES que este servidor todavía no puede abrir.",
        )
    except PdfReadError:
        raise PdfNoClasificable(
            MOTIVO_ILEGIBLE,
            f"'{nombre}' está dañado o no se pudo leer su contenido.",
        )


def extraer_texto_primera_pagina(raw: bytes, nombre: str) -> str:
    reader = _abrir_reader(raw, nombre)
    _desbloquear(reader, nombre)
    text = _extraer_texto(reader, nombre)

    if not text.strip():
        raise PdfNoClasificable(
            MOTIVO_SIN_TEXTO,
            f"'{nombre}' no tiene texto en su primera página "
            "(probablemente es un escaneado sin OCR), así que no se puede clasificar.",
        )

    return text
