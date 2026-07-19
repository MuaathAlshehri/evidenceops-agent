from pathlib import Path
import io
import fitz
import pytesseract
from PIL import Image
import re


def clean_text(raw_text: str) -> str:
    print("Cleaning text...")

    cleaned_lines = []

    for line in raw_text.splitlines():

        line = line.strip()

        if re.fullmatch(r"[\[\]()\- ]*\d+[\[\]()\- ]*", line):
            continue

        if re.fullmatch(r"[-_=.:•|/\\]+", line):
            continue

        if not line:
            continue


        line = re.sub(r"http\S+|www\.\S+","",line,)


        line = re.sub(r"\s+"," ",line,)


        line = re.sub(r"[^\u0600-\u06FFa-zA-Z0-9\s،؛؟.,:()\-]","",line,)

        line = line.strip()

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def extract_text_from_pdf(pdf_path: Path , skip_pages: int = 2) -> str:

    print(f"Processing: {pdf_path.name}")

    text = ""

    with fitz.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf, start=1):
            if page_number <= skip_pages:
                print(f"Skipping page {page_number}")
                continue

            pix = page.get_pixmap(matrix=fitz.Matrix(4, 4),alpha=False,)

            image = Image.open(io.BytesIO(pix.tobytes("png")))

            page_text = pytesseract.image_to_string(image,lang="ara+eng",config="--psm 4",)

            text += (f"\n\n--- Page {page_number} ---\n"f"{page_text}")

    return text


def process_data():
    raw_data = Path("data/raw")
    processed_data = Path("data/processed")

    processed_data.mkdir(parents=True,)

    for pdf_file in raw_data.rglob("*.pdf"):
        text = extract_text_from_pdf(pdf_file)
        text = clean_text(text)
        output_file = (processed_data/ f"{pdf_file.stem}.txt")

        output_file.write_text(text,encoding="utf-8",)

        print(f"Saved: {output_file}")


if __name__ == "__main__":
    process_data()