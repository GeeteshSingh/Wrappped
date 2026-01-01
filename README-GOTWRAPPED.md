# 🎬 GotWrapped - Your Personal Year in Review

**One unified dashboard for Strava, Netflix, and YouTube**

A beautiful, real-time Streamlit application that shows you:
- 💪 Your Strava fitness activities (running, cycling, swimming, etc.)
- 📺 Your Netflix viewing habits and top shows
- 📹 Your YouTube watch history and favorite channels

All in one elegant dashboard with instant insights and achievement badges.

## 🌟 Features

- **📊 Overview Dashboard** - See all your stats at a glance
- **💪 Strava Integration** - Live sync of all your workouts with OAuth
- **📺 Netflix Analytics** - Track what you watched and when
- **📹 YouTube Insights** - Analyze your viewing patterns
- **🏆 Achievement Badges** - Unlock badges based on your activity
- **📈 Real-time Charts** - Auto-updating visualizations
- **🎨 Beautiful UI** - Modern, responsive design
- **🚀 Ready to Deploy** - Works on Streamlit Cloud out of the box

## 📋 Prerequisites

- Python 3.8+
- Free accounts:
  - [Strava Developer](https://www.strava.com/settings/api)
  - [Supabase](https://supabase.com/)
  - Netflix account
  - Google account (for YouTube)

## 🚀 Quick Start (5 Minutes)

### 1. Clone and Setup

```bash
mkdir got-wrapped && cd got-wrapped

# Virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Get API Credentials

**Strava:**
1. Go to https://www.strava.com/settings/api
2. Create Application
3. Copy Client ID and Client Secret

**Supabase:**
1. Go to https://supabase.com
2. Create project
3. Copy Project URL and anon key
4. Run SQL setup (see below)

### 3. Create Secrets File

Create `.streamlit/secrets.toml`:

```toml
[connections.supabase]
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"

STRAVA_CLIENT_ID = "your-strava-client-id"
STRAVA_CLIENT_SECRET = "your-strava-client-secret"
STRAVA_REDIRECT_URI = "http://localhost:8501"
```

### 4. Setup Supabase Tables

In Supabase SQL Editor, run:

```sql
CREATE TABLE netflix_history (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  date_watched TIMESTAMP,
  show_name VARCHAR,
  genre VARCHAR,
  duration_minutes INT,
  profile_name VARCHAR,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE youtube_history (
  id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
  date_watched TIMESTAMP,
  video_title VARCHAR,
  channel_name VARCHAR,
  duration_minutes INT,
  category VARCHAR,
  created_at TIMESTAMP DEFAULT NOW()
);
```

### 5. Run the App

```bash
streamlit run streamlit_app.py
```

Open http://localhost:8501 and start connecting your data!

## 📖 Full Setup Guide

See [README-GOTWRAPPED.md](README-GOTWRAPPED.md) for:
- Detailed API setup
- Data export instructions
- Customization options
- Deployment guide
- Troubleshooting

## 🎯 How to Use

### Overview
Start at the **Overview** tab to see all your stats at once.

### Strava
1. Click **💪 Strava** tab
2. Click "Connect Your Strava Account"
3. Authorize on Strava
4. Your workouts appear instantly! 🎉

### Netflix
1. Export your viewing activity:
   - Netflix Settings → Account → Profile & Parental Controls
   - Viewing activity → Download as CSV
2. Click **📺 Netflix** tab
3. Upload your CSV
4. Done! 📊

### YouTube
1. Download your watch history:
   - takeout.google.com
   - Select YouTube
   - Download
2. Click **📹 YouTube** tab
3. Upload your CSV
4. Done! 📊

## 🔧 Configuration

### Change Strava Refresh Rate

Edit `got_wrapped.py`, find:
```python
@st.cache_data(ttl=300)  # 300 seconds = 5 minutes
```

Change `300` to your preferred seconds.

### Add Custom Badges

In `calculate_strava_stats()`:
```python
if stats["total_distance"] > 200:
    badges.append("🌍 **World Traveler**: 200+ km!")
```

### Customize Colors

Modify the CSS in the `st.markdown()` section at the top.

## 📊 Data Formats

**Netflix CSV (from Netflix):**
```
date_watched,show_name,genre,duration_minutes
2025-12-31 20:30:00,The Office,Comedy,42
```

**YouTube CSV (from Google Takeout):**
```
date_watched,video_title,channel_name,duration_minutes,category
2025-12-31 14:30:00,How to Code,Tech Tutorials,18,Education
```

**Strava:** Fetched automatically from Strava API!

## 🚀 Deployment

### Streamlit Cloud (Free)

1. Push to GitHub
2. Go to share.streamlit.io
3. New app → Connect GitHub repo
4. Select `got_wrapped.py`
5. Add secrets in Settings → Secrets
6. Deploy! 🎉

See [DEPLOYMENT-GOTWRAPPED.md](DEPLOYMENT-GOTWRAPPED.md) for details.

## 📁 Project Structure

```
got-wrapped/
├── got_wrapped.py              # Main app
├── requirements.txt            # Dependencies
├── .streamlit/
│   └── secrets.toml           # API keys (keep secret!)
├── README-GOTWRAPPED.md       # Full documentation
├── DEPLOYMENT-GOTWRAPPED.md   # Deployment guide
└── .gitignore                 # Git rules
```

## 🆘 Troubleshooting

### Strava Not Connecting

**Problem:** "Credentials not found"

**Solution:**
1. Check `.streamlit/secrets.toml` exists
2. Verify STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET are filled
3. Restart app

### Netflix/YouTube CSV Not Loading

**Problem:** "Invalid data"

**Solution:**
1. Check CSV column names match expected format
2. Verify timestamps are in YYYY-MM-DD HH:MM:SS format
3. See DATA-FORMAT-GOTWRAPPED.md for examples

### Supabase Connection Error

**Problem:** "Connection refused"

**Solution:**
1. Verify SUPABASE_URL and SUPABASE_KEY are correct
2. Check Supabase project is active
3. Verify tables exist (run SQL setup again)

## 📚 Resources

- [Streamlit Docs](https://docs.streamlit.io/)
- [Strava API](https://developers.strava.com/)
- [Supabase Docs](https://supabase.com/docs)
- [YouTube Data API](https://developers.google.com/youtube/v3)

## 🎨 Customization Examples

**Dark Mode Toggle:**
```python
st.set_page_config(
    ...,
    initial_sidebar_state="collapsed"
)
```

**Add More Metrics:**
```python
if not strava_df.empty:
    st.metric("New Metric", value)
```

**Custom Colors:**
```python
st.markdown("""
    <style>
    .metric { color: #your-color; }
    </style>
""", unsafe_allow_html=True)
```

## 📞 Support

1. **Setup issues?** → Check README-GOTWRAPPED.md
2. **Strava problems?** → See STRAVA-SETUP-GOTWRAPPED.md
3. **Data format?** → See DATA-FORMAT-GOTWRAPPED.md
4. **Deploying?** → See DEPLOYMENT-GOTWRAPPED.md

## 🎉 You're All Set!

You now have everything you need. Just:
1. Get your API credentials
2. Create `.streamlit/secrets.toml`
3. Run `streamlit run got_wrapped.py`
4. Connect your data
5. See your wrapped! 🎬

---

**Made with ❤️ for tracking your year**

**Questions? Check the docs or reach out!**
