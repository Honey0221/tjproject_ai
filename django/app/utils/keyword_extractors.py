from sklearn.feature_extraction.text import TfidfVectorizer
from krwordrank.word import KRWordRank
from konlpy.tag import Okt
from gensim import corpora, models
from collections import Counter
import numpy as np
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

# ❗️ 반드시 SentenceTransformer로 감싼 후 KeyBERT에 전달
kw_model = KeyBERT("sentence-transformers/xlm-r-100langs-bert-base-nli-mean-tokens")  # ✅ 안정적


def extract_with_keybert(text, top_n=10):
    keywords = kw_model.extract_keywords(text, keyphrase_ngram_range=(1, 2), stop_words=None, top_n=top_n)
    return [kw[0] for kw in keywords]

# ✅ TF-IDF 방식
def extract_with_tfidf(texts, stopwords, top_n=10):
    vectorizer = TfidfVectorizer(stop_words=stopwords)
    X = vectorizer.fit_transform(texts)
    scores = np.asarray(X.sum(axis=0)).flatten()
    vocab = vectorizer.get_feature_names_out()
    sorted_idx = scores.argsort()[::-1]
    return [vocab[i] for i in sorted_idx[:top_n]]

# ✅ KRWordRank 방식
def extract_with_krwordrank(text, stopwords, top_n=10):
    extractor = KRWordRank(min_count=5, max_length=10, verbose=False)
    keywords, _ = extractor.extract([text], beta=0.85, max_iter=10)
    filtered = [kw for kw in keywords if kw not in stopwords]
    return filtered[:top_n]

# ✅ Okt + 빈도수 방식
def extract_with_okt(texts, stopwords, top_n=10):
    okt = Okt()
    words = []
    for text in texts:
        nouns = okt.nouns(text)
        words.extend([n for n in nouns if n not in stopwords and len(n) > 1])
    count = Counter(words)
    return [word for word, _ in count.most_common(top_n)]

# ✅ LDA 방식
def extract_with_lda(texts, stopwords, top_n=10):
    tokenized = [
        [word for word in text.split() if word not in stopwords]
        for text in texts if text.strip()
    ]
    dictionary = corpora.Dictionary(tokenized)
    corpus = [dictionary.doc2bow(text) for text in tokenized]
    lda_model = models.LdaModel(corpus, num_topics=1, id2word=dictionary, passes=10)
    topics = lda_model.show_topic(0, topn=top_n)
    return [word for word, _ in topics]