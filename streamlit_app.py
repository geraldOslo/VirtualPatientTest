import streamlit as st
from openai import AzureOpenAI
import os
import base64
from gtts import gTTS
import tempfile
import PyPDF2
from io import BytesIO

# Define the initial system content
DEFAULT_SYSTEM_CONTENT = """
Du skal spille rollespill for å gi tannlegestudenter trening i å kommunisere med pasienter som har demensutfordringer. 
Du skal være den demente pasienten og svare som den. Beskrivelse av demens: Du glemmer lett og kan virke litt forvirret, ...

Bruk samtaleeksempler i filene lastet opp som eksempler på hvordan en dement pasient kommuniserer med sin tannlege
"""

# Create an AzureOpenAI client
client = AzureOpenAI(
    azure_endpoint=st.secrets["OPENAI_API_BASE"],
    api_version=st.secrets["OPENAI_API_VERSION"],
    api_key=st.secrets["OPENAI_API_KEY"],
)

# Function to create speech from text
def text_to_speech(text):
    tts = gTTS(text=text, lang='no')
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        return fp.name

# Function to create a playable audio in streamlit
def autoplay_audio(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)

# Sidebar settings
st.sidebar.title("Innstillinger")
speech_enabled = st.sidebar.toggle("Aktiver tale", value=True)
file_enabled = st.sidebar.toggle("Aktiver filopplasting", value=False)

# Editable system prompt in sidebar
if "system_content" not in st.session_state:
    st.session_state.system_content = DEFAULT_SYSTEM_CONTENT

st.session_state.system_content = st.sidebar.text_area(
    "System Prompt (AI instructions)",
    st.session_state.system_content,
    height=300
)

# File uploader in sidebar if enabled
if file_enabled:
    uploaded_file = st.sidebar.file_uploader("Last opp fil med samtaleeksempler", type=["txt", "pdf"])
    if uploaded_file is not None:
        if uploaded_file.type == "text/plain":
            file_contents = uploaded_file.read().decode("utf-8")
        elif uploaded_file.type == "application/pdf":
            reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
            file_contents = ""
            for page in reader.pages:
                file_contents += page.extract_text()
        else:
            st.sidebar.error("Ikke støttet filtype.")
            file_contents = ""

        if file_contents:
            st.sidebar.text_area("Innhold i filen:", file_contents, height=200)
            if "messages" in st.session_state:
                st.session_state.messages.append({
                    "role": "system",
                    "content": f"Samtaleeksempler:\n{file_contents}"
                })

# Main app
st.title("💬 SimSamBot")
st.write("Prototype for intern testing")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": st.session_state.system_content
        }
    ]

# Update system message if it has changed
if st.session_state.messages[0]["content"] != st.session_state.system_content:
    st.session_state.messages[0]["content"] = st.session_state.system_content

# Display the existing chat messages
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field
if prompt := st.chat_input("Hva vil du si til pasienten?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        response = client.chat.completions.create(
            model=st.secrets["OPENAI_DEPLOYMENT_NAME"],
            messages=st.session_state.messages,
            temperature=1,
            top_p=1,
            max_tokens=500,
            stream=True,
        )

        with st.chat_message("assistant"):
            response_text = st.empty()
            full_response = ""
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    chunk_message = chunk.choices[0].delta.content
                    if chunk_message:
                        full_response += chunk_message
                        response_text.markdown(full_response)
            
            if full_response:
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                if speech_enabled:
                    # Generate speech from the response
                    speech_file = text_to_speech(full_response)
                    autoplay_audio(speech_file)
                    # Clean up the temporary audio file
                    os.remove(speech_file)
            else:
                st.error("Ingen respons mottatt fra AI. Vennligst prøv igjen.")
                
    except Exception as e:
        st.error(f"En feil oppstod: {str(e)}")
        st.error(f"Responsobjekt: {response}")
