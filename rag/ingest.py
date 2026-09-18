from pathlib import Path
import json
import re
from lxml import etree


PROJECT_ROOT = Path(__file__).resolve().parent.parent

PHP_DOCS = PROJECT_ROOT / "knowledge_base" / "php"
OUTPUT_DIR = PROJECT_ROOT / "knowledge_base" / "chunks"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


# Only ingest documentation that is useful for our PHP coding agent.
ALLOWED_PATHS = [
    "language",
    "features",
    "security",
]

ALLOWED_REFERENCE_MODULES = [
    "array",
    "curl",
    "datetime",
    "filesystem",
    "filter",
    "json",
    "mysqli",
    "mysql",
    "password",
    "pdo",
    "pdo_mysql",
    "session",
    "strings",
]


def is_relevant_file(xml_file: Path) -> bool:
    """Return True if the XML file belongs to our initial PHP knowledge base."""

    relative_path = xml_file.relative_to(PHP_DOCS)
    parts = relative_path.parts

    if not parts:
        return False

    # language/, features/, security/
    if parts[0] in ALLOWED_PATHS:
        return True

    # Selected reference/<extension>/...
    if parts[0] == "reference" and len(parts) >= 2:
        return parts[1] in ALLOWED_REFERENCE_MODULES

    return False


def clean_text(text: str) -> str:
    """Normalize whitespace."""

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_xml_text(xml_file: Path) -> str:
    """Extract readable text from PHP documentation XML."""

    try:
        parser = etree.XMLParser(
            recover=True,
            load_dtd=False,
            no_network=True,
            resolve_entities=False,
        )

        tree = etree.parse(str(xml_file), parser)

        parts = []

        for element in tree.iter():

            if element.text:
                text = clean_text(element.text)

                if text:
                    parts.append(text)

            if element.tail:
                text = clean_text(element.tail)

                if text:
                    parts.append(text)

        return " ".join(parts)

    except Exception as exc:
        print(f"[WARNING] Could not parse {xml_file}: {exc}")
        return ""

def create_chunks(text: str) -> list[str]:
    """Create overlapping text chunks."""

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):

        end = start + CHUNK_SIZE

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def process_documents() -> None:
    """Process relevant PHP documentation into JSONL chunks."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    output_file = OUTPUT_DIR / "php_chunks.jsonl"

    all_xml_files = list(PHP_DOCS.rglob("*.xml"))

    relevant_files = [
        file
        for file in all_xml_files
        if is_relevant_file(file)
    ]

    print(f"Total XML files found     : {len(all_xml_files)}")
    print(f"Relevant XML files       : {len(relevant_files)}")

    total_chunks = 0
    processed_files = 0

    with output_file.open("w", encoding="utf-8") as output:

        for xml_file in relevant_files:

            text = extract_xml_text(xml_file)

            if not text:
                continue

            chunks = create_chunks(text)

            relative_path = xml_file.relative_to(PHP_DOCS)

            for index, chunk in enumerate(chunks):

                record = {
                    "id": f"{relative_path.as_posix()}::{index}",
                    "text": chunk,
                    "source": relative_path.as_posix(),
                    "type": "php_documentation",
                    "chunk_index": index,
                }

                output.write(
                    json.dumps(
                        record,
                        ensure_ascii=False
                    ) + "\n"
                )

                total_chunks += 1

            processed_files += 1

    print()
    print("Ingestion completed.")
    print(f"Files processed           : {processed_files}")
    print(f"Chunks created            : {total_chunks}")
    print(f"Output                    : {output_file}")


if __name__ == "__main__":
    process_documents()