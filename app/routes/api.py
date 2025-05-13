from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import os
import re
from app.utils.logging import initialize_logging
from app.utils.data_manager import get_best_response, add_response, rate_response, initialize_data
from app.utils.pdf_generator import export_conversations
from app.utils.image_processing import extract_text
from flask_login import login_required, current_user
from app.utils.history import get_conversations
from app.utils.evaluate_model import cross_validate_model
logger = initialize_logging()
api = Blueprint('api', __name__)
supported_langs = ['fr', 'en', 'ar']

try:
    initialize_data()
except Exception as e:
    logger.error(f"Failed to initialize data: {e}", exc_info=True)
    raise

@api.route('/')
@api.route('/home')
@login_required
def home():
    return render_template('chat.html')

@api.route('/chat', methods=['POST'])
@login_required
def chat_handler():
    try:
        pdf = request.files.get('pdf_file')
        image = request.files.get('image_file')
        uploaded_files = []
        extracted_text = ""
        
        # Ensure UPLOAD_FOLDER exists
        upload_folder = current_app.config['UPLOAD_FOLDER']
        try:
            os.makedirs(upload_folder, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create UPLOAD_FOLDER {upload_folder}: {e}")
            return jsonify({'error': 'Failed to create upload directory'}), 500
        
        # Process PDF
        if pdf and pdf.filename:
            logger.debug(f"Processing PDF: {pdf.filename}")
            if not pdf.filename.endswith('.pdf') or pdf.content_type != 'application/pdf':
                return jsonify({'error': 'Invalid PDF file'}), 400
            pdf.seek(0, os.SEEK_END)
            if pdf.tell() > current_app.config['MAX_CONTENT_LENGTH']:
                return jsonify({'error': 'PDF file too large (max 5 MB)'}), 400
            pdf.seek(0)
            filename = secure_filename(pdf.filename)
            if not re.match(r'^[\w\-. ]+\.pdf$', filename):
                return jsonify({'error': 'Invalid PDF filename'}), 400
            pdf_path = os.path.join(upload_folder, filename)
            pdf.save(pdf_path)
            uploaded_files.append(pdf_path)
        
        # Process image
        if image:
            logger.debug(f"Processing image: {image.filename}")
            if image.content_type not in ['image/png', 'image/jpeg']:
                logger.error(f"Invalid image file: {image.filename}")
                return jsonify({'error': 'Invalid image file (PNG/JPEG required)'}), 400
            image.seek(0, os.SEEK_END)
            if image.tell() > current_app.config['MAX_CONTENT_LENGTH']:
                logger.error(f"Image file too large: {image.filename}")
                return jsonify({'error': 'Image file too large (max 5 MB)'}), 400
            image.seek(0)
            filename = secure_filename(image.filename)
            if not re.match(r'^[\w\-. ]+\.(png|jpg|jpeg)$', filename):
                return jsonify({'error': 'Invalid image filename'}), 400
            image_path = os.path.join(upload_folder, filename)
            image.save(image_path)
            uploaded_files.append(image_path)
            extracted_text = extract_text(image_path)
            logger.info(f"Text extracted from image: {extracted_text[:100]}...")
            if extracted_text.startswith("Erreur") or extracted_text == "Aucun texte détecté dans l'image.":
                logger.warning(f"Failed to extract text from image: {extracted_text}")
                return jsonify({'error': extracted_text, 'extracted_text': extracted_text, 'questions': []}), 400
        
        # Process question
        question = request.form.get('message', '')
        if not isinstance(question, str) or len(question) > 1000:
            return jsonify({'error': 'Invalid or too long message'}), 400
        
        if extracted_text and not extracted_text.startswith("Erreur") and extracted_text != "Aucun texte détecté dans l'image.":
            question = f"{question} [Texte extrait: {extracted_text}]" if question else f"Texte extrait: {extracted_text}"
        
        if not question and not (pdf or image):
            return jsonify({'error': 'No question or file provided'}), 400
        
        # Generate response
        try:
            response = get_best_response(question or "Uploaded file", method='knn')
        except ValueError as ve:
            logger.error(f"Invalid method in get_best_response: {ve}")
            return jsonify({'error': f"Invalid response method: {str(ve)}"}), 500
        
        response['ask_for_response'] = response['confidence'] < 0.3
        if extracted_text and not extracted_text.startswith("Erreur") and extracted_text != "Aucun texte détecté dans l'image.":
            response['extracted_text'] = extracted_text
        
        # Clean up uploaded files
        for file_path in uploaded_files:
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error deleting file {file_path}: {e}")
        
        logger.info(f"User {current_user.username} sent message: {question[:100]}..., response: {response['answer'][:100]}...")
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error in /chat: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred.'}), 500

@api.route('/add_response', methods=['POST'])
@login_required
def add_response_route():
    try:
        data = request.json
        if not data or 'question' not in data or 'response' not in data:
            logger.error("Missing data in /add_response")
            return jsonify({'error': 'Missing question or response data'}), 400
        
        result, status = add_response(data)
        return jsonify(result), status
    
    except Exception as e:
        logger.error(f"Error in /add_response: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred.'}), 500

@api.route('/rate', methods=['POST'])
@login_required
def rate():
    try:
        result, status = rate_response(request.json)
        return jsonify(result), status
    
    except Exception as e:
        logger.error(f"Error in /rate: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred.'}), 500

@api.route('/export_conversations', methods=['POST'])
@login_required
def export_conversations_route():
    try:
        result = export_conversations(request.json)
        if isinstance(result, tuple):
            buffer, mimetype, filename = result
            return send_file(buffer, mimetype=mimetype, download_name=filename)
        return jsonify(result), result.get('status', 500)
    
    except Exception as e:
        logger.error(f"Error in /export_conversations: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred.'}), 500
    
    
@api.route('/evaluate_models', methods=['GET'])
def evaluate_models():
    """Run cross-validation for all models and display results."""
    try:
        lang = request.args.get('lang', 'fr')
        if lang not in supported_langs:
            logger.error(f"Langue non supportée: {lang}")
            return jsonify({'error': f"Langue non supportée. Choisissez parmi {supported_langs}"}), 400

        # Call cross_validate_model with use_sbert=False to avoid SBERT error
        results = cross_validate_model(lang=lang, k_folds=5, use_sbert=False)

        formatted_results = {}
        for model, metrics in results.items():
            formatted_results[model] = {
                'mean_accuracy': metrics['mean_accuracy'],
                'classification_report': metrics['mean_classification_report'],
                'folds': metrics['folds']
            }

        if request.args.get('format') == 'html':
            return render_template('evaluate_models.html', language=lang, results=formatted_results)
        else:
            return jsonify({
                'language': lang,
                'results': formatted_results
            }), 200

    except Exception as e:
        logger.error(f"Erreur lors de l'évaluation des modèles: {e}", exc_info=True)
        if request.args.get('format') == 'html':
            return render_template('error.html', error_message=f"Erreur lors de l'évaluation des modèles: {str(e)}"), 500
        else:
            return jsonify({'error': f"Une erreur interne est survenue: {str(e)}"}), 500