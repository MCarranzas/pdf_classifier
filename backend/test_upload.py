import hashlib
import io
import json
import os
import struct
import uuid
import urllib.error
import urllib.request

import PyPDF2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from PyPDF2._encryption import AlgV4

BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:8000")

_P = 2147483644
_REV = 3
_KEY_SIZE = 128
_ID1 = bytes(range(16))


def _assemble(content: bytes, encrypt_dict: bytes | None = None) -> bytes:
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    if encrypt_dict is not None:
        objects.append(encrypt_dict)

    out = bytearray(b"%PDF-1.7\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    trailer = f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R"
    if encrypt_dict is not None:
        trailer += f" /Encrypt {len(objects)} 0 R /ID [<{_ID1.hex()}> <{_ID1.hex()}>]"
    out += (trailer + f" >>\nstartxref\n{xref_pos}\n%%EOF").encode()
    return bytes(out)


def _standard_dict(o_value: bytes, u_value: bytes, cfm: str) -> bytes:
    return (
        f"<< /Filter /Standard /V 4 /R {_REV} /Length {_KEY_SIZE} /P {_P} "
        f"/O <{o_value.hex()}> /U <{u_value.hex()}> "
        f"/StmF /StdCF /StrF /StdCF /CF << /StdCF << /CFM {cfm} /Length 16 >> >> >>"
    ).encode()


def make_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text} {uuid.uuid4().hex[:8]}) Tj ET".encode("latin-1")
    return _assemble(content)


def make_pdf_sin_texto() -> bytes:
    return _assemble(b"q 1 0 0 1 0 0 cm 100 100 200 200 re f Q")


def _credenciales(user_pwd: str, owner_pwd: str) -> tuple[bytes, bytes, bytes]:
    user_bytes = user_pwd.encode("latin-1")
    o_key = AlgV4.compute_O_value_key(owner_pwd.encode("latin-1"), _REV, _KEY_SIZE)
    o_value = AlgV4.compute_O_value(o_key, user_bytes, _REV)
    key = AlgV4.compute_key(user_bytes, _REV, _KEY_SIZE, o_value, _P, _ID1, True)
    return o_value, AlgV4.compute_U_value(key, _REV, _ID1), key


def _texto_pdf(text: str) -> bytes:
    return f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")


def make_pdf_protegido(user_pwd: str, owner_pwd: str, text: str) -> bytes:
    o_value, u_value, _ = _credenciales(user_pwd, owner_pwd)
    return _assemble(_texto_pdf(f"{text} {uuid.uuid4().hex[:8]}"), _standard_dict(o_value, u_value, "/Identity"))


def _aes_cbc(key: bytes, obj_num: int, content: bytes) -> bytes:
    key_data = key[: _KEY_SIZE // 8] + struct.pack("<i", obj_num)[:3] + struct.pack("<i", 0)[:2]
    digest = hashlib.md5(key_data)
    digest.update(b"sAlT")
    iv = bytes(range(16, 32))
    pad = 16 - len(content) % 16
    encryptor = Cipher(algorithms.AES(digest.digest()[:16]), modes.CBC(iv)).encryptor()
    return iv + encryptor.update(content + bytes([pad]) * pad) + encryptor.finalize()


def make_pdf_aes(user_pwd: str, owner_pwd: str, text: str) -> bytes:
    o_value, u_value, key = _credenciales(user_pwd, owner_pwd)
    return _assemble(
        _aes_cbc(key, 4, _texto_pdf(f"{text} {uuid.uuid4().hex[:8]}")), _standard_dict(o_value, u_value, "/AESV2")
    )



def multipart(fields: dict, files: list):
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    for name, filename, data in files:
        header = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode()
        parts.append(header + data + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return boundary, b"".join(parts)


def request(method, url, token=None, json_body=None, multipart_body=None, boundary=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if json_body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(json_body).encode()
    elif multipart_body is not None:
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        data = multipart_body

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as res:
            raw = res.read()
            return res.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = raw.decode(errors="replace")
        return e.code, body


def upload(filename, text, nombre_lote):
    pdf = make_pdf(text)
    reader = PyPDF2.PdfReader(io.BytesIO(pdf))
    extracted = reader.pages[0].extract_text() or ""
    print(f"  sanity extracción de '{filename}': '{extracted}'")

    boundary, body = multipart({"nombre_lote": nombre_lote}, [("files", filename, pdf)])
    return request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)


def upload_bytes(filename, pdf, nombre_lote):
    boundary, body = multipart({"nombre_lote": nombre_lote}, [("files", filename, pdf)])
    return request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)


samples = [
    ("factura.pdf", "Factura CFDI con folio fiscal, subtotal y total a pagar"),
    ("hoja_de_vida.pdf", "Curriculum vitae con experiencia laboral y habilidades"),
    ("recibo.pdf", "Recibo de pago recibido de nomina"),
    ("contrato.pdf", "Contrato laboral con clausula y acuerdo de partes"),
    ("informe.pdf", "Informe ejecutivo con resumen ejecutivo y conclusiones"),
]

username = f"test_{uuid.uuid4().hex[:8]}"
password = "secret123"

status, data = request("POST", f"{BASE_URL}/api/auth/register", json_body={"username": username, "password": password})
print(f"[register] {status} {data}")

status, data = request("POST", f"{BASE_URL}/api/auth/login", json_body={"username": username, "password": password})
if status != 200:
    raise SystemExit(f"Login falló: {status} {data}")
TOKEN = data["access_token"]
print(f"[login] OK user={data['user']['username']}")

status, data = upload(*samples[0], "Prueba 1 - un solo PDF")
print(f"\n[TEST 1 - 1 archivo] {status}")
print(json.dumps(data, indent=2, ensure_ascii=False))

all_files = [("files", name, make_pdf(text)) for name, text in samples]
boundary, body = multipart({"nombre_lote": "Prueba 2 - cinco PDFs"}, all_files)
status, data = request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)
print(f"\n[TEST 2 - 5 archivos] {status}")
print(json.dumps(data, indent=2, ensure_ascii=False))

six_files = [("files", f"doc_{i}.pdf", make_pdf(text)) for i, (_, text) in enumerate(samples + samples[:1])]
boundary, body = multipart({"nombre_lote": "Prueba 3 - seis archivos (debe fallar)"}, six_files)
status, data = request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)
print(f"\n[TEST 3 - 6 archivos, espera 400] {status} {json.dumps(data, ensure_ascii=False)}")

casos_especiales = [
    (
        "TEST 4 - contraseña de apertura (espera 400 'protegido con contraseña')",
        "protegido.pdf",
        make_pdf_protegido("secreto123", "duenio", "Factura con folio fiscal"),
    ),
    (
        "TEST 5 - solo contraseña de propietario (espera 201, se clasifica)",
        "solo_propietario.pdf",
        make_pdf_protegido("", "duenio", "Factura con folio fiscal, importe y total a pagar"),
    ),
    (
        "TEST 6 - cifrado AES-128 (espera 201, se clasifica)",
        "aes.pdf",
        make_pdf_aes("", "duenio", "Factura con folio fiscal, importe y total a pagar"),
    ),
    (
        "TEST 7 - escaneado sin texto (espera 400 'sin texto')",
        "escaneado.pdf",
        make_pdf_sin_texto(),
    ),
    (
        "TEST 8 - archivo corrupto (espera 400 'dañado')",
        "corrupto.pdf",
        b"%PDF-1.7\nbasura no es un pdf\n",
    ),
    (
        "TEST 9 - cifrado AES-128 con contraseña de apertura (espera 400 'protegido')",
        "aes_protegido.pdf",
        make_pdf_aes("secreto123", "duenio", "Factura con folio fiscal"),
    ),
]

for titulo, nombre, pdf in casos_especiales:
    status, data = upload_bytes(nombre, pdf, titulo)
    resumen = data if status != 201 else {"documents": data["documents"]}
    print(f"\n[{titulo}] {status} {json.dumps(resumen, ensure_ascii=False)}")

lote_mixto = [
    ("files", "bueno.pdf", make_pdf("Contrato laboral con objeto del contrato y partes contratantes")),
    ("files", "malo.pdf", make_pdf_protegido("secreto123", "duenio", "Factura")),
]
boundary, body = multipart({"nombre_lote": "Prueba 10 - lote mixto (debe fallar completo)"}, lote_mixto)
status, data = request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)
print(f"\n[TEST 10 - lote mixto, espera 400] {status} {json.dumps(data, ensure_ascii=False)}")

otro_usuario = f"otro_{uuid.uuid4().hex[:8]}"
status, data = request(
    "POST",
    f"{BASE_URL}/api/auth/register",
    json_body={"username": otro_usuario, "password": password},
)
print(f"\n[register segundo usuario] {status}")

status, data = request(
    "POST", f"{BASE_URL}/api/auth/login", json_body={"username": otro_usuario, "password": password}
)
if status != 200:
    raise SystemExit(f"Login del segundo usuario falló: {status} {data}")
OTRO_TOKEN = data["access_token"]

status, data = request("GET", f"{BASE_URL}/api/batches", token=OTRO_TOKEN)
print(f"[TEST 11 - lotes ajenos, espera 200 y lista vacía] {status} {json.dumps(data, ensure_ascii=False)}")

status, data = request("GET", f"{BASE_URL}/api/documents", token=OTRO_TOKEN)
print(f"[TEST 12 - documentos ajenos, espera 200 y lista vacía] {status} {json.dumps(data, ensure_ascii=False)}")

batches_propios = [
    batch
    for batch in (request("GET", f"{BASE_URL}/api/batches", token=TOKEN)[1] or [])
]
if batches_propios:
    ajeno = batches_propios[0]["id"]
    status, data = request("GET", f"{BASE_URL}/api/batches/{ajeno}", token=OTRO_TOKEN)
    print(f"[TEST 13 - leer lote ajeno, espera 404] {status} {json.dumps(data, ensure_ascii=False)}")
    status, data = request("DELETE", f"{BASE_URL}/api/batches/{ajeno}", token=OTRO_TOKEN)
    print(f"[TEST 14 - borrar lote ajeno, espera 404] {status} {json.dumps(data, ensure_ascii=False)}")

documentos_ajenos = request("GET", f"{BASE_URL}/api/documents", token=TOKEN)[1] or []
if documentos_ajenos:
    ajeno = documentos_ajenos[0]["id"]
    status, data = request("DELETE", f"{BASE_URL}/api/documents/{ajeno}", token=OTRO_TOKEN)
    print(f"[TEST 15 - borrar documento ajeno, espera 404] {status} {json.dumps(data, ensure_ascii=False)}")

status, data = request("GET", f"{BASE_URL}/api/batches", token=TOKEN)
print(f"[TEST 16 - el dueño sigue viendo {len(data or [])} lote(s)] {status}")

status, data = request("GET", f"{BASE_URL}/api/documents/resumen", token=TOKEN)
print(f"[TEST 17 - resumen global con rol user, espera 403] {status}")
if status != 403:
    raise SystemExit(f"El dashboard debería estar restringido a admin: {status} {data}")

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Role, User

with SessionLocal() as db:
    usuario = db.scalar(select(User).where(User.username == username))
    rol_admin = db.scalar(select(Role).where(Role.nombre == "admin"))
    if usuario is not None and rol_admin is not None and rol_admin not in usuario.roles:
        usuario.roles.append(rol_admin)
        db.commit()

status, data = request("GET", f"{BASE_URL}/api/documents/resumen", token=TOKEN)
conteo = {c["clasificacion"]: c["total"] for c in data.get("categorias", [])}
print(
    f"[TEST 18 - resumen global con rol admin, espera 200] {status} total={data.get('total')} {json.dumps(conteo, ensure_ascii=False)}"
)
if status != 200 or data.get("total") != sum(conteo.values()):
    raise SystemExit("El resumen del dashboard no es coherente")

with SessionLocal() as db:
    usuario = db.scalar(select(User).where(User.username == username))
    rol_admin = db.scalar(select(Role).where(Role.nombre == "admin"))
    if usuario is not None and rol_admin in usuario.roles:
        usuario.roles.remove(rol_admin)
        db.commit()

pdf_dupe = make_pdf("Documento único para prueba de duplicados")
boundary, body = multipart({"nombre_lote": "Prueba 19 - subida original"}, [("files", "original.pdf", pdf_dupe)])
status, data = request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)
print(f"[TEST 19 - subida original, espera 201] {status}")
if status != 201:
    raise SystemExit(f"La subida original debería ser 201: {status} {data}")

boundary, body = multipart({"nombre_lote": "Prueba 19 - repetida"}, [("files", "copia.pdf", pdf_dupe)])
status, data = request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)
print(f"[TEST 20 - mismo usuario repite mismo archivo, espera 400 'ya fue subido'] {status} {json.dumps(data, ensure_ascii=False)}")
if status != 400 or "ya fue subido" not in data.get("detail", ""):
    raise SystemExit(f"Debería rechazarse el duplicado: {status} {data}")

boundary, body = multipart({"nombre_lote": "Prueba 20 - repetida por otro usuario"}, [("files", "copia.pdf", pdf_dupe)])
status, data = request("POST", f"{BASE_URL}/api/documents/upload", token=OTRO_TOKEN, multipart_body=body, boundary=boundary)
print(f"[TEST 21 - otro usuario repite mismo archivo, espera 400 'ya fue subido'] {status} {json.dumps(data, ensure_ascii=False)}")
if status != 400 or "ya fue subido" not in data.get("detail", ""):
    raise SystemExit(f"El deduplicado debería ser global: {status} {data}")

pdf_interno = make_pdf("Documento que se duplica dentro del lote")
boundary, body = multipart(
    {"nombre_lote": "Prueba 21 - repetidos dentro del lote"},
    [("files", "a.pdf", pdf_interno), ("files", "b.pdf", make_pdf("Otro documento cualquiera")), ("files", "c.pdf", pdf_interno)],
)
status, data = request("POST", f"{BASE_URL}/api/documents/upload", token=TOKEN, multipart_body=body, boundary=boundary)
print(f"[TEST 22 - el mismo archivo dos veces en un lote, espera 400 'se repite'] {status} {json.dumps(data, ensure_ascii=False)}")
if status != 400 or "se repite" not in data.get("detail", ""):
    raise SystemExit(f"Un archivo no debe repetirse dentro del lote: {status} {data}")
