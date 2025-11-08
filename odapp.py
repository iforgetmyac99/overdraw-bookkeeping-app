import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import re
from datetime import datetime
from builtins import max
import time

# Google Sheets config with environment variable support
@st.cache_resource
def load_gspread():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds).open_by_key('10CLEJyH7LGkZrVjc8EiicJ2PCBY_se7gALChd_YyaCg').sheet1

# State reset function
def reset_page_state(page):
    """Reset session state variables for a fresh page load."""
    state_keys = ['success', 'error', 'show_button', 'show_submit', 'sf_delivery', 'message_lang', 'quick_response_lang', 'input_text', 'sf_input', 'search_query', 'refresh_trigger']
    for key in state_keys:
        if key in st.session_state:
            del st.session_state[key]
    if page == 'Book Keeping':
        st.session_state['input_text'] = ""  # Ensure text box is empty
    elif page == 'Order Details':
        st.session_state['sf_input'] = ""  # Clear SF delivery input
    elif page == 'Record Checking':
        st.session_state['search_query'] = ""  # Clear search input
    elif page == 'Quick Responses':
        st.session_state['quick_response_lang'] = None  # No messages on page load
    st.session_state['last_page'] = page  # Track current page

# Navigation helper
def go_home():
    st.session_state['page'] = 'Home'
    st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
    reset_page_state('Home')

# Login Implementation
def login_page():
    st.markdown("""
    <style>
    .login-form { max-width: 400px; margin: 0 auto; }
    .login-form input { width: 100% !important; }
    .login-form button { background-color: #4CAF50; color: white; padding: 10px; width: 100%; }
    .login-title { 
        font-size: 2em; /* Reduced font size for iPhone 15 Pro */
        max-width: 400px; 
        margin: 0 auto; 
        text-align: left; /* Align with login box */
        padding-bottom: 20px; 
    }
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
                st.session_state['page'] = 'Home'  # Always start at Home on new login
                st.query_params.update({"logged_in": "true", "page": "Home"})
                reset_page_state('Home')
                st.rerun()
            else:
                st.error("Invalid credentials.")

# Extract data from Carousell template
def extract_data(template_text):
    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    if not df.empty and 'Order' in df.columns:
        latest_order = df['Order'].dropna().astype(str)
        if latest_order.empty:
            order_num = "OD001"
        else:
            latest_num = max(latest_order)
            num_part = int(latest_num.replace('OD', '')) + 1
            order_num = f"OD{num_part:03d}"
    else:
        order_num = "OD001"

    date = datetime.now().strftime("%d/%m/%Y")
    carousell_id = ""
    item = ""
    color = ""
    size = ""
    status = "Pending"
    name = ""
    carousell_id = name  # Assign name to Carousell ID
    phone = ""
    address = ""
    sf_delivery_number = ""

    item_en = re.search(r'Shoe:\s*([^\n]+)', template_text)
    color_en = re.search(r'Color:\s*([^\n]+)', template_text)
    size_en = re.search(r'Size:\s*(\d+)', template_text)
    name_en = re.search(r'Name:\s*([^\n]+)', template_text)
    phone_en = re.search(r'Phone:\s*(\d+)', template_text)
    address_en = re.search(r'Address:\s*(.+?)(?=\s*(Phone|Payment|\n|$))', template_text, re.DOTALL)

    item_zh = re.search(r'鞋款：\s*([^\n]+)', template_text)
    color_zh = re.search(r'顏色：\s*([^\n]+)', template_text)
    size_zh = re.search(r'碼數：\s*(\d+)', template_text)
    name_zh = re.search(r'姓名：\s*([^\n]+)', template_text)
    phone_zh = re.search(r'電話：\s*(\d+)', template_text)
    address_zh = re.search(r'地址：\s*(.+?)(?=\s*(電話|付款方式|\n|$))', template_text, re.DOTALL)

    item = item_en.group(1).strip() if item_en else (item_zh.group(1).strip() if item_zh else "")
    color = color_en.group(1).strip() if color_en else (color_zh.group(1).strip() if color_zh else "")
    size = size_en.group(1) if size_en else (size_zh.group(1) if size_zh else "")
    name = name_en.group(1).strip() if name_en else (name_zh.group(1).strip() if name_zh else "")
    carousell_id = name  # Assign name to Carousell ID
    phone = phone_en.group(1) if phone_en else (phone_zh.group(1) if phone_zh else "")
    address = address_en.group(1).strip() if address_en else (address_zh.group(1).strip() if address_zh else "")

    if not all([item, color, size, name, phone, address]):
        st.warning("Some fields are missing in the template. Please verify the input.")

    return order_num, date, carousell_id, item, color, size, status, phone, address, sf_delivery_number

# Add to Sheet
def add_to_sheet(order_num, date, carousell_id, item, color, size, status, name, phone, address, sf_delivery_number):
    try:
        sheet = load_gspread()
        sheet.append_row([order_num, date, carousell_id, item, color, size, status, name, phone, address, sf_delivery_number])
        return True
    except Exception as e:
        return str(e)

# Search Sheet
def search_sheet(query):
    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    results = df[df.apply(lambda row: query.lower() in ' '.join(str(col) for col in row).lower(), axis=1)]
    return results

# Update SF Delivery Number
def update_sf_delivery(order_num, sf_delivery_number):
    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty and 'Order' in df.columns:
        row_idx = df.index[df['Order'] == order_num].tolist()
        if row_idx:
            sheet.update_cell(row_idx[0] + 2, df.columns.get_loc('SF Delivery Number') + 1, sf_delivery_number)
            return True
    return False

# Update Order Status
def update_order_status(order_num, status):
    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty and 'Order' in df.columns:
        row_idx = df.index[df['Order'] == order_num].tolist()
        if row_idx:
            sheet.update_cell(row_idx[0] + 2, df.columns.get_loc('Status') + 1, status)
            return True
    return False

# Quick Responses
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

    # Language toggle buttons
    if 'quick_response_lang' not in st.session_state:
        st.session_state['quick_response_lang'] = None  # No messages on page load
    
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

    # Show responses only if a language is selected
    if st.session_state['quick_response_lang'] == 'zh':
        # 快速落單
        st.markdown('<div class="item-container"><p class="item-label">快速落單</p>', unsafe_allow_html=True)
        express_order_zh = """快速落單💨

㩒一㩒「出價」同埋留低以下資料就可以快速落單㗎喇🤝🏻

鞋款：
顏色：
碼數：
姓名：
電話：
地址：
付款方式（FPS / Payme / Alipay）：

溫馨提示🥰
貨品如非質量問題 不設退換👟
收貨後請先作檢查✅
已經穿著嘅鞋將不接受退換處理🚫"""
        st.text_area("", value=express_order_zh, height=200, disabled=True, key="express_order_zh")
        st.markdown('</div>', unsafe_allow_html=True)

        # 付款方法
        st.markdown('<div class="item-container"><p class="item-label">付款方法</p>', unsafe_allow_html=True)
        payment_method = """FPS ID
111780946
Yu Txx Lxx

Payme
Tap to PayMe!
https://payme.hsbc/overdraw9"""
        st.text_area("", value=payment_method, height=150, disabled=True, key="payment_method_zh")
        st.markdown('</div>', unsafe_allow_html=True)

        # 落單成功
        st.markdown('<div class="item-container"><p class="item-label">落單成功</p>', unsafe_allow_html=True)
        completed_order_zh = """唔該曬
大約五至七日左右到貨
寄出後會有順豐寄件編號比翻你嘅
到時可以用順豐APP查詢寄件狀況
多謝支持🫡"""
        st.text_area("", value=completed_order_zh, height=150, disabled=True, key="completed_order_zh")
        st.markdown('</div>', unsafe_allow_html=True)

    elif st.session_state['quick_response_lang'] == 'en':
        # Express Order
        st.markdown('<div class="item-container"><p class="item-label">Express Order</p>', unsafe_allow_html=True)
        express_order_en = """Express Order💨

Please fill in the information below and click "Make Offer" button for placing order🤝🏻

Shoe:
Color:
Size:
Name:
Phone:
Address:
Payment (FPS/Alipay/Payme):

Warm Reminder🥰
Refund / Exchange is only facilitated for shoes with quality issue👟
Please check when receiving the delivery✅
Worn shoes are not accepted as return🚫"""
        st.text_area("", value=express_order_en, height=200, disabled=True, key="express_order_en")
        st.markdown('</div>', unsafe_allow_html=True)

        # Payment Method
        st.markdown('<div class="item-container"><p class="item-label">Payment Method</p>', unsafe_allow_html=True)
        payment_method = """FPS ID
111780946
Yu Txx Lxx

Payme
Tap to PayMe!
https://payme.hsbc/overdraw9"""
        st.text_area("", value=payment_method, height=150, disabled=True, key="payment_method_en")
        st.markdown('</div>', unsafe_allow_html=True)

        # Completed Order
        st.markdown('<div class="item-container"><p class="item-label">Completed Order</p>', unsafe_allow_html=True)
        completed_order_en = """Well received and Thank you for the order!
Pre-Ordered shoes take around 5 - 7 days for stock arrival.
SF Delivery Number will be provided after shipment being sent.
Delivery status can be checked with the provided SF Delivery number.
Thank you for your support and patience."""
        st.text_area("", value=completed_order_en, height=150, disabled=True, key="completed_order_en")
        st.markdown('</div>', unsafe_allow_html=True)

    # Handle navigation
    if st.session_state.get('page') != 'Quick Responses':
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state(st.session_state['page'])
        st.rerun()

# Callback for clearing input in Book Keeping
def clear_template_input():
    if 'success' in st.session_state:
        del st.session_state['success']
    st.session_state['show_button'] = True
    st.session_state['input_text'] = ""  # Clear text box for next entry

# Home page
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

# Pending Orders page
@st.cache_data(show_spinner=False)
def get_pending_df(_refresh_trigger):
    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    if not df.empty and 'Status' in df.columns:
        # Normalize Status column to handle whitespace and case sensitivity
        df['Status'] = df['Status'].astype(str).str.strip().str.lower()
        pending_df = df[df['Status'] == 'pending'][['Order', 'Item', 'Color', 'Size']].dropna()
        return pending_df
    return pd.DataFrame()

def pending_orders_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Pending Orders")
    with col2:
        st.button("Home", key="home_button_pending", on_click=go_home)
    
    if 'refresh_trigger' not in st.session_state:
        st.session_state['refresh_trigger'] = time.time()
    
    if st.button("Refresh", key="refresh_button_pending"):
        get_pending_df.clear()  # Clear cache to force fresh data
        st.session_state['refresh_trigger'] = time.time()
    
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

    # Debugging output to verify data
    if not pending_df.empty:
        st.write(f"Found {len(pending_df)} pending orders:")
        st.dataframe(pending_df, use_container_width=True)  # Display raw data for debugging
        for index, row in pending_df.iterrows():
            if st.button(f"{row['Item']} (Color: {row['Color']}, Size: {row['Size']})", key=f"order_{row['Order']}"):
                st.session_state['selected_order'] = row['Order']
                st.session_state['page'] = 'Order Details'
                st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
                reset_page_state('Order Details')
                st.rerun()
    else:
        st.warning("No pending orders found. Check if 'Status' column in Google Sheet has 'Pending' entries.")

    # Handle navigation
    if st.session_state.get('page') != 'Pending Orders':
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state(st.session_state['page'])
        st.rerun()

# Order Details page
def order_details_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Order Details")
    with col2:
        st.button("Home", key="home_button_details", on_click=go_home)
    st.button("Return", key="return_button", on_click=lambda: st.session_state.update({'page': 'Pending Orders', 'refresh_trigger': time.time()}))
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .stTextArea textarea { user-select: all; }
    .item-label { margin-bottom: 0px; font-weight: bold; }
    .item-container { margin-bottom: 20px; }
    </style>
    <script>
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('dblclick', function() {
            this.select();
        });
    });
    </script>
    """, unsafe_allow_html=True)

    if 'selected_order' not in st.session_state:
        st.error("No order selected. Please go back to Pending Orders.")
        return

    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    order_row = df[df['Order'] == st.session_state['selected_order']].iloc[0]

    # Display order details with improved formatting
    st.markdown('<div class="item-container"><p class="item-label">Order Number:</p>', unsafe_allow_html=True)
    st.text_area("", value=str(order_row['Order']) if not pd.isna(order_row['Order']) else "", height=50, disabled=True, key=f"order_box_{st.session_state['selected_order']}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="item-container"><p class="item-label">Item, Color, Size:</p>', unsafe_allow_html=True)
    st.text_area("", value=f"{order_row['Item']} (Color: {order_row['Color']}, Size: {order_row['Size']})", height=50, disabled=True, key=f"item_box_{st.session_state['selected_order']}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="item-container"><p class="item-label">Carousell ID:</p>', unsafe_allow_html=True)
    st.text_area("", value=str(order_row['Carousell ID']) if not pd.isna(order_row['Carousell ID']) else "", height=50, disabled=True, key=f"carousell_id_box_{st.session_state['selected_order']}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="item-container"><p class="item-label">Phone:</p>', unsafe_allow_html=True)
    st.text_area("", value=str(order_row['Phone']) if not pd.isna(order_row['Phone']) else "", height=50, disabled=True, key=f"phone_box_{st.session_state['selected_order']}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="item-container"><p class="item-label">Address:</p>', unsafe_allow_html=True)
    st.text_area("", value=str(order_row['Address']) if not pd.isna(order_row['Address']) else "", height=100, disabled=True, key=f"address_box_{st.session_state['selected_order']}")
    st.markdown('</div>', unsafe_allow_html=True)

    # SF Delivery Number input
    st.markdown('<div class="item-container"><p class="item-label">Enter SF Delivery Number:</p>', unsafe_allow_html=True)
    st.text_input("", key="sf_input", value=st.session_state.get('sf_input', ""))
    st.markdown('</div>', unsafe_allow_html=True)

    if 'show_submit' not in st.session_state:
        st.session_state['show_submit'] = True
    if st.session_state['show_submit'] and st.button("Submit"):
        if sf_input:
            if update_sf_delivery(st.session_state['selected_order'], sf_input):
                st.session_state['success'] = True
                st.session_state['show_submit'] = False
                st.session_state['sf_delivery'] = sf_input
                st.rerun()
            else:
                st.error("Failed to update SF Delivery Number.")
        else:
            st.error("Please enter a delivery number.")

    # Success banner and message
    if 'success' in st.session_state:
        st.success("SF Delivery Number updated successfully!", icon="✅")
        if 'message_lang' not in st.session_state:
            st.session_state['message_lang'] = 'en'  # Default to English

        st.markdown('<div class="item-container"><p class="item-label">Delivery Message:</p>', unsafe_allow_html=True)
        if st.session_state['message_lang'] == 'zh':
            message = f"順豐number: {st.session_state['sf_delivery']}\nHello 鞋已經寄出咗了 收到嘅話麻煩比個五星好評 多謝支持🫡"
            st.text_area("", value=message, height=100, disabled=True, key="message_chinese")
        else:
            message = f"SF Delivery Number: {st.session_state['sf_delivery']}\nHello shoes are sent. Please leave a 5 star review when receiving the product. Have a nice day."
            st.text_area("", value=message, height=100, disabled=True, key="message_english")

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
                st.session_state['success'] = False
                st.session_state['page'] = 'Pending Orders'
                st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
                reset_page_state('Pending Orders')
                st.rerun()
            else:
                st.error("Failed to update order status.")

    # Handle navigation
    if st.session_state.get('page') != 'Order Details':
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state(st.session_state['page'])
        st.rerun()

# Order Completed page
def order_completed_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Order Completed")
    with col2:
        st.button("Home", key="home_button_completed", on_click=go_home)
    if 'selected_order' not in st.session_state:
        st.error("No order selected.")
        return

    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    order_row = df[df['Order'] == st.session_state['selected_order']].iloc[0]

    st.write("Order Details:")
    st.write(f"Order: {order_row['Order']}")
    st.write(f"Date: {order_row['Date']}")
    st.write(f"Carousell ID: {order_row['Carousell ID']}")
    st.write(f"Item: {order_row['Item']}")
    st.write(f"Color: {order_row['Color']}")
    st.write(f"Size: {order_row['Size']}")
    st.write(f"Status: {order_row['Status']}")
    st.write(f"Carousell ID: {order_row['Carousell ID']}")
    st.write(f"Phone: {order_row['Phone']}")
    st.write(f"Address: {order_row['Address']}")
    st.write(f"SF Delivery Number: {order_row['SF Delivery Number']}")

    # Handle navigation
    if st.session_state.get('page') != 'Order Completed':
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
        reset_page_state(st.session_state['page'])
        st.rerun()

# Main App
query_params = st.query_params.to_dict()
if 'logged_in' in query_params and query_params['logged_in'] == 'true' and 'page' in query_params and st.session_state.get('logged_in'):
    st.session_state['page'] = query_params['page']
    st.session_state['last_activity'] = time.time()  # Reset activity timer on refresh

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    login_page()
else:
    # Session timeout check (10 min idle timeout)
    current_time = time.time()
    if 'last_activity' not in st.session_state:
        st.session_state['last_activity'] = current_time
    if current_time - st.session_state['last_activity'] > 600:
        del st.session_state['logged_in']
        if 'page' in st.session_state:
            del st.session_state['page']
        st.query_params.clear()
        reset_page_state('Login')
        st.rerun()
    st.session_state['last_activity'] = current_time

    if 'page' not in st.session_state:
        st.session_state['page'] = 'Home'
        st.query_params.update({"logged_in": "true", "page": st.session_state['page']})

    if st.session_state['page'] == 'Home':
        home_page()
    elif st.session_state['page'] == 'Book Keeping':
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
        template_text = st.text_area("", value=st.session_state.get('input_text', ""), height=200, key="template_text")
        if 'show_button' not in st.session_state:
            st.session_state['show_button'] = True
        if st.session_state['show_button'] and st.button("Process and Add"):
            if template_text:
                order_num, date, carousell_id, item, color, size, status, name, phone, address, sf_delivery_number = extract_data(template_text)
                if all([item, color, size, name, phone, address]):
                    result = add_to_sheet(order_num, date, carousell_id, item, color, size, status, name, phone, address, sf_delivery_number)
                    if result is True:
                        st.session_state['success'] = True
                        st.session_state['show_button'] = False
                        st.session_state['input_text'] = ""  # Clear text box
                        st.rerun()
                    else:
                        st.session_state['error'] = result
                        st.rerun()
                else:
                    st.error("Couldn't extract all required data. Check template.")
            else:
                st.error("Enter template text.")

        if 'success' in st.session_state:
            st.success("Entry added successfully!", icon="✅")
            st.button("Add Another Entry", on_click=clear_template_input)
        elif 'error' in st.session_state:
            st.error(f"Failed to add entry: {st.session_state['error']}")
            if st.button("Home"):
                go_home()
                st.rerun()

    elif st.session_state['page'] == 'Pending Orders':
        pending_orders_page()
    elif st.session_state['page'] == 'Order Details':
        order_details_page()
    elif st.session_state['page'] == 'Order Completed':
        order_completed_page()
    elif st.session_state['page'] == 'Record Checking':
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
        query = st.text_input("Enter search terms (e.g., date, shoe model, name)", value=st.session_state.get('search_query', ""))
        if st.button("Search"):
            if query:
                st.session_state['search_query'] = query
                results = search_sheet(query)
                if not results.empty:
                    st.dataframe(results, use_container_width=True)
                else:
                    st.warning("No matches found.")
            else:
                st.error("Enter search terms.")

        # Handle navigation
        if st.session_state.get('page') != 'Record Checking':
            st.query_params.update({"logged_in": "true", "page": st.session_state['page']})
            reset_page_state(st.session_state['page'])
            st.rerun()

    elif st.session_state['page'] == 'Quick Responses':
        quick_responses_page()
