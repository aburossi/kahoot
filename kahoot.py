import streamlit as st
from openai import OpenAI
import json
import random
import pandas as pd
import openpyxl
import re
from io import BytesIO, StringIO
from tiktoken import encoding_for_model  # Import tiktoken for token counting

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

def estimate_tokens_and_cost(input_text, model):
    input_tokens = count_tokens(input_text, model)
    estimated_output_tokens = input_tokens * 1.5  # Adjust this multiplier as needed
    estimated_cost = calculate_cost(input_tokens, estimated_output_tokens, model)
    return input_tokens, estimated_output_tokens, estimated_cost

# Function to calculate cost
def calculate_cost(input_tokens, output_tokens, model):
    costs = {
        "gpt-4o-mini": (0.00015, 0.0006),
        "gpt-4o": (0.005, 0.015),
        "gpt-4-turbo-preview": (0.01, 0.03)
    }
    input_cost, output_cost = costs[model]
    total_cost = (input_tokens * input_cost + output_tokens * output_cost) / 1000000
    return total_cost

def generate_and_process_quiz(client, input_text, selected_model, num_questions_selected):
    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are specialized in generating custom quizzes for the Kahoot platform."},
                {"role": "user", "content": input_text}
            ],
            temperature=0.7,
            max_tokens=4000,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        generated_quiz = response.choices[0].message.content.strip()

        # Count actual output tokens
        output_tokens = count_tokens(generated_quiz, selected_model)
        st.session_state['output_tokens'] = output_tokens

        # Calculate and display actual cost
        actual_cost = calculate_cost(st.session_state['estimated_input_tokens'], output_tokens, selected_model)
        st.write(f"Actual Cost: ${actual_cost:.6f}")

        try:
            # Attempt to parse the JSON
            quiz_data = json.loads(generated_quiz)
        except json.JSONDecodeError as json_error:
            st.warning(f"Error parsing JSON. Attempting to fix the response.")

            # Attempt to fix common JSON issues
            fixed_json = re.sub(r',\s*]', ']', generated_quiz)  # Remove trailing commas
            fixed_json = re.sub(r',\s*}', '}', fixed_json)  # Remove trailing commas in objects

            # If the JSON is incomplete, attempt to complete it
            if fixed_json.count('{') > fixed_json.count('}'):
                fixed_json += '}' * (fixed_json.count('{') - fixed_json.count('}'))
            if fixed_json.count('[') > fixed_json.count(']'):
                fixed_json += ']' * (fixed_json.count('[') - fixed_json.count(']'))

            try:
                quiz_data = json.loads(fixed_json)
                st.success("Successfully fixed and parsed the JSON response.")
            except json.JSONDecodeError:
                st.error(f"Unable to fix JSON parsing error. Raw response:\n{generated_quiz}")
                return None

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

        return valid_quiz_data

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return None

# Streamlit UI
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
num_questions = st.selectbox("Number of questions:", [str(i) for i in range(1, 13)])

# GPT Model selection dropdown
model_options = {
    "gpt-4o-mini (Cheapest & Fastest)": "gpt-4o-mini",
    "gpt-4o": "gpt-4o",
    "gpt-4-turbo-preview (Best & Most Expensive)": "gpt-4-turbo-preview"
}
selected_model_key = st.selectbox("Select GPT Model:", list(model_options.keys()))
selected_model = model_options[selected_model_key]

# Estimate Tokens and Cost button
if st.button("Estimate Tokens and Cost"):
    if not text_input.strip():
        st.error("Please enter a text or topic.")
    else:
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
        4. Generate exactly {num_questions} questions.
        5. Learning Objectives: {learning_objectives}
        6. Audience: {audience}
        
        Text or topic: {text_input}
                        
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

        input_tokens, estimated_output_tokens, estimated_cost = estimate_tokens_and_cost(input_text, selected_model)
        
        st.write(f"Estimated Input Tokens: {input_tokens}")
        st.write(f"Estimated Output Tokens: {estimated_output_tokens}")
        st.write(f"Estimated Cost: ${estimated_cost:.6f}")

        st.session_state['estimated_input_tokens'] = input_tokens
        st.session_state['estimated_output_tokens'] = estimated_output_tokens
        st.session_state['estimated_cost'] = estimated_cost
        st.session_state['input_text'] = input_text

# Generate Quiz button
if st.button("Generate Quiz"):
    if not api_key:
        st.error("API Key cannot be empty")
    elif 'estimated_cost' not in st.session_state:
        st.warning("Please estimate tokens and cost first.")
    else:
        st.write(f"Estimated Cost: ${st.session_state['estimated_cost']:.6f}")
        client = OpenAI(api_key=api_key)
        
        quiz_data = generate_and_process_quiz(client, st.session_state['input_text'], selected_model, int(num_questions))
        if quiz_data:
            st.session_state["quiz_data"] = quiz_data
            st.success("Quiz generated successfully!")
        else:
            st.error("Failed to generate quiz. Please try again.")

# Edit and Save Quiz Data
if "quiz_data" in st.session_state:
    quiz_data = st.session_state["quiz_data"]

    st.write("Edit Quiz Data:")
    for idx, question in enumerate(quiz_data):
        st.markdown(f"<h3 style='text-align: center;'>Question {idx+1}</h3>", unsafe_allow_html=True)
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
        
        st.markdown("<hr>", unsafe_allow_html=True)

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

    # Display token counts and cost
    if 'input_tokens' in st.session_state and 'output_tokens' in st.session_state:
        input_tokens = st.session_state['input_tokens']
        output_tokens = st.session_state['output_tokens']
        st.write(f"Input Tokens: {input_tokens}")
        st.write(f"Output Tokens: {output_tokens}")
        
        cost = calculate_cost(input_tokens, output_tokens, selected_model)
        st.write(f"Estimated Cost: ${cost:.6f}")

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
