import os
import re
import pathlib
import joblib
import pandas as pd
from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score


BASE_DIR = pathlib.Path(__file__).parent
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "sentiment_pipeline.joblib"
REPORT_PATH = MODEL_DIR / "eval_report.txt"

LABEL_MAP = {"negative": 0, "neutral": 1, "positive": 2}

def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", "", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = re.sub(r"[^a-z0-9\s'\-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def load_clean(split):
    ds = load_dataset("yhua219/EduRABSA_SA", split=split)
    df = pd.DataFrame(ds).dropna(subset=["text", "output"])
    df = df[df["output"].isin(LABEL_MAP)].copy()
    df["clean_text"] = df["text"].astype(str).apply(clean_text)
    df["label"] = df["output"].map(LABEL_MAP).astype(int)
    
    return df

if __name__ == "__main__":
    MODEL_DIR.mkdir(exist_ok=True)

    print("Loading data...")
    train = load_clean("train")
    test = load_clean("test")
    print(f"Train size: {len(train)} | Test size: {len(test)}")

    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            max_features=20000,
            min_df=2,
            token_pattern=r"(?u)\b[\w']+\b"
        )),
        ("clf", LogisticRegression(C=1.0, class_weight="balanced", max_iter=2000, n_jobs=-1))
    ])

    print("Training model...")
    pipe.fit(train["clean_text"], train["label"])

    print("Evaluating...")
    y_true = test["label"]
    y_pred = pipe.predict(test["clean_text"])
    
    target_names = ["negative", "neutral", "positive"]

    report = classification_report(y_true, y_pred, target_names=target_names, digits=3)
    mac_f1 = f1_score(y_true, y_pred, average="macro")
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)

    summary = f"Accuracy: {acc:.3f}\nMacro-F1: {mac_f1:.3f}\n\n{report}\nConfusion Matrix:\n{cm}\n"
    print(summary)

    joblib.dump(pipe, MODEL_PATH)
    
    with open(REPORT_PATH, "w") as f:
        f.write(summary)
        
    print("Saved pipeline and report.")