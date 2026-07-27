import os
import json
import re
import genanki
import random
import io
import streamlit as st
from google import genai
from google.genai import types
from google.genai import errors
from dotenv import load_dotenv
from string import Template

# src: https://www.bomberbot.com/python/mastering-file-saving-in-python-a-comprehensive-guide-to-user-defined-filenames/
def sanitize_filename(filename):
    # Remove any non-word characters (everything except numbers and letters)
    filename = re.sub(r'[^\w\-_\. ]', '_', filename)
    # Remove any runs of periods (since we don't want '../' to be in the filename)
    filename = re.sub(r'\.+', '.', filename)
    return filename

def main():
    load_dotenv()
    with open("SYSTEM_PROMPT.md", "r") as f:
        system_prompt = (f.read())

    AI_MODEL_CODE = 'gemini-3.5-flash-lite'
    MODEL_ID = 1607392319 # keep template shape identical for every card/deck
    

    json_schema = {
        "type": "array",
        "items": {
        "type": "object",
        "properties": {
            "Front": {
            "type": "string",
            "examples": [
                "Question related to the context"
            ]
            },
            "Back": {
            "type": "string",
            "examples": [
                "Answer directly related to the question"
            ]
            }
        },
        "required": [
            "Front",
            "Back"
        ]
        }
    }

    st.title('AI-powered Anki card generator')
    st.text('Upload lecture notes to be automatically created into an Anki deck of flashcards!')

    # user input:
    with st.form(key="my_form", enter_to_submit=False):
        topic = st.text_input("Enter a specific topic or module name:")

        col1, col2 = st.columns(2)
        with col1:
            uploaded_file = st.file_uploader("Upload a text file:", type='text/*') 
        with col2:
            pasted_notes = st.text_area("Paste in notes and/or extra instructions:")

        study_level = st.pills("Enter study level:", ['GCSE', 'A-Level', 'Undergraduate', 'Postgraduate'])
        num_cards = st.select_slider("Select the number of cards to be generated:", [i for i in range(1,21)])

        submitted = st.form_submit_button("Generate")

    if submitted:
        # guard check:
        if not topic:
            st.warning("Please enter topic or module name.")
            st.stop()
        if not pasted_notes and uploaded_file is None:
            st.warning("Please paste notes, or upload a file.")
            st.stop()
        if not study_level:
            st.warning("Please select study level.")
            st.stop()

        # model inputs:
        system_prompt = Template(system_prompt).safe_substitute(study_level=study_level, num_cards=num_cards)

        # combine user inputs
        model_input = ""
        if uploaded_file is not None:
                stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
                model_input += stringio.read()
        if pasted_notes:
            model_input += f'\n {pasted_notes}'

        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        try:
            print(f"Generating Anki cards about {topic}...")
            with st.spinner(text=f"Generating Anki cards about {topic}..."):
                response = client.models.generate_content(
                    model=AI_MODEL_CODE,
                    contents=types.Part.from_text(text=f'topic:{topic} \n contents:{model_input}'),
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0,
                        top_p=0.95,
                        top_k=20,
                        response_mime_type='application/json',
                        response_json_schema=json_schema
                    ),
                )
                st.success("Anki deck generated!")

            cards = json.loads(response.text)

            # Genanki create model (note type): defines the structure of notes and how cards are generated

            my_model = genanki.Model(
                MODEL_ID,
                'Simple Model',
                fields=[
                    {'name': 'Front'},
                    {'name': 'Back'},
                ],
                templates=[
                    {
                    'name': 'Card 1',
                    'qfmt': '{{Front}}',  # Question format
                    'afmt': '{{Front}}<hr id="answer">{{Back}}',  # Answer format
                    },
                ]
            )

            # Genanki create a deck
            deck_id = random.randrange(1 << 30, 1 << 31)

            my_deck = genanki.Deck(
                deck_id,
                topic # Deck name
            )

            # Genanki create note: contains actual content of flashcards
            # Genanki add to deck: created notes get added to a deck

            for card in cards:
                note = genanki.Note(
                    model=my_model,
                    fields=[card['Front'], card['Back']]
                )
                my_deck.add_note(note)

            # Genanki generate anki package:
            package = genanki.Package(my_deck)

            # create bytesio buffer for virutal folder in memory to save to
            buffer = io.BytesIO()
            filename = sanitize_filename(topic)
            package.write_to_file(buffer) # cursor at end 
            data = buffer.getvalue() # gets entire value regardless of cursor pos
            print("Success: Deck created!")

            st.download_button(
                "Download file", 
                data, 
                file_name=f'{filename}.apkg',
                mime="application/octet-stream"
            )
            buffer.close()

        except errors.APIError as e:
            st.error(f'Model API error ({e.code}): {e.message}')

        except json.JSONDecodeError as e:
            st.error(f'Invalid JSON syntax: {e}')

        client.close()


if __name__ == "__main__":
    main()
