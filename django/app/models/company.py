from ..database.mongodb import mongodb_manager

class CompanyModel:
  """기업 정보 모델"""
  def __init__(self):
    self.db_manager = mongodb_manager
  
  @property
  def collection(self):
    """컬렉션 인스턴스 반환"""
    if not self.db_manager.is_connected:
      return None
    return self.db_manager.db['companies']
  
  async def get_companies_by_name(self, name):
    """다수 기업 검색"""
    try:
      cursor = self.collection.find({"name": {"$regex": name, "$options": "i"}})
      return await cursor.to_list(length=None)
    except Exception as e:
      print(f"기업 조회 중 오류 발생: {str(e)}")
      return []
  
  async def get_company_by_exact_name(self, name):
    """단일 기업 검색"""
    try:
      return await self.collection.find_one({"name": name})
    except Exception as e:
      print(f"기업 조회 중 오류 발생: {str(e)}")
      return None
  
  async def get_total_count(self):
    """전체 기업 수 조회"""
    try:
      return await self.collection.count_documents({})
    except Exception as e:
      print(f"전체 수 조회 중 오류 발생: {str(e)}")
      return 0

  async def get_companies_by_field(self, field_name):
    """특정 필드가 있는 모든 기업 조회"""
    try:
      cursor = self.collection.find({field_name: {"$exists": True, "$ne": None}})
      return await cursor.to_list(length=None)
    except Exception as e:
      print(f"{field_name} 필드 기업 조회 중 오류 발생: {str(e)}")
      return []

  async def get_companies_by_category(self, category):
    """특정 카테고리의 기업들 조회"""
    try:
      cursor = self.collection.find({"산업 분야": {"$regex": category, "$options": "i"}})
      return await cursor.to_list(length=None)
    except Exception as e:
      print(f"카테고리 기업 조회 중 오류 발생: {str(e)}")
      return []

class CompanyReviewModel:
  """기업 리뷰 모델"""
  def __init__(self):
    self.db_manager = mongodb_manager

  @property
  def collection(self):
    """컬렉션 인스턴스 반환"""
    if not self.db_manager.is_connected:
      return None
    return self.db_manager.db['company_reviews']

  async def get_reviews_by_company(self, name):
    """기업명으로 리뷰 조회"""
    try:
      cursor = self.collection.find({"name": name})
      return await cursor.to_list(length=None)
    except Exception as e:
      print(f"리뷰 조회 중 오류 발생: {str(e)}")
      return []

# 전역 인스턴스
company_model = CompanyModel()
company_review_model = CompanyReviewModel()