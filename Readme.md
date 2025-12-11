# Youtube-Auto-Subtitler

**Une application IA complète pour l'analyse, la transcription et la traduction de vidéos YouTube.**

Ce projet est une interface **Streamlit** qui automatise le pipeline de traitement vidéo en utilisant plusieurs modèles d'Intelligence Artificielle de pointe. Il permet de passer d'une simple URL YouTube à une vidéo entièrement sous-titrée et traduite, avec identification des interlocuteurs.

## ✨ Fonctionnalités Principales

* **🎥 Téléchargement YouTube** : Extraction automatique de l'audio et de la vidéo depuis une URL.
* **🗣️ Identification Vocale (2 Modes)** :
    * **Mode Diarization** : Distingue les voix anonymement ("Intervenant 01", "Intervenant 02"...).
    * **Mode Identification** : Reconnait des personnes spécifiques (ex: "Federer", "Djokovic") grâce à une base de données d'empreintes vocales (Voiceprints).
* **📝 Transcription Haute Précision** : Utilise le modèle **OpenAI Whisper** pour convertir la parole en texte.
* **🌍 Traduction Automatique** : Traduit instantanément les sous-titres vers le Français, Anglais, Espagnol, Allemand ou Italien.
* **🎬 Génération de Vidéo** : Crée un fichier `.mp4` final avec les sous-titres incrustés (hardcoded), prêt à être partagé.
* **📊 Export de Données** : Téléchargement des transcriptions au format CSV.


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