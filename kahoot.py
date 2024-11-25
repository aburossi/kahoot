import streamlit as st
from openai import OpenAI
import json
import random
import openpyxl
import re
from io import BytesIO
from tiktoken import encoding_for_model
from PIL import Image
import base64

# Helper function to save quiz data to Excel
def save_to_excel(quiz_data):
    output = BytesIO()
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Time", "Correct"])
    for question in quiz_data:
        answers = question['answers']
        random.shuffle(answers)
        correct_index = next((i for i, ans in enumerate(answers) if ans['is_correct']), None)
        if correct_index is None:
            st.error("No correct answer specified for a question.")
            return None
        row = [question['question']] + [ans['text'] for ans in answers] + ["20", correct_index + 1]
        sheet.append(row)
    wb.save(output)
    output.seek(0)
    return output

# Function to count tokens
def count_tokens(text, model_name):
    enc = encoding_for_model(model_name)
    return len(enc.encode(text))

# Function to process image
def process_image(image):
    img = Image.open(image)
    max_size = 1000
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    if img.mode != 'RGB':
        img = img.convert('RGB')
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

# Function to get max tokens for each model
def get_max_tokens(model):
    return {"gpt-4o-mini": 16383, "gpt-4o": 16000, "gpt-4-turbo-preview": 4095}.get(model, 4095)

st.title("Kahoot Quiz Generator")

# Instructions (in expandable sections)
with st.expander("How to Get an API Key from OpenAI"):
    st.write("1. Go to [OpenAI website](https://www.openai.com) and register/login.\n2. Navigate to API settings.\n3. Create a new API key.\n4. Copy and securely store the key.")

with st.expander("Best Practices for Using This App"):
    st.write("1. Use clear, concise topics.\n2. Specify desired question count.\n3. Review and edit generated questions.\n4. Be aware of model limitations.\n5. For longer texts, generate multiple sets of questions.")

# Input fields
api_key = st.text_input("OpenAI API Key:", type="password")
uploaded_file = st.file_uploader("Upload an image (optional)", type=["jpg", "jpeg", "png"])
if uploaded_file:
    with st.expander("View Uploaded Image", expanded=False):
        st.image(uploaded_file, caption='Uploaded Image', use_column_width=True)

text_input = st.text_area("Enter your text or topic:")
learning_objectives = st.text_input("Learning Objectives:")
audience = st.text_input("Audience:")
num_questions = st.selectbox("Number of questions:", [str(i) for i in range(1, 13)])
model_options = {
    "gpt-4o-mini (Cheapest & Fastest)": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gpt-4-turbo-preview (Best & Most Expensive)": "gpt-4-turbo-preview"
}
selected_model = model_options[st.selectbox("Select GPT Model:", list(model_options.keys()))]

def generate_quiz():
    if not api_key:
        st.error("API Key cannot be empty")
        return

    client = OpenAI(api_key=api_key)
    image_content = process_image(uploaded_file) if uploaded_file else None
    
    input_text = f"""
    Create a quiz based on the given text/topic and image (if provided). 
    Generate {num_questions} questions, each with four answers. 
    Questions must not exceed 120 characters. 
    Answers must not exceed 75 characters.
    Learning Objectives: {learning_objectives}
    Audience: {audience}
    Text/Topic: {text_input}
    
    Provide output in this JSON format:
    [
        {{
            "question": "Question text",
            "answers": [
                {{"text": "Answer 1", "is_correct": false}},
                {{"text": "Answer 2", "is_correct": false}},
                {{"text": "Answer 3", "is_correct": false}},
                {{"text": "Answer 4", "is_correct": true}}
            ]
        }}
    ]
    """

    messages = [
        {"role": "system", "content": "You are a quiz generator for Kahoot."},
        {"role": "user", "content": input_text}
    ]
    if image_content:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Consider this image:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_content}"}}
            ]
        })

    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=0.7,
            max_tokens=get_max_tokens(selected_model) - count_tokens(input_text, selected_model) - 100,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        quiz_data = json.loads(response.choices[0].message.content.strip())
        st.success(f"Successfully generated {len(quiz_data)} questions.")
        
        excel_buffer = save_to_excel(quiz_data)
        if excel_buffer:
            st.download_button(
                label="Download Quiz as Excel",
                data=excel_buffer,
                file_name="kahoot_quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        st.session_state["quiz_data"] = quiz_data

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if st.button("Generate Quiz"):
    generate_quiz()

if "quiz_data" in st.session_state:
    st.write("Edit Quiz Data:")
    for idx, question in enumerate(st.session_state["quiz_data"]):
        question_text = st.text_input(f"Question {idx+1}", value=question["question"], key=f"q_{idx}")
        st.markdown(f'<p style="color:{"red" if len(question_text) > 120 else "green"};">Characters: {len(question_text)}/120</p>', unsafe_allow_html=True)
        
        for ans_idx, answer in enumerate(question["answers"]):
            answer_text = st.text_input(f"Answer {idx+1}-{ans_idx+1}", value=answer["text"], key=f"a_{idx}_{ans_idx}")
            st.markdown(f'<p style="color:{"red" if len(answer_text) > 75 else "green"};">Characters: {len(answer_text)}/75</p>', unsafe_allow_html=True)
            st.checkbox("Correct", value=answer["is_correct"], key=f"c_{idx}_{ans_idx}")

    if st.button("Update Quiz"):
        updated_quiz = [
            {
                "question": st.session_state[f"q_{idx}"],
                "answers": [
                    {
                        "text": st.session_state[f"a_{idx}_{ans_idx}"],
                        "is_correct": st.session_state[f"c_{idx}_{ans_idx}"]
                    } for ans_idx in range(4)
                ]
            } for idx in range(len(st.session_state["quiz_data"]))
        ]
        excel_buffer = save_to_excel(updated_quiz)
        if excel_buffer:
            st.download_button(
                label="Download Updated Quiz",
                data=excel_buffer,
                file_name="updated_kahoot_quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with st.expander("Next Steps"):
        st.write("1. Download the Excel file.\n2. Create a new Kahoot quiz.\n3. Use Kahoot's import function to upload the Excel file.")
