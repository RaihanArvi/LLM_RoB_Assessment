import os
import csv
import time
import yaml
import logging
import tiktoken
from openai import OpenAI
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

# Set tiktoken encoder.
enc = tiktoken.encoding_for_model(model_name)

# Between assessment sleep time in seconds
sleep_time = config.get("SleepTime", 0.5)

# File and folder setup
pdf_input_folder = config["pdf_input_files_folder"]
plain_text_input_folder = config["plain_text_input_files_folder"]
output_folder = config["output_files_folder"]
prompt_file = config["prompt_file_path"]
logger_output_folder = config["logger_output_folder"]

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

criteria = script["Criteria"]

# Prompt main body.
prompt_body = "\n".join(
    criteria.values())  # combine all criteria, the old code line outputs dictionaries of the criteria.

### Logger ###

t = time.localtime()
start_system_time = time.strftime("%d-%m-%Y_%H:%M:%S", t)

# File handler
os.makedirs(logger_output_folder, exist_ok=True)
# --- Setup logger ---
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(os.path.join(logger_output_folder, f"rob_log_{start_system_time}.log"), encoding="utf-8")]
)
logger = logging.getLogger("logger")

def print_and_log(*args, sep=" ", end="\n", file=None, flush=False):
    message = sep.join(str(a) for a in args)
    logger.info(message)                  # log to file
    print(message, sep=sep, end=end, file=file, flush=flush)  # print to console

### Methods ###

def save_outputs(notes, summary):
    with open(os.path.join(output_folder, f"assessment_notes_{start_system_time}.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(notes))
    print_and_log(f"Successfully saved assessment_notes_{start_system_time}.txt.")

    with open(os.path.join(output_folder, f"assessment_summary_{start_system_time}.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(summary)
    print_and_log(f"Successfully saved assessment_summary_{start_system_time}.csv.")


def get_number_of_stored_files():
    return len(client.files.list().data)

def delete_all_stored_files():
    files = client.files.list()
    for file in files.data:
        client.files.delete(file.id)
        logging.debug("Deleted file: " + file.filename)
        print_and_log("Deleted file: " + file.filename)
    print_and_log("Stored files deleted successfully.")

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
    print_and_log("Uploading " + str(len(os.listdir(pdf_input_folder))) + " files.")

    for file_name in sorted(os.listdir(pdf_input_folder)):
        if not file_name.lower().endswith(".pdf"):
            logging.warning("This file is not a pdf: " + file_name)
            continue

        file_path = os.path.join(pdf_input_folder, file_name)
        try:
            print_and_log("Uploading " + file_name)
            file = client.files.create(
                file=open(file_path, "rb"),
                purpose="assistants"
            )
            uploaded_files[file_name] = file.id
            print_and_log("Uploaded " + file_name)
            time.sleep(0.1)

        except Exception as e:
            print_and_log(f"Failed to upload {file_name}: {e}")

    return uploaded_files