# LLM-Based Risk of Bias (RoB) Assessment Tool

Description (outdated):

This project automates the Risk of Bias (RoB) assessment of research papers using OpenAI's large language models. It supports both PDF and plain text inputs and outputs a structured CSV summary along with detailed reasoning.

This tool is a part of the AIRS Project.

## Requirements
- Python 3.7 or newer
#### Python packages:
- openai
- numpy
- pydantic

## Usage
```
python rob_assessment_cli.py
```

## Features:
- Easy to use command line user interface.
- Supports PDF upload or plain text input.
- Uses configurable, structured YAML-based prompt.
- Able to batch pre-upload or batch delete files stored in OpenAI Platform.
- Outputs both detailed notes and csv summary table.

## How to Run:
1. Install dependencies:
```
pip install -r requirements.txt
```

2. Place your .pdf or .txt files into the designated input folder specified in the `config.yaml` file.

3. Paste the prompt inside the `prompt.yaml`.
4. Adjust the `config.yaml` file.
4. Run the script:
```
python rob_assessment_cli.py
```
4. Navigate through the menus.

5. After processing, results will appear in the `output/` folder:
   - assessment_summary.csv
   - assessment_notes.txt
