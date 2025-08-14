from RoBAssessment import Assessment as assess
import os
import time
from typing import List
from pydantic import BaseModel

# Pydantic Class for Structured Output.
class AssessmentResult(BaseModel):
    """
    Output format for the risk-of-bias assessment.
    Each field requires explanation to guide the LLM in output generation.
    """
    title: str
    """"""
    authors: str
    """"""
    explanation: str
    """"""
    summary: str
    """"""

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

    pdfs_count = len(os.listdir(assess.plain_text_input_folder))
    tokens_all_paper = 0
    for i, file_name in enumerate(sorted(os.listdir(assess.plain_text_input_folder))):
        print(f"Processing plain text: File {i + 1}/{pdfs_count}. Filename: {file_name}")

        note_entry = ""

        # Open markdown file.
        with open(os.path.join(assess.plain_text_input_folder, file_name), "r", encoding="utf-8") as f:
            document = f.read()

        note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
        try:
            input_prompt_tokens = len(assess.enc.encode(f"{assess.prompt_body} || {document}"))
            print(f"Input Tokens: {str(input_prompt_tokens)}")
            structured_response = call_openai_response_api_plain_text_input(assess.prompt_body, document, AssessmentResult)
        except Exception as e:
            exception = f"Error: {e}. Error prccessing {file_name}"
            note_entry += f"\n{exception}\n"
            print(f"Processing Error. Exception: {exception}")
            continue

        note_entry += (f"\n{structured_response.title}\n"
                       f"{structured_response.authors}\n"
                       f"\n{structured_response.explanation}")

        # token
        responses_tokens = len(assess.enc.encode(f"{note_entry}+{structured_response.summary})"))
        total_tokens = input_prompt_tokens+responses_tokens
        tokens_all_paper+=total_tokens
        print(f"Responses Tokens: {str(responses_tokens)}")
        print(f"Total Tokens: {str(total_tokens)}")

        assessment_notes.append(note_entry)
        summary_row = structured_response.summary.split(",")  # this is output from llm.
        full_row = [str(i + 1), file_name, structured_response.title] + summary_row
        assessment_summary.append(full_row)
        time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

    print("Processed " + str(pdfs_count) + " papers.")
    print("Consumed "+str(tokens_all_paper) +" for "+str(pdfs_count)+" papers.")
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
    assessment_notes.append("Assessing PDFs Stored in Cloud.")
    assessment_summary: List[List[str]] = [assess.summary_header]

    pdfs_count = len(file_dict.keys())
    tokens_all_paper = 0
    for i, file_name in enumerate(sorted(file_dict.keys())):  # sorted in ascending order.
        print(f"Processing pdf file: File {i + 1}/{pdfs_count}. Filename: {file_name}")
        file_id = file_dict[file_name]

        note_entry = ""
        note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"

        try:
            input_prompt_tokens = len(assess.enc.encode(assess.prompt_body))
            print(f"Input Tokens (prompt only, no parsed document): {str(input_prompt_tokens)}")
            structured_response = call_openai_response_api_file_upload(assess.prompt_body, file_id, AssessmentResult)
        except Exception as e:
            exception = f"Error: {e}. Error prccessing {file_name}"
            note_entry += f"\n{exception}\n"
            print(f"Processing Error. Exception: {exception}")
            continue

        note_entry += (f"\n{structured_response.title}\n"
                       f"{structured_response.authors}\n"
                       f"{structured_response.overall_risk}"
                       f"\n{structured_response.explanation}")

        # token
        responses_tokens = len(assess.enc.encode(f"{note_entry}+{structured_response.summary})"))
        total_tokens = input_prompt_tokens+responses_tokens
        tokens_all_paper += total_tokens
        print(f"Responses Tokens: {str(responses_tokens)}")
        print(f"Total Tokens: {str(total_tokens)}")

        assessment_notes.append(note_entry)
        summary_row = structured_response.summary.split(",")  # this is output from llm.
        full_row = [str(i + 1), file_name, structured_response.title] + summary_row
        assessment_summary.append(full_row)
        time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

    print("Processed " + str(pdfs_count) + " papers.")
    print("Consumed " + str(tokens_all_paper) + " for " + str(pdfs_count) + " papers.")
    # Save outputs
    assess.save_outputs(assessment_notes, assessment_summary)

### API Calls ###
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

def call_openai_response_api_plain_text_input(messages, document, output_format):
    """
    Function to call OpenAI API (Structured Output), intended for files parsed locally.
    :param messages: messages (prompt, string), document (string).
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