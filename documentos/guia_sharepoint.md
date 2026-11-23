# Guía de SharePoint de FaroNorte

> **Documento de práctica.** FaroNorte es una empresa ficticia. Las normas que aparecen aquí se han redactado expresamente para probar un sistema RAG simple.

**Versión:** noviembre de 2026  
**Área responsable:** Sistemas y colaboración digital

## 1. Estructura de sitios

En FaroNorte existen tres sitios principales de SharePoint:

- **Proyectos**: contiene documentación activa de los equipos y sus entregables.
- **Plantillas**: reúne modelos oficiales para informes, actas y solicitudes.
- **Comunicación**: publica noticias, avisos generales y procedimientos comunes.

Cada proyecto tiene una biblioteca con el mismo nombre que su código interno. Por ejemplo, el proyecto `PRJ-AURORA` utiliza la biblioteca `PRJ-AURORA` dentro del sitio Proyectos. Los archivos finales se guardan en la carpeta `Entregables`; los borradores, en `Trabajo`.

## 2. Niveles de permisos

Los permisos se asignan **mediante grupos**, no usuario a usuario:

- **Lectores**: pueden consultar y descargar documentos, pero no modificarlos.
- **Editores**: pueden crear y modificar documentos dentro de la biblioteca asignada.
- **Responsables**: pueden gestionar miembros y configurar la biblioteca, siempre dentro de las normas de sistemas.

Para solicitar el nivel Editores o Responsables se abre una petición en **Mesa Faro** indicando la biblioteca, el motivo y el plazo. Se necesita la aprobación del responsable del área. El equipo de sistemas tramita la petición después de esa aprobación. La guía no autoriza a compartir enlaces públicos sin revisión.

## 3. Subir y localizar documentación

1. Accede al sitio Proyectos con la cuenta corporativa y completa la MFA si se solicita.
2. Abre la biblioteca correspondiente al código de proyecto.
3. Para documentos en elaboración utiliza la carpeta `Trabajo`.
4. Para archivos revisados utiliza la carpeta `Entregables`.
5. Nombra los archivos siguiendo el patrón `PROYECTO_tipo_fecha_version`, por ejemplo `AURORA_acta_2026-11-18_v02.docx`.

Antes de subir un archivo hay que comprobar que no contiene contraseñas ni datos personales que no sean necesarios. Se recomienda utilizar títulos descriptivos para facilitar las búsquedas.

## 4. Historial de versiones

SharePoint conserva el historial de versiones de los documentos de bibliotecas de trabajo. Si alguien sobrescribe información por error, debe abrir el archivo, consultar **Historial de versiones** y seleccionar la versión anterior adecuada. Restaurar una versión genera una nueva entrada en el historial, en lugar de eliminar todas las anteriores.

Cuando un archivo se elimina, se puede recuperar desde la papelera del sitio **durante los primeros 45 días**, según la norma ficticia de FaroNorte. Pasado ese plazo se debe abrir una solicitud a sistemas, aunque la recuperación no está garantizada.

## 5. Compartición y colaboración

Para colaborar con personal interno se recomienda compartir el enlace restringido a **Personas con acceso existente**. Si un compañero necesita permisos nuevos, debe solicitarlos por Mesa Faro; el hecho de recibir un enlace no sustituye una autorización.

La compartición con personas externas está deshabilitada por defecto. Para habilitarla en un proyecto concreto hay que justificar el motivo, definir una fecha de caducidad y obtener autorización del área de seguridad. No se permiten vínculos de tipo «Cualquier persona con el enlace».

## 6. Incidencias habituales

**No puedo editar un documento:** comprueba si perteneces al grupo Lectores. Si es así, solicita el grupo Editores por Mesa Faro, en lugar de pedir que otra persona te comparta sus credenciales.

**He borrado un archivo:** revisa la papelera del sitio y el plazo interno de 45 días. Si no aparece, abre un ticket detallando biblioteca, ruta y nombre aproximado.

**Hay dos personas editando:** utiliza la edición conjunta si el formato lo permite. Evita descargar y volver a subir múltiples copias con nombres ambiguos como `final_final2.docx`.

## 7. Fuera de alcance

Este documento no establece costes de Microsoft 365, contratos de proveedores ni niveles de prioridad para caídas generales de red. Para prioridades de incidencias hay que consultar el manual de soporte.
