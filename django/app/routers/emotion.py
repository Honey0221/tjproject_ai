from fastapi import APIRouter, HTTPException

# ✅ 요청 바디 스키마 (text, model 지정)
from app.schemas.emotion_schema import EmotionRequest

# ✅ 감정 분석 로직을 처리하는 서비스 함수
from app.services.emotion_service import analyze_emotion

# ✅ 허용된 모델 키 (e.g., "vote", "stack", "transformer") 리스트
from app.utils.emotion_model_loader import ALLOWED_MODELS

# 🔧 라우터 객체 생성
router = APIRouter()

# -----------------------------------------------------------------------------
# ✅ 엔드포인트: 단일 텍스트 감정 분석 API
# - 입력된 기사(또는 문장)에 대해 감정 라벨(긍정/중립/부정)을 분류
# - 분석 모델은 전통 ML 또는 Transformer 중 선택 가능
# -----------------------------------------------------------------------------
@router.post("/api/emotion")
def emotion_machine(req: EmotionRequest):
    # 입력된 텍스트 전처리
    text = req.text.strip()
    model_key = req.model

    # 예외 처리: 빈 텍스트
    if not text:
        raise HTTPException(status_code=400, detail="기사를 넣어주세요.")

    # 예외 처리: 허용되지 않은 모델 키
    if model_key not in ALLOWED_MODELS:
        raise HTTPException(status_code=400, detail=f"지원되지 않는 모델입니다: '{model_key}'")

    # 감정 분석 실행
    result = analyze_emotion(text, model_key)

    # 결과 반환
    return {
        "text": text,         # 원문
        "model": model_key,   # 사용된 모델 키
        **result              # label (예: "긍정") + confidence
    }
