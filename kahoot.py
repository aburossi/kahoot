import streamlit as st
from openai import OpenAI
import json
import random
import pandas as pd
import openpyxl
import re
from io import BytesIO, StringIO
from tiktoken import encoding_for_model  # Import tiktoken for token counting
import streamlit.components.v1 as components  # Import components for embedding HTML
import PyPDF2
import docx
import base64
from pdf2image import convert_from_bytes
from PIL import Image
import logging

# Logging für bessere Fehlerverfolgung einrichten
logging.basicConfig(level=logging.INFO)

# Seitenkonfiguration festlegen
st.set_page_config(
    page_title="📝 Kahoot Quiz Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

# Funktion zur Extraktion von Text aus PDF
def extract_text_from_pdf(file):
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text.strip()
    except Exception as e:
        st.error(f"Fehler beim Extrahieren von Text aus PDF: {e}")
        return ""

# Funktion zur Extraktion von Text aus DOCX
def extract_text_from_docx(file):
    try:
        doc = docx.Document(file)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        st.error(f"Fehler beim Extrahieren von Text aus DOCX: {e}")
        return ""

# Funktion zur Verarbeitung von Bildern (falls notwendig)
def process_image(image):
    try:
        img = Image.open(image)
        img = img.convert('RGB')
        img.thumbnail((1000, 1000))
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        return base64.b64encode(img_byte_arr).decode('utf-8')
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung des Bildes: {e}")
        return ""

# Funktion zur Bereinigung des JSON-Strings
def clean_json_string(s):
    s = s.strip()
    s = re.sub(r'^```json\s*', '', s)
    s = re.sub(r'\s*```$', '', s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'(?<=text": ")(.+?)(?=")', lambda m: m.group(1).replace('\n', '\\n'), s)
    s = ''.join(char for char in s if ord(char) >= 32 or char == '\n')
    match = re.search(r'\[.*\]', s, re.DOTALL)
    return match.group(0) if match else s

# Funktion zur Umwandlung des JSON in ein geeignetes Format
def transform_output(json_string):
    try:
        cleaned_json_string = clean_json_string(json_string)
        json_data = json.loads(cleaned_json_string)
        return json_data
    except json.JSONDecodeError as e:
        st.error(f"Fehler beim Parsen von JSON: {e}")
        st.text("Bereinigte Eingabe:")
        st.code(cleaned_json_string, language='json')
        st.text("Originale Eingabe:")
        st.code(json_string)
        return None
    except Exception as e:
        st.error(f"Fehler bei der Verarbeitung der Eingabe: {str(e)}")
        st.text("Originale Eingabe:")
        st.code(json_string)
        return None

# Funktion zur Initialisierung des OpenAI-Clients
def initialize_openai(api_key):
    try:
        client = OpenAI(api_key=api_key)
        st.success("API-Schlüssel erfolgreich erkannt und verbunden.")
        return client
    except Exception as e:
        st.error(f"Fehler bei der Initialisierung des OpenAI-Clients: {e}")
        return None

st.title("📝 Kahoot Quiz Generator")

# Move Anleitungen to the sidebar
with st.sidebar:
    st.header("❗ **Anleitungen und Informationen**")
    
    # YouTube-Video in die Seitenleiste einbetten
    components.html("""
        <iframe width="100%" height="180" src="https://www.youtube.com/embed/NsTAjBdHb1k" 
        title="Demo-Video auf Deutsch" frameborder="0" allow="accelerometer; autoplay; 
        clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen>
        </iframe>
    """, height=180)
    
    # Deutsche Anleitungen
    st.markdown("### ❗ **Wie man einen API-Schlüssel von OpenAI erhält**")
    st.write("""
    Um einen API-Schlüssel von OpenAI zu erhalten, folgen Sie diesen Schritten:

    **Registrierung:** Gehen Sie auf die [OpenAI-Website](https://www.openai.com) und registrieren Sie sich für ein Konto, falls Sie noch keines haben.

    **Anmelden:** Melden Sie sich mit Ihren Anmeldedaten an.

    **API-Schlüssel erstellen:**
    1. Navigieren Sie zu Ihrem Benutzerprofil, indem Sie oben rechts auf Ihr Profilbild klicken.
    2. Wählen Sie im Dropdown-Menü die Option "API Keys" (API-Schlüssel) oder gehen Sie direkt zu den API-Einstellungen mit diesem [Link](https://platform.openai.com/api-keys).
    3. Neuen Schlüssel erstellen: Klicken Sie auf die Schaltfläche „New API Key“ (Neuen API-Schlüssel erstellen).

    **Schlüsselbenennung:** Geben Sie dem Schlüssel einen Namen, um ihn später leicht identifizieren zu können, und bestätigen Sie die Erstellung.

    **Speicherung:** Kopieren Sie den generierten API-Schlüssel und speichern Sie ihn an einem sicheren Ort. Dieser Schlüssel wird nur einmal angezeigt, und Sie benötigen ihn für die Integration der API in Ihre Anwendung.
    """)

    # Deutsche Best Practices
    with st.expander("👉 **Best Practices für die Nutzung dieser App**"):
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

    # Englische Anleitungen
    st.markdown("### ❗ **How to Get an API Key from OpenAI**")
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

    # Englische Best Practices
    with st.expander("👉 **Best Practices for Using This App**"):
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

    # Lizenzinformationen
    st.markdown("---")
    st.header("📜 **Lizenz**")
    st.markdown("""
    Diese Anwendung steht unter der [MIT-Lizenz](https://opensource.org/licenses/MIT). 
    Sie dürfen diese Software verwenden, ändern und weitergeben, solange die ursprüngliche Lizenz beibehalten wird.
    """)

    # Kontaktinformationen
    st.header("💬 **Kontakt**")
    st.markdown("""
    Für Unterstützung, Fragen oder um mehr über die Nutzung dieser App zu erfahren, kannst du gerne auf mich zukommen.
    **Kontakt**: [Pietro](mailto:pietro.rossi@bbw.ch)
    """)

# API Key input
st.header("🔑 **Geben Sie Ihren OpenAI-API-Schlüssel ein**")
api_key = st.text_input("OpenAI API Key:", type="password")

# Initialize OpenAI client if an API key is provided
client = None
if api_key:
    client = initialize_openai(api_key)

# Optionen zum Eingeben von Text oder Hochladen von Dateien
st.header("📄 **Eingabe**")

# Auswahl zwischen Text eingeben oder Datei hochladen
input_option = st.radio("Wählen Sie die Eingabequelle:", ("Eigenen Text eingeben", "Datei hochladen"))

text_input = ""
uploaded_file = None

if input_option == "Eigenen Text eingeben":
    text_input = st.text_area("Geben Sie Ihren Text oder Ihr Thema ein:")
else:
    uploaded_file = st.file_uploader("Laden Sie eine PDF, DOCX oder Bilddatei hoch", type=["pdf", "docx", "jpg", "jpeg", "png"])

# Extrahierter Text aus der Datei
extracted_text = ""

if uploaded_file is not None:
    if uploaded_file.type == "application/pdf":
        extracted_text = extract_text_from_pdf(uploaded_file)
        if extracted_text:
            st.success("Text aus PDF extrahiert.")
            st.text_area("Extrahierter Text:", value=extracted_text, height=200)
        else:
            st.warning("Kein Text aus der PDF extrahiert. Bitte überprüfen Sie die Datei.")
    elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        extracted_text = extract_text_from_docx(uploaded_file)
        if extracted_text:
            st.success("Text aus DOCX extrahiert.")
            st.text_area("Extrahierter Text:", value=extracted_text, height=200)
        else:
            st.warning("Kein Text aus der DOCX-Datei extrahiert. Bitte überprüfen Sie die Datei.")
    elif uploaded_file.type.startswith('image/'):
        st.image(uploaded_file, caption='Hochgeladenes Bild', use_column_width=True)
        extracted_text = st.text_input("Optional: Geben Sie zusätzlichen Text oder Anweisungen ein:")
    else:
        st.error("Nicht unterstützter Dateityp. Bitte laden Sie eine PDF, DOCX oder Bilddatei hoch.")

# Learning Objectives input
learning_objectives = st.text_input("Lernziele:")

# Audience input
audience = st.text_input("Zielgruppe:")

# Number of questions dropdown
num_questions = st.selectbox("Anzahl der Fragen:", [str(i) for i in range(1, 13)])

# GPT Model selection dropdown
model_options = {
    "gpt-4o-mini (Günstigste & Schnellste)": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gpt-4-turbo-preview (Beste & Teuerste)": "gpt-4-turbo-preview"
}
selected_model_key = st.selectbox("Wählen Sie das GPT-Modell:", list(model_options.keys()))
selected_model = model_options[selected_model_key]

# Funktion zum Abrufen der maximalen Tokenanzahl pro Modell
def get_max_tokens(model):
    max_tokens = {
        "gpt-4o-mini": 16383,
        "gpt-4o": 16000,
        "gpt-4-turbo-preview": 4095
    }
    return max_tokens.get(model, 4095)  # Default zu 4095, falls Modell nicht gefunden

# Funktion zur Generierung des Quiz
def generate_quiz():
    global extracted_text, text_input
    if input_option == "Eigenen Text eingeben":
        text = text_input.strip()
    else:
        text = extracted_text.strip()

    num_questions_selected = int(num_questions)
    learning_objectives_selected = learning_objectives.strip()
    audience_selected = audience.strip()

    if not api_key:
        st.error("API Key darf nicht leer sein.")
        return

    if not text:
        st.error("Bitte geben Sie einen Text ein oder laden Sie eine Datei hoch.")
        return

    client = OpenAI(api_key=api_key)

    # Vorbereitung des Eingabetextes
    input_text = f"""
    Erstellen Sie ein Quiz basierend auf dem gegebenen Text oder Thema.
    Erstellen Sie Fragen und vier mögliche Antworten für jede Frage.
    Stellen Sie sicher, dass jede Frage nicht mehr als 120 Zeichen enthält.
    SEHR WICHTIG: Stellen Sie sicher, dass jede Antwort innerhalb von 75 Zeichen bleibt.
    Befolgen Sie diese Regeln strikt:
    1. Generieren Sie Fragen über den bereitgestellten Text oder das Thema.
    2. Erstellen Sie Fragen und Antworten in derselben Sprache wie der Eingabetext.
    3. Geben Sie die Ausgabe im angegebenen JSON-Format.
    4. Generieren Sie genau {num_questions_selected} Fragen.
    5. Lernziele: {learning_objectives_selected}
    6. Zielgruppe: {audience_selected}
    
    Text oder Thema: {text}
                    
    JSON-Format:
    [
        {{
            "question": "Fragetext (max. 120 Zeichen)",
            "answers": [
                {{
                    "text": "Antwortoption 1 (max. 75 Zeichen)",
                    "is_correct": false
                }},
                {{
                    "text": "Antwortoption 2 (max. 75 Zeichen)",
                    "is_correct": false
                }},
                {{
                    "text": "Antwortoption 3 (max. 75 Zeichen)",
                    "is_correct": false
                }},
                {{
                    "text": "Antwortoption 4 (max. 75 Zeichen)",
                    "is_correct": true
                }}
            ]
        }}
    ]
    
    Wichtig:
    1. Stellen Sie sicher, dass das JSON ein gültiges Array von Frageobjekten ist.
    2. Jede Frage muss genau 4 Antwortoptionen haben.
    3. Nur eine Antwort pro Frage sollte als korrekt markiert sein (is_correct: true).
    4. Fügen Sie keine Kommentare oder Auslassungspunkte (...) in die tatsächliche JSON-Ausgabe ein.
    5. Wiederholen Sie die Struktur für jede Frage, bis zur angegebenen Anzahl der Fragen.
    6. Stellen Sie sicher, dass die gesamte Antwort ein gültiges JSON-Array ist.
    """

    # Token zählen
    input_tokens = count_tokens(input_text, selected_model)
    st.write(f"**Input Tokens:** {input_tokens}")

    # Maximale Tokenanzahl für das ausgewählte Modell abrufen
    max_tokens = get_max_tokens(selected_model)

    # Verfügbare Token für die Antwort berechnen
    available_tokens = max_tokens - input_tokens - 100  # 100 als Sicherheitsmarge abziehen

    # Sicherstellen, dass die verfügbaren Token nicht negativ sind
    available_tokens = max(0, available_tokens)

    st.write(f"**Verfügbare Token für die Antwort:** {available_tokens}")

    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "Du bist spezialisiert auf die Erstellung von benutzerdefinierten Quizzen für die Kahoot-Plattform."},
                {"role": "user", "content": input_text}
            ],
            temperature=0.7,
            max_tokens=available_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        generated_quiz = response.choices[0].message.content.strip()

        # Tatsächliche Ausgabe-Tokens zählen
        output_tokens = count_tokens(generated_quiz, selected_model)
        st.write(f"**Tatsächliche Ausgabe Tokens:** {output_tokens}")

        # JSON verarbeiten
        quiz_data = transform_output(generated_quiz)

        if quiz_data is None:
            st.error("Fehler beim Verarbeiten der generierten JSON-Daten.")
            return

        # Validieren und Struktur des Quiz-Daten überprüfen
        valid_quiz_data = []
        for item in quiz_data:
            if isinstance(item, dict) and 'question' in item and 'answers' in item:
                question = item['question'][:120]  # Frage bei Bedarf kürzen
                answers = item['answers'][:4]  # Sicherstellen, dass nur 4 Antworten vorhanden sind
                while len(answers) < 4:
                    answers.append({"text": "Platzhalter Antwort", "is_correct": False})
                valid_quiz_data.append({
                    "question": question,
                    "answers": [{"text": ans['text'][:75], "is_correct": ans['is_correct']} for ans in answers]
                })

        if len(valid_quiz_data) != num_questions_selected:
            st.warning(f"Es wurden {len(valid_quiz_data)} gültige Fragen generiert anstelle der angeforderten {num_questions_selected}.")

        st.session_state["quiz_data"] = valid_quiz_data

        # Expander für Bearbeitungsanweisungen
        with st.expander("📌 **Anweisungen zur Bearbeitung der generierten Inhalte**"):
            st.write("""
            Sie können nun die generierten Inhalte bearbeiten. Bitte beachten Sie, dass alle Fragen, die länger als 120 Zeichen sind, und Antworten, die länger als 75 Zeichen sind, von Kahoot nicht akzeptiert werden.
            """)

        with st.expander("📌 **Instructions for Editing the Generated Content**"):
            st.write("""
            You can now edit the generated content. Please note that any questions longer than 120 characters and answers longer than 75 characters will not be accepted by Kahoot.
            """)

    except Exception as e:
        st.error(f"Ein Fehler ist aufgetreten: {str(e)}")

# Generate button
if st.button("🛠️ **Quiz generieren**"):
    generate_quiz()

# Edit and Save Quiz Data
if "quiz_data" in st.session_state:
    quiz_data = st.session_state["quiz_data"]

    st.header("✏️ **Quiz Daten bearbeiten:**")
    for idx, question in enumerate(quiz_data):
        st.subheader(f"**Frage {idx+1}**")
        question_text = st.text_input(f"**Frage {idx+1}**", value=question["question"], key=f"question_{idx}")
        char_count = len(question_text)
        color = "red" if char_count > 120 else "green"
        st.markdown(f'<p style="color:{color};">Zeichenanzahl: {char_count}/120</p>', unsafe_allow_html=True)
        
        for answer_idx, answer in enumerate(question["answers"]):
            answer_text = st.text_input(f"Antwort {idx+1}-{answer_idx+1}", value=answer["text"], key=f"answer_{idx}_{answer_idx}")
            char_count = len(answer_text)
            color = "red" if char_count > 75 else "green"
            st.markdown(f'<p style="color:{color};">Zeichenanzahl: {char_count}/75</p>', unsafe_allow_html=True)
            st.checkbox(f"Korrekte Antwort {idx+1}-{answer_idx+1}", value=answer["is_correct"], key=f"correct_{idx}_{answer_idx}")

    # Buttons zum Speichern
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 **Als JSON speichern**"):
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
                label="🔽 JSON herunterladen",
                data=json_buffer,
                file_name="quiz.json",
                mime="application/json"
            )

    with col2:
        if st.button("💾 **Als Excel speichern**"):
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
                label="🔽 Excel herunterladen",
                data=excel_buffer,
                file_name="quiz.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Expander für nächste Schritte
    with st.expander("📋 **Nächste Schritte**"):
        st.write("""
        1. Speichern Sie die Excel-Datei.
        2. Erstellen Sie ein neues Kahoot-Quiz.
        3. Fügen Sie eine neue Frage hinzu.
        4. Wählen Sie die Importfunktion in Kahoot.
        5. Laden Sie die gerade gespeicherte Excel-Datei hoch.
        """)

    with st.expander("📋 **Next Steps**"):
        st.write("""
        1. Save the Excel File.
        2. Create a new Kahoot quiz.
        3. Add a new question.
        4. Choose the import function in Kahoot.
        5. Upload the Excel file you just saved.
        """)

# Anzeige der Tokenanzahl, falls verfügbar
if 'input_tokens' in st.session_state and 'output_tokens' in st.session_state:
    st.write(f"**Input Tokens:** {st.session_state['input_tokens']}")
    st.write(f"**Output Tokens:** {st.session_state['output_tokens']}")
