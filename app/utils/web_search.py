import requests
from bs4 import BeautifulSoup
import logging
from urllib.parse import quote_plus
import re
import pandas as pd
import os
from datetime import datetime
import uuid
import time

logger = logging.getLogger(__name__)

def search_google(query, num_results=3):
    """
    Effectue une recherche Google et retourne les résultats
    """
    try:
        # Encoder la requête pour l'URL
        encoded_query = quote_plus(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        
        # Simuler un navigateur pour éviter d'être bloqué
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Ajouter un délai pour éviter d'être bloqué
        time.sleep(1)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Extraire les résultats de recherche
        for g in soup.find_all('div', class_='g'):
            title_element = g.find('h3')
            link_element = g.find('a')
            snippet_element = g.find('div', class_='VwiC3b')
            
            if title_element and link_element and snippet_element:
                title = title_element.text
                link = link_element['href']
                snippet = snippet_element.text
                
                # Vérifier si le lien est valide
                if link.startswith('http'):
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'source': 'Google'
                    })
                    
                    if len(results) >= num_results:
                        break
        
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la recherche Google: {e}")
        return []

def search_iset_website(query, num_results=3):
    """
    Recherche spécifiquement sur le site de l'ISET
    """
    try:
        # Encoder la requête pour l'URL
        encoded_query = quote_plus(f"site:iset.rnu.tn {query}")
        url = f"https://www.google.com/search?q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Ajouter un délai pour éviter d'être bloqué
        time.sleep(1)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for g in soup.find_all('div', class_='g'):
            title_element = g.find('h3')
            link_element = g.find('a')
            snippet_element = g.find('div', class_='VwiC3b')
            
            if title_element and link_element and snippet_element:
                title = title_element.text
                link = link_element['href']
                snippet = snippet_element.text
                
                if 'iset.rnu.tn' in link:
                    results.append({
                        'title': title,
                        'link': link,
                        'snippet': snippet,
                        'source': 'Site ISET'
                    })
                    
                    if len(results) >= num_results:
                        break
        
        return results
    except Exception as e:
        logger.error(f"Erreur lors de la recherche sur le site ISET: {e}")
        return []

def auto_learn(question, answer, source, link):
    """
    Ajoute automatiquement la nouvelle question/réponse à la base de données
    """
    try:
        # Charger le fichier CSV existant
        df_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'iset_questions_reponses.csv')
        df = pd.read_csv(df_path)
        
        # Créer une nouvelle entrée
        new_row = {
            'Question': question,
            'Réponse': answer,
            'Lien': link,
            'Catégorie': 'Auto-apprentissage',
            'Rating': 0,
            'Source': source,
            'Date_Ajout': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'response_id': str(uuid.uuid4())
        }
        
        # Ajouter la nouvelle entrée
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        
        # Sauvegarder le fichier
        df.to_csv(df_path, index=False, encoding='utf-8')
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'auto-apprentissage: {e}")
        return False

def get_web_response(question, confidence):
    """
    Obtient une réponse basée sur la recherche web si la confiance est faible
    """
    if confidence >= 0.3:  # Si la confiance est suffisante, ne pas faire de recherche web
        return None
    
    # Rechercher sur le site ISET d'abord
    iset_results = search_iset_website(question)
    if iset_results:
        best_result = iset_results[0]
        response = {
            'answer': f"Selon le site de l'ISET : {best_result['snippet']}",
            'link': best_result['link'],
            'source': 'Site ISET',
            'confidence': 0.2,  # Confiance moyenne car c'est une source fiable
            'sources': [{
                'title': best_result['title'],
                'link': best_result['link'],
                'snippet': best_result['snippet'],
                'source': 'Site ISET'
            }]
        }
        
        # Auto-apprentissage
        auto_learn(question, best_result['snippet'], 'Site ISET', best_result['link'])
        return response
    
    # Si pas de résultats sur ISET, chercher sur Google
    google_results = search_google(question)
    if google_results:
        best_result = google_results[0]
        response = {
            'answer': f"D'après mes recherches : {best_result['snippet']}",
            'link': best_result['link'],
            'source': 'Recherche Google',
            'confidence': 0.1,  # Confiance plus faible car source externe
            'sources': [{
                'title': result['title'],
                'link': result['link'],
                'snippet': result['snippet'],
                'source': result['source']
            } for result in google_results[:3]]
        }
        
        # Auto-apprentissage
        auto_learn(question, best_result['snippet'], 'Google', best_result['link'])
        return response
    
    return None 