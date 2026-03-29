# ─────────────────────────────────────────────
# STEP 1: Import the tools we need
# ─────────────────────────────────────────────

import pandas as pd

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

import pickle


# ─────────────────────────────────────────────
# STEP 2: Load the dataset
# ─────────────────────────────────────────────

import os

# Look for dataset in current dir or parent dir (local dev)
DATASET = 'WA_Fn-UseC_-Telco-Customer-Churn.csv'
if not os.path.exists(DATASET):
    DATASET = '../WA_Fn-UseC_-Telco-Customer-Churn.csv'

df = pd.read_csv(DATASET)
print(f"Dataset shape: {df.shape}")


# ─────────────────────────────────────────────
# STEP 3: Clean the data
# ─────────────────────────────────────────────

df.drop('customerID', axis=1, inplace=True)

# TotalCharges has blank strings — convert to NaN then drop
df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
df.dropna(inplace=True)

print(f"After cleaning: {df.shape}")


# ─────────────────────────────────────────────
# STEP 4: Encode text columns into numbers
# ─────────────────────────────────────────────

le = LabelEncoder()
for col in df.select_dtypes(include='object').columns:
    df[col] = le.fit_transform(df[col])

print("All columns are now numeric.")


# ─────────────────────────────────────────────
# STEP 5: Separate features (X) and target (y)
# ─────────────────────────────────────────────

X = df.drop('Churn', axis=1)
y = df['Churn']

print(f"Features (X): {X.shape[1]} columns")
print(f"Target distribution:\n{y.value_counts()}")


# ─────────────────────────────────────────────
# STEP 6: Split into training and test sets
# ─────────────────────────────────────────────

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples:  {len(X_test)}")


# ─────────────────────────────────────────────
# STEP 7: Train and compare two models
# We train Random Forest AND Gradient Boosting,
# then automatically save whichever scores higher AUC-ROC.
# ─────────────────────────────────────────────

models = {
    'Random Forest': RandomForestClassifier(
        n_estimators=200,        # more trees = more stable predictions
        max_depth=10,            # limits tree depth to prevent overfitting
        min_samples_leaf=4,      # each leaf must have at least 4 samples
        class_weight='balanced', # compensates for more non-churners than churners
        random_state=42
    ),
    'Gradient Boosting': GradientBoostingClassifier(
        n_estimators=200,        # 200 boosting rounds
        learning_rate=0.05,      # small steps = more accurate but slower
        max_depth=4,             # shallow trees work well for boosting
        subsample=0.8,           # use 80% of data per round to reduce overfitting
        random_state=42
    )
}

best_model = None
best_auc   = 0
best_name  = ''

print("\n--- Model Comparison ---")

for name, m in models.items():
    m.fit(X_train, y_train)
    y_pred = m.predict(X_test)
    y_prob = m.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)

    print(f"\n{name}")
    print(f"  Accuracy : {acc:.4f}")
    print(f"  AUC-ROC  : {auc:.4f}")
    print(classification_report(y_test, y_pred, target_names=['No Churn', 'Churn']))

    if auc > best_auc:
        best_auc   = auc
        best_model = m
        best_name  = name

print(f"\nBest model: {best_name} (AUC-ROC: {best_auc:.4f})")


# ─────────────────────────────────────────────
# STEP 8: Save the best model
# ─────────────────────────────────────────────

with open('churn_model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

print(f"Model saved as churn_model.pkl")
print(f"Flask will now use: {best_name}")
