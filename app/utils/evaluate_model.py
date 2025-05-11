from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score
import pandas as pd
import numpy as np
from .data_manager import get_best_response
from .logging import initialize_logging

logger = initialize_logging()

def cross_validate_model(lang='fr', k_folds=5):
    from .data_manager import _state
    if not _state['initialized']:
        logger.error("Data not initialized.")
        raise RuntimeError("Data not initialized.")
    
    df = _state[lang]['df']
    X = _state[lang]['X']
    kf = KFold(n_splits=k_folds, shuffle=True, random_state=42)
    accuracies = []
    
    for train_idx, test_idx in kf.split(X):
        train_df = df.iloc[train_idx]
        test_df = df.iloc[test_idx]
        
        correct = 0
        total = len(test_df)
        
        for _, row in test_df.iterrows():
            question = row['Question']
            expected_answer = row['Réponse']
            response = get_best_response(question, method='ensemble')
            if response['answer'] == expected_answer:
                correct += 1
        
        accuracy = correct / total if total > 0 else 0
        accuracies.append(accuracy)
    
    mean_accuracy = np.mean(accuracies)
    logger.info(f"Cross-validation accuracy for {lang}: {mean_accuracy:.2f}")
    return {'mean_accuracy': mean_accuracy, 'folds': k_folds}