/**
 * Localiza palabras clave dentro de la capa de texto de una pagina de pdf.js.
 *
 * El backend clasifica con PyPDF2 y el visor dibuja con pdf.js: los dos
 * extraen el texto con espacios y saltos distintos, asi que las posiciones que
 * devuelve el servidor no servirian. Aqui se busca directamente sobre el texto
 * que se esta pintando.
 *
 * La comparacion ignora los espacios a proposito. pdf.js parte una pagina en
 * items como le viene, y el hueco entre dos items no se puede reconstruir de
 * forma fiable: puede ser un espacio real, un salto de linea, o cero si el
 * PDF emite un item por glifo. Comparar sin espacios acierta en los tres casos.
 */

/** Une los items de la pagina conservando donde empieza cada uno. */
export function concatenarItems(items) {
  let crudo = ''
  const inicios = []
  for (const item of items) {
    inicios.push(crudo.length)
    crudo += item.str
  }
  return { crudo, inicios }
}

/** Minúsculas, NFKC y sin espacios, con el índice de origen de cada carácter. */
export function compactar(crudo) {
  const salida = []
  const mapa = []

  for (let i = 0; i < crudo.length; i += 1) {
    const ch = crudo[i]
    if (/\s/u.test(ch)) continue
    // Un carácter puede normalizarse a varios (p. ej. ligaduras), y en ese caso
    // todos los caracteres normalizados apuntan al mismo índice original.
    for (const norm of ch.normalize('NFKC').toLowerCase()) {
      salida.push(norm)
      mapa.push(i)
    }
  }

  return { texto: salida.join(''), mapa }
}

export function compactarPalabra(palabra) {
  return palabra
    .normalize('NFKC')
    .toLowerCase()
    .replace(/\s+/gu, '')
}

/** Devuelve [{ palabra, inicio, fin }] sobre los índices de `crudo`. */
export function buscarPalabras(crudo, palabras) {
  const { texto, mapa } = compactar(crudo)
  const coincidencias = []

  for (const palabra of palabras) {
    const objetivo = compactarPalabra(palabra)
    if (!objetivo) continue

    let desde = 0
    for (;;) {
      const idx = texto.indexOf(objetivo, desde)
      if (idx === -1) break
      const ultimo = Math.min(idx + objetivo.length - 1, mapa.length - 1)
      coincidencias.push({ palabra, inicio: mapa[idx], fin: mapa[ultimo] + 1 })
      desde = idx + objetivo.length
    }
  }

  return { texto, mapa, coincidencias }
}

/** Convierte cada coincidencia en rectangulos de canvas. */
export function resaltar(items, medidas, inicios, coincidencias) {
  const rects = []

  for (const { palabra, inicio, fin } of coincidencias) {
    items.forEach((item, i) => {
      const desde = inicios[i]
      const hasta = desde + item.str.length
      if (fin <= desde || inicio >= hasta) return

      const largo = item.str.length || 1
      const m = medidas[i]
      const f0 = (Math.max(inicio, desde) - desde) / largo
      const f1 = (Math.min(fin, hasta) - desde) / largo

      rects.push({
        palabra,
        x: m.izquierda + m.ancho * f0,
        y: m.arriba,
        width: m.ancho * (f1 - f0),
        height: m.alto,
      })
    })
  }

  return rects
}
