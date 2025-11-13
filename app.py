from flask import Flask, render_template, request, redirect, url_for, flash, session
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
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options
import pandas as pd

# --- Setup Chrome Driver ---
chrome_options = Options()
chrome_options.add_argument('--start-maximized')  # open full screen
chrome_options.add_argument('--disable-blink-features=AutomationControlled')

# Create a driver instance





# Extract commodity list from website
def extract_commodity_list():

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # --- Step 1: Open the target website ---
    url = 'https://enam.gov.in/web/dashboard/live_price'  # Replace this with your mandi price website
    driver.get(url)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Step 4: Click the "Commodity Wise" radio button
    commodity_radio = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//input[@name='colorRadio' and @value='blue']"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", commodity_radio)
    commodity_radio.click()

    time.sleep(2)  # Wait for dropdown to activate

    # Wait for dropdown to appear
    dropdown = wait.until(
        EC.presence_of_element_located((By.ID, "min_max_commodity"))
    )

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # Find the select element
    select = soup.find('select', {'id': 'min_max_commodity'})

    # Extract all option texts except the first two placeholder options
    commodities = [option.text for option in select.find_all('option')[2:]]  # skipping "-- Select Commodity --" and "-- All --"

    print(commodities)
    driver.quit()

    return commodities



app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Mock data for demonstration
MOCK_CROPS = extract_commodity_list()
MOCK_STATES = ['Punjab', 'Haryana', 'Uttar Pradesh', 'Maharashtra', 'Karnataka', 'Tamil Nadu']
MOCK_MANDIS = ['Delhi Azadpur', 'Mumbai APMC', 'Bangalore Yeshwanthpur', 'Ludhiana Mandi']

# Mock price data
MOCK_PRICES = [
    {'state': 'Punjab', 'APMC': 'Ludhiana Mandi', 'Commodity': 'Wheat', 'Min_Price': 2000, 'Modal_Price': 2150, 'Max_Price': 2300},
    {'state': 'Punjab', 'APMC': 'Ludhiana Mandi', 'Commodity': 'Wheat', 'Min_Price': 2000, 'Modal_Price': 2150, 'Max_Price': 2300},
    {'state': 'Punjab', 'APMC': 'Ludhiana Mandi', 'Commodity': 'Wheat', 'Min_Price': 2000, 'Modal_Price': 2150, 'Max_Price': 2300},
    {'state': 'Punjab', 'APMC': 'Ludhiana Mandi', 'Commodity': 'Wheat', 'Min_Price': 2000, 'Modal_Price': 2150, 'Max_Price': 2300},
]

def extract_commodity_data(commodity_name):
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    url = 'https://enam.gov.in/web/dashboard/live_price'
    driver.get(url)

    wait = WebDriverWait(driver, 20)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    # Click "Commodity Wise"
    commodity_radio = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//input[@name='colorRadio' and @value='blue']"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", commodity_radio)
    commodity_radio.click()

    time.sleep(3)

    dropdown = wait.until(EC.presence_of_element_located((By.ID, "min_max_commodity")))
    select = Select(dropdown)

    # Wait until options are loaded
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


# 
# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/prices', methods=['GET', 'POST'])
def prices():
    prices_data = MOCK_PRICES
    if request.method == 'POST':
        
        commodity_filter = request.form.get('commodity', '')
        is_commodity = bool(commodity_filter)
        state_filter = request.form.get('state', '')
        prices_data = extract_commodity_data(commodity_filter) if is_commodity else []
    else:
        commodity_filter = request.args.get('commodity', '')
        state_filter = request.args.get('state', '')

    is_commodity = bool(commodity_filter)

    # Example dynamic call
    
   

    return render_template(
        'prices.html',
        is_commodity=is_commodity,
        Commodity=MOCK_CROPS,
        states=MOCK_STATES,
        prices=prices_data,
        commodity_filter=commodity_filter,
        state_filter=state_filter
    )



@app.route('/transport-calculator', methods=['GET', 'POST'])
def transport_calculator():
    result = None
    if request.method == 'POST':
        # Mock calculation
        quantity = float(request.form.get('quantity', 0))
        price = float(request.form.get('price', 0))
        transport_cost = float(request.form.get('transport_cost', 0))
        
        gross_revenue = quantity * price
        net_revenue = gross_revenue - transport_cost
        
        result = {
            'gross_revenue': gross_revenue,
            'transport_cost': transport_cost,
            'net_revenue': net_revenue
        }
    
    return render_template('transport_calculator.html', 
                         crops=MOCK_CROPS,
                         mandis=MOCK_MANDIS,
                         result=result)

@app.route('/compare-region')
def compare_region():
    return render_template('compare_region.html', 
                         crops=MOCK_CROPS,
                         states=MOCK_STATES)

@app.route('/farmer-input', methods=['GET', 'POST'])
@login_required
def farmer_input():
    if request.method == 'POST':
        flash('Thank you! Your data has been submitted successfully.', 'success')
        return redirect(url_for('farmer_input'))
    
    return render_template('farmer_input.html', 
                         crops=MOCK_CROPS,
                         mandis=MOCK_MANDIS)

@app.route('/community')
def community():
    # Mock posts
    posts = [
        {'id': 1, 'author': 'Ramesh Kumar', 'title': 'Best time to sell wheat in Punjab', 'excerpt': 'Based on my experience...', 'likes': 15},
        {'id': 2, 'author': 'Suresh Patel', 'title': 'Transport costs from Haryana to Delhi', 'excerpt': 'I recently transported...', 'likes': 8},
    ]
    return render_template('community.html', posts=posts)

@app.route('/schemes')
def schemes():
    # Mock schemes
    schemes = [
        {'name': 'PM-KISAN', 'description': 'Direct income support to farmers', 'type': 'Central', 'applicable': 'All farmers'},
        {'name': 'Crop Insurance Scheme', 'description': 'Insurance against crop failure', 'type': 'Central', 'applicable': 'All crops'},
    ]
    return render_template('schemes.html', schemes=schemes)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Mock login
        email = request.form.get('email')
        password = request.form.get('password')
        
        # For demo purposes, accept any login
        session['user_id'] = 1
        session['user_name'] = email.split('@')[0]
        session['user_type'] = 'farmer'
        
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', states=MOCK_STATES, crops=MOCK_CROPS)

@app.route('/dashboard')
@login_required
def dashboard():
    user_type = session.get('user_type', 'farmer')
    return render_template('dashboard.html', user_type=user_type)

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('Thank you for your message. We will get back to you soon!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/terms-privacy')
def terms_privacy():
    return render_template('terms_privacy.html')

if __name__ == '__main__':
    app.run(debug=True)