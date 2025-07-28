# 01 데이터 전처리 + 태그 기반 텍스트 구성
import pandas as pd
import re
import os

def clean_text(text):
    if pd.isna(text):
        return ""
    text = re.sub(r"[^\w\s가-힣.,]", " ", text)
    text = re.sub(r"[·ㆍ“”‘’■▶◀※★]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def main():
    # csv_path = "../data/manual_labeled_articles.csv"
    csv_path = "./emotionData/train_articles.csv"
    df = pd.read_csv(csv_path)

    df["keywords"] = df["keywords"].fillna("중립 기사")

    df["clean_keywords"] = df["keywords"].apply(clean_text)
    df["clean_title"] = df["title"].apply(clean_text)
    df["clean_summary"] = df["summary"].apply(clean_text)

    # ✅ 문자열 레이블을 숫자로 변환
    label_map = {"긍정": 0, "중립": 1, "부정": 2}
    df["label"] = df["label"].map(label_map)

    # 기본 텍스트 구성
    df_kw = df[["clean_keywords", "label"]].rename(columns={"clean_keywords": "text"})
    df_kw_title = pd.DataFrame({
        "text": df["clean_keywords"] + " " + df["clean_title"],
        "label": df["label"]
    })
    df_kw_summary = pd.DataFrame({
        "text": df["clean_keywords"] + " " + df["clean_summary"],
        "label": df["label"]
    })
    df_kw_all = pd.DataFrame({
        "text": df["clean_keywords"] + " " + df["clean_title"] + " " + df["clean_summary"],
        "label": df["label"]
    })

    # 태그 포함 텍스트 구성
    df["tagged_text"] = (
        "<keyword> " + df["clean_keywords"] + " </keyword> " +
        "<title> " + df["clean_title"] + " </title> " +
        "<summary> " + df["clean_summary"] + " </summary>"
    )
    df_tagged = df[["tagged_text", "label"]].rename(columns={"tagged_text": "text"})

    # 저장
    # os.makedirs("../data", exist_ok=True)
    # df_kw.to_csv("../data/preprocessed_keywords.csv", index=False)
    # df_kw_title.to_csv("../data/preprocessed_keywords_title.csv", index=False)
    # df_kw_summary.to_csv("../data/preprocessed_keywords_summary.csv", index=False)
    # df_kw_all.to_csv("../data/preprocessed_keywords_all.csv", index=False)
    df_tagged.to_csv("./emotionData/train_tagged.csv", index=False)

    print("💾 저장 완료:")
    # print("- ../data/preprocessed_keywords.csv")
    # print("- ../data/preprocessed_keywords_title.csv")
    # print("- ../data/preprocessed_keywords_summary.csv")
    # print("- ../data/preprocessed_keywords_all.csv")
    print("- ./emotionData/train_tagged.csv")

if __name__ == "__main__":
    main()
