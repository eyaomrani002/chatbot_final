import json
import os
from flask import session

def save_conversation(question, answer, link, category, response_id):
    history_file = 'conversations.json'
    conversations = get_conversations()
    session_id = session.get('session_id', 'default')
    conversation = {
        'session_id': session_id,
        'question': question,
        'answer': answer,
        'link': link,
        'category': category,
        'response_id': response_id,
        'rating': 'Non évalué'
    }
    conversations.append(conversation)
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    
    session.setdefault('context', []).append({'question': question, 'answer': answer})
    if len(session['context']) > 5:
        session['context'] = session['context'][-5:]

def get_conversations():
    history_file = 'conversations.json'
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_context():
    return session.get('context', [])