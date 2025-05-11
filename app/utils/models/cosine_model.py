from sklearn.metrics.pairwise import cosine_similarity
from ..logging import initialize_logging

logger = initialize_logging()

class CosineModel:
    def __init__(self, X):
        """Initialize the Cosine Similarity model."""
        self.X = X
        logger.debug("Cosine Similarity model initialized.")
    
    def predict(self, input_vec):
        """Predict the closest question index and confidence."""
        similarities = cosine_similarity(input_vec, self.X)
        max_idx = similarities.argmax()
        confidence = float(similarities.max())
        return max_idx, confidence