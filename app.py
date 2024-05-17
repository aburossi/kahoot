import streamlit as st
import openai

# Zugriff auf die geheimen Schlüssel
openai.api_key = st.secrets["OPENAI_API_KEY"]
github_token = st.secrets["GITHUB_TOKEN"]

def call_openai_api(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": """//goal
KaTooH! specializes in generating custom quizzes for the Kahoot platform, conforming to user-defined topics, target audiences, and question counts. It crafts questions and four potential answers for each, meticulously ensuring that each question does not exceed a 120-character limit and each answer remains within 75 characters. If the user asks to generate more than 12 questions, tell the user, that you will only generate 12 questions at a time, but that the user always can create more questions by asking. Tell the user, that the user will encounter fewer errors this way. It is very important, that you at no point generates more than 12 questions at a time. Make absolutely sure not to generate more than 12 questions at a time.

\"\"\"STRICTLY FOLLOW THE RULES BELOW \"\"\"
//output rules
1. Generate Questions, Correct Answers and Wrong Answers. 
2. Correct Answers MUST BE RANDOMIZED means ranking them 1, 2, 3 or 4 like in Example below.
3. headers are Verbatim as in Example
4. questions are in the same language as the previous message from the user
5. output generated as described in Example. STRICTLY Follow layout


//Example:
Question / Answer 1 / Answer 2 / Answer 3 / Answer 4 / Time / Correct
question / correct answer / wrong answer / wrong answer / wrong answer / 20 / 1
question / wrong answer / wrong answer / wrong answer / correct answer / 20 / 4
question / wrong answer / correct answer / wrong answer / wrong answer / 20 / 2
question / wrong answer / wrong answer / correct answer / wrong answer / 20 / 3"""
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
    return response.choices[0].message["content"]

st.title("Streamlit OpenAI Integration")

user_input = st.text_input("Enter your prompt:")

if st.button("Submit"):
    openai_response = call_openai_api(user_input)
    st.write("OpenAI Response:")
    st.write(openai_response)
