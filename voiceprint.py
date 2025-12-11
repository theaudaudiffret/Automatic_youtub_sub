import streamlit as st
import requests
import json
import os
import time
import yt_dlp
from pydub import AudioSegment
from diarization import upload_to_pyannote

def download_and_cut_audio(youtube_url, start_sec, end_sec):
    """Télécharge et coupe l'audio (inchangé)."""
    temp_dir = "temp_voiceprints"
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)

    timestamp = int(time.time())
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{temp_dir}/full_{timestamp}.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'wav'}],
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info)
            full_audio_path = os.path.splitext(filename)[0] + ".wav"

        audio = AudioSegment.from_wav(full_audio_path)
        start_ms = start_sec * 1000
        end_ms = end_sec * 1000
        if end_ms > len(audio): end_ms = len(audio)
        
        cut_audio = audio[start_ms:end_ms]
        final_cut_path = f"{temp_dir}/sample_{timestamp}_{start_sec}_{end_sec}.wav"
        cut_audio.export(final_cut_path, format="wav")
        
        if os.path.exists(full_audio_path): os.remove(full_audio_path)
        return final_cut_path
    except Exception as e:
        return None

def extract_voiceprint_via_api(api_key, file_path):
    """
    1. Upload le fichier.
    2. Lance le JOB de voiceprint.
    3. Attend le résultat (Polling).
    """
    # 1. Upload
    try:
        media_name, error = upload_to_pyannote(api_key, file_path)
        if error: return None, error
    except Exception as e: return None, str(e)

    # 2. Lancement du Job (POST)
    url = "https://api.pyannote.ai/v1/voiceprint"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"url": media_name}

    try:
        response = requests.post(url, headers=headers, json=data)
        
        # Le job est créé (200 ou 201)
        if response.status_code in [200, 201]:
            job_data = response.json()
            job_id = job_data.get("jobId")
        else:
            return None, f"Erreur Lancement ({response.status_code}): {response.text}"
            
    except Exception as e:
        return None, str(e)

    # 3. Attente du résultat (GET)
    # On boucle tant que le statut n'est pas 'succeeded' ou 'failed'
    status_url = f"https://api.pyannote.ai/v1/jobs/{job_id}"
    
    # Barre de progression locale pour faire patienter
    bar = st.progress(0)
    
    for i in range(30): # Timeout max ~60 secondes (30 * 2s)
        try:
            res = requests.get(status_url, headers=headers)
            if res.status_code != 200:
                return None, f"Erreur Status: {res.text}"
            
            status_data = res.json()
            status = status_data.get("status")
            
            if status == "succeeded":
                bar.progress(100)
                # Le voiceprint est dans output -> voiceprint
                output = status_data.get("output", {})
                return output.get("voiceprint"), None
                
            elif status == "failed":
                return None, "L'IA a échoué à extraire une voix."
            
            # Si "pending" ou "processing"
            bar.progress((i + 1) * 3)
            time.sleep(2)
            
        except Exception as e:
            return None, str(e)
            
    return None, "Timeout: Le job a pris trop de temps."

def render_add_voiceprint_ui(db_path, api_key):
    """Interface (inchangée mais appelle la fonction async corrigée)."""
    with st.expander("➕ Ajouter une voix (YouTube)"):
        st.caption("Extrait un voiceprint via l'API Pyannote officielle.")
        
        new_name = st.text_input("Nom de la personne")
        new_avatar = st.selectbox("Avatar", ["👤", "🎤", "🎾", "🎸", "👨‍⚕️", "👩‍🚀", "🤖", "🦊"], index=0)
        
        youtube_url = st.text_input("URL YouTube source")
        
        col1, col2 = st.columns(2)
        with col1:
            start_t = st.number_input("Début (sec)", min_value=0, value=0)
        with col2:
            end_t = st.number_input("Fin (sec)", min_value=1, value=10)

        if st.button("Extraire & Ajouter"):
            if not api_key:
                st.error("Clé API requise.")
            elif not new_name or not youtube_url:
                st.error("Champs manquants.")
            else:
                with st.status("Traitement en cours...", expanded=True) as status:
                    
                    status.write("✂️ Préparation audio...")
                    sample_path = download_and_cut_audio(youtube_url, start_t, end_t)
                    
                    if sample_path:
                        status.write("🧠 Calcul du voiceprint (Attente API)...")
                        # Appel corrigé avec attente
                        embedding, error = extract_voiceprint_via_api(api_key, sample_path)
                        
                        if os.path.exists(sample_path): os.remove(sample_path)
                        
                        if embedding:
                            # Sauvegarde
                            if os.path.exists(db_path):
                                with open(db_path, 'r', encoding='utf-8') as f:
                                    db = json.load(f)
                            else:
                                db = {}
                            
                            db[new_name] = {
                                "embedding": embedding,
                                "style": {
                                    "avatar": new_avatar,
                                    "display_name": new_name,
                                    "color": "orange"
                                }
                            }
                            
                            with open(db_path, 'w', encoding='utf-8') as f:
                                json.dump(db, f, indent=4, ensure_ascii=False)
                                
                            status.update(label="Terminé !", state="complete")
                            st.success(f"✅ **{new_name}** ajouté !")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            status.update(label="Erreur API", state="error")
                            st.error(error)
                    else:
                        status.update(label="Erreur Audio", state="error")