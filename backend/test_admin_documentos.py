"""Pruebas del panel de administracion de documentos.

Verifica que el admin ve los documentos de todos los usuarios, que puede
moverlos entre estados incluso desde un estado final, que toda accion exige y
guarda una observacion, y que el historial sobrevive al borrado.
"""

import json
import os
import uuid
from urllib.parse import urlencode

from test_upload import make_pdf, multipart, request

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
API = f"{BASE_URL}/api/admin/documentos"

PASSWORD = "secret123"


def listar(token: str, **params) -> tuple[int, dict]:
    """GET del listado con paginacion desactivada (por_pagina=0).

    La mayoria de estos tests_assert sobre el listado completo, no sobre una
    pagina: asi la paginacion no los vuelve fragile.
    """
    query = {"por_pagina": 0, **{k: v for k, v in params.items() if v is not None}}
    status, data = request("GET", f"{API}?{urlencode(query)}", token=token)
    return status, data


def listar_todos(token: str, **params) -> list[dict]:
    status, data = listar(token, **params)
    assert status == 200, (status, data)
    return data["documentos"]


def registrar(username: str) -> str:
    request(
        "POST",
        f"{BASE_URL}/api/auth/register",
        json_body={"username": username, "password": PASSWORD},
    )
    status, data = request(
        "POST",
        f"{BASE_URL}/api/auth/login",
        json_body={"username": username, "password": PASSWORD},
    )
    assert status == 200, (status, data)
    return data["access_token"]


SUFIJO = uuid.uuid4().hex[:8]
DONANTE = f"admin_panel_{SUFIJO}"
TRABAJADOR = f"empleado_{SUFIJO}"

# Los nombres llevan sufijo: una corrida anterior puede haber dejado PDFs con
# el mismo nombre base y el filtro por texto los traeria todos.
NOMBRE_PENDIENTE = f"pendiente_{SUFIJO}.pdf"
NOMBRE_APROBADO = f"aprobado_{SUFIJO}.pdf"
# Este no se toca en todo el test: sirve para comprobar los campos en null.
NOMBRE_INTACTO = f"intacto_{SUFIJO}.pdf"

DONANTE_TOKEN = registrar(DONANTE)
TRABAJADOR_TOKEN = registrar(TRABAJADOR)


def volver_admin(token: str) -> str:
    """Registra un usuario y le da el rol admin directamente en la BD."""
    from sqlalchemy import select

    from app.database import SessionLocal
    from app.models import Role, User

    with SessionLocal() as db:
        usuario = db.scalar(select(User).where(User.username == DONANTE))
        rol_admin = db.scalar(select(Role).where(Role.nombre == "admin"))
        if usuario is not None and rol_admin is not None and rol_admin not in usuario.roles:
            usuario.roles.append(rol_admin)
            db.commit()
    return token


DONANTE_TOKEN = volver_admin(DONANTE_TOKEN)


def subir(token: str, nombre: str, texto: str) -> str:
    """Sube un PDF y devuelve su id.

    La respuesta del upload no trae el id (UploadedDocument no lo incluye), asi
    que se busca despues en el listado del propio usuario.
    """
    boundary, body = multipart(
        {"nombre_lote": "Prueba panel admin"},
        [("files", nombre, make_pdf(texto))],
    )
    status, data = request(
        "POST",
        f"{BASE_URL}/api/documents/upload",
        token=token,
        multipart_body=body,
        boundary=boundary,
    )
    assert status == 201, (status, data)

    documentos = request("GET", f"{BASE_URL}/api/documents", token=token)[1] or []
    return next(d["id"] for d in documentos if d["nombre_archivo"] == nombre)


# El PDF del empleado tiene indicadores debiles, asi que nace PENDIENTE.
DOC_EMPLEADO = subir(TRABAJADOR_TOKEN, NOMBRE_PENDIENTE, "Documento sin indicadores claros")
DOC_APROBADO = subir(TRABAJADOR_TOKEN, NOMBRE_APROBADO, "Contrato laboral con objeto del contrato y partes contratantes")
DOC_INTACTO = subir(TRABAJADOR_TOKEN, NOMBRE_INTACTO, "Factura con numero de factura y datos del emisor")

print("[0] IDs de prueba")
print(f"  empleado pendiente: {DOC_EMPLEADO}")
print(f"  empleado aprobado : {DOC_APROBADO}")
print(f"  empleado intacto  : {DOC_INTACTO}")

print("\n[0b] se deja el segundo documento en APROBADO para probar la salida de un estado final")
estado_inicial = next(
    d["estado"]
    for d in listar_todos(DONANTE_TOKEN, texto=NOMBRE_APROBADO)
    if d["id"] == DOC_APROBADO
)
print(f"  -> estado tras la subida: {estado_inicial}")
if estado_inicial != "APROBADO":
    status, data = request(
        "PATCH",
        f"{API}/{DOC_APROBADO}/estado",
        token=DONANTE_TOKEN,
        json_body={"estado": "APROBADO", "observacion": "Ajuste de la prueba para partir de un estado final."},
    )
    assert status == 200, (status, data)
    print(f"  -> forzado a APROBADO por el admin ({data['documento']['estado']})")

print("\n[1] un usuario normal no puede listar documentos ajenos -> 403")
status, data = request("GET", API, token=TRABAJADOR_TOKEN)
print(f"  -> {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 403, (status, data)

print("\n[2] el admin ve el documento de otro usuario")
documentos = listar_todos(DONANTE_TOKEN)
print(f"  -> 200, {len(documentos)} documento(s) en total")
encontrado = next(d for d in documentos if d["id"] == DOC_EMPLEADO)
print(
    f"  -> dueÃ±o: {encontrado['usuario_nombre']}, "
    f"estado: {encontrado['estado']}, "
    f"observaciones: {encontrado['total_observaciones']}"
)
assert encontrado["usuario_nombre"] == TRABAJADOR, encontrado
assert encontrado["estado"] == "PENDIENTE", encontrado
assert encontrado["total_observaciones"] == 0, encontrado

print("\n[2b] el listado expone el motivo con el que se clasifico el documento")
print(f"  -> motivo: {encontrado['motivo']!r}")
# El clasificador siempre deja un motivo, pero el campo admite null (p. ej.
# documentos anteriores a la columna), asi que la tabla debe tolerar ambos.
assert isinstance(encontrado["motivo"], str) and encontrado["motivo"], encontrado

motivos_vacios = [d for d in listar_todos(DONANTE_TOKEN) if not d.get("motivo")]
print(f"  -> {len(motivos_vacios)} documento(s) sin motivo (el campo admite null)")
assert all(d["motivo"] is None for d in motivos_vacios)

print("\n[3] filtrar por estado y por usuario")
pendientes = listar_todos(DONANTE_TOKEN, estado="PENDIENTE")
print(f"  -> pendientes: {len(pendientes)}")
assert all(d["estado"] == "PENDIENTE" for d in pendientes)

busqueda = listar_todos(DONANTE_TOKEN, texto=f"pendiente_{SUFIJO}")
print(f"  -> busqueda por texto: {len(busqueda)}")
assert [d["id"] for d in busqueda] == [DOC_EMPLEADO], busqueda

print("\n[3b] la paginacion devuelve total, pagina y solo la ventana pedida")
status, data = request("GET", f"{API}?por_pagina=2&pagina=1", token=DONANTE_TOKEN)
assert status == 200, (status, data)
print(f"  -> total={data['total']}, pagina={data['pagina']}, por_pagina={data['por_pagina']}, filas={len(data['documentos'])}")
assert set(data) == {"total", "pagina", "por_pagina", "documentos"}, data
assert data["por_pagina"] == 2 and data["pagina"] == 1
assert len(data["documentos"]) == 2, data
assert data["total"] > len(data["documentos"]), "deberia haber mas documentos que una pagina"

primera = [d["id"] for d in data["documentos"]]
status, data2 = request("GET", f"{API}?por_pagina=2&pagina=2", token=DONANTE_TOKEN)
segunda = [d["id"] for d in data2["documentos"]]
assert status == 200 and data2["pagina"] == 2
assert not set(primera) & set(segunda), "las paginas no deben solaparse"
assert data2["total"] == data["total"], "el total no cambia al paginar"
print(f"  -> pagina 1 {len(primera)} filas, pagina 2 {len(segunda)} filas, sin solape")

status, data3 = request("GET", f"{API}?por_pagina=2&pagina=99999", token=DONANTE_TOKEN)
assert status == 200 and data3["documentos"] == [], data3["documentos"]
print(f"  -> pagina mas alla del final: {status}, {len(data3['documentos'])} filas")

print("\n[3c] la paginacion se combina con los filtros")
status, data4 = request(
    "GET", f"{API}?estado=PENDIENTE&por_pagina=3", token=DONANTE_TOKEN
)
assert status == 200, (status, data4)
assert data4["total"] == len(pendientes), (data4["total"], len(pendientes))
assert all(d["estado"] == "PENDIENTE" for d in data4["documentos"])
print(f"  -> estado=PENDIENTE + por_pagina=3: total={data4['total']}, filas={len(data4['documentos'])}")

print("\n[3d] parametros de paginacion invalidos -> 422")
for query in ("por_pagina=0.5", "por_pagina=-1", "por_pagina=9999", "pagina=0", "pagina=-3"):
    status, _ = request("GET", f"{API}?{query}", token=DONANTE_TOKEN)
    assert status == 422, (query, status)
print("  -> 422 en por_pagina=0.5, por_pagina=-1, por_pagina=9999, pagina=0, pagina=-3")

print("\n[3e] por_pagina=0 desactiva el corte y normaliza la pagina")
status, data5 = request("GET", f"{API}?por_pagina=0", token=DONANTE_TOKEN)
assert status == 200, (status, data5)
assert data5["por_pagina"] == 0 and data5["pagina"] == 1, data5
assert len(data5["documentos"]) == data5["total"], (len(data5["documentos"]), data5["total"])
print(f"  -> sin paginar: pagina={data5['pagina']}, por_pagina={data5['por_pagina']}, {len(data5['documentos'])} filas = total")

status, data6 = request("GET", f"{API}?por_pagina=0&pagina=7", token=DONANTE_TOKEN)
assert status == 200 and data6["pagina"] == 1, data6
print(f"  -> pagina=7 sin paginar se normaliza a {data6['pagina']}")

print("\n[4] cambiar de estado sin observacion -> 422")
status, data = request(
    "PATCH", f"{API}/{DOC_EMPLEADO}/estado", token=DONANTE_TOKEN, json_body={"estado": "APROBADO"}
)
print(f"  -> {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 422, (status, data)

print("\n[5] observacion demasiado corta -> 422")
status, data = request(
    "PATCH",
    f"{API}/{DOC_EMPLEADO}/estado",
    token=DONANTE_TOKEN,
    json_body={"estado": "APROBADO", "observacion": "ok"},
)
print(f"  -> {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 422, (status, data)

print("\n[6] estado invalido -> 400")
status, data = request(
    "PATCH",
    f"{API}/{DOC_EMPLEADO}/estado",
    token=DONANTE_TOKEN,
    json_body={"estado": "inventado", "observacion": "no existe ese estado"},
)
print(f"  -> {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 400, (status, data)

print("\n[7] rechazar el pendiente con observacion")
status, data = request(
    "PATCH",
    f"{API}/{DOC_EMPLEADO}/estado",
    token=DONANTE_TOKEN,
    json_body={"estado": "RECHAZADO", "observacion": "No es un documento valido."},
)
print(f"  -> {status}")
print(f"     documento: {data['documento']['estado']}, requiere_revision={data['documento']['requiere_revision']}")
print(f"     observacion: {json.dumps(data['observacion'], ensure_ascii=False)}")
assert status == 200 and data["documento"]["estado"] == "RECHAZADO"
assert data["documento"]["requiere_revision"] is False
assert data["observacion"]["accion"] == "RECHAZAR"
assert data["observacion"]["estado_anterior"] == "PENDIENTE"
assert data["observacion"]["estado_nuevo"] == "RECHAZADO"
assert data["observacion"]["admin_username"] == DONANTE
assert data["observacion"]["usuario_username"] == TRABAJADOR

print("\n[8] el admin sale de un estado final: PENDIENTE -> APROBADO")
status, data = request(
    "PATCH",
    f"{API}/{DOC_EMPLEADO}/estado",
    token=DONANTE_TOKEN,
    json_body={"estado": "PENDIENTE", "observacion": "Revisado de nuevo, falta informacion."},
)
assert status == 200 and data["documento"]["estado"] == "PENDIENTE", data
assert data["documento"]["requiere_revision"] is True, data
print(f"  -> PENDIENTE, requiere_revision={data['documento']['requiere_revision']}")

status, data = request(
    "PATCH",
    f"{API}/{DOC_EMPLEADO}/estado",
    token=DONANTE_TOKEN,
    json_body={"estado": "APROBADO", "observacion": "Revisado, ahora si es valido."},
)
assert status == 200 and data["documento"]["estado"] == "APROBADO", data
print(f"  -> APROBADO, accion={data['observacion']['accion']}")

print("\n[9] el usuario normal sigue sin poder tocar el estado final")
status, data = request(
    "PATCH",
    f"{BASE_URL}/api/documents/{DOC_EMPLEADO}/estado",
    token=TRABAJADOR_TOKEN,
    json_body={"estado": "PENDIENTE"},
)
print(f"  -> {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 400 and "es final" in data.get("detail", ""), (status, data)

print("\n[10] el admin si puede rechazar un documento en estado APROBADO")
estado_antes = next(
    d["estado"]
    for d in listar_todos(DONANTE_TOKEN, texto=NOMBRE_APROBADO)
    if d["id"] == DOC_APROBADO
)
print(f"  -> estado de partida: {estado_antes}")
status, data = request(
    "PATCH",
    f"{API}/{DOC_APROBADO}/estado",
    token=DONANTE_TOKEN,
    json_body={"estado": "RECHAZADO", "observacion": "Clasificacion equivocada, es una nomina."},
)
assert status == 200 and data["documento"]["estado"] == "RECHAZADO", data
assert data["observacion"]["estado_anterior"] == estado_antes, data
print(f"  -> RECHAZADO desde APROBADO, accion={data['observacion']['accion']}")

print("\n[11] historial con las 3 observaciones del primer documento")
status, data = request("GET", f"{API}/{DOC_EMPLEADO}/observaciones", token=DONANTE_TOKEN)
print(f"  -> {status}, {len(data)} observacion(es)")
for obs in data:
    print(f"     {obs['accion']}: {obs['estado_anterior']} -> {obs['estado_nuevo']} | {obs['observacion']}")
assert status == 200 and len(data) == 3, data
assert [o["accion"] for o in data] == ["APROBAR", "PENDIENTE", "RECHAZAR"], data

print("\n[12] el listado muestra la ultima observacion y el total")
fila = next(d for d in listar_todos(DONANTE_TOKEN, texto=NOMBRE_PENDIENTE))
print(f"  -> ultima: {fila['ultima_observacion']!r} ({fila['total_observaciones']} en total)")
assert fila["ultima_observacion"] == "Revisado, ahora si es valido.", fila
assert fila["total_observaciones"] == 3, fila

print("\n[12b] el listado expone la transicion del ultimo cambio de estado")
for campo in (
    "ultima_observacion_accion",
    "ultima_observacion_estado_anterior",
    "ultima_observacion_estado_nuevo",
    "ultima_observacion_admin",
):
    assert fila[campo] is not None, (campo, fila)
print(
    f"  -> {fila['ultima_observacion_estado_anterior']} -> "
    f"{fila['ultima_observacion_estado_nuevo']} por {fila['ultima_observacion_admin']} "
    f"(accion={fila['ultima_observacion_accion']})"
)
assert fila["ultima_observacion_accion"] == "APROBAR", fila
assert fila["ultima_observacion_estado_anterior"] == "PENDIENTE", fila
assert fila["ultima_observacion_estado_nuevo"] == "APROBADO", fila

# Un documento sin acciones manuales no tiene transicion: los campos van a null.
sin_cambios = next(
    d for d in listar_todos(DONANTE_TOKEN, texto=NOMBRE_INTACTO)
)
assert sin_cambios["id"] == DOC_INTACTO, sin_cambios
assert sin_cambios["ultima_observacion"] is None, sin_cambios
assert sin_cambios["ultima_observacion_estado_anterior"] is None, sin_cambios
assert sin_cambios["ultima_observacion_estado_nuevo"] is None, sin_cambios
assert sin_cambios["ultima_observacion_admin"] is None, sin_cambios
assert sin_cambios["total_observaciones"] == 0, sin_cambios
print("  -> un documento sin cambios manuales deja los campos de transicion en null")

print("\n[12c] el dueño ve la ultima observacion en su propia lista de lotes")
estado, lotes = request("GET", f"{BASE_URL}/api/batches", token=TRABAJADOR_TOKEN)
assert estado == 200, (estado, lotes)
propio = next(
    d for lote in lotes for d in lote["documents"] if d["id"] == DOC_EMPLEADO
)
print(
    f"  -> {propio['nombre_archivo']}: {propio['ultima_observacion']!r} "
    f"({propio['ultima_observacion_estado_anterior']} -> "
    f"{propio['ultima_observacion_estado_nuevo']} por {propio['ultima_observacion_admin']})"
)
assert propio["ultima_observacion"] == "Revisado, ahora si es valido.", propio
assert propio["ultima_observacion_estado_anterior"] == "PENDIENTE", propio
assert propio["ultima_observacion_estado_nuevo"] == "APROBADO", propio
assert propio["ultima_observacion_admin"] == DONANTE, propio

# El documento que el admin nunca toco no debe inventarse una observacion.
sin_cambios_propio = next(
    d for lote in lotes for d in lote["documents"] if d["id"] == DOC_INTACTO
)
assert sin_cambios_propio["ultima_observacion"] is None, sin_cambios_propio
print("  -> el documento sin acciones del admin no trae observacion en la lista del dueño")

print("\n[12d] el historial tambien esta disponible para el dueño")
status, propio_hist = request(
    "GET", f"{BASE_URL}/api/documents/{DOC_EMPLEADO}/observaciones", token=TRABAJADOR_TOKEN
)
print(f"  -> el dueño pide su historial: {status}, {len(propio_hist)} observacion(es)")
assert status == 200 and len(propio_hist) == 3, propio_hist
assert [o["accion"] for o in propio_hist] == ["APROBAR", "PENDIENTE", "RECHAZAR"], propio_hist
for obs in propio_hist:
    assert obs["admin_username"] == DONANTE, obs

# Un documento ajeno no debe filtrarse por esta puerta.
AJENO = f"ajeno_{SUFIJO}"
AJENO_TOKEN = registrar(AJENO)
DOC_AJENO = subir(AJENO_TOKEN, f"ajeno_{SUFIJO}.pdf", "Factura con numero de factura")
status, data = request(
    "GET", f"{BASE_URL}/api/documents/{DOC_AJENO}/observaciones", token=TRABAJADOR_TOKEN
)
print(f"  -> pedir el historial de un documento ajeno: {status} {data}")
assert status == 404, (status, data)

# El dueño real si entra, aunque todavia no tenga observaciones.
status, data = request(
    "GET", f"{BASE_URL}/api/documents/{DOC_AJENO}/observaciones", token=AJENO_TOKEN
)
print(f"  -> el dueño del documento ajeno ve su historial vacio: {status} {data}")
assert status == 200 and data == [], (status, data)

print("\n[13] el admin abre el PDF y el analisis de un documento ajeno")
req = __import__("urllib.request", fromlist=["Request"]).Request(
    f"{API}/{DOC_EMPLEADO}/archivo",
    headers={"Authorization": f"Bearer {DONANTE_TOKEN}"},
)
with __import__("urllib.request", fromlist=["urlopen"]).urlopen(req) as res:
    cuerpo = res.read()
print(f"  -> descarga: {res.status}, {len(cuerpo)} bytes")
assert res.status == 200 and cuerpo.startswith(b"%PDF")

status, data = request("GET", f"{API}/{DOC_EMPLEADO}/analisis", token=DONANTE_TOKEN)
print(f"  -> analisis: {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 200 and "palabras" in data

print("\n[14] borrar con observacion")
ruta_pdf = next(
    d["ruta_fisica"]
    for d in request("GET", f"{BASE_URL}/api/documents", token=TRABAJADOR_TOKEN)[1]
    if d["id"] == DOC_EMPLEADO
)
status, data = request(
    "DELETE",
    f"{API}/{DOC_EMPLEADO}",
    token=DONANTE_TOKEN,
    json_body={"observacion": "Documento duplicado, se elimina."},
)
print(f"  -> {status}")
print(f"     observacion: {json.dumps(data['observacion'], ensure_ascii=False)}")
assert status == 200 and data["documento"] is None, data
assert data["observacion"]["accion"] == "ELIMINAR"
assert data["observacion"]["estado_nuevo"] is None
assert not os.path.isfile(ruta_pdf), "el PDF deberia haberse borrado del disco"
print(f"     PDF borrado del disco: {not os.path.isfile(ruta_pdf)}")

print("\n[15] el documento desaparece del listado, pero su historial sigue")
restantes = listar_todos(DONANTE_TOKEN)
assert all(d["id"] != DOC_EMPLEADO for d in restantes), "el documento deberia estar borrado"
print(f"  -> {len(restantes)} documento(s) en el listado, el eliminado ya no aparece")

status, data = request("GET", f"{API}/{DOC_EMPLEADO}/observaciones", token=DONANTE_TOKEN)
print(f"  -> historial tras el borrado: {status}, {len(data)} observacion(es)")
for obs in data:
    print(f"     {obs['accion']}: {obs['observacion']}")
assert status == 200 and len(data) == 4, (status, data)
assert data[0]["accion"] == "ELIMINAR", data[0]

print("\n[15b] el PDF y el analisis de un documento borrado ya no se sirven")
status, data = request("GET", f"{API}/{DOC_EMPLEADO}/analisis", token=DONANTE_TOKEN)
print(f"  -> analisis: {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 404, (status, data)

print("\n[16] borrar el otro documento y limpiar")
status, data = request(
    "DELETE",
    f"{API}/{DOC_APROBADO}",
    token=DONANTE_TOKEN,
    json_body={"observacion": "Limpieza de la prueba."},
)
assert status == 200, data
print(f"  -> {status}")

print("\n[17] documento inexistente -> 404")
status, data = request(
    "PATCH",
    f"{API}/no-existe/estado",
    token=DONANTE_TOKEN,
    json_body={"estado": "APROBADO", "observacion": "no deberia llegar aqui"},
)
print(f"  -> {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 404, (status, data)

print("\n[18] resumen del panel")
status, data = request("GET", f"{API}/resumen", token=DONANTE_TOKEN)
print(f"  -> {status} {json.dumps(data, ensure_ascii=False)}")
assert status == 200 and "por_estado" in data

print("\n[19] el total del listado cuadra con el resumen tras los borrados")
status, listado = request("GET", f"{API}?por_pagina=1", token=DONANTE_TOKEN)
assert status == 200
status, resumen_data = request("GET", f"{API}/resumen", token=DONANTE_TOKEN)
assert status == 200
resumen_estados = {e["estado"]: e["total"] for e in resumen_data["por_estado"]}
assert listado["total"] == resumen_data["total"], (listado["total"], resumen_data["total"])
assert listado["total"] == sum(resumen_estados.values()), (listado["total"], resumen_estados)
print(
    f"  -> listado={listado['total']}, resumen={resumen_data['total']}, "
    f"suma por estado={sum(resumen_estados.values())} ({resumen_estados})"
)

print("\nOK - todas las pruebas del panel de administracion pasaron")

