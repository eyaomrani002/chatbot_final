import pandas as pd
import uuid
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import nltk
import logging

logger = logging.getLogger(__name__)

class NaiveBayesModel:
    def __init__(self, df, vectorizer=None, tfidf_matrix=None):
        self.df = df.copy()
        
        # Validate required columns
        required_columns = ['Question', 'Réponse', 'Processed_Question']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        if missing_columns:
            logger.error(f"Colonnes manquantes dans le dataset: {missing_columns}")
            raise ValueError(f"Dataset manque les colonnes: {missing_columns}")
        
        # Add response_id if not present
        if 'response_id' not in self.df.columns:
            logger.info("Ajout de la colonne response_id au dataset")
            self.df['response_id'] = [str(uuid.uuid4()) for _ in range(len(self.df))]
        
        # Ensure Rating column exists
        if 'Rating' not in self.df.columns:
            logger.info("Ajout de la colonne Rating au dataset")
            self.df['Rating'] = 0
        
        self.vectorizer = vectorizer or TfidfVectorizer()
        self.tfidf_matrix = tfidf_matrix or self.vectorizer.fit_transform(self.df['Processed_Question'])
        self.model = MultinomialNB()
        self.model.fit(self.tfidf_matrix, self.df.index)

    def get_response(self, question):
        try:
            if not question or not isinstance(question, str) or question.strip() == "":
                logger.warning("Question vide ou invalide reçue")
                return {
                    'answer': 'Veuillez fournir une question valide.',
                    'link': '',
                    'category': 'Général',
                    'confidence': 0.0,
                    'response_id': '',
                    'ask_for_response': True
                }
            
            processed_question = self.preprocess_text(question)
            question_tfidf = self.vectorizer.transform([processed_question])
            probabilities = self.model.predict_proba(question_tfidf)[0]
            
            # Get top 3 predictions to consider ratings
            top_indices = probabilities.argsort()[-3:][::-1]
            max_rating = -float('inf')
            best_index = top_indices[0]
            
            # Select highest-rated response among top predictions
            for idx in top_indices:
                current_rating = self.df.iloc[idx]['Rating']
                if current_rating > max_rating:
                    max_rating = current_rating
                    best_index = idx
                elif current_rating == max_rating and probabilities[idx] > probabilities[best_index]:
                    best_index = idx
            
            predicted_index = best_index
            confidence = probabilities[predicted_index]
            row = self.df.iloc[predicted_index]
            
            return {
                'answer': row['Réponse'],
                'link': row['Lien'],
                'category': row['Catégorie'],
                'confidence': confidence,
                'response_id': row['response_id'],
                'ask_for_response': confidence < 0.3 or row['Rating'] < -2
            }
        except Exception as e:
            logger.error(f"Erreur dans get_response: {e}", exc_info=True)
            return {
                'answer': 'Désolé, je n’ai pas compris.',
                'link': '',
                'category': 'Général',
                'confidence': 0.0,
                'response_id': '',
                'ask_for_response': True
            }

    def preprocess_text(self, text):
        import string
        from nltk.corpus import stopwords
        from nltk.stem.snowball import FrenchStemmer
        text = text.lower()
        text = ''.join(c for c in text if c not in '0123456789' + string.punctuation)
        tokens = nltk.word_tokenize(text, language='french')
        tokens = [FrenchStemmer().stem(word) for word in tokens if word not in stopwords.words('french')]
        return ' '.join(tokens)