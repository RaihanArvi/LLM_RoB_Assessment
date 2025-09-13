import os
import time
import json
import openai
from typing import List
from functools import wraps
from RoBAssessment import Assessment
from core.schemas import AssessmentResultAllCriteria
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

class AllCriteria:

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
        assessment_notes.append("Assessing plain files locally. Assessing all criteria all at once per one paper.")
        assessment_summary: List[List[str]] = [self.assess.summary_header]
        self.assess.print_and_log("Assessing plain files locally. Assessing all criteria all at once per one paper.")

        # tokens
        tokens_all_papers = 0

        # Get only .txt and .md files
        plain_text_files = [
            f for f in sorted(os.listdir(self.assess.plain_text_input_folder))
            if f.lower().endswith((".txt", ".md"))
        ]
        pdfs_count = len(plain_text_files)
        for i, file_name in enumerate(plain_text_files):
            self.assess.print_and_log(f"Processing plain text: File {i + 1}/{pdfs_count}. Filename: {file_name}")

            note_entry = ""

            # Open markdown file.
            with open(os.path.join(self.assess.plain_text_input_folder, file_name), "r", encoding="utf-8") as f:
                document = f.read()

            note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
            try:
                structured_response, token_usage = (
                    self.call_openai_response_api_plain_text_input(self.assess.prompt_body,
                                                                   document, AssessmentResultAllCriteria))
            except Exception as e:
                exception = f"Error: {e}. Error processing {file_name}"
                note_entry += f"\n{exception}\n"
                self.assess.print_and_log(f"Processing Error. Exception: {exception}")
                continue

            note_entry += (f"\nFile: {file_name}\n"
                           f"\n{structured_response.explanation}")

            # token
            tokens_all_papers += token_usage
            self.assess.print_and_log(f"This paper ({file_name}) consumed {token_usage} tokens.")

            assessment_notes.append(note_entry)
            summary_row = structured_response.result.split(",")  # this is output from llm.
            full_row = [str(i + 1), file_name] + summary_row
            assessment_summary.append(full_row)
            time.sleep(self.assess.sleep_time)  # prevent TPM rate limit error, in second.

        self.assess.print_and_log("Processed " + str(pdfs_count) + " papers.")
        self.assess.print_and_log("Consumed "+str(tokens_all_papers) + " for "+str(pdfs_count)+" papers.")
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
        assessment_notes.append("Assessing PDFs stored in cloud. Assessing all criteria all at once per one paper.")
        assessment_summary: List[List[str]] = [self.assess.summary_header]
        self.assess.print_and_log("Assessing PDFs stored in cloud. Assessing all criteria all at once per one paper.")

        # tokens.
        tokens_all_papers = 0

        pdfs_count = len(file_dict.keys())
        for i, file_name in enumerate(sorted(file_dict.keys())):  # sorted in ascending order.
            self.assess.print_and_log(f"Processing pdf file: File {i + 1}/{pdfs_count}. Filename: {file_name}")
            file_id = file_dict[file_name]

            note_entry = ""
            note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"

            try:
                structured_response, token_usage = (
                    self.call_openai_response_api_file_upload(self.assess.prompt_body,
                                                              file_id, AssessmentResultAllCriteria))
            except Exception as e:
                exception = f"Error: {e}. Error processing {file_name}"
                note_entry += f"\n{exception}\n"
                self.assess.print_and_log(f"Processing Error. Exception: {exception}")
                continue

            note_entry += (f"\nTitle: {file_name}\n"
                           f"\n{structured_response.explanation}")

            # token
            tokens_all_papers += token_usage
            self.assess.print_and_log(f"This paper ({file_name}) consumed {token_usage} tokens.")

            assessment_notes.append(note_entry)
            summary_row = structured_response.result.split(",")  # this is output from llm.
            full_row = [str(i + 1), file_name] + summary_row
            assessment_summary.append(full_row)
            time.sleep(self.assess.sleep_time)  # prevent TPM rate limit error, in second.

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
            SystemMessage(content=self.assess.all_criteria_output_format),
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
                        {"type": "input_text", "text": self.assess.all_criteria_output_format},
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
