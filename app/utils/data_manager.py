import os
import pandas as pd
import uuid
from threading import Lock
import bleach
from .logging import initialize_logging
from .preprocess import preprocess_text, initialize_vectorizer
from .models import KNNModel, SVMModel, CosineModel
from langdetect import detect

logger = initialize_logging()

# Thread lock for dataset updates
_df_lock = Lock()

# Internal state
_state = {
    'fr': {'df': None, 'vectorizer': None, 'X': None, 'knn': None, 'svm': None, 'cosine': None},
    'en': {'df': None, 'vectorizer': None, 'X': None, 'knn': None, 'svm': None, 'cosine': None},
    'ratings': pd.DataFrame(columns=['response_id', 'rating', 'timestamp']),
    'initialized': False
}

# Proactive suggestion links
SUGGESTIONS = {
    'Horaires': 'http://iset.example.com/calendrier',
    'Professeurs': 'http://iset.example.com/enseignants',
    'Général': 'http://iset.example.com/accueil'
}

def initialize_data():
    """Initialize datasets, vectorizers, and models for French and English."""
    if _state['initialized']:
        logger.debug("Data already initialized.")
        return
    
    try:
        # Ensure data directory exists
        base_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.normpath(os.path.join(base_dir, '../data'))
        logger.debug(f"Looking for data directory at: {data_dir}")
        if not os.path.exists(data_dir):
            logger.error(f"Data directory not found at {data_dir}. Please create it and add dataset files.")
            raise FileNotFoundError(f"Data directory not found at {data_dir}")
        
        # Initialize French data
        _state['fr']['df'] = load_data('fr')
        if _state['fr']['df'].empty:
            logger.warning("French dataset is empty. Skipping model initialization.")
        else:
            _state['fr']['df']['Processed_Question'] = _state['fr']['df']['Question'].apply(lambda x: preprocess_text(x, 'fr'))
            _state['fr']['vectorizer'], _state['fr']['X'] = initialize_vectorizer(_state['fr']['df'], 'fr')
            _state['fr']['knn'] = KNNModel(_state['fr']['X'])
            _state['fr']['svm'] = SVMModel(_state['fr']['df'], _state['fr']['X'], lang='fr')
            _state['fr']['cosine'] = CosineModel(_state['fr']['X'])
        
        # Initialize English data
        _state['en']['df'] = load_data('en')
        if _state['en']['df'].empty:
            logger.warning("English dataset is empty. Skipping model initialization.")
        else:
            _state['en']['df']['Processed_Question'] = _state['en']['df']['Question'].apply(lambda x: preprocess_text(x, 'en'))
            _state['en']['vectorizer'], _state['en']['X'] = initialize_vectorizer(_state['en']['df'], 'en')
            _state['en']['knn'] = KNNModel(_state['en']['X'])
            _state['en']['svm'] = SVMModel(_state['en']['df'], _state['en']['X'], lang='en')
            _state['en']['cosine'] = CosineModel(_state['en']['X'])
        
        _state['initialized'] = True
        logger.info("Datasets, vectorizers, and models initialized successfully for French and English.")
        
        # Evaluate models only if dataset is non-empty and has enough rows
        for lang in ['fr', 'en']:
            if not _state[lang]['df'].empty and len(_state[lang]['df']) >= 3:  # Reduced to 3 folds
                try:
                    evaluate_all_models(lang=lang)
                except Exception as e:
                    logger.warning(f"Skipping evaluation for {lang} due to error: {e}")
            else:
                logger.warning(f"Skipping evaluation for {lang}: Dataset too small or empty ({len(_state[lang]['df'])} rows).")
    
    except Exception as e:
        logger.error(f"Failed to initialize data: {e}", exc_info=True)
        raise RuntimeError(f"Data initialization failed: {e}")

def load_data(lang):
    """Load the dataset for the specified language."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.normpath(os.path.join(base_dir, f'../data/iset_questions_reponses_{lang}.csv'))
    logger.debug(f"Attempting to load dataset from: {data_path}")  # Fixed typo here
    if not os.path.exists(data_path):
        logger.error(f"Dataset file not found at {data_path}. Please ensure the file exists.")
        raise FileNotFoundError(f"Dataset file not found at {data_path}")
    
    try:
        df = pd.read_csv(data_path, encoding='utf-8')
        logger.debug(f"Loaded {lang} dataset columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        logger.error(f"Error loading {lang} dataset from {data_path}: {e}")
        raise

def get_df_lock():
    """Return a thread lock for dataset updates."""
    return _df_lock

def get_df(lang):
    """Return the dataset for the specified language."""
    if not _state['initialized']:
        raise RuntimeError("Data not initialized. Please check server logs.")
    return _state[lang]['df']

def get_vectorizer(lang):
    """Return the vectorizer for the specified language."""
    if not _state['initialized']:
        raise RuntimeError("Data not initialized. Please check server logs.")
    return _state[lang]['vectorizer']

def get_X(lang):
    """Return the vectorized questions for the specified language."""
    if not _state['initialized']:
        raise RuntimeError("Data not initialized. Please check server logs.")
    return _state[lang]['X']

def get_best_response(user_input, method='knn'):
    """Find the best response using the specified model."""
    if not _state['initialized']:
        logger.error("Cannot process response: Data not initialized.")
        raise RuntimeError("Data not initialized. Please check server logs.")
    
    if not user_input or not isinstance(user_input, str):
        logger.error("Invalid input: user_input must be a non-empty string.")
        raise ValueError("Input must be a non-empty string.")
    
    # Detect language
    try:
        lang = detect(user_input)
        if lang not in ['fr', 'en']:
            lang = 'fr'  # Default to French
    except Exception as e:
        logger.warning(f"Language detection failed: {e}. Defaulting to French.")
        lang = 'fr'
    
    df = _state[lang]['df']
    vectorizer = _state[lang]['vectorizer']
    svm = _state[lang]['svm']
    
    logger.debug(f"Processing input: {user_input} in language: {lang} with method: {method}")
    processed_input = preprocess_text(user_input, lang)
    input_vec = vectorizer.transform([processed_input])
    
    # Predict intent with SVM
    intent, intent_confidence = svm.predict(input_vec)
    
    # Get response based on method
    if method == 'knn':
        max_idx, confidence = _state[lang]['knn'].predict(input_vec)
    elif method == 'cosine':
        max_idx, confidence = _state[lang]['cosine'].predict(input_vec)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    response = {
        'answer': df.iloc[max_idx]['Réponse' if lang == 'fr' else 'Response'],
        'link': df.iloc[max_idx]['Lien' if lang == 'fr' else 'Link'],
        'category': df.iloc[max_idx]['Catégorie' if lang == 'fr' else 'Category'],
        'response_id': str(uuid.uuid4()),
        'confidence': float(confidence),
        'intent': intent,
        'suggestion': SUGGESTIONS.get(intent, ''),
        'language': lang
    }
    logger.debug(f"Generated response: {response}")
    return response

def add_response(data):
    """Add a new question/response to the dataset."""
    if not _state['initialized']:
        logger.error("Cannot add response: Data not initialized.")
        return {'error': 'Data not initialized. Please check server logs.'}, 500
    
    lang = data.get('language', 'fr')
    df = _state[lang]['df']
    
    try:
        if not data or 'question' not in data or 'response' not in data:
            return {'error': 'Missing question or response data'}, 400

        new_row = pd.DataFrame([{
            'Question': bleach.clean(data['question']),
            'Réponse' if lang == 'fr' else 'Response': bleach.clean(data['response']),
            'Lien' if lang == 'fr' else 'Link': bleach.clean(data.get('link', '')),
            'Catégorie' if lang == 'fr' else 'Category': bleach.clean(data.get('category', 'Général')),
            'Rating': 0
        }])
        
        with _df_lock:
            _state[lang]['df'] = pd.concat([df, new_row], ignore_index=True)
            _state[lang]['df']['Processed_Question'] = _state[lang]['df']['Question'].apply(lambda x: preprocess_text(x, lang))
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.normpath(os.path.join(base_dir, f'../data/iset_questions_reponses_{lang}.csv'))
            _state[lang]['df'].to_csv(data_path, index=False, encoding='utf-8')
            logger.info(f"New response added for language {lang}. Model retraining deferred.")
        
        return {'success': True}, 200
    
    except Exception as e:
        logger.error(f"Error in add_response: {e}", exc_info=True)
        return {'error': 'An internal error occurred.'}, 500

def retrain_models(lang):
    """Retrain models for the specified language."""
    try:
        with _df_lock:
            vectorizer = _state[lang]['vectorizer']
            _state[lang]['X'] = vectorizer.fit_transform(_state[lang]['df']['Processed_Question'])
            _state[lang]['knn'] = KNNModel(_state[lang]['X'])
            _state[lang]['svm'] = SVMModel(_state[lang]['df'], _state[lang]['X'], lang=lang)
            _state[lang]['cosine'] = CosineModel(_state[lang]['X'])
            logger.info(f"Models retrained for language {lang}.")
    except Exception as e:
        logger.error(f"Error in retrain_models for language {lang}: {e}", exc_info=True)
        raise RuntimeError(f"Model retraining failed: {e}")

def rate_response(data):
    """Record a response rating."""
    try:
        if not data or 'response_id' not in data or 'rating' not in data:
            return {'error': 'Missing response_id or rating data'}, 400

       

        new_rating = pd.DataFrame([{
            'response_id': data['response_id'],
            'rating': data['rating'],
            'timestamp': pd.Timestamp.now()
        }])
        
        with _df_lock:
            _state['ratings'] = pd.concat([_state['ratings'], new_rating], ignore_index=True)
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ratings_path = os.path.normpath(os.path.join(base_dir, '../data/ratings.csv'))
            _state['ratings'].to_csv(ratings_path, index=False, encoding='utf-8')
        
        return {'success': True}, 200
    
    except Exception as e:
        logger.error(f"Error in rate_response: {e}", exc_info=True)
        return {'error': 'An internal error occurred.'}, 500

def evaluate_all_models(lang='fr'):
    """Evaluate all models and log results."""
    from .evaluate_model import cross_validate_model
    try:
        # Disable SBERT for initial evaluation to avoid download issues
        results = cross_validate_model(lang=lang, k_folds=3, use_sbert=False)
        logger.info(f"Résultats de l'évaluation pour la langue {lang}:")
        for model, metrics in results.items():
            logger.info(f"Modèle {model.capitalize()}:")
            logger.info(f"  Précision moyenne: {metrics['mean_accuracy']:.4f}")
            logger.info(f"  Rapport de classification: {metrics['mean_classification_report']}")
        return results
    except Exception as e:
        logger.error(f"Erreur lors de l'évaluation des modèles: {e}", exc_info=True)
        raise