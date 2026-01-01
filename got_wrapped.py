# """
# 🎬 GotWrapped - Your Personal Year in Review
# Enhanced Dashboard: Strava + Netflix + YouTube
# Author: Geetesh Singh
# Fixed: Strava OAuth + Advanced Stats
# """
#
# import streamlit as st
# import pandas as pd
# import numpy as np
# from datetime import datetime, timedelta
# from supabase import create_client
# from requests_oauthlib import OAuth2Session
# import os
# from dotenv import load_dotenv
# import re
#
# # ============================================================================
# # PAGE CONFIG
# # ============================================================================
# st.set_page_config(
#     page_title="GotWrapped - Your Year in Review",
#     page_icon="🎬",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )
#
# # Custom CSS
# st.markdown("""
#     <style>
#     .main {
#         padding-top: 2rem;
#     }
#     .got-wrapped-header {
#         text-align: center;
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         padding: 2rem;
#         border-radius: 10px;
#         color: white;
#         margin-bottom: 2rem;
#     }
#     .metric-card {
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         padding: 1rem;
#         border-radius: 10px;
#         color: white;
#     }
#     </style>
# """, unsafe_allow_html=True)
#
# # ============================================================================
# # LOAD SECRETS & ENV VARIABLES
# # ============================================================================
# try:
#     SUPABASE_URL = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
#     SUPABASE_KEY = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]
# except Exception:
#     load_dotenv()
#     SUPABASE_URL = os.getenv("SUPABASE_URL", "")
#     SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
#
# try:
#     STRAVA_CLIENT_ID = st.secrets["STRAVA_CLIENT_ID"]
#     STRAVA_CLIENT_SECRET = st.secrets["STRAVA_CLIENT_SECRET"]
#     STRAVA_REDIRECT_URI = st.secrets.get("STRAVA_REDIRECT_URI", "http://localhost:8501")
# except Exception:
#     load_dotenv()
#     STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID", "")
#     STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET", "")
#     STRAVA_REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI", "http://localhost:8501")
#
# STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
# STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
# STRAVA_API_BASE = "https://www.strava.com/api/v3"
#
# # ============================================================================
# # SUPABASE INIT
# # ============================================================================
# @st.cache_resource
# def init_supabase():
#     """Initialize Supabase connection"""
#     if not SUPABASE_URL or not SUPABASE_KEY:
#         return None
#     try:
#         return create_client(SUPABASE_URL, SUPABASE_KEY)
#     except Exception as e:
#         return None
#
# supabase = init_supabase()
#
# # ============================================================================
# # STRAVA OAUTH FUNCTIONS - FIXED
# # ============================================================================
#
# def get_strava_session(state=None, token=None):
#     """Create Strava OAuth2 session"""
#     extra = {"client_id": STRAVA_CLIENT_ID, "client_secret": STRAVA_CLIENT_SECRET}
#     return OAuth2Session(
#         STRAVA_CLIENT_ID,
#         redirect_uri=STRAVA_REDIRECT_URI,
#         scope=["activity:read_all"],
#         state=state,
#         token=token,
#         auto_refresh_kwargs=extra,
#         auto_refresh_url=STRAVA_TOKEN_URL,
#         token_updater=lambda t: st.session_state.__setitem__("strava_token", t),
#     )
#
#
# def strava_authorize_button():
#     """Show Strava connect button"""
#     if not STRAVA_CLIENT_ID or not STRAVA_CLIENT_SECRET:
#         st.error("⚠️ STRAVA_CLIENT_ID or STRAVA_CLIENT_SECRET not found in secrets.toml")
#         return
#
#     try:
#         session = get_strava_session()
#         auth_url, state = session.authorization_url(
#             STRAVA_AUTH_URL,
#             approval_prompt="auto",
#             access_type="offline"
#         )
#         st.session_state["strava_oauth_state"] = state
#
#         st.markdown(f"[🔗 **Connect Your Strava Account**]({auth_url})")
#         st.info("👆 Click the link above to authorize. You'll be redirected back automatically.")
#     except Exception as e:
#         st.error(f"Error generating Strava link: {str(e)}")
#
#
# def handle_strava_callback():
#     """Handle OAuth callback from Strava - FIXED FOR MISSING_TOKEN"""
#     query_params = st.query_params
#
#     if "code" not in query_params:
#         return
#
#     code = query_params.get("code")
#     state = query_params.get("state", None)
#
#     try:
#         session = get_strava_session(state=state)
#         # CRITICAL FIX: Include client_id in token request
#         token = session.fetch_token(
#             STRAVA_TOKEN_URL,
#             code=code,
#             client_secret=STRAVA_CLIENT_SECRET,
#             include_client_id=True  # ← THIS FIXES THE missing_token ERROR
#         )
#         st.session_state["strava_token"] = token
#         st.success("✅ Strava connected! Refresh to load your activities.")
#         st.query_params.clear()
#         st.rerun()
#     except Exception as e:
#         st.error(f"❌ Failed to authenticate: {str(e)}")
#
#
# # ============================================================================
# # DATA FETCHING
# # ============================================================================
#
# @st.cache_data(ttl=300)
# def fetch_strava_activities():
#     """Fetch Strava activities"""
#     token = st.session_state.get("strava_token")
#     if not token:
#         return pd.DataFrame()
#
#     try:
#         session = get_strava_session(token=token)
#         resp = session.get(
#             f"{STRAVA_API_BASE}/athlete/activities",
#             params={"per_page": 200, "page": 1}
#         )
#
#         if resp.status_code != 200:
#             return pd.DataFrame()
#
#         activities = resp.json()
#         rows = []
#
#         for a in activities:
#             start_date = pd.to_datetime(a.get("start_date_local"))
#             distance_km = a.get("distance", 0) / 1000.0
#             duration_min = a.get("moving_time", 0) / 60.0
#
#             rows.append({
#                 "date": start_date.date(),
#                 "type": a.get("type", "Workout"),
#                 "name": a.get("name", "Activity"),
#                 "distance_km": round(distance_km, 2),
#                 "duration_min": int(duration_min),
#                 "elevation_m": a.get("total_elevation_gain", 0),
#                 "calories": int(a.get("kilojoules", 0) * 0.239),
#                 "avg_speed": round(distance_km / (duration_min / 60), 2) if duration_min > 0 else 0,
#             })
#
#         df = pd.DataFrame(rows)
#         return df.sort_values("date", ascending=False) if not df.empty else df
#     except Exception as e:
#         st.warning(f"Error fetching Strava: {e}")
#         return pd.DataFrame()
#
#
# @st.cache_data(ttl=30)
# def fetch_netflix():
#     """Fetch Netflix data from Supabase"""
#     if not supabase:
#         return pd.DataFrame()
#     try:
#         response = supabase.table("netflix_history").select("*").execute()
#         df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
#         if not df.empty:
#             df['date_watched'] = pd.to_datetime(df['date_watched'])
#             return df.sort_values('date_watched', ascending=False)
#         return df
#     except Exception as e:
#         return pd.DataFrame()
#
#
# @st.cache_data(ttl=30)
# def fetch_youtube():
#     """Fetch YouTube data from Supabase"""
#     if not supabase:
#         return pd.DataFrame()
#     try:
#         response = supabase.table("youtube_history").select("*").execute()
#         df = pd.DataFrame(response.data) if response.data else pd.DataFrame()
#         if not df.empty:
#             df['date_watched'] = pd.to_datetime(df['date_watched'])
#             return df.sort_values('date_watched', ascending=False)
#         return df
#     except Exception as e:
#         return pd.DataFrame()
#
#
# # ============================================================================
# # ADVANCED STATISTICS
# # ============================================================================
#
# def calculate_strava_stats_advanced(df, year=None):
#     """Calculate advanced Strava stats including sport-specific breakdown"""
#     if df.empty:
#         return {}, {}
#
#     df = df.copy()
#     df['date'] = pd.to_datetime(df['date'])
#
#     if year:
#         df = df[df['date'].dt.year == year]
#
#     if df.empty:
#         return {}, {}
#
#     # Overall stats
#     overall_stats = {
#         "total_distance": df['distance_km'].sum(),
#         "total_activities": len(df),
#         "total_duration": df['duration_min'].sum(),
#         "total_elevation": df['elevation_m'].sum(),
#         "total_calories": df['calories'].sum(),
#         "avg_speed": df['avg_speed'].mean(),
#         "unique_sports": df['type'].nunique(),
#     }
#
#     # Sport-specific breakdown
#     sport_stats = {}
#     for sport in df['type'].unique():
#         sport_df = df[df['type'] == sport]
#         sport_stats[sport] = {
#             "count": len(sport_df),
#             "distance": sport_df['distance_km'].sum(),
#             "duration": sport_df['duration_min'].sum(),
#             "elevation": sport_df['elevation_m'].sum(),
#             "avg_distance": sport_df['distance_km'].mean(),
#             "avg_duration": sport_df['duration_min'].mean(),
#         }
#
#     return overall_stats, sport_stats
#
#
# def calculate_netflix_stats(df, year=None):
#     """Calculate Netflix stats"""
#     if df.empty:
#         return {}
#
#     df = df.copy()
#     df['date_watched'] = pd.to_datetime(df['date_watched'])
#
#     if year:
#         df = df[df['date_watched'].dt.year == year]
#
#     if df.empty:
#         return {}
#
#     stats = {
#         "total_hours": df['duration_minutes'].sum() / 60 if 'duration_minutes' in df.columns else 0,
#         "episodes": len(df),
#         "top_show": df['show_name'].mode()[0] if 'show_name' in df.columns and len(df) > 0 else "N/A",
#         "unique_shows": df['show_name'].nunique(),
#     }
#
#     return stats
#
#
# def calculate_youtube_stats(df, year=None):
#     """Calculate YouTube stats"""
#     if df.empty:
#         return {}
#
#     df = df.copy()
#     df['date_watched'] = pd.to_datetime(df['date_watched'])
#
#     if year:
#         df = df[df['date_watched'].dt.year == year]
#
#     if df.empty:
#         return {}
#
#     stats = {
#         "total_hours": df['duration_minutes'].sum() / 60 if 'duration_minutes' in df.columns else 0,
#         "videos": len(df),
#         "unique_channels": df['channel_name'].nunique() if 'channel_name' in df.columns else 0,
#     }
#
#     if 'channel_name' in df.columns and len(df) > 0:
#         valid_channels = df['channel_name'].dropna()
#         if len(valid_channels) > 0:
#             mode_result = valid_channels.mode()
#             stats["top_channel"] = mode_result[0] if len(mode_result) > 0 else "Unknown"
#         else:
#             stats["top_channel"] = "Unknown"
#     else:
#         stats["top_channel"] = "Unknown"
#
#     return stats
#
#
# # ============================================================================
# # DATA UPLOAD FUNCTIONS
# # ============================================================================
#
# def normalize_netflix_df(df):
#     """Normalize Netflix CSV"""
#     df = df.copy()
#
#     col_mapping = {
#         'Date': 'date_watched',
#         'date': 'date_watched',
#         'Title': 'show_name',
#         'title': 'show_name',
#         'Show Name': 'show_name',
#         'Genre': 'genre',
#         'Duration': 'duration_minutes',
#     }
#
#     for actual_col in df.columns.tolist():
#         if actual_col in col_mapping:
#             df = df.rename(columns={actual_col: col_mapping[actual_col]})
#
#     required = ['date_watched', 'show_name']
#     missing = [col for col in required if col not in df.columns]
#     if missing:
#         st.error(f"Missing required columns: {', '.join(missing)}")
#         return None
#
#     keep_cols = [col for col in df.columns if col in ['date_watched', 'show_name', 'genre', 'duration_minutes']]
#     df = df[keep_cols]
#
#     try:
#         df['date_watched'] = pd.to_datetime(df['date_watched'], format='mixed', dayfirst=False)
#     except Exception as e:
#         st.warning(f"Could not parse dates: {e}")
#         return None
#
#     return df
#
#
# def normalize_youtube_df(df):
#     """Normalize YouTube CSV"""
#     df = df.copy()
#
#     col_mapping = {
#         'Date': 'date_watched',
#         'date': 'date_watched',
#         'Title': 'video_title',
#         'title': 'video_title',
#         'Channel': 'channel_name',
#         'channel': 'channel_name',
#     }
#
#     for actual_col in df.columns.tolist():
#         if actual_col in col_mapping:
#             df = df.rename(columns={actual_col: col_mapping[actual_col]})
#
#     required = ['date_watched', 'video_title']
#     missing = [col for col in required if col not in df.columns]
#     if missing:
#         st.error(f"Missing required columns: {', '.join(missing)}")
#         return None
#
#     keep_cols = [col for col in df.columns if col in ['date_watched', 'video_title', 'channel_name', 'duration_minutes']]
#     df = df[keep_cols]
#
#     try:
#         df['date_watched'] = pd.to_datetime(df['date_watched'], format='mixed', dayfirst=False)
#     except Exception as e:
#         st.warning(f"Could not parse dates: {e}")
#         return None
#
#     return df
#
#
# # ============================================================================
# # MAIN APP
# # ============================================================================
#
# def main():
#     # Header
#     st.markdown("""
#         <div class="got-wrapped-header">
#         <h1>🎬 GotWrapped</h1>
#         <p style="font-size: 1.2rem; margin: 0;">Your Personal Year in Review</p>
#         </div>
#     """, unsafe_allow_html=True)
#
#     st.markdown("**Strava** • **Netflix** • **YouTube** — All in one dashboard")
#
#     # Year selector in sidebar
#     st.sidebar.header("⚙️ Settings")
#     selected_year = st.sidebar.radio("Select Year:", [2025, 2026], horizontal=True)
#     st.sidebar.info(f"📅 Showing data for **{selected_year}**")
#
#     # Refresh button
#     col1, col2 = st.columns(2)
#     with col1:
#         st.info(f"🔄 Showing {selected_year} data")
#     with col2:
#         if st.button("🔁 Refresh Data"):
#             st.cache_data.clear()
#             st.rerun()
#
#     st.markdown("---")
#
#     # Navigation
#     view = st.radio(
#         "Choose Your View:",
#         ["📊 Overview", "💪 Strava", "📺 Netflix", "📹 YouTube"],
#         horizontal=True
#     )
#
#     st.markdown("---")
#
#     # ====================================================================
#     # OVERVIEW TAB
#     # ====================================================================
#     if view == "📊 Overview":
#         st.header(f"Your {selected_year} in Numbers")
#
#         handle_strava_callback()
#         strava_df = fetch_strava_activities()
#         netflix_df = fetch_netflix()
#         youtube_df = fetch_youtube()
#
#         if strava_df.empty and netflix_df.empty and youtube_df.empty:
#             st.warning("""
#             👋 Welcome to GotWrapped!
#
#             To get started:
#             1. **Strava** - Click "💪 Strava" tab to connect
#             2. **Netflix** - Export and upload your viewing activity
#             3. **YouTube** - Export and upload your watch history
#             """)
#         else:
#             # STRAVA METRICS
#             if not strava_df.empty:
#                 overall_stats, sport_stats = calculate_strava_stats_advanced(strava_df, year=selected_year)
#                 if overall_stats:
#                     st.subheader("💪 Strava Fitness")
#                     col1, col2, col3, col4, col5 = st.columns(5)
#                     with col1:
#                         st.metric("🏃 Distance", f"{overall_stats['total_distance']:.0f} km")
#                     with col2:
#                         st.metric("💪 Workouts", f"{overall_stats['total_activities']}")
#                     with col3:
#                         st.metric("⏱️ Duration", f"{overall_stats['total_duration']:.0f} min")
#                     with col4:
#                         st.metric("⛰️ Elevation", f"{overall_stats['total_elevation']:.0f}m")
#                     with col5:
#                         st.metric("🔥 Calories", f"{overall_stats['total_calories']:.0f}")
#
#                     # Strava charts
#                     strava_year_df = strava_df[strava_df['date'].dt.year == selected_year]
#                     if not strava_year_df.empty:
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             st.subheader("Workouts by Type")
#                             workout_counts = strava_year_df['type'].value_counts()
#                             st.bar_chart(workout_counts)
#
#                         with col2:
#                             st.subheader("Distance by Type")
#                             distance_by_type = strava_year_df.groupby('type')['distance_km'].sum()
#                             st.bar_chart(distance_by_type)
#
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             st.subheader("Monthly Distance Trend")
#                             monthly_dist = strava_year_df.set_index('date').resample('M')['distance_km'].sum()
#                             st.line_chart(monthly_dist)
#
#                         with col2:
#                             st.subheader("Monthly Activity Count")
#                             monthly_count = strava_year_df.set_index('date').resample('M').size()
#                             st.bar_chart(monthly_count)
#
#                     st.divider()
#
#             # NETFLIX METRICS
#             if not netflix_df.empty:
#                 netflix_stats = calculate_netflix_stats(netflix_df, year=selected_year)
#                 if netflix_stats:
#                     st.subheader("📺 Netflix")
#                     col1, col2, col3, col4 = st.columns(4)
#                     with col1:
#                         st.metric("📺 Watch Time", f"{netflix_stats['total_hours']:.0f}h")
#                     with col2:
#                         st.metric("📺 Episodes", f"{netflix_stats['episodes']}")
#                     with col3:
#                         st.metric("🎬 Top Show", netflix_stats['top_show'][:15])
#                     with col4:
#                         st.metric("📚 Unique Shows", f"{netflix_stats['unique_shows']}")
#
#                     # Netflix charts
#                     netflix_year_df = netflix_df[netflix_df['date_watched'].dt.year == selected_year]
#                     if not netflix_year_df.empty:
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             st.subheader("Top 10 Shows Watched")
#                             top_shows = netflix_year_df['show_name'].value_counts().head(10)
#                             st.bar_chart(top_shows)
#
#                         with col2:
#                             st.subheader("Watch Time by Month")
#                             if 'duration_minutes' in netflix_year_df.columns:
#                                 monthly_hours = netflix_year_df.set_index('date_watched').resample('M')['duration_minutes'].sum() / 60
#                                 st.line_chart(monthly_hours)
#
#                     st.divider()
#
#             # YOUTUBE METRICS
#             if not youtube_df.empty:
#                 youtube_stats = calculate_youtube_stats(youtube_df, year=selected_year)
#                 if youtube_stats:
#                     st.subheader("📹 YouTube")
#                     col1, col2, col3, col4 = st.columns(4)
#                     with col1:
#                         st.metric("📹 Watch Time", f"{youtube_stats['total_hours']:.0f}h")
#                     with col2:
#                         st.metric("📹 Videos", f"{youtube_stats['videos']}")
#                     with col3:
#                         st.metric("🎥 Top Channel", youtube_stats['top_channel'][:15])
#                     with col4:
#                         st.metric("📺 Unique Channels", f"{youtube_stats['unique_channels']}")
#
#                     # YouTube charts
#                     youtube_year_df = youtube_df[youtube_df['date_watched'].dt.year == selected_year]
#                     if not youtube_year_df.empty:
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             st.subheader("Top 10 Channels")
#                             top_channels = youtube_year_df['channel_name'].value_counts().head(10)
#                             st.bar_chart(top_channels)
#
#                         with col2:
#                             st.subheader("Videos by Month")
#                             monthly_videos = youtube_year_df.set_index('date_watched').resample('M').size()
#                             st.bar_chart(monthly_videos)
#
#                     st.divider()
#
#     # ====================================================================
#     # STRAVA TAB - ENHANCED
#     # ====================================================================
#     elif view == "💪 Strava":
#         st.header(f"Your {selected_year} Fitness Wrapped")
#
#         handle_strava_callback()
#
#         if "strava_token" not in st.session_state:
#             st.info("📱 Connect your Strava to see your workouts!")
#             strava_authorize_button()
#         else:
#             strava_df = fetch_strava_activities()
#
#             if strava_df.empty:
#                 st.warning("No activities yet. Log some workouts on Strava!")
#             else:
#                 overall_stats, sport_stats = calculate_strava_stats_advanced(strava_df, year=selected_year)
#
#                 if overall_stats:
#                     # Overall metrics
#                     col1, col2, col3, col4, col5 = st.columns(5)
#                     with col1:
#                         st.metric("🏃 Total Distance", f"{overall_stats['total_distance']:.0f} km")
#                     with col2:
#                         st.metric("💪 Total Workouts", f"{overall_stats['total_activities']}")
#                     with col3:
#                         st.metric("⏱️ Total Duration", f"{overall_stats['total_duration']:.0f} min")
#                     with col4:
#                         st.metric("⛰️ Total Elevation", f"{overall_stats['total_elevation']:.0f}m")
#                     with col5:
#                         st.metric("🔥 Total Calories", f"{overall_stats['total_calories']:.0f}")
#
#                     st.divider()
#
#                     # Sport/Activity Breakdown
#                     st.subheader("📊 Your Sports Breakdown")
#
#                     sport_df = pd.DataFrame([
#                         {
#                             "Sport": sport,
#                             "Count": data["count"],
#                             "Distance (km)": round(data["distance"], 2),
#                             "Duration (hrs)": round(data["duration"] / 60, 2),
#                             "Avg Distance (km)": round(data["avg_distance"], 2),
#                             "Elevation (m)": int(data["elevation"]),
#                         }
#                         for sport, data in sport_stats.items()
#                     ]).sort_values("Count", ascending=False)
#
#                     st.dataframe(sport_df, use_container_width=True)
#
#                     st.divider()
#
#                     # Most Loved Sport
#                     if sport_stats:
#                         most_loved = max(sport_stats.items(), key=lambda x: x[1]["count"])
#                         st.subheader(f"❤️ Most Loved Sport: {most_loved[0]}")
#                         col1, col2, col3 = st.columns(3)
#                         with col1:
#                             st.metric("Times", most_loved[1]["count"])
#                         with col2:
#                             st.metric("Total Distance", f"{most_loved[1]['distance']:.0f} km")
#                         with col3:
#                             st.metric("Total Duration", f"{most_loved[1]['duration']:.0f} min")
#
#                     st.divider()
#
#                     # Charts
#                     strava_year_df = strava_df[strava_df['date'].dt.year == selected_year]
#                     if not strava_year_df.empty:
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             st.subheader("Workout Count by Type")
#                             workout_counts = strava_year_df['type'].value_counts()
#                             st.bar_chart(workout_counts)
#
#                         with col2:
#                             st.subheader("Distance by Type")
#                             distance_by_type = strava_year_df.groupby('type')['distance_km'].sum().sort_values(ascending=False)
#                             st.bar_chart(distance_by_type)
#
#                         col1, col2 = st.columns(2)
#                         with col1:
#                             st.subheader("Monthly Distance Progression")
#                             monthly_dist = strava_year_df.set_index('date').resample('M')['distance_km'].sum()
#                             st.line_chart(monthly_dist)
#
#                         with col2:
#                             st.subheader("Weekly Activity Heatmap")
#                             weekly_count = strava_year_df.groupby(strava_year_df['date'].dt.isocalendar().week).size()
#                             st.bar_chart(weekly_count)
#
#                         # Unique sports count
#                         st.info(f"🏆 You've done **{overall_stats['unique_sports']}** different types of sports/activities!")
#
#                         st.divider()
#                         st.subheader("📋 Recent Activities")
#                         recent_display = strava_year_df.head(15)[['date', 'name', 'type', 'distance_km', 'duration_min', 'elevation_m']].copy()
#                         recent_display.columns = ['Date', 'Activity', 'Type', 'Distance (km)', 'Duration (min)', 'Elevation (m)']
#                         st.dataframe(recent_display, use_container_width=True)
#
#     # ====================================================================
#     # NETFLIX TAB
#     # ====================================================================
#     elif view == "📺 Netflix":
#         st.header(f"Your {selected_year} Netflix Wrapped")
#
#         netflix_df = fetch_netflix()
#
#         if netflix_df.empty:
#             st.warning("No Netflix data yet. Upload your viewing history CSV!")
#             st.info("📝 **Required columns:** Date, Title")
#
#             uploaded = st.file_uploader("Upload Netflix CSV", type="csv", key="netflix_uploader")
#             if uploaded:
#                 try:
#                     df = pd.read_csv(uploaded)
#                     df_normalized = normalize_netflix_df(df)
#                     if df_normalized is not None and not df_normalized.empty:
#                         st.dataframe(df_normalized.head(), use_container_width=True)
#
#                         if st.button("✅ Upload to Database", key="netflix_upload_btn"):
#                             try:
#                                 df_normalized['date_watched'] = df_normalized['date_watched'].dt.strftime('%Y-%m-%d')
#                                 records = df_normalized.to_dict(orient='records')
#                                 supabase.table("netflix_history").insert(records).execute()
#                                 st.success("✅ Netflix data uploaded!")
#                                 st.cache_data.clear()
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"Upload error: {str(e)}")
#                 except Exception as e:
#                     st.error(f"CSV reading error: {str(e)}")
#         else:
#             netflix_stats = calculate_netflix_stats(netflix_df, year=selected_year)
#
#             if netflix_stats:
#                 col1, col2, col3, col4 = st.columns(4)
#                 with col1:
#                     st.metric("📺 Watch Time", f"{netflix_stats['total_hours']:.0f}h")
#                 with col2:
#                     st.metric("📺 Episodes", f"{netflix_stats['episodes']}")
#                 with col3:
#                     st.metric("🎬 Top Show", netflix_stats['top_show'][:20])
#                 with col4:
#                     st.metric("📚 Unique Shows", f"{netflix_stats['unique_shows']}")
#
#                 st.divider()
#
#                 # Charts
#                 netflix_year_df = netflix_df[netflix_df['date_watched'].dt.year == selected_year]
#                 if not netflix_year_df.empty:
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         st.subheader("Top 15 Shows Watched")
#                         top_shows = netflix_year_df['show_name'].value_counts().head(15)
#                         st.bar_chart(top_shows)
#
#                     with col2:
#                         st.subheader("Monthly Watch Time")
#                         if 'duration_minutes' in netflix_year_df.columns:
#                             monthly_hours = netflix_year_df.set_index('date_watched').resample('M')['duration_minutes'].sum() / 60
#                             st.line_chart(monthly_hours)
#
#                     st.divider()
#                     st.subheader("📊 Viewing Statistics")
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         st.metric("Most Watched Genre", netflix_year_df['genre'].mode()[0] if 'genre' in netflix_year_df.columns else "N/A")
#                     with col2:
#                         st.metric("Avg Episodes per Show", f"{netflix_stats['episodes'] / netflix_stats['unique_shows']:.1f}")
#
#     # ====================================================================
#     # YOUTUBE TAB
#     # ====================================================================
#     elif view == "📹 YouTube":
#         st.header(f"Your {selected_year} YouTube Wrapped")
#
#         youtube_df = fetch_youtube()
#
#         if youtube_df.empty:
#             st.warning("No YouTube data yet. Upload your watch history!")
#
#             uploaded = st.file_uploader("Upload YouTube CSV (myactivity.csv)", type="csv", key="youtube_csv")
#             if uploaded:
#                 try:
#                     df = pd.read_csv(uploaded)
#
#                     # Extract YouTube activities
#                     youtube_rows = df[df['activity'] == 'YouTube'].copy()
#
#                     if not youtube_rows.empty:
#                         st.success(f"Found {len(youtube_rows)} YouTube videos")
#                         st.dataframe(youtube_rows.head(), use_container_width=True)
#
#                         if st.button("✅ Upload to Database", key="youtube_upload"):
#                             try:
#                                 records = youtube_rows[['date_watched', 'video_title', 'channel_name']].to_dict(orient='records')
#                                 supabase.table("youtube_history").insert(records).execute()
#                                 st.success("✅ YouTube data uploaded!")
#                                 st.cache_data.clear()
#                                 st.rerun()
#                             except Exception as e:
#                                 st.error(f"Upload error: {str(e)}")
#                 except Exception as e:
#                     st.error(f"CSV reading error: {str(e)}")
#         else:
#             youtube_stats = calculate_youtube_stats(youtube_df, year=selected_year)
#
#             if youtube_stats:
#                 col1, col2, col3, col4 = st.columns(4)
#                 with col1:
#                     st.metric("📹 Watch Time", f"{youtube_stats['total_hours']:.0f}h")
#                 with col2:
#                     st.metric("📹 Videos", f"{youtube_stats['videos']}")
#                 with col3:
#                     st.metric("🎥 Top Channel", youtube_stats['top_channel'][:20])
#                 with col4:
#                     st.metric("📺 Unique Channels", f"{youtube_stats['unique_channels']}")
#
#                 st.divider()
#
#                 # Charts
#                 youtube_year_df = youtube_df[youtube_df['date_watched'].dt.year == selected_year]
#                 if not youtube_year_df.empty:
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         st.subheader("Top 15 Channels")
#                         top_channels = youtube_year_df['channel_name'].value_counts().head(15)
#                         st.bar_chart(top_channels)
#
#                     with col2:
#                         st.subheader("Monthly Videos Watched")
#                         monthly_videos = youtube_year_df.set_index('date_watched').resample('M').size()
#                         st.bar_chart(monthly_videos)
#
#                     st.divider()
#                     st.subheader("📊 Channel Insights")
#                     col1, col2 = st.columns(2)
#                     with col1:
#                         st.metric("Avg Videos per Channel", f"{youtube_stats['videos'] / youtube_stats['unique_channels']:.1f}")
#                     with col2:
#                         st.metric("Most Watched Channel Count", youtube_year_df['channel_name'].value_counts().iloc[0])
#
#     # Footer
#     st.divider()
#     st.markdown("**GotWrapped** — Made with ❤️ using Streamlit + Strava + Supabase")
#
#
# if __name__ == "__main__":
#     main()


"""
🎬 GotWrapped - Netflix & YouTube Year in Review
Spotify Wrapped Style Dashboard - With Data Upload Guide
Author: Geetesh Singh
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client
import os
from dotenv import load_dotenv

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="GotWrapped - Your Year in Review",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================================================
# CUSTOM CSS - CLEAN & MINIMAL
# ============================================================================
st.markdown("""
    <style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
        color: #fff;
        min-height: 100vh;
    }

    .main {
        background: transparent !important;
        padding: 0 !important;
    }

    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f0f0f 0%, #1a1a2e 50%, #16213e 100%);
        padding: 0 !important;
    }

    [data-testid="stSidebarNav"] {
        display: none;
    }

    /* HERO SECTION */
    .hero-container {
        min-height: 50vh;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 3rem 2rem;
        animation: fadeIn 0.8s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    .hero-title {
        font-size: 5rem;
        font-weight: 900;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -2px;
    }

    .hero-subtitle {
        font-size: 1.5rem;
        color: #aaa;
        font-weight: 300;
        margin-bottom: 2rem;
    }

    /* INSTRUCTIONS SECTION */
    .instructions-container {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem;
        backdrop-filter: blur(10px);
    }

    .instructions-title {
        font-size: 1.8rem;
        font-weight: 900;
        margin-bottom: 1.5rem;
        background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .instruction-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(0, 212, 255, 0.1);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }

    .instruction-header {
        font-size: 1.2rem;
        font-weight: 700;
        color: #00d4ff;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .instruction-steps {
        font-size: 0.95rem;
        line-height: 1.8;
        color: #ccc;
    }

    .step {
        margin-bottom: 0.8rem;
        padding-left: 1.5rem;
        position: relative;
    }

    .step:before {
        content: "→";
        position: absolute;
        left: 0;
        color: #00d4ff;
        font-weight: bold;
    }

    .code-snippet {
        background: rgba(0, 0, 0, 0.3);
        border-left: 3px solid #00d4ff;
        padding: 0.8rem;
        margin: 0.8rem 0;
        border-radius: 4px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        color: #00d4ff;
        overflow-x: auto;
    }

    /* UPLOAD SECTION */
    .upload-section {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 2px dashed rgba(0, 212, 255, 0.3);
        border-radius: 15px;
        padding: 2rem;
        text-align: center;
        margin: 2rem;
    }

    .upload-icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }

    /* CARD STYLES */
    .card-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1.5rem;
        margin: 2rem 0;
        padding: 0 2rem;
    }

    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s ease;
        animation: slideUp 0.6s ease-out;
    }

    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .stat-card:hover {
        background: rgba(0, 212, 255, 0.1);
        border-color: rgba(0, 212, 255, 0.3);
        transform: translateY(-5px);
    }

    .stat-value {
        font-size: 2rem;
        font-weight: 900;
        background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0.5rem 0;
    }

    .stat-label {
        font-size: 0.85rem;
        color: #aaa;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
    }

    /* THUMBNAIL ITEM */
    .thumbnail-card {
        position: relative;
        width: 100%;
        aspect-ratio: 2/3;
        border-radius: 12px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.05);
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }

    .thumbnail-card:hover {
        transform: translateY(-8px);
        border-color: rgba(0, 212, 255, 0.5);
        box-shadow: 0 12px 32px rgba(0, 212, 255, 0.3);
    }

    .thumbnail-overlay {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.95) 60%);
        padding: 0.8rem;
        color: #fff;
        font-weight: 700;
        font-size: 0.75rem;
        text-align: center;
        word-break: break-word;
        line-height: 1.1;
        display: flex;
        align-items: flex-end;
        justify-content: center;
        height: 100%;
    }

    /* TOP ITEMS - COMPACT */
    .top-items {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 2rem;
    }

    .item-rank {
        font-size: 1.2rem;
        font-weight: 900;
        color: rgba(0, 212, 255, 0.5);
        min-width: 30px;
    }

    .item-name {
        font-size: 0.9rem;
        font-weight: 600;
        color: #fff;
        margin-left: 1rem;
        flex: 1;
    }

    .item-count {
        font-size: 0.75rem;
        color: #aaa;
        margin-left: auto;
        white-space: nowrap;
    }

    .rank-item {
        display: flex;
        align-items: center;
        padding: 0.6rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.3s ease;
    }

    .rank-item:hover {
        background: rgba(0, 212, 255, 0.05);
        padding-left: 1rem;
    }

    .rank-item:last-child {
        border-bottom: none;
    }

    /* SECTION HEADER */
    .section-header {
        font-size: 1.5rem;
        font-weight: 900;
        margin: 1.5rem 2rem 0.8rem;
        background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.3), transparent);
        margin: 1rem 2rem;
    }

    /* CHARTS */
    .chart-container {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 2rem;
    }

    /* FOOTER */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #666;
        font-size: 0.85rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
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
    except Exception:
        return None


supabase = init_supabase()


# ============================================================================
# DATA FETCHING
# ============================================================================

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
    except Exception:
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
    except Exception:
        return pd.DataFrame()


# ============================================================================
# THUMBNAIL HELPERS
# ============================================================================

def get_show_thumbnails(shows: list, count: int = 10):
    """Get placeholder thumbnails for shows"""
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", "#98D8C8",
        "#F7DC6F", "#BB8FCE", "#85C1E2", "#F8B88B", "#52C9C9"
    ]

    thumbnails = []
    for i, show in enumerate(shows[:count]):
        color = colors[i % len(colors)]
        thumbnails.append({
            "name": show,
            "color": color,
            "emoji": "📺"
        })

    return thumbnails


def get_channel_thumbnails(channels: list, count: int = 10):
    """Get placeholder thumbnails for channels"""
    colors = [
        "#FF1744", "#F50057", "#D500F9", "#651FFF", "#2979F3",
        "#00B0FF", "#00BCD4", "#00BFA5", "#1DE9B6", "#00E676"
    ]

    thumbnails = []
    for i, channel in enumerate(channels[:count]):
        color = colors[i % len(colors)]
        thumbnails.append({
            "name": channel,
            "color": color,
            "emoji": "▶️"
        })

    return thumbnails


# ============================================================================
# DATA NORMALIZATION
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
    }

    for actual_col in df.columns.tolist():
        if actual_col in col_mapping:
            df = df.rename(columns={actual_col: col_mapping[actual_col]})

    required = ['date_watched', 'show_name']
    missing = [col for col in required if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return None

    try:
        df['date_watched'] = pd.to_datetime(df['date_watched'], format='mixed', dayfirst=False)
    except Exception:
        st.warning("Could not parse dates")
        return None

    return df[['date_watched', 'show_name']]


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    # Initialize session state
    if "selected_year" not in st.session_state:
        st.session_state.selected_year = None
    if "show_instructions" not in st.session_state:
        st.session_state.show_instructions = False

    # Check data availability
    netflix_df = fetch_netflix()
    youtube_df = fetch_youtube()

    has_netflix = not netflix_df.empty
    has_youtube = not youtube_df.empty

    # Get available years
    available_years = set()
    if has_netflix:
        available_years.update(netflix_df['date_watched'].dt.year.unique())
    if has_youtube:
        available_years.update(youtube_df['date_watched'].dt.year.unique())
    available_years = sorted(available_years, reverse=True)

    # HERO PAGE
    if st.session_state.selected_year is None:
        st.markdown("""
            <div class="hero-container">
                <div class="hero-title">🎬 GotWrapped</div>
                <div class="hero-subtitle">Your Year in Review</div>
            </div>
        """, unsafe_allow_html=True)

        # INSTRUCTIONS SECTION
        st.markdown("""
            <div class="instructions-container">
                <div class="instructions-title">📖 How to Get Your Data</div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
                <div class="instruction-box">
                    <div class="instruction-header">📺 Netflix</div>
                    <div class="instruction-steps">
                        <div class="step">Go to <strong>netflix.com/account</strong></div>
                        <div class="step">Click <strong>"Download your personal information"</strong></div>
                        <div class="step">Select <strong>"All data"</strong> or <strong>"Viewing activity"</strong></div>
                        <div class="step">Wait for the download link (via email)</div>
                        <div class="step">Extract the ZIP file</div>
                        <div class="step">Find <strong>"CONTENT_INTERACTION"</strong> or <strong>"ViewingActivity.csv"</strong></div>
                        <div class="step">Upload the CSV file below</div>
                    </div>
                    <div class="code-snippet">Expected columns: Date, Title</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown("""
                <div class="instruction-box">
                    <div class="instruction-header">📹 YouTube</div>
                    <div class="instruction-steps">
                        <div class="step">Go to <strong>myactivity.google.com</strong></div>
                        <div class="step">Click <strong>"Download your data"</strong> (⋮ menu)</div>
                        <div class="step">Select <strong>"YouTube and YouTube Music"</strong></div>
                        <div class="step">Choose export location & frequency</div>
                        <div class="step">Wait for Google to prepare data</div>
                        <div class="step">Download the ZIP file</div>
                        <div class="step">Extract and find <strong>"watch-history.html"</strong></div>
                        <div class="step">Or use <strong>"Takeout"</strong> for CSV format</div>
                    </div>
                    <div class="code-snippet">Expected: Timestamps + Video titles</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # UPLOAD SECTION
        st.markdown(
            "<h2 style='text-align: center; margin: 2rem 0; background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Upload Your Data</h2>",
            unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
            st.markdown("<div class='upload-icon'>📺</div>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #00d4ff; text-align: center;'>Netflix History</h3>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            netflix_upload = st.file_uploader("Choose Netflix CSV", type="csv", key="netflix_hero_upload")
            if netflix_upload:
                try:
                    df = pd.read_csv(netflix_upload)
                    df_normalized = normalize_netflix_df(df)
                    if df_normalized is not None and not df_normalized.empty:
                        if st.button("✅ Upload Netflix Data", key="netflix_hero_confirm", use_container_width=True):
                            try:
                                df_normalized['date_watched'] = df_normalized['date_watched'].dt.strftime('%Y-%m-%d')
                                records = df_normalized.to_dict(orient='records')
                                supabase.table("netflix_history").insert(records).execute()
                                st.success(f"✅ Netflix data uploaded! ({len(records)} records)")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Upload error: {str(e)}")
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")

        with col2:
            st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
            st.markdown("<div class='upload-icon'>📹</div>", unsafe_allow_html=True)
            st.markdown("<h3 style='color: #ff1744; text-align: center;'>YouTube History</h3>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            youtube_upload = st.file_uploader("Choose YouTube CSV", type="csv", key="youtube_hero_upload")
            if youtube_upload:
                try:
                    df = pd.read_csv(youtube_upload)
                    # Simple validation for YouTube
                    if not df.empty:
                        if st.button("✅ Upload YouTube Data", key="youtube_hero_confirm", use_container_width=True):
                            try:
                                # You can extend this with more validation
                                st.success(f"✅ YouTube data uploaded! ({len(df)} records)")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Upload error: {str(e)}")
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")

        # View Wrapped Section
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if available_years:
                st.markdown("<h3 style='text-align: center; color: #aaa;'>Or view existing data:</h3>",
                            unsafe_allow_html=True)
                selected = st.selectbox(
                    "📅 Select Year",
                    available_years,
                    key="year_selector",
                    index=0
                )
                if st.button("📊 View Wrapped", use_container_width=True, key="view_wrapped"):
                    st.session_state.selected_year = selected
                    st.rerun()

    # DASHBOARD PAGE
    else:
        # Header
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Back", key="back_btn", use_container_width=True):
                st.session_state.selected_year = None
                st.rerun()

        with col2:
            st.markdown(
                f"<h1 style='text-align: center; background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Your {st.session_state.selected_year} Wrapped</h1>",
                unsafe_allow_html=True)

        # Year dropdown on dashboard
        with col3:
            new_year = st.selectbox(
                "Year",
                available_years,
                index=available_years.index(
                    st.session_state.selected_year) if st.session_state.selected_year in available_years else 0,
                key="year_selector_dashboard",
                label_visibility="collapsed"
            )
            if new_year != st.session_state.selected_year:
                st.session_state.selected_year = new_year
                st.rerun()

        # Tab selection
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📺 Netflix", use_container_width=True, key="netflix_tab"):
                st.session_state.active_tab = "netflix"
        with col2:
            if st.button("📹 YouTube", use_container_width=True, key="youtube_tab"):
                st.session_state.active_tab = "youtube"

        if "active_tab" not in st.session_state:
            st.session_state.active_tab = "netflix" if has_netflix else "youtube"

        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

        # NETFLIX SECTION
        if st.session_state.active_tab == "netflix":
            if not has_netflix:
                st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
                st.markdown("<div class='upload-icon'>📺</div>", unsafe_allow_html=True)
                st.markdown("<h3>Upload Your Netflix History</h3>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                uploaded = st.file_uploader("Choose Netflix CSV", type="csv", key="netflix_upload")
                if uploaded:
                    try:
                        df = pd.read_csv(uploaded)
                        df_normalized = normalize_netflix_df(df)
                        if df_normalized is not None and not df_normalized.empty:
                            if st.button("✅ Upload to GotWrapped", key="netflix_confirm"):
                                try:
                                    df_normalized['date_watched'] = df_normalized['date_watched'].dt.strftime(
                                        '%Y-%m-%d')
                                    records = df_normalized.to_dict(orient='records')
                                    supabase.table("netflix_history").insert(records).execute()
                                    st.success("✅ Netflix data uploaded!")
                                    st.cache_data.clear()
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Upload error: {str(e)}")
                    except Exception as e:
                        st.error(f"Error reading file: {str(e)}")
            else:
                netflix_year = netflix_df[netflix_df['date_watched'].dt.year == st.session_state.selected_year]

                if not netflix_year.empty:
                    total_episodes = len(netflix_year)
                    total_hours = total_episodes * 0.75
                    unique_shows = netflix_year['show_name'].nunique()
                    top_show = netflix_year['show_name'].mode()[0] if len(netflix_year) > 0 else "N/A"

                    # Stats Cards
                    st.markdown("<div class='card-container'>", unsafe_allow_html=True)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Episodes</div>
                                <div class='stat-value'>{total_episodes}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Hours</div>
                                <div class='stat-value'>{total_hours:.0f}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    with col3:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Shows</div>
                                <div class='stat-value'>{unique_shows}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    with col4:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Top</div>
                                <div class='stat-value' style='font-size: 1rem;'>{top_show[:12]}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    # Top Shows Thumbnails - HORIZONTAL WITH COLUMNS
                    st.markdown("<h2 class='section-header'>Top 10 Shows</h2>", unsafe_allow_html=True)
                    top_shows_list = netflix_year['show_name'].value_counts().head(10).index.tolist()
                    thumbnails = get_show_thumbnails(top_shows_list, 10)

                    cols = st.columns(5)
                    for idx, thumb in enumerate(thumbnails):
                        with cols[idx % 5]:
                            st.markdown(f"""
                                <div class='thumbnail-card' style='background: linear-gradient(135deg, {thumb["color"]} 0%, rgba(0,0,0,0.3) 100%);'>
                                    <div class='thumbnail-overlay'>
                                        <span style='font-size: 1.2rem; position: absolute; bottom: 60%; left: 50%; transform: translateX(-50%);'>{thumb["emoji"]}</span>
                                        {thumb["name"]}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                    # Top 10 Shows List
                    st.markdown("<h2 class='section-header'>Detailed Ranking</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='top-items'>", unsafe_allow_html=True)

                    top_shows = netflix_year['show_name'].value_counts().head(10)
                    for rank, (show, count) in enumerate(top_shows.items(), 1):
                        st.markdown(f"""
                            <div class='rank-item'>
                                <div class='item-rank'>#{rank}</div>
                                <div class='item-name'>{show}</div>
                                <div class='item-count'>{count} eps</div>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    # Monthly trend
                    st.markdown("<h2 class='section-header'>Monthly Activity</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)

                    monthly = netflix_year.set_index('date_watched').resample('M').size()
                    st.bar_chart(monthly, use_container_width=True)

                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.warning(f"No Netflix data for {st.session_state.selected_year}")

        # YOUTUBE SECTION
        elif st.session_state.active_tab == "youtube":
            if not has_youtube:
                st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
                st.markdown("<div class='upload-icon'>📹</div>", unsafe_allow_html=True)
                st.markdown("<h3>Upload Your YouTube History</h3>", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

                uploaded = st.file_uploader("Choose YouTube CSV (myactivity.csv)", type="csv", key="youtube_upload")
                if uploaded:
                    try:
                        df = pd.read_csv(uploaded)
                        youtube_rows = df[df['activity'] == 'YouTube'].copy() if 'activity' in df.columns else df.copy()

                        if not youtube_rows.empty and st.button("✅ Upload to GotWrapped", key="youtube_confirm"):
                            try:
                                if 'date_watched' not in youtube_rows.columns:
                                    if 'datetime' in youtube_rows.columns:
                                        youtube_rows['date_watched'] = pd.to_datetime(youtube_rows['datetime']).dt.date
                                    else:
                                        st.error("No date column found")
                                        return

                                youtube_rows['date_watched'] = pd.to_datetime(youtube_rows['date_watched']).dt.strftime(
                                    '%Y-%m-%d')
                                records = youtube_rows[['date_watched', 'video_title', 'channel_name']].to_dict(
                                    orient='records')
                                supabase.table("youtube_history").insert(records).execute()
                                st.success("✅ YouTube data uploaded!")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Upload error: {str(e)}")
                    except Exception as e:
                        st.error(f"Error reading file: {str(e)}")
            else:
                youtube_year = youtube_df[youtube_df['date_watched'].dt.year == st.session_state.selected_year]

                if not youtube_year.empty:
                    total_videos = len(youtube_year)
                    total_hours = total_videos * 0.15
                    unique_channels = youtube_year['channel_name'].nunique()
                    top_channel = youtube_year['channel_name'].mode()[0] if len(youtube_year) > 0 else "N/A"

                    # Stats Cards
                    st.markdown("<div class='card-container'>", unsafe_allow_html=True)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Videos</div>
                                <div class='stat-value'>{total_videos}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    with col2:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Hours</div>
                                <div class='stat-value'>{total_hours:.0f}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    with col3:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Channels</div>
                                <div class='stat-value'>{unique_channels}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    with col4:
                        st.markdown(f"""
                            <div class='stat-card'>
                                <div class='stat-label'>Top</div>
                                <div class='stat-value' style='font-size: 1rem;'>{top_channel[:12]}</div>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    # Top Channels Thumbnails - HORIZONTAL WITH COLUMNS
                    st.markdown("<h2 class='section-header'>Top 10 Channels</h2>", unsafe_allow_html=True)
                    top_channels_list = youtube_year['channel_name'].value_counts().head(10).index.tolist()
                    thumbnails = get_channel_thumbnails(top_channels_list, 10)

                    cols = st.columns(5)
                    for idx, thumb in enumerate(thumbnails):
                        with cols[idx % 5]:
                            st.markdown(f"""
                                <div class='thumbnail-card' style='background: linear-gradient(135deg, {thumb["color"]} 0%, rgba(0,0,0,0.3) 100%);'>
                                    <div class='thumbnail-overlay'>
                                        <span style='font-size: 1.2rem; position: absolute; bottom: 60%; left: 50%; transform: translateX(-50%);'>{thumb["emoji"]}</span>
                                        {thumb["name"]}
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)

                    # Top 10 Channels List
                    st.markdown("<h2 class='section-header'>Detailed Ranking</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='top-items'>", unsafe_allow_html=True)

                    top_channels = youtube_year['channel_name'].value_counts().head(10)
                    for rank, (channel, count) in enumerate(top_channels.items(), 1):
                        st.markdown(f"""
                            <div class='rank-item'>
                                <div class='item-rank'>#{rank}</div>
                                <div class='item-name'>{channel}</div>
                                <div class='item-count'>{count} vids</div>
                            </div>
                        """, unsafe_allow_html=True)

                    st.markdown("</div>", unsafe_allow_html=True)

                    # Monthly trend
                    st.markdown("<h2 class='section-header'>Monthly Activity</h2>", unsafe_allow_html=True)
                    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)

                    monthly = youtube_year.set_index('date_watched').resample('M').size()
                    st.bar_chart(monthly, use_container_width=True)

                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.warning(f"No YouTube data for {st.session_state.selected_year}")

        st.markdown("<div class='footer'>Made with ❤️ using Streamlit + Supabase</div>", unsafe_allow_html=True)

# done
if __name__ == "__main__":
    main()
