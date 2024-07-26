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
    
    # Estimate output tokens
    estimated_output_tokens = input_tokens * 1.5  # Adjust this multiplier as needed
    st.write(f"Estimated Output Tokens: {int(estimated_output_tokens)}")

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
        st.write(f"Actual Output Tokens: {output_tokens}")

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
