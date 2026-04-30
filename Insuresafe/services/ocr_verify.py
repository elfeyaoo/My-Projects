# services/ocr_verify.py
# Improved Aadhaar OCR Verification Service (Professional Version)

import re
import os
import cv2
import numpy as np
from typing import Dict, Any
from PIL import Image

import easyocr
import pytesseract

# ---------------------------------
# Optional: Windows Tesseract Path
# ---------------------------------
if os.name == "nt":
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


class DocumentVerifier:
    def __init__(self, demo: bool = False):
        self.demo = demo

        if not self.demo:
            self.reader = easyocr.Reader(['en'], gpu=False)
        else:
            self.reader = None

    # ---------------------------------
    # Image Loader
    # ---------------------------------
    def _load_image(self, path: str):
        img = cv2.imread(path)
        if img is None:
            raise ValueError("Invalid image file")
        return img

    # ---------------------------------
    # Image Preprocessing for Better OCR
    # ---------------------------------
    def preprocess_image(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Resize for better OCR
        gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Noise removal
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        # Thresholding
        gray = cv2.threshold(
            gray,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]

        return gray

    # ---------------------------------
    # OCR Extraction
    # ---------------------------------
    def extract_text(self, image_path: str) -> str:
        if self.demo:
            return (
                "Government of India\n"
                "Rahul Sharma\n"
                "DOB: 12/05/1998\n"
                "Male\n"
                "1234 5678 9012"
            )

        img = self._load_image(image_path)
        processed = self.preprocess_image(img)

        text = ""

        # EasyOCR first
        if self.reader:
            results = self.reader.readtext(processed)
            if results:
                text = "\n".join([r[1] for r in results])

        # Fallback to Tesseract
        if not text.strip():
            pil = Image.fromarray(processed)
            text = pytesseract.image_to_string(pil)

        return text.strip()

    # ---------------------------------
    # Aadhaar Number Validation
    # ---------------------------------
    def clean_aadhaar(self, aadhaar: str):
        digits = re.sub(r'\D', '', aadhaar)
        return digits if len(digits) == 12 else None

    # ---------------------------------
    # Field Extraction
    # ---------------------------------
    def extract_fields(self, text: str) -> Dict[str, str]:
        fields = {}
        lines = [l.strip() for l in text.split("\n") if len(l.strip()) > 2]

        ignore_words = {
            "government",
            "india",
            "authority",
            "unique",
            "identification"
        }

        # -----------------------------
        # Name Extraction
        # -----------------------------
        for i, line in enumerate(lines):
            lower = line.lower()

            if any(word in lower for word in ignore_words):
                continue

            if re.search(r'\d', line):
                continue

            alpha_ratio = sum(c.isalpha() for c in line) / max(len(line), 1)

            if alpha_ratio > 0.7 and 3 <= len(line.split()) <= 4:
                fields["name"] = line
                break

        # -----------------------------
        # DOB Extraction
        # -----------------------------
        dob_match = re.search(
            r'(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})',
            text
        )

        if dob_match:
            fields["dob"] = dob_match.group(1)
        else:
            yob_match = re.search(r'(?:year of birth|yob)[:\s]*(\d{4})', text, re.I)
            if yob_match:
                fields["dob"] = yob_match.group(1)

        # -----------------------------
        # Gender Extraction
        # -----------------------------
        if re.search(r'\bfemale\b', text, re.I):
            fields["gender"] = "female"
        elif re.search(r'\bmale\b', text, re.I):
            fields["gender"] = "male"

        # -----------------------------
        # Aadhaar Extraction
        # -----------------------------
        aadhaar_match = re.search(
            r'(\d{4}[\s-]?\d{4}[\s-]?\d{4})',
            text
        )

        if aadhaar_match:
            cleaned = self.clean_aadhaar(aadhaar_match.group(1))
            if cleaned:
                fields["aadhaar"] = cleaned

        return fields

    # ---------------------------------
    # Normalization Helper
    # ---------------------------------
    def _norm(self, s: str) -> str:
        return re.sub(r'[^a-z0-9]', '', s.lower()) if s else ""

    # ---------------------------------
    # Validation API
    # ---------------------------------
    def validate(self, image_path: str, expected: Dict[str, str]) -> Dict[str, Any]:
        text = self.extract_text(image_path)
        extracted = self.extract_fields(text)

        match = {}

        if extracted.get("name") and expected.get("name"):
            match["name"] = (
                self._norm(extracted["name"]) == self._norm(expected["name"])
            )

        if extracted.get("dob") and expected.get("dob"):
            match["dob"] = extracted["dob"] == expected["dob"]

        if extracted.get("gender") and expected.get("gender"):
            match["gender"] = (
                extracted["gender"] == expected["gender"].lower()
            )

        if extracted.get("aadhaar") and expected.get("aadhaar"):
            match["aadhaar"] = (
                extracted["aadhaar"] == re.sub(r'\D', '', expected["aadhaar"])
            )

        is_valid = bool(match) and all(match.values())

        return {
            "document_type": "AADHAAR",
            "ocr_text": text,
            "extracted": extracted,
            "match": match,
            "is_valid": is_valid
        }
