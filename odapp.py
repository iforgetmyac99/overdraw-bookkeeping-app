import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import os
import re
from datetime import datetime
from builtins import max
from st_clipboard import copy_to_clipboard  # For reliable clipboard copying
import requests
from urllib.parse import urlencode

# Google Sheets config with environment variable support
@st.cache_resource
def load_gspread():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds).open_by_key('10CLEJyH7LGkZrVjc8EiicJ2PCBY_se7gALChd_YyaCg').sheet1

# State reset function for Task 6
def reset_page_state(page):
    """Reset session state variables for a fresh page load."""
    state_keys = ['success', 'error', 'show_button', 'show_submit', 'sf_delivery', 'message_lang']
    for key in state_keys:
        if key in st.session_state:
            del st.session_state[key]
    if page == 'Book Keeping':
        st.session_state['template_text'] = ""  # Clear template text input
    elif page == 'Order Details':
        st.session_state['sf_input'] = ""  # Clear SF delivery input

# Google OAuth2 Login
def google_login():
    st.title("OverDraw Management Portal")
    st.markdown("""
    <style>
    .login-button { display: flex; justify-content: center; }
    .login-button button { background-color: #4285F4; color: white; padding: 10px 20px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; }
    .login-button button:hover { background-color: #357ae8; }
    </style>
    """, unsafe_allow_html=True)

    if 'auth_state' not in st.session_state:
        st.session_state['auth_state'] = 'not_authenticated'

    try:
        # Google OAuth2 configuration
        client_id = st.secrets["google_oauth"]["client_id"]
        redirect_uri = st.secrets["google_oauth"]["redirect_uri"]
        client_secret = st.secrets["google_oauth"]["client_secret"]
    except KeyError as e:
        st.error(f"Missing secret: {e}. Please check your secrets.toml or app secrets.")
        st.stop()

    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'email profile',
        'access_type': 'offline',
        'prompt': 'consent'
    })

    # Display Login button with target="_self" for same-tab redirect
    if st.session_state['auth_state'] == 'not_authenticated':
        st.markdown(f'<div class="login-button"><a href="{auth_url}" target="_self"><button>Login with Google</button></a></div>', unsafe_allow_html=True)
        st.stop()

    # Handle OAuth callback
    query_params = st.experimental_get_query_params()
    if 'code' in query_params:
        code = query_params['code'][0]
        # Exchange code for access token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': client_id,
            'client_secret': client_secret,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        response = requests.post(token_url, data=token_data)
        if response.status_code != 200:
            st.error(f"Token exchange failed: {response.text}")
            st.session_state['auth_state'] = 'not_authenticated'
            st.stop()

        token_json = response.json()

        if 'access_token' in token_json:
            # Get user info
            user_info_url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {'Authorization': f"Bearer {token_json['access_token']}"}
            user_response = requests.get(user_info_url, headers=headers)
            if user_response.status_code != 200:
                st.error(f"User info fetch failed: {user_response.text}")
                st.session_state['auth_state'] = 'not_authenticated'
                st.stop()

            user_info = user_response.json()

            # Check if the email is allowed
            allowed_email = "ryantlyu1018@gmail.com"
            if user_info.get('email') == allowed_email:
                st.session_state['auth_state'] = 'authenticated'
                st.session_state['user_email'] = user_info['email']
                st.session_state['page'] = 'Home'
                st.experimental_set_query_params()  # Clear query params
                st.rerun()
            else:
                st.error("Access denied: Only ryantlyu1018@gmail.com is authorized.")
                st.session_state['auth_state'] = 'not_authenticated'
                st.stop()
        else:
            st.error("Authentication failed. Please try again.")
            st.session_state['auth_state'] = 'not_authenticated'
            st.stop()

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
    phone = phone_en.group(1) if phone_en else (phone_zh.group(1) if phone_zh else "")
    address = address_en.group(1).strip() if address_en else (address_zh.group(1).strip() if address_zh else "")

    return order_num, date, carousell_id, item, color, size, status, name, phone, address, sf_delivery_number

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
    results = df[df.apply(lambda row: query.lower() in ' '.join(row.astype(str)).lower(), axis=1)]
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
quick_responses = [
    "Thank you for your purchase!",
    "Your order has been shipped.",
    "Sorry, item out of stock."
]

# Home page
def home_page():
    st.title("Home Page")
    if st.button("Book Keeping"):
        st.session_state['page'] = 'Book Keeping'
        reset_page_state('Book Keeping')
        st.rerun()
    if st.button("Pending Orders"):
        st.session_state['page'] = 'Pending Orders'
        reset_page_state('Pending Orders')
        st.rerun()

# Pending Orders page
def pending_orders_page():
    reset_page_state('Pending Orders')  # Reset state on entry
    st.title("Pending Orders")
    def go_home():
        st.session_state['page'] = 'Home'
    def refresh():
        st.cache_data.clear()  # Clear cache for fresh data
        st.rerun()
    col1 = st.columns(1)[0]
    with col1:
        st.button("Home", key="home_button_pending", on_click=go_home)
        st.button("Refresh", key="refresh_button_pending", on_click=refresh)
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    </style>
    """, unsafe_allow_html=True)

    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    pending_df = df[df['Status'] == 'Pending'][['Order', 'Item', 'Color', 'Size']].dropna()

    if not pending_df.empty:
        for index, row in pending_df.iterrows():
            if st.button(f"{row['Item']} (Color: {row['Color']}, Size: {row['Size']})", key=f"order_{row['Order']}"):
                st.session_state['selected_order'] = row['Order']
                st.session_state['page'] = 'Order Details'
                reset_page_state('Order Details')
                st.rerun()
    else:
        st.write("No pending orders found.")

# Order Details page
def order_details_page():
    reset_page_state('Order Details')  # Reset state on entry
    st.title("Order Details")
    def go_home():
        st.session_state['page'] = 'Home'
    def go_pending_orders():
        st.session_state['page'] = 'Pending Orders'
        reset_page_state('Pending Orders')
    col1 = st.columns(1)[0]
    with col1:
        st.button("Return", key="return_button", on_click=go_pending_orders)
        st.button("Home", key="home_button_details", on_click=go_home)
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    </style>
    """, unsafe_allow_html=True)

    if 'selected_order' not in st.session_state:
        st.error("No order selected. Please go back to Pending Orders.")
        return

    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    order_row = df[df['Order'] == st.session_state['selected_order']].iloc[0]

    # Display order details with copy buttons (Task 5: Unified "Copy" label)
    st.write(f"**Order Number:** {order_row['Order']}")
    st.write(f"**Item, Color, Size:** {order_row['Item']} (Color: {order_row['Color']}, Size: {order_row['Size']})")
    st.write(f"**Name:**")
    st.text_area("", value=order_row['Name'], height=50, disabled=True, key="name_box")
    if st.button("Copy", key="copy_name"):
        copy_to_clipboard(order_row['Name'])
    st.write(f"**Phone:**")
    st.text_area("", value=order_row['Phone'], height=50, disabled=True, key="phone_box")
    if st.button("Copy", key="copy_phone"):
        copy_to_clipboard(order_row['Phone'])
    st.write(f"**Address:**")
    st.text_area("", value=order_row['Address'], height=100, disabled=True, key="address_box")
    if st.button("Copy", key="copy_address"):
        copy_to_clipboard(order_row['Address'])

    # SF Delivery Number input
    sf_input = st.text_input("Enter SF Delivery Number", key="sf_input", value="")
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
        row_text = ' '.join(str(order_row[col]) for col in order_row.index)
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', row_text))
        if 'message_lang' not in st.session_state:
            st.session_state['message_lang'] = 'default'

        if has_chinese and st.session_state['message_lang'] in ['default', 'zh']:
            message = f"順豐number: {st.session_state['sf_delivery']}\nHello 鞋已經寄出咗了 收到嘅話麻煩比個五星好評 多謝支持🫡"
            st.text_area("", value=message, height=100, disabled=True, key="message_chinese")
            if st.button("Copy", key="copy_message_chinese"):
                copy_to_clipboard(message)
            if st.button("English"):
                st.session_state['message_lang'] = 'en'
                st.rerun()
        else:
            message = f"SF Delivery Number: {st.session_state['sf_delivery']}\nHello shoes are sent. Please leave a 5 star review when receiving the product. Have a nice day."
            st.text_area("", value=message, height=100, disabled=True, key="message_english")
            if st.button("Copy", key="copy_message_english"):
                copy_to_clipboard(message)
            if st.button("中文"):
                st.session_state['message_lang'] = 'zh'
                st.rerun()

        if st.button("Finish"):
            if update_order_status(st.session_state['selected_order'], "Delivered"):
                st.session_state['success'] = False
                st.session_state['page'] = 'Pending Orders'
                reset_page_state('Pending Orders')
                st.rerun()
            else:
                st.error("Failed to update order status.")

# Order Completed page
def order_completed_page():
    st.title("Order Completed")
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
    st.write(f"Name: {order_row['Name']}")
    st.write(f"Phone: {order_row['Phone']}")
    st.write(f"Address: {order_row['Address']}")
    st.write(f"SF Delivery Number: {order_row['SF Delivery Number']}")

# Main App
if 'auth_state' not in st.session_state or st.session_state['auth_state'] != 'authenticated':
    google_login()
else:
    if 'page' not in st.session_state:
        st.session_state['page'] = 'Home'

    if st.session_state['page'] == 'Home':
        home_page()
    elif st.session_state['page'] == 'Book Keeping':
        reset_page_state('Book Keeping')  # Reset state on entry
        st.title("Transaction Record")
        def go_home():
            st.session_state['page'] = 'Home'
        st.button("Home", key="home_button", on_click=go_home)
        st.write("")
        st.write("")
        st.markdown("""
        <style>
        .stTextInput, .stTextArea { width: 100% !important; }
        .stDataFrame { width: 100%; overflow-x: auto; }
        .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
        </style>
        """, unsafe_allow_html=True)
        st.markdown('<h3 style="font-size: 1.4em;">Paste transaction here.</h3>', unsafe_allow_html=True)
        template_text = st.text_area("", height=200, key="template_text", value=st.session_state.get('template_text', ""))
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
                    else:
                        st.session_state['error'] = result
                    st.rerun()
                else:
                    st.error("Couldn't extract all required data. Check template.")
            else:
                st.error("Enter template text.")

        if 'success' in st.session_state:
            st.success("Entry added successfully!", icon="✅")
            if st.button("Add Another Entry"):
                del st.session_state['success']
                st.session_state['show_button'] = True
                st.session_state['template_text'] = ""
                st.rerun()
        elif 'error' in st.session_state:
            st.error(f"Failed to add entry: {st.session_state['error']}")
            if st.button("Home"):
                st.session_state['page'] = 'Home'
                del st.session_state['error']
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
            def go_home_record():
                st.session_state['page'] = 'Home'
            st.button("Home", key="home_button_record", on_click=go_home_record)
        st.markdown("""
        <style>
        .stTextInput, .stTextArea { width: 100% !important; }
        .stDataFrame { width: 100%; overflow-x: auto; }
        .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
        </style>
        """, unsafe_allow_html=True)
        st.header("Record Checking")
        query = st.text_input("Enter search terms (e.g., date, shoe model, name)")
        if st.button("Search"):
            if query:
                results = search_sheet(query)
                if not results.empty:
                    st.dataframe(results, use_container_width=True)
                else:
                    st.warning("No matches found.")
            else:
                st.error("Enter search terms.")

    elif st.session_state['page'] == 'Quick Responses':
        col1, col2 = st.columns([8, 1])
        with col1:
            st.title("Transaction Record")
        with col2:
            def go_home_quick():
                st.session_state['page'] = 'Home'
            st.button("Home", key="home_button_quick", on_click=go_home_quick)
        st.markdown("""
        <style>
        .stTextInput, .stTextArea { width: 100% !important; }
        .stDataFrame { width: 100%; overflow-x: auto; }
        .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
        </style>
        """, unsafe_allow_html=True)
        st.header("Quick Responses")
        for response in quick_responses:
            st.write(response)
            if st.button("Copy", key=f"copy_response_{response}"):
                copy_to_clipboard(response)
