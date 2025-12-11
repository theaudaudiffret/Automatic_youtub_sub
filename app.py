import streamlit as st
import yt_dlp
import os
import json
import pandas as pd

# Import de tous nos modules
from diarization import upload_to_pyannote, start_identification_job, start_diarization_job, wait_for_result
from transcript import load_whisper_model, transcribe_segments
from translate import translate_transcript
from voiceprint import render_add_voiceprint_ui
from final_video import download_video, generate_subtitled_video 

st.set_page_config(page_title="Youtube-Auto-Subtitler", page_icon="🧠", layout="wide")

# --- Configuration ---
DB_PATH = "voice_database.json"

# --- Fonctions Utilitaires ---
def load_voice_database():
    if not os.path.exists(DB_PATH): return {}
    try:
        with open(DB_PATH, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def get_speaker_style(speaker_name, db):
    # Si c'est un SPEAKER_XX générique (mode Diarization)
    if "SPEAKER_" in speaker_name:
        # On génère une couleur basée sur le numéro pour les différencier visuellement
        return {"avatar": "🗣️", "display_name": speaker_name, "color": "grey"}
    
    # Si c'est une personne identifiée (mode Identification)
    if speaker_name in db and "style" in db[speaker_name]:
        return db[speaker_name]["style"]
        
    # Cas par défaut
    if "Inconnu" in speaker_name:
        return {"avatar": "❓", "color": "grey"}
        
    return {"avatar": "👤", "color": "grey"}

def download_audio(youtube_url):
    download_path = "downloads"
    if not os.path.exists(download_path): os.makedirs(download_path)
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{download_path}/%(id)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'wav'}],
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            title = info.get('title', 'Vidéo')
            filename = ydl.prepare_filename(info)
            final_filename = os.path.splitext(filename)[0] + ".wav"
            return final_filename, title
    except Exception as e: return None, str(e)

# --- UI ---

st.title("🧠 Analyseur Vidéo Générique")
st.markdown("Identification Vocale & Traduction Automatique")

# Sidebar
with st.sidebar:
    st.header("Paramètres")
    api_key = st.text_input("Clé API Pyannote", type="password")
    
    # Ajout de voix
    render_add_voiceprint_ui(DB_PATH, api_key)
    st.divider()

    # Chargement dynamique de la DB
    voice_db = load_voice_database()
    
    if voice_db:
        st.success(f"Base de données : {len(voice_db)} profils")
        with st.expander("Voir les profils actifs"):
            for name, data in voice_db.items():
                style = data.get("style", {"avatar": "👤"})
                st.write(f"{style['avatar']} **{name}**")
    else:
        st.warning("Aucune base de données trouvée.")

    st.divider()
    target_lang = st.selectbox("Langue de traduction", ["fr", "en", "es", "de", "it"], index=0)

# --- ZONE PRINCIPALE ---

col_main_1, col_main_2 = st.columns([3, 1])
with col_main_1:
    url = st.text_input("URL YouTube")

with col_main_2:
    # --- NOUVEAU SÉLECTEUR DE MODE ---
    mode_analyse = st.radio(
        "Mode IA :",
        ["Identification (Nommée)", "Diarization (Anonyme)"],
        index=0,
        help="Identification utilise la DB pour trouver les noms. Diarization distingue juste les voix (Speaker 00, 01...)."
    )

# --- BLOC 1 : CALCUL (Lancer l'analyse) ---
if st.button("Lancer l'analyse"):
    if not api_key or not url:
        st.error("Veuillez remplir les champs obligatoires (API Key & URL).")
        st.stop()

    with st.spinner("Initialisation des modèles IA..."):
        whisper_model = load_whisper_model()

    status_box = st.status("Traitement en cours...", expanded=True)

    try:
        # 1. Download
        status_box.write("📥 1/4 Téléchargement de l'audio...")
        file_path, title = download_audio(url)
        if not file_path: st.stop()

        # 2. Pyannote Processing (Identification OU Diarization)
        status_box.write(f"👤 2/4 Analyse Pyannote ({mode_analyse})...")
        media_name, err = upload_to_pyannote(api_key, file_path)
        if err: st.error(err); st.stop()
        
        # Diarization ou Identification
        if mode_analyse == "Identification (Nommée)":
            # Mode identification
            if not voice_db:
                
                st.error("Erreur : Le mode Identification nécessite au moins une voix dans la base de données (ajout via la sidebar).")
                st.stop()
            job_id, err = start_identification_job(api_key, media_name, voice_db)
        else:
            # Mode Diarization 
            job_id, err = start_diarization_job(api_key, media_name)
            
        if err: st.error(err); st.stop()
        
        # Attente du résultat (la fonction wait_for_result gère les deux types de sortie)
        pyannote_res = wait_for_result(api_key, job_id)
        if "error" in pyannote_res: st.error(pyannote_res['error']); st.stop()
            
        segments = pyannote_res.get("segments", [])
        if not segments: st.warning("Aucun segment vocal détecté."); st.stop()

        # 3. Whisper Transcription
        status_box.write("📝 3/4 Transcription du texte...")
        # Note : transcript.py gère déjà intelligemment le champ 'speaker' ou 'match'
        transcript_en = transcribe_segments(file_path, segments, whisper_model)
        
        # 4. Traduction
        status_box.write(f"🌍 4/4 Traduction ({target_lang})...")
        final_transcript = translate_transcript(transcript_en, target_lang=target_lang)
        
        status_box.update(label="Analyse terminée avec succès !", state="complete")
        
        # --- SAUVEGARDE EN SESSION STATE ---
        st.session_state['analysis_done'] = True
        st.session_state['final_transcript'] = final_transcript
        st.session_state['video_title'] = title
        st.session_state['video_url'] = url 
        
    except Exception as e:
        st.error(f"Une erreur inattendue est survenue : {e}")


# --- BLOC 2 : AFFICHAGE & VIDÉO (Persistant) ---

if st.session_state.get('analysis_done'):
    
    final_transcript = st.session_state['final_transcript']
    title = st.session_state['video_title']
    saved_url = st.session_state['video_url']

    st.divider()
    st.subheader(title)
    
    show_original = st.toggle("Voir texte original")

    # Affichage du Chat
    for entry in final_transcript:
        speaker_name = entry['speaker']
        
        # Récupération du style (fonction mise à jour plus haut pour gérer SPEAKER_00)
        style = get_speaker_style(speaker_name, voice_db)
        avatar = style.get("avatar", "👤")
        display_name = style.get("display_name", speaker_name) 
        
        with st.chat_message(name=speaker_name, avatar=avatar):
            st.markdown(f"**{display_name}**")
            st.write(entry['text_translated'])
            if show_original:
                st.caption(entry['text'])

    # Export CSV
    if final_transcript:
        df = pd.DataFrame(final_transcript)
        # On s'assure que les colonnes existent
        cols = ["start", "end", "speaker", "text_translated", "text"]
        existing_cols = [c for c in cols if c in df.columns]
        csv = df[existing_cols].to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Télécharger CSV", csv, "transcript.csv", "text/csv")

    # --- SECTION VIDÉO ---
    st.divider()
    st.subheader("🎬 Génération de la Vidéo Finale")
    
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        lang_choice = st.radio(
            "Langue des sous-titres :",
            ["Français (Traduit)", "Langue Originale (Transcription)"],
            index=0
        )
    
    use_original = (lang_choice == "Langue Originale (Transcription)")
    
    if st.button("Générer la vidéo sous-titrée (MP4)"):
        with st.status("Montage vidéo en cours...", expanded=True) as vid_status:
            
            vid_status.write("📥 Téléchargement de la source vidéo...")
            video_source_path = download_video(saved_url)
            
            if video_source_path:
                vid_status.write(f"⚙️ Incrustation des sous-titres ({'Original' if use_original else 'Traduit'})...")
                
                final_video_path = generate_subtitled_video(
                    video_source_path, 
                    final_transcript, 
                    use_original_lang=use_original
                )
                
                if final_video_path and os.path.exists(final_video_path):
                    vid_status.update(label="Vidéo prête !", state="complete")
                    st.success("Vidéo générée !")
                    
                    st.video(final_video_path)
                    
                    with open(final_video_path, "rb") as v_file:
                        st.download_button(
                            label="⬇️ Télécharger MP4",
                            data=v_file,
                            file_name="video_sous_titree.mp4",
                            mime="video/mp4"
                        )
                else:
                    vid_status.update(label="Erreur Montage", state="error")
            else:
                vid_status.update(label="Erreur Download Vidéo", state="error")