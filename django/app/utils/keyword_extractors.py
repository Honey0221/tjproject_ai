from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
from krwordrank.word import KRWordRank
from konlpy.tag import Okt
from gensim import corpora, models
from collections import Counter
from keybert import KeyBERT
from difflib import SequenceMatcher
import numpy as np
import re

from app.utils.stopwords import DEFAULT_STOPWORDS, STOPWORD_PREFIXES

okt = Okt()
kw_model = KeyBERT("sentence-transformers/xlm-r-100langs-bert-base-nli-mean-tokens")
embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# ✅ 후처리 함수: 조사/접두사 제거 + 명사만 추출
def clean_keywords(keywords):
    cleaned = []
    for word in keywords:
        if re.fullmatch(r'[a-zA-Z]+', word):
            continue
        for prefix in STOPWORD_PREFIXES:
            if word.startswith(prefix) and len(word) > len(prefix):
                word = word[len(prefix):]
                break
        morphs = okt.pos(word, norm=True, stem=True)
        nouns = [w for w, t in morphs if t == 'Noun' and w not in DEFAULT_STOPWORDS]
        filtered = [n for n in nouns if len(n) > 1]
        if filtered:
            cleaned.extend(filtered)  # ✅ 붙이지 않고 각각 추가
    return list(set(cleaned))

# ✅ 실제 빈도수 카운트 함수 (요약 내 등장 여부 + 유사도 보정)
def count_frequencies(keywords, summary, content=None):
    """
    ✅ 키워드 등장 횟수 계산 (요약 + 본문 포함)
    - 정확 매칭 + 유사도 보정
    - 디버깅 로그 출력 포함
    """
    # ✅ count 기준 텍스트 결정: summary + content
    base_text = summary
    if content:
        base_text += " " + content

    # 형태소 기반 토큰화
    tokens = okt.nouns(base_text)
    tokens = [t for t in tokens if len(t) > 1]
    freq = Counter(tokens)

    result = []
    print(f"\n📄 기사 요약 요약 (앞 60자): {summary[:60]}")
    print(f"📄 본문 존재 여부: {'있음' if content else '없음'}")
    print(f"🔍 대상 키워드 수: {len(keywords)}")

    for kw in keywords:
        count = base_text.count(kw)  # 정확 일치

        # ✅ 유사도 기반 fallback
        if count == 0:
            for token in tokens:
                sim = SequenceMatcher(None, kw, token).ratio()
                if sim > 0.85:
                    count = 1
                    break

        print(f"   ➤ '{kw}': {count}회 등장")
        if count > 0:
            result.append((kw, count))

    return result


# ✅ 유사 키워드 클러스터링 + 통합
def cluster_keywords(keywords, threshold=0.85):
    if len(keywords) <= 1:
        return {kw: kw for kw in keywords}
    embeddings = embedding_model.encode(keywords)
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1 - threshold,
        affinity="cosine",
        linkage="average"
    )
    clustering.fit(embeddings)
    label_to_keywords = {}
    for i, label in enumerate(clustering.labels_):
        label_to_keywords.setdefault(label, []).append(keywords[i])
    cluster_map = {}
    for label, kw_list in label_to_keywords.items():
        representative = sorted(kw_list, key=lambda x: (len(x), x))[0]
        for kw in kw_list:
            cluster_map[kw] = representative
    return cluster_map

def merge_similar_keywords(freq_keywords, threshold=0.85):
    keywords = [kw for kw, _ in freq_keywords]
    cluster_map = cluster_keywords(keywords, threshold)
    merged_counter = Counter()
    for kw, cnt in freq_keywords:
        merged_counter[cluster_map.get(kw, kw)] += cnt
    return sorted(merged_counter.items(), key=lambda x: x[1], reverse=True)

# ✅ KeyBERT
def extract_with_keybert(text, top_n=10, return_counts=False):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words=None, top_n=top_n * 2)
    raw_keywords = [(kw[0], kw[1]) for kw in keywords]
    cleaned = []
    for word, _ in raw_keywords:
        words = clean_keywords([word])
        cleaned.extend(words)
    freq_keywords = count_frequencies(set(cleaned), text)
    freq_keywords = merge_similar_keywords(freq_keywords)
    freq_keywords = sorted(freq_keywords, key=lambda x: x[1], reverse=True)[:top_n]
    return freq_keywords if return_counts else [kw for kw, _ in freq_keywords]

# ✅ TF-IDF
def extract_with_tfidf(texts, stopwords, top_n=10, return_counts=False):
    vectorizer = TfidfVectorizer(stop_words=stopwords)
    X = vectorizer.fit_transform(texts)
    vocab = vectorizer.get_feature_names_out()
    words = ' '.join(texts)
    cleaned = clean_keywords(vocab)
    freq_keywords = count_frequencies(set(cleaned), words)
    freq_keywords = merge_similar_keywords(freq_keywords)
    freq_keywords = sorted(freq_keywords, key=lambda x: x[1], reverse=True)[:top_n]
    return freq_keywords if return_counts else [kw for kw, _ in freq_keywords]

# ✅ KRWordRank
def extract_with_krwordrank(text, stopwords, top_n=10, return_counts=False):
    extractor = KRWordRank(min_count=2, max_length=10, verbose=False)
    keywords, _, _ = extractor.extract([text], beta=0.85, max_iter=10)
    raw_keywords = [kw for kw in keywords.keys() if kw not in stopwords]
    cleaned = clean_keywords(raw_keywords)
    freq_keywords = count_frequencies(set(cleaned), text)
    freq_keywords = merge_similar_keywords(freq_keywords)
    freq_keywords = sorted(freq_keywords, key=lambda x: x[1], reverse=True)[:top_n]
    return freq_keywords if return_counts else [kw for kw, _ in freq_keywords]

# ✅ Okt + 빈도 기반
def extract_with_okt(texts, stopwords, top_n=10, return_counts=False):
    words = []
    for text in texts:
        nouns = okt.nouns(text)
        words.extend([n for n in nouns if n not in stopwords and len(n) > 1])
    count = Counter(words)
    most_common = count.most_common(top_n * 2)
    freq_keywords = merge_similar_keywords(most_common)
    freq_keywords = sorted(freq_keywords, key=lambda x: x[1], reverse=True)[:top_n]
    return freq_keywords if return_counts else [kw for kw, _ in freq_keywords]

# ✅ LDA (기사 합침 기반 전체 추출)
def extract_with_lda(texts, stopwords, top_n=10, return_counts=False):
    tokenized = [
        [word for word in text.split() if word not in stopwords and not re.fullmatch(r'[a-zA-Z]+', word)]
        for text in texts if text.strip()
    ]
    dictionary = corpora.Dictionary(tokenized)
    corpus = [dictionary.doc2bow(text) for text in tokenized]
    lda_model = models.LdaModel(corpus, num_topics=1, id2word=dictionary, passes=10)
    topics = lda_model.show_topic(0, topn=top_n * 2)
    words = [word for word, _ in topics]
    cleaned = clean_keywords(words)
    merged_text = ' '.join(texts)
    freq_keywords = count_frequencies(set(cleaned), merged_text)
    freq_keywords = merge_similar_keywords(freq_keywords)
    freq_keywords = sorted(freq_keywords, key=lambda x: x[1], reverse=True)[:top_n]
    return freq_keywords if return_counts else [kw for kw, _ in freq_keywords]

# ✅ 기사별 키워드 누적 방식 전체 키워드 생성
def aggregate_keywords_from_articles(individual_results, top_n=10):
    keyword_counter = Counter()
    for article in individual_results:
        for kw in article["keywords"]:
            keyword_counter[kw["keyword"]] += kw["count"]
    total_keyword_sum = sum(keyword_counter.values())
    formatted_overall = [
        {
            "keyword": kw,
            "count": count,
            "ratio": round(count / total_keyword_sum * 100, 1) if total_keyword_sum else 0
        }
        for kw, count in keyword_counter.most_common(top_n)
    ]
    return formatted_overall
