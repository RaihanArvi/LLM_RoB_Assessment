import os
import time
import openai
from typing import List
from pydantic import BaseModel
from RoBAssessment import Assessment as assess
from tenacity import retry, wait_exponential, retry_if_exception_type

# Pydantic Class for Structured Output.
class AssessmentResultPerCriteria(BaseModel):
    """
    Output format for the risk-of-bias assessment.
    Each field requires explanation to guide the LLM in output generation.
    """
    criteria: str
    """This corresponds to the name of the criteria assessed."""
    result: str
    """The overall decision for this item. Respond only with one of ['yes', 'no']."""
    explanation: str
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
    assessment_notes.append("Assessing plain files locally. Assessing one criteria at a time for one paper.")
    assessment_summary: List[List[str]] = [assess.summary_header]
    assess.print_and_log("Assessing plain files locally. Assessing one criteria at a time for one paper.")

    # token counter for all papers.
    tokens_all_papers = 0

    # Loop for one paper.
    # Get only .txt and .md files
    plain_text_files = [
        f for f in sorted(os.listdir(assess.plain_text_input_folder))
        if f.lower().endswith((".txt", ".md"))
    ]
    pdfs_count = len(plain_text_files)
    for i, file_name in enumerate(plain_text_files):
        assess.print_and_log(f"Processing plain text: File {i + 1}/{pdfs_count}. Filename: {file_name}")

        # Initialize note.
        note_entry = ""
        note_entry += (f"\n=== Paper {i + 1}: {file_name} ===\n")
        csv_entry = ""

        # token counter for this paper.
        tokens_this_paper = 0

        # Open markdown file.
        with open(os.path.join(assess.plain_text_input_folder, file_name), "r", encoding="utf-8") as f:
            document = f.read()

        # Loop over criterion.
        list_of_sub_criteria_keys = list(assess.criteria.keys())
        for sub_criteria in list_of_sub_criteria_keys:
            sub_criteria_prompt = assess.criteria[sub_criteria]

            try:
                structured_response = call_openai_response_api_plain_text_input(sub_criteria_prompt, document,
                                                                                AssessmentResultPerCriteria)
            except Exception as e:
                exception = f"Error: {e}. Error prccessing {file_name}"
                note_entry += f"\n{exception}\n"
                assess.print_and_log(f"Processing Error. Exception: {exception}")
                continue

            # Reasoning field.
            note_entry += (f"\n{structured_response.output_parsed.criteria} = {structured_response.output_parsed.result}\n"
                           f"\n{structured_response.output_parsed.explanation}\n")
            # Append csv entry.
            csv_entry += (f"{structured_response.output_parsed.result},") # comma at the end.

            # Responses tokens.
            tokens_this_paper += structured_response.usage.total_tokens
            time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

        assess.print_and_log(f"This paper ({file_name}) consumed {tokens_this_paper} tokens.")
        tokens_all_papers += tokens_this_paper

        assessment_notes.append(note_entry)
        full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
        assessment_summary.append(full_row)

    assess.print_and_log("Processed " + str(pdfs_count) + " papers.")
    assess.print_and_log("Consumed "+str(tokens_all_papers) +" tokens for "+str(pdfs_count)+" papers.")
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
    assessment_notes.append("Assessing PDFs stored in cloud. Assessing one criteria at a time for one paper.")
    assessment_summary: List[List[str]] = [assess.summary_header]
    assess.print_and_log("Assessing PDFs stored in cloud. Assessing one criteria at a time for one paper.")

    # Initialize token counter for all papers.
    tokens_all_papers = 0

    pdfs_count = len(file_dict.keys())
    for i, file_name in enumerate(sorted(file_dict.keys())):  # sorted in ascending order.
        assess.print_and_log(f"Processing pdf file: File {i + 1}/{pdfs_count}. Filename: {file_name}")
        file_id = file_dict[file_name]

        note_entry = ""
        note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
        csv_entry = ""

        # tokens for this paper
        tokens_this_paper = 0

        # Loop over criterion.
        list_of_sub_criteria_keys = list(assess.criteria.keys())
        for sub_criteria in list_of_sub_criteria_keys:
            sub_criteria_prompt = assess.criteria[sub_criteria]

            try:
                structured_response = call_openai_response_api_file_upload(sub_criteria_prompt,
                                                                           file_id, AssessmentResultPerCriteria)
            except Exception as e:
                exception = f"Error: {e}. Error prccessing {file_name}"
                note_entry += f"\n{exception}\n"
                assess.print_and_log(f"Processing Error. Exception: {exception}")
                continue

            # Reasoning field.
            note_entry += (f"\n{structured_response.output_parsed.criteria} = {structured_response.output_parsed.result}\n"
                           f"\n{structured_response.output_parsed.explanation}\n")
            # Append csv entry.
            csv_entry += (f"{structured_response.output_parsed.result},")  # comma at the end.
            # Responses tokens.
            tokens_this_paper += structured_response.usage.total_tokens

            time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

        assess.print_and_log(f"This paper ({file_name}) consumed {tokens_this_paper} tokens.")
        tokens_all_papers += tokens_this_paper

        assessment_notes.append(note_entry)
        full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
        assessment_summary.append(full_row)

    assess.print_and_log("Processed " + str(pdfs_count) + " papers.")
    assess.print_and_log("Consumed " + str(tokens_all_papers) + " for " + str(pdfs_count) + " papers.")
    # Save outputs
    assess.save_outputs(assessment_notes, assessment_summary)

### API Calls ###
@retry(wait=wait_exponential(multiplier=assess.retry_multiplier, min=assess.retry_min, max=assess.retry_max),
       retry=retry_if_exception_type(openai.RateLimitError))
def call_openai_response_api_plain_text_input(messages, document, output_format):
    """
    Function to call OpenAI API (Structured Output), intended for files parsed locally.
    :param messages: messages (prompt, string), document (string), output_format (pydantic class).
    :return: AssessmentResult
    """
    response = assess.client.responses.parse(
        model=assess.model_name,
        temperature=assess.model_temperature,
        instructions=assess.intro_prompt,
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
    return response

@retry(wait=wait_exponential(multiplier=assess.retry_multiplier, min=assess.retry_min, max=assess.retry_max),
       retry=retry_if_exception_type(openai.RateLimitError))
def call_openai_response_api_file_upload(messages, file_id, output_format):
    """
    Function to call OpenAI API (Structured Output), intended for files stored in OpenAI platform.
    :param messages: messages (prompt, string), file_id (string).
    :return: AssessmentResult
    """
    response = assess.client.responses.parse(
        model=assess.model_name,
        temperature=assess.model_temperature,
        instructions=assess.intro_prompt,
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

    return response
