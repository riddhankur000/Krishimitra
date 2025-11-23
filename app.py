from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
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
from models import db, User, CommunityPost
import glob
import random
import json
import numpy as np
# --- Setup Chrome Driver ---

import matplotlib
matplotlib.use('Agg') # Prevents GUI errors

chrome_options = Options()
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('--headless')  # Run in background


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

COMMODITY_MAP=json.load(open(r'data\commodity_mapping.json'))

def get_bar_chart_data(master_df, state_name, commodity_name):
    try:
        if master_df.empty:
            return None

        # Clean Data
        df = master_df.copy()
        df['Modal_Price'] = pd.to_numeric(df['Modal_Price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
        state_name = state_name.strip().upper()
        commodity_name = commodity_name.strip()

        # 1. Filter for Commodity (All India)
        national_df = df[df['Commodity'] == commodity_name].copy()
        
        if national_df.empty:
            return None

        national_avg = round(national_df['Modal_Price'].mean(), 2)
        
        # 2. Filter for State
        state_df = national_df[national_df['state'].str.upper() == state_name].copy()
        
        # --- STATE DATA PREPARATION ---
        if state_df.empty:
            state_avg = 0
            # Initialize empty lists to prevent errors
            st_asc_labels, st_asc_data = [], []
            st_desc_labels, st_desc_data = [], []
        else:
            state_avg = round(state_df['Modal_Price'].mean(), 2)
            
            # State Cheapest (Ascending)
            st_asc = state_df.sort_values(by='Modal_Price', ascending=True).head(5)
            st_asc_labels = st_asc['APMC'].tolist()
            st_asc_data = st_asc['Modal_Price'].tolist()

            # State Costliest (Descending)
            st_desc = state_df.sort_values(by='Modal_Price', ascending=False).head(5)
            st_desc_labels = st_desc['APMC'].tolist()
            st_desc_data = st_desc['Modal_Price'].tolist()

        # --- NATIONAL DATA PREPARATION ---
        
        # National Cheapest (Ascending)
        nat_asc = national_df.sort_values(by='Modal_Price', ascending=True).head(10)
        nat_asc_labels = nat_asc.apply(lambda x: f"{x['APMC']}, {x['state']}", axis=1).tolist()
        nat_asc_data = nat_asc['Modal_Price'].tolist()

        # National Costliest (Descending)
        nat_desc = national_df.sort_values(by='Modal_Price', ascending=False).head(10)
        nat_desc_labels = nat_desc.apply(lambda x: f"{x['APMC']}, {x['state']}", axis=1).tolist()
        nat_desc_data = nat_desc['Modal_Price'].tolist()

        return {
            "state_name": state_name,
            "national_avg": national_avg,
            "state_avg": state_avg,
            # Return 4 distinct datasets
            "state_asc": {"labels": st_asc_labels, "data": st_asc_data},
            "state_desc": {"labels": st_desc_labels, "data": st_desc_data},
            "national_asc": {"labels": nat_asc_labels, "data": nat_asc_data},
            "national_desc": {"labels": nat_desc_labels, "data": nat_desc_data}
        }

    except Exception as e:
        print(f"Bar Chart Data Error: {e}")
        return None
    

# --- Helper Function to Generate Historical Graph ---
def get_historical_data(state_name, commodity_name):
    try:
        csv_path = r'data\agmarknet_india_historical_prices_2024_2025.csv' 
        if not os.path.exists(csv_path):
            return None, "Dataset not found."

        df = pd.read_csv(csv_path)

        # Standardize text
        state_name = state_name.strip().lower()
        commodity_name = COMMODITY_MAP[commodity_name.strip().upper()].lower()
        
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
    

def extract_commodity_list():

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
        # dataframe = pd.DataFrame(MOCK_PRICES)
        dataframe = pd.DataFrame(data_rows, columns=["state", "APMC", "Commodity", "Min_Price", "Modal_Price", "Max_Price"])
        driver.quit()
        return dataframe
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()

def extract_commodity_data(commodity_name):

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
        # dataframe = pd.DataFrame(MOCK_PRICES)
        driver.quit()
        return dataframe.to_dict(orient='records')
    except Exception as e:
        print(f"Error: {e}")
        return []
    

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krishimitra.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


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
def home():
    return render_template('home.html',current_user=current_user)

@app.route('/about')
def about():
    return render_template('about.html',current_user=current_user)


@app.route('/prices', methods=['GET', 'POST'])
def prices():
    show_graph=False
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
            
            prices_data = extract_commodity_data(commodity_filter)

            # prices_data = extract_commodity_data(commodity_filter)
        else:
            prices_data = master_df.to_dict(orient='records')

        if state_filter:
            prices_data = [row for row in prices_data if row['state'].upper() == state_filter.upper()]

        # --- CHART LOGIC ---
        if commodity_filter and state_filter:
            show_graph=True

            historical_chart_data, historical_msg = get_historical_data(state_filter, commodity_filter)
            
            bar_chart_data = get_bar_chart_data(master_df, state_filter, commodity_filter)
            print(bar_chart_data)
        elif commodity_filter or state_filter:
            historical_msg = "Please select both State and Commodity to view charts."
            
    else:
        prices_data = master_df.to_dict(orient='records')
        is_commodity = False

    return render_template(
        'prices.html',
        show_graph=show_graph,
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
    
    # --- 1. Data Extraction ---
    master_df = extract_commodity_list() 
    
    # --- 2. Data Cleaning & Setup ---
    crop_to_mandi = {}
    price_lookup = {}
    all_crops = []

    if not master_df.empty:
        # Clean Price Column
        master_df['Modal_Price'] = pd.to_numeric(
            master_df['Modal_Price'].astype(str).str.replace(',', ''), 
            errors='coerce'
        ).fillna(0)
        
        master_df['state'] = master_df['state'].str.upper().str.strip()
        master_df['mandi_display'] = master_df['APMC'] + ", " + master_df['state'].str.title()

        crop_to_mandi = master_df.groupby('Commodity')['mandi_display'].apply(
            lambda x: sorted(list(set(x)))
        ).to_dict()
        
        for _, row in master_df.iterrows():
            crop = row['Commodity']
            mandi_key = row['mandi_display'] 
            price = row['Modal_Price']
            
            if crop not in price_lookup:
                price_lookup[crop] = {}
            price_lookup[crop][mandi_key] = price

        all_crops = sorted(list(crop_to_mandi.keys()))

    # Initialize variables
    result = None
    top_5_india = []
    top_5_state = []
    chart_data = None

    if request.method == 'POST':
        try:
            # Get Form Data
            selected_crop = request.form.get('crop')
            selected_mandi_full = request.form.get('to_mandi')  # Format: "APMC, State"
            from_location = request.form.get('from_location')
            
            quantity = float(request.form.get('quantity') or 0)
            price = float(request.form.get('price') or 0)
            distance = float(request.form.get('distance') or 0)
            rate_per_km = float(request.form.get('rate_per_km') or 25)
            
            # Calculations
            transport_cost = distance * rate_per_km
            gross_revenue = quantity * price
            net_revenue = gross_revenue - transport_cost
            profit_per_qtl = (net_revenue / quantity) if quantity > 0 else 0
            
            # Extract State name safely
            selected_state_name = ""
            if selected_mandi_full and ',' in selected_mandi_full:
                selected_state_name = selected_mandi_full.split(',')[-1].strip().upper()

            result = {
                'gross_revenue': gross_revenue,
                'transport_cost': transport_cost,
                'net_revenue': net_revenue,
                'quantity': quantity,
                'selected_crop': selected_crop,
                'selected_mandi': selected_mandi_full,
                'distance': distance,
                'rate_per_km': rate_per_km,
                'from_location': from_location,
                'profit_per_qtl': profit_per_qtl
            }

            if not master_df.empty and selected_crop:
                # Filter by Crop
                crop_df = master_df[master_df['Commodity'] == selected_crop].copy()
                
                if not crop_df.empty:
                    df_india = crop_df.sort_values(by='Modal_Price', ascending=False).head(5)
                    
                    for _, row in df_india.iterrows():
                        top_5_india.append({
                            'APMC': row['mandi_display'],
                            'Price': row['Modal_Price'],
                            'Gross_Rev': quantity * row['Modal_Price'],
                            'rate_per_km': rate_per_km  # Pass rate to frontend
                        })

                    df_state = crop_df[crop_df['state'] == selected_state_name].sort_values(by='Modal_Price', ascending=False).head(5)
                    
                    for _, row in df_state.iterrows():
                        top_5_state.append({
                            'APMC': row['mandi_display'],
                            'Price': row['Modal_Price'],
                            'Gross_Rev': quantity * row['Modal_Price'],
                            'rate_per_km': rate_per_km  # Pass rate to frontend
                        })

                    if top_5_india:
                        chart_data = {
                            'india_labels': [item['APMC'].split(',')[0] for item in top_5_india],
                            'india_data': [item['Gross_Rev'] for item in top_5_india], 
                            'state_labels': [item['APMC'].split(',')[0] for item in top_5_state] if top_5_state else [],
                            'state_data': [item['Gross_Rev'] for item in top_5_state] if top_5_state else [],
                            'state_name': selected_state_name.title() if selected_state_name else "State"
                        }
                        print("✓ Chart data prepared:", chart_data)
                    else:
                        print("✗ No data found for charts")

            show_calc = True

        except Exception as e:
            print(f"Calculation Error: {e}")
            flash("Error in calculation. Please check your inputs.", "danger")

    return render_template('transport_calculator.html', 
                           show_calc=show_calc,
                           current_user=current_user,
                           crops=all_crops,
                           crop_to_mandi=crop_to_mandi,
                           price_lookup=price_lookup,
                           result=result,
                           top_5_india=top_5_india,
                           top_5_state=top_5_state,
                           chart_data=chart_data)


@app.route('/community', methods=['GET', 'POST'])
def community():
    if request.method == 'POST':
        # Check if user is logged in
        if not current_user['is_authenticated']:
            flash('Please login to post in the community.', 'warning')
            return redirect(url_for('login'))
        
        try:
            title = request.form.get('title')
            category = request.form.get('category')
            content = request.form.get('content')
            
            # Validate inputs
            if not title or not content:
                flash('Title and content are required.', 'danger')
                return redirect(url_for('community'))
            
            # Create new post
            new_post = CommunityPost(
                user_id=current_user['id'],
                title=title,
                content=content,
                category=category
            )
            
            db.session.add(new_post)
            db.session.commit()
            
            flash('Your post has been published successfully!', 'success')
            return redirect(url_for('community'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error posting to community. Please try again.', 'danger')
            print(f"Error: {e}")
            return redirect(url_for('community'))
    
    # GET request - fetch latest 10 posts
    posts = CommunityPost.query\
        .order_by(CommunityPost.created_at.desc())\
        .limit(10)\
        .all()
    
    # Convert to list of dicts with author info
    posts_data = []
    for post in posts:
        author = User.query.get(post.user_id)
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'excerpt': post.content[:100] + '...' if len(post.content) > 100 else post.content,
            'category': post.category,
            'likes': post.likes,
            'author': author.full_name if author else 'Unknown',
            'created_at': post.created_at.strftime('%b %d, %Y at %I:%M %p'),
            'user_id': post.user_id
        })
    
    return render_template('community.html', 
                         posts=posts_data,
                         current_user=current_user)


@app.route('/community/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    if not current_user['is_authenticated']:
        return {'success': False, 'message': 'Please login to like posts'}, 401
    
    try:
        post = CommunityPost.query.get_or_404(post_id)
        
        action = request.json.get('action')  # 'like' or 'unlike'
        
        if action == 'like':
            post.likes += 1
        elif action == 'unlike' and post.likes > 0:
            post.likes -= 1
        
        db.session.commit()
        
        return {'success': True, 'likes': post.likes}, 200
        
    except Exception as e:
        print(f"Error: {e}")
        return {'success': False, 'message': 'Error updating likes'}, 500


@app.route('/dashboard')
@login_required
def dashboard():
    posts_count = CommunityPost.query.filter_by(user_id=current_user['id']).count()
    
    # Get user's recent posts
    recent_posts = CommunityPost.query\
        .filter_by(user_id=current_user['id'])\
        .order_by(CommunityPost.created_at.desc())\
        .limit(5)\
        .all()
    
    # Calculate total likes received
    total_likes = db.session.query(db.func.sum(CommunityPost.likes))\
        .filter_by(user_id=current_user['id'])\
        .scalar() or 0
    
    return render_template('dashboard.html', 
                         current_user=current_user,
                         user_type=current_user['details'].user_type,
                         posts_count=posts_count,
                         recent_posts=recent_posts,
                         total_likes=total_likes)


@app.route('/profile')
@login_required
def profile():
    # Get user statistics
    posts_count = CommunityPost.query.filter_by(user_id=current_user['id']).count()
    
    # Calculate total likes received
    total_likes = db.session.query(db.func.sum(CommunityPost.likes))\
        .filter_by(user_id=current_user['id'])\
        .scalar() or 0
    
    return render_template('profile.html', 
                         user=current_user['details'],
                         current_user=current_user,
                         posts_count=posts_count,
                         total_likes=total_likes)

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
            return redirect(url_for('home'))
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


@app.route('/logout')
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