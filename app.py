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
from models import db, User, FarmerInput, CommunityPost, MarketPrice

# --- Setup Chrome Driver ---

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

# Extract commodity list from website
def extract_commodity_list():
    try:
        
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = 'https://enam.gov.in/web/dashboard/live_price'
        driver.get(url)

        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        commodity_radio = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@name='colorRadio' and @value='blue']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", commodity_radio)
        commodity_radio.click()

        time.sleep(2)

        # dropdown = wait.until(
        #     EC.presence_of_element_located((By.ID, "min_max_commodity"))
        # )

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        select = soup.find('select', {'id': 'min_max_commodity'})
        commodities = [option.text for option in select.find_all('option')[2:]]

        dropdown = wait.until(EC.presence_of_element_located((By.ID, "min_max_commodity")))
        select = Select(dropdown)

        wait.until(lambda d: len(Select(dropdown).options) > 1)
        select.select_by_visible_text("-- All --")
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find_all("tbody", class_=lambda c: c and "tbodya" in c)
        # print(table)
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
        MOCK_STATES=dataframe[['state']].drop_duplicates()
        MOCK_CROPS=dataframe[['Commodity']].drop_duplicates()

        # dataframe = pd.DataFrame(data_rows, columns=["state", "APMC", "Commodity", "Min_Price", "Modal_Price", "Max_Price"])
        
        # REMOVE THIS LINE: 
        # unique_pairs = dataframe[['state', 'Commodity']].drop_duplicates()
        
        driver.quit()
        
        # CHANGE RETURN TO THIS:
        return dataframe
    except Exception as e:
        print(f"Error extracting commodities: {e}")
        return ['Wheat', 'Rice', 'Cotton', 'Sugarcane', 'Maize']  # Fallback

def extract_commodity_data(commodity_name):
    try:
        driver = webdriver.Chrome(service=service, options=chrome_options)

        url = 'https://enam.gov.in/web/dashboard/live_price'
        driver.get(url)

        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        commodity_radio = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@name='colorRadio' and @value='blue']"))
        )
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
        print(f"Error extracting data: {e}")
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
    is_commodity = False
    # 1. Get the Master Data (The "All Commodities" list)
    # Since we updated the function, 'master_df' now contains prices too!
    master_df = extract_commodity_list()
    
    # 2. Create Mappings (Dropdown Logic)
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

    # 3. Initialize variables
    prices_data = [] 
    commodity_filter = ""
    state_filter = ""

    if request.method == 'POST':
        is_commodity=True
        commodity_filter = request.form.get('commodity', '')
        state_filter = request.form.get('state', '')

        # --- SCENARIO LOGIC ---

        if commodity_filter:
            # SCENARIO: Specific Commodity Selected
            # We scrape fresh data for this specific commodity to get the best details
            fetched_data = extract_commodity_data(commodity_filter)
            prices_data = fetched_data # Default to all states for this commodity
        else:
            # SCENARIO: "All Commodities" Selected
            # We use the master_df we already scraped at the start
            prices_data = master_df.to_dict(orient='records')

        # --- FILTERING BY STATE ---
        # Now, regardless of whether we got data from 'master_df' or 'extract_commodity_data',
        # we check if we need to hide other states.
        
        if state_filter:
            # Filter the list to keep only the selected state
            prices_data = [
                row for row in prices_data 
                if row['state'].upper() == state_filter.upper()
            ]
            
    else:
        # GET request (Page Load)
        # Show everything by default (or show nothing if you prefer)
        prices_data = master_df.to_dict(orient='records')
        is_commodity = False

     # Always show the table

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
        state_filter=state_filter
    )


@app.route('/transport-calculator', methods=['GET', 'POST'])
def transport_calculator():
    # 1. Get Master Data
    master_df = extract_commodity_list()
    
    # 2. Data Cleaning (Crucial for Math)
    # Ensure prices are numbers (remove commas if present)
    if not master_df.empty:
        # Convert 'Modal_Price' to numeric, coercing errors to NaN, then fill with 0
        master_df['Modal_Price'] = pd.to_numeric(master_df['Modal_Price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        master_df['state'] = master_df['state'].str.upper() # Normalize state names
    
    # 3. Create Mappings for Dropdowns & Auto-fill
    # Map: Crop -> List of Mandis
    crop_to_mandi = {}
    if not master_df.empty:
        crop_to_mandi = master_df.groupby('Commodity')['APMC'].apply(lambda x: sorted(list(set(x)))).to_dict()
    
    # Map: Crop -> { Mandi : Price } (For auto-filling price in JS)
    price_lookup = {}
    if not master_df.empty:
        for _, row in master_df.iterrows():
            crop = row['Commodity']
            mandi = row['APMC']
            price = row['Modal_Price']
            
            if crop not in price_lookup:
                price_lookup[crop] = {}
            price_lookup[crop][mandi] = price

    # Lists for initial dropdowns
    all_crops = sorted(list(crop_to_mandi.keys()))

    result = None
    lowest_3_mandis = []

    if request.method == 'POST':
        try:
            # Get Form Data
            selected_crop = request.form.get('crop')
            selected_mandi = request.form.get('to_mandi')
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
                'selected_crop': selected_crop,
                'selected_mandi': selected_mandi,
                'quantity': quantity
            }

            # Logic for "Compare Other Mandis" (Lowest 3 prices for this crop)
            if not master_df.empty and selected_crop:
                # Filter for the selected crop
                crop_df = master_df[master_df['Commodity'] == selected_crop].copy()
                
                # Sort by Price Ascending (Cheapest/Lowest first)
                crop_df = crop_df.sort_values(by='Modal_Price', ascending=True)
                
                # Take top 3
                top_3_rows = crop_df.head(3).to_dict(orient='records')
                
                # Calculate potential revenues for these comparisons
                # (Assuming same transport cost for comparison purposes, or you can leave blank)
                for row in top_3_rows:
                    pot_gross = quantity * row['Modal_Price']
                    pot_net = pot_gross - transport_cost
                    
                    lowest_3_mandis.append({
                        'APMC': row['APMC'],
                        'Price': row['Modal_Price'],
                        'Est_Transport': transport_cost, # Using same transport cost for reference
                        'Pot_Net': pot_net
                    })

        except Exception as e:
            print(f"Calculation Error: {e}")
            flash("Error in calculation. Please check your inputs.", "danger")

    return render_template('transport_calculator.html', 
                           current_user=current_user,
                           crops=all_crops,
                           crop_to_mandi=crop_to_mandi, # For JS Dropdown
                           price_lookup=price_lookup,   # For JS Auto-price
                           result=result,
                           lowest_mandis=lowest_3_mandis)


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