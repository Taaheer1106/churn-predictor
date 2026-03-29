# ─────────────────────────────────────────────
# STEP 1: Import the tools we need
# ─────────────────────────────────────────────

from flask import Flask, request, jsonify  # Flask = web framework | request = reads incoming data | jsonify = sends JSON response
from flask_cors import CORS               # Allows Angular (running on a different port) to call this API
from dotenv import load_dotenv            # Loads secret keys from a .env file
import pickle                             # Loads the saved ML model
import pandas as pd                       # Builds the input data into the format the model expects
import os                                 # Reads environment variables (API keys)
from openai import OpenAI                 # OpenAI client for GPT-4o-mini explanation
from groq import Groq                     # Groq client for free AI explanations
import psycopg2                           # Connects to PostgreSQL database
from sklearn.preprocessing import LabelEncoder  # Encode text columns in bulk CSV


# ─────────────────────────────────────────────
# STEP 2: Initialize the app
# ─────────────────────────────────────────────

load_dotenv()       # Reads the .env file and makes its values available via os.getenv()

app = Flask(__name__)  # Creates the Flask app. __name__ tells Flask where to look for files.
CORS(app)              # Enables Cross-Origin requests — Angular (port 4200) talking to Flask (port 5000)


# ─────────────────────────────────────────────
# STEP 2b: Database helper functions
# ─────────────────────────────────────────────

def get_db_connection():
    # Reads DATABASE_URL from .env and opens a connection to PostgreSQL
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn

def save_prediction(data, probability, risk_level, explanation, customer_name=None):
    # Saves one prediction record to the database
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO predictions
                (customer_name, tenure, contract, monthly_charges, total_charges,
                 churn_probability, risk_level, explanation)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            customer_name if customer_name else None,
            int(data.get('tenure')),
            int(data.get('Contract')),
            float(data.get('MonthlyCharges')),
            float(data.get('TotalCharges')),
            float(round(probability * 100, 1)),
            risk_level,
            explanation
        ))
        conn.commit()
        cur.close()
        conn.close()
        print("Prediction saved to database.")
    except Exception as e:
        print(f"Database error: {e}")


# ─────────────────────────────────────────────
# STEP 3: Load the trained ML model
# ─────────────────────────────────────────────

# Load once when the server starts — not on every request (that would be slow)
with open('churn_model.pkl', 'rb') as f:  # 'rb' = read binary
    model = pickle.load(f)


# ─────────────────────────────────────────────
# STEP 4: Define the column order
# ─────────────────────────────────────────────

# The model was trained on columns in a specific order
# We MUST send data in the exact same order during prediction
# Otherwise the model reads the wrong values for the wrong features

FEATURE_COLUMNS = [
    'gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure',
    'PhoneService', 'MultipleLines', 'InternetService', 'OnlineSecurity',
    'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV',
    'StreamingMovies', 'Contract', 'PaperlessBilling', 'PaymentMethod',
    'MonthlyCharges', 'TotalCharges'
]


# ─────────────────────────────────────────────
# STEP 5: Helper — determine risk level from probability
# ─────────────────────────────────────────────

def get_risk_level(probability):
    # probability is a float between 0 and 1
    # We convert it to a human-readable risk label
    if probability < 0.4:
        return 'Low'
    elif probability < 0.7:
        return 'Medium'
    else:
        return 'High'


# ─────────────────────────────────────────────
# STEP 5b: Fallback explanation (no OpenAI needed)
# ─────────────────────────────────────────────

def get_fallback_explanation(customer_data, probability, risk_level):
    tenure = customer_data.get('tenure', 0)
    contract = customer_data.get('Contract', 0)
    monthly = customer_data.get('MonthlyCharges', 0)

    contract_label = {0: 'month-to-month', 1: 'one-year', 2: 'two-year'}.get(contract, 'month-to-month')

    if risk_level == 'High':
        return (f"This customer has a high churn risk of {probability:.0%}. "
                f"With only {tenure} months of tenure, a {contract_label} contract, "
                f"and monthly charges of ${monthly}, they show several indicators of dissatisfaction. "
                f"Consider offering a discounted long-term contract or additional services to retain them.")
    elif risk_level == 'Medium':
        return (f"This customer has a moderate churn risk of {probability:.0%}. "
                f"They have been with the company for {tenure} months on a {contract_label} contract. "
                f"A proactive check-in or loyalty reward could help strengthen their commitment.")
    else:
        return (f"This customer has a low churn risk of {probability:.0%}. "
                f"With {tenure} months of tenure and a {contract_label} contract, "
                f"they appear satisfied. Continue providing consistent service quality.")


# ─────────────────────────────────────────────
# STEP 6: Helper — ask Groq (free AI) to explain the prediction
# ─────────────────────────────────────────────

def get_ai_explanation(customer_data, probability, risk_level):
    # Initialize Groq client — reads GROQ_API_KEY from .env
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))

    # Build a clear prompt that gives the AI all the context it needs
    prompt = f"""
You are a customer retention analyst. A machine learning model predicted that a telecom customer
has a {probability:.0%} chance of canceling their subscription (Risk Level: {risk_level}).

Customer details:
- Tenure: {customer_data['tenure']} months
- Contract type: {customer_data['Contract']}
- Monthly charges: ${customer_data['MonthlyCharges']}
- Internet service: {customer_data['InternetService']}
- Tech support: {customer_data['TechSupport']}
- Online security: {customer_data['OnlineSecurity']}
- Senior citizen: {'Yes' if customer_data['SeniorCitizen'] == 1 else 'No'}

Write 2-3 sentences in plain English explaining WHY this customer might churn
and ONE specific action the business can take to retain them.
Keep it simple — no technical jargon.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",  # Fast free model from Meta via Groq
        messages=[
            {"role": "user", "content": prompt}
        ],
        max_tokens=150,   # Keep response short and focused
        temperature=0.7   # Balanced creativity
    )

    # Extract the text from the response
    return response.choices[0].message.content.strip()


# ─────────────────────────────────────────────
# STEP 6b: Input validation
# Checks that all required fields are present and have valid values
# Returns a list of error messages (empty list = all good)
# ─────────────────────────────────────────────

def validate_input(data):
    errors = []

    # Every feature column must be present
    for col in FEATURE_COLUMNS:
        if col not in data or data[col] == '' or data[col] is None:
            errors.append(f"Missing field: {col}")

    # Numeric fields must be non-negative
    for field in ['tenure', 'MonthlyCharges', 'TotalCharges']:
        if field in data:
            try:
                val = float(data[field])
                if val < 0:
                    errors.append(f"{field} cannot be negative")
            except (ValueError, TypeError):
                errors.append(f"{field} must be a number")

    # Tenure must be a whole number
    if 'tenure' in data:
        try:
            if float(data['tenure']) != int(float(data['tenure'])):
                errors.append("tenure must be a whole number (months)")
        except (ValueError, TypeError):
            pass  # already caught above

    return errors


# ─────────────────────────────────────────────
# STEP 7: The main prediction endpoint
# ─────────────────────────────────────────────

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # request.get_json() reads the JSON body sent by Angular
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate all fields before running the model
        errors = validate_input(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400

        # Build a DataFrame from the incoming data
        # The model expects a 2D table (even for one customer), so we wrap in a list
        input_df = pd.DataFrame([data], columns=FEATURE_COLUMNS)

        # Run the prediction
        # predict_proba returns [[prob_no_churn, prob_churn]] — we want the second value
        probability = model.predict_proba(input_df)[0][1]

        # Get risk level label
        risk_level = get_risk_level(probability)

        # Get plain English explanation from Groq AI (free)
        try:
            explanation = get_ai_explanation(data, probability, risk_level)
        except Exception as ai_error:
            print(f"Groq error (using fallback): {ai_error}")
            explanation = get_fallback_explanation(data, probability, risk_level)

        # Save to PostgreSQL (extract optional customer name first)
        customer_name = str(data.get('customer_name', '') or '').strip() or None
        save_prediction(data, probability, risk_level, explanation, customer_name)

        # Send the result back to Angular as JSON
        return jsonify({
            'churn_probability': round(probability * 100, 1),  # e.g. 0.734 → 73.4
            'risk_level': risk_level,                          # 'Low', 'Medium', or 'High'
            'explanation': explanation                         # GPT-generated text
        })

    except Exception as e:
        # If anything goes wrong, return the error message with a 500 status code
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# STEP 8: Health check endpoint
# ─────────────────────────────────────────────

# A simple GET endpoint to confirm the server is running
# Useful for Heroku and for testing in the browser

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


# ─────────────────────────────────────────────
# STEP 8c: Bulk prediction endpoint
# Accepts a CSV file, predicts churn for all rows
# ─────────────────────────────────────────────

@app.route('/predict/bulk', methods=['POST'])
def predict_bulk():
    try:
        file = request.files['file']
        df = pd.read_csv(file)

        # Drop columns that are not features (present in original dataset)
        df.drop(columns=[c for c in ['customerID', 'Churn'] if c in df.columns], inplace=True)

        # Fix TotalCharges — may have blank strings
        if 'TotalCharges' in df.columns:
            df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
            df.dropna(subset=['TotalCharges'], inplace=True)

        # Encode all text columns to numbers
        le = LabelEncoder()
        for col in df.select_dtypes(include='object').columns:
            df[col] = le.fit_transform(df[col].astype(str))

        # Keep only the 19 feature columns the model needs
        input_df = df[FEATURE_COLUMNS]

        # Run predictions on all rows at once
        probabilities = model.predict_proba(input_df)[:, 1]

        results = []
        for i, prob in enumerate(probabilities):
            probability = float(round(prob * 100, 1))
            risk_level  = get_risk_level(prob)
            results.append({
                'row':               i + 1,
                'churn_probability': probability,
                'risk_level':        risk_level,
            })

        return jsonify(results)

    except Exception as e:
        print(f"Bulk predict error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# STEP 8b: Prediction history endpoint
# ─────────────────────────────────────────────

@app.route('/history', methods=['GET'])
def history():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch last 50 predictions, newest first
        cur.execute("""
            SELECT id, customer_name, tenure, contract, monthly_charges, total_charges,
                   churn_probability, risk_level, explanation, created_at
            FROM predictions
            ORDER BY created_at DESC
            LIMIT 50
        """)

        rows = cur.fetchall()
        cur.close()
        conn.close()

        # Convert each row to a dictionary so jsonify can serialize it
        predictions = []
        for row in rows:
            predictions.append({
                'id':                row[0],
                'customer_name':     row[1],
                'tenure':            row[2],
                'contract':          row[3],
                'monthly_charges':   row[4],
                'total_charges':     row[5],
                'churn_probability': row[6],
                'risk_level':        row[7],
                'explanation':       row[8],
                'created_at':        row[9].strftime('%Y-%m-%d %H:%M:%S')
            })

        return jsonify(predictions)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# Delete a single prediction by ID
# ─────────────────────────────────────────────

@app.route('/history/<int:prediction_id>', methods=['DELETE'])
def delete_prediction(prediction_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM predictions WHERE id = %s", (prediction_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# Clear ALL predictions
# ─────────────────────────────────────────────

@app.route('/history', methods=['DELETE'])
def clear_history():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM predictions")
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
# STEP 9: Run the server
# ─────────────────────────────────────────────

# debug=True → auto-restarts the server when you save changes (development only)
# This block only runs when you execute app.py directly (not when Heroku imports it)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
