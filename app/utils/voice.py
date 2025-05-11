from gtts import gTTS
import os
import uuid
import logging

logger = logging.getLogger(__name__)

def generate_audio(text, lang='fr', upload_folder='Uploads'):
    """Generate audio from text using gTTS."""
    try:
        if not text or not isinstance(text, str):
            return None, "Texte invalide pour la génération audio."
        
        # Map Flask language codes to gTTS language codes
        lang_map = {
            'fr': 'fr',
            'en': 'en',
            'ar': 'ar'
        }
        if lang not in lang_map:
            logger.warning(f"Langue non supportée pour TTS: {lang}")
            return None, f"Langue non supportée: {lang}"

        # Generate audio
        tts = gTTS(text=text, lang=lang_map[lang], slow=False)
        filename = f"audio_{uuid.uuid4()}.mp3"
        audio_path = os.path.join(upload_folder, filename)
        
        # Save audio file
        tts.save(audio_path)
        logger.info(f"Audio généré: {audio_path}")
        return audio_path, filename
    except Exception as e:
        logger.error(f"Erreur lors de la génération de l'audio: {e}", exc_info=True)
        return None, str(e)