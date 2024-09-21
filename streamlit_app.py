import streamlit as st
import openai

# Set up the OpenAI client to use Azure OpenAI services
openai.api_type = "azure"
openai.api_base = st.secrets["OPENAI_API_BASE"]         # Your Azure OpenAI Endpoint
openai.api_version = st.secrets["OPENAI_API_VERSION"]   # API version
openai.api_key = st.secrets["OPENAI_API_KEY"]           # API key

# Show title and description.
st.title("💬 SimSamBot")
st.write(
    "Prototype for intern testing"
)

# Create a session state variable to store the chat messages.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the existing chat messages using st.chat_message.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field to allow the user to enter a message.
if prompt := st.chat_input("What is up?"):

    # Store and display the user's message.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate a response using the Azure OpenAI API.
    response = openai.ChatCompletion.create(
        engine=st.secrets["OPENAI_DEPLOYMENT_NAME"],  # Uses your assistant ID
        messages=st.session_state.messages,
        temperature=0.7,
        max_tokens=500,
        stream=True,
    )

    # Stream the response and store it in session state.
    with st.chat_message("assistant"):
        response_text = st.empty()
        full_response = ""
        for chunk in response:
            chunk_message = chunk['choices'][0]['delta'].get('content', '')
            full_response += chunk_message
            response_text.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
