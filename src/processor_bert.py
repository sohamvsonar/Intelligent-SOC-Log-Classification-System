import joblib
from sentence_transformers import SentenceTransformer

model_embedding = SentenceTransformer('all-MiniLM-L6-v2')  # Lightweight embedding model
model_classification = joblib.load("../models/log_classification_model.joblib")


def bert_classify(log_message):
    embeddings = model_embedding.encode([log_message])
    probabilities = model_classification.predict_proba(embeddings)[0]
    print(probabilities)
    if max(probabilities) < 0.55:
        return "Unclassified"
    predicted_label = model_classification.predict(embeddings)[0]
    
    return predicted_label


if __name__ == "__main__":
    logs = [
        "alpha.osapi_compute.wsgi.server - 12.10.11.1 - API returned 404 not found error",
        "GET /v2/3454/servers/detail HTTP/1.1 RCODE   404 len: 1583 time: 0.1878400",
        "System crashed due to drivers errors when restarting the server",
        "Hey bro, chill ya!",
        "Multiple login failures occurred on user 6454 account",
        "Server A790 was restarted unexpectedly during the process of data transfer"
    ]
    for log in logs:
        label = bert_classify(log)
        print(log, "->", label)
