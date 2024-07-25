import streamlit as st
from openai import OpenAI
import json
import random
import pandas as pd
import openpyxl
import re

# Helper function to save quiz data to Excel
def save_to_excel(quiz_data, file_name):
    # ... (keep the existing save_to_excel function as is)

# Streamlit app
st.title("Kahoot Quiz Generator")

# ... (keep all the existing input fields and dropdowns as they are)

def generate_quiz():
    text = text_input.strip()
    num_questions_selected = int(num_questions)
    learning_objectives_selected = learning_objectives.strip()
    audience_selected = audience.strip()

    if not api_key:
        st.error("API Key cannot be empty")
        return

    client = OpenAI(api_key=api_key)
    
    try:
        response = client.chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": "You are specialized in generating custom quizzes for the Kahoot platform."},
                {"role": "user", "content": f"""
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
                    "question": "Your question here max 120 characters",
                    "answers": [
                    {{
                        "text": "Answer 1 max 75 characters",
                        "is_correct": false
                    }},
                    {{
                        "text": "Answer 2 max 75 characters",
                        "is_correct": false
                    }},
                    {{
                        "text": "Answer 3 max 75 characters",
                        "is_correct": false
                    }},
                    {{
                        "text": "Answer 4 max 75 characters",
                        "is_correct": true
                    }}
                    ]
                }},
                ... (repeat for all questions)
                ]
                """}
            ],
            temperature=0.7,  # Reduced temperature for more consistent output
            max_tokens=4000,  # Adjusted max tokens
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )

        generated_quiz = response.choices[0].message.content.strip()
        
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
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")

# ... (keep the rest of the code, including the Generate button and Edit and Save Quiz Data section, as is)
