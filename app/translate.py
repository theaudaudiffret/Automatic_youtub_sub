from deep_translator import GoogleTranslator
import streamlit as st
import time

def translate_transcript(transcript, target_lang='fr'):
    """
    Traduit une liste de segments de transcription.
    Ajoute un champ 'text_fr' (ou autre langue cible) à chaque segment.
    """
    
    # On utilise Google Translate via deep_translator (fiable et gratuit pour ce volume)
    translator = GoogleTranslator(source='auto', target=target_lang)
    
    translated_transcript = []
    total = len(transcript)
    
    # Barre de progression spécifique à la traduction
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, segment in enumerate(transcript):
        original_text = segment['text']
        
        try:
            # Traduction du texte
            translated_text = translator.translate(original_text)
            
            # On copie le segment pour ne pas écraser l'original
            new_segment = segment.copy()
            new_segment['text_translated'] = translated_text
            translated_transcript.append(new_segment)
            
        except Exception as e:
            # En cas d'erreur (ex: limite API), on garde le texte original
            print(f"Erreur traduction segment {i}: {e}")
            new_segment = segment.copy()
            new_segment['text_translated'] = f"[Erreur Traduction] {original_text}"
            translated_transcript.append(new_segment)
        
        # Mise à jour UI
        status_text.text(f"Traduction segment {i+1}/{total}...")
        progress_bar.progress((i + 1) / total)
        
        # Petite pause pour éviter de spammer l'API et se faire bloquer
        time.sleep(0.1)

    status_text.empty()
    progress_bar.empty()
    
    return translated_transcript