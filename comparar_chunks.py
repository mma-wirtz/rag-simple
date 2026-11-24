import csv
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from indexar import cargar_documentos, chunkenizar


# Configuraciones que vamos a comparar (caracteres)
CONFIGURACIONES = [
    (500, 0),
    (500, 100),
    (900, 0),
    (900, 150),
    (1500, 250),
]

TOP_K = 5
UMBRAL_SIMILITUD = 0.50
RESULTADOS_DIR = Path(__file__).resolve().parent / "evidencias"

# En estas preguntas sabemos en qué archivo debería estar la respuesta.
# La última sirve para observar qué ocurre con una pregunta no documentada.
PRUEBAS = [
    {
        "nombre": "Permisos SharePoint",
        "pregunta": "¿Qué permisos tiene un lector en SharePoint?",
        "fuente_esperada": "guia_sharepoint.md",
        "terminos": ["lectores", "consultar", "descargar"],
    },
    {
        "nombre": "Prioridades",
        "pregunta": "¿Cuáles son los niveles de prioridad de las incidencias informáticas?",
        "fuente_esperada": "manual_incidencias.pdf",
        "terminos": ["P1", "P2", "P3", "P4"],
    },
    {
        "nombre": "Dispositivo perdido",
        "pregunta": "¿Qué debo hacer si pierdo un dispositivo corporativo?",
        "fuente_esperada": "politica_seguridad.docx",
        "terminos": ["dispositivo", "Mesa Faro"],
    },
    {
        "nombre": "Pregunta sin documentar",
        "pregunta": "¿Cuál es el menú de la cafetería de FaroNorte?",
        "fuente_esperada": None,
        "terminos": [],
    },
]


def guardar_csv(nombre, filas):
    if not filas:
        return
    ruta = RESULTADOS_DIR / nombre
    with ruta.open("w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)
    print(f"CSV guardado: {ruta}")


def main():
    RESULTADOS_DIR.mkdir(exist_ok=True)

    # Reutilizamos la lectura y el chunking ya implementados en indexar.py.
    documentos = cargar_documentos()
    if not documentos:
        print("No se han encontrado documentos para comparar.")
        return

    print("\nCargando BGE-M3 una sola vez...")
    modelo_emb = SentenceTransformer("BAAI/bge-m3")

    # Las preguntas son idénticas en todos los experimentos.
    preguntas = [prueba["pregunta"] for prueba in PRUEBAS]
    vectores_preguntas = modelo_emb.encode(
        preguntas, normalize_embeddings=True
    ).tolist()

    # Base de datos temporal: NO modifica chroma_rag/.
    cliente = chromadb.EphemeralClient()
    detalles = []
    resumen = []

    for tamano, solapamiento in CONFIGURACIONES:
        nombre_config = f"{tamano}/{solapamiento}"
        print(f"\n===== CONFIGURACIÓN {nombre_config} =====")

        chunks = chunkenizar(documentos, tamano=tamano, solapamiento=solapamiento)
        if not chunks:
            continue

        longitudes = [len(c.page_content) for c in chunks]
        promedio = round(sum(longitudes) / len(longitudes), 1)
        print(f"Chunks: {len(chunks)} | Tamaño medio: {promedio} caracteres")

        # Cada configuración tiene su colección independiente.
        coleccion = cliente.create_collection(
            name=f"comparacion_t{tamano}_s{solapamiento}",
            metadata={"hnsw:space": "cosine"},
        )

        textos = [c.page_content for c in chunks]
        vectores = modelo_emb.encode(
            textos,
            normalize_embeddings=True,
            batch_size=16,
            show_progress_bar=False,
        )

        coleccion.add(
            ids=[f"chunk_{i:04d}" for i in range(len(chunks))],
            embeddings=vectores.tolist(),
            documents=textos,
            metadatas=[{"doc_key": c.metadata["doc_key"]} for c in chunks],
        )

        # Consultamos todas las preguntas con los mismos parámetros.
        resultados = coleccion.query(
            query_embeddings=vectores_preguntas,
            n_results=min(TOP_K, len(chunks)),
            include=["documents", "metadatas", "distances"],
        )

        aciertos_fuente = 0
        total_evaluables = 0

        for i, prueba in enumerate(PRUEBAS):
            documentos_encontrados = resultados["documents"][i]
            metadatos = resultados["metadatas"][i]
            distancias = resultados["distances"][i]

            # Filtramos los fragmentos igual que el chat.
            validos = [
                (texto, meta, 1 - distancia)
                for texto, meta, distancia in zip(
                    documentos_encontrados, metadatos, distancias
                )
                if 1 - distancia >= UMBRAL_SIMILITUD
            ]

            fuentes = [meta["doc_key"] for _, meta, _ in validos]
            contexto = "\n".join(texto for texto, _, _ in validos).casefold()
            presentes = [
                palabra for palabra in prueba["terminos"]
                if palabra.casefold() in contexto
            ]

            fuente_esperada = prueba["fuente_esperada"]
            if fuente_esperada is not None:
                total_evaluables += 1
                recuperada = fuente_esperada in fuentes
                aciertos_fuente += int(recuperada)
                estado = "SÍ" if recuperada else "NO"
            else:
                recuperada = "No evaluable"
                estado = "Revisión manual"

            fuente_top1 = metadatos[0]["doc_key"]
            similitud_top1 = round(1 - distancias[0], 3)
            print(
                f"  {prueba['nombre']}: top1={fuente_top1} "
                f"({similitud_top1:.3f}) | fuente esperada en top{TOP_K}: {estado} "
                f"| términos: {len(presentes)}/{len(prueba['terminos'])}"
            )

            detalles.append({
                "configuracion": nombre_config,
                "pregunta": prueba["nombre"],
                "tamano_chunk": tamano,
                "solapamiento": solapamiento,
                "total_chunks": len(chunks),
                "fuente_top1": fuente_top1,
                "similitud_top1": similitud_top1,
                "fuente_esperada": fuente_esperada or "No documentada",
                "fuente_en_top5_con_umbral": recuperada,
                "chunks_sobre_umbral": len(validos),
                "terminos_en_contexto": f"{len(presentes)}/{len(prueba['terminos'])}",
                "fuentes_recuperadas": "; ".join(dict.fromkeys(fuentes)),
            })

        resumen.append({
            "configuracion": nombre_config,
            "tamano_chunk": tamano,
            "solapamiento": solapamiento,
            "total_chunks": len(chunks),
            "tamano_medio": promedio,
            "fuentes_relevantes_recuperadas": f"{aciertos_fuente}/{total_evaluables}",
        })

    print("\n===== RESUMEN FINAL =====")
    print(f"{'Tamaño/Solape':<16} {'Chunks':<10} {'Media':<10} {'Fuentes top5'}")
    for fila in resumen:
        print(
            f"{fila['configuracion']:<16} "
            f"{fila['total_chunks']:<10} "
            f"{fila['tamano_medio']:<10} "
            f"{fila['fuentes_relevantes_recuperadas']}"
        )

    guardar_csv("resumen_chunks.csv", resumen)
    guardar_csv("detalle_chunks.csv", detalles)
    print("\nComparación terminada. La base principal no se ha modificado.")


if __name__ == "__main__":  
    main()
