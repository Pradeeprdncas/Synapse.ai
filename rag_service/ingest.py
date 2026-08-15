import uuid
import pdfplumber
from docx import Document
from typing import List


from config import (
    MISTRAL_API_KEY,
    CHUNK_SIZE,
    CHUNK_OVERLAP
)

from utils import (
    clean_text,
    semantic_chunk_text,

)

from retriever import (
    create_collection,
    store_chunks
)

from ingest_status import (
    update_status
)

import requests

from config import (
    MISTRAL_API_KEY
)


# -----------------------------------
# PDF TEXT EXTRACTION
# -----------------------------------
def extract_pdf_text(file_path: str):

    """
    Extract text from PDF.
    """

    text = ""

    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text()

            if page_text:

                text += page_text + "\n"

    return clean_text(text)

# -----------------------------------
# EMBEDDING GENERATION
# -----------------------------------

def generate_embeddings(texts: list):

    url = "https://api.mistral.ai/v1/embeddings"

    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    embeddings = []
    BATCH_SIZE = 20  # reduce for safety

    for i in range(0, len(texts), BATCH_SIZE):

        batch = texts[i:i+BATCH_SIZE]

        payload = {
            "model": "mistral-embed",
            "input": batch
        }

        print("\n[MISTRAL REQUEST]")
        print(payload)

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )

        print("[MISTRAL STATUS]", response.status_code)
        print("[MISTRAL RESPONSE]", response.text)

        if response.status_code != 200:
            raise Exception(response.text)

        data = response.json()

        embeddings.extend([
            item["embedding"]
            for item in data["data"]
        ])

    return embeddings

# -----------------------------------
# DOCUMENT INGESTION
# -----------------------------------
def ingest_document(
    file_path: str,
    filename: str,
    collection_name: str
):

    """
    Full PDF ingestion pipeline.
    """



    try:

        # -----------------------------
        # STATUS: EXTRACTING
        # -----------------------------
        update_status(
            filename,
            "EXTRACTING"
        )

        create_collection(
            collection_name
        )

        # -----------------------------
        # EXTRACT TEXT
        # -----------------------------
        text = extract_pdf_text(
            file_path
        )

        # -----------------------------
        # STATUS: CHUNKING
        # -----------------------------
        update_status(
            filename,
            "CHUNKING"
        )

        chunks = semantic_chunk_text(
            text=text,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )

        # -----------------------------
        # STATUS: EMBEDDING
        # -----------------------------
        update_status(
            filename,
            "EMBEDDING"
        )

        embeddings = generate_embeddings(
            chunks
        )

        # -----------------------------
        # STATUS: STORING
        # -----------------------------
        update_status(
            filename,
            "STORING"
        )

        metadata_list = []

        for idx, chunk in enumerate(chunks):

            metadata_list.append({
                "filename": filename,
                "chunk_index": idx,
                "collection_name": collection_name
            })

        store_chunks(
            collection_name=collection_name,
            chunks=chunks,
            embeddings=embeddings,
            metadata_list=metadata_list
        )

        # -----------------------------
        # STATUS: COMPLETED
        # -----------------------------
        update_status(
            filename,
            "COMPLETED"
        )

        return {
            "status": "success",
            "file_name": filename,
            "chunks_created": len(chunks)
        }

    except Exception as e:

        update_status(
            filename,
            "FAILED"
        )

        raise Exception(str(e))

# -----------------------------------
# RAW TEXT INGESTION
# -----------------------------------
def ingest_text(
    text: str,
    filename: str,
    collection_name: str
):

    """
    Ingest raw extracted text.
    Used by external backend services.
    """

    try:

        create_collection(
            collection_name
        )

        chunks = semantic_chunk_text(
            text=text,
            chunk_size=CHUNK_SIZE,
            overlap=CHUNK_OVERLAP
        )

        embeddings = generate_embeddings(
            chunks
        )

        metadata_list = []

        for idx, chunk in enumerate(chunks):

            metadata_list.append({
                "filename": filename,
                "chunk_index": idx,
                "collection_name": collection_name
            })

        store_chunks(
            collection_name=collection_name,
            chunks=chunks,
            embeddings=embeddings,
            metadata_list=metadata_list
        )

        return {
            "status": "success",
            "file_name": filename,
            "chunks_created": len(chunks)
        }

    except Exception as e:

        raise Exception(str(e))


def extract_docx_text(file_path: str):

    doc = Document(file_path)

    text = "\n".join([
        para.text
        for para in doc.paragraphs
    ])

    return clean_text(text)


def extract_txt_text(file_path: str):

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:

        text = f.read()

    return clean_text(text)
