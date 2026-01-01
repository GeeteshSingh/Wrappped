"""
🎬 GotWrapped - Your Personal Year in Review
Enhanced Dashboard: Strava + Netflix + YouTube
Author: Geetesh Singh
Fixed: Strava OAuth + Advanced Stats
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from supabase import create_client
from requests_oauthlib import OAuth2Session
import os
from dotenv import load_dotenv
import re

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="GotWrapped - Your Year in Review",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
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
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# ============================================================================
# LOAD SECRETS & ENV VARIABLES
# ============================================================================
try:
    SUPABASE_URL = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
except Exception:
    load_dotenv()
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

try:
    STRAVA_CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
    STRAVA_CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
    STRAVA_REDIRECT_URI = st.secrets.get("STRAVA_REDIRECT_URI", "http://localhost:8501")
except Exception:
    load_dotenv()
    STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
    STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
    STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8501")

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"

# ============================================================================
# SUPABASE INIT
# ============================================================================
@st.cache_resource
def init_supabase():
    """Initialize Supabase connection"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_supabase()

# ============================================================================
# STRAVA OAUTH FUNCTIONS - FIXED
# ============================================================================

def get_strava_session(state=None, token=None):
    """Create Strava OAuth2 session"""
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
        st.error("⚠️ STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET not found in secrets.toml")
        return

    try:
        session = get_strava_session()
        auth_url, state = session.authorization_url(
            STRAVA_AUTH_URL,
            approval_prompt="auto",
            access_type="offline"
        )
        st.session_state["strava_oauth_state"] = state
        
        st.markdown(f"[🔗 **Connect Your Strava Account**]({auth_url})")
        st.info("👆 Click the link above to authorize. You'll be redirected back automatically.")
    except Exception as e:
        st.error(f"Error generating Strava link: {str(e)}")


def handle_strava_callback():
    """Handle OAuth callback from Strava - FIXED FOR MISSING_TOKEN"""
    query_params = st.query_params
    
    if "code" not in query_params:
        return

    code = query_params.get("code")
    state = query_params.get("state", None)

    try:
        session = get_strava_session(state=state)
        # CRITICAL FIX: Include client_id in token request
        token = session.fetch_token(
            STRAVA_TOKEN_URL,
            code=code,
            client_secret=STRAVA_CLIENT_SECRET,
            include_client_id=True  # ← THIS FIXES THE missing_token ERROR
        )
        st.session_state["strava_token"] = token
        st.success("✅ Strava connected! Refresh to load your activities.")
        st.query_params.clear()
        st.rerun()
    except Exception as e:
        st.error(f"❌ Failed to authenticate: {str(e)}")


# ============================================================================
# DATA FETCHING
# ============================================================================

@st.cache_data(ttl=300)
def fetch_strava_activities():
    """Fetch Strava activities"""
    token = st.session_state.get("strava_token")
    if not token:
        return pd.DataFrame()

    try:
        session = get_strava_session(token=token)
        resp = session.get(
            f"{STRAVA_API_BASE}/athlete/activities",
            params={"per_page": 200, "page": 1}
        )
        
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
                "name": a.get("name", "Activity"),
                "distance_km": round(distance_km, 2),
                "duration_min": int(duration_min),
                "elevation_m": a.get("total_elevation_gain", 0),
                "calories": int(a.get("kilojoules", 0) * 0.239),
                "avg_speed": round(distance_km / (duration_min / 60), 2) if duration_min > 0 else 0,
            })

        df = pd.DataFrame(rows)
        return df.sort_values("date", ascending=False) if not df.empty else df
    except Exception as e:
        st.warning(f"Error fetching Strava: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_netflix():
    """Fetch Netflix data from Supabase"""
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("netflix_history").select("*").execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        if not df.empty:
            df['date_watched'] = pd.to_datetime(df['date_watched'])
            return df.sort_values('date_watched', ascending=False)
        return df
    except Exception as e:
        return pd.DataFrame()


@st.cache_data(ttl=30)
def fetch_youtube():
    """Fetch YouTube data from Supabase"""
    if not supabase:
        return pd.DataFrame()
    try:
        response = supabase.table("youtube_history").select("*").execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
        if not df.empty:
            df['date_watched'] = pd.to_datetime(df['date_watched'])
            return df.sort_values('date_watched', ascending=False)
        return df
    except Exception as e:
        return pd.DataFrame()


# ============================================================================
# ADVANCED STATISTICS
# ============================================================================

def calculate_strava_stats_advanced(df, year=None):
    """Calculate advanced Strava stats including sport-specific breakdown"""
    if df.empty:
        return {}, {}
    
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    if year:
        df = df[df['date'].dt.year == year]
    
    if df.empty:
        return {}, {}
    
    # Overall stats
    overall_stats = {
        "total_distance": df['distance_km'].sum(),
        "total_activities": len(df),
        "total_duration": df['duration_min'].sum(),
        "total_elevation": df['elevation_m'].sum(),
        "total_calories": df['calories'].sum(),
        "avg_speed": df['avg_speed'].mean(),
        "unique_sports": df['type'].nunique(),
    }
    
    # Sport-specific breakdown
    sport_stats = {}
    for sport in df['type'].unique():
        sport_df = df[df['type'] == sport]
        sport_stats[sport] = {
            "count": len(sport_df),
            "distance": sport_df['distance_km'].sum(),
            "duration": sport_df['duration_min'].sum(),
            "elevation": sport_df['elevation_m'].sum(),
            "avg_distance": sport_df['distance_km'].mean(),
            "avg_duration": sport_df['duration_min'].mean(),
        }
    
    return overall_stats, sport_stats


def calculate_netflix_stats(df, year=None):
    """Calculate Netflix stats"""
    if df.empty:
        return {}
    
    df = df.copy()
    df['date_watched'] = pd.to_datetime(df['date_watched'])
    
    if year:
        df = df[df['date_watched'].dt.year == year]
    
    if df.empty:
        return {}
    
    stats = {
        "total_hours": df['duration_minutes'].sum() / 60 if 'duration_minutes' in df.columns else 0,
        "episodes": len(df),
        "top_show": df['show_name'].mode()[0] if 'show_name' in df.columns and len(df) > 0 else "N/A",
        "unique_shows": df['show_name'].nunique(),
    }
    
    return stats


def calculate_youtube_stats(df, year=None):
    """Calculate YouTube stats"""
    if df.empty:
        return {}
    
    df = df.copy()
    df['date_watched'] = pd.to_datetime(df['date_watched'])
    
    if year:
        df = df[df['date_watched'].dt.year == year]
    
    if df.empty:
        return {}
    
    stats = {
        "total_hours": df['duration_minutes'].sum() / 60 if 'duration_minutes' in df.columns else 0,
        "videos": len(df),
        "unique_channels": df['channel_name'].nunique() if 'channel_name' in df.columns else 0,
    }
    
    if 'channel_name' in df.columns and len(df) > 0:
        valid_channels = df['channel_name'].dropna()
        if len(valid_channels) > 0:
            mode_result = valid_channels.mode()
            stats["top_channel"] = mode_result[0] if len(mode_result) > 0 else "Unknown"
        else:
            stats["top_channel"] = "Unknown"
    else:
        stats["top_channel"] = "Unknown"
    
    return stats


# ============================================================================
# DATA UPLOAD FUNCTIONS
# ============================================================================

def normalize_netflix_df(df):
    """Normalize Netflix CSV"""
    df = df.copy()
    
    col_mapping = {
        'Date': 'date_watched',
        'date': 'date_watched',
        'Title': 'show_name',
        'title': 'show_name',
        'Show Name': 'show_name',
        'Genre': 'genre',
        'Duration': 'duration_minutes',
    }
    
    for actual_col in df.columns.tolist():
        if actual_col in col_mapping:
            df = df.rename(columns={actual_col: col_mapping[actual_col]})
    
    required = ['date_watched', 'show_name']
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return None
    
    keep_cols = [col for col in df.columns if col in ['date_watched', 'show_name', 'genre', 'duration_minutes']]
    df = df[keep_cols]
    
    try:
        df['date_watched'] = pd.to_datetime(df['date_watched'], format='mixed', dayfirst=False)
    except Exception as e:
        st.warning(f"Could not parse dates: {e}")
        return None
    
    return df


def normalize_youtube_df(df):
    """Normalize YouTube CSV"""
    df = df.copy()
    
    col_mapping = {
        'Date': 'date_watched',
        'date': 'date_watched',
        'Title': 'video_title',
        'title': 'video_title',
        'Channel': 'channel_name',
        'channel': 'channel_name',
    }
    
    for actual_col in df.columns.tolist():
        if actual_col in col_mapping:
            df = df.rename(columns={actual_col: col_mapping[actual_col]})
    
    required = ['date_watched', 'video_title']
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return None
    
    keep_cols = [col for col in df.columns if col in ['date_watched', 'video_title', 'channel_name', 'duration_minutes']]
    df = df[keep_cols]
    
    try:
        df['date_watched'] = pd.to_datetime(df['date_watched'], format='mixed', dayfirst=False)
    except Exception as e:
        st.warning(f"Could not parse dates: {e}")
        return None
    
    return df


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
    
    st.markdown("**Strava** • **Netflix** • **YouTube** — All in one dashboard")
    
    # Year selector in sidebar
    st.sidebar.header("⚙️ Settings")
    selected_year = st.sidebar.radio("Select Year:", [2025, 2026], horizontal=True)
    st.sidebar.info(f"📅 Showing data for **{selected_year}**")
    
    # Refresh button
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"🔄 Showing {selected_year} data")
    with col2:
        if st.button("🔁 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    
    # Navigation
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
        st.header(f"Your {selected_year} in Numbers")
        
        handle_strava_callback()
        strava_df = fetch_strava_activities()
        netflix_df = fetch_netflix()
        youtube_df = fetch_youtube()
        
        if strava_df.empty and netflix_df.empty and youtube_df.empty:
            st.warning("""
            👋 Welcome to GotWrapped!
            
            To get started:
            1. **Strava** - Click "💪 Strava" tab to connect
            2. **Netflix** - Export and upload your viewing activity
            3. **YouTube** - Export and upload your watch history
            """)
        else:
            # STRAVA METRICS
            if not strava_df.empty:
                overall_stats, sport_stats = calculate_strava_stats_advanced(strava_df, year=selected_year)
                if overall_stats:
                    st.subheader("💪 Strava Fitness")
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("🏃 Distance", f"{overall_stats['total_distance']:.0f} km")
                    with col2:
                        st.metric("💪 Workouts", f"{overall_stats['total_activities']}")
                    with col3:
                        st.metric("⏱️ Duration", f"{overall_stats['total_duration']:.0f} min")
                    with col4:
                        st.metric("⛰️ Elevation", f"{overall_stats['total_elevation']:.0f}m")
                    with col5:
                        st.metric("🔥 Calories", f"{overall_stats['total_calories']:.0f}")
                    
                    # Strava charts
                    strava_year_df = strava_df[strava_df['date'].dt.year == selected_year]
                    if not strava_year_df.empty:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Workouts by Type")
                            workout_counts = strava_year_df['type'].value_counts()
                            st.bar_chart(workout_counts)
                        
                        with col2:
                            st.subheader("Distance by Type")
                            distance_by_type = strava_year_df.groupby('type')['distance_km'].sum()
                            st.bar_chart(distance_by_type)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Monthly Distance Trend")
                            monthly_dist = strava_year_df.set_index('date').resample('M')['distance_km'].sum()
                            st.line_chart(monthly_dist)
                        
                        with col2:
                            st.subheader("Monthly Activity Count")
                            monthly_count = strava_year_df.set_index('date').resample('M').size()
                            st.bar_chart(monthly_count)
                    
                    st.divider()
            
            # NETFLIX METRICS
            if not netflix_df.empty:
                netflix_stats = calculate_netflix_stats(netflix_df, year=selected_year)
                if netflix_stats:
                    st.subheader("📺 Netflix")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📺 Watch Time", f"{netflix_stats['total_hours']:.0f}h")
                    with col2:
                        st.metric("📺 Episodes", f"{netflix_stats['episodes']}")
                    with col3:
                        st.metric("🎬 Top Show", netflix_stats['top_show'][:15])
                    with col4:
                        st.metric("📚 Unique Shows", f"{netflix_stats['unique_shows']}")
                    
                    # Netflix charts
                    netflix_year_df = netflix_df[netflix_df['date_watched'].dt.year == selected_year]
                    if not netflix_year_df.empty:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Top 10 Shows Watched")
                            top_shows = netflix_year_df['show_name'].value_counts().head(10)
                            st.bar_chart(top_shows)
                        
                        with col2:
                            st.subheader("Watch Time by Month")
                            if 'duration_minutes' in netflix_year_df.columns:
                                monthly_hours = netflix_year_df.set_index('date_watched').resample('M')['duration_minutes'].sum() / 60
                                st.line_chart(monthly_hours)
                    
                    st.divider()
            
            # YOUTUBE METRICS
            if not youtube_df.empty:
                youtube_stats = calculate_youtube_stats(youtube_df, year=selected_year)
                if youtube_stats:
                    st.subheader("📹 YouTube")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("📹 Watch Time", f"{youtube_stats['total_hours']:.0f}h")
                    with col2:
                        st.metric("📹 Videos", f"{youtube_stats['videos']}")
                    with col3:
                        st.metric("🎥 Top Channel", youtube_stats['top_channel'][:15])
                    with col4:
                        st.metric("📺 Unique Channels", f"{youtube_stats['unique_channels']}")
                    
                    # YouTube charts
                    youtube_year_df = youtube_df[youtube_df['date_watched'].dt.year == selected_year]
                    if not youtube_year_df.empty:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Top 10 Channels")
                            top_channels = youtube_year_df['channel_name'].value_counts().head(10)
                            st.bar_chart(top_channels)
                        
                        with col2:
                            st.subheader("Videos by Month")
                            monthly_videos = youtube_year_df.set_index('date_watched').resample('M').size()
                            st.bar_chart(monthly_videos)
                    
                    st.divider()
    
    # ====================================================================
    # STRAVA TAB - ENHANCED
    # ====================================================================
    elif view == "💪 Strava":
        st.header(f"Your {selected_year} Fitness Wrapped")
        
        handle_strava_callback()
        
        if "strava_token" not in st.session_state:
            st.info("📱 Connect your Strava to see your workouts!")
            strava_authorize_button()
        else:
            strava_df = fetch_strava_activities()
            
            if strava_df.empty:
                st.warning("No activities yet. Log some workouts on Strava!")
            else:
                overall_stats, sport_stats = calculate_strava_stats_advanced(strava_df, year=selected_year)
                
                if overall_stats:
                    # Overall metrics
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.metric("🏃 Total Distance", f"{overall_stats['total_distance']:.0f} km")
                    with col2:
                        st.metric("💪 Total Workouts", f"{overall_stats['total_activities']}")
                    with col3:
                        st.metric("⏱️ Total Duration", f"{overall_stats['total_duration']:.0f} min")
                    with col4:
                        st.metric("⛰️ Total Elevation", f"{overall_stats['total_elevation']:.0f}m")
                    with col5:
                        st.metric("🔥 Total Calories", f"{overall_stats['total_calories']:.0f}")
                    
                    st.divider()
                    
                    # Sport/Activity Breakdown
                    st.subheader("📊 Your Sports Breakdown")
                    
                    sport_df = pd.DataFrame([
                        {
                            "Sport": sport,
                            "Count": data["count"],
                            "Distance (km)": round(data["distance"], 2),
                            "Duration (hrs)": round(data["duration"] / 60, 2),
                            "Avg Distance (km)": round(data["avg_distance"], 2),
                            "Elevation (m)": int(data["elevation"]),
                        }
                        for sport, data in sport_stats.items()
                    ]).sort_values("Count", ascending=False)
                    
                    st.dataframe(sport_df, use_container_width=True)
                    
                    st.divider()
                    
                    # Most Loved Sport
                    if sport_stats:
                        most_loved = max(sport_stats.items(), key=lambda x: x[1]["count"])
                        st.subheader(f"❤️ Most Loved Sport: {most_loved[0]}")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Times", most_loved[1]["count"])
                        with col2:
                            st.metric("Total Distance", f"{most_loved[1]['distance']:.0f} km")
                        with col3:
                            st.metric("Total Duration", f"{most_loved[1]['duration']:.0f} min")
                    
                    st.divider()
                    
                    # Charts
                    strava_year_df = strava_df[strava_df['date'].dt.year == selected_year]
                    if not strava_year_df.empty:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Workout Count by Type")
                            workout_counts = strava_year_df['type'].value_counts()
                            st.bar_chart(workout_counts)
                        
                        with col2:
                            st.subheader("Distance by Type")
                            distance_by_type = strava_year_df.groupby('type')['distance_km'].sum().sort_values(ascending=False)
                            st.bar_chart(distance_by_type)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            st.subheader("Monthly Distance Progression")
                            monthly_dist = strava_year_df.set_index('date').resample('M')['distance_km'].sum()
                            st.line_chart(monthly_dist)
                        
                        with col2:
                            st.subheader("Weekly Activity Heatmap")
                            weekly_count = strava_year_df.groupby(strava_year_df['date'].dt.isocalendar().week).size()
                            st.bar_chart(weekly_count)
                        
                        # Unique sports count
                        st.info(f"🏆 You've done **{overall_stats['unique_sports']}** different types of sports/activities!")
                        
                        st.divider()
                        st.subheader("📋 Recent Activities")
                        recent_display = strava_year_df.head(15)[['date', 'name', 'type', 'distance_km', 'duration_min', 'elevation_m']].copy()
                        recent_display.columns = ['Date', 'Activity', 'Type', 'Distance (km)', 'Duration (min)', 'Elevation (m)']
                        st.dataframe(recent_display, use_container_width=True)
    
    # ====================================================================
    # NETFLIX TAB
    # ====================================================================
    elif view == "📺 Netflix":
        st.header(f"Your {selected_year} Netflix Wrapped")
        
        netflix_df = fetch_netflix()
        
        if netflix_df.empty:
            st.warning("No Netflix data yet. Upload your viewing history CSV!")
            st.info("📝 **Required columns:** Date, Title")
            
            uploaded = st.file_uploader("Upload Netflix CSV", type="csv", key="netflix_uploader")
            if uploaded:
                try:
                    df = pd.read_csv(uploaded)
                    df_normalized = normalize_netflix_df(df)
                    if df_normalized is not None and not df_normalized.empty:
                        st.dataframe(df_normalized.head(), use_container_width=True)
                        
                        if st.button("✅ Upload to Database", key="netflix_upload_btn"):
                            try:
                                df_normalized['date_watched'] = df_normalized['date_watched'].dt.strftime('%Y-%m-%d')
                                records = df_normalized.to_dict(orient='records')
                                supabase.table("netflix_history").insert(records).execute()
                                st.success("✅ Netflix data uploaded!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Upload error: {str(e)}")
                except Exception as e:
                    st.error(f"CSV reading error: {str(e)}")
        else:
            netflix_stats = calculate_netflix_stats(netflix_df, year=selected_year)
            
            if netflix_stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📺 Watch Time", f"{netflix_stats['total_hours']:.0f}h")
                with col2:
                    st.metric("📺 Episodes", f"{netflix_stats['episodes']}")
                with col3:
                    st.metric("🎬 Top Show", netflix_stats['top_show'][:20])
                with col4:
                    st.metric("📚 Unique Shows", f"{netflix_stats['unique_shows']}")
                
                st.divider()
                
                # Charts
                netflix_year_df = netflix_df[netflix_df['date_watched'].dt.year == selected_year]
                if not netflix_year_df.empty:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Top 15 Shows Watched")
                        top_shows = netflix_year_df['show_name'].value_counts().head(15)
                        st.bar_chart(top_shows)
                    
                    with col2:
                        st.subheader("Monthly Watch Time")
                        if 'duration_minutes' in netflix_year_df.columns:
                            monthly_hours = netflix_year_df.set_index('date_watched').resample('M')['duration_minutes'].sum() / 60
                            st.line_chart(monthly_hours)
                    
                    st.divider()
                    st.subheader("📊 Viewing Statistics")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Most Watched Genre", netflix_year_df['genre'].mode()[0] if 'genre' in netflix_year_df.columns else "N/A")
                    with col2:
                        st.metric("Avg Episodes per Show", f"{netflix_stats['episodes'] / netflix_stats['unique_shows']:.1f}")
    
    # ====================================================================
    # YOUTUBE TAB
    # ====================================================================
    elif view == "📹 YouTube":
        st.header(f"Your {selected_year} YouTube Wrapped")
        
        youtube_df = fetch_youtube()
        
        if youtube_df.empty:
            st.warning("No YouTube data yet. Upload your watch history!")
            
            uploaded = st.file_uploader("Upload YouTube CSV (myactivity.csv)", type="csv", key="youtube_csv")
            if uploaded:
                try:
                    df = pd.read_csv(uploaded)
                    
                    # Extract YouTube activities
                    youtube_rows = df[df['activity'] == 'YouTube'].copy()
                    
                    if not youtube_rows.empty:
                        st.success(f"Found {len(youtube_rows)} YouTube videos")
                        st.dataframe(youtube_rows.head(), use_container_width=True)
                        
                        if st.button("✅ Upload to Database", key="youtube_upload"):
                            try:
                                records = youtube_rows[['date_watched', 'video_title', 'channel_name']].to_dict(orient='records')
                                supabase.table("youtube_history").insert(records).execute()
                                st.success("✅ YouTube data uploaded!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Upload error: {str(e)}")
                except Exception as e:
                    st.error(f"CSV reading error: {str(e)}")
        else:
            youtube_stats = calculate_youtube_stats(youtube_df, year=selected_year)
            
            if youtube_stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📹 Watch Time", f"{youtube_stats['total_hours']:.0f}h")
                with col2:
                    st.metric("📹 Videos", f"{youtube_stats['videos']}")
                with col3:
                    st.metric("🎥 Top Channel", youtube_stats['top_channel'][:20])
                with col4:
                    st.metric("📺 Unique Channels", f"{youtube_stats['unique_channels']}")
                
                st.divider()
                
                # Charts
                youtube_year_df = youtube_df[youtube_df['date_watched'].dt.year == selected_year]
                if not youtube_year_df.empty:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.subheader("Top 15 Channels")
                        top_channels = youtube_year_df['channel_name'].value_counts().head(15)
                        st.bar_chart(top_channels)
                    
                    with col2:
                        st.subheader("Monthly Videos Watched")
                        monthly_videos = youtube_year_df.set_index('date_watched').resample('M').size()
                        st.bar_chart(monthly_videos)
                    
                    st.divider()
                    st.subheader("📊 Channel Insights")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Avg Videos per Channel", f"{youtube_stats['videos'] / youtube_stats['unique_channels']:.1f}")
                    with col2:
                        st.metric("Most Watched Channel Count", youtube_year_df['channel_name'].value_counts().iloc[0])
    
    # Footer
    st.divider()
    st.markdown("**GotWrapped** — Made with ❤️ using Streamlit + Strava + Supabase")


if __name__ == "__main__":
    main()
