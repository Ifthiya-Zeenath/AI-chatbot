import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder
import os

st.set_page_config(page_title="CookIN", page_icon="🍳", layout="wide")

# --- INJECT CUSTOM SAN FRANCISCO FONT STYLING ---
st.markdown(
    """
    <style>
        /* 1. Global Typography Settings */
        html, body, [data-testid="stAppViewContainer"], .stApp, button, input, select, textarea {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        }
        
        .stChatInput textarea {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        }

        /* 2. Primary Button Styling (Orange & Green Logo Theme) */
        div.stButton > button:first-child {
            background-color: #FF8400 !important;
            color: #ffffff !important;
            border: 2px solid #5C3A21 !important; /* Soft brown border from logo */
            border-radius: 12px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease;
        }
        
        div.stButton > button:first-child:hover {
            background-color: #E07300 !important;
            box-shadow: 0px 4px 10px rgba(255, 132, 0, 0.3) !important;
        }

        /* 3. Welcome Screen Heading Customization */
        .welcome-title {
            text-align: center; 
            font-weight: 800; 
            color: #FF8400; /* Matching 'Cook' Orange */
            margin-bottom: 5px;
        }
        
        .welcome-subtitle {
            text-align: center; 
            color: #84D32C; /* Matching 'IN' Green */
            font-size: 1.3rem;
            font-weight: 600;
        }

        /* 4. Chat Input Focus Border Accent */
        .stChatInput focus-within {
            border-color: #84D32C !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# 1. Initialize the Gemini Client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# 2. Sidebar Setup with Logo
if os.path.exists("logo.png"):
    st.sidebar.image("logo.png", use_container_width=True)

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
    # Creating clean vertical spacing to push elements to the middle
    for _ in range(2):
        st.write("")

    # Render Logo Centered on landing page
    if os.path.exists("logo.png"):
        col_img_l, col_img_m, col_img_r = st.columns([1, 1, 1])
        with col_img_m:
            st.image("logo.png", use_container_width=True)
        
    # Main Welcome Header Layout
    st.markdown("<h1 class='welcome-title'>Hello, I'm Aththamma</h1>", unsafe_allow_html=True)
    st.markdown("<p class='welcome-subtitle'>What traditional Sri Lankan dish are we cooking together today, my dear?</p>", unsafe_allow_html=True)
   
    st.write("")

    # Centered Input Box Container
    col_left, col_mid, col_right = st.columns([1, 3, 1])
    with col_mid:
        chat_input = st.chat_input("Ask Aththamma for a traditional recipe...")
        st.write("")
        st.markdown("<p style='text-align: center; color: #888888;'>Or use the sidebar to select your pantry ingredients!</p>", unsafe_allow_html=True)

# -------------------------------------------------------------------------
# LAYOUT CONDITION 2: ACTIVE CONVERSATION (Show History & Fixed Bottom Layout)
# -------------------------------------------------------------------------
else:
    # Head row with small inline branding once active
    col_title_l, col_title_r = st.columns([1,12])
    with col_title_l:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=60)
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