# Universal Video Analyzer & Subtitler

Outil d'automatisation basé sur Streamlit pour le sous-titrage, la traduction et l'identification de locuteurs (diarisation) sur des vidéos YouTube.

Le pipeline combine plusieurs modèles pour produire une vidéo finale avec sous-titres incrustés (hardsub) :
* **Pyannote AI** : Diarisation et identification biométrique des voix (via API).
* **OpenAI Whisper** : Transcription speech-to-text (modèle local).
* **Google Translate** : Traduction multilingue.
* **FFmpeg** : Traitement vidéo, segmentation et incrustation des sous-titres.

---

## Prérequis

L'application nécessite impérativement les éléments suivants pour fonctionner :

1.  **FFmpeg** : Doit être installé et accessible via le PATH système. Il est utilisé pour l'extraction audio et le rendu vidéo final.
    * *Windows/Mac/Linux* : [Site officiel FFmpeg](https://ffmpeg.org/download.html).
2.  **Clé API Pyannote** : Requise pour l'accès aux modèles de diarisation et d'empreinte vocale (disponible sur [console.pyannote.ai](https://console.pyannote.ai)).

---

## Installation

```bash

# Installer les dépendances (environnement virtuel recommandé)
pip install -r requirements.txt

# Lancer l'interface
streamlit run app.py
```

## Structure du projet

* `app.py` : L'interface principale (Streamlit) et l'orchestration.
* `diarization.py` : Gestion de l'API Pyannote (Upload & Identification).
* `voiceprint.py` : Extraction des empreintes vocales pour la base de données.
* `transcript.py` : Transcription audio via le modèle Whisper (local).
* `translate.py` : Traduction du texte via deep-translator.
* `final_video.py` : Montage vidéo et incrustation des sous-titres via FFMPEG.
* `voice_database.json` : Base de données locale contenant les signatures vocales.

---