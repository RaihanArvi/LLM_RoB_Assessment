# LLM-based Risk-of-Bias Assessment

## Overview

Part of the **AIRS Project** of The University of British Columbia.

The **AIRS Risk-of-Bias CLI** is a command-line tool that automates risk-of-bias (RoB) assessments on academic papers using LLMs. It supports both **PDF inputs** (uploaded and processed with OpenAI models) and **plain-text/Markdown inputs**. The CLI integrates with large language models (LLMs) and provides structured outputs and logs.

## Features

* Run assessments in two modes:
  * **Per Sub-Criteria** (evaluate each sub-criterion separately)
  * **All Criteria** (evaluate all RoB criteria at once)
* Support for plain-text/Markdown assessments.
* Upload and manage PDF files for RoB assessment (OpenAI only).
* Configurable (API key, model, temperature, prompt, etc.).
* Organized outputs and logs.

## Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/RaihanArvi/LLM_RoB_Assessment.git
cd LLM_RoB_Assessment
pip install -r requirements.txt
```

You can run the CLI script directly:

```bash
python AIRS-RoBAssessment.py --help
```

## Usage

The CLI supports **subcommands** for different workflows.

### Global Options

**Model settings:**
* `--api-key` : API key for the LLM provider (e.g., OpenAI).
* `--model` : Model name (default: `gpt-4o`).
* `--temperature` : Model temperature (default: `0.0`).
* `--mode` : Assessment mode, `all-criteria` or `per-sub-criteria` (default: `per-sub-criteria`).

**Error handling:**
* `--sleep-time` : Delay between API calls (seconds).
* `--retry-multiplier` : Retry backoff multiplier.
* `--retry-minimum` : Minimum retry attempts.
* `--retry-maximum` : Maximum retry attempts.

**Input - output:**
* `--prompt-file-path` : Path to custom prompt YAML file.
* `--pdf-input-path` : Folder for PDF inputs (default: `pdf_papers`).
* `--plain-text-input-path` : Folder for text/markdown inputs (default: `markdown_files`).
* `--output` : Output folder (default: `output`).
* `--logs-output` : Logs folder (default: `logs`).

### Assessment Input Mode Subcommands:

#### Plain-Text assessment

```bash
 AIRS-RoBAssessment.py [GLOBAL_OPTIONS] assess-text start        # Run assessment on plain text/Markdown files
```

#### PDF operations / assessment (requires OpenAI models)

```bash
 AIRS-RoBAssessment.py [GLOBAL_OPTIONS] openai-pdf upload        # Upload PDFs for assessment
 AIRS-RoBAssessment.py [GLOBAL_OPTIONS] openai-pdf start         # Run assessment on stored PDFs
 AIRS-RoBAssessment.py [GLOBAL_OPTIONS] openai-pdf count         # Count stored PDFs
 AIRS-RoBAssessment.py [GLOBAL_OPTIONS] openai-pdf delete-all    # Delete all stored PDFs
```

### Assessment Modes:

`per-sub-criteria` (default, recommended): 

Pass each sub-criteria independently of other sub-criteria. Paper is passed through the number of sub-criteria in the prompt. Consumes more tokens, generates more detailed reasoning, and more accurate.

`all-criteria`:

Pass all sub-criteria all at once for one paper. One unique paper is only passed once. Consumes less tokens, generates less detailed reasoning, and less accurate.

### Supported Models:
This wrapper supports OpenAI, Google Gemini, and Anthropic Claude models. PDF operations currently only supported using OpenAI models.

**Available models:**

- [OpenAI Models](https://platform.openai.com/docs/models)
- [Anthropic Claude Models](https://docs.anthropic.com/en/docs/about-claude/models/overview#model-names)
- [Google Gemini Models](https://ai.google.dev/gemini-api/docs/models#model-variations)

## Examples

Upload PDF papers:

```bash
 AIRS-RoBAssessment.py --api-key sk-xxx openai-pdf upload
```

Run RoB assessment on PDFs with **per-sub-criteria** mode:

```bash
 AIRS-RoBAssessment.py --api-key sk-xxx --mode per-sub-criteria openai-pdf start
```

Run RoB assessment on Markdown files with **all-criteria** mode:

```bash
 AIRS-RoBAssessment.py --api-key sk-xxx --mode all-criteria assess-text start
```

Count stored PDFs:

```bash
 AIRS-RoBAssessment.py --api-key sk-xxx openai-pdf count
```

Delete stored PDFs:

```bash
 AIRS-RoBAssessment.py --api-key sk-xxx openai-pdf delete-all
```

## Input

This package takes a prompt file and either a set of pdf or markdown files.

### 1. Prompt

Prompt file is structured and is in `.yaml` format. A sample `prompt.yaml` file is included. Path to this file is specified in `--prompt-file-path`. Prompt has to strictly follow this format:

```yaml
Intro: |
  <intro text here>

Criteria:

- id: '<criteria id>'
  title: <criteria title>
  explanation: <criteria explanation if any>
  sub_criteria:

  - id: '<sub-criteria id>'
    title: <sub-criteria title>
    explanation: |
      <sub-criteria explanation here>
...
```

### 2. Paper Set
Paper set is either a set of `.pdf` or markdown `.md` files. Path to the folder containing this set is passed in `--pdf-input-path` and `--plain-text-input-path` respectively. PDF input uses OpenAI's PDF processing and only supported when using OpenAI models.


## Output

This packages will generate the following files after each assessment:

* **Assessment notes** file contains detailed reasoning for each decision on each sub criteria for each paper.
* **Assessment summary** csv file contains the summary results for each decision on each sub criteria.
* **Logs** are written to the `logs` folder. This contains token calculations, any errors that occurred during assessment, and other relevant information.

The output files will be generated inside the folder passed in `--output`.

## Requirements

* Python 3.8+
* Dependencies listed in `requirements.txt`
* OpenAI API key (if using OpenAI models)

## License

Open Source MIT License

---

[![Website](https://img.shields.io/badge/Website-Raihan_Arvi-red)](https://www.raihanarvi.com)
