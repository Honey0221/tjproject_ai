import os
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------

# BASE_DIR = /<프로젝트 루트>/newsCrawling
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 전통 ML 모델 저장 디렉토리
MODEL_DIR = os.path.join(BASE_DIR, 'emotionAnalysisModels', 'baseEnsembleModels')

# HuggingFace Transformer 모델 디렉토리
HF_MODEL_DIR = os.path.join(BASE_DIR, 'emotionAnalysisModels', 'emotionKcbertModels')

# ---------------------------------------------------------------
# 모델 키 매핑
# ---------------------------------------------------------------

ALLOWED_MODELS = {
    "stack": "StackingEnsemble",     # ✅ .joblib 확장자 생략
    "vote": "VotingEnsemble",
    "transformer": "transformer"     # 특별 처리
}

# ---------------------------------------------------------------
# 문장 임베딩 모델 (전통 ML용)
# ---------------------------------------------------------------

embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")

# ---------------------------------------------------------------
# HuggingFace 모델 로딩 (transformer용)
# ---------------------------------------------------------------

hf_tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_DIR)
hf_model = AutoModelForSequenceClassification.from_pretrained(HF_MODEL_DIR)

# ---------------------------------------------------------------
# 감정 분류 라벨 매핑
# ---------------------------------------------------------------

id2label = {
    0: "긍정",
    1: "중립",
    2: "부정"
}
