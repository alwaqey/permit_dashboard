import pandas as pd
from datetime import datetime, timedelta
from twilio.rest import Client
import streamlit as st
import os

# Load Excel file
FILE_PATH = "names.xlsx"
if os.path.exists(FILE_PATH):
    df = pd.read_excel(FILE_PATH)
    df["رقم الطلب"] = df["رقم الطلب"].astype(str).str.replace(".0", "", regex=False)
else:
    st.error("❌ File not found. Please make sure 'names.xlsx' is in the same folder.")
    st.stop()

# Detect if running in Streamlit Cloud or locally
if st.secrets._secrets is not None and "TWILIO_SID" in st.secrets:
    ACCOUNT_SID = st.secrets["TWILIO_SID"]
    AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
    FROM_NUMBER = st.secrets["FROM_NUMBER"]
    TO_NUMBER = st.secrets["TO_NUMBER"]
else:
    from dotenv import load_dotenv
    load_dotenv()
    ACCOUNT_SID = os.getenv("TWILIO_SID")
    AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    FROM_NUMBER = os.getenv("FROM_NUMBER")
    TO_NUMBER = os.getenv("TO_NUMBER")

# Twilio client
client = Client(ACCOUNT_SID, AUTH_TOKEN)

# Format and cleanup
df["تاريخ الانتهاء"] = pd.to_datetime(df["تاريخ الانتهاء"], errors="coerce")
df["Days_Left"] = (df["تاريخ الانتهاء"] - pd.Timestamp.today().normalize()).dt.days
df["Notified_10"] = df.get("Notified_10", "No")
df["Notified_30"] = df.get("Notified_30", "No")

# WhatsApp alert function
def send_whatsapp_alert(row, level):
    msg = (
        f"🚨 تنبيه: التصريح رقم {row['رقم الطلب']} باسم {row['الاسم']} "
        f"ينتهي خلال {level} يوم.\n"
        f"📅 تاريخ الانتهاء: {row['تاريخ الانتهاء'].strftime('%Y-%m-%d')}\n"
        f"📱 رقم الجوال للتواصل: {row['رقم الجوال']}"
    )
    client.messages.create(
        from_=FROM_NUMBER,
        to=TO_NUMBER,
        body=msg
    )
    return "Yes"

# Streamlit interface
st.title("📋 لوحة متابعة التصاريح - مركز سامودة")

# Sidebar form
with st.sidebar.form("add_permit"):
    st.markdown("### ➕ إضافة تصريح جديد")
    name = st.text_input("👤 الاسم")
    req_id = st.text_input("🧾 رقم الطلب")
    mobile = st.text_input("📱 رقم الجوال (بدون +966)")
    exp_date = st.date_input("📅 تاريخ انتهاء التصريح")
    camels = st.text_input("🐪 عدد الماشية (اختياري)")
    submit = st.form_submit_button("✅ إضافة")
    if submit:
        new_row = {
            "الاسم": name,
            "رقم الطلب": req_id,
            "رقم الجوال": mobile,
            "تاريخ الانتهاء": pd.to_datetime(exp_date),
            "عدد الحوافز": camels if camels else "غير معروف",
            "CreatedOn": datetime.now(),
            "Days_Left": (pd.to_datetime(exp_date) - datetime.today()).days,
            "Notified_10": "No",
            "Notified_30": "No"
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

# Send alerts only if Days_Left == 10 or 30
for i, row in df.iterrows():
    if row["Days_Left"] == 10 and row["Notified_10"] == "No":
        df.at[i, "Notified_10"] = send_whatsapp_alert(row, 10)
        st.success(f"✅ تم إرسال تنبيه ١٠ أيام للتصريح: {row['الاسم']}")
    elif row["Days_Left"] == 30 and row["Notified_30"] == "No":
        df.at[i, "Notified_30"] = send_whatsapp_alert(row, 30)
        st.success(f"✅ تم إرسال تنبيه ٣٠ يوم للتصريح: {row['الاسم']}")

# Filter selector
st.selectbox("📅 اختر عدد الأيام المتبقية", ["الكل", "10", "30", "120"], key="days_filter")

# Apply filter
if st.session_state.days_filter != "الكل":
    days = int(st.session_state.days_filter)
    filtered_df = df[df["Days_Left"] <= days]
else:
    filtered_df = df

# Display table
st.dataframe(filtered_df[["الاسم", "رقم الطلب", "تاريخ الانتهاء", "Days_Left", "رقم الجوال"]])

# Download option
if not filtered_df.empty:
    export_file = "filtered_permits.xlsx"
    filtered_df.to_excel(export_file, index=False)
    with open(export_file, "rb") as f:
        st.download_button("📎 تحميل التصاريح المفلترة", f, file_name="التصاريح.xlsx")

# Save final updated Excel
df.to_excel(FILE_PATH, index=False)
