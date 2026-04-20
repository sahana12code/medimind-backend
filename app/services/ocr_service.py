import re
from io import BytesIO
from PIL import Image

try:
    import pytesseract
except Exception:  # pragma: no cover
    pytesseract = None


def extract_text_from_bytes(image_bytes: bytes) -> str:
    if pytesseract is None:
        return ""
    try:
        image = Image.open(BytesIO(image_bytes))
        return pytesseract.image_to_string(image)
    except Exception:
        return ""


def parse_medicine_text(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    name = lines[0] if lines else None

    dosage_match = re.search(r"(\d+\s?(mg|ml|mcg))", text, re.IGNORECASE)
    expiry_match = re.search(r"(\d{2}[/-]\d{2}[/-]\d{2,4})", text)

    medicine_type = None
    lower = text.lower()
    if "tablet" in lower:
        medicine_type = "Tablet"
    elif "capsule" in lower:
        medicine_type = "Capsule"
    elif "syrup" in lower:
        medicine_type = "Syrup"

    return {
        "name": name,
        "dosage": dosage_match.group(1) if dosage_match else None,
        "medicine_type": medicine_type,
        "expiry_date": expiry_match.group(1) if expiry_match else None,
        "raw_text": text[:3000] if text else "OCR engine not available. You can still edit details manually.",
    }
