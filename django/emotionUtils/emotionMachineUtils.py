import os
import torch
import joblib
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------

# 프로젝트 루트 기준 BASE 디렉토리
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 전통 ML 모델이 저장된 디렉토리
MODEL_DIR = os.path.join(BASE_DIR, 'emotionAnalysisModels', 'baseEnsembleModels')

# HuggingFace transformer 모델 디렉토리
HF_MODEL_DIR = os.path.join(BASE_DIR, 'emotionAnalysisModels', 'emotionKcbertModels')


# ---------------------------------------------------------------
# 모델 매핑 및 로딩
# ---------------------------------------------------------------

# 지원되는 모델 목록 (model_key: 파일명)
ALLOWED_MODELS = {
    "stack": "StackingEnsemble.joblib",        # 스태킹 앙상블
    "vote": "VotingEnsemble.joblib",           # 보팅 앙상블 (기본값)
    "transformer": "transformer"               # transformer은 별도 처리
}

# 전통 ML에서 사용할 문장 임베딩 모델
embedding_model = SentenceTransformer("jhgan/ko-sroberta-multitask")


# ---------------------------------------------------------------
# HuggingFace 모델 로딩 (transformer 방식용)
# ---------------------------------------------------------------

# transformers pipeline 객체 (GPU 사용 우선)
sentiment_pipeline = pipeline(
    "text-classification",
    model=HF_MODEL_DIR,
    tokenizer=HF_MODEL_DIR,
    device=0 if torch.cuda.is_available() else -1
)

# tokenizer & model 객체 직접 로딩
hf_tokenizer = AutoTokenizer.from_pretrained(HF_MODEL_DIR)
hf_model = AutoModelForSequenceClassification.from_pretrained(HF_MODEL_DIR)


# ---------------------------------------------------------------
# 감정 라벨 매핑
# ---------------------------------------------------------------

id2label = {
    0: "긍정",
    1: "중립",
    2: "부정"
}
