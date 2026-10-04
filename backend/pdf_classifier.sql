-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 30-09-2026 a las 01:42:53
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
(157, 'gonchito1', '2026-09-29 23:27:19', 2),
(158, 'gonchito2', '2026-09-29 23:27:51', 2),
(159, 'gonchi3', '2026-09-29 23:28:37', 2),
(160, 'carranza1', '2026-09-29 23:31:58', 1),
(161, 'carranza2', '2026-09-29 23:32:23', 1),
(162, 'carranza3', '2026-09-29 23:32:57', 1),
(164, 'marito1', '2026-09-29 23:34:25', 3),
(166, 'marito2', '2026-09-29 23:35:37', 3);

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
('0ebea001-885c-4484-a5a7-689b6a2cc937', 'facturas_04_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\160\\370e43557ebd4f4997f9e20fa6dae930_facturas_04_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, 'de5d7d972dc03b295d96e8a0f02ef88c8c1bc21a8e85883eac9ab8d3b0f57255', 'APROBADO', 1, 160, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('11b00401-323d-495f-9b05-f95b52b71d4a', 'facturas_05_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\160\\33ea668a1f784b0bbb7704bec7dc69c6_facturas_05_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '71ffa00241250545fd1d02868a475c611591114a2a6d057c80599eef8d79e60a', 'APROBADO', 1, 160, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('1585c963-7cff-43af-82b3-b45cfa507f0b', 'diciembre_2022.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\158\\cb51d0a4cfb34de581680798481b0942_diciembre_2022.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, '42831de2e45ba55c23346e0725ec400b5b8ff1fadd9af3e9f3e4c224213b9473', 'PENDIENTE', 2, 158, '[]'),
('1c3dd3f4-53b4-4451-81f3-afa8101a0443', 'facturas_mcarranza_07_2025.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\162\\5bfec0b156504081928fb1e84c356290_facturas_mcarranza_07_2025.pdf', 'FACTURA', 0.4, 'La primera página contiene indicadores de factura: factura, importe. La evidencia es limitada y se requiere revisión.', 1, 'ab787ace3a9c0253d26004413d813c535f269ab93257b6a85db3580dd4e4fcb7', 'PENDIENTE', 1, 162, '[\"factura\", \"importe\"]'),
('22b56283-5b5b-458c-bdc5-822083738017', 'pago_achocalla_2020.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\166\\62ac9802ffc047dbaf4db6c211652f0d_pago_achocalla_2020.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, '4c8a45d523e697216cf849fa9ce3fb5d726de09805460b6128579889c44cd27c', 'PENDIENTE', 3, 166, '[]'),
('22cf6c73-0520-4eeb-9ea3-f29ca43ff3cd', 'facturas_07_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\161\\c5f71e8a4af04fd0b3ad8965a6b7a501_facturas_07_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '5a262406d17a038382261f13eec00e8656a065050c3ad9c69db8b658fb71b811', 'APROBADO', 1, 161, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('2508ea07-23a4-4eec-b08c-ca8aa6aceb07', 'facturas_12_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\162\\bcebde72516a4a0b8ddc097578ff2c48_facturas_12_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '9eda3513212203110602171f4e02d6ce70352815611a9226e780ebc8e3bed6be', 'APROBADO', 1, 162, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('3eefd48d-1c63-4fe0-a99a-2c1d497b4b70', 'Marzo_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\166\\ff7089c88af34a46adac55bfad5c92e5_Marzo_2023.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, 'f9fa63152c6a80ccbeb8970d045f66557bf6079dbd3f1f1fe345e8d154a26bcc', 'PENDIENTE', 3, 166, '[]'),
('45d927b1-aeec-4df3-bb7f-d65d109ddbde', 'facturas_01_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\158\\d6cb0e45e9f8474790c5b373f87937d2_facturas_01_2024.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '6802b04775f19c46135a9f98ea1b8ae90a81c7619c27ca4c26f581c876862e94', 'APROBADO', 2, 158, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('4cd8e6e3-567d-45b1-8d46-d455403cddf9', 'facturas_01_2022.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\158\\4dd4569b94bf4bb2a7076f261b1a3403_facturas_01_2022.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '102ea36397d768e4968853500aa7c422e9cb5a47a24eadde5c28bf37d41d25b5', 'APROBADO', 2, 158, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('4e57cfd8-ac91-4908-b49a-05badc6949e1', 'lista_ongs_2.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\166\\023bab5a72b140e9bfa5171eecc9bebb_lista_ongs_2.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, 'c8a1e1e136f5f68a896082b5b832ca0b40f40920bcdc1b2586e62a4112f3c2e8', 'PENDIENTE', 3, 166, '[]'),
('542e0dd5-c558-481a-9b3f-2fea084ba6b4', 'facturas_11_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\161\\e541aa7a7c284b25bd202d07905899d5_facturas_11_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '892faee23da30bf34eb313c98d58daaacfae88ef97757e16e8d67c34ac7b846e', 'APROBADO', 1, 161, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('58d2eb9c-9942-4e78-af8a-682078e14d8b', 'facturas_02_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\159\\7f1e5ca4f0f94391bd75c405cd6aa155_facturas_02_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, 'af973a7d1b59f457320b0f99b2a59b6fdd1e986298baf114e1ecba6f04174860', 'APROBADO', 2, 159, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('5efedcf9-ef91-461d-bb78-29b45c946460', 'junio_2022.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\164\\c0ac824aebc34b3291b5873f408e4f1a_junio_2022.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, 'a77671a1c06358c18da7955159dd83222dc9bfd2bcdd110a12f931818bf06f7f', 'PENDIENTE', 3, 164, '[]'),
('602959a8-12ce-4f9d-8eb3-8342eaa62c48', 'contrato3.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\157\\f2da055f9b4741579b5651efb2a0f2ab_contrato3.pdf', 'CONTRATO', 0.6, 'La primera página contiene indicadores de contrato: CONTRATO, CÓDIGO, OBJETO DEL CONTRATO.', 0, '7b4716ce62b02d8c931588af2201a676f115c02125980c820e52e863efa70ff3', 'APROBADO', 2, 157, '[\"CONTRATO\", \"CÓDIGO\", \"OBJETO DEL CONTRATO\"]'),
('6783dc0b-c7f3-4a54-a8fd-3c355cf7d39d', 'facturas_mcarranza_09_2025.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\162\\291acca4889a4ea290caedf2531edf05_facturas_mcarranza_09_2025.pdf', 'FACTURA', 0.4, 'La primera página contiene indicadores de factura: factura, importe. La evidencia es limitada y se requiere revisión.', 1, '07f2bfeeeeebaf40f056931798c65aa2e7559d9803194403d388ee7a225d6b57', 'PENDIENTE', 1, 162, '[\"factura\", \"importe\"]'),
('6af756fa-eeec-44f5-809a-3bff23369d06', 'facturas_02_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\159\\f2ca406b39984c25a72a18d3ac96d742_facturas_02_2024.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '7c499c9850b6edc3ca14618f1a0c585e10d9a2060218d1af241c1b0a5164d7f2', 'APROBADO', 2, 159, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('6c1be796-460e-4c4e-b34a-1b227b437c70', 'contrato1.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\157\\417d5ffdd2ba4201bf66a6ed0067401e_contrato1.pdf', 'CONTRATO', 0.8, 'La primera página contiene indicadores de contrato: CONTRATO, CÓDIGO, OBJETO DEL CONTRATO, PARTES CONTRATANTES.', 0, 'd1600f437d5d3b762af0c2fd2a309fdf617b19eb8fab5aa7afd52aecc0445064', 'APROBADO', 2, 157, '[\"CONTRATO\", \"CÓDIGO\", \"OBJETO DEL CONTRATO\", \"PARTES CONTRATANTES\"]'),
('6de35e4c-1c6c-478b-82e3-92fbe59dcb38', 'facturas_mcarranza_11_2025.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\164\\6a6e9a9ca1414dfd99967d9ff58cc429_facturas_mcarranza_11_2025.pdf', 'FACTURA', 0.4, 'La primera página contiene indicadores de factura: factura, importe. La evidencia es limitada y se requiere revisión.', 1, '2362e58e33ef525c8cc89da18935301437ed2cc0ea17baa4119817615a6e2a3e', 'PENDIENTE', 3, 164, '[\"factura\", \"importe\"]'),
('73e9726b-5817-4c21-a882-64bbc4183d85', 'facturas_08_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\161\\f834416851654e8eba9bf748c29d8db8_facturas_08_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '13b9a802a9b8bda4c503b82540cba25e261b554efa9fd2f9b9c5c86ace33c438', 'APROBADO', 1, 161, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('86e54f27-0d8e-4416-8b31-0cfefa797bf2', 'facturas_02_2022.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\159\\47446867f9e542acb07efd5698490008_facturas_02_2022.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '5311e164b9a069a536bb8be9b36ffc7a24e76d2e33579342f0cfcfe3cd9ada55', 'APROBADO', 2, 159, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('8d83f6a2-2fda-48d2-ad60-1775fb1d8d90', 'facturas_06_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\160\\aca133766e69478985084c5be5448855_facturas_06_2024.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, 'e385e9b0ba6e5e250b3335051d2477b9aaf19eea9645de707e7708925854b7e9', 'APROBADO', 1, 160, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('9214fdf8-cfc0-47db-b9ea-07ef04bd5913', 'facturas_12_2022.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\162\\1fccd92ab15843bd846fd468dcb5f71c_facturas_12_2022.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, 'ed1b4563b53156cf148c677d8325c27eb0dd2657d4d7f56404d266873345f2fe', 'APROBADO', 1, 162, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('9bcc1a40-0e95-4b03-889a-2cabd519826d', 'DICIEMBRE_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\158\\b7ec261e6bcf45c5898c6d93e3364eae_DICIEMBRE_2024.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, '1b7ea6f5f9a43d9861efd5bd23437d00aea215f7ef92be5e9c7c5ca510cf395e', 'PENDIENTE', 2, 158, '[]'),
('a1e76db9-f8fe-4ef8-957f-d577a59b1fd0', 'facturas_01_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\158\\58875f56b5eb477ca944b2abda4509fd_facturas_01_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '96520fa05001e9cacfaccf543ae04f333b60b0d4acfb73b0b820de9bf0d1ff85', 'APROBADO', 2, 158, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('ae897ed3-f018-456f-a16a-e8285a51bccb', 'Junio_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\164\\242c053e66db4fcca6bd43954ed68f5c_Junio_2024.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, '6809194525648c0c318cbda6797e7a6cf250293bd921fe23336bf33c457ef33a', 'PENDIENTE', 3, 164, '[]'),
('b634d2b7-24ce-419a-9fd4-87fb41a3b5cf', 'Junio_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\164\\1017666777794312a1e2a910a61a0e88_Junio_2023.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, '1b787c6d4864fbbaa23e135091e3764b339a27548ec29971f591263b7c726721', 'PENDIENTE', 3, 164, '[]'),
('b70b40e7-b824-4373-8973-7f48592cac39', '100-Cliente-1.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\157\\64e854dd791d4f9898f5bfc5257aa131_100-Cliente-1.pdf', 'FACTURA', 0.8, 'La primera página contiene indicadores de factura: factura, n° de factura, facturar a, importe.', 0, 'cce11b7fe0b5e5ec58ba7924029cfb24145c1672376cd153eb07964fb8ba6321', 'APROBADO', 2, 157, '[\"factura\", \"n° de factura\", \"facturar a\", \"importe\"]'),
('bea19df4-75cd-4146-a79e-ee83c46e7616', 'contrato2.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\157\\820014a2243e4fe8a2865f9a65c75417_contrato2.pdf', 'CONTRATO', 0.6, 'La primera página contiene indicadores de contrato: CONTRATO, CÓDIGO, OBJETO DEL CONTRATO.', 0, '5f071ed4a1f818e10a2c89ed0bbac657822ddd7872e41e362fe8de17697ce828', 'APROBADO', 2, 157, '[\"CONTRATO\", \"CÓDIGO\", \"OBJETO DEL CONTRATO\"]'),
('c15e348a-34d1-4105-bd88-626ef777a908', 'MARZO_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\166\\3c6743c06cd448acb3d6e40f5699c25f_MARZO_2024.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, '86e0b31d218433fe3dcbb1e0966cd42ad0a6dcfbb9a80b0625de9c59d33cd448', 'PENDIENTE', 3, 166, '[]'),
('c79acc58-3166-4031-8fa3-3d2b1ac41a98', 'facturas_mcarranza_08_2025.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\162\\fce8b63edd3d4d6d81de0ecea0e0e0fb_facturas_mcarranza_08_2025.pdf', 'FACTURA', 0.4, 'La primera página contiene indicadores de factura: factura, importe. La evidencia es limitada y se requiere revisión.', 1, '9ab5e4b8c2bcf1c5dd9912d5941dc17fea7e218ff85f8e44b28830e25da4a110', 'PENDIENTE', 1, 162, '[\"factura\", \"importe\"]'),
('cba1cb14-ab58-484e-83d7-188a120302fe', 'facturas_06_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\160\\ae8a952026924164b8ff65c93a4e8228_facturas_06_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, 'd3e807d54aa3acad8a2809b0531d0c90114b165ce3d09d7435df0d432b7212f1', 'APROBADO', 1, 160, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('d318ea67-b927-478a-a172-5b969549da22', 'facturas_04_2022.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\159\\dc6a54e4b31749edb9f93018091ffdab_facturas_04_2022.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '5ed68a5ff4896a1ad18b381950bde5ae018b75d374cd9d98837562ade0e551ba', 'APROBADO', 2, 159, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('d4139de4-3e9e-4b0c-8698-cdbbdf37228b', 'facturas_05_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\160\\56632d8171fa4f74bba76fd26b3232db_facturas_05_2024.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '30dc4cb993f8bb9a40e4a970f87b18bd5b2b542055f1019a8e7fadd1bb1ad0ac', 'APROBADO', 1, 160, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('d728ea21-e242-4ff2-aad5-469933860120', 'facturas_08_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\161\\47941ca081a54a0eb0293a1f93f53951_facturas_08_2024.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, '8392d598828a2d9fb1729d656c6bea076fbe0723402b882f9d9c080062ef06ed', 'APROBADO', 1, 161, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('e942f81f-e1d5-4728-8c6d-e6abc36d844e', '101-Cliente-2.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\157\\f8acb4b3f68041918948ba2ec361af03_101-Cliente-2.pdf', 'FACTURA', 0.8, 'La primera página contiene indicadores de factura: factura, n° de factura, facturar a, importe.', 0, '7bd1653578fb306be00acd22f07c0f4348851a35f5120fab53c3c41d8ab3f04e', 'APROBADO', 2, 157, '[\"factura\", \"n° de factura\", \"facturar a\", \"importe\"]'),
('eae107dc-346e-493c-ba48-74fd0c86e370', 'facturas_03_2024.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\159\\24f5fb38dd4c457c8a2ec606b42509a4_facturas_03_2024.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, 'd08f58a8ef6ff55c92b3511151ef68ec2b2e2420a628f2566ac1a4aba3f36634', 'APROBADO', 2, 159, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]'),
('f1e72330-2fde-426d-bcd3-eae6d43da064', 'marzo_2022.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\166\\318b337432364282a6b2ba1671244589_marzo_2022.pdf', 'OTRO', 0, 'La primera página no contiene indicadores suficientes de factura, contrato, formulario 110.', 1, '6627f6fee9a045e094156c52478095a51f3174a0ad2c800767e318b111b35e02', 'PENDIENTE', 3, 166, '[]'),
('f38ac282-6ef9-4690-9a5e-40ca12e61d80', 'facturas_mcarranza_10_2025.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\164\\be8cb88360414750942564eb6b293631_facturas_mcarranza_10_2025.pdf', 'FACTURA', 0.4, 'La primera página contiene indicadores de factura: factura, importe. La evidencia es limitada y se requiere revisión.', 1, '6d610a69d207f5ab213f49310c42aa7fcf073443a71ab1cbcc6c6e3189c6fa9f', 'PENDIENTE', 3, 164, '[\"factura\", \"importe\"]'),
('fa865ad9-7a9b-4fe7-b9be-53690e742b0f', 'facturas_09_2023.pdf', 'C:\\marioc\\webs_figma\\pdf_classifier\\backend\\uploads\\161\\f9b7ee6de367435d938c71544aaca206_facturas_09_2023.pdf', 'FORMULARIO 110', 0.8, 'La primera página contiene indicadores de formulario 110: Funcionario Dependiente, Anexo al Form 610, Anexo al Form 702, Anexo al Form 510.', 0, 'e66e6c722026e3badd4958e73ca2a26e3a95723172a84983dd3400322c7063b2', 'APROBADO', 1, 161, '[\"Funcionario Dependiente\", \"Anexo al Form 610\", \"Anexo al Form 702\", \"Anexo al Form 510\"]');

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
  ADD KEY `ix_batches_user_id` (`user_id`);

--
-- Indices de la tabla `documents`
--
ALTER TABLE `documents`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `uq_documents_hash_archivo` (`hash_archivo`),
  ADD KEY `ix_documents_hash_archivo` (`hash_archivo`),
  ADD KEY `ix_documents_user_id` (`user_id`),
  ADD KEY `documents_batch_id_fk` (`batch_id`);

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
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=168;

--
-- AUTO_INCREMENT de la tabla `roles`
--
ALTER TABLE `roles`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT de la tabla `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=68;

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
-- Filtros para la tabla `user_roles`
--
ALTER TABLE `user_roles`
  ADD CONSTRAINT `user_roles_role_id_fk` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `user_roles_user_id_fk` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
