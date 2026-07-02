import streamlit as st
from google import genai
from google.genai import types
from streamlit_mic_recorder import mic_recorder

st.set_page_config(page_title="CookIN", page_icon="🍳", layout="wide")

# --- INJECT CUSTOM SAN FRANCISCO FONT STYLING ---
st.markdown(
    """
    <style>
        /* Target the main app container, buttons, sidebar, and inputs */
        html, body, [data-testid="stAppViewContainer"], .stApp, button, input, select, textarea {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        }
        
        /* Ensure chat input bar inherits the clean font style */
        .stChatInput textarea {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro", "SF Pro Text", "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("CookIN — Your Personal Culinary Assistant")

# 1. Initialize the Gemini Client
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

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

# --- FIX: Combine all ingredients into a clean list format ---
all_ingredients = list(selected_ingredients)
if custom_ingredients:
    all_ingredients.extend([i.strip() for i in custom_ingredients.split(",") if i.strip()])

# 3. Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

if st.sidebar.button("Reset kitchen (Clear Chat)"):
    st.session_state.messages = []
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
    for _ in range(5):
        st.write("")
        
    # Main Welcome Header Layout
    st.markdown("<h1 style='text-align: center; font-weight: 700;'>Hello, I'm Aththamma</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888888; font-size: 1.2rem;'>What traditional Sri Lankan dish are we cooking together today, my dear?</p>", unsafe_allow_html=True)
    
    for _ in range(2):
        st.write("")

    # Centered Input Box Container
    col_left, col_mid, col_right = st.columns([1, 3, 1])
    with col_mid:
        chat_input = st.chat_input("Ask Aththamma for a traditional recipe...")
        st.write("")
        st.write("Or use the sidebar to select your pantry ingredients!")

# -------------------------------------------------------------------------
# LAYOUT CONDITION 2: ACTIVE CONVERSATION (Show History & Fixed Bottom Layout)
# -------------------------------------------------------------------------
else:
    # Display the app title at the top once the chat is active
    st.title("🍳 CookIN — Your Personal Culinary Assistant")
    
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
            "CRITICAL CONVERSATIONAL & TROUBLESHOOTING RULES:\n"
            "1. Live Kitchen Rescue: If the user indicates a problem mid-cooking, look at previous context and provide an immediate solution.\n"
            "2. No Guesswork: Always specify exact flame level adjustments or physical visual cues.\n"
            "3. Formatting Constraints: Keep every response short, sharp, and easy to glance at. Use numbered steps under 15 words.\n"
            "4. Always include your signature '**Aththamma's Tip:**' at the end."
        )

        try:
            response_stream = client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=contents_payload,
                config=types.GenerateContentConfig(system_instruction=cookin_persona, temperature=0.4)
            )
            full_response = message_placeholder.write_stream(chunk.text for chunk in response_stream)

            #Forcing a layout adjustment refresh    
            st.rerun()
        
        except Exception as e:
            full_response = f"⚠️ Error: {str(e)}"
            message_placeholder.markdown(full_response)
            
     # Save assistant's final structured output to memory
    st.session_state.messages.append({"role": "assistant", "content": full_response})