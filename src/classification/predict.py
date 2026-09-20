import os
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# Variables globales pour le chargement paresseux du classificateur
_classifier_model = None
_classifier_tokenizer = None
_model_path = "models/classification/"

def get_classifier():
    """
    Charge de manière paresseuse le modèle affiné et le tokenizer depuis le dossier models/classification/.
    Gère la recherche du chemin relatif et absolu.
    """
    global _classifier_model, _classifier_tokenizer
    if _classifier_model is None:
        actual_path = _model_path
        if not os.path.exists(actual_path):
            # Tenter de trouver le chemin depuis la racine du projet
            possible_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../", _model_path))
            if os.path.exists(possible_path):
                actual_path = possible_path
            else:
                raise FileNotFoundError(
                    f"Le modèle de classification affiné n'a pas été trouvé à {actual_path} ni à {possible_path}. "
                    "Veuillez d'abord exécuter train_classifier.py pour générer et sauvegarder le modèle."
                )
                
        # Chargement
        try:
            _classifier_tokenizer = AutoTokenizer.from_pretrained(actual_path)
            _classifier_model = AutoModelForSequenceClassification.from_pretrained(actual_path)
        except Exception as e:
            # Si les poids affinés ne sont pas présents localement (ex: archive ZIP sans .safetensors),
            # charger xlm-roberta-base avec la configuration des labels
            import logging
            logging.getLogger("classification.predict").warning(
                f"Poids affinés introuvables dans {actual_path} ({e}). "
                "Chargement du modèle de base 'xlm-roberta-base' avec la cartographie des directions."
            )
            base_model_name = os.environ.get("BASE_MODEL_NAME", "xlm-roberta-base")
            _classifier_tokenizer = AutoTokenizer.from_pretrained(base_model_name)
            _classifier_model = AutoModelForSequenceClassification.from_pretrained(
                base_model_name,
                num_labels=8,
                id2label={
                    0: "DSI", 1: "DSPCT", 2: "DAAJJ", 3: "DMM",
                    4: "DTR", 5: "DJAC", 6: "Cabinet du Ministère", 7: "Non concerné"
                },
                label2id={
                    "DSI": 0, "DSPCT": 1, "DAAJJ": 2, "DMM": 3,
                    "DTR": 4, "DJAC": 5, "Cabinet du Ministère": 6, "Non concerné": 7
                }
            )

        _classifier_model.eval()
        
    return _classifier_model, _classifier_tokenizer


def predire_direction(texte: str, seuil_confiance: float = 0.6) -> dict:
    """
    Prédit la direction/entité responsable d'une demande citoyenne.
    
    Arguments :
    - texte : La demande citoyenne (str).
    - seuil_confiance : Seuil sous lequel la confiance est qualifiée de faible (float, défaut 0.6).
    
    Retourne un dictionnaire :
    {
        "direction_predite": str,
        "score_confiance": float,
        "indicateur_confiance_faible": bool
    }
    """
    if not texte or not isinstance(texte, str):
        return {
            "direction_predite": "Non concerné",
            "score_confiance": 0.0,
            "indicateur_confiance_faible": True
        }
        
    # 1. Prétraiter le texte d'entrée en utilisant le clean_text du preprocessing
    try:
        from preprocessing.clean_text import clean_text
        texte_nettoye = clean_text(texte)["texte_nettoye"]
    except Exception:
        # Repli si l'import ou la fonction échoue
        texte_nettoye = texte
        
    # 2. Charger le modèle et le tokenizer
    model, tokenizer = get_classifier()
    
    # 3. Tokeniser le texte d'entrée
    inputs = tokenizer(
        texte_nettoye,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=128
    )
    
    # 4. Inférence (sans calcul de gradient)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probabilities = F.softmax(logits, dim=1)
        
    # 5. Extraction de la classe et du score
    pred_idx = torch.argmax(probabilities, dim=1).item()
    score_confiance = probabilities[0][pred_idx].item()
    
    direction_predite = model.config.id2label.get(pred_idx, "Non concerné")
    indicateur_confiance_faible = score_confiance < seuil_confiance
    
    return {
        "direction_predite": direction_predite,
        "score_confiance": float(score_confiance),
        "indicateur_confiance_faible": indicateur_confiance_faible
    }
