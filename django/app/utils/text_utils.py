import re

def is_summary_empty(summary: str) -> bool:
    if not isinstance(summary, str):
        return True
    # 한글, 영문, 숫자 포함 안되면 비어있는 것으로 판단
    return not bool(re.search(r"[가-힣a-zA-Z0-9]", summary))
