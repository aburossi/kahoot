import streamlit as st
import openai
import json
import random
import pandas as pd
import openpyxl

# Helper function to save quiz data to Excel
def save_to_excel(quiz_data, file_name):
    wb = openpyxl.Workbook()
    sheet = wb.active

    header = ["Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Time", "Correct"]
    sheet.append(header)

    for question in quiz_data:
        answers = question['answers']
        random.shuffle(answers)  # Randomize the order of answers
        correct_index = next((i for i, ans in enumerate(answers) if ans['is_correct']), None)

        if correct_index is None:
            st.error("No correct answer specified for a question.")
            return

        row = [
            question['question'],
            answers[0]['text'],
            answers[1]['text'],
            answers[2]['text'],
            answers[3]['text'],
            "20",  # Default time
            correct_index + 1  # +1 because Excel is 1-indexed
        ]
        sheet.append(row)

    wb.save(file_name)

# Streamlit app
st.title("Kahoot Quiz Generator")

# API Key input
api_key = st.text_input("OpenAI API Key:", type="password")

# Text input
text_input = st.text_area("Enter your text or topic:")

# Learning Objectives input
learning_objectives = st.text_input("Learning Objectives:")

# Audience input
audience = st.text_input("Audience:")

# Number of questions dropdown
num_questions = st.selectbox("Number of questions:", [str(i) for i in range(0, 13)])

# GPT Model selection dropdown
model_options = {
    "gpt-4o-mini (Cheapest & Fastest)": "gpt-4o-mini",
    "gpt-4o": "gpt-4",
    "gpt-4-turbo (Best & Most Expensive)": "gpt-4-turbo"
}
selected_model = st.selectbox("Select GPT Model:", list(model_options.keys()))

def generate_quiz():
    text = text_input.strip()
    num_questions_selected = num_questions
    learning_objectives_selected = learning_objectives.strip()
    audience_selected = audience.strip()
    selected_model = model_options[selected_model]
    
    if not api_key:
        st.error("API Key cannot be empty")
        return

    openai.api_key = api_key
    
    try:
        response = openai.ChatCompletion.create(
            model=selected_model,
            messages=[
                {
                    "role": "system",
                    "content": f"""
                        You are specialized in generating custom quizzes for the Kahoot platform. 
                        Your task is to create a quiz based on the given text or topic. 
                        Create questions and four potential answers for each question. 
                        Ensure that each question does not exceed 120 characters 
                        VERY IMPORTANT: Ensure each answer remains within 75 characters. 
                        Follow these rules strictly:
                        1. Generate questions about the provided text or topic.
                        2. Create questions and answers in the same language as the input text.
                        3. Provide output in the specified JSON format.
                        4. Generate exactly {num_questions_selected} questions.
                        5. Learning Objectives: {learning_objectives_selected}
                        6. Audience: {audience_selected}
                        JSON format:
                        [
                        {{
                            "question": "Your question here max 120 characters",
                            "answers": [
                            {{
                                "text": "Answer 1 max 75 characters",
                                "is_correct": false
                            }},
                            {{
                                "text": "Answer 2 max 75 characters",
                                "is_correct": false
                            }},
                            {{
                                "text": "Answer 3 max 75 characters",
                                "is_correct": false
                            }},
                            {{
                                "text": "Answer 4 max 75 characters",
                                "is_correct": false
                            }}
                            ]
                        }},
                        ... (repeat for all questions)
                        ]
                    """
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.9,
            max_tokens=4095,
            top_p=0.9,
            frequency_penalty=0,
            presence_penalty=0
        )

        generated_quiz = response.choices[0].message.content
        
        try:
            quiz_data = json.loads(generated_quiz)
            st.session_state["quiz_data"] = quiz_data
        except json.JSONDecodeError as json_error:
            st.error(f"Error parsing JSON: {str(json_error)}\n\nRaw response:\n{generated_quiz}")
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Generate button
if st.button("Generate Quiz"):
    generate_quiz()

# Edit and Save Quiz Data
if "quiz_data" in st.session_state:
    quiz_data = st.session_state["quiz_data"]

    st.write("Edit Quiz Data:")
    for idx, question in enumerate(quiz_data):
        st.text_input(f"Question {idx+1}", value=question["question"], key=f"question_{idx}")
        for answer_idx, answer in enumerate(question["answers"]):
            st.text_input(f"Answer {idx+1}-{answer_idx+1}", value=answer["text"], key=f"answer_{idx}_{answer_idx}")
            st.checkbox(f"Correct Answer {idx+1}-{answer_idx+1}", value=answer["is_correct"], key=f"correct_{idx}_{answer_idx}")

    if st.button("Save as JSON"):
        file_name = st.text_input("Enter file name for JSON:", value="quiz.json")
        quiz_data = [
            {
                "question": st.session_state[f"question_{idx}"],
                "answers": [
                    {
                        "text": st.session_state[f"answer_{idx}_{answer_idx}"],
                        "is_correct": st.session_state[f"correct_{idx}_{answer_idx}"]
                    } for answer_idx in range(4)
                ]
            } for idx in range(len(quiz_data))
        ]
        with open(file_name, 'w') as json_file:
            json.dump(quiz_data, json_file, indent=4)
        st.success(f"Quiz saved to {file_name}")

    if st.button("Save as Excel"):
        file_name = st.text_input("Enter file name for Excel:", value="quiz.xlsx")
        quiz_data = [
            {
                "question": st.session_state[f"question_{idx}"],
                "answers": [
                    {
                        "text": st.session_state[f"answer_{idx}_{answer_idx}"],
                        "is_correct": st.session_state[f"correct_{idx}_{answer_idx}"]
                    } for answer_idx in range(4)
                ]
            } for idx in range(len(quiz_data))
        ]
        save_to_excel(quiz_data, file_name)
        st.success(f"Quiz saved to {file_name}")
