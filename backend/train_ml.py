import random
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
import joblib
import os

# Set random seeds for reproducibility
random.seed(42)
np.random.seed(42)

def generate_synthetic_data(num_samples=1200):
    # Templates and keywords
    purchase_protection_templates = [
        ("iPhone {version} {issue}", ["screen crack", "damaged screen", "liquid damage", "dropped in water", "stolen from car", "broken display"]),
        ("MacBook Pro {version} {issue}", ["spilled coffee on keyboard", "dropped from desk", "stolen bag", "broken hinge"]),
        ("Sony {device} {issue}", ["stolen at gym", "damaged headphones", "shattered screen"]),
        ("Gucci {bag_type} {issue}", ["stolen handbag", "ripped strap", "damaged leather"]),
        ("Samsung {device} {issue}", ["cracked glass", "stolen in subway", "water damage"]),
        ("Rolex {watch_type} {issue}", ["stolen from hotel room", "shattered face", "physical damage"]),
        ("designer {item} {issue}", ["stolen wallet", "stolen backpack", "damaged material"])
    ]
    
    pp_device_vars = {
        "{version}": ["14", "15", "16", "M2", "M3", "M4"],
        "{device}": ["headphones", "earbuds", "tablet", "galaxy S24", "oled tv"],
        "{bag_type}": ["purse", "clutch", "tote bag", "backpack"],
        "{watch_type}": ["Submariner", "Datejust", "Oyster"],
        "{item}": ["sunglasses", "briefcase", "leather belt"]
    }

    return_protection_templates = [
        ("merchant denied return of {item}", ["unworn dress", "size M shoes", "unused camera", "size L jacket", "unopened skin serum", "perfect condition headphones"]),
        ("refused to accept return of {item}", ["designer sneakers", "size 8 heels", "unopened perfume", "unworn luxury coat"]),
        ("return rejected for {item}", ["size 32 jeans", "unworn shirt", "unopened smartwatch"]),
        ("clothing return refused by {merchant}", ["unworn boots", "wrong size jacket", "gift item"])
    ]

    rp_vars = {
        "{item}": ["dress", "shoes", "coat", "camera", "perfume", "jacket", "jeans", "boots", "smartwatch", "sneakers"],
        "{merchant}": ["Zara", "H&M", "Nordstrom", "Nike Town", "Sephora", "Best Buy"]
    }

    travel_delay_templates = [
        ("{airline} Flight {flight_num} delay expenses", ["food and hotel", "refreshment and dinner", "airport hotel stay", "delayed flight meals", "lodging costs"]),
        ("flight delay booking {airline} {flight_num}", ["delay meal ticket", "overnight hotel", "taxi fare and dinner"]),
        ("ticket delay reimbursement {airline}", ["expenses due to flight cancellation", "stranded at airport food", "delayed connection expenses"])
    ]

    td_vars = {
        "{airline}": ["Delta", "United", "American Airlines", "Lufthansa", "JetBlue", "British Airways", "Air France"],
        "{flight_num}": ["DL102", "UA883", "AA203", "LH430", "B6590", "BA217", "AF012"]
    }

    none_templates = [
        ("grocery shopping at {grocery_merchant}", ["weekly food", "organic produce", "fruits and milk", "family dinner supplies", "household essentials"]),
        ("gas station fill-up {gas_merchant}", ["premium fuel", "unleaded gas", "car wash and snacks"]),
        ("dinner at {restaurant}", ["table for two", "family dinner", "drinks and dessert", "lunch special"]),
        ("coffee run {coffee_merchant}", ["morning latte", "espresso and muffin", "iced coffee"]),
        ("ride sharing {ride_merchant}", ["commute to office", "ride to airport", "weekend ride"]),
        ("subscription {sub_merchant}", ["monthly streaming fee", "cloud storage renewal", "premium membership"]),
        ("monthly bill {bill_merchant}", ["electricity payment", "water utility bill", "gym membership fee"]),
        ("pharmacy checkout {pharmacy}", ["cough syrup and vitamins", "prescription medication", "toiletries"])
    ]

    none_vars = {
        "{grocery_merchant}": ["Whole Foods", "Trader Joe's", "Safeway", "Kroger", "Aldi"],
        "{gas_merchant}": ["ExxonMobil", "Shell", "Chevron", "BP", "Texaco"],
        "{restaurant}": ["Olive Garden", "Chipotle", "Cheesecake Factory", "McDonald's", "Subway"],
        "{coffee_merchant}": ["Starbucks", "Dunkin", "Peet's Coffee", "Blue Bottle"],
        "{ride_merchant}": ["Uber", "Lyft"],
        "{sub_merchant}": ["Netflix", "Spotify", "Amazon Prime", "Disney+"],
        "{bill_merchant}": ["ConEd", "Comcast", "Equinox Gym", "Planet Fitness"],
        "{pharmacy}": ["CVS Pharmacy", "Walgreens", "Rite Aid"]
    }

    mccs = {
        "purchase_protection": ["5732", "5621", "5944", "5311", "5651"],
        "return_protection": ["5651", "5977", "5732", "5621"],
        "travel_delay": ["3000", "3001", "3002", "3003", "3004", "3005", "4511"],
        "none": ["5411", "5541", "5812", "4121", "4899", "4900", "5912"]
    }

    merchants = {
        "purchase_protection": ["Apple Store", "Best Buy", "Gucci", "Tiffany & Co", "Rolex", "Samsung Store", "Nordstrom"],
        "return_protection": ["Zara", "H&M", "Nordstrom", "Nike Town", "Sephora", "Best Buy", "B&H Photo"],
        "travel_delay": ["Delta Air Lines", "United Airlines", "American Airlines", "Lufthansa", "JetBlue", "Air France"],
        "none": ["Whole Foods", "ExxonMobil", "Olive Garden", "Starbucks", "Uber", "Netflix", "ConEd", "CVS Pharmacy"]
    }

    data = []
    
    samples_per_class = num_samples // 4

    # 1. Purchase Protection
    for _ in range(samples_per_class):
        template, issues = random.choice(purchase_protection_templates)
        desc = template
        for placeholder, values in pp_device_vars.items():
            if placeholder in desc:
                desc = desc.replace(placeholder, random.choice(values))
        desc = desc.replace("{issue}", random.choice(issues))
        
        mcc = random.choice(mccs["purchase_protection"])
        merchant = random.choice(merchants["purchase_protection"])
        amount = round(random.uniform(100.0, 3500.0), 2)
        data.append((desc, merchant, mcc, amount, "purchase_protection"))

    # 2. Return Protection
    for _ in range(samples_per_class):
        template, issues = random.choice(return_protection_templates)
        desc = template
        for placeholder, values in rp_vars.items():
            if placeholder in desc:
                desc = desc.replace(placeholder, random.choice(values))
        if "{merchant}" in desc:
            desc = desc.replace("{merchant}", random.choice(merchants["return_protection"]))
            
        mcc = random.choice(mccs["return_protection"])
        merchant = random.choice(merchants["return_protection"])
        amount = round(random.uniform(50.0, 800.0), 2)
        data.append((desc, merchant, mcc, amount, "return_protection"))

    # 3. Travel Delay
    for _ in range(samples_per_class):
        template, issues = random.choice(travel_delay_templates)
        desc = template
        for placeholder, values in td_vars.items():
            if placeholder in desc:
                desc = desc.replace(placeholder, random.choice(values))
        desc = desc.replace("{flight_num}", f"FL{random.randint(100, 999)}")
        
        mcc = random.choice(mccs["travel_delay"])
        merchant = random.choice(merchants["travel_delay"])
        amount = round(random.uniform(150.0, 1500.0), 2)
        data.append((desc, merchant, mcc, amount, "travel_delay"))

    # 4. None
    for _ in range(samples_per_class):
        template, issues = random.choice(none_templates)
        desc = template
        for placeholder, values in none_vars.items():
            if placeholder in desc:
                desc = desc.replace(placeholder, random.choice(values))
        
        mcc = random.choice(mccs["none"])
        merchant = random.choice(merchants["none"])
        amount = round(random.uniform(5.0, 250.0), 2)
        data.append((desc, merchant, mcc, amount, "none"))

    # Convert to DataFrame
    df = pd.DataFrame(data, columns=["product_description", "merchant_name", "mcc", "amount", "label"])
    return df

def train_model():
    print("Generating synthetic transaction data...")
    df = generate_synthetic_data(1600)

    # Features representation: we combine text features to prevent leakage of individual variables
    # Format: mcc:<mcc> amount:<bucket> merchant:<name> desc:<desc>
    # Discretize amount to help the linear model understand price levels
    def bin_amount(amt):
        if amt < 50: return "low"
        if amt < 250: return "medium"
        if amt < 1000: return "high"
        return "premium"

    df["feature_text"] = df.apply(
        lambda r: f"mcc:{r['mcc']} amt:{bin_amount(r['amount'])} merchant:{r['merchant_name'].lower()} desc:{r['product_description'].lower()}",
        axis=1
    )

    # Deduplicate to strictly prevent data leakage across splits
    df = df.drop_duplicates(subset=["feature_text"])
    print(f"Data shape after deduplication: {df.shape}")

    # Split train/test
    X = df["feature_text"]
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Strict check for leakage: ensure test set has no identical texts as train set
    train_set = set(X_train)
    leaks = [x for x in X_test if x in train_set]
    print(f"Number of test set leakage items (exactly identical features): {len(leaks)}")
    assert len(leaks) == 0, "DATA LEAKAGE DETECTED! Test items exist in Train set."

    # Define TF-IDF + Logistic Regression Pipeline
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("clf", LogisticRegression(C=1.0, max_iter=200, solver="lbfgs"))
    ])

    print("Training the scikit-learn classifier...")
    pipeline.fit(X_train, y_train)

    # Evaluation
    y_pred = pipeline.predict(X_test)
    print("\n--- ML Classification Report ---")
    print(classification_report(y_test, y_pred))

    # Save the pipeline
    model_dir = os.path.dirname(__file__)
    model_path = os.path.join(model_dir, "model.joblib")
    joblib.dump(pipeline, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_model()
