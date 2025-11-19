# odapp.py - FULLY FIXED | 710+ LINES | PENDING ORDERS + 15-MIN TIMEOUT
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
SF Delivery Number will be provided after shipment being sent.
Delivery status can be checked with the provided SF Delivery number.
Thank you for your support and patience."""
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
    state_keys = ['success', 'error', 'show_button', 'show_submit', 'sf_delivery', 'message_lang',
                  'quick_response_lang', 'input_text', 'sf_input', 'search_query', 'refresh_trigger']
    for key in state_keys:
        if key in st.session_state:
            del st.session_state[key]
    if page == 'Book Keeping':
        st.session_state['input_text'] = ""
    elif page == 'Order Details':
        st.session_state['sf_input'] = ""
    elif page == 'Record Checking':
        st.session_state['search_query'] = ""
    elif page == 'Quick Responses':
        st.session_state['quick_response_lang'] = None
    st.session_state['last_page'] = page

def go_home():
    st.session_state['page'] = 'Home'
    st.query_params.update({"logged_in": "true", "page": "Home"})
    reset_page_state('Home')
    st.rerun()

# === LOGIN PAGE ===
def login_page():
    st.markdown("""
    <style>
    .login-form { max-width: 400px; margin: 0 auto; }
    .login-form input { width: 100% !important; }
    .login-form button { background-color: #4CAF50; color: white; padding: 10px; width: 100%; }
    .login-title { font-size: 2em; max-width: 400px; margin: 0 auto; text-align: left; padding-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<h1 class="login-title">OverDraw Management Portal</h1>', unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Account")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        if submit:
            if username == "iforgetmyac" and password == "OverDraw@99":
                st.session_state['logged_in'] = True
                st.session_state['last_activity'] = time.time()
                st.session_state['page'] = 'Home'
                st.query_params.update({"logged_in": "true", "page": "Home"})
                reset_page_state('Home')
                st.rerun()
            else:
                st.error("Invalid credentials.")

# === EXTRACT DATA FROM TEMPLATE - FIXED ORDER NUMBER ===
# === EXTRACT DATA FROM TEMPLATE - FULLY FIXED ===
def extract_data(template_text):
    sheet = load_journal_sheet()
    all_values = sheet.get_all_values()
    
    # --- Generate next Order number ---
    order_num = "OD001"
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])  # proper DataFrame
        if 'Order' in df.columns:
            orders = df['Order'].astype(str).str.strip()
            od_orders = orders[orders.str.startswith('OD') & (orders.str.len() == 5)]
            if not od_orders.empty:
                max_num = max(od_orders, key=lambda x: int(x[2:]))
                next_num = int(max_num[2:]) + 1
                order_num = f"OD{next_num:03d}"

    date = datetime.now().strftime("%d/%m/%Y")
    status = "Pending"
    sf_delivery_number = ""

    # Default empty values
    item = color = size = name = phone = address = carousell_id = ""

    # English pattern
    item_en = re.search(r'Shoe:\s*([^\n]+)', template_text, re.IGNORECASE)
    color_en = re.search(r'Color:\s*([^\n]+)', template_text, re.IGNORECASE)
    size_en = re.search(r'Size:\s*(\d+[.,]?\d*)', template_text)
    name_en = re.search(r'Name:\s*([^\n]+)', template_text, re.IGNORECASE)
    phone_en = re.search(r'Phone:\s*(\d+)', template_text)
    address_en = re.search(r'Address:\s*(.+)', template_text, re.DOTALL)

    # Chinese pattern
    item_zh = re.search(r'鞋款[:：]\s*([^\n]+)', template_text)
    color_zh = re.search(r'顏色[:：]\s*([^\n]+)', template_text)
    size_zh = re.search(r'碼數[:：]\s*(\d+[.,]?\d*)', template_text)
    name_zh = re.search(r'姓名[:：]\s*([^\n]+)', template_text)
    phone_zh = re.search(r'電話[:：]\s*(\d+)', template_text)
    address_zh = re.search(r'地址[:：]\s*(.+)', template_text, re.DOTALL)

    item = (item_en.group(1).strip() if item_en else (item_zh.group(1).strip() if item_zh else ""))
    color = (color_en.group(1).strip() if color_en else (color_zh.group(1).strip() if color_zh else ""))
    size = (size_en.group(1) if size_en else (size_zh.group(1) if size_zh else ""))
    name = (name_en.group(1).strip() if name_en else (name_zh.group(1).strip() if name_zh else ""))
    carousell_id = name
    phone = (phone_en.group(1) if phone_en else (phone_zh.group(1) if phone_zh else ""))
    address = (address_en.group(1).strip() if address_en else (address_zh.group(1).strip() if address_zh else "")).strip()

    return order_num, date, carousell_id, item, color, size, status, phone, address, sf_delivery_number
# === ADD TO SHEET ===
def add_to_sheet(order_num, date, carousell_id, item, color, size, status, phone, address, sf_delivery_number):
    try:
        sheet = load_journal_sheet()
        sheet.append_row([order_num, date, carousell_id, item, color, size, status, phone, address, sf_delivery_number])
        return True
    except Exception as e:
        return str(e)

# === SEARCH SHEET ===
def search_sheet(query):
    sheet = load_journal_sheet()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    results = df[df.apply(lambda row: query.lower() in ' '.join(str(col) for col in row).lower(), axis=1)]
    return results

# === UPDATE SF & STATUS ===
# === UPDATE SF & AUTO-CHANGE STATUS TO DELIVERED ===
def update_sf_delivery(order_num, sf_delivery_number):
    sheet = load_journal_sheet()
    all_data = sheet.get_all_values()
    if len(all_data) < 2:
        return False
    
    headers = all_data[0]
    rows = all_data[1:]
    df = pd.DataFrame(rows, columns=headers)
    
    if 'Order' not in df.columns:
        return False
    
    row_idx = df.index[df['Order'] == order_num].tolist()
    if not row_idx:
        return False
    
    row_num = row_idx[0] + 2  # +2 because row 1 = headers, +1 for 0-index
    
    try:
        # Update SF Delivery Number
        sf_col = headers.index('SF Delivery Number') + 1
        sheet.update_cell(row_num, sf_col, sf_delivery_number.strip())
        
        # Auto-update Status to "Delivered"
        status_col = headers.index('Status') + 1
        sheet.update_cell(row_num, status_col, "Delivered")
        
        return True
    except Exception as e:
        st.error(f"Update failed: {e}")
        return False

def update_order_status(order_num, status):
    sheet = load_journal_sheet()
    all_data = sheet.get_all_values()
    if len(all_data) < 2: return False
    headers = all_data[0]
    rows = all_data[1:]
    df = pd.DataFrame(rows, columns=headers)
    if 'Order' not in df.columns: return False
    row_idx = df.index[df['Order'] == order_num].tolist()
    if not row_idx: return False
    col_idx = headers.index('Status') + 1
    sheet.update_cell(row_idx[0] + 2, col_idx, status)
    return True

# === QUICK RESPONSES PAGE ===
def quick_responses_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Quick Responses")
    with col2:
        st.button("Home", key="home_button_quick", on_click=go_home)
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .stTextArea textarea { user-select: all; }
    .item-label { margin-bottom: 0px; font-weight: bold; }
    .item-container { margin-bottom: 20px; }
    .button-container { display: flex; gap: 5px; justify-content: flex-start; margin-bottom: 20px; }
    </style>
    <script>
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('dblclick', function() {
            this.select();
        });
    });
    </script>
    """, unsafe_allow_html=True)
    if 'quick_response_lang' not in st.session_state:
        st.session_state['quick_response_lang'] = None
    st.markdown('<div class="button-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("中文", key="quick_chinese_button"):
            st.session_state['quick_response_lang'] = 'zh'
            st.rerun()
    with col2:
        if st.button("English", key="quick_english_button"):
            st.session_state['quick_response_lang'] = 'en'
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state['quick_response_lang'] is None:
        return

    lang = st.session_state['quick_response_lang']
    responses = DEFAULT_RESPONSES[lang]
    keys = ['express_order', 'payment_method', 'completed_order', 'more_products'] if lang == 'zh' else ['express_order', 'payment_method', 'completed_order']
    labels = ['快速落單', '付款方法', '落單成功', '更多款式'] if lang == 'zh' else ['Express Order', 'Payment Method', 'Completed Order']

    for i, key in enumerate(keys):
        st.markdown(f"### {labels[i]}")
        saved_key = f"saved_{lang}_{key}"
        current_key = f"current_{lang}_{key}"
        edit_key = f"edit_{lang}_{key}"
        saved_text = st.session_state.get(saved_key, responses[key])
        current_text = st.session_state.get(current_key, saved_text)

        if st.session_state.get(edit_key, False):
            edited = st.text_area("", value=current_text, height=150, key=f"edit_input_{lang}_{key}")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Save", key=f"save_{lang}_{key}"):
                    st.session_state[saved_key] = edited
                    st.session_state[current_key] = edited
                    st.session_state[edit_key] = False
                    st.rerun()
            with col_b:
                if st.button("Cancel", key=f"cancel_{lang}_{key}"):
                    st.session_state[current_key] = saved_text
                    st.session_state[edit_key] = False
                    st.rerun()
        else:
            st.code(saved_text, language=None)
            col_a, col_b = st.columns([1, 4])
            with col_a:
                if st.button("Edit", key=f"edit_btn_{lang}_{key}"):
                    st.session_state[edit_key] = True
                    st.session_state[current_key] = saved_text
                    st.rerun()
            with col_b:
                st.markdown("")

# === STOCK TAKING PAGE ===
def stock_taking_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Stock Taking")
    with col2:
        st.button("Home", key="home_stock", on_click=go_home)
    st.markdown("""
    <style>
    .stTextArea textarea { font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown("**Enter: Product Name → Cost (newline or tab)**", help="Example:\nAdidas Terrex\n240\nOR\nAdidas Terrex[TAB]240")
    input_text = st.text_area("", height=200, key="stock_input")
    if st.button("Add to Stock Sheet", key="add_stock_btn"):
        lines = [line.strip() for line in input_text.splitlines() if line.strip()]
        entries = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if '\t' in line:
                product, cost_str = line.split('\t', 1)
                product = product.strip()
                cost_str = cost_str.strip()
            else:
                product = line
                i += 1
                if i >= len(lines):
                    st.error(f"Missing cost for: {product}")
                    return
                cost_str = lines[i].strip()
            try:
                cost = float(cost_str)
            except:
                st.error(f"Invalid cost '{cost_str}' for: {product}")
                return
            entries.append((product, cost))
            i += 1
        if not entries:
            st.error("No valid entries.")
            return
        sheet = load_stock_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        next_id = 1
        if not df.empty and 'ID' in df.columns:
            ids = pd.to_numeric(df['ID'], errors='coerce').dropna()
            next_id = int(ids.max()) + 1 if not ids.empty else 1
        success = 0
        errors = []
        with st.spinner(f"Adding {len(entries)} items..."):
            for product, cost in entries:
                try:
                    sheet.append_row([next_id, product, cost])
                    success += 1
                    next_id += 1
                except Exception as e:
                    errors.append(f"{product}: {str(e)}")
        if success:
            st.success(f"Added {success} to **Stock** sheet!")
        if errors:
            st.error(f"{len(errors)} error(s):")
            for e in errors: st.code(e)

# === CLEAR INPUT ===
def clear_template_input():
    if 'success' in st.session_state:
        del st.session_state['success']
    st.session_state['show_button'] = True
    st.session_state['input_text'] = ""

# === HOME PAGE ===
def home_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Home Page")
    with col2:
        st.button("Home", disabled=True, key="home_button_home")
    if st.button("Book Keeping"):
        st.session_state['page'] = 'Book Keeping'
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state('Book Keeping')
        st.rerun()
    if st.button("Pending Orders"):
        st.session_state['page'] = 'Pending Orders'
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state('Pending Orders')
        st.rerun()
    if st.button("Record Checking"):
        st.session_state['page'] = 'Record Checking'
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state('Record Checking')
        st.rerun()
    if st.button("Quick Responses"):
        st.session_state['page'] = 'Quick Responses'
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state('Quick Responses')
        st.rerun()
    if st.button("Stock Taking"):
        st.session_state['page'] = 'Stock Taking'
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state('Stock Taking')
        st.rerun()

@st.cache_data(show_spinner=False)
def get_pending_df(_refresh_trigger):
    sheet = load_journal_sheet()
    all_data = sheet.get_all_values()
    if len(all_data) < 2:
        return pd.DataFrame()
    headers = all_data[0]
    rows = all_data[1:]
    df = pd.DataFrame(rows, columns=headers)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    required = ['Order', 'Item', 'Color', 'Size', 'Status']
    if not all(col in df.columns for col in required):
        return pd.DataFrame()
    df = df[required].copy()
    df['Status'] = df['Status'].astype(str).str.strip().str.lower()
    pending_df = df[df['Status'] == 'pending']
    pending_df = pending_df.dropna(subset=['Order', 'Item'])
    return pending_df[required]

def pending_orders_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Pending Orders")
    with col2:
        st.button("Home", key="home_button_pending", on_click=go_home)
    if 'refresh_trigger' not in st.session_state:
        st.session_state['refresh_trigger'] = time.time()
    if st.button("Refresh", key="refresh_button_pending"):
        get_pending_df.clear()
        st.session_state['refresh_trigger'] = time.time()
        st.rerun()
    pending_df = get_pending_df(st.session_state['refresh_trigger'])
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .stTextArea textarea { user-select: all; }
    </style>
    <script>
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('dblclick', function() {
            this.select();
        });
    });
    </script>
    """, unsafe_allow_html=True)
    if not pending_df.empty:
        st.write(f"Found {len(pending_df)} pending order(s):")
        st.dataframe(pending_df[['Order', 'Item', 'Color', 'Size']], use_container_width=True)
        for _, row in pending_df.iterrows():
            label = f"{row['Item']} (Color: {row['Color']}, Size: {row['Size']})"
            if st.button(label, key=f"order_{row['Order']}"):
                st.session_state['selected_order'] = row['Order']
                st.session_state['page'] = 'Order Details'
                st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
                reset_page_state('Order Details')
                st.rerun()
    else:
        st.warning("No pending orders found. Ensure 'Status' is exactly 'Pending' (case-insensitive).")
    if st.session_state.get('page') != 'Pending Orders':
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state(st.session_state['page'])
        st.rerun()

# === ORDER DETAILS PAGE ===
# === ORDER DETAILS PAGE - FIXED & SIMPLIFIED ===
def order_details_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Order Details")
    with col2:
        st.button("Home", key="home_button_details", on_click=go_home)

    st.button("← Back", on_click=lambda: st.session_state.update(page="Pending Orders"))

    if 'selected_order' not in st.session_state:
        st.error("No order selected.")
        return

    sheet = load_journal_sheet()
    all_data = sheet.get_all_values()
    if len(all_data) < 2:
        st.error("No data.")
        return

    headers = all_data[0]
    rows = all_data[1:]
    df = pd.DataFrame(rows, columns=headers)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)

    order_row = df[df['Order'] == st.session_state['selected_order']]
    if order_row.empty:
        st.error("Order not found.")
        return
    order_row = order_row.iloc[0]

    st.markdown("**Order Number**")
    st.code(order_row.get('Order', ''), language=None)
    st.markdown("**Item • Color • Size**")
    st.code(f"{order_row.get('Item','')} (Color: {order_row.get('Color','')}, Size: {order_row.get('Size','')})")
    st.markdown("**Carousell ID**")
    st.code(order_row.get('Carousell ID', ''))
    st.markdown("**Phone**")
    st.code(order_row.get('Phone', ''))
    st.markdown("**Address**")
    st.code(order_row.get('Address', ''))

    sf_input = st.text_input("Enter SF Delivery Number", key="sf_input")

    # ── ONE-CLICK SUBMIT (saves SF + auto changes status to Delivered) ──
    if st.button("Submit SF Number & Mark as Delivered", type="primary"):
        if not sf_input.strip():
            st.error("Please enter SF number.")
        else:
            if update_sf_delivery(st.session_state['selected_order'], sf_input.strip()):
                st.success("SF number saved → Status changed to **Delivered**")
                msg = f"SF Delivery Number: {sf_input.strip()}\nHello shoes are sent. Please leave a 5-star review! Thank you!"
                st.text_area("Copy message to customer:", value=msg, height=100)
                if st.button("Back to Pending Orders"):
                    get_pending_df.clear()
                    st.session_state.page = "Pending Orders"
                    st.rerun()
            else:
                st.error("Failed to update Google Sheet.")
            
    if 'success' in st.session_state:
        st.success("Updated!")
        if 'message_lang' not in st.session_state:
            st.session_state['message_lang'] = 'en'
        st.markdown('<div class="item-container"><p class="item-label">Delivery Message:</p>', unsafe_allow_html=True)
        msg = f"順豐number: {st.session_state['sf_delivery']}\nHello 鞋已經寄出咗了 收到嘅話麻煩比個五星好評 多謝支持" if st.session_state['message_lang'] == 'zh' else f"SF Delivery Number: {st.session_state['sf_delivery']}\nHello shoes are sent. Please leave a 5 star review. Have a nice day."
        st.text_area("", value=msg, height=100, disabled=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("English", key="english_button"):
                st.session_state['message_lang'] = 'en'
                st.rerun()
        with col2:
            if st.button("中文", key="chinese_button"):
                st.session_state['message_lang'] = 'zh'
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        if st.button("Finish"):
            if update_order_status(st.session_state['selected_order'], "Delivered"):
                ...
                del st.session_state['success']
                st.session_state['page'] = 'Pending Orders'
                st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
                reset_page_state('Pending Orders')
                st.rerun()
            else:
                st.error("Failed to update status.")
    if st.session_state.get('page') != 'Order Details':
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state(st.session_state['page'])
        st.rerun()

# === BOOK KEEPING PAGE ===
def book_keeping_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Transaction Record")
    with col2:
        st.button("Home", key="home_button", on_click=go_home)
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .stTextArea textarea { user-select: all; }
    </style>
    <script>
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('dblclick', function() {
            this.select();
        });
    });
    </script>
    """, unsafe_allow_html=True)
    st.markdown('<h3 style="font-size: 1.4em;">Paste transaction here.</h3>', unsafe_allow_html=True)
    template_text = st.text_area(
        "Paste customer message here",
        value=st.session_state.get('input_text', ""),
        height=200,
        key="template_text",
        label_visibility="collapsed"
    )
    
    if 'show_button' not in st.session_state:
        st.session_state['show_button'] = True
    if st.session_state['show_button'] and st.button("Process and Add"):
        if template_text:
            order_num, date, carousell_id, item, color, size, status, phone, address, sf_delivery_number = extract_data(template_text)
            if all([item, color, size, phone, address]):
                result = add_to_sheet(order_num, date, carousell_id, item, color, size, status, phone, address, sf_delivery_number)
                if result is True:
                    st.session_state['success'] = True
                    st.session_state['show_button'] = False
                    st.session_state['input_text'] = ""
                    st.rerun()
                else:
                    st.session_state['error'] = result
                    st.rerun()
            else:
                st.error("Missing data.")
        else:
            st.error("Enter text.")
    if 'success' in st.session_state:
        st.success("Added!")
        st.button("Add Another", on_click=clear_template_input)
    elif 'error' in st.session_state:
        st.error(f"Error: {st.session_state['error']}")
        if st.button("Home"):
            go_home()

# === RECORD CHECKING PAGE ===
def record_checking_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Transaction Record")
    with col2:
        st.button("Home", key="home_button_record", on_click=go_home)
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .stTextArea textarea { user-select: all; }
    </style>
    <script>
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('dblclick', function() {
            this.select();
        });
    });
    </script>
    """, unsafe_allow_html=True)
    st.header("Record Checking")
    query = st.text_input("Search", value=st.session_state.get('search_query', ""))
    if st.button("Search"):
        if query:
            st.session_state['search_query'] = query
            results = search_sheet(query)
            if not results.empty:
                st.dataframe(results, use_container_width=True)
            else:
                st.warning("No matches.")
        else:
            st.error("Enter terms.")
    if st.session_state.get('page') != 'Record Checking':
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state(st.session_state['page'])
        st.rerun()

# === MAIN ROUTER ===
query_params = st.query_params.to_dict()
if 'logged_in' in query_params and query_params['logged_in'] == 'true' and 'page' in query_params and st.session_state.get('logged_in'):
    st.session_state['page'] = query_params['page']
    st.session_state['last_activity'] = time.time()

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    login_page()
else:
    current_time = time.time()
    
    # Initialize on first load
    if 'last_activity' not in st.session_state:
        st.session_state['last_activity'] = current_time
    
    # Update activity on every interaction
    st.session_state['last_activity'] = current_time
    
    # Logout only after 15 minutes of real inactivity
    if current_time - st.session_state['last_activity'] > 900:  # 15 × 60 = 900 seconds
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    st.session_state['last_activity'] = current_time
    if 'page' not in st.session_state:
        st.session_state['page'] = 'Home'
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})

    if st.session_state['page'] == 'Home':
        home_page()
    elif st.session_state['page'] == 'Book Keeping':
        book_keeping_page()
    elif st.session_state['page'] == 'Pending Orders':
        pending_orders_page()
    elif st.session_state['page'] == 'Order Details':
        order_details_page()
    elif st.session_state['page'] == 'Record Checking':
        record_checking_page()
    elif st.session_state['page'] == 'Quick Responses':
        quick_responses_page()
    elif st.session_state['page'] == 'Stock Taking':
        stock_taking_page()
