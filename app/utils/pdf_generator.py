from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from io import BytesIO
import os
import bleach
from .logging import initialize_logging
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import Counter

logger = initialize_logging()

def generate_summary(conversations):
    """Generate a summary of conversation topics using keyword extraction."""
    if not conversations:
        return "Aucune conversation à résumer."
    
    texts = [conv['question'] + ' ' + conv['answer'] for conv in conversations if isinstance(conv, dict)]
    vectorizer = TfidfVectorizer(max_features=5)
    try:
        X = vectorizer.fit_transform(texts)
        feature_names = vectorizer.get_feature_names_out()
        keywords = feature_names.tolist()
        return f"Résumé des sujets discutés : {', '.join(keywords)}"
    except ValueError:
        return "Impossible de générer un résumé (conversations insuffisantes ou vides)."

def export_conversations(data):
    """Export conversations to PDF with a summary."""
    try:
        if not data or 'conversations' not in data or not isinstance(data['conversations'], list):
            return {'error': 'Données de conversation invalides ou manquantes'}, 400

        valid_conversations = [
            conv for conv in data['conversations']
            if isinstance(conv, dict) and 'question' in conv and 'answer' in conv
        ]
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        
        # Charger la police Amiri
        try:
            font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../fonts', 'Amiri-Regular.ttf')
            pdfmetrics.registerFont(TTFont('Amiri', font_path))
            p.setFont('Amiri', 12)
        except Exception as e:
            logger.warning(f"Échec du chargement de la police Amiri, utilisation de Helvetica: {e}")
            p.setFont('Helvetica', 12)

        y = 750
        margin = 50
        max_width = 500  # Largeur max pour le texte
        line_height = 20

        # Ajouter le titre
        p.setFont('Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 16)
        p.drawString(margin, y, "Exportation des Conversations")
        y -= 40

        # Ajouter le résumé
        p.setFont('Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12)
        summary = generate_summary(valid_conversations)
        p.drawString(margin, y, "Résumé :")
        y -= line_height
        # Gérer le texte long avec des retours à la ligne
        words = summary.split()
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            if p.stringWidth(test_line, 'Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12) < max_width:
                current_line.append(word)
            else:
                p.drawString(margin, y, ' '.join(current_line))
                y -= line_height
                current_line = [word]
                if y < 50:
                    p.showPage()
                    p.setFont('Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12)
                    y = 750
        if current_line:
            p.drawString(margin, y, ' '.join(current_line))
            y -= line_height * 2

        # Ajouter les conversations
        for conv in valid_conversations:
            question = bleach.clean(str(conv['question']))
            answer = bleach.clean(str(conv['answer']))
            
            # Afficher la question
            p.drawString(margin, y, f"Question :")
            y -= line_height
            words = question.split()
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if p.stringWidth(test_line, 'Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12) < max_width:
                    current_line.append(word)
                else:
                    p.drawString(margin, y, ' '.join(current_line))
                    y -= line_height
                    current_line = [word]
                    if y < 50:
                        p.showPage()
                        p.setFont('Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12)
                        y = 750
            if current_line:
                p.drawString(margin, y, ' '.join(current_line))
                y -= line_height

            # Afficher la réponse
            p.drawString(margin, y, f"Réponse :")
            y -= line_height
            words = answer.split()
            current_line = []
            for word in words:
                test_line = ' '.join(current_line + [word])
                if p.stringWidth(test_line, 'Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12) < max_width:
                    current_line.append(word)
                else:
                    p.drawString(margin, y, ' '.join(current_line))
                    y -= line_height
                    current_line = [word]
                    if y < 50:
                        p.showPage()
                        p.setFont('Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12)
                        y = 750
            if current_line:
                p.drawString(margin, y, ' '.join(current_line))
                y -= line_height * 2

            if y < 50:
                p.showPage()
                p.setFont('Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12)
                y = 750
        
        if not valid_conversations:
            p.setFont('Amiri' if 'Amiri' in pdfmetrics.getRegisteredFontNames() else 'Helvetica', 12)
            p.drawString(margin, 750, "Aucune conversation valide trouvée.")
        
        p.save()
        buffer.seek(0)
        return buffer, 'application/pdf', 'conversation.pdf'
    
    except Exception as e:
        logger.error(f"Erreur dans export_conversations: {e}", exc_info=True)
        return {'error': 'Une erreur interne est survenue.'}, 500