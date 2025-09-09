import os
import time
import json
import openai
from functools import wraps
from typing import List
from pydantic import BaseModel, Field
from RoBAssessment import Assessment
from tenacity import Retrying, retry, wait_exponential, retry_if_exception_type
from langchain_core.messages import SystemMessage, HumanMessage


# Decorator
def retry_openai_dynamic(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # read instance-specific settings at CALL time
        rm = self.assess.retry_multiplier
        rmin = self.assess.retry_min
        rmax = self.assess.retry_max

        retryer = Retrying(
            wait=wait_exponential(multiplier=rm, min=rmin, max=rmax),
            retry=(
                    retry_if_exception_type(openai.RateLimitError)
                    | retry_if_exception_type(openai.APIConnectionError)
            ),
        )
        for attempt in retryer:
            with attempt:
                return method(self, *args, **kwargs)
    return wrapper


# Pydantic Class for Structured Output.
class AssessmentResultPerCriteria(BaseModel):
    """
    Output format for the risk-of-bias assessment.
    Each field requires explanation to guide the LLM in output generation.
    """
    explanation: str = Field(..., description="A detailed reasoning that supports the decision, based on evidence from the document.")
    result: str = Field(..., description="The overall decision for this item. Respond only with one of ['yes', 'no'].")


class PerCriteria:
    def __init__(self, assess: Assessment):
        self.assess = assess

    # ----- Methods ----- #
    def process_plain_text(self):
        """
        Process all the plain Markdown text locally. Saves assessment output files.
        Input: NA.
        Output: NA.
        """
        # Initialize output containers
        assessment_notes: List[str] = []
        assessment_notes.append(self.assess.notes_header)
        assessment_notes.append("Assessing plain files locally. Assessing one sub criteria at a time for one paper.")
        assessment_summary: List[List[str]] = [self.assess.summary_header]
        self.assess.print_and_log("Assessing plain files locally. Assessing one sub criteria at a time for one paper.")

        # token counter for all papers.
        tokens_all_papers = 0

        # Loop for one paper.
        # Get only .txt and .md files
        plain_text_files = [
            f for f in sorted(os.listdir(self.assess.plain_text_input_folder))
            if f.lower().endswith((".txt", ".md"))
        ]
        pdfs_count = len(plain_text_files)
        for i, file_name in enumerate(plain_text_files):
            self.assess.print_and_log(f"Processing plain text: File {i + 1}/{pdfs_count}. Filename: {file_name}")

            # Initialize note.
            note_entry = ""
            note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
            csv_entry = ""

            # token counter for this paper.
            tokens_this_paper = 0

            # Open markdown file.
            with open(os.path.join(self.assess.plain_text_input_folder, file_name), "r", encoding="utf-8") as f:
                document = f.read()

            for criteria_id, sub_crit_dict in self.assess.nested_subs.items():
                for sub_crit_id, sub_crit in sub_crit_dict.items():
                    sub_criteria_prompt = sub_crit["explanation"]

                    try:
                        structured_response, token_usage = self.call_openai_response_api_plain_text_input(sub_criteria_prompt, document,
                                                                                        AssessmentResultPerCriteria)
                    except Exception as e:
                        exception = f"Error: {e}. Error processing {file_name}"
                        note_entry += f"\n{exception}\n"
                        self.assess.print_and_log(f"Processing Error. Exception: {exception}")
                        continue

                    # Reasoning field.
                    note_entry += (f"\n{sub_crit_id}) {sub_crit['title']} = {structured_response.result}\n"
                                   f"\n{structured_response.explanation}\n")

                    # Append csv entry.
                    csv_entry += f"{structured_response.result},"  # comma at the end.

                    # Responses tokens.
                    tokens_this_paper += token_usage
                    time.sleep(self.assess.sleep_time)  # prevent TPM rate limit error, in second.

            self.assess.print_and_log(f"This paper ({file_name}) consumed {tokens_this_paper} tokens.")
            tokens_all_papers += tokens_this_paper

            assessment_notes.append(note_entry)
            full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
            assessment_summary.append(full_row)

        self.assess.print_and_log("Processed " + str(pdfs_count) + " papers.")
        self.assess.print_and_log("Consumed "+str(tokens_all_papers) + " tokens for "+str(pdfs_count)+" papers.")
        # Save outputs
        self.assess.save_outputs(assessment_notes, assessment_summary)

    def process_pdf_stored_in_cloud(self, file_dict):
        """
        Process all the pdf stored in the cloud. Loop through the dictionary. Saves assessment output files.
        Input: {file_name: file_id} dictionary.
        Output: NA.
        """
        # Initialize output containers
        assessment_notes: List[str] = []
        assessment_notes.append(self.assess.notes_header)
        assessment_notes.append("Assessing PDFs stored in cloud. Assessing one sub criteria at a time for one paper.")
        assessment_summary: List[List[str]] = [self.assess.summary_header]
        self.assess.print_and_log("Assessing PDFs stored in cloud. Assessing one sub criteria at a time for one paper.")

        # Initialize token counter for all papers.
        tokens_all_papers = 0

        pdfs_count = len(file_dict.keys())
        for i, file_name in enumerate(sorted(file_dict.keys())):  # sorted in ascending order.
            self.assess.print_and_log(f"Processing pdf file: File {i + 1}/{pdfs_count}. Filename: {file_name}")
            file_id = file_dict[file_name]

            note_entry = ""
            note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
            csv_entry = ""

            # tokens for this paper
            tokens_this_paper = 0

            # Loop over criterion.
            for criteria_id, sub_crit_dict in self.assess.nested_subs.items():
                for sub_crit_id, sub_crit in sub_crit_dict.items():
                    sub_criteria_prompt = sub_crit["explanation"]

                    try:
                        structured_response, token_usage = self.call_openai_response_api_file_upload(sub_criteria_prompt,
                                                                                   file_id, AssessmentResultPerCriteria)
                    except Exception as e:
                        exception = f"Error: {e}. Error processing {file_name}"
                        note_entry += f"\n{exception}\n"
                        self.assess.print_and_log(f"Processing Error. Exception: {exception}")
                        continue

                    # Reasoning field.
                    note_entry += (f"\n{sub_crit_id}) {sub_crit['title']} = {structured_response.result}\n"
                                   f"\n{structured_response.explanation}\n")

                    # Append csv entry.
                    csv_entry += f"{structured_response.result},"  # comma at the end.
                    # Responses tokens.
                    tokens_this_paper += token_usage

                    time.sleep(self.assess.sleep_time)  # prevent TPM rate limit error, in second.

            self.assess.print_and_log(f"This paper ({file_name}) consumed {tokens_this_paper} tokens.")
            tokens_all_papers += tokens_this_paper

            assessment_notes.append(note_entry)
            full_row = [str(i + 1), file_name] + [p for p in csv_entry.split(",") if p]
            assessment_summary.append(full_row)

        self.assess.print_and_log("Processed " + str(pdfs_count) + " papers.")
        self.assess.print_and_log("Consumed " + str(tokens_all_papers) + " for " + str(pdfs_count) + " papers.")
        # Save outputs
        self.assess.save_outputs(assessment_notes, assessment_summary)

    # ----- API Calls ----- #

    @retry_openai_dynamic
    @retry(retry=retry_if_exception_type(openai.APIConnectionError))
    def call_openai_response_api_plain_text_input(self, messages, document, OutputFormat):
        prompts = [
            SystemMessage(content=self.assess.intro_prompt),
            SystemMessage(content=self.assess.pseudo_json_output_format),
            HumanMessage(content=f"{messages}\n\nHere is the paper:\n{document}")
        ]
        response = self.assess.llm.invoke(prompts)

        # Parsing
        data = json.loads(response.content)
        parsed_response = OutputFormat(**data)

        token_usage = response.usage_metadata["total_tokens"]
        return parsed_response, token_usage

    @retry_openai_dynamic
    @retry(retry=retry_if_exception_type(openai.APIConnectionError))
    def call_openai_response_api_file_upload(self, messages, file_id, OutputFormat):
        """
        Function to call OpenAI API (Structured Output), intended for files stored in OpenAI platform.
        :param OutputFormat:
        :param file_id:
        :param messages: messages (prompt, string), file_id (string).
        :return: AssessmentResult
        """
        response = self.assess.client.responses.create(
            model=self.assess.model_name,
            temperature=self.assess.temperature,
            instructions=self.assess.intro_prompt,
            input=[
                {
                    "role": "system",
                    "content": [
                        {"type": "input_text", "text": self.assess.pseudo_json_output_format},
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": messages},
                        {"type": "input_file", "file_id": file_id},
                    ],
                },
            ],
        )

        # Parsing
        data = json.loads(response.output_text)
        parsed_response = OutputFormat(**data)

        return parsed_response, response.usage.total_tokens
