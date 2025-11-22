from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from selenium.webdriver.chrome.options import Options
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import io
import base64
from models import db, User, FarmerInput, CommunityPost, MarketPrice
import glob
import random
import json
import numpy as np
# --- Setup Chrome Driver ---

import matplotlib
matplotlib.use('Agg') # Prevents GUI errors

chrome_options = Options()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
# chrome_options.add_argument('--headless')  # Run in background


# REMOVE: Service(ChromeDriverManager().install())
# REPLACE WITH: Service() 
# Selenium will handle the driver download automatically.
service = Service() 

# chrome_options = Options()
# chrome_options.add_argument('--start-maximized')
# chrome_options.add_argument('--disable-blink-features=AutomationControlled')
# chrome_options.add_argument('--headless')  # Run in background

# Mock data for demonstration
MOCK_CROPS = []
MOCK_STATES = []
MOCK_MANDIS = ['Delhi Azadpur', 'Mumbai APMC', 'Bangalore Yeshwanthpur', 'Ludhiana Mandi']

# Mock price data
MOCK_PRICES = [
    {'state': 'Punjab', 'APMC': 'Ludhiana Mandi', 'Commodity': 'Wheat', 'Min_Price': 2000, 'Modal_Price': 2150, 'Max_Price': 2300},
    {'state': 'Haryana', 'APMC': 'Delhi Azadpur', 'Commodity': 'Rice', 'Min_Price': 3000, 'Modal_Price': 3200, 'Max_Price': 3400},
    {'state': 'Maharashtra', 'APMC': 'Mumbai APMC', 'Commodity': 'Cotton', 'Min_Price': 7000, 'Modal_Price': 7500, 'Max_Price': 8000},
]


def get_bar_chart_data(master_df, state_name, commodity_name):
    try:
        if master_df.empty:
            return None

        # Clean Data: Convert Price to Numeric
        # Create a copy to avoid SettingWithCopy warnings on the original master_df
        df = master_df.copy()
        df['Modal_Price'] = pd.to_numeric(df['Modal_Price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        # Standardize strings
        state_name = state_name.strip().upper()
        commodity_name = commodity_name.strip() # Case sensitive matching usually required for exact match

        # 1. Filter for Commodity (All India)
        national_df = df[df['Commodity'] == commodity_name].copy()
        
        if national_df.empty:
            return None

        # Calculate Averages
        national_avg = round(national_df['Modal_Price'].mean(), 2)
        
        # Filter for State
        state_df = national_df[national_df['state'].str.upper() == state_name].copy()
        
        # Handle case where state might not have data for this crop
        if state_df.empty:
            state_avg = 0
            state_top_10 = []
            state_labels = []
        else:
            state_avg = round(state_df['Modal_Price'].mean(), 2)
            # Get Cheapest 10 in State
            state_sorted = state_df.sort_values(by='Modal_Price', ascending=True).head(10)
            state_labels = state_sorted['APMC'].tolist()
            state_top_10 = state_sorted['Modal_Price'].tolist()

        # Get Cheapest 10 in India
        national_sorted = national_df.sort_values(by='Modal_Price', ascending=True).head(10)
        national_labels = national_sorted.apply(lambda x: f"{x['APMC']}, {x['state']}", axis=1).tolist()
        national_top_10 = national_sorted['Modal_Price'].tolist()

        return {
            "state_name": state_name,
            "national_avg": national_avg,
            "state_avg": state_avg,
            "state_chart": {
                "labels": state_labels,
                "data": state_top_10
            },
            "national_chart": {
                "labels": national_labels,
                "data": national_top_10
            }
        }

    except Exception as e:
        print(f"Bar Chart Data Error: {e}")
        return None

# --- Helper Function to Generate Historical Graph ---
def get_historical_data(state_name, commodity_name):
    try:
        csv_path = 'D:/STUDY/IITB MS/CS 699/project/krishimitra/data/agmarknet_india_historical_prices_2024_2025.csv' 
        if not os.path.exists(csv_path):
            return None, "Dataset not found."

        df = pd.read_csv(csv_path)

        # Standardize text
        state_name = state_name.strip().lower()
        commodity_name = commodity_name.strip().lower()
        
        # Clean Data
        df['State'] = df['State'].str.strip()
        df['Commodity'] = df['Commodity'].str.strip()
        df['Price Date'] = pd.to_datetime(df['Price Date'], format='%d %b %Y', errors='coerce')
        df = df.sort_values('Price Date')
        
        # Create Month Column (YYYY-MM) for grouping
        df['Month'] = df['Price Date'].dt.to_period('M').astype(str)

        # 1. Filter for Specific Crop (All India)
        crop_df = df[df['Commodity'].str.lower() == commodity_name].copy()
        
        if crop_df.empty:
            return None, "Historical Price for this crop is not available"

        # 2. Calculate National Average (All India Trend)
        national_avg = crop_df.groupby('Month')['Modal Price (Rs./Quintal)'].mean().round(2)

        # 3. Filter for Specific State
        state_df = crop_df[crop_df['State'].str.lower() == state_name].copy()
        
        if state_df.empty:
            return None, f"No data found for {commodity_name} in {state_name}"

        # 4. Calculate State Average
        state_avg = state_df.groupby('Month')['Modal Price (Rs./Quintal)'].mean().round(2)

        # 5. Prepare Market-wise Data
        market_data = {}
        unique_markets = state_df['Market Name'].unique()
        
        for market in unique_markets:
            m_df = state_df[state_df['Market Name'] == market]
            m_avg = m_df.groupby('Month')['Modal Price (Rs./Quintal)'].mean().round(2)
            # Convert to dict mapping Month -> Price
            market_data[market] = m_avg.to_dict()

        # 6. Consolidate all unique months (Labels)
        all_months = sorted(list(set(national_avg.index) | set(state_avg.index)))

        # 7. Align Data to Labels (Fill missing months with None)
        def align_data(source_series, labels):
            return [source_series.get(month, None) for month in labels]

        final_data = {
            "labels": all_months,
            "national": align_data(national_avg, all_months),
            "state": align_data(state_avg, all_months),
            "markets": {},
            "market_list": sorted(unique_markets.tolist()),
            "state_name": state_name.title(),
            "commodity_name": commodity_name.title()
        }

        for market, data_dict in market_data.items():
            # Manually align market dictionary to the master month list
            aligned_market = [data_dict.get(month, None) for month in all_months]
            final_data["markets"][market] = aligned_market

        return final_data, None

    except Exception as e:
        print(f"Data Error: {e}")
        return None, "Error processing data"
    

# ... (Keep your extract_commodity_list and extract_commodity_data functions EXACTLY as they were) ...
def extract_commodity_list():
    # ... [Insert your existing extraction code here] ...
    # For brevity I am assuming you keep the code you provided previously
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        url = 'https://enam.gov.in/web/dashboard/live_price'
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        commodity_radio = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='colorRadio' and @value='blue']")))
        driver.execute_script("arguments[0].scrollIntoView(true);", commodity_radio)
        commodity_radio.click()
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        select = soup.find('select', {'id': 'min_max_commodity'})
        dropdown = wait.until(EC.presence_of_element_located((By.ID, "min_max_commodity")))
        select = Select(dropdown)
        wait.until(lambda d: len(Select(dropdown).options) > 1)
        select.select_by_visible_text("-- All --")
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find_all("tbody", class_=lambda c: c and "tbodya" in c)
        data_list = []
        for tbody in table:
            rows = tbody.find_all("tr")
            for row in rows:
                cols = [col.text.strip() for col in row.find_all("td")]
                if cols:
                    data_list.append(cols)
        data_rows = data_list[1:]
        num_cols = 6
        data_rows = [row if len(row) == num_cols else row + ['']*(num_cols-len(row)) for row in data_rows]
        dataframe = pd.DataFrame(data_rows, columns=["state", "APMC", "Commodity", "Min_Price", "Modal_Price", "Max_Price"])
        driver.quit()
        return dataframe
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def extract_commodity_data(commodity_name):
    # ... [Keep your existing code here] ...
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)
        url = 'https://enam.gov.in/web/dashboard/live_price'
        driver.get(url)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        commodity_radio = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@name='colorRadio' and @value='blue']")))
        driver.execute_script("arguments[0].scrollIntoView(true);", commodity_radio)
        commodity_radio.click()
        time.sleep(3)
        dropdown = wait.until(EC.presence_of_element_located((By.ID, "min_max_commodity")))
        select = Select(dropdown)
        wait.until(lambda d: len(Select(dropdown).options) > 1)
        select.select_by_visible_text(commodity_name)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find_all("tbody", class_=lambda c: c and "tbodya" in c)
        data_list = []
        for tbody in table:
            rows = tbody.find_all("tr")
            for row in rows:
                cols = [col.text.strip() for col in row.find_all("td")]
                if cols:
                    data_list.append(cols)
        data_rows = data_list[1:]
        num_cols = 6
        data_rows = [row if len(row) == num_cols else row + ['']*(num_cols-len(row)) for row in data_rows]
        dataframe = pd.DataFrame(data_rows, columns=["state", "APMC", "Commodity", "Min_Price", "Modal_Price", "Max_Price"])
        driver.quit()
        return dataframe.to_dict(orient='records')
    except Exception as e:
        print(f"Error: {e}")
        return []
    

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krishimitra.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login to access this page.'
login_manager.login_message_category = 'warning'


current_user={'name':None,"id":None,"is_authenticated":False,'details':None}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user['is_authenticated'] == False:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Routes
@app.route('/')
def home(current_user=current_user):
    return render_template('home.html',current_user=current_user)

@app.route('/about')
def about():
    return render_template('about.html',current_user=current_user)

# @app.route('/prices', methods=['GET', 'POST'])
# @app.route('/prices', methods=['GET', 'POST'])
@app.route('/prices', methods=['GET', 'POST'])
def prices():
    # 1. Get Master Data
    master_df = extract_commodity_list()
    
    if not master_df.empty:
        state_to_commodity = master_df.groupby('state')['Commodity'].apply(lambda x: sorted(list(set(x)))).to_dict()
        commodity_to_state = master_df.groupby('Commodity')['state'].apply(lambda x: sorted(list(set(x)))).to_dict()
        all_states = sorted(master_df['state'].unique().tolist())
        all_commodities = sorted(master_df['Commodity'].unique().tolist())
    else:
        state_to_commodity = {}
        commodity_to_state = {}
        all_states = []
        all_commodities = []

    prices_data = [] 
    commodity_filter = ""
    state_filter = ""
    
    # Variables for Charts
    historical_chart_data = None
    bar_chart_data = None  # <--- NEW
    historical_msg = None
    is_commodity = False

    if request.method == 'POST':
        is_commodity = True
        commodity_filter = request.form.get('commodity', '')
        state_filter = request.form.get('state', '')

        # Real Time Table Data
        if commodity_filter:
            prices_data= (master_df.loc[master_df['Commodity'] == commodity_filter]).to_dict(orient='records')

            # prices_data = extract_commodity_data(commodity_filter)
        else:
            prices_data = master_df.to_dict(orient='records')

        if state_filter:
            prices_data = [row for row in prices_data if row['state'].upper() == state_filter.upper()]

        # --- CHART LOGIC ---
        if commodity_filter and state_filter:
            # 1. Historical Line Chart (Your existing logic)
            historical_chart_data, historical_msg = get_historical_data(state_filter, commodity_filter)
            
            # 2. Bar Charts (New logic using master_df from live scrape)
            bar_chart_data = get_bar_chart_data(master_df, state_filter, commodity_filter)
            
        elif commodity_filter or state_filter:
            historical_msg = "Please select both State and Commodity to view charts."
            
    else:
        prices_data = master_df.to_dict(orient='records')
        is_commodity = False

    return render_template(
        'prices.html',
        current_user=current_user,
        is_commodity=is_commodity,
        Commodity=all_commodities,
        states=all_states,
        state_map=state_to_commodity,
        commodity_map=commodity_to_state,
        prices=prices_data,
        commodity_filter=commodity_filter,
        state_filter=state_filter,
        
        # Pass Chart Data
        chart_data=historical_chart_data,
        bar_chart_data=bar_chart_data, # <--- NEW
        historical_msg=historical_msg
    )

@app.route('/transport-calculator', methods=['GET', 'POST'])
def transport_calculator():
    show_calc = False
    # 1. Get Master Data
    master_df = extract_commodity_list()
    
    # 2. Data Cleaning
    if not master_df.empty:
        # Clean Price
        master_df['Modal_Price'] = pd.to_numeric(
            master_df['Modal_Price'].astype(str).str.replace(',', ''), 
            errors='coerce'
        ).fillna(0)
        
        # Clean State
        master_df['state'] = master_df['state'].str.upper()
        
        # --- NEW: Create the combined "Name, State" column ---
        # This creates strings like "Ludhiana Mandi, Punjab"
        master_df['mandi_display'] = master_df['APMC'] + ", " + master_df['state'].str.title()

    # 3. Create Mappings using the NEW 'mandi_display' column
    crop_to_mandi = {}
    price_lookup = {}
    
    if not master_df.empty:
        # Map: Crop -> List of ["Mandi, State"]
        # We group by Commodity, but take values from 'mandi_display'
        crop_to_mandi = master_df.groupby('Commodity')['mandi_display'].apply(lambda x: sorted(list(set(x)))).to_dict()
        
        # Map: Crop -> { "Mandi, State" : Price }
        for _, row in master_df.iterrows():
            crop = row['Commodity']
            
            # Use the combined name as the key
            mandi_key = row['mandi_display'] 
            price = row['Modal_Price']
            
            if crop not in price_lookup:
                price_lookup[crop] = {}
            price_lookup[crop][mandi_key] = price

    all_crops = sorted(list(crop_to_mandi.keys()))

    result = None
    lowest_mandis = []

    if request.method == 'POST':
        try:
            # Get Data
            selected_crop = request.form.get('crop')
            selected_mandi = request.form.get('to_mandi') # This will now contain "Mandi, State"
            quantity = float(request.form.get('quantity', 0))
            price = float(request.form.get('price', 0))
            transport_cost = float(request.form.get('transport_cost', 0))
            
            # Calculate
            gross_revenue = quantity * price
            net_revenue = gross_revenue - transport_cost
            
            result = {
                'gross_revenue': gross_revenue,
                'transport_cost': transport_cost,
                'net_revenue': net_revenue,
                'quantity': quantity,
                'selected_crop': selected_crop,
                'selected_mandi': selected_mandi
            }

            # --- LOGIC FOR COMPARISON ---
            if not master_df.empty and selected_crop:
                crop_df = master_df[master_df['Commodity'] == selected_crop].copy()
                crop_df = crop_df.sort_values(by='Modal_Price', ascending=True)
                
                top_3 = crop_df.head(3).to_dict(orient='records')
                
                for row in top_3:
                    pot_net = (quantity * row['Modal_Price']) - transport_cost
                    lowest_mandis.append({
                        'APMC': row['mandi_display'], # Show "Mandi, State" here too
                        'Price': row['Modal_Price'],
                        'Pot_Net': pot_net
                    })
            show_calc = True

        except Exception as e:
            print(f"Calculation Error: {e}")
            flash("Error in calculation.", "danger")
    print(show_calc)
    return render_template('transport_calculator.html', 
                           show_calc=show_calc,
                           current_user=current_user,
                           crops=all_crops,
                           crop_to_mandi=crop_to_mandi,
                           price_lookup=price_lookup,
                           result=result,
                           lowest_mandis=lowest_mandis)

@app.route('/compare-region')
def compare_region():
    return render_template('compare_region.html', 
                           current_user=current_user,
                         crops=MOCK_CROPS,
                         states=MOCK_STATES)

@app.route('/farmer-input', methods=['GET', 'POST'])
@login_required
def farmer_input():
    if request.method == 'POST':
        try:
            new_input = FarmerInput(
                user_id=current_user.id,
                crop=request.form.get('crop'),
                quantity=float(request.form.get('quantity')),
                price=float(request.form.get('price')),
                mandi=request.form.get('mandi'),
                sale_date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
                notes=request.form.get('notes')
            )
            db.session.add(new_input)
            db.session.commit()
            flash('Thank you! Your data has been submitted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error submitting data. Please try again.', 'danger')
            print(f"Error: {e}")
        return redirect(url_for('farmer_input',current_user=current_user))
    
    return render_template('farmer_input.html', 
                           current_user=current_user,
                         crops=MOCK_CROPS,
                         mandis=MOCK_MANDIS)


@app.route('/community')
def community():
    # Mock posts
    posts = [
        {'id': 1, 'author': 'Ramesh Kumar', 'title': 'Best time to sell wheat in Punjab', 'excerpt': 'Based on my experience...', 'likes': 15},
        {'id': 2, 'author': 'Suresh Patel', 'title': 'Transport costs from Haryana to Delhi', 'excerpt': 'I recently transported...', 'likes': 8},
    ]
    return render_template('community.html', posts=posts,current_user=current_user)

@app.route('/schemes')
def schemes():
    # Mock schemes
    schemes = [
        {'name': 'PM-KISAN', 'description': 'Direct income support to farmers', 'type': 'Central', 'applicable': 'All farmers'},
        {'name': 'Crop Insurance Scheme', 'description': 'Insurance against crop failure', 'type': 'Central', 'applicable': 'All crops'},
    ]
    return render_template('schemes.html', schemes=schemes,current_user=current_user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user['is_authenticated']:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            current_user['name']=user.full_name
            current_user['id']=user.id
            current_user['is_authenticated']=True
            current_user['details']=user
            
            # next_page = request.args.get('next')
            # return redirect(url_for('home',current_user=current_user)) if next_page else redirect(url_for('dashboard'))
            return redirect(url_for('home',current_user=current_user))
        else:
            flash('Invalid email or password. Please try again.', 'danger')
    
    return render_template('login.html',current_user=current_user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user['is_authenticated']:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))
        
        try:
            # Get crops list if farmer
            crops_list = request.form.getlist('crops')
            crops_str = ','.join(crops_list) if crops_list else ''
            
            new_user = User(
                full_name=request.form.get('full_name'),
                email=email,
                phone=request.form.get('phone'),
                user_type=request.form.get('user_type'),
                state=request.form.get('state'),
                district=request.form.get('district'),
                farm_size=float(request.form.get('farm_size', 0)) if request.form.get('farm_size') else None,
                primary_crops=crops_str
            )
            new_user.set_password(request.form.get('password'))
            
            db.session.add(new_user)
            db.session.commit()
            
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            print(f"Error: {e}")
    
    return render_template('register.html', states=MOCK_STATES, crops=MOCK_CROPS,current_user=current_user)


@app.route('/dashboard')
@login_required
def dashboard():
    # Get user's submissions count
    submissions_count = FarmerInput.query.filter_by(user_id=current_user['id']).count()
    
    # Get user's recent activity
    recent_inputs = FarmerInput.query.filter_by(user_id=current_user['id'])\
        .order_by(FarmerInput.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                           current_user=current_user,
                         user_type=current_user['details'].user_type,
                         submissions_count=submissions_count,
                         recent_inputs=recent_inputs)

@app.route('/profile')
@login_required
def profile():

    return render_template('profile.html', user=current_user['details'],current_user=current_user)

@app.route('/logout')
# @login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    current_user['is_authenticated']=False
    current_user['name']=None
    current_user['id']=None
    current_user['details']=None
    return redirect(url_for('home',current_user=current_user))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html',current_user=current_user)

@app.route('/terms-privacy')
def terms_privacy():
    return render_template('terms_privacy.html',current_user=current_user)

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)