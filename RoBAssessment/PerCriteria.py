import Assessment as assess
import os
import time
from typing import List
from pydantic import BaseModel

# Pydantic Class for Structured Output.
class AssessmentResultPerCriteria(BaseModel):
    """
    Output format for the risk-of-bias assessment.
    Each field requires explanation to guide the LLM in output generation.
    """
    criteria: str
    """This corresponds to the name of the criteria assessed."""
    result: str
    """The overall decision for this item. Respond only with ['Yes', 'No']."""
    explanation: float
    """A detailed reasoning that supports the decision, based on evidence from the document."""

### Methods ###
def process_plain_text():
    """
    Process all the plain Markdown text locally. Saves assessment output files.
    Input: NA.
    Output: NA.
    """
    # Initialize output containers
    assessment_notes: List[str] = []
    assessment_notes.append(assess.notes_header)
    assessment_notes.append("Assessing Plain Files Locally.")
    assessment_summary: List[List[str]] = [assess.summary_header]

    # token counter for all papers.
    tokens_all_paper = 0

    # Loop for one paper.
    pdfs_count = len(os.listdir(assess.plain_text_input_folder))
    for i, file_name in enumerate(sorted(os.listdir(assess.plain_text_input_folder))):
        print(f"Processing plain text: File {i + 1}/{pdfs_count}. Filename: {file_name}")

        # Initialize note.
        note_entry = ""
        note_entry += (f"\n=== Paper {i + 1}: {file_name} ===\n")
        csv_entry = ""

        # Open markdown file.
        with open(os.path.join(assess.plain_text_input_folder, file_name), "r", encoding="utf-8") as f:
            document = f.read()

        # Token counter for one paper.
        tokens_this_paper = 0

        # Loop over criterion.
        list_of_sub_criteria_keys = list(assess.criteria.keys())
        for sub_criteria in list_of_sub_criteria_keys:
            sub_criteria_prompt = assess.criteria[sub_criteria]

            tokens_this_paper += len(assess.enc.encode(f"{assess.intro_message}+{sub_criteria_prompt}+{document}"))

            try:
                structured_response = call_openai_response_api_plain_text_input(sub_criteria_prompt, document,
                                                                                AssessmentResultPerCriteria)
            except Exception as e:
                exception = f"Error: {e}. Error prccessing {file_name}"
                note_entry += f"\n{exception}\n"
                print(f"Processing Error. Exception: {exception}")
                continue

            # Reasoning field.
            note_entry += (f"\n{structured_response.criteria} = {structured_response.result}\n"
                           f"\n{structured_response.explanation}\n")
            # Append csv entry.
            csv_entry += (f"{structured_response.result},") # comma at the end.
            # Responses tokens.
            tokens_this_paper += len(assess.enc.encode(f"{note_entry}+{csv_entry}"))
            tokens_all_paper += tokens_this_paper
            time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

        print(f"This paper consumer approximately {tokens_this_paper} tokens.")
        assessment_notes.append(note_entry)
        full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
        assessment_summary.append(full_row)

    print("Processed " + str(pdfs_count) + " papers.")
    print("Consumed "+str(tokens_all_paper) +" tokens for "+str(pdfs_count)+" papers.")
    # Save outputs
    assess.save_outputs(assessment_notes, assessment_summary)

def process_pdf_stored_in_cloud(file_dict):
    """
    Process all the pdf stored in the cloud. Loop through the dictionary. Saves assessment output files.
    Input: {file_name: file_id} dictionary.
    Output: NA.
    """
    # Initialize output containers
    assessment_notes: List[str] = []
    assessment_notes.append(assess.notes_header)
    assessment_notes.append("Assessing Plain Files Locally.")
    assessment_summary: List[List[str]] = [assess.summary_header]

    # Initialize token counter for all papers.
    tokens_all_paper = 0

    pdfs_count = len(file_dict.keys())
    for i, file_name in enumerate(sorted(file_dict.keys())):  # sorted in ascending order.
        print(f"Processing pdf file: File {i + 1}/{pdfs_count}. Filename: {file_name}")
        file_id = file_dict[file_name]

        note_entry = ""
        note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
        csv_entry = ""

        # Token counter for one paper.
        tokens_this_paper = 0

        # Loop over criterion.
        list_of_sub_criteria_keys = list(assess.criteria.keys())
        for sub_criteria in list_of_sub_criteria_keys:
            sub_criteria_prompt = assess.criteria[sub_criteria]
            #tokens_this_paper += len(assess.enc.encode(f"{assess.intro_message}+{sub_criteria_prompt}+{document}"))

            try:
                #input_prompt_tokens = len(enc.encode(prompt_body))
                #print(f"Input Tokens (prompt only, no parsed document): {str(input_prompt_tokens)}")
                structured_response = call_openai_response_api_file_upload(sub_criteria_prompt,
                                                                           file_id, AssessmentResultPerCriteria)
            except Exception as e:
                exception = f"Error: {e}. Error prccessing {file_name}"
                note_entry += f"\n{exception}\n"
                print(f"Processing Error. Exception: {exception}")
                continue

            # Reasoning field.
            note_entry += (f"\n{structured_response.criteria} = {structured_response.result}\n"
                           f"\n{structured_response.explanation}\n")
            # Append csv entry.
            csv_entry += (f"{structured_response.result},")  # comma at the end.
            # Responses tokens.
            #tokens_this_paper += len(assess.enc.encode(f"{note_entry}+{csv_entry}"))
            #tokens_all_paper += tokens_this_paper
            time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

        # token
        #responses_tokens = len(enc.encode(f"{note_entry}+{structured_response.summary})"))
        #total_tokens = input_prompt_tokens+responses_tokens
        #tokens_all_paper += total_tokens
        #print(f"Responses Tokens: {str(responses_tokens)}")
        #print(f"Total Tokens: {str(total_tokens)}")

        assessment_notes.append(note_entry)
        full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
        assessment_summary.append(full_row)

    print("Processed " + str(pdfs_count) + " papers.")
    #print("Consumed " + str(tokens_all_paper) + " for " + str(pdfs_count) + " papers.")
    # Save outputs
    assess.save_outputs(assessment_notes, assessment_summary)

### API Calls ###
def call_openai_response_api_plain_text_input(messages, document, output_format):
    """
    Function to call OpenAI API (Structured Output), intended for files parsed locally.
    :param messages: messages (prompt, string), document (string), output_format (pydantic class).
    :return: AssessmentResult
    """
    response = assess.client.responses.parse(
        model=assess.model_name,
        temperature=assess.model_temperature,
        instructions=assess.intro_message,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"{messages}\n"
                    },
                    {
                        "type": "input_text",
                        "text": f"\nHere is the paper:\n{document}"
                    }
                ]
            },
        ],
        text_format=output_format,
    )
    return response.output_parsed

def call_openai_response_api_file_upload(messages, file_id, output_format):
    """
    Function to call OpenAI API (Structured Output), intended for files stored in OpenAI platform.
    :param messages: messages (prompt, string), file_id (string).
    :return: AssessmentResult
    """
    response = assess.client.responses.parse(
        model=assess.model_name,
        temperature=assess.model_temperature,
        instructions=assess.intro_message,
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": messages,
                    },
                    {
                        "type": "input_file",
                        "file_id": file_id
                    }
                ]
            },
        ],
        text_format=output_format,
    )

    return response.output_parsed