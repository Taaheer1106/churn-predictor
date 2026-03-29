# Customer Churn Predictor

An end-to-end Machine Learning web application that predicts telecom customer churn using Random Forest / Gradient Boosting, a Flask REST API, Groq AI explanations, and an Angular frontend.

---

## Features

- **Churn Prediction** — Enter customer details and get an instant churn probability score
- **AI Explanation** — Groq AI (Llama 3.1) explains *why* the customer might churn in plain English
- **Prediction History** — Every prediction is saved to PostgreSQL and viewable in a history table
- **Bulk CSV Prediction** — Upload a CSV with multiple customers and get results for all rows at once
- **PDF Report** — Download a professional PDF report for any prediction
- **Dark Mode** — Full dark/light theme toggle with localStorage persistence

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| ML Model | scikit-learn (Random Forest + Gradient Boosting) |
| AI Explanation | Groq API (llama-3.1-8b-instant) |
| Backend | Python + Flask + psycopg2 |
| Database | PostgreSQL |
| Frontend | Angular 21 + Angular Material |
| PDF Export | jsPDF |

---

## Model Performance

Both models are trained and compared automatically — the best one is saved:

| Model | Accuracy | AUC-ROC |
|-------|----------|---------|
| Random Forest | ~0.79 | ~0.83 |
| Gradient Boosting | ~0.80 | ~0.85 |

**Dataset**: IBM Telco Customer Churn — 7,032 customers, 19 features

---

## Project Structure

```
churn-predictor/
├── backend/
│   ├── app.py              # Flask API (predict, history, bulk)
│   ├── model.py            # Train & compare ML models
│   ├── churn_model.pkl     # Saved best model (generated)
│   ├── requirements.txt    # Python dependencies
│   └── .env                # API keys & DB URL (not committed)
├── frontend/
│   └── churn-app/          # Angular application
└── WA_Fn-UseC_-Telco-Customer-Churn.csv
```

---

## Setup & Run

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd churn-predictor
```

### 2. Set up the backend

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file:

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/churn_db
```

Get a free Groq API key at [console.groq.com](https://console.groq.com)

### 3. Set up PostgreSQL

```sql
CREATE DATABASE churn_db;

\c churn_db

CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    tenure INTEGER,
    contract INTEGER,
    monthly_charges FLOAT,
    total_charges FLOAT,
    churn_probability FLOAT,
    risk_level VARCHAR(10),
    explanation TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 4. Train the model

```bash
cd backend
python model.py
```

This trains both Random Forest and Gradient Boosting, compares them, and saves the best one as `churn_model.pkl`.

### 5. Start the Flask API

```bash
python app.py
```

API runs on `http://localhost:5000`

### 6. Start the Angular frontend

```bash
cd frontend/churn-app
npm install
ng serve
```

App runs on `http://localhost:4200`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predict` | Predict churn for one customer |
| GET | `/history` | Get last 50 predictions |
| POST | `/predict/bulk` | Predict churn from CSV file |
| GET | `/health` | Health check |

---

## How It Works

1. User fills in 19 customer features (demographics, services, billing)
2. Angular sends a POST request to Flask `/predict`
3. Flask validates the input, runs the ML model, gets a churn probability
4. Groq AI generates a plain-English explanation
5. Result is saved to PostgreSQL and returned to the frontend
6. Angular displays the probability gauge, risk level, and AI explanation

---

## Acknowledgements

- Dataset: [IBM Sample Data — Telco Customer Churn](https://www.kaggle.com/datasets/blastchar/telco-customer-churn)
- AI Explanations: [Groq](https://groq.com) (free LLM API)
