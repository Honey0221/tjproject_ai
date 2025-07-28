from xgboost import XGBClassifier
from sklearn.ensemble import VotingClassifier

print(XGBClassifier)  # <class 'xgboost.sklearn.XGBClassifier'>

model = VotingClassifier(estimators=[
    ("xgb", XGBClassifier(eval_metric="mlogloss", use_label_encoder=False)),
    ...
], voting="soft")
