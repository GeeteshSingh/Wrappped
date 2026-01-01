"""
🎬 GotWrapped - Netflix & YouTube Year in Review
Spotify Wrapped Style Dashboard - Horizontal Scroll Carousel
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
        min-height: 60vh;
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
    
    /* THUMBNAIL GRID - HORIZONTAL SCROLL CAROUSEL */
    .thumbnail-grid {
        display: flex;
        flex-direction: row;
        gap: 1.2rem;
        margin: 1.5rem 2rem;
        padding: 1rem 0;
        overflow-x: auto;
        overflow-y: hidden;
        scroll-behavior: smooth;
        -webkit-overflow-scrolling: touch;
    }
    
    /* Hide scrollbar but keep functionality */
    .thumbnail-grid::-webkit-scrollbar {
        height: 4px;
    }
    
    .thumbnail-grid::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
    }
    
    .thumbnail-grid::-webkit-scrollbar-thumb {
        background: rgba(0, 212, 255, 0.3);
        border-radius: 10px;
    }
    
    .thumbnail-grid::-webkit-scrollbar-thumb:hover {
        background: rgba(0, 212, 255, 0.5);
    }
    
    .thumbnail-item {
        position: relative;
        width: 160px;
        height: 240px;
        border-radius: 12px;
        overflow: hidden;
        cursor: pointer;
        transition: all 0.3s ease;
        border: 2px solid rgba(255, 255, 255, 0.1);
        background: rgba(255, 255, 255, 0.05);
        flex-shrink: 0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }
    
    .thumbnail-item:hover {
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
        padding: 1rem;
        color: #fff;
        font-weight: 700;
        font-size: 0.85rem;
        text-align: center;
        word-break: break-word;
        line-height: 1.2;
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
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if available_years:
                selected = st.selectbox(
                    "📅 Select Year",
                    available_years,
                    key="year_selector",
                    index=0
                )
                if st.button("📊 View Wrapped", use_container_width=True, key="view_wrapped"):
                    st.session_state.selected_year = selected
                    st.rerun()
            else:
                st.info("📤 Upload your Netflix & YouTube data to get started!")
    
    # DASHBOARD PAGE
    else:
        # Header
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("← Back", key="back_btn", use_container_width=True):
                st.session_state.selected_year = None
                st.rerun()
        
        with col2:
            st.markdown(f"<h1 style='text-align: center; background: linear-gradient(135deg, #00d4ff 0%, #0099ff 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;'>Your {st.session_state.selected_year} Wrapped</h1>", unsafe_allow_html=True)
        
        # Year dropdown on dashboard
        with col3:
            new_year = st.selectbox(
                "Year",
                available_years,
                index=available_years.index(st.session_state.selected_year) if st.session_state.selected_year in available_years else 0,
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
                                    df_normalized['date_watched'] = df_normalized['date_watched'].dt.strftime('%Y-%m-%d')
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
                    
                    # Top Shows Thumbnails
                    st.markdown("<h2 class='section-header'>Top 10 Shows</h2>", unsafe_allow_html=True)
                    top_shows_list = netflix_year['show_name'].value_counts().head(10).index.tolist()
                    thumbnails = get_show_thumbnails(top_shows_list, 10)
                    
                    st.markdown("<div class='thumbnail-grid'>", unsafe_allow_html=True)
                    for thumb in thumbnails:
                        st.markdown(f"""
                            <div class='thumbnail-item' style='background: linear-gradient(135deg, {thumb["color"]} 0%, rgba(0,0,0,0.3) 100%);' title='{thumb["name"]}'>
                                <div class='thumbnail-overlay'>
                                    <span style='font-size: 1.2rem; position: absolute; bottom: 60%; left: 50%; transform: translateX(-50%);'>{thumb["emoji"]}</span>
                                    {thumb["name"]}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
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
                                
                                youtube_rows['date_watched'] = pd.to_datetime(youtube_rows['date_watched']).dt.strftime('%Y-%m-%d')
                                records = youtube_rows[['date_watched', 'video_title', 'channel_name']].to_dict(orient='records')
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
                    
                    # Top Channels Thumbnails
                    st.markdown("<h2 class='section-header'>Top 10 Channels</h2>", unsafe_allow_html=True)
                    top_channels_list = youtube_year['channel_name'].value_counts().head(10).index.tolist()
                    thumbnails = get_channel_thumbnails(top_channels_list, 10)
                    
                    st.markdown("<div class='thumbnail-grid'>", unsafe_allow_html=True)
                    for thumb in thumbnails:
                        st.markdown(f"""
                            <div class='thumbnail-item' style='background: linear-gradient(135deg, {thumb["color"]} 0%, rgba(0,0,0,0.3) 100%);' title='{thumb["name"]}'>
                                <div class='thumbnail-overlay'>
                                    <span style='font-size: 1.2rem; position: absolute; bottom: 60%; left: 50%; transform: translateX(-50%);'>{thumb["emoji"]}</span>
                                    {thumb["name"]}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                    
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

if __name__ == "__main__":
    main()
