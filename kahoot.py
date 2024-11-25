import streamlit as st
from openai import OpenAI
import json
import random
import pandas as pd
import openpyxl
import re
from io import BytesIO, StringIO
from PIL import Image
import base64
import PyPDF2
from pdf2image import convert_from_bytes

# Helper function to save quiz data to Excel
def save_to_excel(quiz_data):
    output = BytesIO()
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

    wb.save(output)
    output.seek(0)
    return output

# Function to process uploaded images and prepare for API
def process_image(image_file):
    """Convert an image to base64 for OpenAI API"""
    img = Image.open(image_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    max_size = 1000
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    return base64.b64encode(img_byte_arr).decode('utf-8')

# Function to extract text from PDFs
def extract_text_from_pdf(file):
    """Extract text from PDF"""
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text
    return text.strip()

# Function to convert PDF to images
def convert_pdf_to_images(file):
    """Convert PDF pages to images"""
    images = convert_from_bytes(file.read())
    return images

# Function to extract text from DOCX files
def extract_text_from_docx(file):
    """Extract text from DOCX"""
    from docx import Document
    doc = Document(file)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.strip()

def validate_and_fix_json(generated_quiz):
    """Validate and fix JSON output from OpenAI."""
    try:
        # Attempt to parse the raw JSON directly
        return json.loads(generated_quiz)
    except json.JSONDecodeError:
        st.warning("Error parsing JSON. Attempting to extract valid snippets.")

        # Remove invalid characters and attempt to fix common issues
        fixed_json = re.sub(r',\s*]', ']', generated_quiz)  # Fix trailing commas
        fixed_json = re.sub(r',\s*}', '}', fixed_json)  # Fix trailing commas in objects
        fixed_json = re.sub(r'(?<=\})\s*,\s*(?=\})', '', fixed_json)  # Remove commas between objects
        fixed_json = fixed_json.strip()

        # Extract valid JSON objects using regex
        pattern = r'\{\s*"question":\s*".+?",\s*"answers":\s*\[.+?\]\s*\}'
        valid_snippets = re.findall(pattern, fixed_json)

        if valid_snippets:
            st.info(f"Extracted {len(valid_snippets)} valid questions from the response.")
            try:
                # Rebuild the JSON array from valid snippets
                valid_json = "[" + ",".join(valid_snippets) + "]"
                return json.loads(valid_json)
            except json.JSONDecodeError:
                st.error("Failed to parse extracted JSON snippets.")
        else:
            st.error("No valid JSON objects found in the response.")

        # Display raw response for debugging
        st.error("Original response could not be parsed:")
        st.code(generated_quiz, language="json")

        return []

# Function to generate quiz from OpenAI response
def generate_quiz(api_key, input_text, num_questions, model):
    client = OpenAI(api_key=api_key)

    prompt = f"""
    Create a quiz based on the given text. 
    Generate {num_questions} questions, each with four possible answers, one of which is correct.
    Format the output as a JSON array. Ensure each answer text is concise and suitable for Kahoot.
    Text: {input_text}
    """

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are specialized in generating Kahoot quizzes."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
        )
        raw_response = response.choices[0].message.content
        st.text_area("Raw Response from OpenAI", raw_response, height=300)  # Display raw response for debugging
        return raw_response
    except Exception as e:
        st.error(f"Error generating quiz: {e}")
        return None


# Streamlit UI
st.title("Quiz Generator with File Uploads")

api_key = st.text_input("OpenAI API Key", type="password")
uploaded_file = st.file_uploader("Upload a PDF, DOCX, or Image", type=["pdf", "docx", "jpg", "jpeg", "png"])

text_content = None
image_base64 = None

if uploaded_file:
    if uploaded_file.type == "application/pdf":
        text_content = extract_text_from_pdf(uploaded_file)
        if not text_content:
            images = convert_pdf_to_images(uploaded_file)
            st.image(images, caption="PDF pages as images", use_column_width=True)
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        text_content = extract_text_from_docx(uploaded_file)
    elif uploaded_file.type.startswith("image/"):
        image_base64 = process_image(uploaded_file)

if text_content:
    st.text_area("Extracted Text", text_content)
elif image_base64:
    st.success("Image processed for API input.")

num_questions = st.number_input("Number of Questions", min_value=1, max_value=12, value=5)
model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini"])

if st.button("Generate Quiz"):
    if not api_key:
        st.error("Please enter your OpenAI API Key")
    elif not (text_content or image_base64):
        st.error("Please upload a file or provide input text.")
    else:
        input_data = text_content or f"Image input: {image_base64}"
        quiz_json = generate_quiz(api_key, input_data, num_questions, model)
        quiz_data = validate_and_fix_json(quiz_json)

        if quiz_data:
            st.session_state["quiz_data"] = quiz_data
            excel_data = save_to_excel(quiz_data)
            st.download_button("Download Quiz as Excel", data=excel_data, file_name="quiz.xlsx")
