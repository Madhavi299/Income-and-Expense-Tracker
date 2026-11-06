import streamlit as st


def render_theme_control():
    st.session_state.setdefault("dark_mode", False)
    st.sidebar.toggle(
        "Dark appearance",
        key="dark_mode",
        help="Switch between light and dark colors.",
    )

    palette = {
        True: {
            "background": "#0b1020",
            "surface": "#111a2e",
            "foreground": "#e5eaf5",
            "muted": "#9aa7bf",
            "border": "#27334b",
            "accent": "#a5b4fc",
            "button_background": "#18243d",
            "input_background": "#0e1729",
        },
        False: {
            "background": "#f3f6fb",
            "surface": "#ffffff",
            "foreground": "#172033",
            "muted": "#667085",
            "border": "#e5eaf2",
            "accent": "#4338ca",
            "button_background": "#ffffff",
            "input_background": "#ffffff",
        },
    }[st.session_state.dark_mode]
    colors = {key: value for key, value in palette.items()}

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-color: {colors["background"]};
        }}
        [data-testid="stHeader"] {{
            background-color: {colors["background"]}ee;
        }}
        [data-testid="stSidebar"] {{
            background-color: {colors["surface"]};
            border-right: 1px solid {colors["border"]};
        }}
        [data-testid="stMarkdownContainer"] p,
        [data-testid="stMarkdownContainer"] li,
        [data-testid="stMetricLabel"],
        [data-testid="stMetricValue"],
        [data-testid="stMarkdownContainer"] strong,
        [data-testid="stMarkdownContainer"] b,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] label,
        label,
        h1, h2, h3, h4, h5, h6 {{
            color: {colors["foreground"]} !important;
        }}
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h1,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h2,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h3,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h4,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h5,
        [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"] h6 {{
            color: {colors["foreground"]} !important;
            -webkit-text-fill-color: {colors["foreground"]} !important;
        }}
        h1, h2, h3, h4, h5, h6 {{
            letter-spacing: -0.035em;
        }}
        [data-testid="stCaptionContainer"] {{
            color: {colors["muted"]} !important;
        }}
        div[data-testid="stMetric"] {{
            background: linear-gradient(145deg, {colors["surface"]}, {colors["background"]});
            border: 1px solid {colors["border"]};
            border-radius: 16px;
            padding: 18px 20px;
            box-shadow: 0 8px 24px #0000000a;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {colors["muted"]};
            font-weight: 600;
        }}
        [data-testid="stVerticalBlockBorderWrapper"] {{
            border-color: {colors["border"]};
            border-radius: 16px;
        }}
        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextArea"] textarea {{
            background-color: {colors["input_background"]};
            color: {colors["foreground"]} !important;
            -webkit-text-fill-color: {colors["foreground"]} !important;
            border-color: {colors["border"]};
            border-radius: 10px;
        }}
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stNumberInput"] input::placeholder,
        [data-testid="stTextArea"] textarea::placeholder {{
            color: {colors["muted"]} !important;
            -webkit-text-fill-color: {colors["muted"]} !important;
            opacity: 1;
        }}
        .stButton > button,
        .stDownloadButton > button,
        [data-testid="stBaseButton-secondary"] {{
            background-color: {colors["button_background"]};
            color: {colors["foreground"]};
            border-color: {colors["border"]};
            border-radius: 10px;
            transition: all 150ms ease;
        }}
        .stButton > button:hover,
        .stDownloadButton > button:hover {{
            border-color: {colors["accent"]};
            color: {colors["accent"]};
            transform: translateY(-1px);
        }}
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stBaseButton-primary"] {{
            background: linear-gradient(100deg, #4f46e5, #7c3aed);
            color: #ffffff;
            border: none;
            border-radius: 10px;
            font-weight: 650;
            transition: all 150ms ease;
        }}
        [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stBaseButton-primary"]:hover {{
            filter: brightness(1.08);
            transform: translateY(-1px);
        }}
        [data-baseweb="tab-list"] {{
            gap: 8px;
        }}
        [data-baseweb="tab"] {{
            border-radius: 10px 10px 0 0;
        }}
        [data-testid="stRadio"] label,
        [data-testid="stCheckbox"] label {{
            color: {colors["foreground"]} !important;
        }}
        [data-testid="stDataFrame"] {{
            border: 1px solid {colors["border"]};
            border-radius: 12px;
            overflow: hidden;
        }}
        [data-testid="stForm"] {{
            border-color: {colors["border"]};
            border-radius: 16px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
