import os
import time
import openai
from typing import List
from pydantic import BaseModel, Field
from RoBAssessment import Assessment as assess
from tenacity import retry, wait_exponential, retry_if_exception_type

# Pydantic Class for Structured Output.
class AssessmentResultPerCriteria(BaseModel):
    """
    Output format for the risk-of-bias assessment.
    Each field requires explanation to guide the LLM in output generation.
    """
    explanation: str = Field(..., description="A detailed reasoning that supports the decision, based on evidence from the document.")
    result: str = Field(..., description="The overall decision for this item. Respond only with one of ['yes', 'no'].")

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

    if assess.robust_mode == True:
        assessment_notes_raw: List[str] = []
        assessment_notes_raw.append(assess.notes_header)
        assessment_notes_raw.append("Raw notes. Assessing plain files locally. Assessing one criteria at a time for one paper.")
    else:
        assessment_notes_raw = None

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
        # Raw note.
        raw_note_entry = ""

        # token counter for this paper.
        tokens_this_paper = 0

        # Open markdown file.
        with open(os.path.join(assess.plain_text_input_folder, file_name), "r", encoding="utf-8") as f:
            document = f.read()

        for criteria_id, sub_crit_dict in assess.nested_subs.items():
            for sub_crit_id, sub_crit in sub_crit_dict.items():
                sub_criteria_prompt = sub_crit["explanation"]

                try:
                    if assess.robust_mode == True:
                        structured_response, response = call_openai_response_api_plain_text_input_robust(sub_criteria_prompt, document,
                                                                                    AssessmentResultPerCriteria)
                    else:
                        structured_response = call_openai_response_api_plain_text_input(sub_criteria_prompt, document,
                                                                                        AssessmentResultPerCriteria)
                except Exception as e:
                    exception = f"Error: {e}. Error prccessing {file_name}"
                    note_entry += f"\n{exception}\n"
                    assess.print_and_log(f"Processing Error. Exception: {exception}")
                    continue

                # Reasoning field.
                note_entry += (f"\n{sub_crit_id}) {sub_crit['title']} = {structured_response.output_parsed.result}\n"
                               f"\n{structured_response.output_parsed.explanation}\n")
                # Raw unparsed notes.
                if assess.robust_mode == True:
                    raw_note_entry += (f"\n{sub_crit_id}) {sub_crit['title']}:\n"
                                   f"\n{response.output_text}\n")
                # Append csv entry.
                csv_entry += (f"{structured_response.output_parsed.result},") # comma at the end.

                # Responses tokens.
                tokens_this_paper += structured_response.usage.total_tokens
                time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

        assess.print_and_log(f"This paper ({file_name}) consumed {tokens_this_paper} tokens.")
        tokens_all_papers += tokens_this_paper

        assessment_notes.append(note_entry)
        if assess.robust_mode == True:
            assessment_notes_raw.append(raw_note_entry)
        full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
        assessment_summary.append(full_row)

    assess.print_and_log("Processed " + str(pdfs_count) + " papers.")
    assess.print_and_log("Consumed "+str(tokens_all_papers) +" tokens for "+str(pdfs_count)+" papers.")
    # Save outputs
    assess.save_outputs(assessment_notes, assessment_summary, assessment_notes_raw)

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

    if assess.robust_mode == True:
        assessment_notes_raw: List[str] = []
        assessment_notes_raw.append(assess.notes_header)
        assessment_notes_raw.append("Raw notes. Assessing plain files locally. Assessing one criteria at a time for one paper.")
    else:
        assessment_notes_raw = None

    # Initialize token counter for all papers.
    tokens_all_papers = 0

    pdfs_count = len(file_dict.keys())
    for i, file_name in enumerate(sorted(file_dict.keys())):  # sorted in ascending order.
        assess.print_and_log(f"Processing pdf file: File {i + 1}/{pdfs_count}. Filename: {file_name}")
        file_id = file_dict[file_name]

        note_entry = ""
        note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
        csv_entry = ""
        raw_note_entry = ""

        # tokens for this paper
        tokens_this_paper = 0

        # Loop over criterion.
        for criteria_id, sub_crit_dict in assess.nested_subs.items():
            for sub_crit_id, sub_crit in sub_crit_dict.items():
                sub_criteria_prompt = sub_crit["explanation"]

                try:
                    if assess.robust_mode == True:
                        structured_response, response = call_openai_response_api_file_upload_robust(sub_criteria_prompt,
                                                                                   file_id, AssessmentResultPerCriteria)
                    else:
                        structured_response = call_openai_response_api_file_upload(sub_criteria_prompt,
                                                                                   file_id, AssessmentResultPerCriteria)
                except Exception as e:
                    exception = f"Error: {e}. Error prccessing {file_name}"
                    note_entry += f"\n{exception}\n"
                    assess.print_and_log(f"Processing Error. Exception: {exception}")
                    continue

                # Reasoning field.
                note_entry += (f"\n{sub_crit_id}) {sub_crit['title']} = {structured_response.output_parsed.result}\n"
                               f"\n{structured_response.output_parsed.explanation}\n")
                # Raw unparsed notes.
                if assess.robust_mode == True:
                    raw_note_entry += (f"\n{sub_crit_id}) {sub_crit['title']}:\n"
                                   f"\n{response.output_text}\n")
                # Append csv entry.
                csv_entry += (f"{structured_response.output_parsed.result},")  # comma at the end.
                # Responses tokens.
                tokens_this_paper += structured_response.usage.total_tokens

                time.sleep(assess.sleep_time)  # prevent TPM rate limit error, in second.

        assess.print_and_log(f"This paper ({file_name}) consumed {tokens_this_paper} tokens.")
        tokens_all_papers += tokens_this_paper

        assessment_notes.append(note_entry)
        if assess.robust_mode == True:
            assessment_notes_raw.append(raw_note_entry)
        full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
        assessment_summary.append(full_row)

    assess.print_and_log("Processed " + str(pdfs_count) + " papers.")
    assess.print_and_log("Consumed " + str(tokens_all_papers) + " for " + str(pdfs_count) + " papers.")
    # Save outputs
    assess.save_outputs(assessment_notes, assessment_summary, assessment_notes_raw)

### API Calls ###
@retry(wait=wait_exponential(multiplier=assess.retry_multiplier, min=assess.retry_min, max=assess.retry_max),
       retry=retry_if_exception_type(openai.RateLimitError))
@retry(retry=retry_if_exception_type(openai.APIConnectionError))
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
@retry(retry=retry_if_exception_type(openai.APIConnectionError))
def call_openai_response_api_plain_text_input_robust(messages, document, output_format):

    response = assess.client.responses.create(
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
        ]
    )

    parsed = assess.call_parser(response, output_format)
    parsed.usage.total_tokens = parsed.usage.total_tokens + response.usage.total_tokens
    return parsed, response

@retry(wait=wait_exponential(multiplier=assess.retry_multiplier, min=assess.retry_min, max=assess.retry_max),
       retry=retry_if_exception_type(openai.RateLimitError))
@retry(retry=retry_if_exception_type(openai.APIConnectionError))
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

@retry(wait=wait_exponential(multiplier=assess.retry_multiplier, min=assess.retry_min, max=assess.retry_max),
       retry=retry_if_exception_type(openai.RateLimitError))
@retry(retry=retry_if_exception_type(openai.APIConnectionError))
def call_openai_response_api_file_upload_robust(messages, file_id, output_format):
    """
    Function to call OpenAI API (Structured Output), intended for files stored in OpenAI platform. Uses two-step prompting.
    :param messages: messages (prompt, string), file_id (string).
    :return: AssessmentResult
    """
    response = assess.client.responses.create(
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
    )

    parsed = assess.call_parser(response, output_format)
    parsed.usage.total_tokens = parsed.usage.total_tokens + response.usage.total_tokens
    return parsed, response
