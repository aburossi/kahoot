import streamlit as st
from openai import OpenAI
import json
import random
import pandas as pd
import openpyxl
import re
from io import BytesIO, StringIO
from tiktoken import encoding_for_model
from PIL import Image
import base64

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
            return None

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

# Function to count tokens
def count_tokens(text, model_name):
    enc = encoding_for_model(model_name)
    return len(enc.encode(text))

# New function to process image
def process_image(image):
    img = Image.open(image)
    # Resize image if it's too large
    max_size = 1000
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size))
    # Convert to RGB if necessary
    if img.mode != 'RGB':
        img = img.convert('RGB')
    # Save image to bytes
    img_byte_arr = BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    return base64.b64encode(img_byte_arr).decode('utf-8')

st.title("Kahoot Quiz Generator")

# Create two columns
col1, col2 = st.columns(2)

# English section
with col1:
    with st.expander("❗ **How to Get an API Key from OpenAI**"):
        st.write("""
        To obtain an API key from OpenAI, follow these steps:

        **Registration:** Go to the [OpenAI website](https://www.openai.com) and register for an account if you don't have one already.

        **Login:** Log in with your credentials.

        **Create an API Key:**

        1. Navigate to your user profile by clicking on your profile picture in the top right corner.
        2. Select the "API Keys" option from the dropdown menu or go directly to the API settings using this [link](https://platform.openai.com/api-keys).
        3. Create a new key: Click the "New API Key" button.

        **Key Naming:** Give the key a name to easily identify it later and confirm the creation.

        **Storage:** Copy the generated API key and store it in a secure place. This key will only be shown once, and you will need it to integrate the API into your application.
        """)

    with st.expander("👉 Best Practices for Using This App"):
        st.write("""
        1. Use clear and concise topics or texts.
        2. Specify the desired number of questions.
        3. Review and edit the generated questions if needed.
        4. Be aware of model limitations:
           - Depending on the length of your input text, the models gpt-4o and gpt-4-turbo-preview may generate fewer than 12 questions due to token limitations.
           - If you need more questions, you can:
             a) Generate a second output and import two tables in Kahoot.
             b) Use the gpt-4o-mini model, which has a larger text window and can handle longer inputs.
        5. For longer texts or more complex topics, consider breaking them into smaller sections and generating multiple sets of questions.
        """)

# German section
with col2:
    with st.expander("❗ Wie man einen API-Schlüssel von OpenAI erhält"):
        st.write("""
        Um einen API-Schlüssel von OpenAI zu erhalten, folgen Sie diesen Schritten:

        **Registrierung:** Gehen Sie auf die [OpenAI-Website](https://www.openai.com) und registrieren Sie sich für ein Konto, falls Sie noch keines haben.

        **Anmelden:** Melden Sie sich mit Ihren Anmeldedaten an.

        **API-Schlüssel erstellen:**
        [Videoeanleitung](https://youtu.be/NsTAjBdHb1k?feature=shared)

        1. Navigieren Sie zu Ihrem Benutzerprofil, indem Sie oben rechts auf Ihr Profilbild klicken.
        2. Wählen Sie im Dropdown-Menü die Option "API Keys" (API-Schlüssel) oder gehen Sie direkt zu den API-Einstellungen mit diesem [Link](https://platform.openai.com/api-keys).
        3. Neuen Schlüssel erstellen: Klicken Sie auf die Schaltfläche „New API Key“ (Neuen API-Schlüssel erstellen).

        **Schlüsselbenennung:** Geben Sie dem Schlüssel einen Namen, um ihn später leicht identifizieren zu können, und bestätigen Sie die Erstellung.

        **Speicherung:** Kopieren Sie den generierten API-Schlüssel und speichern Sie ihn an einem sicheren Ort. Dieser Schlüssel wird nur einmal angezeigt, und Sie benötigen ihn für die Integration der API in Ihre Anwendung.
        """)

    with st.expander("👉 Best Practices für die Nutzung dieser App"):
        st.write("""
        1. Verwenden Sie klare und prägnante Themen oder Texte.
        2. Nutzen Sie die Lernziele, um die LLM auf bestimmten Inhalte zu prompten.
        3. Überprüfen und bearbeiten Sie die generierten Fragen bei Bedarf.
        4. Beachten Sie die Modellbeschränkungen:
           - Abhängig von der Länge Ihres Eingabetextes können die Modelle gpt-4o und gpt-4-turbo-preview aufgrund von Token-Beschränkungen möglicherweise weniger als 12 Fragen generieren.
           - Wenn Sie mehr Fragen benötigen, können Sie:
             a) Eine zweite Ausgabe generieren und zwei Tabellen in Kahoot importieren.
             b) Das Modell gpt-4o-mini verwenden, das ein grösseres Textfenster hat und längere Eingaben verarbeiten kann.
        5. Für längere Texte oder komplexere Themen sollten Sie diese in kleinere Abschnitte unterteilen und mehrere Fragensätze generieren.
        """)

# API Key input
api_key = st.text_input("OpenAI API Key:", type="password")

# Add file uploader for images
uploaded_file = st.file_uploader("Upload an image (optional)", type=["jpg", "jpeg", "png"])

# Text input
text_input = st.text_area("Enter your text or topic:")

# Learning Objectives input
learning_objectives = st.text_input("Learning Objectives:")

# Audience input
audience = st.text_input("Audience:")

# Number of questions dropdown
num_questions = st.selectbox("Number of questions:", [str(i) for i in range(1, 13)])

# GPT Model selection dropdown
model_options = {
    "gpt-4o-mini (Cheapest & Fastest)": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gpt-4-turbo-preview (Best & Most Expensive)": "gpt-4-turbo-preview"
}
selected_model_key = st.selectbox("Select GPT Model:", list(model_options.keys()))
selected_model = model_options[selected_model_key]


# Add this function to get the max tokens for each model
def get_max_tokens(model):
    max_tokens = {
        "gpt-4o-mini": 16383,
        "gpt-4o": 16000,
        "gpt-4-turbo-preview": 4095
    }
    return max_tokens.get(model, 4095)  # Default to 4095 if model not found

def generate_quiz():
    text = text_input.strip()
    num_questions_selected = int(num_questions)
    learning_objectives_selected = learning_objectives.strip()
    audience_selected = audience.strip()

    if not api_key:
        st.error("API Key cannot be empty")
        return

    client = OpenAI(api_key=api_key)

    # Process image if uploaded
    image_content = None
    if uploaded_file:
        image_content = process_image(uploaded_file)
        st.image(uploaded_file, caption='Uploaded Image', use_column_width=True)

    # Prepare input text
    input_text = f"""
    Create a quiz based on the given text or topic and image (if provided). 
    Create questions and four potential answers for each question. 
    Ensure that each question does not exceed 120 characters 
    VERY IMPORTANT: Ensure each answer remains within 75 characters. 
    Follow these rules strictly:
    1. Generate questions about the provided text or topic, and the image if provided.
    2. Create questions and answers in the same language as the input text.
    3. Provide output in the specified JSON format.
    4. Generate exactly {num_questions_selected} questions.
    5. Learning Objectives: {learning_objectives_selected}
    6. Audience: {audience_selected}
    
    Text or topic: {text}
                    
    JSON format:
    [
        {{
            "question": "Question text (max 120 characters)",
            "answers": [
                {{
                    "text": "Answer option 1 (max 75 characters)",
                    "is_correct": false
                }},
                {{
                    "text": "Answer option 2 (max 75 characters)",
                    "is_correct": false
                }},
                {{
                    "text": "Answer option 3 (max 75 characters)",
                    "is_correct": false
                }},
                {{
                    "text": "Answer option 4 (max 75 characters)",
                    "is_correct": true
                }}
            ]
        }}
    ]
    
    Important:
    1. Ensure the JSON is a valid array of question objects.
    2. Each question must have exactly 4 answer options.
    3. Only one answer per question should be marked as correct (is_correct: true).
    4. Do not include any comments or ellipsis (...) in the actual JSON output.
    5. Repeat the structure for each question, up to the specified number of questions.
    6. Ensure the entire response is a valid JSON array.
    """

    # Count input tokens
    input_tokens = count_tokens(input_text, selected_model)
    st.write(f"Input Tokens: {input_tokens}")
    
    # Get max tokens for the selected model
    max_tokens = get_max_tokens(selected_model)
    
    # Calculate available tokens for the response
    available_tokens = max_tokens - input_tokens - 100  # Subtract 100 as a safety margin
    
    # Ensure available tokens is not negative
    available_tokens = max(0, available_tokens)
    
    st.write(f"Available Tokens for Response: {available_tokens}")

    try:
        messages = [
            {"role": "system", "content": "You are specialized in generating custom quizzes for the Kahoot platform."},
            {"role": "user", "content": input_text}
        ]

        # Add image to the message if provided
        if image_content:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "Please also consider this image when generating the quiz:"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_content}"
                        }
                    }
                ]
            })

        response = client.chat.completions.create(
            model=selected_model,
            messages=messages,
            temperature=0.7,
            max_tokens=available_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        generated_quiz = response.choices[0].message.content.strip()

        # Count actual output tokens
        output_tokens = count_tokens(generated_quiz, selected_model)
        st.write(f"Actual Output Tokens: {output_tokens}")

        try:
            # Attempt to parse the JSON
            quiz_data = json.loads(generated_quiz)
        except json.JSONDecodeError as json_error:
            st.warning(f"Error parsing JSON. Attempting to fix the response.")

            # Attempt to fix common JSON issues
            fixed_json = re.sub(r',\s*]', ']', generated_quiz)  # Remove trailing commas
            fixed_json = re.sub(r',\s*}', '}', fixed_json)  # Remove trailing commas in objects
            fixed_json = re.sub(r'\{\.\.\..*?\}', '', fixed_json, flags=re.DOTALL)  # Remove incomplete objects

            # If the JSON is incomplete, attempt to complete it
            if fixed_json.count('{') > fixed_json.count('}'):
                fixed_json += '}' * (fixed_json.count('{') - fixed_json.count('}'))
            if fixed_json.count('[') > fixed_json.count(']'):
                fixed_json += ']' * (fixed_json.count('[') - fixed_json.count(']'))

            try:
                quiz_data = json.loads(fixed_json)
                st.success("Successfully fixed and parsed the JSON response.")
            except json.JSONDecodeError:
                st.error(f"Unable to fix JSON parsing error. Attempting to extract valid questions.")
                # Extract valid questions using regex
                pattern = r'\{\s*"question":\s*"[^"]*",\s*"answers":\s*\[(?:[^}]+\},?){4}\s*\]\s*\}'
                valid_questions = re.findall(pattern, generated_quiz)
                if valid_questions:
                    quiz_data = json.loads(f"[{','.join(valid_questions)}]")
                    st.success(f"Extracted {len(quiz_data)} valid questions from the response.")
                else:
                    st.error("No valid questions found in the response.")
                    return

        # Validate and fix the quiz data structure
        valid_quiz_data = []
        for item in quiz_data:
            if isinstance(item, dict) and 'question' in item and 'answers' in item:
                question = item['question'][:120]  # Truncate question if too long
                answers = item['answers'][:4]  # Ensure only 4 answers
                while len(answers) < 4:
                    answers.append({"text": "Placeholder answer", "is_correct": False})
                valid_quiz_data.append({
                    "question": question,
                    "answers": [{"text": ans['text'][:75], "is_correct": ans['is_correct']} for ans in answers]
                })

        if len(valid_quiz_data) != num_questions_selected:
            st.warning(f"Generated {len(valid_quiz_data)} valid questions instead of the requested {num_questions_selected}.")

        st.session_state["quiz_data"] = valid_quiz_data

        # Expander for editing instructions
        with st.expander("Instructions for Editing the Generated Content"):
            st.write("""
            You can now edit the generated content. Please note that any questions longer than 120 characters and answers longer than 75 characters will not be accepted by Kahoot.
            """)

        # Expander for editing instructions
        with st.expander("Anleitung zur Bearbeitung der generierten Inhalte"):
            st.write("""
            Sie können nun die generierten Inhalte bearbeiten. Beachten Sie dabei, dass alle Fragen, die länger als 120 Zeichen sind, 
            und Antworten, die länger als 75 Zeichen sind, von Kahoot nicht akzeptiert werden.
            """)

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
        question_text = st.text_input(f"**Question {idx+1}**", value=question["question"], key=f"question_{idx}")
        char_count = len(question_text)
        color = "red" if char_count > 120 else "green"
        st.markdown(f'<p style="color:{color};">Character count: {char_count}/120</p>', unsafe_allow_html=True)
        
        for answer_idx, answer in enumerate(question["answers"]):
            answer_text = st.text_input(f"Answer {idx+1}-{answer_idx+1}", value=answer["text"], key=f"answer_{idx}_{answer_idx}")
            char_count = len(answer_text)
            color = "red" if char_count > 75 else "green"
            st.markdown(f'<p style="color:{color};">Character count: {char_count}/75</p>', unsafe_allow_html=True)
            st.checkbox(f"Correct Answer {idx+1}-{answer_idx+1}", value=answer["is_correct"], key=f"correct_{idx}_{answer_idx}")

    if st.button("Save as JSON"):
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
        json_data = json.dumps(quiz_data, indent=4)
        json_buffer = StringIO(json_data)
        st.download_button(
            label="Download JSON",
            data=json_buffer,
            file_name="quiz.json",
            mime="application/json"
        )

    if st.button("Save as Excel"):
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
        excel_buffer = save_to_excel(quiz_data)
        
        if excel_buffer is not None:
            st.download_button(
                label="Download Excel",
                data=excel_buffer,
                file_name="quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("Failed to generate Excel file. Please check your quiz data.")

        # Expander for next steps
        with st.expander("Next Steps"):
            st.write("""
            1. Save the Excel File.
            2. Create a new Kahoot quiz.
            3. Add a new question.
            4. Choose the import function in Kahoot.
            5. Upload the Excel file you just saved.
            """)
        # Expander for next steps
        with st.expander("Nächste Schritte"):
            st.write("""
            1. Speichern Sie die Excel-Datei.
            2. Erstellen Sie ein neues Kahoot-Quiz.
            3. Fügen Sie eine neue Frage hinzu.
            4. Wählen Sie die Importfunktion in Kahoot.
            5. Laden Sie die gerade gespeicherte Excel-Datei hoch.
            """)

# Display input and output token counts if available
if 'input_tokens' in st.session_state and 'output_tokens' in st.session_state:
    st.write(f"Input Tokens: {st.session_state['input_tokens']}")
    st.write(f"Output Tokens: {st.session_state['output_tokens']}")
