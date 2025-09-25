import streamlit as st
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
import pandas as pd
from io import BytesIO
import os
import re  # For extracting data from template
from datetime import datetime
from builtins import max
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials  # Added import for Credentials
import os

# Google Sheets config with environment variable support
@st.cache_resource
def load_gspread():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = None
    # Check if token_out.json exists to reuse credentials
    if os.path.exists('token_out.json'):
        creds = Credentials.from_authorized_user_file('token_out.json', scope)
    # Use credentials.json if token is invalid or missing
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scope).run_local_server(port=0)
            with open('token_out.json', 'w') as token:
                token.write(creds.to_json())
    return gspread.authorize(creds).open_by_key('10CLEJyH7LGkZrVjc8EiicJ2PCBY_se7gALChd_YyaCg').sheet1

# Commented out login section (will uncomment later as requested)
# def check_login():
#     if 'logged_in' not in st.session_state:
#         st.session_state.logged_in = False
#     if not st.session_state.logged_in:
#         st.header("Login")
#         username = st.text_input("Username")
#         password = st.text_input("Password", type="password")
#         if st.button("Log In"):
#             if username == "iforgetmyac99" and password == "OverDraw@99":
#                 st.session_state.logged_in = True
#                 st.rerun()
#             else:
#                 st.error("Incorrect credentials")
#         st.stop()

# Extract data from Carousell template (supports English and Chinese, refined extraction)
def extract_data(template_text):
    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)

    # Get the latest Order number and increment
    if not df.empty and 'Order' in df.columns:
        latest_order = df['Order'].dropna().astype(str)
        if latest_order.empty:
            order_num = "OD001"
        else:
            latest_num = max(latest_order)
            num_part = int(latest_num.replace('OD', '')) + 1
            order_num = f"OD{num_part:03d}"  # Formats as OD001, OD002, etc.
    else:
        order_num = "OD001"  # Start with OD001 if no data

    # Date in dd/mm/yyyy format
    date = datetime.now().strftime("%d/%m/%Y")
    carousell_id = ""
    item = ""
    color = ""
    size = ""
    status = "Pending"  # Default status for new orders
    name = ""
    phone = ""
    address = ""
    sf_delivery_number = ""

    # Refined English regex patterns (stop at next field or newline)
    item_en = re.search(r'Shoe:\s*([^\n]+)', template_text)
    color_en = re.search(r'Color:\s*([^\n]+)', template_text)
    size_en = re.search(r'Size:\s*(\d+)', template_text)
    name_en = re.search(r'Name:\s*([^\n]+)', template_text)
    phone_en = re.search(r'Phone:\s*(\d+)', template_text)
    address_en = re.search(r'Address:\s*(.+?)(?=\s*(Phone|Payment|\n|$))', template_text, re.DOTALL)

    # Refined Chinese regex patterns (stop at next field or newline)
    item_zh = re.search(r'鞋款：\s*([^\n]+)', template_text)
    color_zh = re.search(r'顏色：\s*([^\n]+)', template_text)
    size_zh = re.search(r'碼數：\s*(\d+)', template_text)
    name_zh = re.search(r'姓名：\s*([^\n]+)', template_text)
    phone_zh = re.search(r'電話：\s*(\d+)', template_text)
    address_zh = re.search(r'地址：\s*(.+?)(?=\s*(電話|付款方式|\n|$))', template_text, re.DOTALL)

    # Assign values (prioritize English, fallback to Chinese if English not found)
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
    # Simple search (e.g., contains query in any column)
    results = df[df.apply(lambda row: query.lower() in ' '.join(row.astype(str)).lower(), axis=1)]
    return results

# Quick Responses (add your own)
quick_responses = [
    "Thank you for your purchase!",
    "Your order has been shipped.",
    "Sorry, item out of stock."
]

def copy_to_clipboard(text):
    st.markdown(f"""
    <button onclick="navigator.clipboard.writeText('{text}')">Copy</button>
    """, unsafe_allow_html=True)

# Home page
def home_page():
    st.title("Home Page")
    if st.button("Book Keeping"):
        st.session_state['page'] = 'Book Keeping'
        st.rerun()
    # Placeholder for future functions
    st.write("More functions will be added here later.")

# Main App
# Commented out login call (will uncomment later as requested)
# check_login()

if 'page' not in st.session_state:
    st.session_state['page'] = 'Home'

if st.session_state['page'] == 'Home':
    home_page()
elif st.session_state['page'] == 'Book Keeping':
    st.title("Transaction Record")
    def go_home():
        st.session_state['page'] = 'Home'
    st.button("Home", key="home_button", on_click=go_home)
    # Add two lines of space
    st.write("")
    st.write("")
    # Mobile-friendly and text wrapping
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .home-button button { background: none; border: none; font-size: 16px; color: #666666; cursor: pointer; padding: 0; }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<h3 style="font-size: 1.4em;">Paste transaction here.</h3>', unsafe_allow_html=True)
    template_text = st.text_area("", height=200)  # Empty label, larger height for visibility
    if 'show_button' not in st.session_state:
        st.session_state['show_button'] = True
    if st.session_state['show_button'] and st.button("Process and Add"):
        if template_text:
            order_num, date, carousell_id, item, color, size, status, name, phone, address, sf_delivery_number = extract_data(template_text)
            if all([item, color, size, name, phone, address]):  # Check only extracted fields
                result = add_to_sheet(order_num, date, carousell_id, item, color, size, status, name, phone, address, sf_delivery_number)
                if result is True:
                    st.session_state['success'] = True
                    st.session_state['show_button'] = False  # Hide button on success
                else:
                    st.session_state['error'] = result
                st.rerun()
            else:
                st.error("Couldn't extract all required data. Check template.")
        else:
            st.error("Enter template text.")

    # Success or Error page
    if 'success' in st.session_state:
        st.success("Entry added successfully!", icon="✅")
        if st.button("Add Another Entry"):
            del st.session_state['success']
            st.session_state['show_button'] = True  # Show button again
            st.rerun()
    elif 'error' in st.session_state:
        st.error(f"Failed to add entry: {st.session_state['error']}")
        if st.button("Home"):  # Changed to Home button
            st.session_state['page'] = 'Home'
            del st.session_state['error']
            st.rerun()

elif st.session_state['page'] == 'Record Checking':
    col1, col2 = st.columns([8, 1])  # Adjust ratio to give more space to title
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
    .home-button button { background: none; border: none; font-size: 16px; color: #666666; cursor: pointer; padding: 0; }
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
    col1, col2 = st.columns([8, 1])  # Adjust ratio to give more space to title
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
    .home-button button { background: none; border: none; font-size: 16px; color: #666666; cursor: pointer; padding: 0; }
    </style>
    """, unsafe_allow_html=True)
    st.header("Quick Responses")
    for response in quick_responses:
        st.write(response)
        copy_to_clipboard(response)
