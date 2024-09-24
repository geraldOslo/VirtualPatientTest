import streamlit as st
from openai import AzureOpenAI
import os
import base64
from gtts import gTTS
import tempfile
import PyPDF2
from io import BytesIO
import json
import pandas as pd
from io import StringIO

# URL til raw CSV-innhold
csv_url = 'https://raw.githubusercontent.com/geraldOslo/VirtualPatientTest/d4bc0e2da1548971f4d4937d887f09c3af2a0856/data/skybert.csv'

# Les CSV-filen og forbered dataene
try:
    response = requests.get(csv_url)
    response.raise_for_status()  # Vil reise en exception for HTTP-feil
    csv_content = StringIO(response.text)
    df = pd.read_csv(csv_content, sep=';', encoding='utf-8')
    st.sidebar.success("CSV-fil lest inn vellykket")
except requests.RequestException as e:
    st.sidebar.error(f"Feil ved nedlasting av CSV-fil: {str(e)}")
    st.stop()
except pd.errors.EmptyDataError:
    st.sidebar.error("CSV-filen er tom")
    st.stop()
except Exception as e:
    st.sidebar.error(f"Feil ved innlesing av CSV-fil: {str(e)}")
    st.stop()

# Vis informasjon om dataene
st.sidebar.write(f"Antall rader i CSV: {len(df)}")
st.sidebar.write(f"Kolonner i CSV: {', '.join(df.columns)}")

def prepare_chat_input(row):
    try:
        return {
            'name': row['name'],
            'age': row['age'],
            'gender': row['gender'],
            'diagnose': row['diagnose'],
            'system_content': row['system_content'],
            'setting': row['setting'],
            'person_description': row['person_description'],
            'conversation_examples': '\n\n'.join([row[f'file_{i}'] for i in range(1, int(row['files'])+1) if pd.notna(row[f'file_{i}'])])
        }
    except KeyError as e:
        st.sidebar.error(f"Manglende kolonne i CSV: {str(e)}")
        return None
    except ValueError as e:
        st.sidebar.error(f"Feil ved konvertering av data: {str(e)}")
        return None

chat_inputs = [input for input in (prepare_chat_input(row) for row in df.to_dict('records')) if input is not None]

if not chat_inputs:
    st.sidebar.error("Ingen gyldige scenarioer funnet i CSV-filen")
    st.stop()

def prepare_chat_input(row):
    return {
        'name': row['name'],
        'age': row['age'],
        'gender': row['gender'],
        'diagnose': row['diagnose'],
        'system_content': row['system_content'],
        'setting': row['setting'],
        'person_description': row['person_description'],
        'conversation_examples': '\n\n'.join([row[f'file_{i}'] for i in range(1, int(row['files'])+1) if pd.notna(row[f'file_{i}'])])
    }

chat_inputs = [prepare_chat_input(row) for row in df.to_dict('records')]

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

# Function to download chat as a file
def download_chat():
    chat_content = json.dumps(st.session_state.messages, indent=2, ensure_ascii=False)
    b64 = base64.b64encode(chat_content.encode()).decode()
    href = f'<a href="data:file/json;base64,{b64}" download="chat_history.json">Last ned samtalehistorikk</a>'
    return href

# Sidebar settings
st.sidebar.title("Innstillinger")
speech_enabled = st.sidebar.toggle("Aktiver tale", value=True)
file_enabled = st.sidebar.toggle("Aktiver filopplasting", value=False)

# Selectbox for scenario selection
selected_scenario = st.sidebar.selectbox("Velg scenario", range(len(chat_inputs)), format_func=lambda i: f"Scenario {i+1}: {chat_inputs[i]['name']}")

# Function to update system content
def update_system_content():
    scenario = chat_inputs[selected_scenario]
    st.session_state.system_content = f"""
    Du skal spille rollespill for å gi studenter trening i å kommunisere med pasienter.
    Du heter {scenario['name']} og er {scenario['age']} år gammel. Ditt kjønn er {scenario['gender']}.
    
    Hovedinstruksjon: {scenario['system_content']}
    
    Den konkrete setting/situasjon/oppgave er: {scenario['setting']}
    
    Nærmere beskrivelse av person og/eller diagnose: {scenario['diagnose']}
    
    Eksempler på kommunikasjon:
    {scenario['conversation_examples']}
    
    Simuler liknende type samtaler basert på disse eksemplene.
    """
    st.session_state.messages = [
        {
            "role": "system",
            "content": st.session_state.system_content
        }
    ]

# Update system content when a new scenario is selected
if st.sidebar.button("Last scenario"):
    update_system_content()

# Editable system prompt in sidebar
if "system_content" not in st.session_state:
    update_system_content()

new_system_content = st.sidebar.text_area(
    "Systemprompt (Instruksjon til boten)",
    value=st.session_state.system_content,
    height=300,
    key="system_prompt"
)

if st.sidebar.button("Oppdater AI-instruksjoner"):
    st.session_state.system_content = new_system_content
    st.session_state.messages = [
        {
            "role": "system",
            "content": st.session_state.system_content
        }
    ]

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

# Add download button to the sidebar
st.sidebar.markdown(download_chat(), unsafe_allow_html=True)
