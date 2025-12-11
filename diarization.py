import requests
import uuid
import time
import os
import json

def upload_to_pyannote(api_key, file_path):
    """(Inchangé) Envoie le fichier audio vers les serveurs de Pyannote."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    safe_media_key = str(uuid.uuid4())
    ext = os.path.splitext(file_path)[1]
    if not ext: ext = ".wav"
    media_name = f"media://{safe_media_key}{ext}"
    
    # 1. Demande d'URL d'upload
    res_url = None
    try:
        res_url = requests.post("https://api.pyannote.ai/v1/media/input", headers=headers, json={"url": media_name})
    except Exception as e:
        return None, f"Erreur connexion: {str(e)}"

    if not res_url or res_url.status_code not in [200, 201]:
        return None, f"Erreur API Upload: {res_url.text if res_url else 'No response'}"
    
    upload_url = res_url.json()["url"]
    
    # 2. Upload binaire
    try:
        with open(file_path, 'rb') as f:
            res_upload = requests.put(upload_url, data=f)
    except Exception as e:
        return None, f"Erreur envoi fichier: {str(e)}"

    if res_upload.status_code not in [200, 201]: 
        return None, f"Echec upload S3: {res_upload.text}"
        
    return media_name, None

def start_identification_job(api_key, media_name, voice_db):
    """
    Lance le job d'IDENTIFICATION.
    Correction : Utilise 'label' et 'voiceprint' au lieu de 'id' et 'embedding'.
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # 1. Transformation de la base de données au format attendu par l'API
    voiceprints_list = []
    
    for speaker_name, data in voice_db.items():
        # On vérifie si on a bien un embedding
        raw_embedding = data.get("embedding")
        
        if raw_embedding:
            # L'API refuse les labels commençant par "SPEAKER_"
            # On nettoie le nom au cas où
            clean_label = speaker_name.replace("SPEAKER_", "Person_")
            
            voiceprints_list.append({
                "label": clean_label,      # REMPLACÉ: 'id' -> 'label'
                "voiceprint": raw_embedding # REMPLACÉ: 'embedding' -> 'voiceprint'
            })
            
    if not voiceprints_list:
        return None, "Aucune empreinte vocale valide trouvée."

    # 2. Construction de la payload
    payload = {
        "url": media_name,
        "voiceprints": voiceprints_list,
        "matching": {
            "threshold": 0.999 
        }
    }
    
    # Debug : Afficher ce qu'on envoie (utile pour vérifier dans la console Streamlit)
    print(f"Envoi de {len(voiceprints_list)} voiceprints à l'API.")
    
    try:
        res = requests.post("https://api.pyannote.ai/v1/identify", headers=headers, json=payload)
    except Exception as e:
        return None, f"Erreur connexion Job Start: {str(e)}"

    if res.status_code != 200:
        # On renvoie le texte complet de l'erreur pour le debug
        return None, f"Erreur Lancement Identify ({res.status_code}): {res.text}"
        
    return res.json()['jobId'], None

def start_diarization_job(api_key, media_name):
    """
    Lance une DIARIZATION simple (Qui parle quand ?).
    Ne nomme pas les gens, donne juste SPEAKER_00, SPEAKER_01...
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    
    # Endpoint différent : /v1/diarize
    try:
        res = requests.post("https://api.pyannote.ai/v1/diarize", headers=headers, json={"url": media_name})
    except Exception as e:
        return None, f"Erreur connexion Job Start: {str(e)}"

    if res.status_code != 200:
        return None, f"Erreur Lancement Diarize ({res.status_code}): {res.text}"
        
    return res.json()['jobId'], None

def wait_for_result(api_key, job_id, progress_callback=None):
    """Polling du résultat (Identification ou Diarisation)."""
    headers = {"Authorization": f"Bearer {api_key}"}
    
    while True:
        try:
            res = requests.get(f"https://api.pyannote.ai/v1/jobs/{job_id}", headers=headers)
        except requests.exceptions.ConnectionError:
            time.sleep(1)
            continue
            
        if res.status_code != 200: 
            return {"error": f"Erreur Job Status: {res.text}"}
            
        job_info = res.json()
        status = job_info['status']
        
        if status == 'succeeded':
            if progress_callback: progress_callback(100)
            
            output = job_info['output']
            
            # Gestion spécifique du retour de l'identification
            if 'identification' in output:
                # Format: une liste de segments avec un champ 'match' (si identifié) ou non
                # Exemple : [{"start": 0, "end": 2, "match": "Novak", "confidence": 0.9}, ...]
                return {"status": "success", "segments": output['identification'], "type": "identification"}
            
            elif 'diarization' in output:
                return {"status": "success", "segments": output['diarization'], "type": "diarization"}
            else:
                return {"status": "success", "raw": output} 
                
        elif status == 'failed': 
            return {"error": "Le job Pyannote a échoué."}
        
        if progress_callback: progress_callback(50)
        time.sleep(2)