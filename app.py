import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder
import os
import base64

st.set_page_config(page_title="CookIN", page_icon="🍳", layout="wide")

# --- INJECT CUSTOM SAN FRANCISCO FONT STYLING ---
st.markdown(
    """
    <style>
        /* Maintain the background color across BOTH welcome screen and active chat screen */
        html, body, [data-testid="stAppViewContainer"], .stApp, button, input, select, textarea {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
            background-color: #e9d2b4 !important;
        }
        
        /* Ensure the bottom bar area matches the background color across all views */
        [data-testid="stBottom"] {
            background-color: #e9d2b4 !important;
            box-shadow: none !important;
            border-top: none !important;
        }
        [data-testid="stBottomBlockContainer"] {
            background-color: #e9d2b4 !important;
            padding: 0 !important;
        }

        /* Customize sidebar background for a warm, clean feel */
        [data-testid="stSidebar"] {
            background-color: #f7e6d0 !important;
            border-right: 1px solid #f87d0f33 !important;
        }
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3, 
        [data-testid="stSidebar"] p, 
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] span {
            color: #3d1706 !important;
        }
        
        /* Ensure chat text area inherits clean styling */
        .stChatInput textarea {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        }

        /* FORCE ALL COOKEIN / ATHTHAMMA AI RESPONSES TO BE IN #3d1706 */
        [data-testid="stChatMessage"] {
            background-color: transparent !important; /* Keeps background clean */
        }
        
        /* Target assistant text messages specifically */
        [data-testid="stChatMessageContent"] {
            color: #3d1706 !important;
        }
        
        /* Ensure standard markdown elements inside responses match your color */
        [data-testid="stChatMessageContent"] p, 
        [data-testid="stChatMessageContent"] li, 
        [data-testid="stChatMessageContent"] ol {
            color: #3d1706 !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# 1. Initialize the Gemini Client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. Sidebar Setup with Logo
if os.path.exists("logo1.png"):
    # Center the logo in the sidebar with a smaller width (swapped from welcome page)
    col_sb1, col_sb2, col_sb3 = st.sidebar.columns([1, 8, 1])
    with col_sb2:
        st.image("logo1.png", width=180)

# 2. Sidebar Setup for Local Ingredients Search
st.sidebar.header("Kitchen Pantry")
st.sidebar.write("Select the items you have available, and CookIN will suggest what you can prepare!")

# Define a collection of common local ingredients
common_ingredients = [
    "Eggs", "Kithul Jaggery", "Coconut Milk", "Cardamom", "Nutmeg",
    "Rice Flour", "Coconut Scraps", "Treacle", "Bananas", "Onions", 
    "Green Chillies", "Curry Leaves", "Chilli Powder", "Coconut Oil", "Potatoes", "Tomatoes", "Garlic", "Ginger", "Cinnamon"
]

selected_ingredients = st.sidebar.multiselect("Available Ingredients:", options=common_ingredients, default=[])
custom_ingredients = st.sidebar.text_input("Any other ingredients? (comma-separated):")
st.sidebar.markdown("___")
suggest_recipe_clicked = st.sidebar.button("✨ Suggest Recipes Based on Pantry")

# Combine all ingredients into a clean list format ---
all_ingredients = list(selected_ingredients)
if custom_ingredients:
    all_ingredients.extend([i.strip() for i in custom_ingredients.split(",") if i.strip()])

# 3. Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Reset Kitchen / Clear Chat Session Button
st .sidebar.markdown("___")
if st.sidebar.button("Reset kitchen (Clear Chat)"):
    st.session_state.messages = []

    # Clear local cache file on reset if it exists
    if os.path.exists("active_recipe.txt"):
        os.remove("active_recipe.txt")
    st.rerun()

# Global variables for capturing inputs
user_intent = None
chat_input = None
audio_input = None

# -------------------------------------------------------------------------
# LAYOUT CONDITION 1: EMPTY CONVERSATION (Show Centered Welcome Page)
# -------------------------------------------------------------------------

if not st.session_state.messages:
    # Convert logo to base64 for HTML embedding
    logo_base64 = ""
    if os.path.exists("logo1.png"):
        with open("logo1.png", "rb") as image_file:
            logo_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Inject background and custom container styling to fit the screen without a scroll bar
    st.markdown(
        """
        <style>
            /* Force the main background color and hide scrollbar */
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #e9d2b4 !important;
                overflow: hidden !important;
                height: 100vh !important;
            }
            [data-testid="stHeader"] {
                background: transparent !important;
            }
            
            /* Center the welcome container relative to the viewport by default (sidebar closed) */
            .welcome-container {
                position: fixed !important;
                top: 2vh !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                width: 85% !important;
                max-width: 580px !important;
                text-align: center !important;
                display: flex !important;
                flex-direction: column !important;
                align-items: center !important;
                z-index: 10 !important;
                transition: left 0.3s ease, width 0.3s ease !important;
            }
            
            .welcome-logo {
                width: 220px !important;
                height: auto !important;
                margin-bottom: 2vh !important;
            }
            
            /* Title Typography with !important to prevent Streamlit overrides */
            .main-title {
                color: #3d1706 !important;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
                font-size: 2.6rem !important;
                font-weight: 700 !important;
                margin: 0 0 1vh 0 !important;
                line-height: 1.2 !important;
            }
            .sub-title {
                color: #953108 !important;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
                font-size: 1.15rem !important;
                font-weight: 600 !important;
                margin: 0 !important;
                line-height: 1.4 !important;
            }
            
            /* Position and Style the Bottom Chat Input block in its slot by default */
            [data-testid="stBottom"] {
                position: fixed !important;
                bottom: 18vh !important; /* Positioned relative to bottom */
                top: auto !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                width: 85% !important;
                max-width: 540px !important;
                background-color: transparent !important;
                box-shadow: none !important;
                border: none !important;
                z-index: 99 !important;
                padding: 0 !important;
                transition: left 0.3s ease, width 0.3s ease !important;
            }
            
            /* Make the inner wrapper transparent to remove the white background band */
            [data-testid="stBottom"] > div {
                background-color: transparent !important;
                background: transparent !important;
                box-shadow: none !important;
                border: none !important;
                padding: 0 !important;
            }
            
            [data-testid="stBottomBlockContainer"] {
                background-color: transparent !important;
                padding: 0 !important;
            }
            
            /* TARGET STREAMLIT CHAT INPUT CONTAINER FOR PILL SHAPE */
            [data-testid="stChatInput"] {
                border: 2px solid #f87d0f !important;
                border-radius: 50px !important; /* Forces perfect pill shape */
                background-color: #ffffff !important;
                padding: 6px 16px !important;
                box-shadow: 0 4px 10px rgba(0,0,0,0.05) !important;
                width: 100% !important;
            }
            
            /* Make entire inside of the pill full white (removes Streamlit's two-color gray/blue textarea bg) */
            [data-testid="stChatInput"] div {
                background-color: transparent !important;
                background: transparent !important;
            }
            
            [data-testid="stChatInput"]:focus-within {
                border-color: #f87d0f !important;
                box-shadow: 0 0 0 0.2rem rgba(248, 125, 15, 0.25) !important;
            }
            
            /* Make sure text input area background stays white inside the pill */
            [data-testid="stChatInput"] textarea {
                background-color: transparent !important;
                color: #3d1706 !important;
                font-size: 1.05rem !important;
                caret-color: #3d1706 !important;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
            }
            
            /* Customize the built-in send arrow button to match #7fbf1f */
            button[data-testid="stChatInputSubmitButton"] {
                background-color: #7fbf1f !important;
                color: white !important;
                border-radius: 50% !important;
                width: 38px !important;
                height: 38px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                border: none !important;
                transition: transform 0.2s, background-color 0.2s !important;
            }
            
            button[data-testid="stChatInputSubmitButton"]:hover {
                background-color: #6da31a !important;
                transform: scale(1.05);
            }
            
            .footer-hint {
                position: fixed !important;
                bottom: 11vh !important; /* Positioned directly below input with clearance */
                top: auto !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
                width: 85% !important;
                color: #953108 !important;
                font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
                font-size: 1rem !important;
                font-weight: 500 !important;
                margin: 0 !important;
                text-align: center;
                opacity: 0.9;
                z-index: 10 !important;
                transition: left 0.3s ease, width 0.3s ease !important;
            }
            
            /* Hide vertical scrollbar for main Streamlit page container */
            [data-testid="stAppViewBlockContainer"] {
                overflow: hidden !important;
                padding: 0 !important;
                height: 100vh !important;
            }
            .main {
                overflow: hidden !important;
            }

            /* --- DYNAMIC ADJUSTMENTS WHEN THE SIDEBAR IS EXPANDED --- */
            @media (min-width: 768px) {
                section[data-testid="stSidebar"][data-collapsed="false"] ~ section.stMain .welcome-container {
                    left: calc(50% + 168px) !important;
                    width: calc(100% - 370px) !important;
                }
                section[data-testid="stSidebar"][data-collapsed="false"] ~ section.stMain [data-testid="stBottom"] {
                    left: calc(50% + 168px) !important;
                    width: calc(100% - 370px) !important;
                }
                section[data-testid="stSidebar"][data-collapsed="false"] ~ section.stMain .footer-hint {
                    left: calc(50% + 168px) !important;
                    width: calc(100% - 370px) !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # 1. Render Logo and Headers in a single styled block
    logo_html = f'<img class="welcome-logo" src="data:image/png;base64,{logo_base64}" />' if logo_base64 else ""
    st.markdown(
        f"""
        <div class="welcome-container">
            {logo_html}
            <h1 class="main-title">Hello, I'm Aththamma</h1>
            <p class="sub-title">What traditional Sri Lankan dish are we cooking together today, my dear?</p>
        </div>
        <p class="footer-hint">Or use the sidebar to select your pantry ingredients!</p>
        """,
        unsafe_allow_html=True
    )

    # 2. Streamlit Pill Input Component
    chat_input = st.chat_input("Ask Aththamma for a traditional recipe....")
   
# -------------------------------------------------------------------------
# LAYOUT CONDITION 2: ACTIVE CONVERSATION (Show History & Fixed Bottom Layout)
# -------------------------------------------------------------------------
else:
    # Head row with small inline branding once active
    col_title_l, col_title_r = st.columns([1,12])
    with col_title_l:
        if os.path.exists("logo1.png"):
            st.image("logo1.png", width=60)
    with col_title_r:
         st.title("CookIN — Your Personal Culinary Assistant")
    
    # Display past chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
    # Fixed Bottom Container for the Typing Interface
    with st.container():
        col_mic, col_text = st.columns([1, 5])
        with col_mic:
            audio_input = mic_recorder(
                start_prompt="🎙️ Speak",
                stop_prompt="🛑 Stop",
                key="pantry_audio"
            )
        with col_text:
            chat_input = st.chat_input("Ask Aththamma for a recipe, next steps, or cooking tips...")


# 4. Core Logic: Process Inputs (Sidebar Text Button OR Voice Input OR Standard Text Chat)
# Case A: User clicked the pantry suggestion button from sidebar
if suggest_recipe_clicked:
    if all_ingredients:
        ingredients_string = ", ".join(all_ingredients)
        user_intent = f"I have these ingredients in my kitchen: {ingredients_string}. What local recipes or treats can I make with them? Suggest options and provide a full step-by-step recipe for the best match."
    else:
        st.sidebar.warning("Please select or type at least one ingredient first!")

# Case B: User recorded a voice message 
elif audio_input and "bytes" in audio_input and audio_input["bytes"]:
    with st.spinner("🎙️ Aththamma is listening closely..."):
        try:
            temp_audio_payload = genai.types.Part.from_bytes(data=audio_input["bytes"], mime_type="audio/webm")
            transcription_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    "You are a speech-to-text transcriber. Listen to this audio and write down exactly what the user said in plain text. Just output the exact transcription.",
                    temp_audio_payload
                ]
            )
            transcribed_text = transcription_response.text.strip()
            user_intent = f"🎙️ **Voice Message:** {transcribed_text}"
        except Exception as e:
            user_intent = "🎤 *Sent a voice message (Transcription failed)*"

# Case C: User inputted text (Works for both center bar and bottom bar smoothly!)
elif chat_input:
    user_intent = chat_input

# 5. Execute AI Generation If There Is An Active Intent
if user_intent:
    # Display the user prompt in the chat container
    with st.chat_message("user"):
        st.markdown(user_intent)
    
    st.session_state.messages.append({"role": "user", "content": user_intent})

    # Prepare the chronological conversation history payload
    contents_payload = []
    for msg in st.session_state.messages:
        role_type = "user" if msg["role"] == "user" else "model"
        contents_payload.append(
            genai.types.Content(role=role_type, parts=[genai.types.Part.from_text(text=msg["content"])])
        )
        
    # Display assistant response block
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # (Keep your robust cookin_persona definition here)
        cookin_persona = (
            "Role: You are 'Aththamma' (Grandma), a loving traditional Sri Lankan grandmother and master chef.\n"
            "Tone: Warm, maternal, encouraging, and highly precise.\n\n"
            "CRITICAL RESPONSE DELIVERY RULES:\n"
            "1. SINGLE-TURN COMPLETENESS: Provide the entire recipe (Ingredients, Prep, and Steps) all at once in your very first response. Never break it across multiple conversational turns or ask the user to prompt you for the next section.\n"
            "2. Live Kitchen Rescue: If the user indicates a problem mid-cooking, immediately scan previous context and provide a direct solution.\n"
            "3. Formatting & Scannability: Use bold text for key visual cues, temperatures, or flame levels. Keep steps short (under 15 words) so they are easy to glance at while cooking.\n"
            "4. Structure: Always group the response into three compact Markdown sections within the same message: '📋 Ingredients', '🔥 Stove Setup & Prep', and '👩‍🍳 Cooking Steps'.\n"
            "5. Always end with your signature sweet maternal advice labeled as '**Aththamma's Tip:**'."
        )

        try:
            response_stream = client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=contents_payload,
                config=types.GenerateContentConfig(system_instruction=cookin_persona, temperature=0.4)
            )
            full_response = message_placeholder.write_stream(chunk.text for chunk in response_stream)

            # 2. SUCCESS: Cache the latest response locally for offline access
            with open("active_recipe.txt", "w", encoding="utf-8") as f:
                f.write(full_response)

        except Exception as e:
            # 3. OFFLINE FALLBACK: If API fails, look for the local file cache
            if os.path.exists("active_recipe.txt"):
                with open("active_recipe.txt", "r", encoding="utf-8") as f:
                    cached_response = f.read()
                full_response = (
                    "**Network Connection Lost.** *Aththamma is running in offline mode from your kitchen cache:*\n\n"
                    + cached_response
                )
                message_placeholder.markdown(full_response)
            else:
                full_response = f"Connection Error: Please check your internet connection. (Error: {str(e)})"
                message_placeholder.markdown(full_response)
            
    # Save assistant's final structured output to memory
    st.session_state.messages.append({"role": "assistant", "content": full_response})

    #Forcing a layout adjustment refresh    
    st.rerun()