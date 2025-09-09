import os
import csv
import time
import yaml
import random
import logging
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI

"""
Script to extract structured data from a set of markdown-converted papers
using the OpenAI API, based on a protocol spreadsheet, and output a CSV.
"""


# Decorator to check any pdf operations uses OpenAI model only.
def requires_openai(method):
    """
    Decorator to ensure the current model is OpenAI before any PDF-related action.
    Raises ValueError with the required message if not.
    """
    def wrapper(self, *args, **kwargs):
        self._ensure_openai_for_pdfs()
        return method(self, *args, **kwargs)
    return wrapper


class Assessment:
    def __init__(
        self,
        apikey,
        model_name,
        temperature,
        mode,
        sleep_time,
        retry_multiplier,
        retry_min,
        retry_max,
        pdf_input_folder,
        plain_text_input_folder,
        output_folder,
        prompt_file,
        logger_output_folder,
    ):
        # Core config
        self.apikey = apikey
        self.model_name = model_name
        self.temperature = float(temperature)
        self.mode = mode
        self.sleep_time = float(sleep_time)
        self.retry_multiplier = float(retry_multiplier)
        self.retry_min = float(retry_min)
        self.retry_max = float(retry_max)

        # OpenAI & LLM
        self.client = None
        self.llm = None

        # Paths
        self.pdf_input_folder = pdf_input_folder
        self.plain_text_input_folder = plain_text_input_folder
        self.output_folder = output_folder
        self.prompt_file = prompt_file
        self.logger_output_folder = logger_output_folder

        # (Optional) basic checks / setup
        if not (0.0 <= self.temperature <= 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")

        for p in (
            self.pdf_input_folder,
            self.plain_text_input_folder,
            self.output_folder,
            self.logger_output_folder,
        ):
            os.makedirs(p, exist_ok=True)

        # Timestamp for filenames
        self.start_time_str = time.strftime("%d-%m-%Y_%H:%M:%S", time.localtime())

        # Prompt
        self.load_prompt_script(prompt_file)
        self.build_prompt_structures()
        self.initialize_model_backend()

        # Output format for per sub criteria.
        self.pseudo_json_output_format = '''
# Output Format
Please output the result STRICTLY in the format below:
{
  "explanation": str,
  "result": str
}
where explanation is a detailed reasoning that supports the decision, based on evidence from the document, and result is the overall decision for this item, respond only with one of ['yes', 'no'].
        '''

        # Output format for all criteria.
        self.all_criteria_output_format = self.generate_all_criteria_output_format()

        # Logger setup
        log_path = os.path.join(
            self.logger_output_folder, f"rob_log_{self.start_time_str}.log"
        )
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[logging.FileHandler(log_path, encoding="utf-8")],
        )
        self.logger = logging.getLogger("rob_logger")

        # Notes Header
        self.notes_header = fr"""
  ___  ___________  _____       ______          _           _   
 / _ \|_   _| ___ \/  ___|      | ___ \        (_)         | |  
/ /_\ \ | | | |_/ /\ `--. ______| |_/ / __ ___  _  ___  ___| |_ 
|  _  | | | |    /  `--. \______|  __/ '__/ _ \| |/ _ \/ __| __|
| | | |_| |_| |\ \ /\__/ /      | |  | | | (_) | |  __/ (__| |_ 
\_| |_/\___/\_| \_|\____/       \_|  |_|  \___/| |\___|\___|\__|
                                              _/ |              
                                             |__/               
Risk-of-Bias Assessment Results

LLM Model: {self.model_name}
Temperature: {self.temperature}
        """

    # -------- LLM Provider detection -------- #
    @staticmethod
    def is_openai_model(model_name: str | None) -> bool:
        return bool(model_name) and model_name.strip().lower().startswith("gpt-")

    def _ensure_openai_for_pdfs(self) -> None:
        """Guard: PDFs only supported for OpenAI models; ensure OpenAI client exists."""
        if not Assessment.is_openai_model(self.model_name):
            raise ValueError("pdfs upload only supported using openai models")

        if self.client is None:
            from openai import OpenAI
            api_key = self.apikey or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI API key is required for PDF operations.")
            self.client = OpenAI(api_key=api_key)

    @staticmethod
    def is_claude_model(model_name: str | None) -> bool:
        return bool(model_name) and model_name.strip().lower().startswith("claude-")

    @staticmethod
    def is_gemini_model(model_name: str | None) -> bool:
        return bool(model_name) and model_name.strip().lower().startswith("gemini-")

    def initialize_model_backend(self) -> None:
        """
        Create self.llm depending on model_name.
        Create self.client only for OpenAI (used for PDF file APIs).
        Required env/keys:
          - OpenAI:    self.apikey or env OPENAI_API_KEY
          - Claude:    self.apikey or env ANTHROPIC_API_KEY
          - Gemini:    self.apikey or env GOOGLE_API_KEY
        """
        # Clear any prior state
        self.client = None
        self.llm = None

        # ---- OpenAI
        if Assessment.is_openai_model(self.model_name):
            api_key = self.apikey or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("API key required for OpenAI models (OPENAI_API_KEY).")

            self.client = OpenAI(api_key=api_key)  # used for Files API (PDF ops)
            self.llm = ChatOpenAI(model=self.model_name, temperature=self.temperature)
            return

        # ---- Claude (Anthropic)
        if Assessment.is_claude_model(self.model_name):
            api_key = self.apikey or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("API key required for Claude models (ANTHROPIC_API_KEY).")

            self.llm = ChatAnthropic(
                model=self.model_name,
                temperature=self.temperature,
                api_key=api_key,
            )
            return

        # ---- Gemini (Google)
        if Assessment.is_gemini_model(self.model_name):
            api_key = self.apikey or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("API key required for Gemini models (GOOGLE_API_KEY).")

            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                temperature=self.temperature,
                google_api_key=api_key,
            )
            return

        raise ValueError(f"Unsupported model name: {self.model_name}")

    ######

    # ----- Prompt Loading ----- #
    def load_prompt_script(self, path: str) -> None:
        """Load YAML prompt script into self.script."""
        with open(path, "r", encoding="utf-8") as f:
            self.script = yaml.safe_load(f) or {}

    def build_prompt_structures(self) -> None:
        """Compute nested sub-criteria, prompt body, intro message, and CSV header list."""
        script = self.script or {}
        self.intro_prompt = script["Intro"]

        # Nested sub-criteria dict
        self.nested_subs = {
            crit["id"]: {
                sub["id"]: {
                    "title": sub.get("title", ""),
                    "explanation": sub.get("explanation", ""),
                }
                for sub in crit.get("sub_criteria", [])
            }
            for crit in script.get("Criteria", [])
        }

        # Prompt body (joined explanations)
        self.prompt_body = "\n\n".join(
            sub["explanation"].rstrip()
            for parent in self.nested_subs.values()
            for sub in parent.values()
            if sub["explanation"]
        )

        # CSV header
        CSVEntryHeader = "no, file_name"
        for criteria_id, sub_crit_dict in self.nested_subs.items():
            for sub_crit_id, sub_crit in sub_crit_dict.items():
                column_header = f", {sub_crit_id}) {sub_crit['title']}"
                CSVEntryHeader = "".join([CSVEntryHeader, column_header])
        self.summary_header = CSVEntryHeader.split(", ")

    def print_and_log(self, *args, sep=" ", end="\n", file=None, flush=False):
        message = sep.join(str(a) for a in args)
        self.logger.info(message)                  # log to file
        print(message, sep=sep, end=end, file=file, flush=flush)  # print to console

    def generate_all_criteria_output_format(self) -> str:
        top = """
# Output Format

Please output the result STRICTLY in the format below:
{
  "explanation": str,
  "result": str
}
where explanation is a detailed reasoning that supports the decision, based on evidence from the document, and result is the overall decision for this item, respond only with one of ['yes', 'no'].

For the "explanation" field, write the detailed reasoning of ALL criteria alongside the assessment result ["yes","no"] of the corresponding criteria. 

### "result" Field
For each reported outcome in the RCT, provide the evaluation results in the following format for the "result":

Only return a CSV entry with exactly the following columns, all lowercase:
        """

        result = []
        for criteria_id, sub_crit_dict in self.nested_subs.items():
            for sub_crit_id, sub_crit in sub_crit_dict.items():
                result.append(sub_crit["title"])
        column_names = "[" + ", ".join(f'"{item}"' for item in result) + "]"

        # Generate random yes/no for each column
        yn_entries = [random.choice(["yes", "no"]) for _ in result]
        example_row = (
                "  Example summary CSV entry:\n  " + ",".join(yn_entries)
        )

        bottom = f"""
Important:
- Return one row only, comma-separated.
- Exactly {len(result)} values in the order listed above.
- Each criteria must have its own value.
- If unsure or no information is available, write "NA".
- Never add or remove columns.
- Never merge multiple values into one field.
        """

        final_output_format = (
                top
                + "\n  " + column_names + "\n\n"
                + "  Example summary CSV entry:\n  " + example_row + "\n"
                + bottom
        )

        return final_output_format

    # ----- Methods ----- #

    def save_outputs(self, notes, summary):
        with open(os.path.join(self.output_folder, f"assessment_notes_{self.start_time_str}.txt"),
                  "w", encoding="utf-8") as f:
            f.write("\n".join(notes))
        self.print_and_log(f"Successfully saved {self.output_folder}/assessment_notes_{self.start_time_str}.txt.")

        with open(os.path.join(self.output_folder, f"assessment_summary_{self.start_time_str}.csv"),
                  "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(summary)
        self.print_and_log(f"Successfully saved {self.output_folder}/assessment_summary_{self.start_time_str}.csv.")

    @requires_openai
    def get_number_of_stored_files(self):
        return len(self.client.files.list().data)

    @requires_openai
    def delete_all_stored_files(self):
        files = self.client.files.list()
        for file in files.data:
            self.client.files.delete(file.id)
            logging.debug("Deleted file: " + file.filename)
            self.print_and_log("Deleted file: " + file.filename)
        self.print_and_log("All stored files deleted successfully.")

    @requires_openai
    def get_file_name_id_dict(self):
        file_dict = {}
        files = self.client.files.list()
        for file in files:
            file_dict[file.filename] = file.id
        return file_dict

    @requires_openai
    def upload_all_pdfs(self):
        """
        Uploads all .pdf files in the input folder to OpenAI.
        Returns a dictionary: {file_name: file_id}
        """
        uploaded_files = {}
        self.print_and_log("Uploading " + str(len(os.listdir(self.pdf_input_folder))) + " files.")

        for file_name in sorted(os.listdir(self.pdf_input_folder)):
            if not file_name.lower().endswith(".pdf"):
                logging.warning("This file is not a pdf: " + file_name)
                continue

            file_path = os.path.join(self.pdf_input_folder, file_name)
            try:
                self.print_and_log("Uploading " + file_name)
                file = self.client.files.create(
                    file=open(file_path, "rb"),
                    purpose="assistants"
                )
                uploaded_files[file_name] = file.id
                self.print_and_log("Uploaded " + file_name)
                time.sleep(0.1)

            except Exception as e:
                self.print_and_log(f"Failed to upload {file_name}: {e}")
        self.print_and_log("Successfully uploaded  " + str(len(os.listdir(self.pdf_input_folder))) + " files.")

        return uploaded_files