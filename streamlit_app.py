import pandas as pd
import streamlit as st
from urllib.request import urlopen
from io import StringIO
import openai

# URL to raw CSV content
csv_url = 'https://raw.githubusercontent.com/geraldOslo/VirtualPatientTest/main/data/skybert.csv'

st.set_page_config(page_title="Virtual Patient Simulator", page_icon="🦷", layout="wide")

# Sidebar
st.sidebar.title("Virtual Patient Simulator")
api_key = st.sidebar.text_input("Enter your API key", type="password")

# Read CSV file and prepare data
try:
    with urlopen(csv_url) as response:
        csv_content = StringIO(response.read().decode())
    df = pd.read_csv(csv_content, sep=';', encoding='utf-8')
    st.sidebar.success("CSV file read successfully")
except Exception as e:
    st.sidebar.error(f"Error reading CSV file: {str(e)}")
    st.stop()

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
    except Exception as e:
        st.sidebar.error(f"Error preparing chat input: {str(e)}")
        return None

chat_inputs = [input for input in (prepare_chat_input(row) for row in df.to_dict('records')) if input is not None]

if not chat_inputs:
    st.sidebar.error("No valid scenarios found in the CSV file")
    st.stop()

# Select a scenario
selected_scenario = st.sidebar.selectbox("Select a scenario", [f"{input['name']} ({input['age']})" for input in chat_inputs])
selected_input = next(input for input in chat_inputs if f"{input['name']} ({input['age']})" == selected_scenario)

# Main content
st.title(f"Virtual Patient: {selected_input['name']}")
st.write(f"Age: {selected_input['age']}, Gender: {selected_input['gender']}")
st.write(f"Diagnosis: {selected_input['diagnose']}")
st.write(f"Setting: {selected_input['setting']}")
st.write("Person Description:")
st.write(selected_input['person_description'])

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What do you want to ask the patient?"):
    if not api_key:
        st.error("Please enter an API key in the sidebar")
    else:
        openai.api_key = api_key
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        full_response = ""
        message_placeholder = st.empty()
        for response in openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": selected_input['system_content']},
                {"role": "system", "content": selected_input['conversation_examples']},
                *[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
            ],
            stream=True,
        ):
            full_response += response.choices[0].delta.get("content", "")
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Reset button
if st.button("Reset Conversation"):
    st.session_state.messages = []
    st.experimental_rerun()
