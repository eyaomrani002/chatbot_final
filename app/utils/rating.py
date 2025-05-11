import os
import pandas as pd
import bleach
import logging
from flask import current_app, jsonify

logger = logging.getLogger(__name__)

def migrate_ratings():
    """Migrate ratings.csv to the new format: question, reponse, rating, response_id, timestamp."""
    try:
        ratings_file = os.path.join(current_app.config['DATA_FOLDER'], 'ratings.csv')
        dataset_file = os.path.join(current_app.config['DATA_FOLDER'], 'iset_questions_reponses.csv')

        # Check if ratings.csv exists
        if not os.path.exists(ratings_file):
            # Create empty ratings.csv with new format
            pd.DataFrame(columns=['question', 'reponse', 'rating', 'response_id', 'timestamp']).to_csv(
                ratings_file, index=False, encoding='utf-8'
            )
            logger.info("Created empty ratings.csv with new format.")
            return

        # Load ratings.csv
        ratings_df = pd.read_csv(ratings_file)

        # Check if already in new format
        expected_columns = ['question', 'reponse', 'rating', 'response_id', 'timestamp']
        if list(ratings_df.columns) == expected_columns:
            logger.debug("ratings.csv is already in the correct format.")
            return

        # Keep only the latest rating for each response_id
        ratings_df['timestamp'] = pd.to_datetime(ratings_df['timestamp'])
        latest_ratings = ratings_df.sort_values('timestamp').groupby('response_id').last().reset_index()

        # Load dataset
        if not os.path.exists(dataset_file):
            logger.error("Dataset file iset_questions_reponses.csv not found.")
            return

        dataset_df = pd.read_csv(dataset_file)

        # Merge with dataset to get question and reponse
        merged_df = latest_ratings.merge(
            dataset_df[['response_id', 'Question', 'Réponse']],
            on='response_id',
            how='left'
        )

        # Handle missing matches
        merged_df['question'] = merged_df['Question'].apply(
            lambda x: bleach.clean(str(x))[:1000] if pd.notnull(x) else 'Question inconnue'
        )
        merged_df['reponse'] = merged_df['Réponse'].apply(
            lambda x: bleach.clean(str(x))[:1000] if pd.notnull(x) else 'Réponse inconnue'
        )

        # Convert rating to numeric
        merged_df['rating'] = merged_df['rating'].map({'like': 1, 'dislike': -1})

        # Select and order columns
        columns = ['question', 'reponse', 'rating', 'response_id', 'timestamp']
        output_df = merged_df[columns]

        # Save to ratings.csv
        output_df.to_csv(ratings_file, index=False, encoding='utf-8')
        logger.info("ratings.csv migrated successfully to new format.")
    except Exception as e:
        logger.error(f"Error migrating ratings.csv: {e}", exc_info=True)

def rate_response(data):
    """Handle rating logic for a response."""
    try:
        if not data or 'response_id' not in data or 'rating' not in data:
            return jsonify({'error': 'Données manquantes'}), 400
        
        if data['rating'] not in ['like', 'dislike']:
            return jsonify({'error': 'Évaluation invalide. Utilisez "like" ou "dislike".'}), 400

        ratings_file = os.path.join(current_app.config['DATA_FOLDER'], 'ratings.csv')
        new_rating_value = 1 if data['rating'] == 'like' else -1
        
        # Fetch question and response from dataset
        df = current_app.config['DATAFRAME']
        if 'response_id' not in df.columns:
            return jsonify({'error': 'response_id non trouvé dans le dataset'}), 400
        
        match = df[df['response_id'] == data['response_id']]
        if match.empty:
            return jsonify({'error': 'Aucune question/réponse trouvée pour ce response_id'}), 400
        
        question = bleach.clean(match['Question'].iloc[0])[:1000]
        reponse = bleach.clean(match['Réponse'].iloc[0])[:1000]
        
        # Define column order for ratings.csv
        columns = ['question', 'reponse', 'rating', 'response_id', 'timestamp']
        
        # Load existing ratings
        if os.path.exists(ratings_file):
            existing_ratings = pd.read_csv(ratings_file)
            existing_rating = existing_ratings[existing_ratings['response_id'] == data['response_id']]
            
            if not existing_rating.empty:
                # Existing rating found, update it
                old_rating_value = existing_rating['rating'].iloc[0]
                existing_ratings.loc[existing_ratings['response_id'] == data['response_id'], 'question'] = question
                existing_ratings.loc[existing_ratings['response_id'] == data['response_id'], 'reponse'] = reponse
                existing_ratings.loc[existing_ratings['response_id'] == data['response_id'], 'rating'] = new_rating_value
                existing_ratings.loc[existing_ratings['response_id'] == data['response_id'], 'timestamp'] = pd.Timestamp.now()
                existing_ratings[columns].to_csv(ratings_file, index=False, encoding='utf-8')
                
                # Update dataset Rating column
                match_index = df[df['response_id'] == data['response_id']].index
                if not match_index.empty:
                    df.loc[match_index, 'Rating'] = df.loc[match_index, 'Rating'] - old_rating_value + new_rating_value
                    current_app.config['DATAFRAME'] = df
                    df.to_csv(os.path.join(current_app.config['DATA_FOLDER'], 'iset_questions_reponses.csv'), index=False, encoding='utf-8')
            else:
                # No existing rating, append new one
                rating_data = pd.DataFrame([{
                    'question': question,
                    'reponse': reponse,
                    'rating': new_rating_value,
                    'response_id': data['response_id'],
                    'timestamp': pd.Timestamp.now()
                }], columns=columns)
                rating_data.to_csv(ratings_file, mode='a', header=False, index=False, encoding='utf-8')
                
                # Update dataset Rating column
                match_index = df[df['response_id'] == data['response_id']].index
                if not match_index.empty:
                    df.loc[match_index, 'Rating'] += new_rating_value
                    current_app.config['DATAFRAME'] = df
                    df.to_csv(os.path.join(current_app.config['DATA_FOLDER'], 'iset_questions_reponses.csv'), index=False, encoding='utf-8')
        else:
            # Create new ratings.csv
            rating_data = pd.DataFrame([{
                'question': question,
                'reponse': reponse,
                'rating': new_rating_value,
                'response_id': data['response_id'],
                'timestamp': pd.Timestamp.now()
            }], columns=columns)
            rating_data.to_csv(ratings_file, index=False, encoding='utf-8')
            
            # Update dataset Rating column
            match_index = df[df['response_id'] == data['response_id']].index
            if not match_index.empty:
                df.loc[match_index, 'Rating'] += new_rating_value
                current_app.config['DATAFRAME'] = df
                df.to_csv(os.path.join(current_app.config['DATA_FOLDER'], 'iset_questions_reponses.csv'), index=False, encoding='utf-8')
        
        return jsonify({'success': True}), 200
    
    except Exception as e:
        logger.error(f"Erreur dans rate_response: {e}", exc_info=True)
        return jsonify({'error': 'Une erreur interne est survenue'}), 500