
from pathlib import Path

import docx
import chromadb
from sentence_transformers import SentenceTransformer
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader


# Carpeta donde tenemos los documentos
DOCS_DIR = Path(__file__).resolve().parent / "documentos"

CHROMA_DIR = Path(__file__).resolve().parent / "chroma_rag"

# Formatos admitidos
EXTENSIONES = {".txt", ".md", ".pdf", ".docx"}


# Leer archivos de texto y Markdown
def cargar_txt_md(ruta):
    try:
        texto = ruta.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        texto = ruta.read_text(encoding="cp1252", errors="replace")

    if not texto.strip():
        return []

    return [Document(
        page_content=texto,
        metadata={"source": str(ruta), "doc_key": ruta.name}
    )]


# Leer documentos PDF
def cargar_pdf(ruta):
    lector = PdfReader(str(ruta))
    documentos = []

    for numero, pagina in enumerate(lector.pages, start=1):
        texto = pagina.extract_text() or ""

        if texto.strip():
            documentos.append(Document(
                page_content=texto,
                metadata={
                    "source": str(ruta),
                    "doc_key": ruta.name,
                    "page": numero
                }
            ))

    return documentos


# Leer documentos Word
def cargar_docx(ruta):
    archivo = docx.Document(str(ruta))

    partes = [p.text for p in archivo.paragraphs if p.text.strip()]

    # Extraemos también el contenido de las tablas
    for tabla in archivo.tables:
        for fila in tabla.rows:
            celdas = [c.text.strip() for c in fila.cells if c.text.strip()]
            if celdas:
                partes.append(" | ".join(celdas))

    texto = "\n".join(partes).strip()

    if not texto:
        return []

    return [Document(
        page_content=texto,
        metadata={"source": str(ruta), "doc_key": ruta.name}
    )]


# Asociar cada extensión con su función de lectura
LECTORES = {
    ".txt": cargar_txt_md,
    ".md": cargar_txt_md,
    ".pdf": cargar_pdf,
    ".docx": cargar_docx
}


# Recorrer la carpeta y cargar todos los documentos
def cargar_documentos():
    documentos = []

    for ruta in sorted(DOCS_DIR.rglob("*")):
        if not ruta.is_file():
            continue

        if ruta.name.startswith(("~$", ".")):
            continue

        extension = ruta.suffix.lower()

        if extension not in EXTENSIONES:
            continue

        try:
            nuevos = LECTORES[extension](ruta)
            documentos.extend(nuevos)

            print(f"Leído: {ruta.name} ({len(nuevos)} documentos/páginas)")

        except Exception as error:
            print(f"Error leyendo {ruta.name}: {error}")

    return documentos


# Dividir los documentos en fragmentos mediante chunking recursivo
def chunkenizar(documentos, tamano=900, solapamiento=150):

    divisor = RecursiveCharacterTextSplitter(
        chunk_size=tamano,
        chunk_overlap=solapamiento,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
        add_start_index=True
    )

    chunks = divisor.split_documents(documentos)

    return chunks



# Vectorizar los chunks y guardarlos en ChromaDB
def indexar_chunks(chunks):

    if not chunks:
        print("No hay chunks para indexar.")
        return

    # 1. Cargar el modelo de embeddings
    print("\nCargando modelo BGE-M3...")
    modelo_emb = SentenceTransformer("BAAI/bge-m3")

    # 2. Extraer los textos de los chunks
    textos = [chunk.page_content for chunk in chunks]

    # 3. Convertir los textos en vectores
    print("\nGenerando embeddings...")

    vectores = modelo_emb.encode(
        textos,
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=True
    )

    print(f"Dimensiones de los vectores: {vectores.shape}")

    # 4. Conectar con ChromaDB
    cliente = chromadb.PersistentClient(path=str(CHROMA_DIR))

    nombre_coleccion = "documentos_rag"

    # Si ya existe, la eliminamos para evitar duplicados
    if nombre_coleccion in [c.name for c in cliente.list_collections()]:
        cliente.delete_collection(nombre_coleccion)

    # Creamos una colección utilizando distancia coseno
    coleccion = cliente.create_collection(
        name=nombre_coleccion,
        metadata={"hnsw:space": "cosine"}
    )

    # 5. Preparar los metadatos de cada chunk
    metadatos = []

    for chunk in chunks:
        meta = {
            "source": chunk.metadata["source"],
            "doc_key": chunk.metadata["doc_key"],
            "start_index": chunk.metadata.get("start_index", 0)
        }

        if "page" in chunk.metadata:
            meta["page"] = chunk.metadata["page"]

        metadatos.append(meta)

    # 6. Guardar los vectores y sus textos
    coleccion.add(
        ids=[f"chunk_{i:04d}" for i in range(len(chunks))],
        embeddings=vectores.tolist(),
        documents=textos,
        metadatas=metadatos
    )

    print(f"\nChunks almacenados en ChromaDB: {coleccion.count()}")
    print(f"Base de datos guardada en: {CHROMA_DIR}")




if __name__ == "__main__":

    # 1. Cargar los documentos
    documentos = cargar_documentos()
    print(f"\nUnidades de texto cargadas: {len(documentos)}")

    # 2. Dividir los textos en chunks
    chunks = chunkenizar(
        documentos,
        tamano=900,
        solapamiento=150
    )

    print(f"Chunks generados: {len(chunks)}")

    # 3. Vectorizar y almacenar en ChromaDB
    indexar_chunks(chunks)

    print("\nIndexación finalizada correctamente.")
