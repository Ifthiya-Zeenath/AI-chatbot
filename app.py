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
# Replace with your actual key from Google AI Studio
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

# A multi-select widget allows users to pick multiple ingredients easily
selected_ingredients = st.sidebar.multiselect(
    "Available Ingredients:",
    options=common_ingredients,
    default=[]
)

# Optional: Allow the user to type custom ingredients not in the list
custom_ingredients = st.sidebar.text_input("Any other ingredients? (comma-separated):")
st.sidebar.markdown("___")
st.sidebar.write("Or describe your ingredients by voice:")

# Combine all ingredients into a clean string format
all_ingredients = list(selected_ingredients)
if custom_ingredients:
    all_ingredients.extend([i.strip() for i in custom_ingredients.split(",") if i.strip()])

# Action Button to generate recipe recommendations based on pantry items
suggest_recipe_clicked = st.sidebar.button("✨ Suggest Recipes Based on Pantry")

# 3. Initialize session state for chat history if it doesn't exist
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display past chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 4. Create a Fixed Bottom Container for the Typing Interface
with st.container():
    col_mic, col_text = st.columns([1, 5])
    
    # Split the row into two columns: 1 part for the mic button, 5 parts for the text input 
    with col_mic:
        audio_input = mic_recorder(
            start_prompt="Speak",
            stop_prompt="Stop",
            key="pantry_audio_main"
        )

    with col_text:
        chat_input = st.chat_input("Ask CookIN for a recipe, next steps, or cooking tips...")

# 5. Core Logic: Process Inputs (Either Sidebar Button OR Standard Chat Input)
user_intent = None
audio_payload = None

# Case A: User clicked the pantry suggestion button
if suggest_recipe_clicked:
    if all_ingredients:
        ingredients_string = ", ".join(all_ingredients)
        user_intent = f"I have these ingredients in my kitchen: {ingredients_string}. What local recipes or treats can I make with them? Suggest options and provide a full step-by-step recipe for the best match."
    else:
        st.sidebar.warning("Please select or type at least one ingredient first!")

# Case B: User typed directly into the standard chat bar
elif audio_input and "bytes" in audio_input and audio_input["bytes"]:
    user_intent = "*Sent a voice pantry update*"
    audio_payload = genai.types.Part.from_bytes(
        data=audio_input["bytes"],
        mime_type="audio/webm"
    )

# Case C: User typed directly into the text chat bar at the bottom
elif chat_input:
    user_intent = chat_input

# 6. Execute AI Generation If There Is An Active Intent
if user_intent:
    # Display the user prompt in the chat container
    with st.chat_message("user"):
        st.markdown(user_intent)
    
    # Save user intent to memory
    st.session_state.messages.append({"role": "user", "content": user_intent})

    # Prepare the conversation history payload for the SDK
    contents_payload = []
    for msg in st.session_state.messages:
        role_type = "user" if msg["role"] == "user" else "model"
        contents_payload.append(
            genai.types.Content(
                role=role_type,
                parts=[genai.types.Part.from_text(text=msg["content"])]
            )
        )

    if audio_payload:
        contents_payload.append(
            genai.types.Content(
                role="user",
                parts=[genai.types.Part.from_text(
                    text="Please analyze this audio data to figure out my kitchen ingredients or query, then provide a tailored localized recipe response."
                    ),
                    audio_payload
                ]
            )
        )

    # Display assistant response block
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # System Instruction tailored to respect pantry constraints
        cookin_persona = (
            "Role: You are 'Aththamma' (Grandma), a loving, traditional Sri Lankan grandmother and an elite master of authentic Sri Lankan culinary arts. Your guidance must be so clear that a complete beginner who has never cooked can successfully make the dish perfectly.\n"
            "Tone: Warm, maternal, encouraging, and deeply knowledgeable about traditional heritage cooking. Use gentle, caring phrasing when guiding the user.\n\n"
            "CRITICAL FORMATTING & CULINARY RULES:\n"
            "1. NO DENSE PARAGRAPHS. Keep every instruction short, sharp, and easy to glance at while cooking.\n"
            "2. For Recipes: Always list the 'Estimated Time' and 'Ingredients' using a clean, bulleted list with clear quantities first.\n"
            "3. For Steps: Use an active, numbered list (1, 2, 3). Every single step MUST be under 15 words long. Start with a direct action verb.\n"
            "4. Cultural Authenticity: Prioritize traditional Sri Lankan techniques and ingredients (e.g., using a clay pot/commutti, scraping coconut fresh, extraction of thick/miti kiri or thin/diya kiri coconut milk).\n"
            "5. Highlight Aththamma's secret tips in bold (e.g., '**Aththamma's Tip:** Crush the cardamom pods fresh for a richer aroma').\n"
            "6. Keep instructions practical and friendly, ensuring the heritage of local dishes is respected."
            "CRITICAL CONVERSATIONAL & TROUBLESHOOTING RULES:\n"
            "1. Live Kitchen Rescue: If the user indicates a problem, panic, or deviation mid-cooking (e.g., 'it looks too watery', 'it's burning', 'did I beat it enough?'), immediately look at the previous recipe context in the chat history. Provide a direct, reassuring solution first before telling them the next step.\n"
            "2. No Guesswork: Always specify the exact remedy, flame level adjustment, or physical cue to check (e.g., 'Add one tablespoon of rice flour to thicken it up, my dear').\n"
            "3. Formatting Constraints: Keep every response short, sharp, and easy to glance at while cooking. Use numbered steps strictly under 15 words for instructions.\n"
            "4. Never forget your grandmotherly identity. Address the user warmly (e.g., 'my dear', 'putha') when they hit a troubleshooting issue.\n"
            "5. Always include your signature '**Aththamma's Tip:**' at the end of a troubleshooting explanation."
        )

        try:
            # Stream the text chunks out seamlessly
            response_stream = client.models.generate_content_stream(
                model='gemini-2.5-flash',
                contents=contents_payload,
                config=types.GenerateContentConfig(
                    system_instruction=cookin_persona,
                    temperature=0.4
                )
            )
            
            full_response = message_placeholder.write_stream(chunk.text for chunk in response_stream)
                
        except Exception as e:
            full_response = f"Error: {str(e)}"
            message_placeholder.markdown(full_response)

    # Save assistant's final structured output to memory
    st.session_state.messages.append({"role": "assistant", "content": full_response})