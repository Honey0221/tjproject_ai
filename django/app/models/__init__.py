# 비즈니스 모델 및 ORM 모델

from .company import CompanyModel, CompanyReviewModel, company_model, company_review_model
from .inquiry import Inquiry

__all__ = [
  # MongoDB 모델
  'CompanyModel',
  'CompanyReviewModel',
  'company_model', 
  'company_review_model',
  
  # PostgreSQL 모델 (Tortoise ORM)
  'Inquiry'
]