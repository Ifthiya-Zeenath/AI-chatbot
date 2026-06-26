import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="CookIN", page_icon="🍳", layout="wide")

st.title("🍳 CookIN — Your Personal Culinary Assistant")

# 1. Initialize the Gemini Client
# Replace with your actual key from Google AI Studio
client = genai.Client(api_key="AQ.Ab8RN6K9cmCtV4dSs87mkBjph-bCUSQ8z5nmSTrQu-Rc8EcMuQ")

# 2. Sidebar Setup for Local Ingredients Search
st.sidebar.header("🛒 Kitchen Pantry")
st.sidebar.write("Select the items you have available, and CookIN will suggest what you can prepare!")

# Define a collection of common local ingredients
common_ingredients = [
    "Eggs", "Kithul Jaggery", "Coconut Milk", "Cardamom", "Nutmeg",
    "Rice Flour", "Coconut Scraps", "Treacle", "Bananas", "Onions", 
    "Green Chillies", "Curry Leaves", "Chilli Powder", "Coconut Oil"
]

# A multi-select widget allows users to pick multiple ingredients easily
selected_ingredients = st.sidebar.multiselect(
    "Available Ingredients:",
    options=common_ingredients,
    default=[]
)

# Optional: Allow the user to type custom ingredients not in the list
custom_ingredients = st.sidebar.text_input("Any other ingredients? (comma-separated):")

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

# 4. Core Logic: Process Inputs (Either Sidebar Button OR Standard Chat Input)
user_intent = None

# Case A: User clicked the pantry suggestion button
if suggest_recipe_clicked:
    if all_ingredients:
        ingredients_string = ", ".join(all_ingredients)
        user_intent = f"I have these ingredients in my kitchen: {ingredients_string}. What local recipes or treats can I make with them? Suggest options and provide a full step-by-step recipe for the best match."
    else:
        st.sidebar.warning("Please select or type at least one ingredient first!")

# Case B: User typed directly into the standard chat bar
elif chat_input := st.chat_input("Ask CookIN for a recipe or cooking tip..."):
    user_intent = chat_input

# 5. Execute AI Generation If There Is An Active Intent
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

    # Display assistant response block
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # System Instruction tailored to respect pantry constraints
        cookin_persona = (
            "Role: You are CookIN, an expert, friendly culinary chef specializing in detailed cooking instructions. "
            "Your main focus is providing step-by-step cooking guidance and localized recipes.\n\n"
            "Formatting & Ingestion Rules:\n"
            "1. When a user provides a specific list of available kitchen pantry ingredients, prioritize suggesting localized recipes that heavily utilize those ingredients.\n"
            "2. It is fine to assume common, standard kitchen staples are available (like salt, water, or basic oil), but highlight any missing primary ingredients clearly if they are needed.\n"
            "3. When presenting a recipe, always provide an 'Estimated Time' and a structured 'Ingredients List' with clear quantities first.\n"
            "4. Break down the cooking instructions into clear, numbered chronological steps (e.g., Step 1: Grate the jaggery, Step 2: Beat the eggs).\n"
            "5. Keep your instructions practical, emphasizing critical actions (e.g., 'Strain the mixture to prevent air bubbles')."
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
            full_response = f"⚠️ Error: {str(e)}"
            message_placeholder.markdown(full_response)

    # Save assistant's final structured output to memory
    st.session_state.messages.append({"role": "assistant", "content": full_response})