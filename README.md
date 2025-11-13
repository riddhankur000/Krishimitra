# 🌾 Krishimitra - Farmer Market Intelligence Platform

A comprehensive Flask-based web application designed to empower farmers with transparent market pricing information and tools for better decision-making.

## 📋 Project Overview

Krishimitra provides:
- Real-time market prices from various mandis
- Transport cost calculator
- Regional price comparison tools
- Crowdsourced data input from farmers
- Community forum for knowledge sharing
- Information about government schemes

## 🗂️ Complete Project Structure

```
krishimitra/
│
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── static/                         # Static files
│   ├── css/
│   │   └── style.css              # Main stylesheet
│   ├── js/
│   │   └── main.js                # JavaScript functionality
│   └── images/
│       └── logo.png               # Your logo (add this)
│
└── templates/                      # HTML templates
    ├── base.html                   # Base template with navbar/footer
    ├── home.html                   # Homepage
    ├── about.html                  # About page
    ├── prices.html                 # Market prices
    ├── transport_calculator.html   # Transport calculator
    ├── compare_region.html         # Regional comparison
    ├── farmer_input.html           # Data submission form
    ├── community.html              # Community forum
    ├── schemes.html                # Government schemes
    ├── login.html                  # Login page
    ├── register.html               # Registration
    ├── dashboard.html              # User dashboard
    ├── contact.html                # Contact page
    └── terms_privacy.html          # Terms & Privacy
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation Steps

1. **Create project directory and navigate to it:**
```bash
mkdir krishimitra
cd krishimitra
```

2. **Create all directories:**
```bash
mkdir -p static/css static/js static/images templates
```

3. **Create virtual environment:**
```bash
python -m venv venv
```

4. **Activate virtual environment:**

**On Windows:**
```bash
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
source venv/bin/activate
```

5. **Create `requirements.txt` file** (copy content from the requirements.txt artifact)

6. **Install dependencies:**
```bash
pip install -r requirements.txt
```

7. **Copy all files** from the artifacts:
   - `app.py` → root directory
   - `style.css` → `static/css/`
   - `main.js` → `static/js/`
   - All HTML files → `templates/`

8. **Run the application:**
```bash
python app.py
```

9. **Open your browser and visit:**
```
http://127.0.0.1:5000
```

## 🎨 Features Currently Implemented


## 📝 Next Steps for Backend Integration

Now that the frontend is complete, here's what needs to be implemented:

<!-- ### Phase 1: Database Setup -->
```python
# Add to app.py:
# from flask_sqlalchemy import SQLAlchemy
# from flask_login import LoginManager

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krishimitra.db'
# db = SQLAlchemy(app)
# login_manager = LoginManager(app)
# ```

# **Models to create:**
# - User (farmers, NGOs, traders)
# - Crop
# - MarketPrice
# - Mandi
# - FarmerInput (crowdsourced data)
# - CommunityPost
# - Scheme

# ### Phase 2: Web Scraping
# - Government mandi APIs
# - State agricultural department websites
# - APMC price data

# **Recommended libraries:**
# - BeautifulSoup4 (already in requirements.txt)
# - Requests (already in requirements.txt)
# - Selenium (if needed for dynamic content)

# ### Phase 3: Authentication System
# - Implement Flask-Login (already in requirements.txt)
# - Password hashing with werkzeug.security
# - Email verification (optional)
# - SMS OTP verification

# ### Phase 4: Data Visualization
# - Integrate Chart.js or Plotly
# - Price trend charts
# - Regional heatmaps
# - Interactive maps (Leaflet.js or Google Maps API)

# ### Phase 5: Advanced Features
# - Real-time price alerts
# - Price prediction (ML model)
# - WhatsApp/SMS notifications
# - Multi-language support
# - Export to PDF/Excel
# - API endpoints for mobile app

# ## 🔧 Configuration

# ### Secret Key
# Change the secret key in `app.py`:
# ```python
# app.secret_key = 'your-very-secret-key-here'
# ```

# ### Database (Future)
# ```python
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krishimitra.db'
# # Or for production:
# # app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:pass@localhost/krishimitra'
# ```

# ## 🎨 Customization

# ### Colors
# Edit colors in `static/css/style.css`:
# ```css
# :root {
#     --primary-color: #2d7a3e;    /* Main green */
#     --secondary-color: #5cb85c;  /* Light green */
#     --accent-color: #ff9800;     /* Orange */
# }
# ```

# ### Logo
# Add your logo to `static/images/logo.png`

# ### Mock Data
# Current mock data is in `app.py`. Replace with real data once database is set up.

# ## 📱 Testing

# ### Test Different User Types
# The demo login accepts any credentials and sets up a basic session. To test:
# - Farmer view: Login with any credentials (defaults to farmer)
# - NGO view: Modify session in code temporarily

# ### Test Responsive Design
# - Desktop: Full browser window
# - Tablet: Resize to ~768px width
# - Mobile: Resize to ~375px width

# ## 🐛 Troubleshooting

# ### Port already in use
# ```bash
# # Change port in app.py:
# app.run(debug=True, port=5001)
# ```

# ### Module not found
# ```bash
# pip install -r requirements.txt
# ```

# ### Templates not found
# Ensure all HTML files are in the `templates/` directory

# ### CSS not loading
# Check that `static/css/style.css` exists and Flask is running

# ## 📞 Support

# For questions or issues:
# - Email: dev@krishimitra.in
# - Create an issue in the project repository

# ## 📄 License

# This project is intended for educational and social good purposes.

# ## 🙏 Acknowledgments

# - Designed to help Indian farmers get fair prices
# - Inspired by the need for market transparency
# - Built with modern web technologies

# ---

# ## 🎯 Current Status

# **Frontend: 100% Complete ✅**
# - All 13 pages designed and functional
# - Fully responsive
# - Modern, farmer-friendly UI
# - Ready for backend integration

# **Backend: 0% - Ready to Start 🚀**
# - Database models needed
# - Web scraping implementation needed
# - Authentication system needed
# - Real data integration needed

# ---

# **Ready to proceed with backend development? Let me know which phase you'd like to tackle first!**