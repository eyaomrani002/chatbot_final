from sklearn.svm import SVC
from sklearn.preprocessing import LabelEncoder
from ..logging import initialize_logging

logger = initialize_logging()

class SVMModel:
    def __init__(self, df, X, lang='fr'):
        """Initialize the SVM model for intent classification."""
        self.label_encoder = LabelEncoder()
        # Use 'Catégorie' for French, 'Category' for English
        column_name = 'Catégorie' if lang == 'fr' else 'Category'
        try:
            y = self.label_encoder.fit_transform(df[column_name])
        except KeyError as e:
            logger.error(f"Column '{column_name}' not found in dataset for language '{lang}'")
            raise KeyError(f"Column '{column_name}' not found in dataset for language '{lang}'")
        self.model = SVC(kernel='linear', probability=True)
        self.model.fit(X, y)
        logger.debug(f"SVM model initialized for intent classification (language: {lang}).")
    
    def predict(self, input_vec):
        """Predict the intent and confidence."""
        intent_idx = self.model.predict(input_vec)[0]
        intent = self.label_encoder.inverse_transform([intent_idx])[0]
        confidence = self.model.predict_proba(input_vec)[0].max()
        return intent, confidence