import streamlit as st


def apply_global_styles():
    st.markdown("""
    <style>
    /* ===== Import Google Font ===== */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

    /* ===== Global Font & Base ===== */
    html, body,
    h1, h2, h3, h4, h5, h6,
    p, a, li, td, th, label, input, textarea, select, button,
    .stMarkdown, .stText, .stCaption,
    .stMarkdown p, .stMarkdown span, .stMarkdown li,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span:not([class*="icon"]):not([data-testid]),
    [data-testid="stMetricValue"],
    [data-testid="stMetricLabel"],
    [data-testid="stForm"] {
        font-family: 'Noto Sans KR', sans-serif !important;
    }

    /* ===== Preserve icon fonts ===== */
    [data-testid="stSidebarCollapseButton"] span,
    [data-testid="stExpanderToggleIcon"],
    .material-symbols-rounded,
    [class*="icon"],
    [data-testid="stBaseButton-headerNoPadding"] span {
        font-family: 'Material Symbols Rounded', sans-serif !important;
    }

    /* ===== Remove all borders & outlines ===== */
    .stTextInput > div > div,
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stNumberInput > div > div,
    .stSlider > div,
    .stFileUploader > div,
    div[data-testid="stForm"],
    div[data-testid="stExpander"],
    .stCheckbox,
    section[data-testid="stSidebar"],
    div[data-testid="stMetric"],
    div[data-testid="stDataFrame"] {
        border: none !important;
        box-shadow: none !important;
        outline: none !important;
    }

    /* ===== Input fields uniform style ===== */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stNumberInput > div > div > input {
        border: none !important;
        border-bottom: 2px solid #e0e0e0 !important;
        border-radius: 0 !important;
        padding: 0.6rem 0.4rem !important;
        font-size: 0.95rem !important;
        background: transparent !important;
        transition: border-color 0.2s ease;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-bottom: 2px solid #ff6b6b !important;
        box-shadow: none !important;
    }

    /* ===== Buttons ===== */
    .stButton > button {
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.6rem !important;
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s ease !important;
        box-shadow: none !important;
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #ff6b6b, #ff8e53) !important;
        color: white !important;
    }

    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(255, 107, 107, 0.3) !important;
    }

    .stButton > button[kind="secondary"],
    .stButton > button:not([kind="primary"]) {
        background: #f5f5f5 !important;
        color: #333 !important;
    }

    .stButton > button[kind="secondary"]:hover,
    .stButton > button:not([kind="primary"]):hover {
        background: #ebebeb !important;
    }

    /* ===== Sidebar ===== */
    section[data-testid="stSidebar"] {
        background: #fafafa !important;
        border-right: none !important;
    }

    section[data-testid="stSidebar"] .stMarkdown {
        font-size: 0.88rem !important;
    }

    /* ===== Metric cards ===== */
    div[data-testid="stMetric"] {
        background: #fff !important;
        padding: 1rem 1.2rem !important;
        border-radius: 16px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
    }

    div[data-testid="stMetric"] label {
        font-size: 0.82rem !important;
        font-weight: 400 !important;
        color: #595959 !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
        font-weight: 700 !important;
        color: #333 !important;
    }

    /* ===== Expander ===== */
    div[data-testid="stExpander"] {
        background: #fff !important;
        border-radius: 16px !important;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important;
        margin-bottom: 0.8rem !important;
        overflow: hidden !important;
    }

    div[data-testid="stExpander"] summary {
        font-weight: 500 !important;
        font-size: 0.95rem !important;
        padding: 0.8rem 1rem !important;
    }

    /* ===== File Uploader ===== */
    div[data-testid="stFileUploader"] > div {
        border: 2px dashed #ddd !important;
        border-radius: 16px !important;
        background: #fafafa !important;
        padding: 2rem !important;
        transition: border-color 0.2s ease;
    }

    div[data-testid="stFileUploader"] > div:hover {
        border-color: #ff6b6b !important;
    }

    /* ===== Checkbox ===== */
    .stCheckbox label {
        font-size: 0.92rem !important;
        font-weight: 400 !important;
    }

    /* ===== Headers ===== */
    h1 {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #222 !important;
        margin-bottom: 0.2rem !important;
    }

    h2, .stHeader {
        font-size: 1.4rem !important;
        font-weight: 600 !important;
        color: #333 !important;
    }

    h3 {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
        color: #444 !important;
    }

    /* ===== Form ===== */
    div[data-testid="stForm"] {
        background: #fafafa !important;
        border-radius: 16px !important;
        padding: 1.2rem !important;
    }

    /* ===== Alert boxes ===== */
    .stAlert {
        border: none !important;
        border-radius: 12px !important;
        font-size: 0.9rem !important;
    }

    /* ===== Spinner ===== */
    .stSpinner > div {
        border-color: #ff6b6b transparent transparent transparent !important;
    }

    /* ===== Slider ===== */
    div[data-testid="stSlider"] [data-testid="stThumbValue"] {
        color: #ff6b6b !important;
    }

    /* ===== Divider ===== */
    hr {
        border: none !important;
        border-top: 1px solid #eee !important;
        margin: 1.5rem 0 !important;
    }

    /* ===== Image (fridge scan preview) ===== */
    .stImage {
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    /* ===== Mobile Responsive ===== */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 0.8rem 0.6rem !important;
        }

        h1 {
            font-size: 1.3rem !important;
            margin-bottom: 0.3rem !important;
        }

        h2, .stHeader {
            font-size: 1.1rem !important;
        }

        h3 {
            font-size: 0.95rem !important;
        }

        /* Larger touch targets for buttons (min 44px) */
        .stButton > button {
            width: 100% !important;
            min-height: 44px !important;
            padding: 0.75rem 1rem !important;
            font-size: 0.95rem !important;
        }

        /* Larger input fields for touch */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input {
            min-height: 44px !important;
            padding: 0.7rem 0.5rem !important;
            font-size: 1rem !important;
        }

        /* Checkbox touch targets */
        .stCheckbox label {
            min-height: 44px !important;
            display: flex !important;
            align-items: center !important;
            padding: 0.3rem 0 !important;
        }

        div[data-testid="stMetric"] {
            padding: 0.8rem 1rem !important;
        }

        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }

        div[data-testid="stForm"] {
            padding: 1rem !important;
        }

        div[data-testid="stExpander"] summary {
            min-height: 44px !important;
            font-size: 0.9rem !important;
            padding: 0.8rem 1rem !important;
        }

        /* File uploader smaller on mobile */
        div[data-testid="stFileUploader"] > div {
            padding: 1.2rem !important;
        }

        section[data-testid="stSidebar"] {
            min-width: 0 !important;
            width: 240px !important;
        }

        /* Stack columns vertically on mobile */
        div[data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.3rem !important;
        }

        div[data-testid="stHorizontalBlock"] > div {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Selectbox touch target */
        .stSelectbox > div > div {
            min-height: 44px !important;
        }

        /* Caption readability */
        .stCaption, [data-testid="stCaptionContainer"] {
            font-size: 0.8rem !important;
        }
    }

    /* ===== Tablet ===== */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main .block-container {
            padding: 1.5rem 1.2rem !important;
        }

        div[data-testid="stHorizontalBlock"] > div {
            min-width: 45% !important;
        }
    }

    /* ===== Desktop padding ===== */
    @media (min-width: 1025px) {
        .main .block-container {
            max-width: 960px !important;
            padding: 2rem 1.5rem !important;
        }
    }

    /* ===== Dark Mode ===== */
    @media (prefers-color-scheme: dark) {
        h1 { color: #f0f0f0 !important; }
        h2, .stHeader { color: #e0e0e0 !important; }
        h3 { color: #d0d0d0 !important; }

        div[data-testid="stMetric"] {
            background: #1e1e1e !important;
            box-shadow: 0 1px 4px rgba(255,255,255,0.06) !important;
        }
        div[data-testid="stMetric"] label { color: #aaa !important; }
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #f0f0f0 !important; }

        section[data-testid="stSidebar"] {
            background: #161616 !important;
        }

        div[data-testid="stExpander"] {
            background: #1e1e1e !important;
            box-shadow: 0 1px 4px rgba(255,255,255,0.04) !important;
        }

        div[data-testid="stForm"] {
            background: #1a1a1a !important;
        }

        .stTextInput > div > div > input,
        .stSelectbox > div > div > div,
        .stNumberInput > div > div > input {
            border-bottom: 2px solid #444 !important;
            color: #e0e0e0 !important;
        }

        .stButton > button[kind="secondary"],
        .stButton > button:not([kind="primary"]) {
            background: #2a2a2a !important;
            color: #e0e0e0 !important;
        }
        .stButton > button[kind="secondary"]:hover,
        .stButton > button:not([kind="primary"]):hover {
            background: #333 !important;
        }

        div[data-testid="stFileUploader"] > div {
            border-color: #444 !important;
            background: #1a1a1a !important;
        }

        hr {
            border-top: 1px solid #333 !important;
        }
    }

    /* Streamlit dark theme override */
    [data-theme="dark"] h1,
    .stApp[data-theme="dark"] h1 { color: #f0f0f0 !important; }
    [data-theme="dark"] h2,
    .stApp[data-theme="dark"] h2 { color: #e0e0e0 !important; }
    [data-theme="dark"] h3,
    .stApp[data-theme="dark"] h3 { color: #d0d0d0 !important; }

    [data-theme="dark"] div[data-testid="stMetric"] {
        background: #1e1e1e !important;
        box-shadow: 0 1px 4px rgba(255,255,255,0.06) !important;
    }
    [data-theme="dark"] div[data-testid="stMetric"] label { color: #aaa !important; }
    [data-theme="dark"] div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #f0f0f0 !important; }

    [data-theme="dark"] section[data-testid="stSidebar"] {
        background: #161616 !important;
    }

    [data-theme="dark"] div[data-testid="stExpander"] {
        background: #1e1e1e !important;
        box-shadow: 0 1px 4px rgba(255,255,255,0.04) !important;
    }

    [data-theme="dark"] div[data-testid="stForm"] {
        background: #1a1a1a !important;
    }

    [data-theme="dark"] .stTextInput > div > div > input,
    [data-theme="dark"] .stSelectbox > div > div > div,
    [data-theme="dark"] .stNumberInput > div > div > input {
        border-bottom: 2px solid #444 !important;
        color: #e0e0e0 !important;
    }

    [data-theme="dark"] .stButton > button[kind="secondary"],
    [data-theme="dark"] .stButton > button:not([kind="primary"]) {
        background: #2a2a2a !important;
        color: #e0e0e0 !important;
    }

    [data-theme="dark"] div[data-testid="stFileUploader"] > div {
        border-color: #444 !important;
        background: #1a1a1a !important;
    }

    [data-theme="dark"] hr {
        border-top: 1px solid #333 !important;
    }

    /* ===== Dark Mode: inline HTML overrides ===== */
    /* All inline div/span text inside markdown */
    @media (prefers-color-scheme: dark) {
        .stMarkdown div[style], .stMarkdown span[style] {
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#f0f0f0"],
        .stMarkdown span[style*="background:#f0f0f0"] {
            background: #333 !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#f5f5f5"],
        .stMarkdown span[style*="background:#f5f5f5"] {
            background: #333 !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#f8f9fa"] {
            background: #2a2a2a !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#f0fff4"] {
            background: #1a2a1d !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#fff5f5"] {
            background: #2a1a1a !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#f0f7ff"] {
            background: #1a1f2a !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#fff8f0"] {
            background: #2a241a !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#f5f0ff"] {
            background: #211a2a !important;
            color: #e0e0e0 !important;
        }
        .stMarkdown div[style*="background:#f0f0f0"] {
            background: #222 !important;
            color: #e0e0e0 !important;
        }
        /* Preserve semantic colors but brighten for dark bg */
        .stMarkdown div[style*="color:#e53e3e"] { color: #ff6b6b !important; }
        .stMarkdown div[style*="color:#e6a700"] { color: #ffd43b !important; }
        .stMarkdown div[style*="color:#38a169"] { color: #68d391 !important; }
        .stMarkdown span[style*="color:#e53e3e"] { color: #ff6b6b !important; }
    }

    [data-theme="dark"] .stMarkdown div[style],
    [data-theme="dark"] .stMarkdown span[style] {
        color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#f0f0f0"],
    [data-theme="dark"] .stMarkdown span[style*="background:#f0f0f0"] {
        background: #333 !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#f5f5f5"],
    [data-theme="dark"] .stMarkdown span[style*="background:#f5f5f5"] {
        background: #333 !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#f8f9fa"] {
        background: #2a2a2a !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#f0fff4"] {
        background: #1a2a1d !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#fff5f5"] {
        background: #2a1a1a !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#f0f7ff"] {
        background: #1a1f2a !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#fff8f0"] {
        background: #2a241a !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#f5f0ff"] {
        background: #211a2a !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="background:#f0f0f0"] {
        background: #222 !important; color: #e0e0e0 !important;
    }
    [data-theme="dark"] .stMarkdown div[style*="color:#e53e3e"] { color: #ff6b6b !important; }
    [data-theme="dark"] .stMarkdown div[style*="color:#e6a700"] { color: #ffd43b !important; }
    [data-theme="dark"] .stMarkdown div[style*="color:#38a169"] { color: #68d391 !important; }
    [data-theme="dark"] .stMarkdown span[style*="color:#e53e3e"] { color: #ff6b6b !important; }
    </style>
    """, unsafe_allow_html=True)
