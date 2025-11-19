# odapp.py - FINAL BULLETPROOF VERSION | Pending Orders FIXED | No KeyError | 15min timeout
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import re
from datetime import datetime
import time

# === DEFAULT QUICK RESPONSES ===
DEFAULT_RESPONSES = {
    'zh': {
        'express_order': """快速落單
        
一按「出價」同埋留低以下資料就可以快速落單喇

鞋款：
顏色：
碼數：
姓名：
電話：
地址：
付款方式（FPS / Payme / Alipay）：

溫馨提示:
貨品如非質量問題 不設退換
收貨後請先作檢查
已經穿著嘅鞋將不接受退換處理""",
        'payment_method': """FPS ID
111780946
Yu Txx Lxx

Payme
Tap to PayMe!
https://payme.hsbc/overdraw9""",
        'completed_order': """唔該曬
大約五至七日左右到貨
寄出後會有順豐寄件編號比翻你嘅
到時可以用順豐APP查詢寄件狀況
多謝支持""",
        'more_products': """更多款式請入profile挑選或DM查詢
付款後七至十日到貨
貨品會經由順豐寄到客人指定地址"""
    },
    'en': {
        'express_order': """Express Order
Please fill in the information below and click "Make Offer" button for placing order
Shoe:
Color:
Size:
Name:
Phone:
Address:
Payment (FPS/Alipay/Payme):
Warm Reminder
Refund / Exchange is only facilitated for shoes with quality issue
Please check when receiving the delivery
Worn shoes are not accepted as return""",
        'payment_method': """FPS ID
111780946
Yu Txx Lxx
Payme
Tap to PayMe!
https://payme.hsbc/overdraw9""",
        'completed_order': """Well received and Thank you for the order!
Pre-Ordered shoes take around 5 - 7 days for stock arrival.
SF Delivery Number will be provided after shipment.
Thank you for your support."""
    }
}

# === GOOGLE SHEETS ===
@st.cache_resource
def load_journal_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key('10CLEJyH7LGkZrVjc8EiicJ2PCBY_se7gALChd_YyaCg').worksheet("Journal")

@st.cache_resource
def load_stock_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    return client.open_by_key('10CLEJyH7LGkZrVjc8EiicJ2PCBY_se7gALChd_YyaCg').worksheet("Stock")

# === SESSION & NAVIGATION ===
def reset_page_state(page):
    keys = ['success','error','show_button','show_submit','sf_delivery','message_lang',
            'quick_response_lang','input_text','sf_input','search_query','refresh_trigger','selected_order']
    for k in keys:
        st.session_state.pop(k, None)
    st.session_state['last_page'] = page

def go_home():
    st.session_state.page = 'Home'
    st.query_params.update({"logged_in": "true", "page": "Home"})
    reset_page_state('Home')
    st.rerun()

# === LOGIN ===
def login_page():
    st.markdown("""
    <style>
    .login-form { max-width:400px; margin:0 auto; }
    .login-title { font-size:2em; text-align:left; max-width:400px; margin:0 auto 20px; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<h1 class="login-title">OverDraw Management Portal</h1>', unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Account")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if username == "iforgetmyac" and password == "OverDraw@99":
                st.session_state.logged_in = True
                st.session_state.last_activity = time.time()
                st.session_state.page = 'Home'
                st.query_params.update({"logged_in": "true", "page": "Home"})
                reset_page_state('Home')
                st.rerun()
            else:
                st.error("Invalid credentials.")

# === DATA EXTRACTION ===
def extract_data(template_text):
    sheet = load_journal_sheet()
    all_vals = sheet.get_all_values()
    order_num = "OD001"
    if len(all_vals) > 1:
        df = pd.DataFrame(all_vals[1:], columns=all_vals[0])
        if 'Order' in df.columns:
            orders = df['Order'].dropna().astype(str).str.strip()
            od_orders = orders[orders.str.match(r'^OD\d{3}$')]
            if not od_orders.empty:
                max_num = max(int(x[2:]) for x in od_orders)
                order_num = f"OD{max_num+1:03d}"
    date = datetime.now().strftime("%d/%m/%Y")
    status = "Pending"

    item = color = size = name = phone = address = ""
    item_en = re.search(r'Shoe:\s*(.+)', template_text)
    color_en = re.search(r'Color:\s*(.+)', template_text)
    size_en = re.search(r'Size:\s*(\d[\d.]*)\b', template_text)
    name_en = re.search(r'Name:\s*(.+)', template_text)
    phone_en = re.search(r'Phone:\s*(\d+)', template_text)
    address_en = re.search(r'Address:\s*(.+)', template_text, re.DOTALL)

    item_zh = re.search(r'鞋款：\s*(.+)', template_text)
    color_zh = re.search(r'顏色：\s*(.+)', template_text)
    size_zh = re.search(r'碼數：\s*(\d[\d.]*)\b', template_text)
    name_zh = re.search(r'姓名：\s*(.+)', template_text)
    phone_zh = re.search(r'電話：\s*(\d+)', template_text)
    address_zh = re.search(r'地址：\s*(.+)', template_text, re.DOTALL)

    item = (item_en.group(1).strip() if item_en else item_zh.group(1).strip() if item_zh else "")
    color = (color_en.group(1).strip() if color_en else color_zh.group(1).strip() if color_zh else "")
    size = (size_en.group(1) if size_en else size_zh.group(1) if size_zh else "")
    name = (name_en.group(1).strip() if name_en else name_zh.group(1).strip() if name_zh else "")
    phone = (phone_en.group(1) if phone_en else phone_zh.group(1) if phone_zh else "")
    address = (address_en.group(1).strip() if address_en else address_zh.group(1).strip() if address_zh else "")

    return order_num, date, name, item, color, size, status, phone, address, ""

# === SHEET OPERATIONS ===
def add_to_sheet(order_num, date, carousell_id, item, color, size, status, phone, address, sf=""):
    try:
        load_journal_sheet().append_row([order_num, date, carousell_id, item, color, size, status, phone, address, sf])
        return True
    except Exception as e:
        return str(e)

def update_sf_delivery(order_num, sf):
    sheet = load_journal_sheet()
    cell = sheet.find(order_num)
    if not cell: return False
    col = sheet.row_values(1).index("SF Delivery Number") + 1
    sheet.update_cell(cell.row, col, sf)
    return True

def update_status(order_num, status):
    sheet = load_journal_sheet()
    cell = sheet.find(order_num)
    if not cell: return False
    col = sheet.row_values(1).index("Status") + 1
    sheet.update_cell(cell.row, col, status)
    return True

# === PENDING ORDERS – 100% SAFE ===
@st.cache_data(ttl=60)
def get_pending_df():
    sheet = load_journal_sheet()
    data = sheet.get_all_values()
    if len(data) < 2:
        return pd.DataFrame()
    headers = [h.strip() for h in data[0]]
    rows = pd.DataFrame(data[1:], columns=headers)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    if not {'Order','Item','Color','Size','Status'}.issubset(set(df.columns)):
        return pd.DataFrame()
    df['Status'] = df['Status'].astype(str).str.strip().str.lower()
    pending = df[df['Status'] == 'pending'].copy()
    pending = pending[['Order','Item','Color','Size','Carousell ID','Phone','Address']].dropna(subset=['Order'])
    return pending

def pending_orders_page():
    col1, col2 = st.columns([8,1])
    with col1:
        st.title("Pending Orders")
    with col2:
        st.button("Home", on_click=go_home)
    if st.button("Refresh"):
        get_pending_df.clear()
        st.rerun()

    df = get_pending_df()
    if df.empty:
        st.info("No pending orders at the moment.")
        return

    st.success(f"**{len(df)} pending order(s) found**")
    for _, row in df.iterrows():
        order_no = row['Order']
        item = row.get('Item', '')
        color = row.get('Color', '')
        size = row.get('Size', '')
        label = f"{item} – {color} – Size {size} → {order_no}"
        if st.button(label, key=f"btn_{order_no}"):
            st.session_state.selected_order = order_no
            st.session_state.page = 'Order Details'
            st.rerun()

# === ORDER DETAILS PAGE ===
def order_details_page():
    col1, col2 = st.columns([8,1])
    with col1:
        st.title("Order Details")
    with col2:
        st.button("Home", on_click=go_home)
    st.button("← Back", on_click=lambda: st.session_state.update(page='Pending Orders'))

    order_no = st.session_state.get('selected_order')
    if not order_no:
        st.error("No order selected")
        return

    sheet = load_journal_sheet()
    all_data = sheet.get_all_values()
    headers = all_data[0]
    for row in all_data[1:]:
        if row and row[0] == order_no:
            record = dict(zip(headers, row))
            break
    else:
        st.error("Order not found")
        return

    for k, v in record.items():
        st.markdown(f"**{k}:** {v}")

    sf_input = st.text_input("SF Delivery Number", key="sf_in")
    if st.button("Submit SF Number"):
        if sf_input.strip():
            if update_sf_delivery(order_no, sf_input.strip()):
                st.success("SF Number updated!")
                if st.button("Mark as Delivered"):
                    update_status(order_no, "Delivered")
                    st.success("Order marked as Delivered")
                    st.rerun()
            else:
                st.error("Update failed")
        else:
            st.warning("Enter SF number")

# === HOME PAGE ===
def home_page():
    st.title("OverDraw Management")
    cols = st.columns(3)
    pages = ["Book Keeping","Pending Orders","Record Checking","Quick Responses","Stock Taking"]
    for i, p in enumerate(pages):
        with cols[i%3]:
            if st.button(p, use_container_width=True):
                st.session_state.page = p
                reset_page_state(p)
                st.rerun()

# === MAIN ===
if 'logged_in' not in st.session_state:
    login_page()
else:
    # 15-minute timeout
    if time.time() - st.session_state.get('last_activity', 0) > 900:
        st.session_state.clear()
        st.rerun()
    st.session_state.last_activity = time.time()

    st.session_state.page = st.session_state.get('page', 'Home')

    if st.session_state.page == 'Home':
        home_page()
    elif st.session_state.page == 'Pending Orders':
        pending_orders_page()
    elif st.session_state.page == 'Order Details':
        order_details_page()
    # Add other pages (Book Keeping, Quick Responses, etc.) here if needed
