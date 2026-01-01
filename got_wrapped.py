"""
🎬 GotWrapped - Your Personal Year in Review

A unified Streamlit dashboard combining:
- Strava fitness activities (running, cycling, swimming, etc.)
- Netflix viewing statistics
- YouTube watch history analytics

All in one beautiful, real-time wrapped dashboard.

Author: Geetesh Singh
Created: 2026-01-01
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from supabase import create_client
from requests_oauthlib import OAuth2Session
import os
from dotenv import load_dotenv

# ============================================================================
# PAGE Ka CONFIG here
# ============================================================================
st.set_page_config(
    page_title="GotWrapped - Your Year in Review",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for branding
st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .got-wrapped-header {
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# ENVIRONMENT & SECRETS SETUP
# ============================================================================
# IMPORTANT: All API keys go in .streamlit/secrets.toml
# See README-GOTWRAPPED.md for detailed setup

try:
    # Supabase
    SUPABASE_URL = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
except KeyError:
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Strava OAuth
try:
    STRAVA_CLIENT_ID = st.secrets.get("STRAVA_CLIENT_ID", "")
    STRAVA_CLIENT_SECRET = st.secrets.get("STRAVA_CLIENT_SECRET", "")
    STRAVA_REDIRECT_URI = st.secrets.get("STRAVA_REDIRECT_URI", "http://localhost:8501")
except:
    STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
    STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
    STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8501")

# Optional YouTube API
try:
    YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
except:
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# ============================================================================
# STRAVA API CONFIGURATION
# ============================================================================
STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"


def get_strava_session(state=None, token=None):
    """Create OAuth2 session for Strava"""
    extra = {"client_id": STRAVA_CLIENT_ID, "client_secret": STRAVA_CLIENT_SECRET}
    return OAuth2Session(
        STRAVA_CLIENT_ID,
        redirect_uri=STRAVA_REDIRECT_URI,
        scope=["activity:read_all"],
        state=state,
        token=token,
        auto_refresh_kwargs=extra,
        auto_refresh_url=STRAVA_TOKEN_URL,
        token_updater=lambda t: st.session_state.__setitem__("strava_token", t),
    )


def strava_authorize_button():
    """Show Strava connect button"""
    if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
        st.error("⚠️ Add STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .streamlit/secrets.toml")
        return

    session = get_strava_session()
    auth_url, state = session.authorization_url(STRAVA_AUTH_URL, approval_prompt="auto", access_type="offline")
    st.session_state["strava_oauth_state"] = state
    st.markdown(f"[🔗 **Connect Your Strava Account**]({auth_url})")
    st.info("Click the link above to authorize. You'll be redirected back automatically.")


def handle_strava_callback():
    """Handle Strava OAuth callback"""
    query_params = st.query_params
    if "code" not in query_params:
        return

    code = query_params.get("code")
    state = query_params.get("state", None)

    try:
        session = get_strava_session(state=state)
        token = session.fetch_token(STRAVA_TOKEN_URL, code=code, client_secret=STRAVA_CLIENT_SECRET)
        st.session_state["strava_token"] = token
        st.success("✅ Strava connected! Refresh to load your activities.")
        st.query_params.clear()
    except Exception as e:
        st.error(f"Failed to authenticate: {e}")


# ============================================================================
# SUPABASE CONNECTION
# ============================================================================
@st.cache_resource
def init_supabase():
    """Initialize Supabase"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ Supabase credentials not found in .streamlit/secrets.toml")
        st.stop()
        st.sidebar.title("🔍 Debug")
        st.sidebar.write(f"URL: {SUPABASE_URL}")
        st.sidebar.write(f"Key starts with: {SUPABASE_KEY[:20]}...")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ============================================================================
# DATA FETCHING - STRAVA
# ============================================================================

@st.cache_data(ttl=300)
def fetch_strava_activities():
    """Fetch Strava activities"""
    token = st.session_state.get("strava_token")
    if not token:
        return pd.DataFrame()

    try:
        session = get_strava_session(token=token)
        resp = session.get(f"{STRAVA_API_BASE}/athlete/activities", params={"per_page": 200, "page": 1})
        
        if resp.status_code != 200:
            return pd.DataFrame()

        activities = resp.json()
        rows = []
        
        for a in activities:
            start_date = pd.to_datetime(a.get("start_date_local"))
            distance_km = a.get("distance", 0) / 1000.0
            duration_min = a.get("moving_time", 0) / 60.0
            
            rows.append({
                "date": start_date.date(),
                "type": a.get("type", "Workout"),
                "distance_km": round(distance_km, 2),
                "duration_min": int(duration_min),
                "elevation_m": a.get("total_elevation_gain", 0),
                "calories": int(a.get("kilojoules", 0) * 0.239),
                "steps": int(distance_km * 1300),
                "active_minutes": int(duration_min),
            })

        df = pd.DataFrame(rows)
        return df.sort_values("date", ascending=False) if not df.empty else df
    except Exception as e:
        st.warning(f"Error fetching Strava: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_netflix():
    """Fetch Netflix data"""
    try:
        response = supabase.table("netflix_history").select("*").execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        if not df.empty:
            df['date_watched'] = pd.to_datetime(df['date_watched'])
            return df.sort_values('date_watched', ascending=False)
        return df
    except Exception as e:
        st.warning(f"Netflix error: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_youtube():
    """Fetch YouTube data"""
    try:
        response = supabase.table("youtube_history").select("*").execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        if not df.empty:
            df['date_watched'] = pd.to_datetime(df['date_watched'])
            return df.sort_values('date_watched', ascending=False)
        return df
    except Exception as e:
        st.warning(f"YouTube error: {e}")
        return pd.DataFrame()


# ============================================================================
# DATA PROCESSING
# ============================================================================

def get_time_range_data(df, date_col, days=30):
    """Get data for last N days"""
    if df.empty:
        return df
    cutoff = pd.Timestamp.now() - timedelta(days=days)
    return df[pd.to_datetime(df[date_col]) >= cutoff]


def calculate_strava_stats(df):
    """Calculate Strava statistics"""
    if df.empty:
        return {}, []
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    today = pd.Timestamp.now().date()
    week_df = df[df['date'] >= (pd.Timestamp.now() - timedelta(days=7))]
    month_df = df[df['date'] >= (pd.Timestamp.now() - timedelta(days=30))]
    today_df = df[df['date'].dt.date == today]
    
    stats = {
        "total_distance": month_df['distance_km'].sum(),
        "total_activities": len(month_df),
        "total_duration": month_df['duration_min'].sum(),
        "total_elevation": month_df['elevation_m'].sum(),
        "avg_distance": week_df['distance_km'].mean() if len(week_df) > 0 else 0,
        "today_distance": today_df['distance_km'].sum(),
        "today_duration": today_df['duration_min'].sum(),
    }
    
    badges = []
    if stats["total_distance"] > 100:
        badges.append("🏃 **Century Club**: 100+ km this month!")
    if stats["total_activities"] > 20:
        badges.append("💪 **Workout Machine**: 20+ activities!")
    if stats["total_elevation"] > 5000:
        badges.append("⛰️ **Mountain Climber**: 5000m elevation!")
    if stats["today_distance"] > 10:
        badges.append("🔥 **On Fire**: 10+ km today!")
    
    return stats, badges


def calculate_netflix_stats(df):
    """Calculate Netflix statistics"""
    if df.empty:
        return {}, []
    
    df = df.copy()
    df['date_watched'] = pd.to_datetime(df['date_watched'])
    
    month_df = df[df['date_watched'] >= (pd.Timestamp.now() - timedelta(days=30))]
    week_df = df[df['date_watched'] >= (pd.Timestamp.now() - timedelta(days=7))]
    
    stats = {
        "total_hours": month_df['duration_minutes'].sum() / 60 if 'duration_minutes' in month_df.columns else 0,
        "episodes": len(month_df),
        "top_show": month_df['show_name'].mode()[0] if 'show_name' in month_df.columns and len(month_df) > 0 else "N/A",
        "top_genre": month_df['genre'].mode()[0] if 'genre' in month_df.columns and len(month_df) > 0 else "N/A",
    }
    
    badges = []
    if stats["total_hours"] > 50:
        badges.append("📺 **Binge Master**: 50+ hours watched!")
    if stats["episodes"] > 30:
        badges.append("👀 **Content Junkie**: 30+ episodes!")
    
    return stats, badges


def calculate_youtube_stats(df):
    """Calculate YouTube statistics"""
    if df.empty:
        return {}, []
    
    df = df.copy()
    df['date_watched'] = pd.to_datetime(df['date_watched'])
    
    month_df = df[df['date_watched'] >= (pd.Timestamp.now() - timedelta(days=30))]
    
    stats = {
        "total_hours": month_df['duration_minutes'].sum() / 60 if 'duration_minutes' in month_df.columns else 0,
        "videos": len(month_df),
        "top_channel": month_df['channel_name'].mode()[0] if 'channel_name' in month_df.columns and len(month_df) > 0 else "N/A",
        "top_category": month_df['category'].mode()[0] if 'category' in month_df.columns and len(month_df) > 0 else "N/A",
    }
    
    badges = []
    if stats["total_hours"] > 100:
        badges.append("🎥 **Video Addict**: 100+ hours!")
    if stats["videos"] > 200:
        badges.append("📱 **Shorts Master**: 200+ videos!")
    
    return stats, badges


def render_badges(badges):
    """Render achievement badges"""
    if not badges:
        st.info("🏆 Keep pushing! Unlock badges by reaching your goals.")
        return
    
    st.subheader("🏆 Your Achievements This Month")
    for badge in badges:
        st.success(badge)


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Header
    st.markdown("""
        <div class="got-wrapped-header">
        <h1>🎬 GotWrapped</h1>
        <p style="font-size: 1.2rem; margin: 0;">Your Personal Year in Review</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**Strava** • **Netflix** • **YouTube** — All in one beautiful dashboard updated in real-time")
    
    # Controls
    col1, col2 = st.columns([4, 1])
    with col1:
        st.info("🔄 Dashboard refreshes automatically")
    with col2:
        if st.button("🔁 Refresh"):
            st.cache_data.clear()
            st.rerun()
    
    # Navigation
    st.markdown("---")
    
    view = st.radio(
        "Choose Your View:",
        ["📊 Overview", "💪 Strava", "📺 Netflix", "📹 YouTube"],
        horizontal=True
    )
    
    st.markdown("---")
    
    # ====================================================================
    # OVERVIEW TAB
    # ====================================================================
    if view == "📊 Overview":
        st.header("Your 2025 in Numbers")
        
        handle_strava_callback()
        strava_df = fetch_strava_activities()
        netflix_df = fetch_netflix()
        youtube_df = fetch_youtube()
        
        if strava_df.empty and netflix_df.empty and youtube_df.empty:
            st.warning("""
            👋 Welcome to GotWrapped!
            
            To get started:
            1. **Strava** - Click "💪 Strava" tab to connect
            2. **Netflix** - Export your viewing activity and upload
            3. **YouTube** - Export your watch history and upload
            
            Then come back here to see your complete wrapped!
            """)
        else:
            # Strava overview
            if not strava_df.empty:
                strava_stats, _ = calculate_strava_stats(strava_df)
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🏃 Distance", f"{strava_stats['total_distance']:.0f} km", "This Month")
                with col2:
                    st.metric("💪 Workouts", f"{strava_stats['total_activities']}", "This Month")
                with col3:
                    st.metric("⏱️ Duration", f"{strava_stats['total_duration']:.0f} min", "Total")
                with col4:
                    st.metric("⛰️ Elevation", f"{strava_stats['total_elevation']:.0f}m", "This Month")
            
            st.divider()
            
            # Netflix overview
            if not netflix_df.empty:
                netflix_stats, _ = calculate_netflix_stats(netflix_df)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📺 Watch Time", f"{netflix_stats['total_hours']:.0f}h", "This Month")
                with col2:
                    st.metric("📺 Episodes", f"{netflix_stats['episodes']}", "Watched")
                with col3:
                    st.metric("🎬 Top Show", netflix_stats['top_show'])
            
            st.divider()
            
            # YouTube overview
            if not youtube_df.empty:
                youtube_stats, _ = calculate_youtube_stats(youtube_df)
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📹 Watch Time", f"{youtube_stats['total_hours']:.0f}h", "This Month")
                with col2:
                    st.metric("📹 Videos", f"{youtube_stats['videos']}", "Watched")
                with col3:
                    st.metric("🎥 Top Channel", youtube_stats['top_channel'])
    
    # ====================================================================
    # STRAVA TAB
    # ====================================================================
    elif view == "💪 Strava":
        st.header("Your Fitness Wrapped")
        
        handle_strava_callback()
        
        if "strava_token" not in st.session_state:
            st.info("📱 Connect your Strava to see your workouts!")
            strava_authorize_button()
        else:
            strava_df = fetch_strava_activities()
            
            if strava_df.empty:
                st.warning("No activities yet. Log some workouts on Strava!")
            else:
                stats, badges = calculate_strava_stats(strava_df)
                
                # Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Distance", f"{stats['today_distance']:.1f} km", "Today")
                with col2:
                    st.metric("This Month", f"{stats['total_distance']:.0f} km")
                with col3:
                    st.metric("Workouts", f"{stats['total_activities']}")
                with col4:
                    st.metric("Elevation", f"{stats['total_elevation']:.0f}m")
                
                st.divider()
                render_badges(badges)
                st.divider()
                
                # Charts
                col1, col2 = st.columns(2)
                with col1:
                    week_df = strava_df[strava_df['date'] >= (pd.Timestamp.now() - timedelta(days=7))].sort_values('date')
                    if not week_df.empty:
                        st.subheader("Distance Trend (7 Days)")
                        st.line_chart(week_df.set_index('date')['distance_km'])
                
                with col2:
                    month_df = strava_df[strava_df['date'] >= (pd.Timestamp.now() - timedelta(days=30))]
                    if not month_df.empty:
                        st.subheader("Workout Types")
                        st.bar_chart(month_df['type'].value_counts())
                
                st.divider()
                st.subheader("Recent Activities")
                display = strava_df.head(10)[['date', 'type', 'distance_km', 'duration_min']].copy()
                display.columns = ['Date', 'Type', 'Distance (km)', 'Duration (min)']
                st.dataframe(display, use_container_width=True)
    
    # ====================================================================
    # NETFLIX TAB
    # ====================================================================
    elif view == "📺 Netflix":
        st.header("Your Netflix Wrapped")
        
        netflix_df = fetch_netflix()
        
        if netflix_df.empty:
            st.warning("No Netflix data yet. Upload your viewing history CSV!")
            
            uploaded = st.file_uploader("Upload Netflix CSV", type="csv")
            if uploaded:
                try:
                    df = pd.read_csv(uploaded)
                    if st.button("Upload to Database"):
                        try:
                            supabase.table("netflix_history").insert(df.to_dict(orient='records')).execute()
                            st.success("✅ Data uploaded!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                except Exception as e:
                    st.error(f"Error reading file: {e}")
        else:
            stats, badges = calculate_netflix_stats(netflix_df)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Watch Time", f"{stats['total_hours']:.0f}h", "This Month")
            with col2:
                st.metric("Episodes", f"{stats['episodes']}")
            with col3:
                st.metric("Top Show", stats['top_show'])
            with col4:
                st.metric("Top Genre", stats['top_genre'])
            
            st.divider()
            render_badges(badges)
            st.divider()
            
            # Charts
            col1, col2 = st.columns(2)
            with col1:
                month_df = netflix_df[netflix_df['date_watched'] >= (pd.Timestamp.now() - timedelta(days=30))]
                if not month_df.empty:
                    grouped = month_df.groupby(month_df['date_watched'].dt.date)['duration_minutes'].sum().reset_index()
                    grouped.columns = ['date', 'minutes']
                    st.subheader("Watch Time Trend")
                    st.bar_chart(grouped.set_index('date')['minutes'])
            
            with col2:
                if not month_df.empty and 'show_name' in month_df.columns:
                    st.subheader("Top Shows")
                    st.bar_chart(month_df['show_name'].value_counts().head(10))
    
    # ====================================================================
    # YOUTUBE TAB
    # ====================================================================
    elif view == "📹 YouTube":
        st.header("Your YouTube Wrapped")
        
        youtube_df = fetch_youtube()
        
        if youtube_df.empty:
            st.warning("No YouTube data yet. Upload your watch history CSV!")
            
            uploaded = st.file_uploader("Upload YouTube CSV", type="csv")
            if uploaded:
                try:
                    df = pd.read_csv(uploaded)
                    if st.button("Upload to Database"):
                        try:
                            supabase.table("youtube_history").insert(df.to_dict(orient='records')).execute()
                            st.success("✅ Data uploaded!")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                except Exception as e:
                    st.error(f"Error reading file: {e}")
        else:
            stats, badges = calculate_youtube_stats(youtube_df)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Watch Time", f"{stats['total_hours']:.0f}h", "This Month")
            with col2:
                st.metric("Videos", f"{stats['videos']}")
            with col3:
                st.metric("Top Channel", stats['top_channel'])
            with col4:
                st.metric("Top Category", stats['top_category'])
            
            st.divider()
            render_badges(badges)
            st.divider()
            
            # Charts
            col1, col2 = st.columns(2)
            with col1:
                month_df = youtube_df[youtube_df['date_watched'] >= (pd.Timestamp.now() - timedelta(days=30))]
                if not month_df.empty:
                    grouped = month_df.groupby(month_df['date_watched'].dt.date)['duration_minutes'].sum().reset_index()
                    grouped.columns = ['date', 'minutes']
                    st.subheader("Watch Time Trend")
                    st.line_chart(grouped.set_index('date')['minutes'])
            
            with col2:
                if not month_df.empty and 'channel_name' in month_df.columns:
                    st.subheader("Top Channels")
                    st.bar_chart(month_df['channel_name'].value_counts().head(10))
    
    # Footer
    st.divider()
    st.markdown("**GotWrapped** — Made with ❤️ using Streamlit + Strava + Supabase")


if __name__ == "__main__":
    main()
