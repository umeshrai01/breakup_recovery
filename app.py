from agno.agent import Agent
from agno.models.google import Gemini
from agno.media import Image as AgnoImage
from agno.tools.duckduckgo import DuckDuckGoTools
import streamlit as st
from typing import List, Optional
import logging
from pathlib import Path
import tempfile
import os

# Optional: load .env locally (not required on deployed server)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# ------------------------------
# SECURE API KEY HANDLING
# ------------------------------
api_key = None

# 1) Try Streamlit secrets (Streamlit Cloud)
try:
    api_key = st.secrets.get("gemini_api_key")
except Exception:
    api_key = None

# 2) Fallback to environment variable (Render, Vercel, Heroku, Local .env)
if not api_key:
    api_key = os.getenv("GEMINI_API_KEY")

# 3) Stop if no key is configured
if not api_key:
    st.set_page_config(page_title="Error", page_icon="⚠️")
    st.error("❌ Gemini API key not found.\n\nPlease set it as:")
    st.code("st.secrets['gemini_api_key'] = 'YOUR_KEY_HERE'")
    st.code("export GEMINI_API_KEY=YOUR_KEY")
    st.stop()

# ------------------------------
# AGENT INITIALIZATION
# ------------------------------
def initialize_agents(api_key: str) -> tuple[Agent, Agent, Agent, Agent]:
    try:
        model = Gemini(id="gemini-2.5-pro", api_key=api_key)
        
        therapist_agent = Agent(
            model=model,
            name="Therapist Agent",
            instructions=[
                "You are an empathetic therapist that:",
                "1. Listens with empathy and validates feelings",
                "2. Uses gentle humor to lighten the mood",
                "3. Shares relatable breakup experiences",
                "4. Offers comforting words and encouragement",
                "5. Analyzes both text and image inputs for emotional context",
                "6. If the user responds in hinglish, give the whole reply in hinglish or hindi",
                "Be supportive and understanding in your responses"
            ],
            markdown=True
        )

        closure_agent = Agent(
            model=model,
            name="Closure Agent",
            instructions=[
                "You are a closure specialist that:",
                "1. Creates emotional messages for unsent feelings",
                "2. Helps express raw, honest emotions",
                "3. Formats messages clearly with headers",
                "4. Ensures tone is heartfelt and authentic",
                "5. If the user responds in hinglish, give the whole reply in hinglish or hindi"
                "Focus on emotional release and closure"
            ],
            markdown=True
        )

        routine_planner_agent = Agent(
            model=model,
            name="Routine Planner Agent",
            instructions=[
                "You are a recovery routine planner that:",
                "1. Designs 7-day recovery challenges",
                "2. Includes fun activities and self-care tasks",
                "3. Suggests social media detox strategies",
                "4. Creates empowering playlists",
                "5. If the user responds in hinglish, give the whole reply in hinglish or hindi",
                "Focus on practical recovery steps"
            ],
            markdown=True
        )

        brutal_honesty_agent = Agent(
            model=model,
            name="Brutal Honesty Agent",
            tools=[DuckDuckGoTools()],
            instructions=[
                "You are a direct feedback specialist that:",
                "1. Gives raw, objective feedback about breakups",
                "2. Explains relationship failures clearly",
                "3. Uses blunt, factual language",
                "4. Provides reasons to move forward",
                "5. If the user responds in hinglish, give the whole reply in hinglish or hindi",
                "Focus on honest insights without sugar-coating"
            ],
            markdown=True
        )
        
        return therapist_agent, closure_agent, routine_planner_agent, brutal_honesty_agent

    except Exception as e:
        st.error(f"Error initializing agents: {str(e)}")
        return None, None, None, None

# ------------------------------
# PAGE UI
# ------------------------------
st.set_page_config(
    page_title="💔 Breakup Recovery App",
    page_icon="💔",
    layout="wide"
)

st.title("💔 Breakup Recovery App")
st.markdown("""
### Your AI-powered breakup recovery team is here to help!
Share your feelings and chat screenshots, and we'll help you navigate through this tough time.
""")

# ------------------------------
# CONSENT (ADDED)
# ------------------------------
st.markdown("### Privacy & Consent")
consent = st.checkbox(
    "I consent to processing my text and uploaded images for the purpose of generating breakup recovery suggestions. I understand that I should not upload extremely sensitive personal information.",
    value=False
)
if not consent:
    st.info("Please provide consent to proceed. Your content will not be processed until you consent.")
# Note: we do not stop the user from interacting with the page UI, but we enforce consent at processing time.

# ------------------------------
# INPUT SECTION
# ------------------------------
col1, col2 = st.columns(2)

with col1:
    st.subheader("Share Your Feelings")
    user_input = st.text_area(
        "How are you feeling? What happened?",
        height=150,
        placeholder="Tell us your story..."
    )

with col2:
    st.subheader("Upload Chat Screenshots")
    uploaded_files = st.file_uploader(
        "Upload screenshots (optional)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        key="screenshots"
    )

    if uploaded_files:
        for file in uploaded_files:
            st.image(file, caption=file.name, use_container_width=True)

# ------------------------------
# PROCESS REQUEST
# ------------------------------
if st.button("Get Recovery Plan 💝", type="primary"):

    # enforce consent before processing
    if not consent:
        st.warning("You must give consent before we can process your input.")
        st.stop()

    therapist_agent, closure_agent, routine_planner_agent, brutal_honesty_agent = initialize_agents(api_key)

    if not all([therapist_agent, closure_agent, routine_planner_agent, brutal_honesty_agent]):
        st.error("Failed to initialize agents. Please check your configuration.")
        st.stop()

    if not (user_input or uploaded_files):
        st.warning("Please share your feelings or upload screenshots.")
        st.stop()

    # Process images
    def process_images(files):
        processed_images = []
        for file in files:
            try:
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, f"temp_{file.name}")
                
                with open(temp_path, "wb") as f:
                    f.write(file.getvalue())
                
                agno_image = AgnoImage(filepath=Path(temp_path))
                processed_images.append(agno_image)
                
            except Exception as e:
                logger.error(f"Error processing image {file.name}: {str(e)}")
                continue
        return processed_images

    all_images = process_images(uploaded_files) if uploaded_files else []

    st.header("Your Personalized Recovery Plan")

    # Therapist Section
    with st.spinner("🤗 Getting empathetic support..."):
        prompt = f"""
        Analyze the emotional state based on:
        User's message: {user_input}

        Provide:
        1. Validation of feelings
        2. Gentle words of comfort
        3. Relatable experiences
        4. Encouragement
        """
        response = therapist_agent.run(prompt, images=all_images)
        st.subheader("🤗 Emotional Support")
        st.markdown(response.content)

    # Closure Section
    with st.spinner("✍️ Crafting closure messages..."):
        prompt = f"""
        Create emotional closure content based on:
        User's feelings: {user_input}

        Include:
        1. Templates for unsent messages
        2. Emotional release exercises
        3. Closure rituals
        4. Moving forward guidance
        """
        response = closure_agent.run(prompt, images=all_images)
        st.subheader("✍️ Finding Closure")
        st.markdown(response.content)

    # Routine Section
    with st.spinner("📅 Creating your recovery plan..."):
        prompt = f"""
        Design a 7-day recovery plan based on:
        {user_input}

        Include:
        1. Daily activities
        2. Self-care routines
        3. Social media detox guidelines
        4. Music suggestions
        """
        response = routine_planner_agent.run(prompt, images=all_images)
        st.subheader("📅 Your Recovery Plan")
        st.markdown(response.content)

    # Brutal Honesty Section
    with st.spinner("💪 Getting honest perspective..."):
        prompt = f"""
        Provide honest feedback about:
        {user_input}

        Include:
        1. Objective analysis
        2. Growth opportunities
        3. Future outlook
        4. Concrete action steps
        """
        response = brutal_honesty_agent.run(prompt, images=all_images)
        st.subheader("💪 Honest Perspective")
        st.markdown(response.content)

# ------------------------------
# FOOTER
# ------------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center'>
    <p>Made by Umesh Kumar Rai</p>
    <p>Don't worry, time heals everything ❤️</p>
</div>
""", unsafe_allow_html=True)
