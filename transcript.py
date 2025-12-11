import whisper
import uuid
import os
import streamlit as st
from pydub import AudioSegment

@st.cache_resource
def load_whisper_model():
    """Charge le modèle Whisper en cache (téléchargé une seule fois)."""
    # 'base' est un bon compromis vitesse/précision. 
    # Utilisez 'small' ou 'medium' si vous avez une bonne machine.
    return whisper.load_model("base")

def transcribe_segments(audio_path, segments, model):
    """
    Découpe l'audio et transcrit.
    Logique intelligente : Identification > Diarisation simple > Inconnu
    """
    try:
        audio = AudioSegment.from_file(audio_path)
    except Exception as e:
        st.error(f"Erreur chargement audio : {e}")
        return []

    full_transcript = []
    total_segments = len(segments)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, segment in enumerate(segments):
        start_ms = int(segment['start'] * 1000)
        end_ms = int(segment['end'] * 1000)
        
        # --- LOGIQUE CORRIGÉE ---

        # 1. Récupération des données brutes
        # En mode Diarization, 'speaker' contient déjà SPEAKER_00
        # En mode Identification, 'match' ou 'label' contient le nom
        candidate_name = segment.get('match') or segment.get('label')
        cluster_id = segment.get('speaker') 
        confidence = segment.get('confidence', 0.0)
        
        # 2. Logique unifiée
        if candidate_name and "SPEAKER_" not in candidate_name and confidence >= 0.90:
            final_name = candidate_name
        elif cluster_id:
            # En mode diarization pure, on aura juste SPEAKER_00, SPEAKER_01
            # On transforme pour que ce soit joli
            final_name = cluster_id#.replace("SPEAKER_", "Locuteur ")
        else:
            final_name = "Inconnu"

        # # 1. On cherche d'abord l'identification formelle (le 'match' ou 'label' via la DB)
        # identity = segment.get('match') or segment.get('label')
        
        # # 2. Si l'IA n'a pas trouvé de match (car sous le seuil de 0.85),
        # # on récupère l'ID de cluster brut (ex: SPEAKER_01) pour faire de la diarisation simple.
        # cluster_id = segment.get('speaker')
        
        # if identity and "SPEAKER_" not in identity:
        #     # C'est une personne identifiée (ex: "Novak")
        #     final_name = identity
        # elif cluster_id:
        #     # C'est une personne distincte, mais inconnue (ex: "Speaker 02")
        #     # On nettoie un peu le nom pour faire joli
        #     final_name = cluster_id.replace("SPEAKER_", "Intervenant ")
        # else:
        #     final_name = "Inconnu"
        # ------------------------
        
        # Extraction et transcription
        chunk = audio[start_ms:end_ms]
        chunk_filename = f"temp_{uuid.uuid4()}.wav"
        chunk.export(chunk_filename, format="wav")
        
        try:
            result = model.transcribe(chunk_filename, fp16=False)
            text = result['text'].strip()
            
            if text:
                full_transcript.append({
                    "speaker": final_name, # On utilise le nom calculé ci-dessus
                    "start": segment['start'],
                    "end": segment['end'],
                    "text": text
                })
                
            status_text.text(f"Traitement : {final_name} ({i+1}/{total_segments})")
            
        except Exception as e:
            print(f"Erreur : {e}")
        finally:
            if os.path.exists(chunk_filename): os.remove(chunk_filename)
            
        progress_bar.progress((i + 1) / total_segments)
        
    status_text.empty()
    progress_bar.empty()
    
    return full_transcript