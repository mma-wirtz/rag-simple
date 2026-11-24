# RAG simple con BGE-M3, ChromaDB, Gemini y Ollama

Proyecto académico de recuperación aumentada por generación (*Retrieval-Augmented Generation*, RAG). He desarrollado un asistente que responde preguntas a partir de una colección de documentos de una empresa ficticia llamada **FaroNorte**.

El sistema sigue un **RAG simple**, sin agentes ni mecanismos de RAG reflexivo: carga documentos, los divide en fragmentos, calcula embeddings, recupera los más relevantes y utiliza un modelo de lenguaje para redactar la respuesta.

## 1. Objetivo y documentación

El objetivo es realizar consultas sobre documentos de distintos formatos, utilizando recuperación semántica en lugar de enviar todos los archivos al modelo en cada pregunta.

He elaborado cuatro documentos ficticios para la práctica:

| Documento | Formato | Contenido |
|---|---|---|
| `manual_incidencias.pdf` | PDF | Registro de incidencias, prioridades P1–P4 y plazos de atención |
| `politica_seguridad.docx` | DOCX | Contraseñas, accesos, MFA y seguridad de dispositivos |
| `guia_sharepoint.md` | Markdown | Bibliotecas, niveles de permisos y colaboración |
| `preguntas_frecuentes.txt` | TXT | Preguntas habituales sobre servicios y soporte informático |

La lectura del PDF genera una unidad de texto por página. Con estos cuatro archivos obtengo **cinco unidades de texto** antes de aplicar el chunking.

## 2. Tecnologías utilizadas

- **Python:** implementación de los scripts y del chat por consola.
- **LangChain:** objetos `Document`, chunking recursivo e integración con los LLM.
- **BGE-M3 (`BAAI/bge-m3`):** embeddings de 1024 dimensiones, tanto para documentos como para preguntas.
- **ChromaDB:** almacenamiento persistente y búsqueda vectorial mediante distancia coseno.
- **Gemini (`gemini-3.5-flash-lite`):** generación de respuestas a través del proxy proporcionado por el centro.
- **Qwen (`qwen3:4b-instruct`):** alternativa local mediante Ollama.
- **pypdf y python-docx:** extracción de contenido de PDF y Word.

## 3. Estructura del proyecto

```text
rag-simple/
├── documentos/
│   ├── guia_sharepoint.md
│   ├── manual_incidencias.pdf
│   ├── politica_seguridad.docx
│   └── preguntas_frecuentes.txt
├── evidencias/                 # Capturas y CSV de las pruebas
├── indexar.py                  # Lectura, chunking, embeddings y ChromaDB
├── chat.py                     # Consultas, recuperación y generación
├── comparar_chunks.py         # Comparación de tamaños y solapamientos
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Las carpetas `.venv/` y `chroma_rag/`, así como el archivo `.env`, se generan o configuran localmente y se excluyen del repositorio mediante `.gitignore`.

## 4. Instalación y configuración

He desarrollado y probado el proyecto en **WSL (Ubuntu)**. Desde la carpeta del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Modelos de lenguaje

Para utilizar **Gemini**, creo un archivo `.env` a partir de `.env.example` y configuro el token y la URL del proxy que proporciona el centro:

```dotenv
GOOGLE_API_KEY=TOKEN_DEL_CENTRO
GOOGLE_GEMINI_BASE_URL=URL_DEL_PROXY_DEL_CENTRO
GEMINI_MODEL=gemini-3.5-flash-lite
OLLAMA_MODEL=qwen3:4b-instruct
```

Para usar **Qwen** en local, se necesita tener Ollama funcionando y el modelo descargado:

```bash
ollama pull qwen3:4b-instruct
ollama list
```

La primera ejecución de BGE-M3 puede descargar los pesos del modelo desde Hugging Face.

## 5. Cómo funciona el RAG

### 5.1. Lectura y chunking

En `indexar.py` leo los archivos PDF, DOCX, TXT y MD. Conservo metadatos como el nombre del archivo de origen y, cuando corresponde, el número de página.

A continuación divido el contenido con `RecursiveCharacterTextSplitter`. Después de comparar varias opciones, he elegido:

```python
chunks = chunkenizar(documentos, tamano=900, solapamiento=150)
```

Utilizo **900 caracteres por chunk** y **150 caracteres de solapamiento** como parámetros de configuración. El separador recursivo intenta respetar párrafos, saltos de línea, frases y espacios; por ello, el solapamiento efectivo no tiene que ser exactamente de 150 caracteres en todos los pares de fragmentos.

Con esta configuración obtengo **22 chunks**.

### 5.2. Embeddings y almacenamiento

Con `SentenceTransformer("BAAI/bge-m3")` convierto los 22 fragmentos en embeddings normalizados de **1024 dimensiones** y los almaceno en la colección `documentos_rag` de ChromaDB.

La base se guarda en `chroma_rag/`, de modo que el chat puede reutilizarla sin volver a indexar en cada ejecución.

Para crear o reconstruir la base:

```bash
python indexar.py
```

**Aviso:** ejecutar de nuevo `indexar.py` reemplaza la colección `documentos_rag` existente. Debe volver a ejecutarse si cambio los documentos o los parámetros de chunking que quiero utilizar en el chat.

### 5.3. Recuperación y respuesta

Al iniciar `chat.py` puedo seleccionar **Gemini** o **Qwen**. Para cada pregunta:

1. Genero su embedding con el mismo modelo BGE-M3.
2. Busco en ChromaDB los **cinco chunks más cercanos** (`TOP_K = 5`).
3. Calculo la similitud como `1 - distancia_coseno` y filtro con un umbral inicial de **0,50**.
4. Envío al LLM la pregunta junto con los fragmentos aceptados.
5. Muestro la respuesta y los documentos recuperados, sin duplicar el mismo archivo y página.

El prompt indica al modelo que responda con el contexto disponible y que reconozca cuando la información no figura en los documentos. Esto ayuda a reducir respuestas inventadas, pero no constituye una garantía absoluta. El umbral de similitud es una heurística, **no una probabilidad de que la respuesta sea correcta**.

Para iniciar el chat:

```bash
python chat.py
```

Se selecciona la opción `1` (Gemini) o `2` (Qwen), se introducen las preguntas y se escribe `salir` para terminar.

## 6. Pruebas funcionales

Probé el sistema con preguntas documentadas y con una pregunta cuya respuesta no aparece en los archivos:

| Pregunta | Resultado observado con `TOP_K = 5` |
|---|---|
| ¿Qué permisos tiene un lector en SharePoint? | Respuesta correcta: consultar y descargar, sin modificar |
| ¿Cuáles son los niveles de prioridad de las incidencias informáticas? | Respuesta correcta: P1, P2, P3 y P4 |
| ¿Cuál es el menú de la cafetería de FaroNorte? | El asistente indica que no encuentra esa información |

Realicé estas pruebas con **Qwen** y **Gemini**. Ambos dieron las respuestas esperadas. En las ejecuciones observadas, Gemini respondió perceptiblemente más rápido; no realicé una medición sistemática de latencia.

Inicialmente, con `TOP_K = 3`, la pregunta sobre prioridades produjo una respuesta incompleta. Al ampliar la recuperación a **cinco chunks**, se incluyó el fragmento que contenía la información de P4 y ambos modelos respondieron correctamente.

En la pregunta de la cafetería, el primer resultado tenía una similitud aproximada de **0,532**, pero no contenía la respuesta. El modelo rechazó correctamente la consulta. Esto demuestra que recuperar un fragmento relativamente cercano **no equivale a tener evidencia suficiente para responder**.

## 7. Comparación de tamaños y solapamientos

En `comparar_chunks.py` he probado cinco configuraciones utilizando los mismos documentos, BGE-M3 y cuatro preguntas. Para cada configuración creo una colección **temporal** de ChromaDB, por lo que no modifico la base persistente utilizada por `chat.py`.

La comparación evalúa si se recuperan los archivos esperados y si los fragmentos recuperados contienen determinadas palabras clave. **No evalúa la calidad de la respuesta generada por el LLM.**

| Tamaño / solapamiento | Chunks | Tamaño medio | Fuentes esperadas recuperadas | Términos P1–P4 |
|---|---:|---:|---:|---:|
| 500 / 0 | 43 | 371,0 | 3/3 | 3/4 |
| 500 / 100 | 44 | 376,5 | 3/3 | 3/4 |
| 900 / 0 | 22 | 726,7 | 3/3 | 3/4 |
| **900 / 150** | **22** | **749,0** | **3/3** | **4/4** |
| 1500 / 250 | 15 | 1124,3 | 3/3 | 4/4 |

**Conclusión:** mantengo `900/150` porque permite recuperar los cuatro términos de prioridad, conserva fragmentos más acotados que `1500/250` y no aumenta el número de chunks frente a `900/0`. Es una elección razonable para esta documentación y estas pruebas, **no una configuración universalmente óptima**.

Para repetir la comparación:

```bash
python comparar_chunks.py
```

El script guarda `evidencias/resumen_chunks.csv` y `evidencias/detalle_chunks.csv`, además de imprimir los resultados por consola.

## 8. Limitaciones y posibles mejoras

- La pertinencia de los chunks se aproxima mediante similitud coseno y un umbral fijo; un documento irrelevante puede superar dicho umbral.
- Una respuesta completa depende de que la recuperación incluya los fragmentos necesarios y de que el LLM los interprete correctamente.
- Los resultados dependen de una colección de documentos pequeña y ficticia; no permiten generalizar a otros corpus.
- El sistema utiliza una interfaz de terminal y no incorpora agentes, evaluación automática de respuestas ni RAG reflexivo (esto será parte del siguiente proyecto).

## 9. Evidencias y entrega

Las capturas de las interacciones con el chat y de la comparación de chunking se incluyen en el **PDF de evidencias** de la entrega. Los CSV permiten consultar las métricas utilizadas en la tabla de comparación.

La entrega comprende el código Python, los cuatro documentos de ejemplo, las dependencias y el PDF de capturas explicadas.

---

**Repositorio:** https://github.com/mma-wirtz/rag-simple
