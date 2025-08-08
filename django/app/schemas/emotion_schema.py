from pydantic import BaseModel
from typing import Optional

# -----------------------------------------------------------------------------
# ✅ 감정 분석 요청 모델 (단일 텍스트)
# - 사용자가 텍스트(기사 요약 또는 본문 등)를 입력하면
#   지정된 모델로 감정을 분석해주는 API에 사용됨
# - 모델은 기본적으로 "vote" 사용 (전통 ML 앙상블)
# -----------------------------------------------------------------------------
class EmotionRequest(BaseModel):
    text: str                        # 감정을 분석할 텍스트 입력 (필수)
    model: Optional[str] = "vote"    # 사용할 모델: "vote", "stack", "transformer"
