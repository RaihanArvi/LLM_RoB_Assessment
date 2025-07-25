import os
import csv
import time
import yaml
import logging
from openai import OpenAI
from typing import List
from pydantic import BaseModel

"""
Script to extract structured data from a set of markdown-converted papers
using the OpenAI API, based on a protocol spreadsheet, and output a CSV.
"""

# Load configuration from config.yaml
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

# Set OpenAI API key and model
apikey = config["api_key"]
client = OpenAI(api_key=apikey)
model_name = config.get("model", "gpt-4o")  # default gpt-4o
mode = config.get("mode", "one_by_one")  # default to one_by_one
model_temperature = config["temperature"]

# Between paper sleep time in seconds
sleep_time = config.get("SleepTime", 0.5)

# File and folder setup
pdf_input_folder = config["pdf_input_files_folder"]
plain_text_input_folder = config["plain_text_input_files_folder"]
output_folder = config["output_files_folder"]
prompt_file = config["prompt_file_path"]

# Load YAML prompt script
with open(prompt_file, "r") as f:
    script = yaml.safe_load(f)

# Create output folder
os.makedirs(output_folder, exist_ok=True)

# Summary Header
summary_header = config.get("CSVEntryHeader", "").split(", ")

# Notes Header
notes_header = r"""
  ___  ___________  _____       ______          _           _   
 / _ \|_   _| ___ \/  ___|      | ___ \        (_)         | |  
/ /_\ \ | | | |_/ /\ `--. ______| |_/ / __ ___  _  ___  ___| |_ 
|  _  | | | |    /  `--. \______|  __/ '__/ _ \| |/ _ \/ __| __|
| | | |_| |_| |\ \ /\__/ /      | |  | | | (_) | |  __/ (__| |_ 
\_| |_/\___/\_| \_|\____/       \_|  |_|  \___/| |\___|\___|\__|
                                              _/ |              
                                             |__/               
Risk-of-Bias Assessment Results

"""

# Intro message (including output format, according to AssessmentResult object).
intro_prompt = script["Intro"]
output_format_prompt = script["OutputFormat"]
intro_message = intro_prompt + "\n" + output_format_prompt

# Prompt main body.
prompt_body = "\n".join(
    script["Criteria"].values())  # combine all criteria, the old code line outputs dictionaries of the criteria.

# Pydantic Class for Structured Output
class AssessmentResult(BaseModel):
    title: str
    authors: str
    overall_risk: str  # overall risk level for the study.
    explanation: str  # explanation per criteria alongside the risk level.
    summary: str  # csv entry for risk level per criteria.

####### Functions #######

def process_plain_text():
    """
    Process all the plain Markdown text locally. Saves assessment output files.
    Input: NA.
    Output: NA.
    """
    # Initialize output containers
    assessment_notes: List[str] = []
    assessment_notes.append(notes_header)
    assessment_notes.append("Assessing Plain Files Locally.")
    assessment_summary: List[List[str]] = [summary_header]

    pdfs_count = len(os.listdir(plain_text_input_folder))
    for i, file_name in enumerate(sorted(os.listdir(plain_text_input_folder))):
        print(f"Processing plain text: File {i + 1}/{pdfs_count}. Filename: {file_name}")

        note_entry = ""

        # Open markdown file.
        with open(os.path.join(plain_text_input_folder, file_name), "r", encoding="utf-8") as f:
            document = f.read()

        note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"
        try:
            structured_response = call_openai_response_api_plain_text_input(prompt_body, document)
        except Exception as e:
            exception = f"Error: {e}. Error prccessing {file_name}"
            note_entry += f"\n{exception}\n"
            print(f"Processing Error. Exception: {exception}")
            continue

        note_entry += (f"\n{structured_response.title}\n"
                       f"{structured_response.authors}\n"
                       f"{structured_response.overall_risk}"
                       f"\n{structured_response.explanation}")

        assessment_notes.append(note_entry)
        summary_row = structured_response.summary.split(",")  # this is output from llm.
        full_row = [str(i + 1), file_name, structured_response.title] + summary_row
        assessment_summary.append(full_row)
        time.sleep(sleep_time)  # prevent TPM rate limit error, in second.

    print("Processed " + str(pdfs_count) + " papers.")
    # Save outputs
    save_outputs(assessment_notes, assessment_summary)


def process_pdf_stored_in_cloud(file_dict):
    """
    Process all the pdf stored in the cloud. Loop through the dictionary. Saves assessment output files.
    Input: {file_name: file_id} dictionary.
    Output: NA.
    """
    # Initialize output containers
    assessment_notes: List[str] = []
    assessment_notes.append(notes_header)
    assessment_notes.append("Assessing PDFs Stored in Cloud.")
    assessment_summary: List[List[str]] = [summary_header]

    pdfs_count = len(file_dict.keys())
    for i, file_name in enumerate(sorted(file_dict.keys())):  # sorted in ascending order.
        print(f"Processing pdf file: File {i + 1}/{pdfs_count}. Filename: {file_name}")
        file_id = file_dict[file_name]

        note_entry = ""
        note_entry += f"\n=== Paper {i + 1}: {file_name} ===\n"

        try:
            structured_response = call_openai_response_api_file_upload(prompt_body, file_id)
        except Exception as e:
            exception = f"Error: {e}. Error prccessing {file_name}"
            note_entry += f"\n{exception}\n"
            print(f"Processing Error. Exception: {exception}")
            continue

        note_entry += (f"\n{structured_response.title}\n"
                       f"{structured_response.authors}\n"
                       f"{structured_response.overall_risk}"
                       f"\n{structured_response.explanation}")

        assessment_notes.append(note_entry)
        summary_row = structured_response.summary.split(",")  # this is output from llm.
        full_row = [str(i + 1), file_name, structured_response.title] + summary_row
        assessment_summary.append(full_row)
        time.sleep(sleep_time)  # prevent TPM rate limit error, in second.

    print("Processed " + str(pdfs_count) + " papers.")
    # Save outputs
    save_outputs(assessment_notes, assessment_summary)


def save_outputs(notes, summary):
    with open(os.path.join(output_folder, "assessment_notes.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes))
    print("Successfully saved assessment_notes.txt.")

    with open(os.path.join(output_folder, "assessment_summary.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(summary)
    print("Successfully saved assessment_summary.csv.")


def call_openai_response_api_file_upload(messages, file_id):
    """
    Function to call OpenAI API (Structured Output), intended for files stored in OpenAI platform.
    :param messages: messages (prompt, string), file_id (string).
    :return: AssessmentResult
    """
    response = client.responses.parse(
        model=model_name,
        temperature=model_temperature,
        instructions=intro_message,
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
        text_format=AssessmentResult,
    )

    return response.output_parsed


def call_openai_response_api_plain_text_input(messages, document):
    """
    Function to call OpenAI API (Structured Output), intended for files parsed locally.
    :param messages: messages (prompt, string), document (string).
    :return: AssessmentResult
    """
    response = client.responses.parse(
        model=model_name,
        temperature=model_temperature,
        instructions=intro_message,
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
        text_format=AssessmentResult,
    )

    return response.output_parsed


def get_number_of_stored_files():
    return len(client.files.list().data)


def delete_all_stored_files():
    files = client.files.list()
    for file in files.data:
        client.files.delete(file.id)
        logging.debug("Deleted file: " + file.filename)
        print("Deleted file: " + file.filename)
    print("Stored files deleted successfully.")


def get_file_name_id_dict():
    file_dict = {}
    files = client.files.list()
    for file in files:
        file_dict[file.filename] = file.id
    return file_dict


def upload_all_pdfs():
    """
    Uploads all .pdf files in the input folder to OpenAI.
    Returns a dictionary: {file_name: file_id}
    """
    uploaded_files = {}
    print("Uploading " + str(len(os.listdir(pdf_input_folder))) + " files.")

    for file_name in sorted(os.listdir(pdf_input_folder)):
        if not file_name.lower().endswith(".pdf"):
            logging.warning("This file is not a pdf: " + file_name)
            continue

        file_path = os.path.join(pdf_input_folder, file_name)
        try:
            print("Uploading " + file_name)
            file = client.files.create(
                file=open(file_path, "rb"),
                purpose="assistants"
            )
            uploaded_files[file_name] = file.id
            logging.debug("Uploaded: " + file_name)
            print("Uploaded " + file_name)
            time.sleep(0.1)

        except Exception as e:
            print(f"Failed to upload {file_name}: {e}")

    return uploaded_files