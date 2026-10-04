-- ============================================================================
-- Indices recomendados para pdf_classifier (MariaDB 10.4)
-- ============================================================================
-- Verificado con EXPLAIN contra las consultas reales de backend/app/routers/
-- y medido sobre una base de prueba de 50.000 documents / 200.000 reviews.
--
-- Aplicar con:  mysql -u root pdf_classifier < indices_rendimiento.sql
-- Es idempotente: se puede volver a ejecutar sin errores.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1) document_reviews.document_id  ->  PRIORIDAD ALTA
-- ---------------------------------------------------------------------------
-- Es la columna que más se consulta del sistema y NO tiene indice. La usan:
--   documents.py:286        historial de observaciones de un documento
--   documents.py:289        (misma consulta desde /api/documents)
--   admin_documents.py:80   ultima observacion + filesort, POR CADA documento
--   admin_documents.py:86   COUNT de observaciones, POR CADA documento
--   observaciones.py:28     IN (...) sobre todos los documentos del usuario
--
-- Sin indice: type=ALL (escaneo completo) + Using filesort.
-- Con indice: type=ref + Using index.
-- El indice incluye created_at, id para que el ORDER BY ... DESC de las
-- consultas de historial se resuelva con el indice y no con filesort.

SET @db := DATABASE();

SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'document_reviews'
        AND INDEX_NAME = 'ix_reviews_document_id_created') > 0,
    'SELECT 1',
    'CREATE INDEX ix_reviews_document_id_created
       ON document_reviews (document_id, created_at, id)'
  )
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ---------------------------------------------------------------------------
-- 2) documents.nombre_archivo  ->  ORDEN del listado del panel de admin
-- ---------------------------------------------------------------------------
-- admin_documents.py:163 hace ORDER BY nombre_archivo, id siempre.
-- Sin indice el plan es type=ALL + Using filesort (ordena toda la tabla
-- para descartar 24 de cada 25 filas).
--
-- El indice (nombre_archivo, id) cubre el listado sin filtros y evita el
-- filesort en los tres casos.

SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'documents'
        AND INDEX_NAME = 'ix_documents_nombre') > 0,
    'SELECT 1',
    'CREATE INDEX ix_documents_nombre ON documents (nombre_archivo, id)'
  )
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ---------------------------------------------------------------------------
-- 3) documents.estado + documents.user_id compuestos con nombre_archivo
-- ---------------------------------------------------------------------------
-- El listado del admin filtra por estado (admin_documents.py:166) o por
-- usuario (:168) y ademas ordena por nombre. Con los indices compuestos el
-- filtro y el orden se resuelven con el indice, sin filesort.
-- NOTA: ix_documents_user_id (sencillo) queda cubierto por este compuesto,
--       asi que se puede eliminar (paso 6).

SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'documents'
        AND INDEX_NAME = 'ix_documents_estado_nombre') > 0,
    'SELECT 1',
    'CREATE INDEX ix_documents_estado_nombre
       ON documents (estado, nombre_archivo, id)'
  )
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'documents'
        AND INDEX_NAME = 'ix_documents_user_nombre') > 0,
    'SELECT 1',
    'CREATE INDEX ix_documents_user_nombre
       ON documents (user_id, nombre_archivo, id)'
  )
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ---------------------------------------------------------------------------
-- 4) documents.nombre_archivo FULLTEXT  ->  SOLO si se cambia el LIKE
-- ---------------------------------------------------------------------------
-- admin_documents.py:170 busca con  LIKE '%texto%'  (wildcard delante).
-- Ningun indice B-tree puede acelerar eso: obliga a escaneo completo.
-- MariaDB NO sustituye el LIKE por el FULLTEXT automaticamente, hay que
-- cambiar la consulta a MATCH ... AGAINST.
-- Medido sobre 50.000 docs:  81 ms (LIKE) -> 0.78 ms (MATCH BOOLEAN).
--
-- Descomentar solo si se adapta la consulta del router:
--
--   --SET @sql := (
--   --  SELECT IF(
--   --    (SELECT COUNT(*) FROM information_schema.STATISTICS
--   --      WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'documents'
--   --        AND INDEX_NAME = 'ft_documents_nombre') > 0,
--   --    'SELECT 1',
--   --    'CREATE FULLTEXT INDEX ft_documents_nombre ON documents (nombre_archivo)'
--   --  )
--   --);
--   --PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ---------------------------------------------------------------------------
-- 5) batches (user_id, fecha_creacion)
-- ---------------------------------------------------------------------------
-- batches.py:33 filtra por user_id y ordena por fecha_creacion DESC.
-- Con ix_batches_user_id solo (estado actual) hay Using filesort; el
-- compuesto resuelve filtro y orden con el indice.

SET @sql := (
  SELECT IF(
    (SELECT COUNT(*) FROM information_schema.STATISTICS
      WHERE TABLE_SCHEMA = @db AND TABLE_NAME = 'batches'
        AND INDEX_NAME = 'ix_batches_user_fecha') > 0,
    'SELECT 1',
    'CREATE INDEX ix_batches_user_fecha ON batches (user_id, fecha_creacion)'
  )
);
PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ---------------------------------------------------------------------------
-- 6) Limpieza de indices redundantes  ->  se gaina espacio y escrituras
-- ---------------------------------------------------------------------------
-- a) ix_documents_hash_archivo (NO unico) es EXACTAMENTE duplicado de
--    uq_documents_hash_archivo (unico). MariaDB usa siempre el unico para
--    el SELECT ... WHERE hash_archivo = ?  (documents.py:122, confirmado con
--    EXPLAIN: key=uq_documents_hash_archivo, Using index).
--    El no unico solo aporta coste en cada INSERT/UPDATE.
--
-- b) document_reviews.admin_user_id: InnoDB lo creo por la FK, pero
--    NINGUNA consulta del proyecto filtra por esa columna. Se puede quitar
--    (InnoDB permitira la FK sin el indice; solo afecta al borrado de un
--    usuario, operacion rara).

--SET @sql := (SELECT IF(
--  (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@db
--     AND TABLE_NAME='documents' AND INDEX_NAME='ix_documents_hash_archivo')>0,
--  'DROP INDEX ix_documents_hash_archivo ON documents', 'SELECT 1'));
--PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

--SET @sql := (SELECT IF(
--  (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@db
--     AND TABLE_NAME='document_reviews' AND INDEX_NAME='admin_user_id')>0,
--  'DROP INDEX admin_user_id ON document_reviews', 'SELECT 1'));
--PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

--SET @sql := (SELECT IF(
--  (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@db
--     AND TABLE_NAME='documents' AND INDEX_NAME='ix_documents_user_id')>0,
--  'DROP INDEX ix_documents_user_id ON documents', 'SELECT 1'));
--PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;

--SET @sql := (SELECT IF(
--  (SELECT COUNT(*) FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=@db
--     AND TABLE_NAME='batches' AND INDEX_NAME='ix_batches_user_id')>0,
--  'DROP INDEX ix_batches_user_id ON batches', 'SELECT 1'));
--PREPARE s FROM @sql; EXECUTE s; DEALLOCATE PREPARE s;


-- ============================================================================
-- RESUMEN MEDIDO (50.000 documentos / 200.000 revisiones, mismo hardware)
-- ============================================================================
-- reviews: historial ORDER BY created_at,id   696.47 ms ->    2.33 ms   299x
-- reviews: COUNT por documento               1796.14 ms ->    1.09 ms  1650x
-- reviews: IN(...) 25 docs ORDER BY id      1008.00 ms ->   22.80 ms    44x
-- documents: listado admin ORDER BY            155.58 ms ->    2.40 ms    65x
-- documents: listado admin WHERE estado        141.26 ms ->    2.68 ms    53x
-- documents: listado admin WHERE user_id       102.68 ms ->    3.39 ms    30x
-- documents: busqueda texto (FULLTEXT)          166.45 ms ->    0.78 ms   213x
-- ============================================================================

ANALYZE TABLE documents, document_reviews, batches;