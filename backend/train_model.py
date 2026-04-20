"""
train_model.py — Pre-trains the Isolation Forest model on synthetic normal prompts.
Run this once before starting the security engine.
"""

import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
import os

# ------------------------------------------------------------------------------
# 1. Feature extraction (must match security_engine.py)
# ------------------------------------------------------------------------------
def extract_features(text: str) -> list[float]:
    """Extract numerical features from a prompt for anomaly detection."""
    length = len(text)
    word_count = len(text.split())
    special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
    special_ratio = special_chars / max(length, 1)
    avg_word_length = (
        sum(len(w) for w in text.split()) / max(word_count, 1)
    )
    # Punctuation density
    punct_count = sum(1 for c in text if c in "!?.,;:\"'")
    punct_ratio = punct_count / max(length, 1)
    # Digit ratio
    digit_ratio = sum(1 for c in text if c.isdigit()) / max(length, 1)
    # Uppercase ratio
    upper_ratio = sum(1 for c in text if c.isupper()) / max(length, 1)

    return [
        length,
        word_count,
        special_ratio,
        avg_word_length,
        punct_ratio,
        digit_ratio,
        upper_ratio,
    ]


# ------------------------------------------------------------------------------
# 2. Synthetic "normal" prompts — representative of everyday user queries
# ------------------------------------------------------------------------------
NORMAL_PROMPTS = [
    "What is the capital of France?",
    "Write me a short poem about the ocean.",
    "Explain quantum computing in simple terms.",
    "How do I bake a chocolate cake?",
    "Summarize the theory of relativity.",
    "Translate 'hello' into Spanish.",
    "Give me three tips for better sleep.",
    "What are the main causes of climate change?",
    "Help me write an email to my professor.",
    "What is machine learning?",
    "Tell me a fun fact about space.",
    "How does photosynthesis work?",
    "Write a short story about a dragon.",
    "What is the meaning of life?",
    "List five healthy breakfast options.",
    "Explain the difference between ML and AI.",
    "How do I start learning Python?",
    "What causes rainbows?",
    "Give me a recipe for tomato soup.",
    "Describe the water cycle.",
    "How do airplanes fly?",
    "What is blockchain technology?",
    "Write a haiku about autumn.",
    "Explain the French Revolution briefly.",
    "How does vaccination work?",
    "What are black holes?",
    "Describe object-oriented programming.",
    "How do I improve my writing skills?",
    "What is the stock market?",
    "Explain neural networks simply.",
]

# ------------------------------------------------------------------------------
# 3. Train and save the model
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    features = np.array([extract_features(p) for p in NORMAL_PROMPTS])
    print(f"[Training] Feature matrix shape: {features.shape}")

    model = IsolationForest(
        n_estimators=150,
        contamination=0.05,  # expect 5% anomalies in normal data
        random_state=42,
    )
    model.fit(features)
    print("[Training] Isolation Forest model trained successfully.")

    model_path = os.path.join(os.path.dirname(__file__), "model.pkl")
    joblib.dump(model, model_path)
    print(f"[Training] Model saved to: {model_path}")
