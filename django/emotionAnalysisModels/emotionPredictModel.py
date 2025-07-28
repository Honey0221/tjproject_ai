import os
import joblib
import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSequenceClassification


# ✅ BERT 예측 함수
def predict_with_bert(texts, tokenizer, model, device):
    label_map = {0: "긍정", 1: "중립", 2: "부정"}
    encoded_inputs = tokenizer(texts, padding=True, truncation=True, return_tensors="pt").to(device)

    with torch.no_grad():
        outputs = model(**encoded_inputs)
        probs = torch.softmax(outputs.logits, dim=-1)
        preds = torch.argmax(probs, dim=-1).cpu().numpy()
        probs = probs.cpu().numpy()

    labels = [label_map[p] for p in preds]
    return labels, probs


# ✅ ML 모델 예측 함수 (joblib로 로드)
def predict_sentiment(model_path, sample_embeddings):
    model = joblib.load(model_path)

    label_map = {0: "긍정", 1: "중립", 2: "부정"}
    predictions = model.predict(sample_embeddings)

    if hasattr(model, "predict_proba"):
        probas = model.predict_proba(sample_embeddings)
    else:
        probas = None

    labels = [label_map[p] for p in predictions]
    return labels, probas


# ✅ 실시간 예측 실행
def main():
    SAVE_DIR = "./baseEnsembleModels"
    JSON_PATH = "../etc/newsData/2025_skt_article.json"

    # 1. JSON 불러오기
    try:
        df = pd.read_json(JSON_PATH)
    except Exception as e:
        print(f"❌ JSON 로드 오류: {e}")
        return

    # 2. 텍스트 결합
    df["combined_text"] = (
        "<title> " + df["title"].fillna("") + " </title> " +
        "<summary> " + df["summary"].fillna("") + " </summary>"
    )

    # 3. 문장 임베딩 (ML 모델용)
    embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")
    embeddings = embedding_model.encode(df["combined_text"].tolist(), show_progress_bar=True)

    # 4. BERT 모델 로딩
    bert_model_dir = "./emotionKcbertModels"
    bert_tokenizer = AutoTokenizer.from_pretrained(bert_model_dir)
    bert_model = AutoModelForSequenceClassification.from_pretrained(bert_model_dir)
    bert_model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bert_model.to(device)

    results_df = []

    # 5. 예측 모델 리스트
    model_list = [
        "LogisticRegression",
        "RandomForest",
        "SVM",
        "XGBoost",
        "LightGBM",
        "VotingEnsemble",
        "StackingEnsemble",
        "kcBERT" # 강사님추천
    ]

    for model_name in model_list:
        if model_name == "kcBERT":
            labels, probas = predict_with_bert(df["combined_text"].tolist(), bert_tokenizer, bert_model, device)
        else:
            model_path = os.path.join(SAVE_DIR, f"{model_name}.joblib")  # ✅ 확장자 변경
            if not os.path.exists(model_path):
                print(f"⚠️ {model_name} 모델이 존재하지 않습니다. 건너뜁니다.")
                continue
            labels, probas = predict_sentiment(model_path, embeddings)

        print(f"{model_name} → 예측 완료")

        for i, label in enumerate(labels):
            result = {
                "model": model_name,
                "title": df.loc[i, "title"],
                "summary": df.loc[i, "summary"],
                "predicted_label": label
            }
            if probas is not None:
                result.update({
                    "prob_긍정": probas[i][0],
                    "prob_중립": probas[i][1],
                    "prob_부정": probas[i][2],
                })
            results_df.append(result)

    # 6. 결과 저장
    df_result = pd.DataFrame(results_df)
    df_result.to_csv("article_predictions.csv", index=False, encoding="utf-8-sig")
    print("✅ article_predictions.csv 파일로 감정 예측 결과 저장 완료")


if __name__ == "__main__":
    main()
