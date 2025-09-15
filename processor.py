import re
import os
import sys
import platform
import logging
import tempfile
import numpy as np
import pandas as pd
from pathlib import Path

from PIL import Image, ImageFilter
from pdf2image import convert_from_path
import pytesseract
import cv2
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# Configure logging
logger = logging.getLogger(__name__)

# Auto-configure tesseract path based on platform
def configure_tesseract():
    system = platform.system().lower()
    common_paths = {
        'windows': [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            r"C:\Users\%USERNAME%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"
        ],
        'darwin': [  # macOS
            "/usr/local/bin/tesseract",
            "/opt/homebrew/bin/tesseract",
            "/usr/bin/tesseract"
        ],
        'linux': [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
            "/bin/tesseract"
        ]
    }
    paths_to_try = common_paths.get(system, ["/usr/bin/tesseract"])
    for path in paths_to_try:
        if Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            logger.info(f"Tesseract found at: {path}")
            return True

    # Try default
    try:
        pytesseract.image_to_string(Image.new('RGB', (100, 100), color='white'))
        logger.info("Tesseract found in system PATH")
        return True
    except Exception:
        pass

    logger.error("Tesseract not found. Please install it.")
    return False

# Auto-configure poppler path based on platform
def configure_poppler():
    system = platform.system().lower()
    
    # Your specific poppler path
    user_poppler_path = r"C:\Users\Hp\Downloads\Release-24.08.0-0 (2)\poppler-24.08.0\Library\bin"
    
    common_paths = {
        'windows': [
            user_poppler_path,  # Your specific path first
            r"C:\poppler\Library\bin",
            r"C:\Program Files\poppler\Library\bin",
            r"C:\Program Files (x86)\poppler\Library\bin",
        ],
        'darwin': [  # macOS
            "/usr/local/bin",
            "/opt/homebrew/bin",
            "/usr/bin"
        ],
        'linux': [
            "/usr/bin",
            "/usr/local/bin"
        ]
    }
    
    paths_to_try = common_paths.get(system, ["/usr/bin"])
    for path in paths_to_try:
        if Path(path).exists():
            logger.info(f"Poppler found at: {path}")
            return path
    
    logger.warning("Poppler path not found, will try without specifying path")
    return None

if not configure_tesseract():
    sys.exit(1)

# Get poppler path
POPPLER_PATH = configure_poppler()

def advanced_preprocessing(image):
    img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2GRAY)
    variations = []

    # Original grayscale
    variations.append(Image.fromarray(img))

    # Resize if small
    h, w = img.shape
    if h < 1000 or w < 700:
        img2 = cv2.resize(img, (w*2, h*2), interpolation=cv2.INTER_CUBIC)
        variations.append(Image.fromarray(img2))

    # Deskew
    coords = np.column_stack(np.where(img < 255))
    angle = cv2.minAreaRect(coords)[-1] if coords.size else 0
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    deskewed = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    variations.append(Image.fromarray(deskewed))

    # Binarization (Otsu)
    _, binary = cv2.threshold(img, 150, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variations.append(Image.fromarray(binary))

    # Adaptive threshold
    adaptive = cv2.adaptiveThreshold(
        img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
    variations.append(Image.fromarray(adaptive))

    # Denoising
    denoised = cv2.fastNlMeansDenoising(img, None, 30, 7, 21)
    variations.append(Image.fromarray(denoised))

    # PIL sharpness and contrast
    pil_img = Image.fromarray(img)
    variations.append(pil_img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3)))
    variations.append(pil_img.filter(ImageFilter.SHARPEN))

    return variations

def robust_total_marks_extraction(ocr_texts):
    possible_patterns = [
        r'TOTAL\s*MARKS?\s*[:\-]?\s*([\dO l]{3,6})',
        r'MARKS\s*OBTAINED\s*[:\-]?\s*([\dO l]{3,6})',
        r'GRAND\s*TOTAL\s*[:\-]?\s*([\dO l]{3,6})',
        r'TOTAL\s*[:\-]?\s*([\dO l]{3,6})',
        r'Total\s*([\dO l]{3,6})',
        r'([\dO l]{3,6})\s*(marks|total|obtained)',
    ]
    for ocr_text in ocr_texts:
        for pat in possible_patterns:
            match = re.search(pat, ocr_text, re.IGNORECASE)
            if match:
                total_raw = match.group(1)
                total_cleaned = total_raw.replace('O', '0').replace('l', '1').replace(' ', '')
                total_cleaned = re.sub(r'[^\d]', '', total_cleaned)
                if total_cleaned.isdigit():
                    total = int(total_cleaned)
                    # Follow dynamic max marks
                    if total <= 500:
                        max_marks = 500
                    elif total <= 600:
                        max_marks = 600
                    else:
                        max_marks = 625
                    pct = round((total / max_marks) * 100, 2)
                    return total, pct
    return None, None

def extract_info_from_page(page_image):
    variations = advanced_preprocessing(page_image)
    ocr_texts = [pytesseract.image_to_string(v, config='--psm 6') for v in variations]

    # Name extraction robust pattern
    name_match = re.search(
        r'Name\s*(?:of\s+the\s+(?:Candidate|Student))?\s*[:\-]?\s*([A-Z\s.]{3,})',
        ocr_texts[0], re.IGNORECASE)
    name = ""
    if name_match:
        raw_name = name_match.group(1)
        cleaned_name = re.split(
            r'\b(Date|Register|Roll|Number|Marks|School|Std|Gender|Father|Mother)\b',
            raw_name, flags=re.IGNORECASE)[0].strip()
        parts = [p for p in cleaned_name.split() if p.isalpha()]
        name = " ".join([x.capitalize() for x in parts])

    # DOB extraction
    dob_match = re.search(
        r'Date\s+of\s+Birth\s*[:\-]?\s*(\d{1,2}[-/.\s]\d{1,2}[-/.\s]\d{2,4})',
        ocr_texts[0], re.IGNORECASE)
    dob = dob_match.group(1).replace(' ', '-') if dob_match else ""

    # Register Number / Roll Number
    reg_match = re.search(
        r'(Register|Roll|Admission)\s+Number\s*[:\-]?\s*(\d{5,})',
        ocr_texts[0], re.IGNORECASE)
    reg_no = reg_match.group(2).strip() if reg_match else ""

    # Total Marks & Percentage
    total, percentage = robust_total_marks_extraction(ocr_texts)

    return {
        "Name": name,
        "DOB": dob,
        "Register Number": reg_no,
        "Total Marks": total,
        "Percentage": percentage
    }

def extract_semester_info_from_page(page_image):
    variations = advanced_preprocessing(page_image)
    ocr_texts = [pytesseract.image_to_string(v, config='--psm 6') for v in variations]

    base_text = ocr_texts[0]

    # Name extraction
    name = ""
    name_match = re.search(
        r"Name\s*of\s*the\s*Candidate\s*[:\-]?\s*(.+?)\s+(?:Register|Reg|Department|Degree)",
        base_text, re.IGNORECASE)
    if name_match:
        raw_name = name_match.group(1).strip()
        raw_name = re.sub(r"\b([A-Z])\.(?=[A-Z])", r"\1. ", raw_name)
        name = re.sub(r"[^A-Z .]+", "", raw_name, flags=re.IGNORECASE).strip()

    # Register Number
    reg_no = ""
    reg_match = re.search(r"Register\s*Number\s*[:\-]?\s*([A-Z0-9]+)", base_text, re.IGNORECASE)
    if reg_match:
        reg_no = reg_match.group(1).strip()

    # Department
    department = ""
    dept_match = re.search(r"Degree\s*\/\s*Branch\s*[:\-]?\s*(.+)", base_text, re.IGNORECASE)
    if dept_match:
        department = dept_match.group(1).strip()
        department = re.sub(r'[\u00AE\u00A9®©:]+', '', department).strip()

    # CGPA / SGPA extraction
    cgpa, sgpa = "", ""
    cgpa_patterns = [
        r'CGPA\s*[:\-]?\s*([0-9OIl]{1,2}\.?[0-9OIl]{1,2})',
        r'C\.G\.P\.A\.?\s*[:\-]?\s*([0-9OIl]{1,2}\.?[0-9OIl]{1,2})',
        r'C G P A\s*[:\-]?\s*([0-9OIl]{1,2}\.?[0-9OIl]{1,2})'
    ]
    sgpa_patterns = [
        r'SGPA\s*[:\-]?\s*([0-9OIl]{1,2}\.?[0-9OIl]{1,2})',
        r'S\.G\.P\.A\.?\s*[:\-]?\s*([0-9OIl]{1,2}\.?[0-9OIl]{1,2})',
        r'S G P A\s*[:\-]?\s*([0-9OIl]{1,2}\.?[0-9OIl]{1,2})'
    ]
    def clean_score(score):
        return score.replace('O', '0').replace('I', '1').replace('l', '1').replace(' ', '')

    for text in ocr_texts:
        if not cgpa:
            for pat in cgpa_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    cleaned = clean_score(m.group(1))
                    if re.match(r'^\d{1,2}\.?\d{0,2}$', cleaned):
                        cgpa = cleaned
                        break
        if not sgpa:
            for pat in sgpa_patterns:
                m = re.search(pat, text, re.IGNORECASE)
                if m:
                    cleaned = clean_score(m.group(1))
                    if re.match(r'^\d{1,2}\.?\d{0,2}$', cleaned):
                        sgpa = cleaned
                        break
        if cgpa and sgpa:
            break

    return {
        "Name": name,
        "Register Number": reg_no,
        "Department": department,
        "CGPA": cgpa,
        "SGPA": sgpa
    }

def process_marksheet(marksheet_type, file_path):
    import time
    import gc
    import shutil
    import os
    
    marksheet_type = marksheet_type.lower()
    results = []

    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    file_ext = Path(file_path).suffix.lower()
    if file_ext not in ['.pdf', '.jpg', '.jpeg', '.png']:
        raise ValueError(f"Unsupported file format: {file_ext}")

    if file_ext in ['.jpg', '.jpeg', '.png']:
        # Single image processing
        image = Image.open(file_path)
        if marksheet_type in ['10th', '12th']:
            results.append(extract_info_from_page(image))
        elif marksheet_type == 'semester':
            results.append(extract_semester_info_from_page(image))
        image.close()
    else:
        # PDF processing with Windows-specific file handling
        temp_dir = None
        try:
            # Create manual temporary directory
            temp_dir = tempfile.mkdtemp(prefix='marksheet_')
            logger.info(f"Created temp directory: {temp_dir}")
            
            # Convert PDF to images with explicit file format control
            # THIS IS WHERE THE POPPLER PATH IS ADDED:
            convert_kwargs = {
                'pdf_path': file_path,
                'dpi': 250,  # Reduced DPI for smaller files
                'output_folder': temp_dir,
                'fmt': 'JPEG',  # Force JPEG instead of PPM
                'jpegopt': {'quality': 95}
            }
            
            # Add poppler_path if available
            if POPPLER_PATH:
                convert_kwargs['poppler_path'] = POPPLER_PATH
                logger.info(f"Using poppler path: {POPPLER_PATH}")
            
            pages = convert_from_path(**convert_kwargs)
            logger.info(f"Converted {len(pages)} pages from PDF")
            
            # Process each page
            for i, page in enumerate(pages):
                logger.info(f"Processing page {i+1} of {len(pages)}")
                try:
                    if marksheet_type in ['10th', '12th']:
                        info = extract_info_from_page(page)
                    elif marksheet_type == 'semester':
                        info = extract_semester_info_from_page(page)
                    
                    results.append(info)
                    
                    # Explicitly close the page
                    page.close()
                    del page
                    
                except Exception as e:
                    logger.error(f"Error processing page {i+1}: {e}")
                    continue
            
            # Clear pages list and force garbage collection
            del pages
            gc.collect()
            time.sleep(0.5)  # Longer delay for Windows
            
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            raise
        finally:
            # Manual cleanup with retry mechanism
            if temp_dir and os.path.exists(temp_dir):
                cleanup_temp_directory(temp_dir)

    if not results:
        raise ValueError("No data could be extracted from the document")
        
    df = pd.DataFrame(results)
    return df

def cleanup_temp_directory(temp_dir):
    """Windows-safe temporary directory cleanup with retries"""
    import time
    import gc
    import shutil
    
    max_retries = 5
    retry_delay = 0.2
    
    for attempt in range(max_retries):
        try:
            gc.collect()  # Force garbage collection
            time.sleep(retry_delay)
            
            # Try to remove all files first
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    try:
                        if os.path.exists(file_path):
                            os.chmod(file_path, 0o777)  # Change permissions
                            os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Could not remove file {file_path}: {e}")
            
            # Now try to remove the directory
            time.sleep(retry_delay)
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            if not os.path.exists(temp_dir):
                logger.info(f"Successfully cleaned up temp directory: {temp_dir}")
                break
                
        except Exception as e:
            logger.warning(f"Cleanup attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))  # Increasing delay
            else:
                logger.error(f"Failed to cleanup temp directory after {max_retries} attempts: {temp_dir}")
