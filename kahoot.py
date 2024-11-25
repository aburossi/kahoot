import streamlit as st
import PyPDF2
import docx
from PIL import Image
from io import BytesIO
import openpyxl
import random
import logging
import json

logging.basicConfig(level=logging.INFO)

def save_to_excel(quiz_data):
    """Saves quiz data to an Excel file."""
    output = BytesIO()
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Time", "Correct"])
    for question in quiz_data:
        answers = question["answers"]
        random.shuffle(answers)
        correct_index = next((i for i, ans in enumerate(answers) if ans["is_correct"]), None)
        if correct_index is None:
            st.error("No correct answer specified for a question.")
            return
        sheet.append([
            question["question"],
            answers[0]["text"],
            answers[1]["text"],
            answers[2]["text"],
            answers[3]["text"],
            "20",
            correct_index + 1
        ])
    wb.save(output)
    output.seek(0)
    return output

@st.cache_data
def extract_text_from_pdf(file):
    """Extracts text from a PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        return "".join(page.extract_text() or "" for page in pdf_reader.pages).strip()
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        return ""

@st.cache_data
def extract_text_from_docx(file):
    """Extracts text from a DOCX file."""
    try:
        doc = docx.Document(file)
        return "\n".join(paragraph.text for paragraph in doc.paragraphs).strip()
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {e}")
        return ""

def main():
    """Main function for the Streamlit app."""
    st.set_page_config(page_title="Quiz Generator", layout="wide")

    # Title
    st.title("📝 Quiz Generator")

    # Sidebar: Only video
    with st.sidebar:
        st.markdown("### Watch the Demo Video")
        st.components.v1.html("""
            <iframe width="100%" height="180" src="https://www.youtube.com/embed/NsTAjBdHb1k" 
            title="Demo Video" frameborder="0" allow="accelerometer; autoplay; clipboard-write; 
            encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
        """, height=180)

    # File uploader
    st.header("Upload Files")
    uploaded_files = st.file_uploader(
        "Upload PDF, DOCX, or image files:",
        type=["pdf", "docx", "png", "jpg", "jpeg"],
        accept_multiple_files=True
    )

    combined_text = ""

    if uploaded_files:
        st.subheader("Processing Files")
        for uploaded_file in uploaded_files:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            if file_extension == "pdf":
                text = extract_text_from_pdf(uploaded_file)
                combined_text += f"\n{text}"
                st.success(f"Extracted text from {uploaded_file.name}")
            elif file_extension == "docx":
                text = extract_text_from_docx(uploaded_file)
                combined_text += f"\n{text}"
                st.success(f"Extracted text from {uploaded_file.name}")
            elif file_extension in ["png", "jpg", "jpeg"]:
                image = Image.open(uploaded_file)
                st.image(image, caption=uploaded_file.name)
                st.info(f"Uploaded image: {uploaded_file.name}")
            else:
                st.error(f"Unsupported file type: {uploaded_file.name}")

    # Text input
    st.header("Provide Text or Topic")
    user_text = st.text_area("Enter your text or topic:", height=200)
    combined_text += f"\n{user_text.strip()}"

    if combined_text.strip():
        st.header("Preview of Combined Text")
        st.text_area("Extracted and Entered Text:", combined_text, height=200)

    # Quiz generation logic placeholder
    st.header("Generate Quiz")
    num_questions = st.selectbox("Number of Questions:", list(range(1, 11)))
    if st.button("Generate Quiz"):
        if combined_text.strip():
            st.success(f"Quiz generated with {num_questions} questions.")
            # Placeholder for quiz generation logic
            st.write("Quiz generation functionality goes here.")
        else:
            st.error("No text provided for quiz generation.")

    # Placeholder for downloading quiz data
    if st.button("Download Quiz as Excel"):
        dummy_quiz_data = [
            {
                "question": "Sample Question?",
                "answers": [
                    {"text": "Option A", "is_correct": False},
                    {"text": "Option B", "is_correct": False},
                    {"text": "Option C", "is_correct": True},
                    {"text": "Option D", "is_correct": False}
                ]
            }
        ]
        excel_file = save_to_excel(dummy_quiz_data)
        st.download_button(
            label="Download Excel File",
            data=excel_file,
            file_name="quiz.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
