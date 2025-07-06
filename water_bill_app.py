import os
import json
import streamlit as st
from datetime import datetime
from pathlib import Path

# ---------------- Configuration ----------------
DATA_DIR = "data/bills"
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

# ---------------- Helper Functions ----------------

def get_file_path(phone):
    return os.path.join(DATA_DIR, f"{phone}.json")

def load_bill(phone):
    path = get_file_path(phone)
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None

def save_bill(phone, customer_name, bill_to, new_bill):
    path = get_file_path(phone)
    data = load_bill(phone)

    if data:
        data["customer_name"] = customer_name
        data["bill_to"] = bill_to
        data["bills"].append(new_bill)
    else:
        data = {
            "customer_name": customer_name,
            "bill_to": bill_to,
            "bills": [new_bill]
        }

    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def list_all_bills_for_month(month, year):
    results = []
    for file in os.listdir(DATA_DIR):
        if file.endswith(".json"):
            path = os.path.join(DATA_DIR, file)
            with open(path, "r") as f:
                data = json.load(f)
                for bill in data.get("bills", []):
                    ts = datetime.fromisoformat(bill["timestamp"])
                    if ts.month == month and ts.year == year:
                        results.append({
                            "phone": file.replace(".json", ""),
                            "name": data["customer_name"],
                            "bill_to": data["bill_to"],
                            "amount": bill["amount"],
                            "timestamp": bill["timestamp"]
                        })
    return results

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Water Bill App", layout="centered")
st.title("💧 Water Bill Manager")

mode = st.sidebar.radio("Select Mode", ["➕ Add or Edit Bill", "🔍 Search by Phone", "📅 Search by Month"])

# ---------------- Add or Edit Bill ----------------
if mode == "➕ Add or Edit Bill":
    st.header("➕ Add or Edit Water Bill")

    phone = st.text_input("Phone Number*", max_chars=10)
    customer_name = st.text_input("Customer Name")
    bill_to = st.text_input("Bill To (Address)")
    amount = st.number_input("Amount Paid (₹)", min_value=0.0)

    if st.button("💾 Save Bill"):
        if phone and customer_name and bill_to:
            bill = {
                "amount": amount,
                "timestamp": datetime.now().isoformat()
            }
            save_bill(phone, customer_name, bill_to, bill)
            st.success("✅ Bill saved successfully!")
        else:
            st.error("❗ All fields are required!")

# ---------------- Search by Phone ----------------
elif mode == "🔍 Search by Phone":
    st.header("🔍 Search Customer History")
    phone = st.text_input("Enter Phone Number")
    if phone:
        data = load_bill(phone)
        if data:
            st.subheader(f"Customer: {data['customer_name']}")
            st.write(f"📍 Address: {data['bill_to']}")
            st.write("📜 Bill History:")
            for bill in sorted(data["bills"], key=lambda x: x["timestamp"], reverse=True):
                dt = datetime.fromisoformat(bill["timestamp"])
                st.markdown(f"""
                - **Date:** {dt.strftime("%d %B %Y")}
                - **Amount:** ₹{bill["amount"]}
                - ⏱️ {bill["timestamp"]}
                """)
        else:
            st.warning("❌ No data found for this phone number.")

# ---------------- Search by Month ----------------
elif mode == "📅 Search by Month":
    st.header("📅 Search Bills for a Month")

    selected_month = st.selectbox("Select Month", range(1, 13), format_func=lambda x: datetime(2023, x, 1).strftime("%B"))
    selected_year = st.selectbox("Select Year", list(range(2020, datetime.now().year + 1))[::-1])

    if st.button("🔍 Search"):
        results = list_all_bills_for_month(selected_month, selected_year)
        if results:
            st.subheader(f"📋 Bills for {datetime(2023, selected_month, 1).strftime('%B')} {selected_year}")
            st.table(results)
        else:
            st.info("ℹ️ No bills found for this month/year.")
