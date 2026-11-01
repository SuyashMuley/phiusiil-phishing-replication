"""PhiUSIIL: leakage check + reproduction of the ~99% with engineered features (random split)."""
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.ensemble import HistGradientBoostingClassifier  # swap for xgboost.XGBClassifier once libomp is installed

df = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv")
df["phish"] = 1 - df["label"]  # PhiUSIIL: 1=legit, 0=phish -> our convention 1=phish
print("rows", len(df), "| phish", df.phish.sum(), "| legit", (df.phish == 0).sum(), "| dup URLs", df.URL.duplicated().sum())

# Trivial baselines
print("majority-class acc:", max(df.phish.mean(), 1 - df.phish.mean()))
rule = (df.URLSimilarityIndex < 100).astype(int)
print("URLSimilarityIndex<100 rule: acc %.4f f1 %.4f" % (accuracy_score(df.phish, rule), f1_score(df.phish, rule)))

# Reproduction: all numeric engineered features, random split
drop = ["FILENAME", "URL", "Domain", "TLD", "Title", "label", "phish"]
X = df.drop(columns=drop)
tr, te = train_test_split(df.index, test_size=0.2, random_state=0, stratify=df.phish)
m = HistGradientBoostingClassifier(max_iter=300, random_state=0).fit(X.loc[tr], df.phish[tr])
p = m.predict_proba(X.loc[te])[:, 1]
print("HistGB all features, random split: acc %.4f f1 %.4f auc %.4f" % (
    accuracy_score(df.phish[te], p > .5), f1_score(df.phish[te], p > .5), roc_auc_score(df.phish[te], p)))
