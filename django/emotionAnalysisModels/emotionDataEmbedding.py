# 02

import os
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import torch
import hdbscan

from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
from sklearn.cluster import KMeans

# ---------------------------------------------------------------
# 설정: 데이터 파일 경로
# ---------------------------------------------------------------
DATA_DIR = "./emotionData"
# CSV_PATH = os.path.join(DATA_DIR, "preprocessed_keywords_all.csv")
# INPUT_PKL = os.path.join(DATA_DIR, "preprocessed_keywords_all.pkl")
# OUTPUT_PKL = os.path.join(DATA_DIR, "keywords_all_embedding.pkl")

CSV_PATH = os.path.join(DATA_DIR, "train_tagged.csv")
INPUT_PKL = os.path.join(DATA_DIR, "train_tagged_embedd.pkl")




# ---------------------------------------------------------------
# 사용 가능한 디바이스(GPU, MPS, CPU) 자동 탐지 함수
# ---------------------------------------------------------------
def detect_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    else:
        return torch.device("cpu")


# ---------------------------------------------------------------
# 피클 파일 로드 함수
# ---------------------------------------------------------------
def load_data(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ 파일을 찾을 수 없습니다: {path}")
    with open(path, "rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------
# 피클 파일 저장 함수
# ---------------------------------------------------------------
def save_pickle(data, path):
    with open(path, "wb") as f:
        pickle.dump(data, f)


# ---------------------------------------------------------------
# 텍스트 컬럼을 임베딩하는 함수
# ---------------------------------------------------------------
def embed_text_column(df, column="text", model_name='jhgan/ko-sroberta-multitask'):
    device = detect_device()
    print(f"✅ 임베딩에 사용되는 디바이스: {device}")

    model = SentenceTransformer(model_name, device=device)
    print(f"📌 '{column}' 컬럼 임베딩 중...")
    embeddings = model.encode(df[column], show_progress_bar=True)

    df["embedding"] = list(embeddings)
    return df



# ---------------------------------------------------------------
# LDA를 통해 차원 축소 수행
# ---------------------------------------------------------------
def reduce_dimensions_lda(df):
    if "embedding" not in df.columns:
        raise KeyError("❌ 'embedding' 컬럼이 없습니다. 먼저 임베딩을 수행하세요.")
    X = np.array(df["embedding"].tolist())
    y = df['label'].values
    lda = LDA(n_components=2)
    lda_result = lda.fit_transform(X, y)
    df['lda_1'] = lda_result[:, 0]
    df['lda_2'] = lda_result[:, 1]
    return df


# ---------------------------------------------------------------
# PCA를 통해 차원 축소 수행
# ---------------------------------------------------------------
def reduce_dimensions_pca(df):
    if "embedding" not in df.columns:
        raise KeyError("❌ 'embedding' 컬럼이 없습니다. 먼저 임베딩을 수행하세요.")
    X = np.array(df["embedding"].tolist())
    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(X)
    df['pca_1'] = pca_result[:, 0]
    df['pca_2'] = pca_result[:, 1]
    return df


# ---------------------------------------------------------------
# KMeans 클러스터링 수행
# ---------------------------------------------------------------
def kmeans_clustering(df, x_col, y_col, n_clusters=3):
    print(f" KMeans 클러스터링 수행 (k={n_clusters})")
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    df['kmeans_label'] = kmeans.fit_predict(df[[x_col, y_col]])
    return df


# ---------------------------------------------------------------
# HDBSCAN 클러스터링 수행
# ---------------------------------------------------------------
def hdbscan_clustering(df, x_col, y_col):
    print(" HDBSCAN 클러스터링 수행")
    clusterer = hdbscan.HDBSCAN(min_cluster_size=5)
    df['hdbscan_label'] = clusterer.fit_predict(df[[x_col, y_col]])
    return df


# ---------------------------------------------------------------
# 시각화 함수: 클러스터 결과 출력
# ---------------------------------------------------------------
def plot_clusters(df, x, y, label, title):
    plt.figure(figsize=(10, 7))
    sns.scatterplot(x=x, y=y, hue=label, data=df, palette='tab10', s=70, alpha=0.85)
    plt.title(title)
    plt.xlabel(x)
    plt.ylabel(y)
    plt.legend(title=label)
    plt.grid(True)
    plt.tight_layout()
    plt.show()


# ---------------------------------------------------------------
# 시각화 함수: 클러스터 결과를 서브플롯으로 출력
# ---------------------------------------------------------------
def plot_all_clusters(df):
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    sns.scatterplot(ax=axes[0], x="lda_1", y="lda_2", hue="kmeans_label",
                    data=df, palette="tab10", s=70, alpha=0.85)
    axes[0].set_title("KMeans Clustering with LDA")
    axes[0].set_xlabel("LDA 1")
    axes[0].set_ylabel("LDA 2")
    axes[0].legend(title="Cluster")
    axes[0].set_aspect('auto')  # ✅ 축 비율 자동 설정 추가

    sns.scatterplot(ax=axes[1], x="pca_1", y="pca_2", hue="kmeans_label",
                    data=df, palette="tab10", s=70, alpha=0.85)
    axes[1].set_title("KMeans Clustering with PCA")
    axes[1].set_xlabel("PCA 1")
    axes[1].set_ylabel("PCA 2")
    axes[1].legend(title="Cluster")
    axes[1].set_aspect('auto')  # (선택) 자동 비율 적용

    sns.scatterplot(ax=axes[2], x="pca_1", y="pca_2", hue="hdbscan_label",
                    data=df, palette="tab10", s=70, alpha=0.85)
    axes[2].set_title("HDBSCAN Clustering with PCA")
    axes[2].set_xlabel("PCA 1")
    axes[2].set_ylabel("PCA 2")
    axes[2].legend(title="Cluster")
    axes[2].set_aspect('auto')  # (선택)

    plt.tight_layout()
    plt.show()




# ---------------------------------------------------------------
# 메인 실행 구문
# ---------------------------------------------------------------
if __name__ == "__main__":

    # ✅ [처음 1회 실행용] CSV 파일에서 임베딩 후 피클 저장
    csv_df = pd.read_csv(CSV_PATH)
    print(f"📄 CSV 파일 로드 완료: {len(csv_df)}건")
    csv_df = embed_text_column(csv_df, column="text")
    save_pickle(csv_df, INPUT_PKL)
    print(f"✅ 임베딩 후 피클 저장 완료: {INPUT_PKL}")
    exit()

    try:
        df = load_data(INPUT_PKL)
        print(f"📂 데이터 로드 완료: {len(df)}건")
    except FileNotFoundError as e:
        print(str(e))
        exit()

    if "embedding" not in df.columns:
        print("❌ 'embedding' 컬럼이 없습니다. 위의 임베딩 코드 주석을 해제하고 다시 실행하세요.")
        exit()


    # 🔹 LDA 차원 축소 및 클러스터링
    df = reduce_dimensions_lda(df)
    df = kmeans_clustering(df, "lda_1", "lda_2", n_clusters=3)
    plot_clusters(df, "lda_1", "lda_2", "kmeans_label", "KMeans Clustering with LDA")

    # 🔹 PCA 차원 축소 및 클러스터링
    df = reduce_dimensions_pca(df)
    df = kmeans_clustering(df, "pca_1", "pca_2", n_clusters=3)
    plot_clusters(df, "pca_1", "pca_2", "kmeans_label", "KMeans Clustering with PCA")

    # 🔹 HDBSCAN 클러스터링 (PCA 기반)
    df = hdbscan_clustering(df, "pca_1", "pca_2")
    plot_clusters(df, "pca_1", "pca_2", "hdbscan_label", "HDBSCAN Clustering with PCA")

    # plot_all_clusters(df)
