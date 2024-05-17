import streamlit as st
import pandas as pd
from io import StringIO, BytesIO
from openai import OpenAI

# Function to convert DataFrame to Excel
def convert_df_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# Function to send user input to OpenAI and get the response
def get_openai_response(user_input):
    client = OpenAI()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "//goal\nKaTooH! specializes in generating custom quizzes for the Kahoot platform, conforming to user-defined topics, target audiences, and question counts. It crafts questions and four potential answers for each, meticulously ensuring that each question does not exceed a 120-character limit and each answer remains within 75 characters. If the user asks to generate more than 12 questions, tell the user, that you will only generate 12 questions at a time, but that the user always can create more questions by asking. Tell the user, that the user will encounter fewer errors this way. It is very important, that you at no point generates more than 12 questions at a time. Make absolutely sure not to generate more than 12 questions at a time.\n\n\"\"\"STRICTLY FOLLOW THE RULES BELOW \"\"\"\n//output rules\n1. Generate Questions, Correct Answers and Wrong Answers. \n2. Correct Answers MUST BE RANDOMIZED means ranking them 1, 2, 3 or 4 like in Example below.\n3. headers are Verbatim as in Example\n4. questions are in the same language as the previous message from the user\n5. output generated as described in Example. STRICTLY Follow layout\n\n\n//Example:\nQuestion / Answer 1 / Answer 2 / Answer 3 / Answer 4 / Time / Correct\nquestion / correct answer / wrong answer / wrong answer / wrong answer / 20 / 1\nquestion / wrong answer / wrong answer / wrong answer / correct answer / 20 / 4\nquestion / wrong answer / correct answer / wrong answer / wrong answer / 20 / 2\nquestion / wrong answer / wrong answer / correct answer / wrong answer / 20 / 3"
                    }
                ]
            },
            {
                "role": "user",
                "content": user_input
            }
        ],
        temperature=1,
        max_tokens=4095,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0
    )
    return response.choices[0].message.content

# Streamlit UI
st.title("KaTooH! - Kahoot Quiz Generator")

st.write("Enter your quiz topic, target audience, and the number of questions you want to generate.")
user_input = st.text_area("Input your quiz details here:", height=200)

if st.button("Generate Quiz and Download Excel"):
    try:
        # Get the response from OpenAI
        openai_response = get_openai_response(user_input)
        
        # Read the CSV data from the OpenAI response
        df = pd.read_csv(StringIO(openai_response), sep=' / ', engine='python')
        
        st.write("Here is a preview of your generated quiz:")
        st.write(df)
        
        excel_data = convert_df_to_excel(df)
        st.download_button(
            label="Download Excel",
            data=excel_data,
            file_name="kahoot_quiz.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"An error occurred: {e}")
