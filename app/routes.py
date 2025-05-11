from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
import os
import bleach
from .utils.logging import initialize_logging
from .utils.data_manager import get_best_response, add_response, rate_response
from .utils.pdf_processing import process_pdf
from .utils.image_processing import extract_text
from .utils.pdf_generator import export_conversations
from .utils.web_search import get_web_response
from .utils.history import save_conversation, get_conversations
from .utils.rating import migrate_ratings
from .utils.voice import generate_audio

logger = initialize_logging()
bp = Blueprint('main', __name__)
supported_langs = ['fr', 'en', 'ar']

@bp.route('/')
def home():
    """Render the home page."""
    return render_template('chat.html')

@bp.route('/history', methods=['GET'])
@login_required
def get_history():
    """Fetch the conversation history for the current user."""
    try:
        conversations = get_conversations(user_id=current_user.id)
        return jsonify({'conversations': conversations}), 200
    except Exception as e:
        logger.error(f"Error fetching history: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred.'}), 500


@bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests with text, PDF, or image inputs."""
    try:
        pdf = request.files.get('pdf_file')
        image = request.files.get('image_file')
        uploaded_files = []
        extracted_text = ""
        output_lang = request.form.get('output_lang', 'fr')
        tts_enabled = request.form.get('tts', 'false').lower() == 'true'

        logger.debug(f"Requête /chat reçue: pdf={bool(pdf)}, image={bool(image)}, output_lang={output_lang}, tts={tts_enabled}")

        if output_lang not in supported_langs:
            logger.error(f"Langue non supportée: {output_lang}")
            return jsonify({'error': f"Langue non supportée. Choisissez parmi {supported_langs}"}), 400

        # Process PDF
        if pdf:
            if not pdf.filename.endswith('.pdf') or pdf.content_type != 'application/pdf':
                logger.error(f"Fichier PDF invalide: {pdf.filename}")
                return jsonify({'error': 'Fichier PDF invalide'}), 400
            pdf.seek(0, os.SEEK_END)
            if pdf.tell() > current_app.config['MAX_CONTENT_LENGTH']:
                logger.error(f"Fichier PDF trop volumineux: {pdf.filename}")
                return jsonify({'error': 'Fichier PDF trop volumineux (max 5 Mo)'}), 400
            pdf.seek(0)
            filename = secure_filename(pdf.filename)
            pdf_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            pdf.save(pdf_path)
            uploaded_files.append(pdf_path)
            extracted_text, questions = process_pdf(pdf_path)
            logger.debug(f"Résultat de process_pdf: extracted_text={extracted_text[:100]}..., questions={questions}")
            if extracted_text.startswith("Erreur") or extracted_text == "Aucun texte détecté dans le PDF.":
                logger.warning(f"Échec de l'extraction du texte du PDF: {extracted_text}")
                return jsonify({'error': extracted_text, 'extracted_text': extracted_text, 'questions': questions}), 400

        # Process image
        if image:
            if image.content_type not in ['image/png', 'image/jpeg']:
                logger.error(f"Fichier image invalide: {image.filename}")
                return jsonify({'error': 'Fichier image invalide (PNG/JPEG requis)'}), 400
            image.seek(0, os.SEEK_END)
            if image.tell() > current_app.config['MAX_CONTENT_LENGTH']:
                logger.error(f"Fichier image trop volumineux: {image.filename}")
                return jsonify({'error': 'Fichier image trop volumineux (max 5 Mo)'}), 400
            image.seek(0)
            filename = secure_filename(image.filename)
            image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            image.save(image_path)
            uploaded_files.append(image_path)
            extracted_text = extract_text(image_path)
            logger.debug(f"Résultat de extract_text: extracted_text={extracted_text[:100]}...")
            if extracted_text.startswith("Erreur") or extracted_text == "Aucun texte détecté dans l'image.":
                logger.warning(f"Échec de l'extraction du texte de l'image: {extracted_text}")
                return jsonify({'error': extracted_text, 'extracted_text': extracted_text, 'questions': []}), 400

        question = request.form.get('message', '').strip()
        logger.debug(f"Question reçue: {question}")
        if extracted_text and not extracted_text.startswith("Erreur") and extracted_text != "Aucun texte détecté dans le PDF.":
            if question:
                question = f"{question} [Texte extrait: {extracted_text}]"
            else:
                question = extracted_text
        logger.debug(f"Question finale envoyée à get_best_response: {question}")

        if not question and not (pdf or image):
            logger.error("Aucune question ou fichier fourni")
            return jsonify({'error': 'Aucune question ou fichier fourni'}), 400

        # Generate response
        response = get_best_response(question or "Fichier uploadé", method='knn')
        logger.debug(f"Réponse générée: {response}")
        if response['confidence'] < 0.3:
            web_response = get_web_response(question, response['confidence'])
            if web_response:
                response['answer'] = web_response
                response['confidence'] = 0.9
                response['ask_for_response'] = True
            else:
                response['ask_for_response'] = True
        else:
            response['ask_for_response'] = False

        response['extracted_text'] = extracted_text
        response['questions'] = []

        # Generate audio if requested
        if tts_enabled:
            try:
                audio_path, audio_filename = generate_audio(
                    response['answer'],
                    lang=output_lang,
                    upload_folder=current_app.config['UPLOAD_FOLDER']
                )
                if audio_path:
                    uploaded_files.append(audio_path)
                    response['audio_url'] = f"/audio/{audio_filename}"
                else:
                    response['audio_error'] = audio_filename  # Contient le message d'erreur
            except Exception as e:
                logger.error(f"Erreur lors de la génération de l'audio: {e}")
                response['audio_error'] = "Erreur lors de la génération de l'audio."

        # Save conversation
        save_conversation(
            question=question,
            answer=response['answer'],
            link=response.get('link', ''),
            category=response.get('category', 'Général'),
            response_id=response['response_id']
        )

        # Clean up uploaded files (except audio, which will be served)
        for file_path in uploaded_files:
            if not file_path.endswith('.mp3'):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logger.error(f"Erreur lors de la suppression du fichier {file_path}: {e}")

        logger.debug(f"Envoi de la réponse finale: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Erreur dans /chat: {e}", exc_info=True)
        return jsonify({'error': f"Une erreur interne est survenue: {str(e)}", 'extracted_text': extracted_text, 'questions': []}), 500

@bp.route('/audio/<filename>')
def serve_audio(filename):
    """Serve an audio file and delete it after sending."""
    audio_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(audio_path):
        logger.error(f"Fichier audio introuvable: {filename}")
        return jsonify({'error': 'Fichier audio introuvable'}), 404
    try:
        response = send_file(audio_path, mimetype='audio/mpeg')
        os.remove(audio_path)
        return response
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du fichier audio {filename}: {e}")
        return jsonify({'error': "Erreur lors de l'envoi de l'audio"}), 500

@bp.route('/add_response', methods=['POST'])
def add_response_route():
    """Add a new question/response to the dataset."""
    try:
        import string
        import nltk
        import bleach
        import pandas as pd
        from nltk.corpus import stopwords
        from nltk.stem.snowball import FrenchStemmer
        import uuid

        data = request.json
        if not data or 'question' not in data or 'response' not in data:
            logger.error("Données manquantes dans /add_response")
            return jsonify({'error': 'Données manquantes'}), 400

        output_lang = data.get('language', 'fr')
        if output_lang not in supported_langs:
            logger.error(f"Langue non supportée: {output_lang}")
            return jsonify({'error': f"Langue non supportée. Choisissez parmi {supported_langs}"}), 400

        df = current_app.config['DATAFRAME']
        vectorizer = current_app.config['VECTORIZER']

        new_row = pd.DataFrame([{
            'Question': bleach.clean(data['question']),
            'Réponse': bleach.clean(data['response']),
            'Lien': bleach.clean(data.get('link', '')),
            'Catégorie': bleach.clean(data.get('category', 'Général')),
            'Rating': 0,
            'response_id': str(uuid.uuid4())
        }])

        def preprocess_text(text):
            stemmer = FrenchStemmer()
            text = text.lower()
            text = ''.join([c for c in text if c not in string.punctuation + '0123456789'])
            tokens = nltk.word_tokenize(text)
            tokens = [stemmer.stem(word) for word in tokens if word not in stopwords.words('french')]
            return ' '.join(tokens)

        new_row['Processed_Question'] = new_row['Question'].apply(preprocess_text)
        with current_app.config['DF_LOCK']:
            current_app.config['DATAFRAME'] = pd.concat([df, new_row], ignore_index=True)
            current_app.config['TFIDF_MATRIX'] = vectorizer.fit_transform(current_app.config['DATAFRAME']['Processed_Question'])
            ratings_file = os.path.join(current_app.config['DATA_FOLDER'], 'ratings.csv')
            current_app.config['DATAFRAME'].to_csv(ratings_file, index=False, encoding='utf-8')
        return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Erreur dans /add_response: {e}", exc_info=True)
        return jsonify({'error': 'Une erreur interne est survenue.'}), 500

@bp.route('/rate', methods=['POST'])
def rate():
    """Rate a response."""
    migrate_ratings()
    result, status = rate_response(request.json)
    return jsonify(result), status

@bp.route('/export_conversations', methods=['POST'])
def export_conversations_route():
    """Export conversations to PDF."""
    result = export_conversations(request.json)
    if isinstance(result, tuple):
        buffer, mimetype, filename = result
        return send_file(buffer, mimetype=mimetype, download_name=filename)
    return jsonify(result), result.get('status', 500)