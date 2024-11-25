import streamlit as st
from openai import OpenAI
import json
import random
import pandas as pd
import openpyxl
import PyPDF2
import docx
from pdf2image import convert_from_bytes
from PIL import Image
import io
from tiktoken import encoding_for_model  # For token counting
import re
from io import BytesIO, StringIO

# Helper Functions
def save_to_excel(quiz_data):
    output = BytesIO()
    wb = openpyxl.Workbook()
    sheet = wb.active
    header = ["Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Time", "Correct"]
    sheet.append(header)
    for question in quiz_data:
        answers = question['answers']
        random.shuffle(answers)
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
            "20",
            correct_index + 1
        ]
        sheet.append(row)
    wb.save(output)
    output.seek(0)
    return output

def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text.strip()

def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)

def convert_pdf_to_images(file):
    return convert_from_bytes(file.read())

def process_image(image):
    img = Image.open(image)
    text = f"Extracted image content from {image.name}"  # Replace with actual OCR if necessary
    return text

def count_tokens(text, model_name):
    enc = encoding_for_model(model_name)
    return len(enc.encode(text))

def generate_quiz_prompt(text, num_questions, learning_objectives, audience):
    return f"""
    Create a quiz based on the following input:
    Text or topic: {text}
    - Number of questions: {num_questions}
    - Learning Objectives: {learning_objectives}
    - Audience: {audience}
    Ensure:
    1. JSON format with question and answers.
    2. Each question max 120 characters.
    3. Each answer max 75 characters.
    """

def process_uploaded_file(file):
    file_type = file.type
    if file_type == "application/pdf":
        text = extract_text_from_pdf(file)
        if not text:
            st.warning("No text extracted from the PDF. Trying image processing.")
            images = convert_pdf_to_images(file)
            return "Image content from PDF", images
        return text, None
    elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_text_from_docx(file), None
    elif file_type.startswith("image/"):
        return process_image(file), None
    else:
        st.error("Unsupported file type.")
        return None, None

# Streamlit UI
st.title("Enhanced Quiz Generator")

api_key = st.text_input("OpenAI API Key:", type="password")

uploaded_file = st.file_uploader("Upload a file (PDF, DOCX, or Image)", type=["pdf", "docx", "jpg", "jpeg", "png"])
text_input = st.text_area("Or paste your text here:")
learning_objectives = st.text_input("Learning Objectives:")
audience = st.text_input("Audience:")
num_questions = st.selectbox("Number of questions:", [str(i) for i in range(1, 13)])
model_options = {"gpt-4o-mini": "gpt-4o-mini", "gpt-4o": "gpt-4o"}
selected_model = st.selectbox("Select GPT Model:", list(model_options.keys()))

if st.button("Generate Quiz"):
    if not api_key:
        st.error("API Key is required.")
    else:
        text = text_input.strip()
        if uploaded_file:
            text, images = process_uploaded_file(uploaded_file)
            if not text and not images:
                st.error("Could not process the uploaded file.")
                st.stop()
        if not text:
            st.error("No valid input provided.")
            st.stop()
        
        client = OpenAI(api_key=api_key)
        prompt = generate_quiz_prompt(text, num_questions, learning_objectives, audience)
        input_tokens = count_tokens(prompt, selected_model)
        max_tokens = 4095 if selected_model == "gpt-4o-mini" else 16000
        available_tokens = max_tokens - input_tokens - 100
        
        response = client.chat.completions.create(
            model=model_options[selected_model],
            messages=[{"role": "system", "content": "Generate a Kahoot quiz."}, {"role": "user", "content": prompt}],
            max_tokens=available_tokens
        )
        
        try:
            quiz_data = json.loads(response.choices[0].message.content)
            excel_data = save_to_excel(quiz_data)
            st.download_button(
                label="Download Quiz as Excel",
                data=excel_data,
                file_name="quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"Error processing quiz data: {e}")
