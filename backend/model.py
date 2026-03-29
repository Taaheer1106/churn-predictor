import os
import pickle
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score

DATASET = 'WA_Fn-UseC_-Telco-Customer-Churn.csv'
if not os.path.exists(DATASET):
    DATASET = '../WA_Fn-UseC_-Telco-Customer-Churn.csv'

df = pd.read_csv(DATASET)
print(f"Dataset shape: {df.shape}")

df.drop('customerID', axis=1, inplace=True)

# TotalCharges has blank strings for some rows — drop them
df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
df.dropna(inplace=True)
print(f"After cleaning: {df.shape}")

le = LabelEncoder()
for col in df.select_dtypes(include='object').columns:
    df[col] = le.fit_transform(df[col])

X = df.drop('Churn', axis=1)
y = df['Churn']
print(f"Features (X): {X.shape[1]} columns")
print(f"Target distribution:\n{y.value_counts()}")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"\nTraining samples: {len(X_train)}")
print(f"Testing samples:  {len(X_test)}")

models = {
    'Random Forest': RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=4,
        class_weight='balanced',
        random_state=42
    ),
    'Gradient Boosting': GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        random_state=42
    )
}

best_model = None
best_auc = 0
best_name = ''

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
        best_auc = auc
        best_model = m
        best_name = name

print(f"\nBest model: {best_name} (AUC-ROC: {best_auc:.4f})")

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'churn_model.pkl')
with open(MODEL_PATH, 'wb') as f:
    pickle.dump(best_model, f)

print(f"Model saved as churn_model.pkl")
print(f"Flask will now use: {best_name}")
