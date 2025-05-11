import requests
import json
from typing import Dict, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base URL of the running Flask app
BASE_URL = "http://127.0.0.1:5000"

# Test questions with expected responses, intents, and confidence thresholds
TEST_CASES = [
    {
        "question": "Quand commence le semestre ?",
        "expected_answer": "Le semestre commence le 1er septembre. Vérifiez le calendrier universitaire.",
        "expected_intent": "Horaires",
        "language": "fr",
        "min_confidence": 0.7
    },
    {
        "question": "When does the semester start?",
        "expected_answer": "The semester starts on September 1st. Check the university calendar.",
        "expected_intent": "Horaires",
        "language": "en",
        "min_confidence": 0.7
    },
    {
        "question": "Qui enseigne le cours de Python ?",
        "expected_answer": "Le cours est enseigné par le Pr. Dupont. Consultez le programme.",
        "expected_intent": "Professeurs",
        "language": "fr",
        "min_confidence": 0.7
    },
    {
        "question": "Bonsoir",
        "expected_answer": "Bonsoir ! Comment puis-je vous aider ?",
        "expected_intent": "Général",
        "language": "fr",
        "min_confidence": 0.0,
        "max_confidence": 0.3
    }
]

def test_chat_endpoint(method: str = "knn") -> List[Dict]:
    """Test the /chat endpoint with the specified method (knn or cosine)."""
    results = []
    
    for case in TEST_CASES:
        question = case["question"]
        expected_answer = case["expected_answer"]
        expected_intent = case["expected_intent"]
        language = case["language"]
        min_confidence = case.get("min_confidence", 0.0)
        max_confidence = case.get("max_confidence", 1.0)
        
        logger.info(f"Testing question: {question} (method: {method})")
        
        try:
            # Send POST request to /chat
            response = requests.post(
                f"{BASE_URL}/chat",
                data={"message": question},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            
            # Check for errors
            if "error" in data:
                logger.error(f"Error for '{question}': {data['error']}")
                results.append({
                    "question": question,
                    "status": "failed",
                    "error": data["error"]
                })
                continue
            
            # Verify response
            actual_answer = data.get("answer")
            actual_intent = data.get("intent")
            confidence = data.get("confidence", 0.0)
            ask_for_response = data.get("ask_for_response", False)
            
            # Check answer correctness
            answer_correct = (
                expected_answer is None or
                actual_answer == expected_answer
            )
            
            # Check intent correctness (SVM)
            intent_correct = actual_intent == expected_intent
            
            # Check confidence range
            confidence_correct = min_confidence <= confidence <= max_confidence
            
            # Check if low-confidence triggers form
            ask_for_response_correct = (
                (confidence < 0.3 and ask_for_response) or
                (confidence >= 0.3 and not ask_for_response)
            )
            
            # Log results
            status = "passed" if all([answer_correct, intent_correct, confidence_correct, ask_for_response_correct]) else "failed"
            logger.info(f"Answer: {actual_answer}")
            logger.info(f"Intent: {actual_intent} (Confidence: {confidence:.2f})")
            logger.info(f"Form triggered: {ask_for_response}")
            logger.info(f"Status: {status}")
            
            results.append({
                "question": question,
                "status": status,
                "answer_correct": answer_correct,
                "intent_correct": intent_correct,
                "confidence_correct": confidence_correct,
                "ask_for_response_correct": ask_for_response_correct,
                "actual_answer": actual_answer,
                "actual_intent": actual_intent,
                "confidence": confidence
            })
            
        except requests.RequestException as e:
            logger.error(f"Request failed for '{question}': {e}")
            results.append({
                "question": question,
                "status": "failed",
                "error": str(e)
            })
    
    return results

def summarize_results(results: List[Dict]):
    """Summarize test results."""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    precision = passed / total if total > 0 else 0.0
    
    logger.info(f"\nSummary:")
    logger.info(f"Total tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Precision: {precision:.2f}")
    
    for result in results:
        if result["status"] == "failed":
            logger.warning(f"Failed test: {result['question']}")
            if "error" in result:
                logger.warning(f"Error: {result['error']}")
            else:
                logger.warning(f"Answer correct: {result['answer_correct']}")
                logger.warning(f"Intent correct: {result['intent_correct']}")
                logger.warning(f"Confidence correct: {result['confidence_correct']}")
                logger.warning(f"Form triggered correct: {result['ask_for_response_correct']}")

def main():
    """Run tests for both KNN and Cosine Similarity models."""
    # Test KNN
    logger.info("Testing KNN model...")
    knn_results = test_chat_endpoint(method="knn")
    summarize_results(knn_results)
    
    # Test Cosine Similarity
    logger.info("\nTesting Cosine Similarity model...")
    logger.warning("Please ensure data_manager.py is set to use 'cosine' method in get_best_response")
    cosine_results = test_chat_endpoint(method="cosine")
    summarize_results(cosine_results)

if __name__ == "__main__":
    main()