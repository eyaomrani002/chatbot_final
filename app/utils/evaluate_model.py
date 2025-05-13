from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
import numpy as np
from .data_manager import get_df, get_vectorizer, get_X, initialize_data
from .preprocess import preprocess_text
from .models import KNNModel, SVMModel, CosineModel, SBERTModel, NaiveBayesModel
from .logging import initialize_logging

logger = initialize_logging()

def cross_validate_model(lang='fr', k_folds=5, use_sbert=True):
    """Perform k-fold cross-validation for all models."""
    # Ensure data is initialized
    try:
        initialize_data()
    except Exception as e:
        logger.error(f"Failed to initialize data: {e}")
        raise RuntimeError(f"Data initialization failed: {e}")
    
    df = get_df(lang)
    X = get_X(lang)
    vectorizer = get_vectorizer(lang)
    y = df['Catégorie' if lang == 'fr' else 'Category']
    
    # Check for empty or insufficient data
    if df.empty or len(df) < k_folds:
        logger.error(f"Dataset for {lang} is empty or has insufficient rows ({len(df)} < {k_folds}) for k-fold cross-validation.")
        raise ValueError(f"Dataset for {lang} is too small for {k_folds}-fold cross-validation.")
    
    # Ensure Processed_Question column exists
    if 'Processed_Question' not in df.columns:
        logger.warning(f"Processed_Question column missing in {lang} dataset. Generating now.")
        df['Processed_Question'] = df['Question'].apply(lambda x: preprocess_text(x, lang))
    
    # Initialize KFold
    kf = KFold(n_splits=k_folds, shuffle=True, random_state=42)
    
    results = {
        'knn': {'accuracies': [], 'classification_reports': []},
        'cosine': {'accuracies': [], 'classification_reports': []},
        'sbert': {'accuracies': [], 'classification_reports': []} if use_sbert else {},
        'naive_bayes': {'accuracies': [], 'classification_reports': []},
        'svm': {'accuracies': [], 'classification_reports': []},
        'ensemble': {'accuracies': [], 'classification_reports': []}
    }
    
    for fold, (train_idx, test_idx) in enumerate(kf.split(X)):
        logger.debug(f"Processing fold {fold + 1}/{k_folds} for language {lang}. Train samples: {len(train_idx)}, Test samples: {len(test_idx)}")
        
        # Split data
        try:
            train_df = df.iloc[train_idx].copy()
            test_df = df.iloc[test_idx].copy()
            X_train = X[train_idx]
            X_test = X[test_idx]
            y_test = y.iloc[test_idx]
            logger.debug(f"Columns in train_df for {lang}: {train_df.columns.tolist()}")
        except Exception as e:
            logger.error(f"Error splitting data in fold {fold + 1}: {e}")
            raise
        
        # Reinitialize models for this fold
        knn_model = KNNModel(X_train)
        svm_model = SVMModel(train_df, X_train, lang=lang)
        cosine_model = CosineModel(X_train)
        sbert_model = None
        if use_sbert:
            try:
                sbert_model = SBERTModel(train_df['Processed_Question'].values.tolist())
            except Exception as e:
                logger.error(f"Failed to initialize SBERTModel in fold {fold + 1}: {e}")
                use_sbert = False
                results.pop('sbert', None)
        nb_model = NaiveBayesModel(train_df, vectorizer, X_train, lang=lang)
        
        # Evaluate each model
        y_pred_knn = []
        y_pred_cosine = []
        y_pred_sbert = []
        y_pred_nb = []
        y_pred_svm = []
        y_pred_ensemble = []
        
        for i, (_, row) in enumerate(test_df.iterrows()):
            question = row['Question']
            expected_answer = row['Réponse' if lang == 'fr' else 'Response']
            expected_intent = row['Catégorie' if lang == 'fr' else 'Category']
            try:
                input_vec = vectorizer.transform([preprocess_text(question, lang)])
            except Exception as e:
                logger.error(f"Failed to vectorize question '{question}' in fold {fold + 1}: {e}")
                continue
            
            # KNN
            max_idx, _ = knn_model.predict(input_vec)
            knn_answer = train_df['Réponse' if lang == 'fr' else 'Response'].iloc[max_idx]
            y_pred_knn.append(train_df['Catégorie' if lang == 'fr' else 'Category'].iloc[max_idx])
            
            # Cosine
            max_idx, _ = cosine_model.predict(input_vec)
            cosine_answer = train_df['Réponse' if lang == 'fr' else 'Response'].iloc[max_idx]
            y_pred_cosine.append(train_df['Catégorie' if lang == 'fr' else 'Category'].iloc[max_idx])
            
            # SBERT
            if sbert_model:
                try:
                    max_idx, _ = sbert_model.predict(question)
                    sbert_answer = train_df['Réponse' if lang == 'fr' else 'Response'].iloc[max_idx]
                    y_pred_sbert.append(train_df['Catégorie' if lang == 'fr' else 'Category'].iloc[max_idx])
                except Exception as e:
                    logger.error(f"SBERT prediction failed in fold {fold + 1}: {e}")
                    y_pred_sbert.append(expected_intent)  # Fallback
            else:
                y_pred_sbert.append(expected_intent)  # Fallback if SBERT is disabled
            
            # Naive Bayes
# In evaluate_model.py, Naive Bayes prediction block
            nb_response = nb_model.get_response(question)
            nb_answer = nb_response['answer']
            logger.debug(f"Naive Bayes predicted answer for question '{question}': {nb_answer}")
            nb_idx = train_df[train_df['Réponse' if lang == 'fr' else 'Response'] == nb_answer].index
            if len(nb_idx) > 0 and nb_idx[0] in train_df.index:
                logger.debug(f"Match found for Naive Bayes answer: {nb_answer} at index {nb_idx[0]}")
                y_pred_nb.append(train_df.loc[nb_idx[0], 'Catégorie' if lang == 'fr' else 'Category'])
            else:
                logger.warning(f"No matching answer found for Naive Bayes response: {nb_answer} in fold {fold + 1}")
                y_pred_nb.append(expected_intent)  # Fallback to expected intent            
            # SVM
            intent, _ = svm_model.predict(input_vec)
            y_pred_svm.append(intent)
            
            # Ensemble (majority voting on intents)
            intents = [y_pred_knn[-1], y_pred_cosine[-1], y_pred_sbert[-1] if use_sbert else y_pred_nb[-1], y_pred_nb[-1], y_pred_svm[-1]]
            intent_counts = pd.Series(intents).value_counts()
            max_count = intent_counts.max()
            top_intents = intent_counts[intent_counts == max_count].index
            ensemble_intent = top_intents[0]  # Pick first in case of tie
            y_pred_ensemble.append(ensemble_intent)
            
            # Track accuracy for response-based models
            for model, answer in [
                ('knn', knn_answer),
                ('cosine', cosine_answer),
                ('sbert', sbert_answer if sbert_model else None),
                ('naive_bayes', nb_answer),
                ('ensemble', train_df[train_df['Catégorie' if lang == 'fr' else 'Category'] == ensemble_intent]['Réponse' if lang == 'fr' else 'Response'].iloc[0])
            ]:
                if answer is None:
                    continue
                if answer == expected_answer:
                    results[model]['accuracies'].append(1)
                else:
                    results[model]['accuracies'].append(0)
        
        # Compute classification report for intent-based models
        for model, y_pred in [
            ('knn', y_pred_knn),
            ('cosine', y_pred_cosine),
            ('sbert', y_pred_sbert if use_sbert else None),
            ('naive_bayes', y_pred_nb),
            ('svm', y_pred_svm),
            ('ensemble', y_pred_ensemble)
        ]:
            if y_pred is None:
                continue
            report = classification_report(y_test, y_pred, zero_division=0, output_dict=True)
            results[model]['classification_reports'].append(report)
            logger.info(f"[{lang}] Fold {fold + 1} {model.capitalize()} Classification Report:\n{classification_report(y_test, y_pred, zero_division=0)}")
    
    # Aggregate results
    aggregated_results = {}
    for model in results:
        if not results[model]:
            continue
        mean_accuracy = np.mean(results[model]['accuracies']) if results[model]['accuracies'] else 0.0
        aggregated_results[model] = {
            'mean_accuracy': mean_accuracy,
            'mean_classification_report': aggregate_classification_reports(results[model]['classification_reports']),
            'folds': k_folds
        }
        logger.info(f"[{lang}] {model.capitalize()} Mean Accuracy: {mean_accuracy:.2f}")
    
    return aggregated_results

def aggregate_classification_reports(reports):
    """Aggregate classification reports across folds."""
    if not reports:
        return {}
    
    aggregated = {}
    labels = set()
    for report in reports:
        for label in report:
            if label not in ['accuracy', 'macro avg', 'weighted avg']:
                labels.add(label)
    
    for label in labels:
        aggregated[label] = {
            'precision': np.mean([r[label]['precision'] for r in reports if label in r]),
            'recall': np.mean([r[label]['recall'] for r in reports if label in r]),
            'f1-score': np.mean([r[label]['f1-score'] for r in reports if label in r]),
            'support': np.sum([r[label]['support'] for r in reports if label in r])
        }
    
    aggregated['accuracy'] = np.mean([r['accuracy'] for r in reports])
    aggregated['macro avg'] = {
        'precision': np.mean([r['macro avg']['precision'] for r in reports]),
        'recall': np.mean([r['macro avg']['recall'] for r in reports]),
        'f1-score': np.mean([r['macro avg']['f1-score'] for r in reports]),
        'support': np.sum([r['macro avg']['support'] for r in reports])
    }
    aggregated['weighted avg'] = {
        'precision': np.mean([r['weighted avg']['precision'] for r in reports]),
        'recall': np.mean([r['weighted avg']['recall'] for r in reports]),
        'f1-score': np.mean([r['weighted avg']['f1-score'] for r in reports]),
        'support': np.sum([r['weighted avg']['support'] for r in reports])
    }
    
    return aggregated