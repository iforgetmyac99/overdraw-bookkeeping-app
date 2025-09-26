import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from io import BytesIO
import os
import re  # For extracting data from template
from datetime import datetime
from builtins import max
from st_clipboard import copy_to_clipboard  # New import for reliable clipboard copying

# Google Sheets config with environment variable support
@st.cache_resource
def load_gspread():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
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
    if st.button("Pending Orders"):
        st.session_state['page'] = 'Pending Orders'
        st.rerun()
    # Placeholder for future functions
    st.write("More functions will be added here later.")

# Pending Orders page
def pending_orders_page():
    st.title("Pending Orders")
    def go_home():
        st.session_state['page'] = 'Home'
    def refresh():
        st.rerun()
    # Place Home and Refresh buttons vertically aligned
    col1 = st.columns(1)[0]  # Single column for vertical alignment
    with col1:
        st.button("Home", key="home_button_pending", on_click=go_home)
        st.button("Refresh", key="refresh_button_pending", on_click=refresh)
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .home-button button { background: none; border: none; font-size: 16px; color: #666666; cursor: pointer; padding: 0; }
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
                st.rerun()
    else:
        st.write("No pending orders found.")

# Order Details page
def order_details_page():
    st.title("Order Details")
    def go_home():
        st.session_state['page'] = 'Home'
    def go_pending_orders():
        st.session_state['page'] = 'Pending Orders'
    # Place Return and Home buttons vertically aligned
    col1 = st.columns(1)[0]  # Single column for vertical alignment
    with col1:
        st.button("Return", key="return_button", on_click=go_pending_orders)
        st.button("Home", key="home_button_details", on_click=go_home)
    st.markdown("""
    <style>
    .stTextInput, .stTextArea { width: 100% !important; }
    .stDataFrame { width: 100%; overflow-x: auto; }
    .stDataFrame td, .stDataFrame th { white-space: normal !important; word-wrap: break-word !important; }
    .home-button button { background: none; border: none; font-size: 16px; color: #666666; cursor: pointer; padding: 0; }
    </style>
    """, unsafe_allow_html=True)

    if 'selected_order' not in st.session_state:
        st.error("No order selected. Please go back to Pending Orders.")
        return

    sheet = load_gspread()
    data = sheet.get_all_records()
    df = pd.DataFrame(data)
    order_row = df[df['Order'] == st.session_state['selected_order']].iloc[0]

    # Display order details with copy buttons (Shoe info combined)
    st.write(f"**Order Number:** {order_row['Order']}")
    st.write(f"**Item, Color, Size:** {order_row['Item']} (Color: {order_row['Color']}, Size: {order_row['Size']})")
    st.write(f"**Name:**")
    st.text_area("", value=order_row['Name'], height=50, disabled=True, key="name_box")
    if st.button("Copy Name"):
        copy_to_clipboard(order_row['Name'])
    st.write(f"**Phone:**")
    st.text_area("", value=order_row['Phone'], height=50, disabled=True, key="phone_box")
    if st.button("Copy Phone"):
        copy_to_clipboard(order_row['Phone'])
    st.write(f"**Address:**")
    st.text_area("", value=order_row['Address'], height=100, disabled=True, key="address_box")
    if st.button("Copy Address"):
        copy_to_clipboard(order_row['Address'])

    # SF Delivery Number input
    sf_input = st.text_input("Enter SF Delivery Number", key="sf_input")
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
        # Determine language based on entire row
        row_text = ' '.join(str(order_row[col]) for col in order_row.index)
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', row_text))
        if 'message_lang' not in st.session_state:
            st.session_state['message_lang'] = 'default'  # Initialize language state

        if has_chinese and st.session_state['message_lang'] in ['default', 'zh']:
            message = f"順豐number: {st.session_state['sf_delivery']}\nHello 鞋已經寄出咗了 收到嘅話麻煩比個五星好評 多謝支持🫡"
            st.text_area("", value=message, height=100, disabled=True, key="message_chinese")
            if st.button("Copy Message"):
                copy_to_clipboard(message)
            if st.button("English"):
                st.session_state['message_lang'] = 'en'
                st.rerun()
        else:
            message = f"SF Delivery Number: {st.session_state['sf_delivery']}\nHello shoes are sent. Please leave a 5 star review when receiving the product. Have a nice day."
            st.text_area("", value=message, height=100, disabled=True, key="message_english")
            if st.button("Copy Message"):
                copy_to_clipboard(message)
            if st.button("中文"):
                st.session_state['message_lang'] = 'zh'
                st.rerun()

        if st.button("Finish"):
            if update_order_status(st.session_state['selected_order'], "Delivered"):
                st.session_state['success'] = False
                st.session_state['page'] = 'Pending Orders'
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

elif st.session_state['page'] == 'Pending Orders':
    pending_orders_page()
elif st.session_state['page'] == 'Order Details':
    order_details_page()
elif st.session_state['page'] == 'Order Completed':
    order_completed_page()
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

