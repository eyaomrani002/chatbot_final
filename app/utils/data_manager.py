import os
import pandas as pd
import uuid
from threading import Lock
from .logging import initialize_logging
from .preprocess import preprocess_text, initialize_vectorizer
from .models import KNNModel, SVMModel, CosineModel
from langdetect import detect

logger = initialize_logging()
ratings = pd.DataFrame(columns=['response_id', 'rating', 'timestamp'])

# Thread lock for dataset updates
_df_lock = Lock()

# Internal state
_state = {
    'fr': {'df': None, 'vectorizer': None, 'X': None, 'knn': None, 'svm': None, 'cosine': None},
    'en': {'df': None, 'vectorizer': None, 'X': None, 'knn': None, 'svm': None, 'cosine': None},
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
            raise FileNotFoundError(f"Data directory not found at {data_dir}.")
        
        # Initialize French data
        _state['fr']['df'] = load_data('fr')
        _state['fr']['vectorizer'], _state['fr']['X'] = initialize_vectorizer(_state['fr']['df'], 'fr')
        _state['fr']['knn'] = KNNModel(_state['fr']['X'])
        _state['fr']['svm'] = SVMModel(_state['fr']['df'], _state['fr']['X'], lang='fr')
        _state['fr']['cosine'] = CosineModel(_state['fr']['X'])
        
        # Initialize English data
        _state['en']['df'] = load_data('en')
        _state['en']['vectorizer'], _state['en']['X'] = initialize_vectorizer(_state['en']['df'], 'en')
        _state['en']['knn'] = KNNModel(_state['en']['X'])
        _state['en']['svm'] = SVMModel(_state['en']['df'], _state['en']['X'], lang='en')
        _state['en']['cosine'] = CosineModel(_state['en']['X'])
        
        _state['initialized'] = True
        logger.info("Datasets, vectorizers, and models initialized successfully for French and English.")
    except Exception as e:
        logger.error(f"Failed to initialize data: {e}", exc_info=True)
        raise RuntimeError(f"Data initialization failed: {e}")

def load_data(lang):
    """Load the dataset for the specified language."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.normpath(os.path.join(base_dir, f'../data/iset_questions_reponses_{lang}.csv'))
    logger.debug(f"Attempting to load dataset from: {data_path}")
    
    if not os.path.exists(data_path):
        logger.error(f"Dataset file not found at {data_path}. Please ensure the file exists.")
        raise FileNotFoundError(f"Dataset file not found at {data_path}.")
    
    try:
        df = pd.read_csv(data_path, encoding='utf-8')
        logger.debug(f"Loaded {lang} dataset from {data_path} with {len(df)} rows.")
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
    
    # Detect language
    try:
        lang = detect(user_input)
        if lang not in ['fr', 'en']:
            lang = 'fr'  # Default to French
    except:
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
    vectorizer = _state[lang]['vectorizer']
    
    try:
        if not data or 'question' not in data or 'response' not in data:
            return {'error': 'Missing question or response data'}, 400

        import bleach
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
            _state[lang]['X'] = vectorizer.fit_transform(_state[lang]['df']['Processed_Question'])
            _state[lang]['knn'] = KNNModel(_state[lang]['X'])
            _state[lang]['svm'] = SVMModel(_state[lang]['df'], _state[lang]['X'], lang=lang)
            _state[lang]['cosine'] = CosineModel(_state[lang]['X'])
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_path = os.path.normpath(os.path.join(base_dir, f'../data/iset_questions_reponses_{lang}.csv'))
            _state[lang]['df'].to_csv(data_path, index=False, encoding='utf-8')
        
        return {'success': True}, 200
    
    except Exception as e:
        logger.error(f"Error in add_response: {e}", exc_info=True)
        return {'error': 'An internal error occurred.'}, 500

def rate_response(data):
    """Record a response rating."""
    global ratings
    try:
        if not data or 'response_id' not in data or 'rating' not in data:
            return {'error': 'Missing response_id or rating data'}, 400

        ratings = pd.concat([ratings, pd.DataFrame([{
            'response_id': data['response_id'],
            'rating': data['rating'],
            'timestamp': pd.Timestamp.now()
        }])], ignore_index=True)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ratings_path = os.path.normpath(os.path.join(base_dir, '../data/ratings.csv'))
        ratings.to_csv(ratings_path, index=False, encoding='utf-8')
        
        return {'success': True}, 200
    
    except Exception as e:
        logger.error(f"Error in rate_response: {e}", exc_info=True)
        return {'error': 'An internal error occurred.'}, 500

def evaluate_model():
    """Evaluate the model using a test set."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    test_path = os.path.normpath(os.path.join(base_dir, '../data/test_questions.csv'))
    
    if not os.path.exists(test_path):
        logger.warning(f"Test dataset not found at {test_path}")
        return {'error': 'Test dataset not found.'}
    
    try:
        test_df = pd.read_csv(test_path, encoding='utf-8')
        correct = 0
        total = len(test_df)
        
        for _, row in test_df.iterrows():
            question = row['Question']
            expected_answer = row['Réponse']
            response = get_best_response(question, method='knn')
            if response['answer'] == expected_answer:
                correct += 1
        
        precision = correct / total if total > 0 else 0
        logger.info(f"Model evaluation: Precision = {precision:.2f} ({correct}/{total})")
        return {'precision': precision, 'correct': correct, 'total': total}
    except Exception as e:
        logger.error(f"Error in evaluate_model: {e}", exc_info=True)
        return {'error': 'Evaluation failed.'}