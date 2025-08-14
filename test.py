import yaml

# Load configuration from config.yaml
with open("config.yaml", "r") as config_file:
    config = yaml.safe_load(config_file)

prompt_file = config["prompt_file_path"]

# Load YAML prompt script
with open(prompt_file, "r") as f:
    script = yaml.safe_load(f)

criteria = script["Criteria"]

## start
list_of_sub_criteria_keys = list(criteria.keys())

## loop for one paper

# input_prompt_tokens = len(enc.encode(f"{prompt_body} || {document}"))
# print(f"Input Tokens: {str(input_prompt_tokens)}")

for sub_criteria in list_of_sub_criteria_keys:
    sub_criteria_prompt = criteria[sub_criteria]

    try:
        structured_response = call_openai_response_api_plain_text_input(sub_criteria_prompt, document, AssessmentResult)
    except Exception as e:
        exception = f"Error: {e}. Error prccessing {file_name}"
        print(f"Processing Error. Exception: {exception}")
        continue






