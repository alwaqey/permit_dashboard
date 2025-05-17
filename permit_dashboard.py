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

# If Days_Left not present, calculate once and don't repeat
if "Days_Left" not in df.columns:
    df["تاريخ الانتهاء"] = pd.to_datetime(df["تاريخ الانتهاء"], errors="coerce")
    df["Days_Left"] = (df["تاريخ الانتهاء"] - pd.Timestamp.today().normalize()).dt.days

# Twilio setup
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

# Streamlit UI
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
        days_left = (pd.to_datetime(exp_date) - pd.Timestamp.today().normalize()).days

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

        if days_left in [10, 30]:
            msg = (
                "🚨 تنبيه بخصوص تصريح دخول للمحمية:\n\n"
                f"📄 الاسم: {name}\n"
                f"🔢 رقم الطلب: {req_id}\n"
                f"📅 تاريخ الانتهاء: {exp_date.strftime('%Y-%m-%d')}\n"
                f"⏳ ينتهي خلال {days_left} {'أيام' if days_left == 10 else 'يوم'}\n"
                f"📞 رقم الجوال: {mobile}"
            )
            client.messages.create(from_=FROM_NUMBER, to=TO_NUMBER, body=msg)
            st.success(f"📤 تم إرسال تنبيه {days_left} يوم لتصريح {name}")

# Filter options
st.selectbox("📅 اختر عدد الأيام المتبقية", ["الكل", "10", "30", "120"], key="days_filter")

# Add display-only columns
df["عرض الأيام المتبقية"] = (pd.to_datetime(df["تاريخ الانتهاء"]) - pd.Timestamp.today().normalize()).dt.days
df["تاريخ الانتهاء للعرض"] = pd.to_datetime(df["تاريخ الانتهاء"]).dt.strftime('%Y-%m-%d')  # ✅ Strip time

# Filtered view
if st.session_state.days_filter != "الكل":
    days = int(st.session_state.days_filter)
    filtered_df = df[df["عرض الأيام المتبقية"] <= days]
else:
    filtered_df = df

# Display table (clean format)
st.dataframe(filtered_df[["الاسم", "رقم الطلب", "تاريخ الانتهاء للعرض", "عرض الأيام المتبقية", "رقم الجوال"]])

# Download clean version
if not filtered_df.empty:
    export_df = filtered_df.copy()
    export_df["تاريخ الانتهاء"] = pd.to_datetime(export_df["تاريخ الانتهاء"]).dt.strftime('%Y-%m-%d')  # ✅ Strip time for Excel
    export_file = "filtered_permits.xlsx"
    export_df.to_excel(export_file, index=False)
    with open(export_file, "rb") as f:
        st.download_button("📎 تحميل التصاريح المفلترة", f, file_name="التصاريح.xlsx")

# Save updates (Days_Left not recalculated again)
df.to_excel(FILE_PATH, index=False)
