import re
from sklearn.feature_extraction.text import TfidfVectorizer
from . import french_stopwords, stemmer

def preprocess_text(text, lang='fr'):
    """Preprocess text by cleaning, stemming, and removing stopwords."""
    # Convert to lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Tokenize and remove stopwords
    words = text.split()
    if lang == 'fr':
        words = [stemmer.stem(word) for word in words if word not in french_stopwords]
    else:
        words = [word for word in words if len(word) > 2]  # Basic filtering for English
    
    return ' '.join(words)

def initialize_vectorizer(df, lang='fr'):
    """Initialize TF-IDF vectorizer and transform questions."""
    df['Processed_Question'] = df['Question'].apply(lambda x: preprocess_text(x, lang))
    
    # Initialize TF-IDF vectorizer
    stop_words = french_stopwords if lang == 'fr' else 'english'
    vectorizer = TfidfVectorizer(max_features=1000, stop_words=stop_words)
    
    # Transform processed questions
    X = vectorizer.fit_transform(df['Processed_Question'])
    return vectorizer, X