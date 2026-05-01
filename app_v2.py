import os
import json
import hashlib
import datetime
import pathlib
import pandas as pd
import gradio as gr
import requests
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = pathlib.Path(__file__).parent.resolve()
FAQ_STATE_PATH = BASE_DIR / "faq_state.json"
FEEDBACK_XLSX_PATH = BASE_DIR / "ece_feedback.xlsx"
SENTIMENT_MODEL_PATH = BASE_DIR / "models" / "sentiment_pipeline.joblib"

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

LABEL_MAP = {0: "negative", 1: "neutral", 2: "positive"}

def chunk_text(text, chunk_size=700, overlap=120):
    chunks = []
    start = 0
    text = text.strip()
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end == len(text):
            break
        start = end - overlap
    return chunks

def load_items_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        df = pd.read_csv(file_path).fillna("")
        return [" | ".join(f"{col}: {row[col]}" for col in df.columns) for _, row in df.iterrows()]

    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path).fillna("")
        return [" | ".join(f"{col}: {row[col]}" for col in df.columns) for _, row in df.iterrows()]

    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            items = []
            for item in data:
                if isinstance(item, dict):
                    items.append(" | ".join(f"{k}: {v}" for k, v in item.items()))
                else:
                    items.append(str(item))
            return items
        if isinstance(data, dict):
            return chunk_text(json.dumps(data, indent=2, ensure_ascii=False))
        return [str(data)]

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return chunk_text(f.read())

    raise ValueError("Unsupported file type. Please upload CSV, XLSX, JSON, or TXT.")

# FAQ Weighting system
# Uses alpha/beta counters. Only penalizes bad responses on negative feedback.

def item_id(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]

def load_faq_state():
    if FAQ_STATE_PATH.exists():
        with open(FAQ_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_faq_state(state):
    with open(FAQ_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)

def get_weight(state, iid):
    entry = state.get(iid, {"alpha": 1, "beta": 1})
    return entry["alpha"] / (entry["alpha"] + entry["beta"])

def update_weight(state, iid, positive):
    entry = state.setdefault(iid, {"alpha": 1, "beta": 1})
    if positive:
        return entry
    
    entry["beta"] += 1
    save_faq_state(state)
    return entry

_INDEX = {"file_path": None, "items": None, "ids": None, "vectorizer": None, "matrix": None}

def build_or_get_index(file_path):
    if _INDEX["file_path"] == file_path and _INDEX["matrix"] is not None:
        return _INDEX

    items = load_items_from_file(file_path)
    items = [i for i in items if str(i).strip()]
    
    if len(items) > 20000:
        items = items[:20000]

    if not items:
        _INDEX.update(file_path=file_path, items=[], ids=[], vectorizer=None, matrix=None)
        return _INDEX

    ids = [item_id(i) for i in items]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(items)
    
    _INDEX.update(file_path=file_path, items=items, ids=ids, vectorizer=vectorizer, matrix=matrix)
    return _INDEX

def retrieve(file_path, question, top_k=4):
    index = build_or_get_index(file_path)
    items, ids = index["items"], index["ids"]
    vectorizer, matrix = index["vectorizer"], index["matrix"]
    
    if not items or vectorizer is None:
        return []

    q_vec = vectorizer.transform([question])
    sims = cosine_similarity(q_vec, matrix).flatten()

    state = load_faq_state()
    weights = [get_weight(state, iid) for iid in ids]
    
    # Combine TF-IDF sim with our historical weight prior
    final_scores = sims * weights 

    top_idx = final_scores.argsort()[-top_k:][::-1]
    return [(ids[i], items[i], float(sims[i]), float(weights[i]), float(final_scores[i])) for i in top_idx]

def call_openrouter(question, retrieved):
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY not found in environment."

    context_text = "\n\n".join(
        f"[Record {idx} | similarity={sim:.3f} | weight={weight:.3f}]\n{item}"
        for idx, (iid, item, sim, weight, score) in enumerate(retrieved, start=1)
    )

    sys_prompt = (
        "You are a helpful assistant for the UIUC Electrical and Computer Engineering (ECE) department. "
        "Use the retrieved records to answer the student's question. If the answer is not supported by the records, "
        "say that clearly. Synthesize the information rather than just listing record numbers."
    )

    user_prompt = (
        f"User question:\n{question}\n\n"
        f"Retrieved records:\n{context_text}\n\n"
        "Instructions:\n"
        "- Answer using only the retrieved records.\n"
        "- If multiple records support the answer, mention them.\n"
        "- If records are insufficient, state it.\n"
        "- When asked about faculty names, return the 'name:' field accurately."
    )

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "openrouter/free",
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.2,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Model API error: {e}"

def load_sentiment_model():
    if SENTIMENT_MODEL_PATH.exists():
        try:
            return joblib.load(SENTIMENT_MODEL_PATH)
        except Exception:
            return None
    return None

_SENTIMENT_PIPELINE = load_sentiment_model()

def classify_sentiment(text):
    if not _SENTIMENT_PIPELINE:
        return {"label": "model_not_loaded", "polarity": 0.5}
    
    probs = _SENTIMENT_PIPELINE.predict_proba([text])[0]
    label_idx = int(probs.argmax())
    
    polarity = float(probs[2]) + 0.5 * float(probs[1])
    return {"label": LABEL_MAP[label_idx], "polarity": polarity}

def append_feedback_to_xlsx(session_id, raw_feedback, sentiment):
    row = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "session_id": session_id,
        "raw_feedback": raw_feedback,
        "predicted_label": sentiment["label"],
        "polarity": round(sentiment["polarity"], 4),
    }
    
    if FEEDBACK_XLSX_PATH.exists():
        df = pd.concat([pd.read_excel(FEEDBACK_XLSX_PATH), pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])
        
    df.to_excel(FEEDBACK_XLSX_PATH, index=False)


def get_session_id():
    return hashlib.sha1(str(datetime.datetime.now().timestamp()).encode()).hexdigest()[:8]

def handle_ask(file_path, question, session_id):
    if not session_id:
        session_id = get_session_id()
    if not file_path:
        return "Please upload a dataset.", "", [], session_id
    if not question.strip():
        return "Please enter a question.", "", [], session_id

    try:
        retrieved = retrieve(file_path, question, top_k=10)
    except Exception as e:
        return f"Retrieval failed: {e}", "", [], session_id

    if not retrieved:
        return "No relevant records found.", "", [], session_id

    answer = call_openrouter(question, retrieved)
    
    supporting = "\n\n".join(
        f"**Record {i}** (sim {sim:.3f}, weight {w:.3f})\n{item}"
        for i, (iid, item, sim, w, s) in enumerate(retrieved, start=1)
    )
    
    output_md = f"## Answer\n{answer}\n\n---\n## Supporting Context\n{supporting}"
    
    top_record = [{"id": retrieved[0][0], "preview": retrieved[0][1][:120]}]
    return output_md, "", top_record, session_id

def handle_helpful(was_helpful, top_state):
    if not top_state:
        return "No prior question to attribute feedback to."
    
    top_iid = top_state[0]["id"]
    state = load_faq_state()
    entry = update_weight(state, top_iid, positive=was_helpful)
    
    curr_weight = entry["alpha"] / (entry["alpha"] + entry["beta"])
    
    if was_helpful:
        return f"Thanks! Current weight: **{curr_weight:.3f}**"
    return f"Feedback recorded — record downweighted. New weight: **{curr_weight:.3f}**"

def handle_feedback(feedback_text, session_id):
    if not feedback_text.strip():
        return "Please enter feedback first.", session_id
        
    if not session_id:
        session_id = get_session_id()
        
    sentiment = classify_sentiment(feedback_text)
    append_feedback_to_xlsx(session_id, feedback_text.strip(), sentiment)
    
    return f"Saved to ece_feedback.xlsx. \n\nPredicted sentiment: {sentiment['label']}", session_id

with gr.Blocks(title="UIUC ECE Chatbot") as demo:
    gr.Markdown("# UIUC ECE Chatbot\nUpload your dataset, ask questions, and leave feedback.")

    session_state = gr.State("")
    top_record_state = gr.State([])

    with gr.Row():
        file_input = gr.File(label="Upload Dataset (JSON/CSV/TXT)", type="filepath")

    question_input = gr.Textbox(label="Ask a question", placeholder="e.g. Prerequisites for ECE 313?")
    ask_btn = gr.Button("Ask", variant="primary")
    answer_out = gr.Markdown()

    gr.Markdown("---\n## Was this response helpful?")
    with gr.Row():
        yes_btn = gr.Button("👍 Yes")
        no_btn = gr.Button("👎 No")
    helpful_status = gr.Markdown()

    gr.Markdown("---\n## Department Feedback")
    feedback_input = gr.Textbox(label="Feedback", lines=2)
    submit_btn = gr.Button("Submit feedback")
    feedback_status = gr.Markdown()

    ask_btn.click(
        handle_ask,
        inputs=[file_input, question_input, session_state],
        outputs=[answer_out, helpful_status, top_record_state, session_state],
    )
    
    yes_btn.click(lambda s: handle_helpful(True, s), inputs=[top_record_state], outputs=[helpful_status])
    no_btn.click(lambda s: handle_helpful(False, s), inputs=[top_record_state], outputs=[helpful_status])
    submit_btn.click(handle_feedback, inputs=[feedback_input, session_state], outputs=[feedback_status, session_state])

if __name__ == "__main__":
    demo.launch()