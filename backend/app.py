from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import pickle
import pandas as pd
import os
from openai import OpenAI
from groq import Groq
import psycopg2
from sklearn.preprocessing import LabelEncoder

load_dotenv()

app = Flask(__name__)
CORS(app, origins=["https://glowing-conkies-f6c9b6.netlify.app", "http://localhost:4200"])

FEATURE_COLUMNS = [
    'gender', 'SeniorCitizen', 'Partner', 'Dependents', 'tenure',
    'PhoneService', 'MultipleLines', 'InternetService', 'OnlineSecurity',
    'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV',
    'StreamingMovies', 'Contract', 'PaperlessBilling', 'PaymentMethod',
    'MonthlyCharges', 'TotalCharges'
]

MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'churn_model.pkl')
with open(MODEL_PATH, 'rb') as f:
    model = pickle.load(f)
print("Model loaded.")


def get_db_connection():
    return psycopg2.connect(os.getenv('DATABASE_URL'))


def get_risk_level(probability):
    if probability < 0.4:
        return 'Low'
    elif probability < 0.7:
        return 'Medium'
    return 'High'


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
    return (f"This customer has a low churn risk of {probability:.0%}. "
            f"With {tenure} months of tenure and a {contract_label} contract, "
            f"they appear satisfied. Continue providing consistent service quality.")


def get_ai_explanation(customer_data, probability, risk_level):
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
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
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()


def validate_input(data):
    errors = []
    for col in FEATURE_COLUMNS:
        if col not in data or data[col] == '' or data[col] is None:
            errors.append(f"Missing field: {col}")

    for field in ['tenure', 'MonthlyCharges', 'TotalCharges']:
        if field in data:
            try:
                val = float(data[field])
                if val < 0:
                    errors.append(f"{field} cannot be negative")
            except (ValueError, TypeError):
                errors.append(f"{field} must be a number")

    if 'tenure' in data:
        try:
            if float(data['tenure']) != int(float(data['tenure'])):
                errors.append("tenure must be a whole number (months)")
        except (ValueError, TypeError):
            pass

    return errors


def save_prediction(data, probability, risk_level, explanation, customer_name=None, user_id=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO predictions
                (customer_name, tenure, contract, monthly_charges, total_charges,
                 churn_probability, risk_level, explanation, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            customer_name,
            int(data.get('tenure')),
            int(data.get('Contract')),
            float(data.get('MonthlyCharges')),
            float(data.get('TotalCharges')),
            float(round(probability * 100, 1)),
            risk_level,
            explanation,
            user_id
        ))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")


@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        errors = validate_input(data)
        if errors:
            return jsonify({'error': 'Validation failed', 'details': errors}), 400

        input_df = pd.DataFrame([data], columns=FEATURE_COLUMNS)
        probability = model.predict_proba(input_df)[0][1]
        risk_level = get_risk_level(probability)

        try:
            explanation = get_ai_explanation(data, probability, risk_level)
        except Exception as ai_error:
            print(f"Groq error: {ai_error}")
            explanation = get_fallback_explanation(data, probability, risk_level)

        customer_name = str(data.get('customer_name', '') or '').strip() or None
        user_id = str(data.get('user_id', '') or '').strip() or None
        save_prediction(data, probability, risk_level, explanation, customer_name, user_id)

        return jsonify({
            'churn_probability': round(probability * 100, 1),
            'risk_level': risk_level,
            'explanation': explanation
        })

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/predict/bulk', methods=['POST'])
def predict_bulk():
    try:
        file = request.files['file']
        df = pd.read_csv(file)

        df.drop(columns=[c for c in ['customerID', 'Churn'] if c in df.columns], inplace=True)

        if 'TotalCharges' in df.columns:
            df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
            df.dropna(subset=['TotalCharges'], inplace=True)

        le = LabelEncoder()
        for col in df.select_dtypes(include='object').columns:
            df[col] = le.fit_transform(df[col].astype(str))

        input_df = df[FEATURE_COLUMNS]
        probabilities = model.predict_proba(input_df)[:, 1]

        results = []
        for i, prob in enumerate(probabilities):
            results.append({
                'row': i + 1,
                'churn_probability': float(round(prob * 100, 1)),
                'risk_level': get_risk_level(prob),
            })

        return jsonify(results)

    except Exception as e:
        print(f"Bulk predict error: {e}")
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['GET'])
def history():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        user_id = request.args.get('user_id')
        if user_id:
            cur.execute("""
                SELECT id, customer_name, tenure, contract, monthly_charges, total_charges,
                       churn_probability, risk_level, explanation, created_at
                FROM predictions
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id,))
        else:
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


@app.route('/history/<int:prediction_id>', methods=['DELETE'])
def delete_prediction(prediction_id):
    try:
        user_id = request.args.get('user_id')
        conn = get_db_connection()
        cur = conn.cursor()
        if user_id:
            cur.execute("DELETE FROM predictions WHERE id = %s AND user_id = %s", (prediction_id, user_id))
        else:
            cur.execute("DELETE FROM predictions WHERE id = %s", (prediction_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/history', methods=['DELETE'])
def clear_history():
    try:
        user_id = request.args.get('user_id')
        conn = get_db_connection()
        cur = conn.cursor()
        if user_id:
            cur.execute("DELETE FROM predictions WHERE user_id = %s", (user_id,))
        else:
            cur.execute("DELETE FROM predictions")
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
