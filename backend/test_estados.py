"""Prueba del flujo de estados: PENDIENTE -> RECHAZADO / APROBADO."""

import json
import os
import urllib.request
import uuid

from test_upload import make_pdf, multipart, request

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")

USUARIO = f"estados_{uuid.uuid4().hex[:8]}"
PASSWORD = "secret123"

request("POST", f"{BASE_URL}/api/auth/register", json_body={"username": USUARIO, "password": PASSWORD})
status, data = request(
    "POST", f"{BASE_URL}/api/auth/login", json_body={"username": USUARIO, "password": PASSWORD}
)
TOKEN = data["access_token"]

OTRO = f"otro_{uuid.uuid4().hex[:8]}"
request("POST", f"{BASE_URL}/api/auth/register", json_body={"username": OTRO, "password": PASSWORD})
status, data = request("POST", f"{BASE_URL}/api/auth/login", json_body={"username": OTRO, "password": PASSWORD})
OTRO_TOKEN = data["access_token"]

# PDF con indicadores debiles -> el clasificador pide revision.
# Se suben dos porque APROBADO y RECHAZADO son estados finales: cada rama
# necesita su propio documento.
def subir(nombre):
    boundary, body = multipart(
        {"nombre_lote": "Prueba estados"},
        [("files", nombre, make_pdf("Documento sin indicadores claros"))],
    )
    status, data = request(
        "POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary
    )
    assert status == 201, (status, data)
    print(f"[subida] {nombre} -> {data['documents'][0]['estado']}")
    docs = request("GET", f"{BASE_URL}/api/documents", token=TOKEN)[1] or []
    return next(d["id"] for d in docs if d["nombre_archivo"] == nombre)


ID_RECHAZO = subir("rechazo.pdf")
ID_APROBADO = subir("aprobado.pdf")


def cambiar(estado, token=TOKEN, doc_id=ID_APROBADO):
    status, data = request(
        "PATCH",
        f"{BASE_URL}/api/documents/{doc_id}/estado",
        token=token,
        json_body={"estado": estado},
    )
    print(f"  -> {estado}: {status} {json.dumps(data, ensure_ascii=False)}")
    return status, data


def toggle(flag, token=TOKEN, doc_id=ID_APROBADO):
    status, data = request(
        "PATCH",
        f"{BASE_URL}/api/documents/{doc_id}/revision",
        token=token,
        json_body={"requiere_revision": flag},
    )
    print(f"  -> revision={flag}: {status} {json.dumps(data, ensure_ascii=False)}")
    return status, data


def descargar(doc_id, token=TOKEN):
    req = urllib.request.Request(
        f"{BASE_URL}/api/documents/{doc_id}/archivo",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(req) as res:
        return res.status, res.read()


print("[1] rechazar un pendiente")
status, data = cambiar("RECHAZADO", doc_id=ID_RECHAZO)
assert status == 200 and data["estado"] == "RECHAZADO" and data["requiere_revision"] is False

print("[2] un RECHAZADO no vuelve a PENDIENTE -> 400")
status, data = cambiar("PENDIENTE", doc_id=ID_RECHAZO)
assert status == 400, (status, data)
assert "es final" in data.get("detail", ""), data

print("[3] un RECHAZADO no vuelve a revision -> 400")
status, data = toggle(True, doc_id=ID_RECHAZO)
assert status == 400, (status, data)

print("[4] el PDF se conserva tras rechazar")
codigo, cuerpo = descargar(ID_RECHAZO)
print(f"  -> descarga: {codigo}, {len(cuerpo)} bytes")
assert codigo == 200 and cuerpo.startswith(b"%PDF")

print("[5] aprobar un pendiente: el toggle sincroniza el estado")
status, data = toggle(False, doc_id=ID_APROBADO)
assert status == 200 and data["estado"] == "APROBADO" and data["requiere_revision"] is False

print("[6] un APROBADO no vuelve a PENDIENTE -> 400")
status, data = cambiar("PENDIENTE", doc_id=ID_APROBADO)
assert status == 400, (status, data)
assert "es final" in data.get("detail", ""), data

print("[7] un APROBADO no vuelve a revision -> 400")
status, data = toggle(True, doc_id=ID_APROBADO)
assert status == 400, (status, data)

print("[8] rechazar sin revision -> 400")
status, data = cambiar("RECHAZADO", doc_id=ID_APROBADO)
assert status == 400, (status, data)

print("[9] reaplicar el mismo estado final es idempotente -> 200")
status, data = cambiar("APROBADO", doc_id=ID_APROBADO)
assert status == 200 and data["estado"] == "APROBADO"

print("[10] estado invalido -> 400")
status, data = cambiar("inventado", doc_id=ID_APROBADO)
assert status == 400, (status, data)

print("[11] usuario ajeno -> 404")
status, data = cambiar("RECHAZADO", token=OTRO_TOKEN, doc_id=ID_RECHAZO)
assert status == 404, (status, data)

print("[12] limpieza")
for doc_id in (ID_RECHAZO, ID_APROBADO):
    status, _ = request("DELETE", f"{BASE_URL}/api/documents/{doc_id}", token=TOKEN)
    print(f"  -> {status}")

print("\nOK - todas las pruebas de estado pasaron")
