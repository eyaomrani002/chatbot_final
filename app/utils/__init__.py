import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import FrenchStemmer
from .logging import initialize_logging
from .models import KNNModel, SVMModel, CosineModel
import fitz
print(fitz.__version__)

# Initialize shared resources
french_stopwords = stopwords.words('french')
stemmer = FrenchStemmer()

def initialize_nltk():
    """Download NLTK data if not present."""
    try:
        nltk.data.find('corpora/stopwords')
    except LookupError:
        nltk.download('stopwords')