import requests
from PIL import Image, ImageDraw, ImageFont
import os
import logging
import time
import base64
from io import BytesIO

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_image(text, filename="test.png"):
    """Crée une image avec du texte pour tester l'OCR."""
    # Créer le dossier test_images s'il n'existe pas
    test_dir = "test_images"
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    # Chemin complet du fichier
    filepath = os.path.join(test_dir, filename)
    
    # Créer une image plus grande avec un fond blanc
    img = Image.new('RGB', (1200, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Essayer d'utiliser une police plus grande et plus lisible
    try:
        # Essayer plusieurs polices courantes
        fonts = [
            "arial.ttf",
            "times.ttf",
            "verdana.ttf",
            "calibri.ttf"
        ]
        font = None
        for font_name in fonts:
            try:
                font = ImageFont.truetype(font_name, 48)
                break
            except:
                continue
        if font is None:
            raise Exception("Aucune police trouvée")
    except:
        logger.warning("Aucune police système trouvée, utilisation de la police par défaut")
        font = ImageFont.load_default()
    
    # Ajouter un fond gris clair pour le texte
    text_bg = Image.new('RGB', (1160, 560), color='#f0f0f0')
    img.paste(text_bg, (20, 20))
    
    # Dessiner le texte avec un contour noir pour plus de lisibilité
    text_position = (60, 280)
    draw.text(text_position, text, fill='black', font=font)
    
    # Ajouter une bordure
    draw.rectangle([(10, 10), (1190, 590)], outline='black', width=2)
    
    # Sauvegarder l'image
    img.save(filepath, format="PNG", quality=100)
    logger.info(f"Image créée : {filepath}")
    return filepath

def extract_text_with_vision_api(image_path):
    """Extrait le texte d'une image en utilisant l'API Vision."""
    try:
        # Convertir l'image en base64
        with open(image_path, 'rb') as image_file:
            content = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Préparer la requête pour l'API Vision
        vision_api_url = "https://vision.googleapis.com/v1/images:annotate"
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            "requests": [{
                "image": {
                    "content": content
                },
                "features": [{
                    "type": "TEXT_DETECTION",
                    "languageHints": ["fr"]
                }]
            }]
        }
        
        # Envoyer la requête à l'API Vision
        response = requests.post(vision_api_url, headers=headers, json=data)
        response.raise_for_status()
        
        # Extraire le texte de la réponse
        result = response.json()
        if 'responses' in result and result['responses']:
            if 'textAnnotations' in result['responses'][0]:
                return result['responses'][0]['textAnnotations'][0]['description']
        
        return "Aucun texte détecté"
        
    except Exception as e:
        logger.error(f"Erreur lors de l'extraction du texte : {e}")
        return None

def test_image_processing():
    """Teste le traitement d'image via l'API."""
    # URL de l'API (ajustez selon votre configuration)
    url = "http://localhost:5000/chat"
    
    # Texte à tester
    test_text = "Test de reconnaissance de texte"
    image_path = create_test_image(test_text)

    try:
        # Extraire le texte avec l'API Vision
        extracted_text = extract_text_with_vision_api(image_path)
        if extracted_text:
            logger.info(f"Texte extrait avec l'API Vision : {extracted_text}")
        
        # Préparation de la requête pour le chatbot
        with open(image_path, 'rb') as img_file:
            files = {
                "image_file": (image_path, img_file, "image/png"),
                "output_lang": (None, "fr"),
                "message": (None, test_text)
            }
            
            # Envoi de la requête
            logger.info("Envoi de l'image au serveur...")
            response = requests.post(url, files=files, timeout=30)
            
            # Vérification de la réponse
            response.raise_for_status()
            data = response.json()
            
            # Affichage des résultats
            logger.info("Réponse du serveur :")
            logger.info(f"Texte extrait : {data.get('extracted_text', 'Aucun texte extrait')}")
            logger.info(f"Réponse du chatbot : {data.get('answer', 'Aucune réponse')}")
            
            # Vérification du texte extrait
            extracted_text = data.get('extracted_text', '')
            if not extracted_text:
                logger.error("Échec : Aucun texte n'a été extrait de l'image")
                return False
                
            if test_text.lower() not in extracted_text.lower():
                logger.error(f"Échec : Le texte extrait ne correspond pas au texte attendu")
                logger.error(f"Texte attendu : {test_text}")
                logger.error(f"Texte extrait : {extracted_text}")
                return False
            
            logger.info("Test terminé avec succès")
            return True

    except requests.RequestException as e:
        logger.error(f"Erreur réseau : {e}")
    except Exception as e:
        logger.error(f"Erreur inattendue : {e}")
    finally:
        # Attendre un peu avant de supprimer le fichier
        time.sleep(1)
        try:
            if os.path.exists(image_path):
                os.remove(image_path)
                logger.info("Fichier de test supprimé")
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du fichier : {e}")
    
    return False

if __name__ == "__main__":
    print("Démarrage du test de traitement d'image...")
    result = test_image_processing()
    print("Résultat du test :", "Succès" if result else "Échec") 