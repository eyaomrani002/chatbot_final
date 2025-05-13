import pandas as pd
import uuid
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import nltk
import logging

logger = logging.getLogger(__name__)

class NaiveBayesModel:
    def __init__(self, df, vectorizer=None, tfidf_matrix=None, lang='fr'):
        self.df = df.copy()
        self.lang = lang
        
        # Define language-specific column names
        response_col = 'Réponse' if lang == 'fr' else 'Response'
        category_col = 'Catégorie' if lang == 'fr' else 'Category'
        link_col = 'Lien' if lang == 'fr' else 'Link'
        
        # Validate required columns
        required_columns = ['Question', response_col, 'Processed_Question']
        missing_columns = [col for col in required_columns if col not in self.df.columns]
        if missing_columns:
            logger.error(f"Colonnes manquantes dans le dataset ({lang}): {missing_columns}")
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
        # Use provided tfidf_matrix if available, otherwise compute it
        self.tfidf_matrix = tfidf_matrix if tfidf_matrix is not None else self.vectorizer.fit_transform(self.df['Processed_Question'])
        self.model = MultinomialNB()
        self.model.fit(self.tfidf_matrix, self.df.index)
        self.response_col = response_col
        self.category_col = category_col
        self.link_col = link_col

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
            logger.debug(f"Selected answer: {row[self.response_col]} for question: {question}, available answers: {self.df[self.response_col].tolist()}")
            return {
                'answer': row[self.response_col],
                'link': row[self.link_col],
                'category': row[self.category_col],
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
        from nltk.stem.snowball import FrenchStemmer, EnglishStemmer
        text = text.lower()
        text = ''.join(c for c in text if c not in '0123456789' + string.punctuation)
        tokens = nltk.word_tokenize(text, language='french' if self.lang == 'fr' else 'english')
        stemmer = FrenchStemmer() if self.lang == 'fr' else EnglishStemmer()
        stop_words = stopwords.words('french' if self.lang == 'fr' else 'english')
        tokens = [stemmer.stem(word) for word in tokens if word not in stop_words]
        return ' '.join(tokens)