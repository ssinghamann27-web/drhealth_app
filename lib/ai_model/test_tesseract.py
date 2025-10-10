import pytesseract
from PIL import Image

print("Path:", pytesseract.pytesseract.tesseract_cmd)

# quick check
img = Image.new("RGB", (300, 80), color="white")
print("Tesseract available:", bool(pytesseract.pytesseract.tesseract_cmd))
