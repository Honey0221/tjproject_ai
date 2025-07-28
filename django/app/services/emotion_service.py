import os
import joblib
import torch
from app.utils.emotion_model_loader import (
    MODEL_DIR, embedding_model, hf_tokenizer, hf_model, id2label
)


def analyze_emotion(text: str, model_key: str):
    """
    입력된 텍스트(text)에 대해 지정된 모델(model_key)을 사용하여 감정 분석 수행

    model_key:
        - "transformer": HuggingFace 기반 BERT 모델
        - "vote", "stack": 전통 ML 모델 (.joblib 로딩)

    반환:
    {
        "label": "긍정" | "중립" | "부정",
        "confidence": 0.XX
    }
    """

    if not text or not text.strip():
        raise ValueError("입력된 텍스트가 비어 있습니다.")

    if model_key not in ["transformer", "vote", "stack"]:
        raise ValueError(f"지원하지 않는 모델입니다: {model_key}")

    try:
        if model_key == "transformer":
            # ✅ HuggingFace transformer 기반 감정 분석
            inputs = hf_tokenizer(text, return_tensors="pt", truncation=True, padding=True)
            with torch.no_grad():
                outputs = hf_model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=1)
                conf, pred = torch.max(probs, dim=1)
            return {
                "label": id2label[pred.item()],
                "confidence": round(conf.item(), 4)
            }

        else:
            # ✅ 전통 ML 모델 사용
            model_path = os.path.join(MODEL_DIR, f"{model_key}.joblib")
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"모델 파일이 존재하지 않습니다: {model_path}")

            model = joblib.load(model_path)
            embedding = embedding_model.encode([text], show_progress_bar=False)
            prediction = model.predict(embedding)[0]
            confidence = model.predict_proba(embedding)[0].max()

            return {
                "label": id2label[prediction],
                "confidence": round(float(confidence), 4)
            }

    except Exception as e:
        raise RuntimeError(f"감정 분석 중 오류 발생: {str(e)}")
