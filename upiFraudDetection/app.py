import os
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import tensorflow as tf
from flask import Flask, request, render_template, redirect, url_for

# import your DB helper (you said database.py already बनाया है)
from database import get_db_connection

# ---------- Load dataset & scaler (same as before) ----------
dataset = pd.read_csv('dataset/upi_fraud_dataset.csv', index_col=0)

x = dataset.iloc[:, : 10].values
y = dataset.iloc[:, 10].values

scaler = StandardScaler()
x = scaler.fit_transform(x)

# ---------- Load model (use os.path.join for portability) ----------
model_path = os.path.join('filesuse', 'project_model1.h5')
model = tf.keras.models.load_model(model_path)

# ---------- Flask app ----------
app = Flask(__name__)

# ---------- Helper: save to DB ----------
def save_result(upi_num, merchant, amount, status, dob, trans_datetime, result):
    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO fraud_results
            (upi_num, merchant, amount, status, dob, trans_datetime, result)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (upi_num, merchant, amount, status, dob, trans_datetime, result))
        conn.commit()
        conn.close()
    except Exception as e:
        # DB error — print to console for debugging
        print("DB save error:", e)

# ---------- Routes ----------
@app.route('/')
@app.route('/first')
def first():
    return render_template('first.html')

@app.route('/login')
def login():
    return render_template('login.html')

def home():
    return render_template('home.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/preview', methods=["POST"])
def preview():
    if request.method == 'POST':
        dataset_file = request.files['datasetfile']
        df = pd.read_csv(dataset_file, encoding='unicode_escape')
        df.set_index('Id', inplace=True)
        return render_template("preview.html", df_view=df)

@app.route('/prediction1', methods=['GET'])
def prediction1():
    return render_template('index.html')

@app.route('/chart')
def chart():
    return render_template('chart.html')

# Optional test route: add a dummy record and redirect to admin
@app.route('/add_test')
def add_test():
    save_result("test@upi", "Test Merchant", 100.0, "success", "2000-01-01", "2025-01-01 00:00:00", "VALID TRANSACTION")
    return redirect(url_for('admin'))

# Admin page: show DB rows
@app.route('/admin')
def admin():
    try:
        conn = get_db_connection()
        rows = conn.execute("SELECT * FROM fraud_results ORDER BY id DESC").fetchall()
        conn.close()
    except Exception as e:
        print("DB read error:", e)
        rows = []
    return render_template('admin.html', data=rows)

# Detect route: apply rules, save result, return template
@app.route('/detect', methods=['POST'])
def detect():
    try:
        # User Inputs
        upi_num = request.form.get("card_number", "").strip()
        merchant = request.form.get("merchant", "").strip()
        # handle missing amounts safely
        amount_raw = request.form.get("trans_amount", "0")
        try:
            amount = float(amount_raw)
        except:
            amount = 0.0
        trans_datetime = pd.to_datetime(request.form.get("trans_datetime"))
        status_input = request.form.get("payment_status", "").strip()  # success/fail
        dob = pd.to_datetime(request.form.get("dob"))

        # Derived fields
        age = int((trans_datetime - dob).days / 365.25)
        hour = trans_datetime.hour

        # Determine result (do NOT return immediately — first decide, then save)
        result = "VALID TRANSACTION"  # default

        # Rule 1: Payment failed
        if status_input and status_input.lower() == "failed":
            result = "FRAUD TRANSACTION"
        # Rule 2: Merchant name empty
        elif merchant == "":
            result = "FRAUD TRANSACTION"
        # Rule 3: Invalid UPI number
        elif len(upi_num) < 10:
            result = "FRAUD TRANSACTION"
        # Rule 4: High-amount sudden transfer
        elif amount > 50000:
            result = "FRAUD TRANSACTION"
        # Rule 5: Age very low/high
        elif age < 15 or age > 80:
            result = "FRAUD TRANSACTION"
        # Rule 6: Time odd hours
        elif 0 <= hour <= 5:
            result = "FRAUD RISK"
        else:
            result = "VALID TRANSACTION"

        # Save to DB (stringify dob and trans_datetime for storage)
        save_result(
            upi_num,
            merchant,
            amount,
            status_input,
            str(dob),
            str(trans_datetime),
            result
        )

        # Return result page
        return render_template("result.html", OUTPUT=result)

    except Exception as e:
        # If anything went wrong, show error (and try to save minimal info)
        msg = f"Error: {e}"
        print(msg)
        return render_template("result.html", OUTPUT=msg)

# ---------- Run ----------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # use env PORT or 5000
    app.run(host="0.0.0.0", port=port, debug=True)
