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

# Set page config
st.set_page_config(page_title="Kahoot Quiz Generator", page_icon="🧠", layout="wide")

# Sidebar for instructions and settings
with st.sidebar:
    st.title("Instructions")
    with st.expander("How to Get an API Key"):
        st.write("1. Go to [OpenAI website](https://www.openai.com) and register/login.")
        st.write("2. Navigate to API settings.")
        st.write("3. Create a new API key.")
        st.write("4. Copy and securely store the key.")
    
    with st.expander("Best Practices"):
        st.write("1. Use clear, concise topics.")
        st.write("2. Specify desired question count.")
        st.write("3. Review and edit generated questions.")
        st.write("4. Be aware of model limitations.")
        st.write("5. For longer texts, generate multiple sets of questions.")
    
    # Language selection
    language = st.radio("Select Language / Wählen Sie die Sprache", ["English", "Deutsch"])

# Main content
st.title("Kahoot Quiz Generator 🧠")

# Input fields
api_key = st.text_input("OpenAI API Key:", type="password", help="Enter your OpenAI API key here")

col1, col2 = st.columns(2)
with col1:
    uploaded_file = st.file_uploader("Upload an image (optional)", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption='Uploaded Image', use_column_width=True)

with col2:
    text_input = st.text_area("Enter your text or topic:", height=150)
    learning_objectives = st.text_input("Learning Objectives:")
    audience = st.text_input("Audience:")

num_questions = st.slider("Number of questions:", min_value=1, max_value=20, value=10)

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
    
    prompt = "Create a quiz based on the given text/topic and image (if provided). " \
             f"Generate {num_questions} questions, each with four answers. " \
             "Questions must not exceed 120 characters. " \
             "Answers must not exceed 75 characters. " \
             f"Learning Objectives: {learning_objectives} " \
             f"Audience: {audience} " \
             f"Text/Topic: {text_input}"

    if language == "Deutsch":
        prompt = f"Erstellen Sie ein Quiz basierend auf dem gegebenen Text/Thema und Bild (falls vorhanden). " \
                 f"Generieren Sie {num_questions} Fragen, jede mit vier Antworten. " \
                 f"Fragen dürfen 120 Zeichen nicht überschreiten. " \
                 f"Antworten dürfen 75 Zeichen nicht überschreiten. " \
                 f"Lernziele: {learning_objectives} " \
                 f"Zielgruppe: {audience} " \
                 f"Text/Thema: {text_input}"

    messages = [
        {"role": "system", "content": "You are a quiz generator for Kahoot."},
        {"role": "user", "content": prompt}
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
        with st.spinner('Generating quiz...'):
            response = client.chat.completions.create(
                model=selected_model,
                messages=messages,
                temperature=0.7,
                max_tokens=get_max_tokens(selected_model) - count_tokens(prompt, selected_model) - 100,
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

    except json.JSONDecodeError:
        st.error("Failed to parse the generated quiz. Please try again.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

if st.button("Generate Quiz"):
    generate_quiz()

if "quiz_data" in st.session_state:
    st.write("Edit Quiz Data:")
    updated_quiz = []
    for idx, question in enumerate(st.session_state["quiz_data"]):
        with st.expander(f"Question {idx+1}"):
            question_text = st.text_input("Question", value=question["question"], key=f"q_{idx}")
            st.markdown(f'<p style="color:{"red" if len(question_text) > 120 else "green"};">Characters: {len(question_text)}/120</p>', unsafe_allow_html=True)
            
            answers = []
            for ans_idx, answer in enumerate(question["answers"]):
                answer_text = st.text_input(f"Answer {ans_idx+1}", value=answer["text"], key=f"a_{idx}_{ans_idx}")
                st.markdown(f'<p style="color:{"red" if len(answer_text) > 75 else "green"};">Characters: {len(answer_text)}/75</p>', unsafe_allow_html=True)
                is_correct = st.checkbox("Correct", value=answer["is_correct"], key=f"c_{idx}_{ans_idx}")
                answers.append({"text": answer_text, "is_correct": is_correct})
            
            updated_quiz.append({"question": question_text, "answers": answers})

    if st.button("Update Quiz"):
        excel_buffer = save_to_excel(updated_quiz)
        if excel_buffer:
            st.download_button(
                label="Download Updated Quiz",
                data=excel_buffer,
                file_name="updated_kahoot_quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    with st.expander("Next Steps"):
        st.write("1. Download the Excel file.")
        st.write("2. Create a new Kahoot quiz.")
        st.write("3. Use Kahoot's import function to upload the Excel file.")

# Footer
st.markdown("---")
st.markdown("Created with ❤️ by Your Name/Company")
