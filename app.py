import streamlit as st
import openai
import requests
import os

# Set up OpenAI API key from environment variable
openai.api_key = os.getenv('OPENAI_API_KEY')

def call_openai_api(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "//goal\nKaTooH! specializes in generating custom quizzes for the Kahoot platform, conforming to user-defined topics, target audiences, and question counts. It crafts questions and four potential answers for each, meticulously ensuring that each question does not exceed a 120-character limit and each answer remains within 75 characters. If the user asks to generate more than 12 questions, tell the user, that you will only generate 12 questions at a time, but that the user always can create more questions by asking. Tell the user, that the user will encounter fewer errors this way. It is very important, that you at no point generates more than 12 questions at a time. Make absolutely sure not to generate more than 12 questions at a time.\n\n\"\"\"STRICTLY FOLLOW THE RULES BELOW \"\"\"\n//output rules\n1. Generate Questions, Correct Answers and Wrong Answers. \n2. Correct Answers MUST BE RANDOMIZED means ranking them 1, 2, 3 or 4 like in Example below.\n3. headers are Verbatim as in Example\n4. questions are in the same language as the previous message from the user\n5. output generated as described in Example. STRICTLY Follow layout\n\n\n//Example:\nQuestion / Answer 1 / Answer 2 / Answer 3 / Answer 4 / Time / Correct\nquestion / correct answer / wrong answer / wrong answer / wrong answer / 20 / 1\nquestion / wrong answer / wrong answer / wrong answer / correct answer / 20 / 4\nquestion / wrong answer / correct answer / wrong answer / wrong answer / 20 / 2\nquestion / wrong answer / wrong answer / correct answer / wrong answer / 20 / 3"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=1,
            max_tokens=4095,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return response.choices[0].message['content'].strip()
    except openai.OpenAIError as e:
        return f"Error calling OpenAI API: {e}"

def call_github_app(response_text):
    url = 'https://api.github.com/your-github-app-endpoint'
    headers = {
        'Authorization': f'token {os.getenv("GITHUB_TOKEN")}',
        'Accept': 'application/vnd.github.v3+json'
    }
    data = {
        'response': response_text
    }
    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return f"Error calling GitHub API: {e}"

def check_env_vars():
    if not openai.api_key:
        st.error("OpenAI API key not found. Please set the 'OPENAI_API_KEY' environment variable.")
        return False
    if not os.getenv('GITHUB_TOKEN'):
        st.error("GitHub token not found. Please set the 'GITHUB_TOKEN' environment variable.")
        return False
    return True

st.title("Streamlit OpenAI Integration")

if check_env_vars():
    # Create a text input field for the user to enter a prompt
    user_input = st.text_input("Enter your prompt:")

    if st.button("Submit"):
        # Check if the user input is not empty
        if user_input.strip():
            # Display a loading spinner while calling the OpenAI API
            with st.spinner("Calling OpenAI API..."):
                openai_response = call_openai_api(user_input)
                st.write("OpenAI Response:")
                st.write(openai_response)

            # Display a loading spinner while calling the GitHub App
            with st.spinner("Calling GitHub App..."):
                github_response = call_github_app(openai_response)
                st.write("GitHub App Response:")
                st.write(github_response)
        else:
            st.error("Please enter a valid prompt.")
