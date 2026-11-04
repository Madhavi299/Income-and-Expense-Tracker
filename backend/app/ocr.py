import io
import os
import re
from datetime import date, datetime
from pathlib import Path
from PIL import Image
import fitz
import pytesseract
from pdf2image import convert_from_bytes

def extract_text(file_name: str, content: bytes) -> str:
    suffix = Path(file_name).suffix.lower()
    if suffix == ".pdf":
        document = fitz.open(stream=content, filetype="pdf")
        text = "\n".join(page.get_text("text") for page in document).strip()
        if text:
            return text
        # Scanned PDF: OCR each page (requires Poppler on Windows).
        try:
            pages = convert_from_bytes(content, dpi=250)
            return "\n".join(pytesseract.image_to_string(page) for page in pages).strip()
        except Exception as exc:
            raise ValueError("This looks like a scanned PDF. Install Poppler and Tesseract, or upload a bill image.") from exc
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
        tesseract_cmd = os.getenv("TESSERACT_CMD", "")
        if tesseract_cmd and os.path.exists(tesseract_cmd):
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        return pytesseract.image_to_string(Image.open(io.BytesIO(content))).strip()
    raise ValueError("Upload a PDF, PNG, JPG, JPEG, WEBP, BMP, TIF, or TIFF bill.")

def guess_fields(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = next((line[:200] for line in lines if len(line) >= 3), "Uploaded bill")
    # Prefer values near total-like labels, otherwise use the largest currency-like number.
    amount = None
    patterns = [
        r"(?i)(?:grand\s+total|total\s+amount|amount\s+due|net\s+amount|total|paid)\s*[:\-]?\s*(?:₹|rs\.?|inr)?\s*([0-9,]+(?:\.[0-9]{1,2})?)",
        r"(?:₹|rs\.?|inr)\s*([0-9,]+(?:\.[0-9]{1,2})?)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            try:
                amount = max(float(value.replace(",", "")) for value in matches if float(value.replace(",", "")) > 0)
                break
            except ValueError:
                pass
    found_date = date.today().isoformat()
    date_match = re.search(r"\b(20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/](?:20)?\d{2})\b", text)
    if date_match:
        raw = date_match.group(1)
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y", "%m/%d/%Y"):
            try:
                found_date = datetime.strptime(raw, fmt).date().isoformat()
                break
            except ValueError:
                continue
    lower = text.lower()
    if any(word in lower for word in ["grocery", "supermarket", "vegetable", "milk", "rice"]):
        category = "Groceries"
    elif any(word in lower for word in ["restaurant", "cafe", "hotel", "food", "pizza", "swiggy", "zomato"]):
        category = "Food"
    elif any(word in lower for word in ["petrol", "fuel", "diesel", "uber", "ola", "bus", "train"]):
        category = "Transport"
    elif any(word in lower for word in ["electricity", "water bill", "internet", "broadband", "mobile recharge"]):
        category = "Utilities"
    elif any(word in lower for word in ["pharmacy", "hospital", "medical", "clinic"]):
        category = "Healthcare"
    else:
        category = "Other"
    return {"title": title, "amount": amount, "transaction_type": "Expense", "category": category, "transaction_date": found_date, "description": text[:4000]}
