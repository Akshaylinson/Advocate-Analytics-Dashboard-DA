# Advocate Analytics Dashboard

A full-stack analytics dashboard built with **Flask**, **Pandas**, and **Plotly.js** for exploring and analyzing advocate/business records from Excel datasets.  
It supports KPIs, interactive charts, server-side table pagination, and CSV/Excel download.

---

## 🚀 Features
- **Interactive Dashboard**
  - KPIs: Total Records, Unique Owners, States, Cities, Phones Present, Potential Duplicates.
  - Charts:
    - Bar: Top States by Count
    - Horizontal Bar: Top Cities
    - Donut: Phone Data Completeness
    - Donut: Duplicates vs Unique
    - Line: State Trends & Phone Present Rate
    - Treemap: Distribution by State
    - Heatmap: State × City Distribution

- **Search & Filtering**
  - Server-side search, pagination, and page-size control.
  - Quick filters on name, firm, city, state, or phone.

- **Data Handling**
  - Reads data from Excel/CSV via **pandas**.
  - Caches dataset as CSV for faster reload.
  - API endpoints for charts and table are powered by Flask routes.

- **Modern UI**
  - Built with **TailwindCSS + custom styles**.
  - Responsive layout with a glassmorphism-inspired look.

---

## 🗂 Project Structure
advocate_analytics/
│── app.py # Flask backend (APIs + routes)
│── requirements.txt # Python dependencies
│── business_cache.csv # Cached dataset (generated automatically)
│
├── templates/ # Jinja2 HTML templates
│ ├── base.html # Base layout (navbar + container)
│ ├── dashboard.html # Analytics dashboard
│
└── static/ # Static files
├── styles.css # Custom CSS (if needed)
└── app.js # (Optional) extra frontend logic

yaml
Copy code

---

## ⚙️ Installation

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/advocate-analytics.git
cd advocate-analytics
2. Create Virtual Environment
bash
Copy code
python -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows
3. Install Dependencies
Install each dependency separately (per your requirement):

bash
Copy code
pip install Flask==3.0.3
pip install pandas==2.2.2
pip install openpyxl==3.1.5
Or install all at once:

bash
Copy code
pip install -r requirements.txt
4. Prepare Dataset
Place your Excel file (e.g., India-Advocate-1750.xlsx) in the project root.
On the first run, the system will read it into a cached business_cache.csv.

▶️ Running the App
bash
Copy code
python app.py
The app will be available at:

cpp
Copy code
http://127.0.0.1:5000
📊 API Endpoints
/api/summary → Returns KPIs

/api/top-states → Top states by record count

/api/top-cities → Top cities by record count

/api/phones-by-state → Phone completeness by state

/api/treemap-states → Data for treemap chart

/api/state-city-heatmap → Heatmap matrix of state × city counts

/api/table → Paginated & filtered data for DataTable

/download/csv → Download dataset as CSV

📌 Example Dataset Fields
Your Excel sheet should have the following columns:

Business Name / Advocate Name

Owner Name

City

State

Mobile Number

🖼 Preview

🔮 Future Enhancements
Role-based login (Admin/User)

File uploader for new datasets

Advanced filters (date, state, category)

Export charts as PDF

