import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import re
from datetime import datetime
import time

# === Copybox Helper Function Start === #
# === Copybox Helper Function – FIXED with visible clipboard icon ===
def copyable_box(text: str, height: int = 150, key=None):
    st.text_area(
        "",
        value=text,
        height=height,
        key=key,
        label_visibility="collapsed",
        help="Click the clipboard icon to copy"   # ← THIS LINE IS REQUIRED
    )
# === Copybox Helper Function End === #

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

def go_back_to_pending():
    get_pending_df.clear()
    st.session_state.page = "Pending Orders"
    st.rerun()
def go_back_to_pending():
    get_pending_df.clear()  # clear cache so list refreshes
    st.session_state.page = "Pending Orders"
    st.rerun()
    
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

# === EXTRACT DATA FROM TEMPLATE - FINAL & BULLETPROOF ===
def extract_data(template_text):
    sheet = load_journal_sheet()
    all_values = sheet.get_all_values()

    # --- Generate next ODxxx number ---
    order_num = "OD001"
    if len(all_values) > 1:
        df = pd.DataFrame(all_values[1:], columns=all_values[0])
        if 'Order' in df.columns and not df.empty:
            existing = df['Order'].astype(str).str.strip()
            od_nums = [int(x[2:]) for x in existing if re.match(r'^OD\d{3}$', x)]
            if od_nums:
                order_num = f"OD{max(od_nums)+1:03d}"

    date = datetime.now().strftime("%d/%m/%Y")
    status = "Pending"
    sf_delivery_number = ""

    item = color = size = name = phone = address = carousell_id = ""

    # Split into lines and clean
    lines = [line.strip() for line in template_text.split('\n') if line.strip()]

    for line in lines:
        low = line.lower()

        # Shoe name — stop at known keywords to avoid "Worn shoes..." line
        if any(k in low for k in ['shoe:', '鞋款', 'item:', 'shoes:']) and 'worn' not in low and 'return' not in low:
            item = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            # Clean common junk
            item = re.sub(r'(?i)warm reminder.*|worn shoes.*|refund.*', '', item, flags=re.DOTALL).strip()

        elif any(k in low for k in ['color', '顏色']):
            color = line.split(':', 1)[-1].split('：', 1)[-1].strip()

        elif any(k in low for k in ['size', '碼數', 'eu', 'us']):
            m = re.search(r'\d+[.,]?\d*', line)
            size = m.group(0) if m else ""

        elif any(k in low for k in ['name', '姓名']):
            name = line.split(':', 1)[-1].split('：', 1)[-1].strip()

        elif any(k in low for k in ['phone', '電話', 'tel']):
            m = re.search(r'\d{8,}', line)
            phone = m.group(0) if m else ""

        elif any(k in low for k in ['address', '地址']):
            addr = line.split(':', 1)[-1].split('：', 1)[-1].strip()
            # Stop address from including payment/reminder lines
            address = re.sub(r'(?i)payment.*|warm reminder.*|worn shoes.*|refund.*', '', addr).strip()

    # Fallback: if item still empty, try first non-empty line that looks like a product
    if not item and lines:
        for line in lines[:5]:  # only check first 5 lines
            if re.match(r'.*[a-zA-Z].*', line) and len(line) > 10 and 'color' not in line.lower():
                item = line.strip()
                break

    carousell_id = name or "Unknown"

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


# === QUICK RESPONSES === #
# === QUICK RESPONSES - EXACT STYLE AS YOUR PHOTO ===
def quick_responses_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Quick Responses")
    with col2:
        st.button("Home", key="home_quick", on_click=go_home)

    def copy_box(text, height=120):
        st.text_area(
            "", 
            value=text.strip(), 
            height=height,
            key=f"copy_{hash(text)}",
            label_visibility="collapsed",
            help="Click the copy icon to copy"
        )

    try:
        sheet = load_response_sheet()
        data = sheet.get("B2:F4")
        if len(data) < 3:
            st.error("Response sheet missing data")
            return

        headers = [h.strip().lower() for h in data[0]]
        zh_row, en_row = data[1], data[2]

        def get_col(name):
            try: return headers.index(name.lower())
            except: return -1

        e, o, p, s = get_col("enquiry"), get_col("order"), get_col("payment"), get_col("success")
        if -1 in (e, o, p, s):
            st.error("Missing columns in Response sheet")
            return

        zh = [zh_row[e], zh_row[o], zh_row[p], zh_row[s]]
        en = [en_row[e], en_row[o], en_row[p], en_row[s]]
        titles = ["Enquiry", "Order", "Payment", "Success"]

        tab_zh, tab_en = st.tabs(["中文", "English"])

        with tab_zh:
            for title, text in zip(titles, zh):
                st.markdown(f"**{title}**")
                copy_box(text, height=160 if "Enquiry" in title else 180 if "Order" in title else 130)

        with tab_en:
            for title, text in zip(titles, en):
                st.markdown(f"**{title}**")
                copy_box(text, height=160 if "Enquiry" in title else 180 if "Order" in title else 130)

    except Exception as e:
        st.error("Failed to load responses")
        st.code(str(e))
        
# === STOCK TAKING PAGE ===
def stock_taking_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Stock Taking")
    with col2:
        st.button("Home", key="home_stock", on_click=go_home)

    st.markdown("**Enter: Product → Cost → Price (newline or tab-separated)**")
    st.code("Nike Air Force\n280\n580\n\nAdidas Ultraboost[TAB]320[TAB]680", language="text")

    input_text = st.text_area(
        "",
        value=st.session_state.get("stock_input", ""),
        height=250,
        key="stock_input",
        label_visibility="collapsed",
        placeholder="Paste or type here..."
    )

    # Only Add button (full width)
    if st.button("Add to Stock Sheet", type="primary", use_container_width=True, key="add_stock"):
        lines = [l.strip() for l in input_text.splitlines() if l.strip()]
        if not lines:
            st.error("No data entered")
            st.stop()

        entries = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if '\t' in line:
                parts = [p.strip() for p in line.split('\t')]
                product = parts[0]
                cost = parts[1] if len(parts) > 1 else ""
                price = parts[2] if len(parts) > 2 else ""
                i += 1
            else:
                product = line
                i += 1
                cost = lines[i].strip() if i < len(lines) else ""
                i += 1
                price = lines[i].strip() if i < len(lines) else ""
                i += 1

            try:
                cost_val = float(cost) if cost else 0.0
                price_val = float(price) if price else 0.0
            except ValueError:
                st.error(f"Invalid number: {product} → Cost: {cost} | Price: {price}")
                st.stop()

            entries.append((product, cost_val, price_val))

        sheet = load_stock_sheet()
        df = pd.DataFrame(sheet.get_all_records() or [])
        next_id = int(df['ID'].max()) + 1 if not df.empty and 'ID' in df.columns else 1

        for product, cost, price in entries:
            sheet.append_row([next_id, product, cost, price])
            next_id += 1

        st.success(f"Successfully added {len(entries)} item(s)!")
        del st.session_state.stock_input  # auto-clear after success

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
# === ORDER DETAILS PAGE - BACK BUTTONS FIXED ===
def order_details_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Order Details")
    with col2:
        st.button("Home", key="home_details", on_click=go_home)

    # ← Back button at top (always visible)
    if st.button("← Back"):
        st.session_state.page = "Pending Orders"
        get_pending_df.clear()
        st.rerun()

    if 'selected_order' not in st.session_state:
        st.error("No order selected.")
        return

    sheet = load_journal_sheet()
    all_data = sheet.get_all_values()
    if len(all_data) < 2: return

    headers = all_data[0]
    df = pd.DataFrame(all_data[1:], columns=headers)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    row = df[df['Order'] == st.session_state['selected_order']].iloc[0]

    st.markdown("**Order Number**"); st.code(row['Order'])
    st.markdown("**Item • Color • Size**"); st.code(f"{row['Item']} (Color: {row['Color']}, Size: {row['Size']})")
    st.markdown("**Carousell ID**"); st.code(row.get('Carousell ID', ''))
    st.markdown("**Phone**"); st.code(row['Phone'])
    st.markdown("**Address**"); st.code(row['Address'])

    sf_input = st.text_input("Enter SF Delivery Number", key="sf_input")

    if st.button("Submit SF Number & Mark as Delivered", type="primary", use_container_width=True):
        if not sf_input.strip():
            st.error("Enter SF number.")
            st.stop()

        if update_sf_delivery(st.session_state['selected_order'], sf_input.strip()):
            st.success("SF number saved → Status changed to **Delivered**")

            msg = f"SF Delivery Number: {sf_input.strip()}\nHello shoes are sent. Please leave a 5-star review! Thank you!"
            copyable_box(msg, height=110)

            st.button(
                "← Back to Pending Orders",
                type="primary",
                use_container_width=True,
                on_click=go_back_to_pending
            )
        else:
            st.error("Update failed.")

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
    template_text = st.text_area("Paste customer message here", value=st.session_state.get('input_text', ""), height=250, key="template_text", label_visibility="collapsed")
    
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
# === RECORD CHECKING - SPLIT INTO ORDER & STOCK ===
def record_checking_page():
    col1, col2 = st.columns([8, 1])
    with col1:
        st.title("Record Checking")
    with col2:
        st.button("Home", key="home_record", on_click=go_home)

    tab1, tab2 = st.tabs(["Order Record", "Stock Record"])

    with tab1:
        st.header("Search Order Records (Journal Sheet)")
        query = st.text_input("Search Order (Carousell ID, Phone, Item, etc.)", key="order_search")
        if st.button("Search Orders"):
            if query:
                results = search_sheet(query)
                if not results.empty:
                    st.dataframe(results, use_container_width=True)
                else:
                    st.info("No matching orders found.")
            else:
                st.warning("Enter search term.")

    with tab2:
        st.header("Search Stock Records (Stock Sheet)")
        stock_query = st.text_input("Search Stock (Product Name)", key="stock_search")
        if st.button("Search Stock"):
            if stock_query:
                stock_sheet = load_stock_sheet()
                data = stock_sheet.get_all_records()
                df = pd.DataFrame(data)
                results = df[df.apply(lambda row: stock_query.lower() in ' '.join(str(v).lower() for v in row.values), axis=1)]
                if not results.empty:
                    st.dataframe(results, use_container_width=True)
                else:
                    st.info("No matching stock found.")
            else:
                st.warning("Enter product name.")

@st.cache_resource
def load_response_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key('10CLEJyH7LGkZrVjc8EiicJ2PCBY_se7gALChd_YyaCg').worksheet("Response")
    return sheet
    
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
