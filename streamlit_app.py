import streamlit as st
from openai import AzureOpenAI
import os

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
    # Include the assistant's instructions as a system prompt
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
    # Read file contents based on file type
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

    # Display file contents (optional)
    st.text_area("Innhold i filen:", file_contents, height=200)

    # Include the file contents in the conversation as a system message
    st.session_state.messages.append({
        "role": "system",
        "content": f"Samtaleeksempler:\n{file_contents}"
    })
    st.session_state.file_contents = file_contents  # To prevent re-adding the content

# Display the existing chat messages
for message in st.session_state.messages:
    if message["role"] == "system":
        continue  # Do not display system messages to the user
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Create a chat input field to allow the user to enter a message.
if prompt := st.chat_input("Hva vil du si til pasienten?"):

    # Store and display the user's message.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # Generate a response using the Azure OpenAI API.
        response = client.chat.completions.create(
            model=st.secrets["OPENAI_DEPLOYMENT_NAME"],  # Use your deployment name as the model
            messages=st.session_state.messages,
            temperature=1,
            top_p=1,
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
    except Exception as e:
        st.error(f"An error occurred: {e}")
