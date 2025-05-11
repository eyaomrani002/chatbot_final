import logging
import io
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import numpy as np

# Configurer le logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Chemin du PDF
pdf_path = r"F:\DSIR12\SYM2\SI2\projet\chatbot2\office_hours.pdf"  # Ajustez pour conversation_5.pdf ou test_scan.pdf

# Prétraitement d'image
def preprocess_image(image):
    try:
        image = image.convert('L')
        image = np.array(image)
        image = (image - np.min(image)) * (255 / (np.max(image) - np.min(image)))
        image = Image.fromarray(image.astype(np.uint8))
        return image
    except Exception as e:
        logger.error(f"Erreur lors du prétraitement: {e}")
        return image

# Tester l'extraction
try:
    # Ouvrir le PDF avec PyMuPDF
    pdf_doc = fitz.open(pdf_path)
    logger.debug(f"Nombre de pages dans le PDF: {pdf_doc.page_count}")
    ocr_text = []
    
    for page_num in range(pdf_doc.page_count):
        page = pdf_doc[page_num]
        # Convertir la page en image (300 DPI)
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        
        # Prétraiter l'image
        img = preprocess_image(img)
        
        # Effectuer l'OCR
        text = pytesseract.image_to_string(img, lang='fra+eng+ara', config='--psm 6').strip()
        if text:
            ocr_text.append(text)
            logger.debug(f"Texte extrait de la page {page_num+1}: {text[:100]}...")
        else:
            logger.debug(f"Aucun texte extrait de la page {page_num+1}")
    
    pdf_doc.close()
    
    full_text = ' '.join(ocr_text)
    full_text = ' '.join(full_text.split())
    print(f"Texte extrait: {full_text}")

except Exception as e:
    logger.error(f"Erreur lors de l'extraction: {e}", exc_info=True)
    print(f"Erreur: {e}")