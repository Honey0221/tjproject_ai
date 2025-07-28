import os
import joblib
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import (
    classification_report, accuracy_score, confusion_matrix, roc_curve,
    auc
)
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, VotingClassifier, StackingClassifier
from sklearn.svm import SVC
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from lightgbm import early_stopping as LGB_EarlyStopping
import matplotlib as mpl

# 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
mpl.rcParams['axes.unicode_minus'] = False

# ---------------------- 데이터 로딩 함수 ----------------------
def load_data(pkl_path):
    return joblib.load(pkl_path)  # ✅ joblib 사용

# ---------------------- 모델 평가 함수 ----------------------
def evaluate_model(model, X_test, y_test, model_name="Model"):
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\n📊 {model_name} 정확도: {acc:.4f}")
    print(classification_report(y_test, y_pred, target_names=["긍정", "중립", "부정"]))

    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(5, 4))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=["긍정", "중립", "부정"],
                yticklabels=["긍정", "중립", "부정"])
    plt.title(f"{model_name} Confusion Matrix")
    plt.xlabel("예측값")
    plt.ylabel("실제값")
    plt.tight_layout()
    plt.show()

    if hasattr(model, "predict_proba"):
        y_score = model.predict_proba(X_test)
        fpr, tpr, roc_auc = {}, {}, {}
        for i in range(3):
            fpr[i], tpr[i], _ = roc_curve(y_test == i, y_score[:, i])
            roc_auc[i] = auc(fpr[i], tpr[i])
        plt.figure(figsize=(6, 5))
        for i, label in enumerate(["긍정", "중립", "부정"]):
            plt.plot(fpr[i], tpr[i], label=f"{label} (AUC = {roc_auc[i]:.2f})")
        plt.plot([0, 1], [0, 1], "k--")
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title(f"{model_name} ROC Curve")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    return acc

# ---------------------- 메인 실행 ----------------------
def main():
    DATA_PATH = "./emotionData/train_tagged_embedd.pkl"
    SAVE_DIR = "baseEnsembleModels"
    os.makedirs(SAVE_DIR, exist_ok=True)

    df = load_data(DATA_PATH)
    df['label'] = df['label'].astype(int)
    X = np.array(df['embedding'].tolist())
    y = df['label'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    models = {
        "LogisticRegression": LogisticRegression(max_iter=1000, C=0.5, penalty='l2'),
        "RandomForest": RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=5, random_state=42),
        "SVM": SVC(kernel="linear", probability=True, C=0.5),
        "XGBoost": XGBClassifier(eval_metric="mlogloss", random_state=42, max_depth=6, learning_rate=0.1, use_label_encoder=False),
        "LightGBM": LGBMClassifier(random_state=42, max_depth=10, learning_rate=0.05, num_leaves=31, min_child_samples=10, n_estimators=200)
    }

    results = {}

    for name, model in models.items():
        print(f"\n🚀 모델 학습 시작: {name}")

        if name == "LightGBM":
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                eval_metric="multi_logloss",
                callbacks=[LGB_EarlyStopping(stopping_rounds=10)]
            )
        elif name == "XGBoost":
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                early_stopping_rounds=10,
                verbose=False
            )
        else:
            model.fit(X_train, y_train)

        acc = evaluate_model(model, X_test, y_test, name)

        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(model, X, y, cv=skf, scoring="accuracy")
        print(f"✅ {name} 교차 검증 평균 정확도: {cv_scores.mean():.4f}")

        model_path = os.path.join(SAVE_DIR, f"{name}.joblib")  # ✅ 확장자 변경
        joblib.dump(model, model_path)
        print(f"✅ {name} 모델 저장 완료")

        results[name] = acc

    # 앙상블 모델: Voting
    voting = VotingClassifier(estimators=[
        ("lr", LogisticRegression(max_iter=1000, C=0.5, penalty='l2')),
        ("rf", RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=5, random_state=42)),
        ("svc", SVC(kernel="linear", probability=True, C=0.5)),
        ("xgb", XGBClassifier(
            objective='multi:softprob',
            eval_metric="mlogloss",
            use_label_encoder=False,
            random_state=42,
            max_depth=6,
            learning_rate=0.1,
            n_estimators=100
        )),
        ("lgb", LGBMClassifier(random_state=42, max_depth=10, learning_rate=0.05,
                               num_leaves=31, min_child_samples=10, n_estimators=200))
    ], voting="soft")

    voting.fit(X_train, y_train)
    acc = evaluate_model(voting, X_test, y_test, "Voting Ensemble")
    results["VotingEnsemble"] = acc
    joblib.dump(voting, os.path.join(SAVE_DIR, "vote.joblib"))
    print("✅ VotingEnsemble 모델 저장 완료")

    # 앙상블 모델: Stacking
    stacking = StackingClassifier(
        estimators=[
            ("lr", LogisticRegression(max_iter=1000, C=0.5, penalty='l2')),
            ("rf", RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_leaf=5, random_state=42)),
            ("svc", SVC(kernel="linear", probability=True, C=0.5)),
            ("xgb", XGBClassifier(eval_metric="mlogloss", random_state=42, max_depth=6, learning_rate=0.1,
                                  use_label_encoder=False)),
            ("lgb",
             LGBMClassifier(random_state=42, max_depth=10, learning_rate=0.05, num_leaves=31, min_child_samples=10,
                            n_estimators=200))
        ],
        final_estimator=LogisticRegression(),
        cv=5
    )
    stacking.fit(X_train, y_train)
    acc = evaluate_model(stacking, X_test, y_test, "Stacking Ensemble")
    results["StackingEnsemble"] = acc
    joblib.dump(stacking, os.path.join(SAVE_DIR, "stack.joblib"))
    print("✅ StackingEnsemble 모델 저장 완료")

    # 시각화
    plt.figure(figsize=(10, 6))
    sns.barplot(x=list(results.keys()), y=list(results.values()))
    plt.ylabel("Accuracy")
    plt.title("모델별 감정 분류 정확도 비교")
    plt.xticks(rotation=45)
    plt.ylim(0.6, 1.0)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()
