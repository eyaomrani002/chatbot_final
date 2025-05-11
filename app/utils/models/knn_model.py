from sklearn.neighbors import NearestNeighbors
from ..logging import initialize_logging

logger = initialize_logging()

class KNNModel:
    def __init__(self, X):
        """Initialize the KNN model."""
        self.model = NearestNeighbors(n_neighbors=1, metric='cosine', algorithm='brute')
        self.model.fit(X)
        logger.debug("KNN model initialized.")
    
    def predict(self, input_vec):
        """Predict the closest question index and confidence."""
        distances, indices = self.model.kneighbors(input_vec, n_neighbors=1)
        max_idx = indices[0][0]
        confidence = 1 - distances[0][0]  # Convert distance to similarity score
        return max_idx, confidence