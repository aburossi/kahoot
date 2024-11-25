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
    if not quiz_data or not isinstance(quiz_data, list):
        st.error("Invalid quiz data format.")
        return None

    output = BytesIO()
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(["Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Time", "Correct"])
    
    for question in quiz_data:
        if 'question' not in question or 'answers' not in question:
            continue
        answers = question['answers']
        if len(answers) != 4:
            continue
        random.shuffle(answers)
        correct_index = next((i for i, ans in enumerate(answers) if ans.get('is_correct')), None)
        if correct_index is None:
            continue
        row = [question['question']] + [ans['text'] for ans in answers] + ["20", correct_index + 1]
        sheet.append(row)

    if sheet.max_row == 1:  # Only header row
        st.error("No valid questions to save.")
        return None

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
    text = text_input.strip()
    num_questions_selected = int(num_questions)
    learning_objectives_selected = learning_objectives.strip()
    audience_selected = audience.strip()

    if not api_key:
        st.error("API Key cannot be empty")
        return

    client = OpenAI(api_key=api_key)

    # Prepare input text
    input_text = f"""
    Create a quiz based on the given text or topic. 
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
    
    Text or topic: {text}
    """

    # Count input tokens
    input_tokens = count_tokens(input_text, selected_model)
    
    # Get max tokens for the selected model
    max_tokens = get_max_tokens(selected_model)
    
    # Calculate available tokens for the response
    available_tokens = max_tokens - input_tokens - 100  # Subtract 100 as a safety margin
    available_tokens = max(0, available_tokens)  # Ensure available tokens is not negative

    try:
        # Call the OpenAI API
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are a quiz generator for Kahoot. Always respond with valid JSON."},
                {"role": "user", "content": input_text}
            ],
            temperature=0.7,
            max_tokens=available_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        # Extract and clean the response
        generated_content = response.choices[0].message.content.strip()

        # Attempt to parse the JSON
        try:
            quiz_data = json.loads(generated_content)
        except json.JSONDecodeError:
            st.warning("Error parsing JSON. Attempting to clean the response.")
            # Clean common JSON issues
            cleaned_content = re.sub(r',\s*]', ']', generated_content)  # Remove trailing commas
            cleaned_content = re.sub(r',\s*}', '}', cleaned_content)  # Remove trailing commas in objects

            # Use regex to extract valid JSON objects
            pattern = r'\{\s*"question":\s*"[^"]*",\s*"answers":\s*\[(?:[^}]+\},?){4}\s*\]\s*\}'
            valid_items = re.findall(pattern, cleaned_content)
            
            if valid_items:
                quiz_data = json.loads(f"[{','.join(valid_items)}]")
                st.success(f"Extracted {len(quiz_data)} valid questions.")
            else:
                st.error("No valid questions found in the response.")
                return

        # Validate and process the quiz data
        processed_quiz_data = []
        for item in quiz_data:
            if 'question' in item and 'answers' in item:
                question = item['question'][:120]
                answers = item['answers'][:4]
                while len(answers) < 4:
                    answers.append({"text": "Placeholder answer", "is_correct": False})
                processed_quiz_data.append({
                    "question": question,
                    "answers": [{"text": ans['text'][:75], "is_correct": ans['is_correct']} for ans in answers]
                })

        if len(processed_quiz_data) != num_questions_selected:
            st.warning(f"Generated {len(processed_quiz_data)} valid questions instead of {num_questions_selected}.")

        # Save processed data to session state
        st.session_state["quiz_data"] = processed_quiz_data

        # Allow user to download the generated quiz
        excel_buffer = save_to_excel(processed_quiz_data)
        st.download_button(
            label="Download Quiz as Excel",
            data=excel_buffer,
            file_name="kahoot_quiz.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")


    # Display raw response for debugging (you can remove this in production)
    with st.expander("Debug: Raw API Response"):
        st.text(generated_content)

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
