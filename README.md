# Competitor Monitoring Alert Tool 🔎

A web-based competitive intelligence tool built with Flask and Python to monitor competitor content, track pricing-page changes, extract SEO keywords, and send email alerts when new content is detected.

## Live Link - https://competitor-monitoring-alert-tool.onrender.com

## 🚀 Features

- **Competitor Monitoring:** Scan competitor websites to discover relevant pages and recent content.
- **New Content Detection:** Store discovered URLs in SQLite and identify newly detected pages without duplicating existing records.
- **SEO Keyword Extraction:** Extract relevant keywords from article titles and descriptions.
- **Pricing Change Monitoring:** Track pricing-page snapshots and detect changes in page content.
- **Email Notifications:** Receive email alerts containing content titles, URLs, descriptions, publication dates when available, and extracted keywords.
- **Dashboard:** View monitored competitors, saved articles, scan results, pricing history, and keyword information.
- **Error Handling:** Handle invalid domains, inaccessible pages, and scanning errors.

## 🛠️ Tech Stack

- **Backend:** Python, Flask
- **Web Scraping:** Requests, Beautiful Soup
- **Database:** SQLite
- **Frontend:** HTML, CSS
- **Notifications:** SMTP / Gmail
- **Deployment:** Render
- **Version Control:** Git and GitHub

## ⚙️ Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/tanish0050/competitor-monitoring-alert-tool.git
cd competitor-monitoring-alert-tool
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
SMTP_EMAIL=your_gmail@gmail.com
SMTP_APP_PASSWORD=your_google_app_password
ALERT_TO_EMAIL=your_gmail@gmail.com
```

Use a Google App Password rather than your regular Gmail password. Keep `.env` private and never commit it to GitHub.

### 5. Run the application

```bash
python app.py
```

Open `http://127.0.0.1:5000` in your browser.

## 🧪 Testing

- Scan a competitor domain and verify that content is stored.
- Scan the same domain again and verify that previously saved pages are not marked as new.
- Verify email notifications when new content is detected.
- Check pricing-page snapshots and keyword extraction.
- Test invalid domains and websites that block automated requests.

## 📊 Keyword Data Note

The current implementation extracts keywords locally using article titles and descriptions. Actual search-volume figures require a working external keyword-data provider; unavailable search volumes are not fabricated.

## 🔐 Security

- Store credentials in environment variables.
- Exclude `.env`, virtual environments, cache files, and local database files from version control.
- Respect website terms of service and crawling restrictions.

## 🔮 Future Improvements

- Integration with a reliable keyword search-volume API.
- Scheduled competitor scans.
- Slack notifications.
- Historical pricing-change comparisons.
- Improved article discovery and publication-date extraction.

## 👨‍💻 Author

**Tanish Kumar**

GitHub: [@tanish0050](https://github.com/tanish0050)

---

*Built as a competitor intelligence project to explore web scraping, data persistence, keyword extraction, pricing monitoring, and automated notifications.*
