import streamlit as st
from openai import AzureOpenAI

# Create an AzureOpenAI client
client = AzureOpenAI(
    azure_endpoint=st.secrets["OPENAI_API_BASE"],         # Your Azure OpenAI Endpoint
    api_version=st.secrets["OPENAI_API_VERSION"],         # API version
    api_key=st.secrets["OPENAI_API_KEY"],                 # API key
)

# Show title and description.
st.title("💬 SimSamBot")
st.write(
    "Prototype til intern testing"
)

# Create a session state variable to store the chat messages.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the existing chat messages using st.chat_message.
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field to allow the user to enter a message.
if prompt := st.chat_input("Hei tannlege?"):

    # Store and display the user's message.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate a response using the Azure OpenAI API.
    response = client.chat.completions.create(
        model=st.secrets["OPENAI_DEPLOYMENT_NAME"],  # Use your deployment name as the model
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
            chunk_message = chunk.choices[0].delta.get('content', '')
            full_response += chunk_message
            response_text.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
