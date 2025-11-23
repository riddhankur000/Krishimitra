# Add these new imports at the top of your app.py
import os
import glob
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import io
import base64

# ... (keep all your existing imports and setup code)

# Add this new function after your existing scraping functions
def scrape_upag_crop_data(commodity_name):
    """
    Scrapes APY Trends and Price Analysis data from UPAg dashboard
    """
    try:
        # Setup download directory
        download_dir = os.path.join(os.getcwd(), 'temp_downloads')
        if not os.path.exists(download_dir):
            os.makedirs(download_dir)
        
        # Configure Chrome options for download
        chrome_options = Options()
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--headless')
        
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Navigate to UPAg crop profile dashboard
        url = f'https://upag.gov.in/dash-reports/cropprofiledash?t=&stateID=0&rtab=Crop%2FCommodity%20Profile&rtype=dashboards'
        driver.get(url)
        
        wait = WebDriverWait(driver, 30)
        
        # Wait for iframe to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "iframe")))
        time.sleep(3)
        
        # Switch to iframe
        iframe = driver.find_element(By.TAG_NAME, "iframe")
        driver.switch_to.frame(iframe)
        
        # Wait for page to fully load
        time.sleep(5)
        
        result_data = {
            'apy_trends': None,
            'price_analysis': None,
            'apy_chart': None,
            'price_chart': None
        }
        
        # ===== SCRAPE APY TRENDS DATA =====
        try:
            # Find and click APY TRENDS tab
            apy_tab = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'APY TRENDS')] | //div[contains(text(), 'APY TRENDS')]")
            ))
            driver.execute_script("arguments[0].click();", apy_tab)
            time.sleep(3)
            
            # Find download button for APY data
            download_btns = driver.find_elements(By.XPATH, 
                "//button[contains(@title, 'Download')] | //a[contains(@download, '')] | //*[contains(@class, 'download')]"
            )
            
            if download_btns:
                # Click first download button
                driver.execute_script("arguments[0].click();", download_btns[0])
                time.sleep(5)  # Wait for download
                
                # Find the downloaded CSV file
                csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
                if csv_files:
                    latest_file = max(csv_files, key=os.path.getctime)
                    result_data['apy_trends'] = pd.read_csv(latest_file)
                    os.remove(latest_file)  # Clean up
                    
        except Exception as e:
            print(f"Error scraping APY Trends: {e}")
        
        # ===== SCRAPE PRICE ANALYSIS DATA =====
        try:
            # Find and click PRICE ANALYSIS INSIGHTS tab
            price_tab = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//button[contains(text(), 'PRICE ANALYSIS')] | //div[contains(text(), 'PRICE ANALYSIS')]")
            ))
            driver.execute_script("arguments[0].click();", price_tab)
            time.sleep(3)
            
            # Find download button for Price data
            download_btns = driver.find_elements(By.XPATH, 
                "//button[contains(@title, 'Download')] | //a[contains(@download, '')] | //*[contains(@class, 'download')]"
            )
            
            if len(download_btns) > 1:
                # Click second download button (price data)
                driver.execute_script("arguments[0].click();", download_btns[1])
                time.sleep(5)
                
                csv_files = glob.glob(os.path.join(download_dir, "*.csv"))
                if csv_files:
                    latest_file = max(csv_files, key=os.path.getctime)
                    result_data['price_analysis'] = pd.read_csv(latest_file)
                    os.remove(latest_file)
                    
        except Exception as e:
            print(f"Error scraping Price Analysis: {e}")
        
        driver.quit()
        
        # Clean up download directory
        try:
            os.rmdir(download_dir)
        except:
            pass
        
        return result_data
        
    except Exception as e:
        print(f"Error in scrape_upag_crop_data: {e}")
        return None


def generate_chart_image(df, chart_type='line', title=''):
    """
    Generates a chart image from DataFrame and returns base64 encoded string
    """
    try:
        plt.figure(figsize=(10, 6))
        
        if chart_type == 'line':
            for col in df.columns[1:]:  # Skip first column (usually labels)
                plt.plot(df.iloc[:, 0], df[col], marker='o', label=col)
            plt.legend()
        elif chart_type == 'bar':
            df.plot(kind='bar', x=df.columns[0], figsize=(10, 6))
        
        plt.title(title)
        plt.tight_layout()
        
        # Convert plot to base64 image
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=100)
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode()
        plt.close()
        
        return img_base64
        
    except Exception as e:
        print(f"Error generating chart: {e}")
        return None


# ===== MODIFY YOUR EXISTING /prices ROUTE =====
@app.route('/prices', methods=['GET', 'POST'])
def prices():
    is_commodity = False
    upag_data = None
    
    # Your existing eNAM data scraping (keep as is)
    master_df = extract_commodity_list()
    
    if not master_df.empty:
        state_to_commodity = master_df.groupby('state')['Commodity'].apply(
            lambda x: sorted(list(set(x)))
        ).to_dict()
        commodity_to_state = master_df.groupby('Commodity')['state'].apply(
            lambda x: sorted(list(set(x)))
        ).to_dict()
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

    if request.method == 'POST':
        is_commodity = True
        commodity_filter = request.form.get('commodity', '')
        state_filter = request.form.get('state', '')
        
        # Check if user wants UPAg data
        fetch_upag = request.form.get('fetch_upag', 'no')

        # Your existing eNAM scraping logic
        if commodity_filter:
            fetched_data = extract_commodity_data(commodity_filter)
            prices_data = fetched_data
        else:
            prices_data = master_df.to_dict(orient='records')

        if state_filter:
            prices_data = [
                row for row in prices_data 
                if row['state'].upper() == state_filter.upper()
            ]
        
        # NEW: Fetch UPAg data if requested
        if fetch_upag == 'yes' and commodity_filter:
            upag_data = scrape_upag_crop_data(commodity_filter)
            
            # Generate charts if data available
            if upag_data and upag_data['apy_trends'] is not None:
                upag_data['apy_chart'] = generate_chart_image(
                    upag_data['apy_trends'], 
                    chart_type='line',
                    title='Historical APY Trends'
                )
            
            if upag_data and upag_data['price_analysis'] is not None:
                upag_data['price_chart'] = generate_chart_image(
                    upag_data['price_analysis'],
                    chart_type='bar',
                    title='Price Analysis Insights'
                )
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
        upag_data=upag_data  # NEW: Pass UPAg data to template
    )