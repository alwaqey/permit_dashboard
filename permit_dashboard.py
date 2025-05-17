import pandas as pd
from datetime import datetime
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

# If Days_Left is not already in the file, calculate it once
if "Days_Left" not in df.columns:
    df["تاريخ الانتهاء"] = pd.to_datetime(df["تاريخ الانتهاء"], errors="coerce")
    df["Days_Left"] = (df["تاريخ الانتهاء"] - pd.Timestamp.today().normalize()).dt.days

# Twilio config
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

client = Client(ACCOUNT_SID, AUTH_TOKEN)

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
        days_left = (pd.to_datetime(exp_date) - datetime.today()).days

        new_row = {
            "الاسم": name,
            "رقم الطلب": req_id,
            "رقم الجوال": mobile,
            "تاريخ الانتهاء": pd.to_datetime(exp_date),
            "عدد الحوافز": camels if camels else "غير معروف",
            "CreatedOn": datetime.now(),
            "Days_Left": days_left,
            "Notified_10": "Yes" if days_left == 10 else "No",
            "Notified_30": "Yes" if days_left == 30 else "No"
        }

        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # ✅ Send WhatsApp alert only for the new permit
        if days_left in [10, 30]:
            msg = (
                f"🚨 تنبيه بخصوص تصريح\n"
                f"التصريح رقم: {req_id}\n"
                f"الاسم: {name}\n"
                f"تبقّى عليه {days_left} {'أيام' if days_left == 10 else 'يوم'}\n"
                f"📅 تاريخ الانتهاء: {exp_date.strftime('%Y-%m-%d')}\n"
                f"📞 رقم الجوال: {mobile}"
            )
            client.messages.create(from_=FROM_NUMBER, to=TO_NUMBER, body=msg)
            st.success(f"📤 تم إرسال تنبيه {days_left} يوم لتصريح {name}")

# Filter selector
st.selectbox("📅 اختر عدد الأيام المتبقية", ["الكل", "10", "30", "120"], key="days_filter")

# Live Days_Left column for display only
df["عرض الأيام المتبقية"] = (df["تاريخ الانتهاء"] - pd.Timestamp.today().normalize()).dt.days

# Apply filter
if st.session_state.days_filter != "الكل":
    days = int(st.session_state.days_filter)
    filtered_df = df[df["عرض الأيام المتبقية"] <= days]
else:
    filtered_df = df

# Display table
st.dataframe(filtered_df[["الاسم", "رقم الطلب", "تاريخ الانتهاء", "عرض الأيام المتبقية", "رقم الجوال"]])

# Download option
if not filtered_df.empty:
    export_file = "filtered_permits.xlsx"
    filtered_df.to_excel(export_file, index=False)
    with open(export_file, "rb") as f:
        st.download_button("📎 تحميل التصاريح المفلترة", f, file_name="التصاريح.xlsx")

# Save final file (DO NOT recalculate Days_Left to avoid repeat alerts)
df.to_excel(FILE_PATH, index=False)
