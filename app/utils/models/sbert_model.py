from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from ..logging import initialize_logging

logger = initialize_logging()

class SBERTModel:
    def __init__(self, sentences, model_name='paraphrase-multilingual-MiniLM-L12-v2'):
        """Initialize Sentence-BERT model."""
        self.model = SentenceTransformer(model_name)
        self.embeddings = self.model.encode(sentences, convert_to_tensor=True)
        logger.debug("SBERT model initialized.")
    
    def predict(self, input_sentence):
        """Predict the closest question index and confidence."""
        input_embedding = self.model.encode([input_sentence], convert_to_tensor=True)
        similarities = cosine_similarity(input_embedding.cpu(), self.embeddings.cpu())
        max_idx = similarities.argmax()
        confidence = float(similarities[0, max_idx])
        return max_idx, confidence