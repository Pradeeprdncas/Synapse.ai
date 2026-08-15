import fitz
import docx


def extract_text(file_path: str):

    if file_path.endswith(".pdf"):
        return extract_pdf(file_path)

    if file_path.endswith(".docx"):
        return extract_docx(file_path)

    if file_path.lower().endswith((".txt", ".md", ".markdown")):
        with open(file_path, "r", encoding="utf-8") as source:
            return source.read()

    return ""


def extract_pdf(file_path: str):

    text = ""

    pdf = fitz.open(file_path)

    for page in pdf:
        text += page.get_text()

    return text


def extract_docx(file_path: str):

    text = ""

    document = docx.Document(file_path)

    for para in document.paragraphs:
        text += para.text + "\n"

    return text
