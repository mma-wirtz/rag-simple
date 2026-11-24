
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama


# Configuración general
BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_rag"
COLECCION = "documentos_rag"

TOP_K = 5
UMBRAL_SIMILITUD = 0.50  # Valor inicial, pendiente de ajustar


# Elegir el modelo de lenguaje
def seleccionar_modelo():
    print("\n=== ASISTENTE RAG SIMPLE ===")
    print("1. Gemini (proxy del centro)")
    print("2. Qwen3 4B (Ollama local)")

    while True:
        opcion = input("\nSelecciona un modelo (1/2): ").strip()

        if opcion == "1":
            if not os.getenv("GOOGLE_API_KEY") or not os.getenv("GOOGLE_GEMINI_BASE_URL"):
                raise ValueError("Falta configurar Gemini en el .env")

            nombre = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

            llm = ChatGoogleGenerativeAI(
                model=nombre,
                base_url=os.environ["GOOGLE_GEMINI_BASE_URL"],
                max_output_tokens=1024
            )

            return llm, nombre

        elif opcion == "2":
            nombre = os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct")

            llm = ChatOllama(
                model=nombre,
                temperature=0
            )

            return llm, nombre

        else:
            print("Opción no válida. Introduce 1 o 2.")


# Buscar los fragmentos más relevantes
def buscar_chunks(pregunta, modelo_emb, coleccion):

    # Vectorizar la pregunta con BGE-M3
    vector = modelo_emb.encode(
        pregunta,
        normalize_embeddings=True
    ).tolist()

    # Buscar en ChromaDB
    resultados = coleccion.query(
        query_embeddings=[vector],
        n_results=min(TOP_K, coleccion.count()),
        include=["documents", "metadatas", "distances"]
    )

    encontrados = []

    for texto, metadata, distancia in zip(
        resultados["documents"][0],
        resultados["metadatas"][0],
        resultados["distances"][0]
    ):
        # La colección utiliza distancia coseno
        similitud = 1 - distancia

        extracto = " ".join(texto.split())[:250]

        print(
            f"  {metadata['doc_key']} "
            f"| similitud: {similitud:.3f}"
        )
        print(f"  Contenido: {extracto}...\n")

        if similitud >= UMBRAL_SIMILITUD:
            encontrados.append({
                "texto": texto,
                "metadata": metadata,
                "similitud": similitud
            })

    return encontrados


# Generar la respuesta utilizando el contexto recuperado
def generar_respuesta(pregunta, chunks, llm):

    contexto = "\n\n".join(
        f"[Fuente {i}: {chunk['metadata']['doc_key']}]\n"
        f"{chunk['texto']}"
        for i, chunk in enumerate(chunks, start=1)
    )

    prompt = f"""
Eres un asistente de soporte informático de FaroNorte.

Responde a la pregunta utilizando exclusivamente la información
del CONTEXTO proporcionado.

Instrucciones:
- Responde en español, de forma clara y natural.
- No inventes información ni utilices conocimientos externos.
- Si el contexto no contiene información suficiente para responder,
  indica: "No encuentro esa información en los documentos disponibles".
- Puedes explicar los pasos cuando aparezcan en la documentación.

CONTEXTO:
{contexto}

PREGUNTA:
{pregunta}

RESPUESTA:
"""

    respuesta = llm.invoke(prompt)

    return str(respuesta.text)


# Chat interactivo
def main():

    load_dotenv()

    if not CHROMA_DIR.exists():
        print("No existe la base de datos. Ejecuta primero indexar.py.")
        return

    # Seleccionar el LLM
    llm, nombre = seleccionar_modelo()
    print(f"\nModelo seleccionado: {nombre}")

    # Conectar con ChromaDB
    cliente = chromadb.PersistentClient(path=str(CHROMA_DIR))
    coleccion = cliente.get_collection(COLECCION)

    print(f"Chunks disponibles: {coleccion.count()}")

    # Cargar el mismo modelo de embeddings usado al indexar
    print("\nCargando BGE-M3...")
    modelo_emb = SentenceTransformer("BAAI/bge-m3")

    print("\nChat preparado. Escribe 'salir' para terminar.")

    while True:
        pregunta = input("\nTú: ").strip()

        if pregunta.lower() in ("salir", "exit", "quit"):
            print("Chat finalizado.")
            break

        if not pregunta:
            continue

        try:
            print("\nBuscando información...")
            chunks = buscar_chunks(pregunta, modelo_emb, coleccion)

            if not chunks:
                print("\nAsistente: No encuentro información relevante "
                      "en los documentos disponibles.")
                continue

            respuesta = generar_respuesta(pregunta, chunks, llm)

            print(f"\nAsistente: {respuesta}")

            # Si el modelo no encuentra la respuesta, no mostramos fuentes
            if "no encuentro esa información en los documentos disponibles" in respuesta.lower():
                continue

            # Evitamos mostrar varias veces el mismo archivo y página
            fuentes_mostradas = set()

            print("\nDocumentos recuperados:")

            for chunk in chunks:
                meta = chunk["metadata"]

                identificador = (
                    meta["doc_key"],
                    meta.get("page")
                )

                if identificador in fuentes_mostradas:
                    continue

                fuentes_mostradas.add(identificador)

                pagina = f" (pág. {meta['page']})" if "page" in meta else ""

                print(f"  - {meta['doc_key']}{pagina}")


        except Exception as error:
            print(f"\nError procesando la pregunta: {error}")


if __name__ == "__main__":
    main()
