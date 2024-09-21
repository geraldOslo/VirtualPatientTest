import streamlit as st
from openai import AzureOpenAI
import os
import base64
from gtts import gTTS
import tempfile

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

# Create an AzureOpenAI client
client = AzureOpenAI(
    azure_endpoint=st.secrets["OPENAI_API_BASE"],
    api_version=st.secrets["OPENAI_API_VERSION"],
    api_key=st.secrets["OPENAI_API_KEY"],
)

# Show title and description.
st.title("💬 Chatbot")
st.write("Prototype av SimSamBot")

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "Du skal spille rollespill for å gi tannlegestudenter trening i å kommunisere med pasienter som har demensutfordringer. "
                "Du skal være den demente pasienten og svare som den. Beskrivelse av demens: Du glemmer lett og kan virke litt forvirret, ...\n\n"
                "Bruk samtaleeksemplene i filene lastet opp som eksempler på hvordan en dement pasient kommuniserer med sin tannlege"
            )
        }
    ]
    st.session_state.file_contents = ""

# File uploader for conversation examples
uploaded_file = st.file_uploader("Last opp fil med samtaleeksempler", type=["txt", "pdf"])

if uploaded_file is not None and not st.session_state.file_contents:
    if uploaded_file.type == "text/plain":
        file_contents = uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        import PyPDF2
        from io import BytesIO
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getvalue()))
        file_contents = ""
        for page in reader.pages:
            file_contents += page.extract_text()
    else:
        st.error("Unsupported file type.")
        file_contents = ""

    st.text_area("Innhold i filen:", file_contents, height=200)

    st.session_state.messages.append({
        "role": "system",
        "content": f"Samtaleeksempler:\n{file_contents}"
    })
    st.session_state.file_contents = file_contents

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
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
            # Generate speech from the response
            speech_file = text_to_speech(full_response)
            autoplay_audio(speech_file)
            
    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.error(f"Response object: {response}")
