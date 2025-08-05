from transformers import AutoTokenizer, AutoModelForSequenceClassification
from transformers.pipelines.text_classification import TextClassificationPipeline
import pandas as pd
import torch
import re
from collections import Counter

class ReviewSentimentAnalyzer:
  # 불용어 정의
  STOPWORDS = {'정말', '너무', '진짜', '그냥', '약간', '조금', '매우', '완전', 
    '아주', '거의', '항상', '때문', '생각', '느낌', '같다', '있다', '없다', '이다', 
    '되다', '하다', '그런', '이런', '저런', '그것', '이것', '저것', '회사', '기업', 
    '일', '때', '곳', '것', '정도', '부분', '좋다', '많다', '크다', '작다', '높다', 
    '낮다', '나쁘다', '어렵다', '쉽다', '힘들다', '편하다', '빠르다', '느리다', 
    '새롭다', '오래되다', '중요하다', '심하다', '좋아하다', '부족하다', '안좋다'
  }

  def __init__(self):
    # 감정분석에 특화된 모델 사용(KoELECTRA 기반 모델)
    model_name = "Copycats/koelectra-base-v3-generalized-sentiment-analysis"
    self.tokenizer = AutoTokenizer.from_pretrained(model_name)
    self.model = AutoModelForSequenceClassification.from_pretrained(model_name)

    self.pipeline = TextClassificationPipeline(
      model=self.model,
      tokenizer=self.tokenizer,
      return_all_scores=True,  # 모든 감정 확률을 리스트로 반환
      truncation=True, # 너무 긴 텍스트는 자동으로 자름
      top_k=None,
      device=0 if torch.cuda.is_available() else -1
    )

  def analyze_sentiment(self, text):
    """ 텍스트에서 긍정/부정 점수 반환 """
    result = self.pipeline(text)[0]
    scores = {res['label']: res['score'] for res in result}
    positive_score = scores.get('1')
    negative_score = scores.get('0')
    
    return positive_score, negative_score

  def compute_satisfaction_score(self, pos, neg):
    """ 감정 점수 기반 만족도 계산: 0~100 """
    return round(((pos - neg + 1) / 2) * 100, 2)

  def extract_keywords(self, texts, top_k=5):
    """KoNLPy를 사용한 의미있는 키워드 추출"""
    try:
      from konlpy.tag import Okt
      okt = Okt()
      
      # 모든 텍스트에서 의미있는 단어 추출
      meaningful_words = []
      for text in texts:
        # 명사와 형용사만 추출 (2글자 이상, 불용어 제외)
        words = okt.pos(text, stem=True)
        filtered_words = [
          word for word, pos in words 
          if pos in ['Noun', 'Adjective'] and len(word) >= 2 
            and word not in self.STOPWORDS
        ]
        meaningful_words.extend(filtered_words)
      
      word_counts = Counter(meaningful_words)
      return [word for word in word_counts.most_common(top_k)]
      
    except Exception as e:
      print(f"KoNLPy 키워드 추출 중 오류: {str(e)}")
      return self._extract_keywords_fallback(texts, top_k)

  def _extract_keywords_fallback(self, texts, top_k=5):
    """KoNLPy 사용 불가시 대체 키워드 추출"""
    # 모든 텍스트를 합치기
    combined_text = ' '.join(texts)
    
    # 한글 단어만 추출 (2글자 이상)
    korean_words = re.findall(r'[가-힣]{2,}', combined_text)
    
    # 불용어 제거 (클래스 변수 사용)
    filtered_words = [
      word for word in korean_words 
        if word not in self.STOPWORDS and len(word) >= 2
    ]
    
    # 빈도 계산
    word_counts = Counter(filtered_words)
    
    # 상위 키워드 반환
    return [word for word in word_counts.most_common(top_k)]

  def get_top_reviews_by_score(self, df, review_type, top_k=3):
    """특정 타입에서 점수가 높은 리뷰들과 점수를 함께 반환"""
    type_df = df[df['type'] == review_type]
    
    # 만족도 점수 기준 내림차순 정렬
    sorted_df = type_df.sort_values('satisfaction_score', ascending=False)
    
    # 상위 리뷰들과 점수를 함께 반환
    top_reviews_data = []
    for _, row in sorted_df.head(top_k).iterrows():
      top_reviews_data.append({
        'text': row['text'],
        'score': round(row['satisfaction_score'], 2)
      })
    
    return top_reviews_data

  def process_dataframe(self, df):
    """ 감정 분석 전체 적용 """
    results = []

    for idx, row in df.iterrows():
      text = row['text']
      review_type = row['type']

      # 리뷰별 감정 분석
      pos, neg = self.analyze_sentiment(text)

      # 감정 분석한 결과를 만족도 점수로 변환
      satisfaction = self.compute_satisfaction_score(pos, neg)

      results.append({
        'type': review_type,
        'text': text,
        'positive_score': pos,
        'negative_score': neg,
        'satisfaction_score': satisfaction
      })

    return pd.DataFrame(results)

  def analyze_reviews_with_keywords(self, df):
    """리뷰 분석 + 키워드 추출 + 상위 리뷰 샘플"""
    # 기본 감정 분석
    scored_df = self.process_dataframe(df)
    
    # 장점 데이터 분석
    pros_df = scored_df[scored_df['type'] == '장점']
    pros_avg_score = (
      pros_df['satisfaction_score'].mean() if not pros_df.empty else 0
    )
    pros_keywords = (
      self.extract_keywords(pros_df['text'].tolist()) 
      if not pros_df.empty else []
    )
    pros_sample_reviews = self.get_top_reviews_by_score(scored_df, '장점', 3)
    
    # 단점 데이터 분석  
    cons_df = scored_df[scored_df['type'] == '단점']
    cons_avg_score = (
      cons_df['satisfaction_score'].mean() if not cons_df.empty else 0
    )
    cons_keywords = (
      self.extract_keywords(cons_df['text'].tolist()) 
      if not cons_df.empty else []
    )
    cons_sample_reviews = self.get_top_reviews_by_score(scored_df, '단점', 3)
    
    return {
      'scored_df': scored_df,
      'pros': {
        'avg_score': round(pros_avg_score, 2),
        'keywords': pros_keywords,
        'sample_reviews': pros_sample_reviews
      },
      'cons': {
        'avg_score': round(cons_avg_score, 2), 
        'keywords': cons_keywords,
        'sample_reviews': cons_sample_reviews
      }
    }
