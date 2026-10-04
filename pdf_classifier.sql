-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 02-10-2026 a las 18:24:29
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `pdf_classifier`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `batches`
--

CREATE TABLE `batches` (
  `id` int(11) NOT NULL,
  `nombre_lote` varchar(255) NOT NULL,
  `fecha_creacion` datetime NOT NULL,
  `user_id` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `batches`
--

INSERT INTO `batches` (`id`, `nombre_lote`, `fecha_creacion`, `user_id`) VALUES
(502, 'Lote 02/10/2026 12:23', '2026-10-02 16:23:01', 3);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `documents`
--

CREATE TABLE `documents` (
  `id` varchar(36) NOT NULL,
  `nombre_archivo` varchar(255) NOT NULL,
  `ruta_fisica` varchar(512) NOT NULL,
  `clasificacion` varchar(100) DEFAULT NULL,
  `confianza` float DEFAULT NULL,
  `motivo` varchar(500) DEFAULT NULL,
  `requiere_revision` tinyint(1) NOT NULL DEFAULT 0,
  `hash_archivo` varchar(64) DEFAULT NULL,
  `estado` varchar(20) NOT NULL DEFAULT 'APROBADO',
  `user_id` int(11) DEFAULT NULL,
  `batch_id` int(11) DEFAULT NULL,
  `palabras` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `documents`
--

INSERT INTO `documents` (`id`, `nombre_archivo`, `ruta_fisica`, `clasificacion`, `confianza`, `motivo`, `requiere_revision`, `hash_archivo`, `estado`, `user_id`, `batch_id`, `palabras`) VALUES
('083228e2-177b-48f7-b629-56361f0a806d', 'contrato1.pdf', 'C:\\MarioC\\webs_figma\\pdf_classifier\\backend\\uploads\\502\\654f2f23938b48c083e1470e896e5d26_contrato1.pdf', 'CONTRATO', 0.8, 'La primera página contiene indicadores de contrato: CONTRATO, CÓDIGO, OBJETO DEL CONTRATO, PARTES CONTRATANTES.', 0, 'd1600f437d5d3b762af0c2fd2a309fdf617b19eb8fab5aa7afd52aecc0445064', 'APROBADO', 3, 502, '[\"CONTRATO\", \"CÓDIGO\", \"OBJETO DEL CONTRATO\", \"PARTES CONTRATANTES\"]'),
('79f4ee06-3ae8-4572-88bc-abb9ecc6927d', 'contrato3.pdf', 'C:\\MarioC\\webs_figma\\pdf_classifier\\backend\\uploads\\502\\798674f349014434a7fb79c1ce4a249e_contrato3.pdf', 'CONTRATO', 0.6, 'La primera página contiene indicadores de contrato: CONTRATO, CÓDIGO, OBJETO DEL CONTRATO.', 0, '7b4716ce62b02d8c931588af2201a676f115c02125980c820e52e863efa70ff3', 'APROBADO', 3, 502, '[\"CONTRATO\", \"CÓDIGO\", \"OBJETO DEL CONTRATO\"]'),
('960fb4a1-4ea6-4bde-a2b6-3f83ee4692ba', '101-Cliente-2.pdf', 'C:\\MarioC\\webs_figma\\pdf_classifier\\backend\\uploads\\502\\6a26c57b86794c9e8f2d0da3a51b05a2_101-Cliente-2.pdf', 'FACTURA', 0.8, 'La primera página contiene indicadores de factura: factura, n° de factura, facturar a, importe.', 0, '7bd1653578fb306be00acd22f07c0f4348851a35f5120fab53c3c41d8ab3f04e', 'APROBADO', 3, 502, '[\"factura\", \"n° de factura\", \"facturar a\", \"importe\"]'),
('bdaab74c-1f47-4a12-8b47-31c63f584c20', 'contrato2.pdf', 'C:\\MarioC\\webs_figma\\pdf_classifier\\backend\\uploads\\502\\40610b41825843deb9cda5253baca57f_contrato2.pdf', 'CONTRATO', 0.6, 'La primera página contiene indicadores de contrato: CONTRATO, CÓDIGO, OBJETO DEL CONTRATO.', 0, '5f071ed4a1f818e10a2c89ed0bbac657822ddd7872e41e362fe8de17697ce828', 'APROBADO', 3, 502, '[\"CONTRATO\", \"CÓDIGO\", \"OBJETO DEL CONTRATO\"]'),
('cf3bd31b-2c2d-440f-8a62-07ed01909b31', '100-Cliente-1.pdf', 'C:\\MarioC\\webs_figma\\pdf_classifier\\backend\\uploads\\502\\d8725322a2f045bb90b4106470d1a99c_100-Cliente-1.pdf', 'FACTURA', 0.8, 'La primera página contiene indicadores de factura: factura, n° de factura, facturar a, importe.', 0, 'cce11b7fe0b5e5ec58ba7924029cfb24145c1672376cd153eb07964fb8ba6321', 'APROBADO', 3, 502, '[\"factura\", \"n° de factura\", \"facturar a\", \"importe\"]');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `document_reviews`
--

CREATE TABLE `document_reviews` (
  `id` int(11) NOT NULL,
  `document_id` varchar(36) NOT NULL,
  `nombre_archivo` varchar(255) NOT NULL,
  `admin_user_id` int(11) DEFAULT NULL,
  `admin_username` varchar(100) NOT NULL,
  `usuario_id` int(11) DEFAULT NULL,
  `usuario_username` varchar(100) DEFAULT NULL,
  `accion` varchar(20) NOT NULL,
  `estado_anterior` varchar(20) DEFAULT NULL,
  `estado_nuevo` varchar(20) DEFAULT NULL,
  `observacion` text NOT NULL,
  `created_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `roles`
--

CREATE TABLE `roles` (
  `id` int(11) NOT NULL,
  `nombre` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `roles`
--

INSERT INTO `roles` (`id`, `nombre`) VALUES
(1, 'admin'),
(2, 'user');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `created_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `users`
--

INSERT INTO `users` (`id`, `username`, `password_hash`, `created_at`) VALUES
(1, 'mcarranza', '$2b$12$KF0XXvJWbFM//ArzsUWopetdJFYY6hN5HhboIJHDHH8DRG.oRW6Qi', '2026-09-24 14:48:18'),
(2, 'gonchito', '$2b$12$sjNbSGfR13QZtwAojif9ie0XaTBsN4qnDWhEaToJfWeILKsmMVbWm', '2026-09-28 14:57:59'),
(3, 'marito', '$2b$12$/yC/kDNOatGA7wivliZWxuK6EqD5U9EA7H/HC7q5YAOpouJR/rVQe', '2026-09-28 16:25:40');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `user_roles`
--

CREATE TABLE `user_roles` (
  `user_id` int(11) NOT NULL,
  `role_id` int(11) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Volcado de datos para la tabla `user_roles`
--

INSERT INTO `user_roles` (`user_id`, `role_id`) VALUES
(1, 1),
(1, 2),
(2, 2),
(3, 2);

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `batches`
--
ALTER TABLE `batches`
  ADD PRIMARY KEY (`id`),
  ADD KEY `ix_batches_user_id` (`user_id`),
  ADD KEY `ix_batches_user_fecha` (`user_id`,`fecha_creacion`);

--
-- Indices de la tabla `documents`
--
ALTER TABLE `documents`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_documents_hash_archivo` (`hash_archivo`),
  ADD KEY `ix_documents_hash_archivo` (`hash_archivo`),
  ADD KEY `ix_documents_user_id` (`user_id`),
  ADD KEY `documents_batch_id_fk` (`batch_id`),
  ADD KEY `ix_documents_nombre` (`nombre_archivo`,`id`),
  ADD KEY `ix_documents_estado_nombre` (`estado`,`nombre_archivo`,`id`),
  ADD KEY `ix_documents_user_nombre` (`user_id`,`nombre_archivo`,`id`);

--
-- Indices de la tabla `document_reviews`
--
ALTER TABLE `document_reviews`
  ADD PRIMARY KEY (`id`),
  ADD KEY `admin_user_id` (`admin_user_id`),
  ADD KEY `ix_reviews_document_id_created` (`document_id`,`created_at`,`id`);

--
-- Indices de la tabla `roles`
--
ALTER TABLE `roles`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_roles_nombre` (`nombre`);

--
-- Indices de la tabla `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_users_username` (`username`);

--
-- Indices de la tabla `user_roles`
--
ALTER TABLE `user_roles`
  ADD PRIMARY KEY (`user_id`,`role_id`),
  ADD KEY `ix_user_roles_role_id` (`role_id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `batches`
--
ALTER TABLE `batches`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=503;

--
-- AUTO_INCREMENT de la tabla `document_reviews`
--
ALTER TABLE `document_reviews`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=82;

--
-- AUTO_INCREMENT de la tabla `roles`
--
ALTER TABLE `roles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=151;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `batches`
--
ALTER TABLE `batches`
  ADD CONSTRAINT `batches_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `documents`
--
ALTER TABLE `documents`
  ADD CONSTRAINT `documents_batch_id_fk` FOREIGN KEY (`batch_id`) REFERENCES `batches` (`id`),
  ADD CONSTRAINT `documents_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;

--
-- Filtros para la tabla `document_reviews`
--
ALTER TABLE `document_reviews`
  ADD CONSTRAINT `document_reviews_ibfk_1` FOREIGN KEY (`admin_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL;

--
-- Filtros para la tabla `user_roles`
--
ALTER TABLE `user_roles`
  ADD CONSTRAINT `user_roles_role_id_fk` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `user_roles_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
