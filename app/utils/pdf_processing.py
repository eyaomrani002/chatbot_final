import pdfplumber
import logging
import os
import pytesseract
import shutil
from PIL import Image
import numpy as np
import fitz  # PyMuPDF
import io

logger = logging.getLogger(__name__)

# Configuration dynamique de Tesseract
def configure_tesseract():
    tesseract_cmd = None
    windows_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(windows_path):
        tesseract_cmd = windows_path
    elif shutil.which("tesseract"):
        tesseract_cmd = shutil.which("tesseract")
    
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        logger.info(f"Tesseract configuré avec le chemin: {tesseract_cmd}")
    else:
        logger.error("Tesseract non trouvé. Veuillez installer Tesseract et vérifier le chemin.")
        raise RuntimeError("Tesseract non trouvé.")

try:
    configure_tesseract()
except Exception as e:
    logger.error(f"Erreur de configuration de Tesseract: {e}")
    raise

# Configurer la police Amiri pour le support arabe
amiri_font_path = r"F:\DSIR12\SYM2\SI2\projet\chatbot2\fonts\Amiri-Regular.ttf"
if os.path.exists(amiri_font_path):
    fitz.TOOLS.set_aa_fonts({"ar": amiri_font_path})
    logger.info(f"Police Amiri configurée pour le support arabe: {amiri_font_path}")
else:
    logger.warning(f"Police Amiri-Regular.ttf introuvable à {amiri_font_path}. Le support arabe peut être limité.")

def preprocess_image(image):
    """
    Prétraiter l'image pour améliorer la qualité de l'OCR.
    """
    try:
        image = image.convert('L')  # Convertir en niveaux de gris
        image = np.array(image)
        image = (image - np.min(image)) * (255 / (np.max(image) - np.min(image)))
        image = Image.fromarray(image.astype(np.uint8))
        return image
    except Exception as e:
        logger.error(f"Erreur lors du prétraitement de l'image: {e}")
        return image

def process_pdf(pdf_path):
    """
    Extrait le texte d'un fichier PDF en utilisant pdfplumber pour le texte natif et PyMuPDF + pytesseract pour l'OCR.
    
    Args:
        pdf_path (str): Chemin vers le fichier PDF.
    
    Returns:
        tuple: (Texte extrait ou message d'erreur, Liste de questions extraites).
    """
    logger.debug(f"Début du traitement du PDF: {pdf_path}")
    try:
        if not os.path.exists(pdf_path):
            logger.error(f"Fichier PDF introuvable: {pdf_path}")
            return f"Fichier PDF introuvable: {pdf_path}", []

        if not pdf_path.lower().endswith('.pdf'):
            logger.error(f"Type de fichier non supporté: {pdf_path}")
            return "Erreur : type de fichier non supporté.", []

        # Essayer l'extraction textuelle avec pdfplumber
        extracted_text = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.debug(f"Nombre de pages dans le PDF: {len(pdf.pages)}")
                for i, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if text:
                        extracted_text.append(text.strip())
                        logger.debug(f"Texte extrait de la page {i+1}: {text[:100]}...")
                    else:
                        logger.debug(f"Aucun texte extrait de la page {i+1}")
        except Exception as e:
            logger.warning(f"Échec de l'extraction textuelle avec pdfplumber: {e}")

        full_text = ' '.join(extracted_text)
        full_text = ' '.join(full_text.split())  # Normalise les espaces
        
        if full_text:
            logger.info(f"Texte extrait du PDF avec pdfplumber: {full_text[:100]}...")
            return full_text, []

        # Si aucun texte, tenter l'OCR avec PyMuPDF
        logger.info(f"Aucun texte détecté avec pdfplumber, tentative d'OCR pour {pdf_path}")
        try:
            # Ouvrir le PDF avec PyMuPDF
            pdf_doc = fitz.open(pdf_path)
            logger.debug(f"Nombre de pages dans le PDF (PyMuPDF): {pdf_doc.page_count}")
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
                    logger.debug(f"Texte OCR extrait de la page {page_num+1}: {text[:100]}...")
                else:
                    logger.debug(f"Aucun texte OCR extrait de la page {page_num+1}")
            
            pdf_doc.close()
            
            full_text = ' '.join(ocr_text)
            full_text = ' '.join(full_text.split())
            
            if not full_text:
                logger.warning(f"Aucun texte détecté dans le PDF après OCR: {pdf_path}")
                return "Aucun texte détecté dans le PDF.", []
            
            logger.info(f"Texte OCR extrait du PDF: {full_text[:100]}...")
            return full_text, []
        
        except Exception as e:
            logger.error(f"Erreur lors de l'OCR du PDF {pdf_path}: {e}", exc_info=True)
            return f"Erreur lors de l'OCR: {str(e)}", []
    
    except Exception as e:
        logger.error(f"Erreur générale lors de l'extraction du texte du PDF {pdf_path}: {e}", exc_info=True)
        return f"Erreur générale: {str(e)}", []