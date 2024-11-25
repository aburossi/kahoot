import streamlit as st
from openai import OpenAI
import json
import random
import PyPDF2
import docx
import re
import base64
from pdf2image import convert_from_bytes
import io
from PIL import Image
import pandas as pd
import openpyxl
from io import BytesIO, StringIO
from tiktoken import encoding_for_model  # Import tiktoken for token counting
import streamlit.components.v1 as components  # Import components for embedding HTML

# Logging für bessere Fehlerverfolgung einrichten
import logging
logging.basicConfig(level=logging.INFO)

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

# Function to count tokens
def count_tokens(text, model_name):
    enc = encoding_for_model(model_name)
    return len(enc.encode(text))

# Functions to extract text from different file types
@st.cache_data
def extract_text_from_pdf(file):
    """Extrahiert Text aus PDF mit PyPDF2."""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text.strip()
    except Exception as e:
        logging.error(f"Fehler bei der Textextraktion aus PDF: {e}")
        return ""

@st.cache_data
def extract_text_from_docx(file):
    """Extrahiert Text aus DOCX-Datei."""
    try:
        doc = docx.Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logging.error(f"Fehler bei der Textextraktion aus DOCX: {e}")
        return ""

@st.cache_data
def convert_pdf_to_images(file):
    """Konvertiert PDF-Seiten in Bilder."""
    try:
        images = convert_from_bytes(file.read())
        return images
    except Exception as e:
        logging.error(f"Fehler bei der Konvertierung von PDF zu Bildern: {e}")
        return []

def replace_german_sharp_s(text):
    """Ersetzt alle Vorkommen von 'ß' durch 'ss'."""
    return text.replace('ß', 'ss')

def clean_json_string(s):
    s = s.strip()
    s = re.sub(r'^```json\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'(?<=text": ")(.+?)(?=")', lambda m: m.group(1).replace('\n', '\\n'), s)
    s = ''.join(char for char in s if ord(char) >= 32 or char == '\n')
    match = re.search(r'\[.*\]', s, re.DOTALL)
    return match.group(0) if match else s

def generate_quiz():
    text = combined_text  # Verwenden Sie den kombinierten Text
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
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are specialized in generating custom quizzes for the Kahoot platform."},
                {"role": "user", "content": input_text}
            ],
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

        # Expander für Bearbeitungsanweisungen
        with st.expander("Instructions for Editing the Generated Content"):
            st.write("""
            You can now edit the generated content. Please note that any questions longer than 120 characters and answers longer than 75 characters will not be accepted by Kahoot.
            """)

        with st.expander("Anleitung zur Bearbeitung der generierten Inhalte"):
            st.write("""
            Sie können nun die generierten Inhalte bearbeiten. Beachten Sie dabei, dass alle Fragen, die länger als 120 Zeichen sind, 
            und Antworten, die länger als 75 Zeichen sind, von Kahoot nicht akzeptiert werden.
            """)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# Initialisieren einer Variable für den kombinierten Text
combined_text = ""

# Funktion zur Extraktion und Kombination von Text aus Dateien
def process_uploaded_files(uploaded_files):
    global combined_text
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_extension = uploaded_file.name.split('.')[-1].lower()
            st.sidebar.write(f"Processing: {uploaded_file.name}")

            if file_extension in ['pdf']:
                extracted_text = extract_text_from_pdf(uploaded_file)
                if extracted_text:
                    combined_text += "\n" + extracted_text
                    st.sidebar.success(f"Text extracted from {uploaded_file.name}.")
                else:
                    images = convert_pdf_to_images(uploaded_file)
                    if images:
                        st.sidebar.info(f"No text found in {uploaded_file.name}. Converted to images.")
                        # Handle image processing if needed
            elif file_extension in ['docx']:
                extracted_text = extract_text_from_docx(uploaded_file)
                if extracted_text:
                    combined_text += "\n" + extracted_text
                    st.sidebar.success(f"Text extracted from {uploaded_file.name}.")
                else:
                    st.sidebar.warning(f"No text found in {uploaded_file.name}.")
            elif file_extension in ['png', 'jpg', 'jpeg']:
                image = Image.open(uploaded_file)
                st.sidebar.image(image, caption=uploaded_file.name, use_column_width=True)
                st.sidebar.info(f"Image {uploaded_file.name} uploaded.")
                # Wenn Text aus Bildern extrahiert werden soll, müssen Sie alternative Methoden verwenden
            else:
                st.sidebar.error(f"Unsupported file type: {uploaded_file.name}")

        st.sidebar.success("All files processed successfully.")

def main():
    """Hauptfunktion für die Streamlit-App."""
    st.set_page_config(
        page_title="📝 OLAT Fragen Generator",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📝 Fragen Generator")

    # Seitenleiste für Anweisungen und Zusatzinformationen
    with st.sidebar:
        st.header("❗ **So verwenden Sie diese App**")
        
        st.markdown("""
        1. **Geben Sie Ihren OpenAI-API-Schlüssel ein**: Erhalten Sie Ihren API-Schlüssel von [OpenAI](https://platform.openai.com/account/api-keys) und geben Sie ihn im Feld *OpenAI-API-Schlüssel* ein.
        """)
        
        # YouTube-Video in die Seitenleiste einbetten
        components.html("""
            <iframe width="100%" height="180" src="https://www.youtube.com/embed/NsTAjBdHb1k" 
            title="Demo-Video auf Deutsch" frameborder="0" allow="accelerometer; autoplay; 
            clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
            </iframe>
        """, height=180)
        
        # Weitere Anweisungen
        st.markdown("""
        2. **Laden Sie eine PDF, DOCX oder Bilddatei hoch**: Wählen Sie eine Datei von Ihrem Computer aus.
        3. **Sprache auswählen**: Wählen Sie die gewünschte Sprache für die generierten Fragen.
        4. **Fragetypen auswählen**: Wählen Sie die Typen der Fragen, die Sie generieren möchten.
        5. **Fragen generieren**: Klicken Sie auf die Schaltfläche "Fragen generieren", um den Prozess zu starten.
        6. **Generierte Inhalte herunterladen**: Nach der Generierung können Sie die Antworten herunterladen.
        """)
    
        # Kosteninformationen und Frage-Erklärungen
        st.markdown('''
        <div class="custom-info">
            <strong>ℹ️ Kosteninformationen:</strong>
            <ul>
                <li>Die Nutzungskosten hängen von der <strong>Länge der Eingabe</strong> ab (zwischen 0,01 $ und 0,1 $).</li>
                <li>Jeder ausgewählte Fragetyp kostet ungefähr 0,01 $.</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
    
        st.markdown('''
        <div class="custom-success">
            <strong>✅ Multiple-Choice-Fragen:</strong>
            <ul>
                <li>Alle Multiple-Choice-Fragen haben maximal 3 Punkte.</li>
                <li><strong>multiple_choice1</strong>: 1 von 4 richtigen Antworten.</li>
                <li><strong>multiple_choice2</strong>: 2 von 4 richtigen Antworten.</li>
                <li><strong>multiple_choice3</strong>: 3 von 4 richtigen Antworten.</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
    
        st.markdown('''
        <div class="custom-success">
            <strong>✅ Inline/FIB-Fragen:</strong>
            <ul>
                <li>Die <strong>Inline</strong> und <strong>FIB</strong> Fragen sind inhaltlich identisch.</li>
                <li>FIB = fehlendes Wort eingeben.</li>
                <li>Inline = fehlendes Wort auswählen.</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
    
        st.markdown('''
        <div class="custom-success">
            <strong>✅ Andere Fragetypen:</strong>
            <ul>
                <li><strong>Single Choice</strong>: 4 Antworten, 1 Punkt pro Frage.</li>
                <li><strong>KPRIM</strong>: 4 Antworten, 5 Punkte (4/4 korrekt), 2,5 Punkte (3/4 korrekt), 0 Punkte (50% oder weniger korrekt).</li>
                <li><strong>True/False</strong>: 3 Antworten, 3 Punkte pro Frage.</li>
                <li><strong>Drag & Drop</strong>: Variable Punkte.</li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
    
        st.markdown('''
        <div class="custom-warning">
            <strong>⚠️ Warnungen:</strong>
            <ul>
                <li><strong>Überprüfen Sie immer, dass die Gesamtpunkte = Summe der Punkte der korrekten Antworten sind.</strong></li>
                <li><strong>Überprüfen Sie immer den Inhalt der Antworten.</strong></li>
            </ul>
        </div>
        ''', unsafe_allow_html=True)
    
        # Trennlinie und Lizenzinformationen
        st.markdown("---")
        st.header("📜 Lizenz")
        st.markdown("""
        Diese Anwendung steht unter der [MIT-Lizenz](https://opensource.org/licenses/MIT). 
        Sie dürfen diese Software verwenden, ändern und weitergeben, solange die ursprüngliche Lizenz beibehalten wird.
        """)
    
        # Kontaktinformationen
        st.header("💬 Kontakt")
        st.markdown("""
        Für Unterstützung, Fragen oder um mehr über die Nutzung dieser App zu erfahren, kannst du gerne auf mich zukommen.
        **Kontakt**: [Pietro](mailto:pietro.rossi@bbw.ch)
        """)
    
        # Datei-Uploads hinzufügen
        st.markdown("### 📂 **Datei-Upload**")
    
        uploaded_files = st.file_uploader(
            "Laden Sie Bilder, PDFs oder DOCX-Dateien hoch:",
            type=["png", "jpg", "jpeg", "pdf", "docx"],
            accept_multiple_files=True
        )
    
    # API Key input
    st.header("🔑 Geben Sie Ihren OpenAI-API-Schlüssel ein")
    api_key = st.text_input("OpenAI-API-Schlüssel:", type="password")
    
    # Initialize OpenAI client if an API key is provided
    client = None
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
            st.success("API-Schlüssel erfolgreich erkannt und verbunden.")
        except Exception as e:
            st.error(f"Fehler bei der Initialisierung des OpenAI-Clients: {e}")
    
    # Liste der verfügbaren Fragetypen
    MESSAGE_TYPES = [
        "single_choice",
        "multiple_choice1",
        "multiple_choice2",
        "multiple_choice3",
        "kprim",
        "truefalse",
        "draganddrop",
        "inline_fib"
    ]
    
    # Verarbeiten der hochgeladenen Dateien
    process_uploaded_files(uploaded_files)
    
    # Textinput und andere Eingaben
    text_input = st.text_area("Enter your text or topic:")
    learning_objectives = st.text_input("Learning Objectives:")
    audience = st.text_input("Audience:")
    num_questions = st.selectbox("Number of questions:", [str(i) for i in range(1, 13)])
    
    # GPT Model selection dropdown
    model_options = {
        "gpt-4o-mini (Cheapest & Fastest)": "gpt-4o-mini",
        "gpt-4o": "gpt-4o",
        "gpt-4-turbo-preview (Best & Most Expensive)": "gpt-4-turbo-preview"
    }
    selected_model_key = st.selectbox("Select GPT Model:", list(model_options.keys()))
    selected_model = model_options[selected_model_key]
    
    # Funktion zum Abrufen der maximalen Token-Anzahl für jedes Modell
    def get_max_tokens(model):
        max_tokens = {
            "gpt-4o-mini": 16383,
            "gpt-4o": 16000,
            "gpt-4-turbo-preview": 4095
        }
        return max_tokens.get(model, 4095)  # Default to 4095 if model not found
    
    # Kombinierter Text aus Benutzereingabe und hochgeladenen Dateien
    combined_text = text_input.strip()
    
    # Extrahierter Text aus Dateien ist bereits in process_uploaded_files hinzugefügt worden
    # Jetzt, falls es noch Text gibt, kombinieren wir ihn
    # Der Prozess_uploaded_files fügt bereits extrahierten Text hinzu
    
    def generate_quiz_button():
        generate_quiz()
    
    # Button zum Generieren von Quiz
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
            st.download_button(
                label="Download Excel",
                data=excel_buffer,
                file_name="quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Expander für nächste Schritte
            with st.expander("Next Steps"):
                st.write("""
                1. Save the Excel File.
                2. Create a new Kahoot quiz.
                3. Add a new question.
                4. Choose the import function in Kahoot.
                5. Upload the Excel file you just saved.
                """)

            # Expander für nächste Schritte auf Deutsch
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

if __name__ == "__main__":
    main()
