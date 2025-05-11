import os
import sys
import pytesseract
from PIL import Image, ImageDraw, ImageFont
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_tesseract_installation():
    """Vérifie l'installation de Tesseract OCR."""
    print("\n=== Vérification de l'installation de Tesseract OCR ===\n")
    
    # 1. Vérifier le chemin de Tesseract
    tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    print(f"1. Vérification du chemin de Tesseract...")
    if os.path.exists(tesseract_path):
        print(f"✓ Tesseract trouvé à : {tesseract_path}")
    else:
        print(f"✗ Tesseract non trouvé à : {tesseract_path}")
        print("\nPour installer Tesseract :")
        print("1. Téléchargez l'installateur depuis : https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Installez-le dans le dossier par défaut : C:\\Program Files\\Tesseract-OCR")
        print("3. Assurez-vous d'installer les langues françaises pendant l'installation")
        return False
    
    # 2. Configurer le chemin de Tesseract
    print("\n2. Configuration de pytesseract...")
    try:
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        print("✓ Chemin de Tesseract configuré")
    except Exception as e:
        print(f"✗ Erreur lors de la configuration : {e}")
        return False
    
    # 3. Vérifier la version
    print("\n3. Vérification de la version...")
    try:
        version = pytesseract.get_tesseract_version()
        print(f"✓ Tesseract version {version} trouvé")
    except Exception as e:
        print(f"✗ Erreur lors de la vérification de la version : {e}")
        return False
    
    # 4. Créer une image de test
    print("\n4. Création d'une image de test...")
    try:
        # Créer une image simple
        img = Image.new('RGB', (300, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 40), "Test OCR", fill='black')
        test_image_path = "test_ocr.png"
        img.save(test_image_path)
        print(f"✓ Image de test créée : {test_image_path}")
    except Exception as e:
        print(f"✗ Erreur lors de la création de l'image : {e}")
        return False
    
    # 5. Tester l'OCR
    print("\n5. Test de l'OCR...")
    try:
        text = pytesseract.image_to_string(img, lang='fra')
        print(f"✓ Texte extrait : {text.strip()}")
    except Exception as e:
        print(f"✗ Erreur lors du test OCR : {e}")
        print("\nSi l'erreur concerne la langue 'fra', assurez-vous d'avoir installé le pack de langue français")
        return False
    
    # Nettoyage
    try:
        os.remove(test_image_path)
        print(f"\n✓ Fichier de test supprimé")
    except:
        pass
    
    print("\n=== Vérification terminée avec succès ===")
    return True

if __name__ == "__main__":
    try:
        check_tesseract_installation()
    except Exception as e:
        print(f"\nErreur inattendue : {e}")
        sys.exit(1) 