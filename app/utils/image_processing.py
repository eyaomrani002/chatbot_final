from PIL import Image
import pytesseract
import logging
import os

logger = logging.getLogger(__name__)

# Configuration de Tesseract (ajustez le chemin si nécessaire)
try:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows
except Exception as e:
    logger.error(f"Erreur de configuration de Tesseract: {e}")

def extract_text(file_path):
    """
    Extrait le texte d'une image (PNG/JPEG).
    
    Args:
        file_path (str): Chemin vers le fichier image.
    
    Returns:
        str: Texte extrait ou message d'erreur.
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Le fichier {file_path} n'existe pas.")
            return "Erreur : fichier introuvable."
        
        if not file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            logger.error(f"Type de fichier non supporté: {file_path}")
            return "Erreur : type de fichier non supporté."
        
        img = Image.open(file_path)
        extracted_text = pytesseract.image_to_string(img, lang='fra+eng+ara')
        extracted_text = extracted_text.strip()
        if not extracted_text:
            extracted_text = "Aucun texte détecté dans l'image."
        logger.info(f"Texte extrait de l'image: {extracted_text}")
        return extracted_text
    
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du texte: {e}")
        return "Erreur lors de l'extraction du texte."