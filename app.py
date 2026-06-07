import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import pickle
from datetime import datetime
import random
import time
import base64
from supabase import create_client, Client
from streamlit_js_eval import get_geolocation

# ---------------------------------------------------------------
# Supabase Config
# ---------------------------------------------------------------
SUPABASE_URL = "https://zxeqlmahvtsbyxwyzvrs.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inp4ZXFsbWFodnRzYnl4d3l6dnJzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA3MDAwMTMsImV4cCI6MjA5NjI3NjAxM30.ECc31qYHfVfAvPjWyuhGO0b6fdPCuI9XcRKfFE3woW0"

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# ---------------------------------------------------------------
# DB Helpers
# ---------------------------------------------------------------
def db_get_user(username):
    res = supabase.table("users").select("*").eq("username", username).execute()
    return res.data[0] if res.data else None

def db_create_user(username, password, name, balance, pin, home_lat, home_lon):
    supabase.table("users").insert({
        "username": username, "password": password, "name": name,
        "balance": balance, "security_pin": pin,
        "home_lat": home_lat, "home_lon": home_lon,
        "card_frozen": False
    }).execute()

def db_update_user(username, data: dict):
    supabase.table("users").update(data).eq("username", username).execute()

def db_get_transactions(username):
    res = supabase.table("transactions").select("*").eq("username", username).order("created_at", desc=True).execute()
    return res.data or []

def db_add_transaction(username, merchant, amount, distance_km, fraud_prob, status):
    txn_time = datetime.now().strftime("%b %d, %Y %I:%M %p")
    supabase.table("transactions").insert({
        "username": username, "merchant": merchant, "amount": float(amount),
        "distance_km": float(distance_km), "fraud_prob": float(fraud_prob),
        "status": status, "txn_time": txn_time
    }).execute()

def db_get_notifications(username):
    res = supabase.table("notifications").select("*").eq("username", username).order("created_at", desc=True).execute()
    return res.data or []

def db_add_notification(username, ntype, merchant, amount, distance_km, fraud_prob, message):
    txn_time = datetime.now().strftime("%b %d, %Y %I:%M %p")
    supabase.table("notifications").insert({
        "username": username, "type": ntype, "merchant": merchant,
        "amount": float(amount), "distance_km": float(distance_km),
        "fraud_prob": float(fraud_prob), "txn_time": txn_time,
        "message": message, "is_read": False
    }).execute()

def db_mark_notifications_read(username):
    supabase.table("notifications").update({"is_read": True}).eq("username", username).execute()

# ---------------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------------
try:
    from PIL import Image
    favicon = Image.open("binpay_logo.png")
    st.set_page_config(page_title="BinPay - Secure Banking", page_icon=favicon,
                       layout="wide", initial_sidebar_state="collapsed")
except:
    st.set_page_config(page_title="BinPay - Secure Banking", page_icon="💳",
                       layout="wide", initial_sidebar_state="collapsed")

# ---------------------------------------------------------------
# Load Model
# ---------------------------------------------------------------
@st.cache_resource
def load_model():
    with open('best_fraud_model.pkl', 'rb') as f:
        model = pickle.load(f)
    with open('feature_columns.pkl', 'rb') as f:
        feature_columns = pickle.load(f)
    return model, feature_columns

model, feature_columns = load_model()

# ---------------------------------------------------------------
# Load Logo
# ---------------------------------------------------------------
def get_logo_base64():
    try:
        with open("binpay_logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

logo_b64 = get_logo_base64()

# ---------------------------------------------------------------
# Merchant Database
# ---------------------------------------------------------------
MERCHANTS = {
    "☕ Starbucks"        : {"lat": 39.7674, "lon": -84.2033, "city": "Dayton, OH"},
    "🛒 Walmart"          : {"lat": 39.7442, "lon": -84.1917, "city": "Dayton, OH"},
    "⛽ Shell Gas Station": {"lat": 39.7601, "lon": -84.1950, "city": "Dayton, OH"},
    "🎯 Target"           : {"lat": 39.7523, "lon": -84.2156, "city": "Dayton, OH"},
    "🍔 McDonald's"       : {"lat": 39.7589, "lon": -84.1916, "city": "Dayton, OH"},
    "💊 CVS Pharmacy"     : {"lat": 39.7634, "lon": -84.1887, "city": "Dayton, OH"},
    "🛍️ Kroger"           : {"lat": 39.7712, "lon": -84.2078, "city": "Dayton, OH"},
    "🍕 Pizza Hut"        : {"lat": 39.7556, "lon": -84.1998, "city": "Dayton, OH"},
    "✈️ LAX Airport Shop" : {"lat": 33.9425, "lon": -118.4081, "city": "Los Angeles, CA"},
    "🎰 Vegas Casino"     : {"lat": 36.1147, "lon": -115.1728, "city": "Las Vegas, NV"},
    "🗽 NYC Store"         : {"lat": 40.7128, "lon": -74.0060,  "city": "New York, NY"},
    "🌴 Miami Mall"       : {"lat": 25.7617, "lon": -80.1918,  "city": "Miami, FL"},
}

# ---------------------------------------------------------------
# Global CSS
# ---------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Plus Jakarta Sans', sans-serif !important; }
.stApp { background: linear-gradient(135deg, #eef3ff 0%, #f8fbff 100%) !important; animation: fadeIn 0.6s ease-in; }
@keyframes fadeIn { from {opacity:0;} to {opacity:1;} }
.glass { background: rgba(255,255,255,0.7); backdrop-filter: blur(14px); border-radius: 16px; border: 1px solid rgba(255,255,255,0.4); box-shadow: 0 8px 30px rgba(0,0,0,0.05); padding: 18px; }
.stButton > button { background: linear-gradient(135deg, #003087, #0072CE) !important; color: white !important; border-radius: 10px !important; font-weight: 600 !important; padding: 11px !important; border: none !important; transition: 0.25s !important; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,48,135,0.25); }
.stTextInput input, .stNumberInput input { border-radius: 10px !important; border: 1.5px solid #dbeafe !important; }
.stTabs [aria-selected="true"] { background: linear-gradient(135deg, #003087, #0072CE) !important; color: white !important; border-radius: 8px; }
.stTabs [aria-selected="false"] { color: #003087 !important; font-weight: 600 !important; }
[data-testid="metric-container"] { background: white; border-radius: 12px; padding: 16px; border: 1.5px solid #dbeafe; box-shadow: 0 2px 8px rgba(0,48,135,0.05); }
[data-testid="metric-container"] label { color: #003087 !important; font-weight: 700 !important; font-size: 14px !important; }
[data-testid="stMetricValue"] { color: #1e293b !important; font-weight: 800 !important; }
[data-testid="stMetricLabel"] { color: #003087 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1; dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    return R * 2 * np.arcsin(np.sqrt(a))

def get_fraud_probability(amount, phone_lat, phone_lon, txn_lat, txn_lon):
    distance_km     = haversine(phone_lat, phone_lon, txn_lat, txn_lon)
    amount_scaled   = (amount - 88.35) / 250.12
    time_scaled     = (50000 - 94813.86) / 47488.15
    distance_scaled = (distance_km - 27.5) / 95.0
    v_features      = {f'V{i}': 0.0 for i in range(1, 29)}
    feature_dict    = {
        'Time': time_scaled, 'Amount': amount_scaled, 'distance_km': distance_scaled,
        'phone_lat': phone_lat, 'phone_long': phone_lon,
        'txn_lat': txn_lat, 'txn_long': txn_lon,
    }
    feature_dict.update(v_features)
    arr = np.array([feature_dict.get(c, 0.0) for c in feature_columns]).reshape(1, -1)
    return model.predict_proba(arr)[0][1] * 100, distance_km

def generate_card_number(seed):
    random.seed(seed)
    return [str(random.randint(1000, 9999)) for _ in range(4)]

# ---------------------------------------------------------------
# Session State
# ---------------------------------------------------------------
defaults = {
    'logged_in': False, 'current_user': None, 'page': 'login',
    'pending_transaction': None, 'pin_attempts': 0, 'selected_merchant': None,
    'gps_saved': False, 'live_lat': None, 'live_lon': None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------------------------------------------------------------
# UI Helpers
# ---------------------------------------------------------------
def show_logo():
    if logo_b64:
        st.markdown(f'<div style="margin-top:24px;text-align:center;"><img src="data:image/png;base64,{logo_b64}" alt="BinPay" style="height:60px;"/></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:center;margin-top:24px;"><h1 style="color:#003087;font-size:2rem;font-weight:800;margin:0;">💳 BinPay</h1></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;color:#94a3b8;font-size:10px;letter-spacing:3px;text-transform:uppercase;margin:4px 0 20px 0;font-weight:600;">SECURE BANKING</p>', unsafe_allow_html=True)

def show_header(logged_in=False):
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:44px;object-fit:contain;filter:brightness(0) invert(1);" alt="BinPay"/>' if logo_b64 else '<h1 style="color:white;margin:0;font-size:1.8rem;font-weight:800;">💳 BinPay</h1>'
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#003087 0%,#0072CE 100%);padding:18px 32px 14px 32px;
                border-radius:0 0 20px 20px;box-shadow:0 4px 20px rgba(0,48,135,0.25);
                display:flex;align-items:center;justify-content:center;margin-bottom:4px;">
        {logo_html}
        <p style="color:rgba(255,255,255,0.7);font-size:10px;letter-spacing:3px;text-transform:uppercase;margin:0 0 0 12px;font-weight:600;align-self:flex-end;padding-bottom:2px;">SECURE BANKING</p>
    </div>""", unsafe_allow_html=True)
    if logged_in:
        col1, col2, col3 = st.columns([4, 1, 1])
        with col3:
            st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)
            if st.button("Sign Out"):
                st.query_params.clear()
                for key in defaults:
                    st.session_state[key] = defaults[key]
                st.rerun()

def show_card(user):
    groups      = generate_card_number(hash(user['username']))
    name        = user['name'].upper()
    status_text = "🔴 FROZEN" if user['card_frozen'] else "🟢 ACTIVE"
    op          = "opacity:0.5;" if user['card_frozen'] else ""
    st.markdown(f"""
<div style="{op}position:relative;background:linear-gradient(135deg,#003087 0%,#0072CE 60%,#2563eb 100%);
     border-radius:20px;padding:28px 30px;max-width:400px;margin:0 auto;
     box-shadow:0 16px 48px rgba(0,48,135,0.4),inset 0 1px 0 rgba(255,255,255,0.12);">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
    <span style="color:white;font-size:1.2rem;font-weight:800;letter-spacing:1px;">BinPay</span>
    <div style="display:flex;">
      <div style="width:24px;height:24px;background:rgba(255,210,0,0.9);border-radius:50%;"></div>
      <div style="width:24px;height:24px;background:rgba(255,140,0,0.7);border-radius:50%;margin-left:-9px;"></div>
    </div>
  </div>
  <div style="width:38px;height:28px;background:linear-gradient(135deg,#f5c518,#d4a017);border-radius:5px;margin-bottom:16px;"></div>
  <p style="color:rgba(255,255,255,0.4);font-size:9px;letter-spacing:2px;margin:0;text-transform:uppercase;">Card Number</p>
  <p style="color:white;font-size:1.1rem;letter-spacing:5px;font-family:monospace;margin:4px 0 18px 0;font-weight:500;">{groups[0]}  ••••  ••••  {groups[3]}</p>
  <div style="display:flex;justify-content:space-between;align-items:flex-end;">
    <div>
      <p style="color:rgba(255,255,255,0.4);font-size:9px;letter-spacing:1.5px;margin:0;text-transform:uppercase;">Card Holder</p>
      <p style="color:white;font-size:0.88rem;font-weight:700;margin:3px 0 0 0;">{name}</p>
    </div>
    <div>
      <p style="color:rgba(255,255,255,0.4);font-size:9px;letter-spacing:1.5px;margin:0;text-transform:uppercase;">Expires</p>
      <p style="color:white;font-size:0.88rem;margin:3px 0 0 0;font-weight:600;">12/28</p>
    </div>
    <div style="text-align:right;">
      <p style="color:white;font-size:1.1rem;font-style:italic;font-weight:700;font-family:serif;margin:0;">VISA</p>
      <p style="color:{'#ff6b6b' if user['card_frozen'] else '#4ade80'};font-size:10px;font-weight:700;margin:3px 0 0 0;">{status_text}</p>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

def show_gps_component():
    components.html("""<!DOCTYPE html><html><head>
<style>
  body{margin:0;padding:0;background:transparent;font-family:'Plus Jakarta Sans',sans-serif;}
  .box{background:#eff6ff;border:1.5px solid #bfdbfe;border-radius:10px;padding:14px;text-align:center;}
  .title{color:#003087;font-weight:700;margin:0 0 5px 0;font-size:14px;}
  .sub{color:#64748b;font-size:12px;margin:0 0 10px 0;}
  .btn{background:linear-gradient(135deg,#003087,#0072CE);color:white;border:none;border-radius:8px;padding:9px 18px;font-size:13px;font-weight:600;cursor:pointer;}
  .ok{color:#16a34a;font-weight:700;font-size:13px;margin:0 0 3px 0;}
  .coord{color:#003087;font-size:13px;margin:2px 0;font-weight:600;}
  .hint{color:#94a3b8;font-size:11px;margin-top:5px;}
</style></head><body>
<div class="box">
  <p class="title">📱 Real-Time Phone GPS</p>
  <p class="sub" id="s">Tap to detect your current location</p>
  <button class="btn" onclick="go()">📍 Detect My Location</button>
  <div id="r" style="display:none;margin-top:10px;">
    <p class="ok">✅ Location Detected!</p>
    <p class="coord" id="la"></p>
    <p class="coord" id="lo"></p>
    <p class="hint">Copy and paste into the fields below</p>
  </div>
</div>
<script>
function go(){
  var s=document.getElementById('s');
  s.innerHTML='⏳ Detecting...';s.style.color='#d97706';
  if(navigator.geolocation){
    navigator.geolocation.getCurrentPosition(
      function(p){
        var la=p.coords.latitude.toFixed(6),lo=p.coords.longitude.toFixed(6);
        s.innerHTML='';document.getElementById('r').style.display='block';
        document.getElementById('la').innerHTML='Latitude: '+la;
        document.getElementById('lo').innerHTML='Longitude: '+lo;
      },
      function(){s.innerHTML='❌ Location denied.';s.style.color='#dc2626';},
      {enableHighAccuracy:true,timeout:10000,maximumAge:0}
    );
  }else{s.innerHTML='❌ Use Chrome on your phone.';s.style.color='#dc2626';}
}
</script></body></html>""", height=180)

# ---------------------------------------------------------------
# AUTO GPS COMPONENT
# ---------------------------------------------------------------
def auto_detect_gps():
    """Auto-detects live GPS using streamlit-js-eval."""
    if st.session_state.get("gps_saved"):
        return

    location = get_geolocation()
    if location and "coords" in location:
        try:
            st.session_state.live_lat  = float(location["coords"]["latitude"])
            st.session_state.live_lon  = float(location["coords"]["longitude"])
            st.session_state.gps_saved = True
        except:
            pass

# ---------------------------------------------------------------
# LOGIN PAGE
# ---------------------------------------------------------------
def show_login_page():
    show_logo()
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div style="background:white;border-radius:18px;padding:36px 40px 28px 40px;
                    box-shadow:0 8px 28px rgba(0,48,135,0.1);border:1.5px solid #dbeafe;text-align:center;margin-bottom:16px;">
            <h2 style="color:#003087;margin:0 0 6px 0;font-size:1.55rem;font-weight:800;">Welcome Back</h2>
            <p style="color:#94a3b8;font-size:0.88rem;margin:0;">Sign in to your BinPay account</p>
        </div>""", unsafe_allow_html=True)

        username = st.text_input("Username", placeholder="Enter your username")
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        if st.button("Sign In to BinPay"):
            if not username or not password:
                st.error("Please enter your username and password.")
            else:
                user = db_get_user(username)
                if not user:
                    st.error("Account not found. Please create an account first.")
                elif user['password'] != password:
                    st.error("Incorrect password. Please try again.")
                else:
                    st.session_state.logged_in    = True
                    st.session_state.current_user = username
                    st.session_state.page         = 'dashboard'
                    st.rerun()

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.markdown('<p style="text-align:center;color:#94a3b8;font-size:13px;margin:0;">New to BinPay?</p>', unsafe_allow_html=True)
        st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
        if st.button("Create New Account"):
            st.session_state.page = 'signup'
            st.rerun()

# ---------------------------------------------------------------
# SIGNUP PAGE
# ---------------------------------------------------------------
def show_signup_page():
    show_logo()
    col1, col2, col3 = st.columns([0.8, 2.4, 0.8])
    with col2:
        st.markdown("""
        <div style="background:white;border-radius:18px;padding:30px 36px 22px 36px;
                    box-shadow:0 8px 28px rgba(0,48,135,0.1);border:1.5px solid #dbeafe;text-align:center;margin-bottom:16px;">
            <h2 style="color:#003087;margin:0 0 4px 0;font-size:1.5rem;font-weight:800;">Open a BinPay Account</h2>
            <p style="color:#94a3b8;font-size:0.85rem;margin:0;">Takes less than 2 minutes</p>
        </div>""", unsafe_allow_html=True)

        full_name = st.text_input("Full Name", placeholder="John Smith")
        col_a, col_b = st.columns(2)
        with col_a:
            username = st.text_input("Username", placeholder="Choose a username")
        with col_b:
            initial_balance = st.number_input("Opening Balance (USD)", min_value=100.0, max_value=100000.0, value=5000.0, step=100.0)
        col_c, col_d = st.columns(2)
        with col_c:
            password = st.text_input("Password", type="password", placeholder="Create a password")
        with col_d:
            confirm_pwd = st.text_input("Confirm Password", type="password", placeholder="Repeat password")

        security_pin = st.text_input("Security PIN", type="password", placeholder="Choose a 4 digit PIN",
                                     help="Requested when transaction is far from your phone")

        st.markdown("<p style='color:#64748b;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:8px 0;'>Your Phone GPS Location</p>", unsafe_allow_html=True)
        show_gps_component()
        st.caption("Detect location above, then paste coordinates below:")
        col_e, col_f = st.columns(2)
        with col_e:
            home_lat = st.number_input("Your Latitude", value=39.758900, format="%.6f")
        with col_f:
            home_lon = st.number_input("Your Longitude", value=-84.191600, format="%.6f")

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        if st.button("Open My BinPay Account"):
            if not all([full_name, username, password, confirm_pwd, security_pin]):
                st.error("Please fill in all fields.")
            elif password != confirm_pwd:
                st.error("Passwords do not match.")
            elif len(security_pin) < 4:
                st.error("Security PIN must be at least 4 digits.")
            elif db_get_user(username):
                st.error("Username already taken. Please choose another.")
            else:
                db_create_user(username, password, full_name, initial_balance, security_pin, home_lat, home_lon)
                st.success("Account created successfully! Please sign in.")
                st.balloons()
                time.sleep(2)
                st.session_state.page = 'login'
                st.rerun()

        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
        if st.button("← Back to Sign In"):
            st.session_state.page = 'login'
            st.rerun()

# ---------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------
def show_dashboard():
    username = st.session_state.current_user
    user     = db_get_user(username)
    if not user:
        st.error("Session error. Please sign in again.")
        st.session_state.logged_in = False
        st.rerun()

    show_header(logged_in=True)

    # Auto detect and update GPS location
    auto_detect_gps()

    notifications = db_get_notifications(username)
    unread        = [n for n in notifications if not n.get('is_read', False)]
    if unread:
        st.error(f"🚨 You have {len(unread)} new fraud alert(s)! Check the Fraud Alerts tab.")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    first_name = user['name'].split()[0]

    live_lat = st.session_state.get('live_lat')
    live_lon = st.session_state.get('live_lon')
    if live_lat and live_lon:
        gps_status = f"📍 Live Location Detected: {live_lat:.4f}, {live_lon:.4f}"
        gps_color  = "#16a34a"
    else:
        gps_status = "⏳ Detecting your location... (allow location access in browser)"
        gps_color  = "#d97706"

    st.markdown(f"""
    <div style="padding:0 4px 18px 4px;">
        <h2 style="color:#003087;font-size:1.5rem;font-weight:800;margin:0;">Good day, <span style="color:#0072CE;">{first_name}</span> 👋</h2>
        <p style="color:{gps_color};margin:4px 0 0 0;font-size:0.88rem;font-weight:600;">{gps_status}</p>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Dashboard", "💸 Make Payment", "📋 Transactions", "🚨 Fraud Alerts", "⚙️ Card Settings"
    ])

    # TAB 1: DASHBOARD
    with tab1:
        transactions  = db_get_transactions(username)
        total_spent   = sum(float(t['amount']) for t in transactions if t['status'] != 'BLOCKED')
        blocked_count = sum(1 for t in transactions if t['status'] == 'BLOCKED')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Available Balance", f"${float(user['balance']):,.2f}")
        with col2:
            st.metric("📤 Total Spent", f"${total_spent:,.2f}")
        with col3:
            st.metric("🚫 Blocked", str(blocked_count))

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        col_left, col_right = st.columns([1.1, 1])
        with col_left:
            st.markdown("<p style='color:#64748b;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 10px 0;'>Your BinPay Card</p>", unsafe_allow_html=True)
            show_card(user)
        with col_right:
            card_status = "🔴 FROZEN" if user['card_frozen'] else "🟢 ACTIVE"
            st.markdown(f"""
            <div style="background:white;border:1.5px solid #dbeafe;border-radius:14px;padding:18px;box-shadow:0 2px 8px rgba(0,48,135,0.05);">
                <div style="padding:9px 0;border-bottom:1px solid #f1f5f9;">
                    <p style="color:#94a3b8;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:0;">Card Status</p>
                    <p style="color:#1e293b;font-weight:700;margin:4px 0 0 0;font-size:14px;">{card_status}</p>
                </div>
                <div style="padding:9px 0;border-bottom:1px solid #f1f5f9;">
                    <p style="color:#94a3b8;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:0;">GPS Protection</p>
                    <p style="color:#16a34a;font-weight:700;margin:4px 0 0 0;font-size:14px;">🛡️ Active</p>
                </div>
                <div style="padding:9px 0;">
                    <p style="color:#94a3b8;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:0;">Fraud Detection</p>
                    <p style="color:#0072CE;font-weight:700;margin:4px 0 0 0;font-size:14px;">🤖 XGBoost Active</p>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("<p style='color:#64748b;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 10px 0;'>Recent Transactions</p>", unsafe_allow_html=True)
        if transactions:
            for t in transactions[:5]:
                color = "#16a34a" if t['status'] == 'APPROVED' else "#d97706" if t['status'] == 'PIN VERIFIED' else "#dc2626"
                icon  = "✅" if t['status'] == 'APPROVED' else "🔐" if t['status'] == 'PIN VERIFIED' else "🚫"
                col_a, col_b, col_c = st.columns([3, 1, 1])
                with col_a:
                    st.markdown(f"<p style='color:#1e293b;font-weight:600;margin:0;font-size:14px;'>{icon} {t['merchant']}</p>", unsafe_allow_html=True)
                    st.caption(t['txn_time'])
                with col_b:
                    st.markdown(f"<p style='color:#003087;font-weight:700;margin:0;font-size:14px;'>${float(t['amount']):.2f}</p>", unsafe_allow_html=True)
                with col_c:
                    st.markdown(f"<span style='color:{color};font-weight:700;font-size:12px;'>{t['status']}</span>", unsafe_allow_html=True)
                st.divider()
        else:
            st.info("No transactions yet. Go to Make Payment to get started!")

    # TAB 2: MAKE PAYMENT
    with tab2:
        if user['card_frozen']:
            st.error("🔴 Your card is frozen. Go to Card Settings to unfreeze it.")
        else:
            st.markdown("<p style='color:#64748b;font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;margin:0 0 8px 0;'>Select Merchant</p>", unsafe_allow_html=True)
            merchant_name = st.selectbox("Choose a merchant", list(MERCHANTS.keys()), label_visibility="collapsed")
            merchant      = MERCHANTS[merchant_name]

            st.markdown(f"""
            <div style="background:#eff6ff;border:1.5px solid #bfdbfe;border-radius:12px;padding:14px 18px;margin:12px 0;">
                <p style="color:#003087;font-weight:700;margin:0;font-size:14px;">{merchant_name}</p>
                <p style="color:#64748b;font-size:12px;margin:4px 0 0 0;">📍 {merchant['city']}</p>
            </div>""", unsafe_allow_html=True)

            amount = st.number_input("Amount (USD)", min_value=1.0, max_value=float(user['balance']), value=50.0, step=1.0)

            if st.button("💳 Process Payment"):
                # Use live session GPS if available, else fall back to saved location
                user_lat = st.session_state.live_lat or float(user['home_lat'])
                user_lon = st.session_state.live_lon or float(user['home_lon'])
                fraud_prob, distance_km = get_fraud_probability(
                    amount, user_lat, user_lon,
                    merchant['lat'], merchant['lon']
                )
                txn = {
                    'merchant': merchant_name, 'amount': amount,
                    'distance_km': round(distance_km, 1),
                    'fraud_prob': round(fraud_prob, 1),
                    'time': datetime.now().strftime("%b %d, %Y %I:%M %p")
                }

                if distance_km > 25:
                    # Far merchant — ask PIN regardless of fraud score
                    st.session_state.pending_transaction = txn
                    st.session_state.pin_attempts        = 0
                    st.warning(f"📍 Merchant is {distance_km:.1f} km from your phone. PIN required.")
                    st.rerun()
                elif fraud_prob > 85:
                    # Nearby but very high fraud score — block
                    db_add_transaction(username, merchant_name, amount, round(distance_km,1), round(fraud_prob,1), 'BLOCKED')
                    db_add_notification(username, "HIGH FRAUD RISK", merchant_name, amount,
                                        round(distance_km,1), round(fraud_prob,1),
                                        f"Transaction blocked. ML fraud score: {fraud_prob:.1f}%")
                    db_update_user(username, {"card_frozen": True})
                    st.error(f"🚫 Transaction BLOCKED! Fraud score {fraud_prob:.1f}%. Card frozen.")
                    st.rerun()
                else:
                    # Nearby and low fraud — approve
                    new_balance = float(user['balance']) - amount
                    db_update_user(username, {"balance": new_balance})
                    db_add_transaction(username, merchant_name, amount, round(distance_km,1), round(fraud_prob,1), 'APPROVED')
                    st.success(f"✅ Payment of ${amount:.2f} to {merchant_name} approved!")
                    st.rerun()

            # PIN verification
            if st.session_state.pending_transaction:
                txn = st.session_state.pending_transaction
                st.markdown("---")
                st.markdown(f"<p style='color:#d97706;font-weight:700;'>🔐 PIN required for ${txn['amount']:.2f} at {txn['merchant']}</p>", unsafe_allow_html=True)
                pin_input = st.text_input("Enter Security PIN", type="password", key="pin_input")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("✅ Confirm"):
                        if pin_input == user.get('security_pin', ''):
                            new_balance = float(user['balance']) - txn['amount']
                            db_update_user(username, {"balance": new_balance})
                            db_add_transaction(username, txn['merchant'], txn['amount'],
                                               txn['distance_km'], txn['fraud_prob'], 'PIN VERIFIED')
                            st.session_state.pending_transaction = None
                            st.session_state.pin_attempts        = 0
                            st.success(f"✅ Payment confirmed via PIN!")
                            st.rerun()
                        else:
                            st.session_state.pin_attempts += 1
                            remaining = 3 - st.session_state.pin_attempts
                            if remaining <= 0:
                                db_add_transaction(username, txn['merchant'], txn['amount'],
                                                   txn['distance_km'], txn['fraud_prob'], 'BLOCKED')
                                db_add_notification(username, "CARD FROZEN", txn['merchant'], txn['amount'],
                                                    txn['distance_km'], txn['fraud_prob'],
                                                    f"3 incorrect PIN attempts at {txn['merchant']}. Card frozen automatically.")
                                db_update_user(username, {"card_frozen": True})
                                st.session_state.pending_transaction = None
                                st.session_state.pin_attempts        = 0
                                st.error("🚫 Card frozen after 3 wrong PIN attempts.")
                                st.rerun()
                            else:
                                st.error(f"Wrong PIN. {remaining} attempt(s) remaining.")
                with col_no:
                    if st.button("❌ Cancel"):
                        st.session_state.pending_transaction = None
                        st.session_state.pin_attempts        = 0
                        st.rerun()

    # TAB 3: TRANSACTIONS
    with tab3:
        transactions = db_get_transactions(username)
        st.markdown(f"""
        <div style="background:white;border:1.5px solid #dbeafe;border-radius:12px;padding:16px 18px;margin-bottom:18px;box-shadow:0 2px 8px rgba(0,48,135,0.05);">
            <h3 style="color:#003087;font-weight:800;margin:0 0 3px 0;font-size:1rem;">📋 Transaction History</h3>
            <p style="color:#64748b;margin:0;font-size:13px;">{len(transactions)} total transactions</p>
        </div>""", unsafe_allow_html=True)

        if transactions:
            for t in transactions:
                color = "#16a34a" if t['status'] == 'APPROVED' else "#d97706" if t['status'] == 'PIN VERIFIED' else "#dc2626"
                badge = "✅ APPROVED" if t['status'] == 'APPROVED' else "🔐 PIN VERIFIED" if t['status'] == 'PIN VERIFIED' else "🚫 BLOCKED"
                col_a, col_b, col_c, col_d = st.columns([3, 1, 1, 1])
                with col_a:
                    st.markdown(f"<p style='color:#1e293b;font-weight:600;margin:0;font-size:14px;'>{t['merchant']}</p>", unsafe_allow_html=True)
                    st.caption(t['txn_time'])
                with col_b:
                    st.markdown(f"<p style='color:#003087;font-weight:700;margin:0;font-size:14px;'>${float(t['amount']):.2f}</p>", unsafe_allow_html=True)
                with col_c:
                    st.caption(f"📍 {t['distance_km']} km")
                    st.caption(f"🤖 {t['fraud_prob']}%")
                with col_d:
                    st.markdown(f"<span style='color:{color};font-weight:700;font-size:12px;'>{badge}</span>", unsafe_allow_html=True)
                st.divider()
        else:
            st.info("No transactions yet. Go to Make Payment to get started!")

    # TAB 4: FRAUD ALERTS
    with tab4:
        notifications = db_get_notifications(username)
        st.markdown("""
        <div style="background:#fef2f2;border:1.5px solid #fecaca;border-radius:12px;padding:16px 18px;margin-bottom:18px;">
            <h3 style="color:#991b1b;font-weight:800;margin:0 0 3px 0;font-size:1rem;">🚨 Fraud Alert Center</h3>
            <p style="color:#64748b;margin:0;font-size:13px;">Real-time notifications for suspicious activity</p>
        </div>""", unsafe_allow_html=True)

        if notifications:
            db_mark_notifications_read(username)
            for n in notifications:
                st.error(f"🚨 **{n['type']}** — {n['txn_time']}")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Merchant", n['merchant'])
                with col_b:
                    st.metric("Amount", f"${float(n['amount']):.2f}")
                with col_c:
                    st.metric("Distance", f"{n['distance_km']} km")
                st.markdown(f"**Details:** {n['message']}")
                st.markdown(f"**ML Fraud Score:** {n['fraud_prob']}%")
                st.divider()
        else:
            st.success("✅ No fraud alerts. Your account is secure.")

    # TAB 5: CARD SETTINGS
    with tab5:
        st.markdown("""
        <div style="background:white;border:1.5px solid #dbeafe;border-radius:12px;padding:16px 18px;margin-bottom:18px;box-shadow:0 2px 8px rgba(0,48,135,0.05);">
            <h3 style="color:#003087;font-weight:800;margin:0 0 3px 0;font-size:1rem;">⚙️ Card Security Settings</h3>
        </div>""", unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            if user['card_frozen']:
                st.error("🔴 Your card is currently FROZEN")
                if st.button("🔓 Unfreeze My Card"):
                    db_update_user(username, {"card_frozen": False})
                    st.success("Your card has been unfrozen!")
                    st.rerun()
            else:
                st.success("🟢 Your card is ACTIVE")
                if st.button("🔒 Freeze My Card"):
                    db_update_user(username, {"card_frozen": True})
                    st.warning("Your card has been frozen for security.")
                    st.rerun()

        with col2:
            st.caption("Detect GPS and paste coordinates to update your location.")
            show_gps_component()
            new_lat = st.number_input("Paste Latitude Here", value=float(user['home_lat']), format="%.6f", key="settings_lat")
            new_lon = st.number_input("Paste Longitude Here", value=float(user['home_lon']), format="%.6f", key="settings_lon")
            if st.button("📍 Save My Location"):
                db_update_user(username, {"home_lat": new_lat, "home_lon": new_lon})
                st.success(f"Location saved! {new_lat:.4f}, {new_lon:.4f}")
                st.rerun()

        st.markdown("---")
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.markdown("""<div style="background:#f0fdf4;border:1.5px solid #bbf7d0;border-radius:12px;padding:20px;text-align:center;">
                <div style="font-size:1.8rem;">✅</div>
                <p style="color:#16a34a;font-weight:800;font-size:13px;margin:8px 0 4px 0;">AUTO APPROVED</p>
                <p style="color:#475569;font-size:12px;margin:0;">Phone within 25 km</p>
                <p style="color:#16a34a;font-weight:700;margin:6px 0 0 0;font-size:12px;">No PIN needed</p>
            </div>""", unsafe_allow_html=True)
        with col_b:
            st.markdown("""<div style="background:#fffbeb;border:1.5px solid #fde68a;border-radius:12px;padding:20px;text-align:center;">
                <div style="font-size:1.8rem;">🔐</div>
                <p style="color:#d97706;font-weight:800;font-size:13px;margin:8px 0 4px 0;">PIN REQUIRED</p>
                <p style="color:#475569;font-size:12px;margin:0;">Phone more than 25 km away</p>
                <p style="color:#d97706;font-weight:700;margin:6px 0 0 0;font-size:12px;">Enter Security PIN</p>
            </div>""", unsafe_allow_html=True)
        with col_c:
            st.markdown("""<div style="background:#fef2f2;border:1.5px solid #fecaca;border-radius:12px;padding:20px;text-align:center;">
                <div style="font-size:1.8rem;">🚫</div>
                <p style="color:#dc2626;font-weight:800;font-size:13px;margin:8px 0 4px 0;">CARD FROZEN</p>
                <p style="color:#475569;font-size:12px;margin:0;">3 wrong PIN attempts</p>
                <p style="color:#dc2626;font-weight:700;margin:6px 0 0 0;font-size:12px;">Fraud alert sent</p>
            </div>""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# APP ROUTER
# ---------------------------------------------------------------

# Restore session from query params on refresh
if not st.session_state.logged_in:
    qp_user = st.query_params.get("user")
    qp_lat  = st.query_params.get("lat")
    qp_lon  = st.query_params.get("lon")
    if qp_user:
        user_check = db_get_user(qp_user)
        if user_check:
            st.session_state.logged_in    = True
            st.session_state.current_user = qp_user
            st.session_state.page         = 'dashboard'
            if qp_lat and qp_lon:
                try:
                    st.session_state.live_lat  = float(qp_lat)
                    st.session_state.live_lon  = float(qp_lon)
                    st.session_state.gps_saved = True
                except:
                    pass

if not st.session_state.logged_in:
    if st.session_state.page == 'signup':
        show_signup_page()
    else:
        show_login_page()
else:
    # Keep user in query params so refresh restores session
    if st.session_state.current_user:
        existing_params = dict(st.query_params)
        existing_params["user"] = st.session_state.current_user
        st.query_params.update(existing_params)
    show_dashboard()