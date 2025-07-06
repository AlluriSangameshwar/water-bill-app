import streamlit as st
import requests
import json
import base64
from datetime import datetime, date

# ---------------- Configuration ----------------
GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
GITHUB_REPO = st.secrets["GITHUB_REPO"]
GITHUB_FOLDER = st.secrets["GITHUB_FOLDER"]

HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

# ---------------- GitHub Operations ----------------
def github_file_url(phone):
    return f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}/{phone}.json"

def fetch_bill_from_github(phone):
    url = github_file_url(phone)
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        content = response.json()["content"]
        return json.loads(base64.b64decode(content).decode())
    return None

def save_bill_to_github(phone, data):
    url = github_file_url(phone)
    content = json.dumps(data, indent=4)
    encoded = base64.b64encode(content.encode()).decode()

    get_resp = requests.get(url, headers=HEADERS)
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

    payload = {
        "message": f"Add/Update bill for {phone}",
        "content": encoded
    }
    if sha:
        payload["sha"] = sha

    put_resp = requests.put(url, headers=HEADERS, json=payload)
    if put_resp.status_code not in [200, 201]:
        st.error("GitHub Error:")
        st.code(put_resp.text)
    return put_resp.status_code in [200, 201]

def list_all_bills_from_github(month, year):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
    resp = requests.get(url, headers=HEADERS)

    results = []
    if resp.status_code == 200:
        for file in resp.json():
            if file["name"].endswith(".json"):
                bill_resp = requests.get(file["download_url"], headers=HEADERS)
                if bill_resp.status_code == 200:
                    try:
                        data = json.loads(bill_resp.content.decode())
                        for bill in data.get("bills", []):
                            ts = datetime.fromisoformat(bill["timestamp"])
                            if ts.month == month and ts.year == year:
                                results.append({
                                    "Phone": file["name"].replace(".json", ""),
                                    "Name": data["customer_name"],
                                    "Address": data["bill_to"],
                                    "Amount (\u20b9)": int(bill["amount"]),
                                    "Date": ts.strftime("%d-%m-%Y")
                                })
                    except Exception:
                        continue
    return results

# ---------------- Streamlit UI ----------------
st.set_page_config(page_title="Water Bill App", layout="centered")
st.title("Water Bill Manager")

mode = st.sidebar.radio("Select Mode", ["Add or Edit Bill", "Search by Phone", "Search by Month"])

if mode == "Add or Edit Bill":
    st.header("Add or Edit Water Bill")

    phone = st.text_input("Phone Number*", max_chars=10)
    customer_name = st.text_input("Customer Name")
    bill_to = st.text_input("Bill To (Address)")
    amount = st.number_input("Amount Paid (\u20b9)", min_value=0, step=1, format="%d")

    use_custom_date = st.checkbox("Select Custom Bill Date")
    bill_datetime = datetime.combine(st.date_input("Bill Date") if use_custom_date else date.today(),
                                     datetime.now().time())

    if st.button("Save Bill"):
        if phone and customer_name and bill_to:
            existing_data = fetch_bill_from_github(phone) or {
                "customer_name": customer_name,
                "bill_to": bill_to,
                "bills": []
            }

            existing_data["customer_name"] = customer_name
            existing_data["bill_to"] = bill_to
            existing_data["bills"].append({
                "amount": int(amount),
                "timestamp": bill_datetime.isoformat()
            })

            success = save_bill_to_github(phone, existing_data)
            if success:
                st.success(f"Bill saved for {bill_datetime.strftime('%d %B %Y')}!")
            else:
                st.error("Failed to save to GitHub.")
                st.code("Make sure token has repo/content access and the folder exists.")
        else:
            st.error("All fields are required!")

elif mode == "Search by Phone":
    st.header("Search Customer History")
    phone = st.text_input("Enter Phone Number")
    if phone:
        data = fetch_bill_from_github(phone)
        if data:
            st.subheader(f"Customer: {data['customer_name']}")
            st.write(f"Address: {data['bill_to']}")
            st.write("Bill History:")
            for bill in sorted(data["bills"], key=lambda x: x["timestamp"], reverse=True):
                ts = datetime.fromisoformat(bill["timestamp"])
                st.markdown(f"""
                - **Date:** {ts.strftime('%d %B %Y')}
                - **Amount Paid:** \u20b9{int(bill["amount"])}
                - Timestamp: {bill["timestamp"]}
                """)
        else:
            st.warning("No data found for this phone number.")

elif mode == "Search by Month":
    st.header("Search Bills for a Month")

    selected_month = st.selectbox("Select Month", range(1, 13),
                                  format_func=lambda x: datetime(2023, x, 1).strftime("%B"))
    selected_year = st.selectbox("Select Year", list(range(2020, datetime.now().year + 1))[::-1])

    if st.button("Search"):
        results = list_all_bills_from_github(selected_month, selected_year)
        if results:
            st.subheader(f"Bills for {datetime(2023, selected_month, 1).strftime('%B')} {selected_year}")
            st.table(results)
        else:
            st.info("No bills found for this month/year.")
