import os
import joblib
from backend.train_ml import train_model

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.joblib")

class MLLayer:
    def __init__(self):
        self.model = None
        self.load_or_train()

    def load_or_train(self):
        if not os.path.exists(MODEL_PATH):
            print("Model file not found. Initializing training...")
            try:
                train_model()
            except Exception as e:
                print(f"Error training model: {e}")
                return
        
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print("ML Model pipeline loaded successfully.")
            except Exception as e:
                print(f"Error loading model from {MODEL_PATH}: {e}")

    def predict_transaction(self, product_description: str, merchant_name: str, mcc: str, amount: float):
        """
        Predicts the benefit class and confidence score for a transaction.
        Returns:
          - benefit_type (str): "purchase_protection" | "return_protection" | "travel_delay" | "none"
          - confidence_score (float): probability score [0.0 - 1.0]
        """
        if not self.model:
            return "none", 0.5  # Fallback if model failed to load

        # Format feature text identically to training format
        def bin_amount(amt):
            if amt < 50: return "low"
            if amt < 250: return "medium"
            if amt < 1000: return "high"
            return "premium"

        desc = (product_description or "").lower()
        merchant = (merchant_name or "").lower()
        feature_text = f"mcc:{mcc} amt:{bin_amount(amount)} merchant:{merchant} desc:{desc}"

        try:
            # Get class probabilities
            classes = self.model.classes_
            probs = self.model.predict_proba([feature_text])[0]
            
            # Find index of max probability
            max_idx = probs.argmax()
            predicted_class = classes[max_idx]
            confidence = float(probs[max_idx])
            
            return predicted_class, confidence
        except Exception as e:
            print(f"Error during ML inference: {e}")
            return "none", 0.5

# Singleton instance
ml_engine = MLLayer()
