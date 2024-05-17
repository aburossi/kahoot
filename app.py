import streamlit as st
import openai
import requests
import os

# Set up OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

def call_openai_api(prompt):
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=150
    )
    return response.choices[0].text.strip()

def call_github_app(response_text):
    url = 'https://api.github.com/your-github-app-endpoint'
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {
        'response': response_text
    }
    response = requests.post(url, json=data, headers=headers)
    return response.json()

st.title("Streamlit OpenAI Integration")

user_input = st.text_input("Enter your prompt:")

if st.button("Submit"):
    openai_response = call_openai_api(user_input)
    st.write("OpenAI Response:")
    st.write(openai_response)

    github_response = call_github_app(openai_response)
    st.write("GitHub App Response:")
    st.write(github_response)
