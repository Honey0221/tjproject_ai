import os
import json
import pickle
import numpy as np
import pandas as pd
import torch
import evaluate
import matplotlib.pyplot as plt
from datasets import Dataset, DatasetDict
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    Trainer,
    TrainingArguments,
    pipeline,
    DataCollatorWithPadding
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    ConfusionMatrixDisplay
)

import matplotlib.pyplot as plt

# 📌 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'  # Windows
# plt.rcParams['font.family'] = 'AppleGothic'  # macOS
# plt.rcParams['font.family'] = 'NanumGothic'  # Ubuntu 등

# 📌 마이너스 깨짐 방지
plt.rcParams['axes.unicode_minus'] = False


# ✅ 모델 및 토크나이저 설정
model_name = "beomi/kcbert-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)

def tokenizer_function(examples):
    return tokenizer(examples["text"], truncation=True, padding=True)

def compute_metrics(eval_pred):
    accuracy_metric = evaluate.load("accuracy")
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=1)
    return accuracy_metric.compute(predictions=predictions, references=labels)

if __name__ == "__main__":
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"현재 사용 중인 장치: {device}")

    # ✅ 데이터 로드
    try:
        with open("./emotionData/train_tagged_embedd.pkl", "rb") as f:
            data = pickle.load(f)
        print(f"데이터 로드 성공: {len(data)}개의 샘플")
    except FileNotFoundError:
        print("에러: './emotionData/train_tagged_embedd.pkl' 파일을 찾을 수 없습니다.")
        exit()

    if data['label'].isnull().any():
        print("경고: 라벨 매핑 과정에서 처리되지 않은 라벨(NaN)이 있습니다.")
        data.dropna(subset=['label'], inplace=True)
        print(f"NaN 라벨 제거 후 데이터 크기: {len(data)}")

    # ✅ train/test 분할
    train_df, test_df = train_test_split(
        data,
        test_size=0.2,
        stratify=data['label'],
        random_state=42
    )

    raw_datasets = DatasetDict({
        "train": Dataset.from_pandas(train_df, preserve_index=False),
        "test": Dataset.from_pandas(test_df, preserve_index=False)
    })

    tokenized_datasets = raw_datasets.map(tokenizer_function, batched=True)
    tokenized_datasets.set_format("torch", columns=["input_ids", "attention_mask", "label"])
    tokenized_train_data = tokenized_datasets["train"]
    tokenized_test_data = tokenized_datasets["test"]

    # ✅ 모델 초기화
    num_labels = len(np.unique(data['label']))
    model = AutoModelForSequenceClassification.from_pretrained(model_name, num_labels=num_labels)
    model.to(device)

    # ✅ 학습 설정
    training_args = TrainingArguments(
        output_dir="../results",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=64,
        warmup_steps=500,
        weight_decay=0.01,
        logging_dir="../logs",
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="accuracy",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_train_data,
        eval_dataset=tokenized_test_data,
        compute_metrics=compute_metrics,
        data_collator=DataCollatorWithPadding(tokenizer)
    )

    # ✅ 모델 훈련
    print("\n모델 훈련 시작...")
    trainer.train()
    print("훈련 완료!")

    # ✅ 평가 및 예측
    predictions = trainer.predict(tokenized_test_data)
    y_pred = np.argmax(predictions.predictions, axis=1)
    y_true = predictions.label_ids
    acc = accuracy_score(y_true, y_pred)
    print(f"\n📊 테스트 정확도: {acc:.4f}")

    # ✅ Confusion Matrix
    label_map = {0: "긍정", 1: "중립", 2: "부정"}
    display_labels = [label_map[i] for i in sorted(label_map.keys())]

    plt.figure(figsize=(6, 5))
    ConfusionMatrixDisplay.from_predictions(y_true, y_pred, display_labels=display_labels, cmap="Blues")
    plt.title("BERT 감정 분류 Confusion Matrix")
    plt.tight_layout()
    plt.savefig("kcbert_confusion_matrix.png")
    plt.show()
    print("✅ Confusion matrix 저장: kcbert_confusion_matrix.png")

    # ✅ Classification Report
    print("\n📋 classification_report:")
    print(classification_report(y_true, y_pred, target_names=display_labels, digits=4))

    # ✅ 에폭별 Loss / Accuracy 시각화
    log_path = os.path.join(training_args.output_dir, "trainer_state.json")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            trainer_state = json.load(f)

        log_history = trainer_state.get("log_history", [])
        train_loss = [log["loss"] for log in log_history if "loss" in log]
        eval_acc = [log["eval_accuracy"] for log in log_history if "eval_accuracy" in log]

        plt.figure(figsize=(12, 5))
        plt.subplot(1, 2, 1)
        plt.plot(range(1, len(train_loss) + 1), train_loss, marker='o')
        plt.title("Training Loss")
        plt.xlabel("Step")
        plt.ylabel("Loss")

        plt.subplot(1, 2, 2)
        plt.plot(range(1, len(eval_acc) + 1), eval_acc, marker='o', color='green')
        plt.title("Evaluation Accuracy (per Epoch)")
        plt.xlabel("Epoch")
        plt.ylabel("Accuracy")
        plt.ylim(0, 1)

        plt.tight_layout()
        plt.savefig("kcbert_training_metrics.png")
        plt.show()
        print("📊 kcbert_training_metrics.png 저장 완료")
    else:
        print("⚠️ trainer_state.json 파일이 없어 그래프를 생성할 수 없습니다.")

    # ✅ 모델 저장
    save_directory = "./emotionKcbertModels"
    trainer.save_model(save_directory)
    tokenizer.save_pretrained(save_directory, safe_serialization=True)
    print(f"🧠 훈련된 모델과 토크나이저가 '{save_directory}'에 저장되었습니다.")



