import streamlit as st
import yt_dlp
import os
import subprocess
import math

# ... (download_video et time_to_srt_format restent inchangés) ...
def download_video(youtube_url):
    download_path = "downloads_video"
    if not os.path.exists(download_path): os.makedirs(download_path)
    ydl_opts = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{download_path}/%(id)s.%(ext)s',
        'quiet': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            filename = ydl.prepare_filename(info)
            if not os.path.exists(filename):
                base = os.path.splitext(filename)[0]
                if os.path.exists(base + ".mp4"): return base + ".mp4"
            return filename
    except Exception as e: return None

def time_to_srt_format(seconds):
    millis = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

def split_text_into_chunks(text, max_chars=50):
    """Découpe intelligente (inchangée)."""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    for word in words:
        if current_length + len(word) + 1 > max_chars:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
            current_length += len(word) + 1
    if current_chunk: chunks.append(" ".join(current_chunk))
    return chunks

def generate_srt_file(transcript_data, srt_path, source_key='text_translated'):
    """
    Génère le SRT en choisissant la bonne langue via source_key.
    """
    srt_entries = []
    counter = 1
    
    for entry in transcript_data:
        original_start = entry['start']
        original_end = entry['end']
        duration = original_end - original_start
        
        # SÉLECTION DE LA LANGUE ICI
        # On cherche la clé demandée (ex: 'text'), sinon fallback sur l'autre
        raw_text = entry.get(source_key, entry.get('text', '')).replace('\n', ' ')
        
        speaker = entry.get('speaker', '')
        
        if "Inconnu" not in speaker and "Intervenant" not in speaker:
            prefix = f"{speaker}: "
        else:
            prefix = ""
            
        full_text = f"{prefix}{raw_text}"
        
        # Découpage et répartition (inchangé)
        text_chunks = split_text_into_chunks(full_text, max_chars=60)
        num_chunks = len(text_chunks)
        chunk_duration = duration / max(num_chunks, 1)
        
        for i, chunk in enumerate(text_chunks):
            chunk_start = original_start + (i * chunk_duration)
            chunk_end = chunk_start + chunk_duration
            if i < num_chunks - 1: chunk_end -= 0.1 
            
            srt_entries.append({
                "index": counter,
                "start": chunk_start,
                "end": chunk_end,
                "text": chunk
            })
            counter += 1

    with open(srt_path, 'w', encoding='utf-8') as f:
        for item in srt_entries:
            f.write(f"{item['index']}\n")
            f.write(f"{time_to_srt_format(item['start'])} --> {time_to_srt_format(item['end'])}\n")
            f.write(f"{item['text']}\n\n")

def generate_subtitled_video(video_path, transcript_data, use_original_lang=False):
    """
    Accepte un paramètre use_original_lang.
    """
    try:
        # Choix de la clé selon le paramètre
        key_to_use = 'text' if use_original_lang else 'text_translated'
        
        srt_path = video_path.replace(".mp4", ".srt")
        
        # On passe la clé à la fonction SRT
        generate_srt_file(transcript_data, srt_path, source_key=key_to_use)
        
        output_path = video_path.replace(".mp4", "_subtitled.mp4")
        srt_filename = os.path.basename(srt_path)
        video_dir = os.path.dirname(video_path)
        
        style = "Fontname=Arial,Fontsize=18,PrimaryColour=&H00FFFFFF,BackColour=&H60000000,BorderStyle=3,Outline=1,Shadow=0,MarginV=25,Alignment=2"
        
        command = [
            'ffmpeg', '-i', os.path.basename(video_path),
            '-vf', f"subtitles={srt_filename}:force_style='{style}'",
            '-c:a', 'copy', '-c:v', 'libx264', '-preset', 'ultrafast', '-y',
            os.path.basename(output_path)
        ]
        
        process = subprocess.run(command, cwd=video_dir, capture_output=True, text=True)
        if process.returncode != 0:
            st.error(f"Erreur FFMPEG : {process.stderr}")
            return None
        if os.path.exists(srt_path): os.remove(srt_path)
        return os.path.join(video_dir, os.path.basename(output_path))

    except Exception as e:
        st.error(f"Erreur incrustation : {e}")
        return None