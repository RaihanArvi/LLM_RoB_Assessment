#!/usr/bin/env python3
import argparse
import os
import textwrap
from typing import Optional
from RoBAssessment.Assessment import Assessment
from RoBAssessment.AllCriteria import AllCriteria
from RoBAssessment.PerCriteria import PerCriteria


# ---------------- Runtime config ---------------- #

def apply_runtime_config(args: argparse.Namespace) -> None:
    """Apply runtime config (env vars etc.)."""
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key


# ---------------- PDF handlers ---------------- #

def pdf_upload(assess: Assessment) -> None:
    assess.upload_all_pdfs()


def pdf_count(assess: Assessment) -> None:
    print(f"Stored files count: {assess.get_number_of_stored_files()}")


def pdf_delete(assess: Assessment) -> None:
    count = assess.get_number_of_stored_files()
    assess.delete_all_stored_files()
    print(f"{count} files have been deleted.\nAll stored files deleted.")


def pdf_start(assess: Assessment, assess_mode: str) -> None:
    print("Starting assessment from stored files (PDFs)...")
    file_dict = assess.get_file_name_id_dict()
    # Choose which flow to run based on default/global '--mode'
    if assess_mode == "all-criteria":
        AllCriteria(assess).process_pdf_stored_in_cloud(file_dict)
    else:
        PerCriteria(assess).process_pdf_stored_in_cloud(file_dict)


# ---------------- Text handlers (separate ALL vs PER) ---------------- #

def text_start(assess: Assessment, assess_mode: str) -> None:
    if assess_mode == "all-criteria":
        print("Starting risk-of-bias assessment (plain text, ALL criteria)...")
        AllCriteria(assess).process_plain_text()
    else:
        print("Starting risk-of-bias assessment (plain text, PER sub-criteria)...")
        PerCriteria(assess).process_plain_text()

# ---------------- Argparse wiring ---------------- #


def add_global_options(p: argparse.ArgumentParser) -> None:
    # LLM
    p.add_argument("--api-key", dest="api_key", default=None, help="API key for LLM provider.")
    p.add_argument("--model", default="gpt-4o", help="Model name (OpenAI= gpt-*, Claude= claude-*, Gemini= gemini-*).")
    p.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature.")
    p.add_argument(
        "--mode",
        choices=["all-criteria", "per-sub-criteria"],
        default="per-sub-criteria",
        help="Default assessment mode.",
    )

    # Error handling
    p.add_argument("--sleep-time", type=int, default=2, help="Sleep time between API calls (seconds).")
    p.add_argument("--retry-multiplier", type=int, default=1, help="Retry backoff multiplier.")
    p.add_argument("--retry-minimum", type=int, default=4, help="Minimum retry attempts.")
    p.add_argument("--retry-maximum", type=int, default=10, help="Maximum retry attempts.")

    # Prompt & I/O
    p.add_argument("--prompt-file-path", default=None, help="Path to the prompt YAML.")
    p.add_argument("--pdf-input-path", default="pdf_papers", help="Folder for PDF inputs.")
    p.add_argument("--plain-text-input-path", default="markdown_files", help="Folder for plain-text/markdown inputs.")
    p.add_argument("--output", default="output", help="Folder for outputs.")
    p.add_argument("--logs-output", default="logs", help="Folder for logs.")


def build_parser() -> argparse.ArgumentParser:
    description = textwrap.dedent("""
        LLM-Based Risk-of-Bias Assessment Tool (argparse CLI)

        Subcommands:

          pdf upload|start|count|delete
          all text start
          per text start
    """)
    parser = argparse.ArgumentParser(
        prog="rob-cli",
        description=description,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    add_global_options(parser)

    sub = parser.add_subparsers(dest="command", required=True)

    # --- openai-pdf (top-level) ---
    pdf = sub.add_parser("openai-pdf", help="PDF operations (OpenAI models only).")
    pdf_sub = pdf.add_subparsers(dest="pdf_cmd", required=True)
    pdf_sub.add_parser("upload", help="Upload PDFs").set_defaults(action="pdf_upload")
    pdf_sub.add_parser("start", help="Start assessment from stored PDFs").set_defaults(action="pdf_start")
    pdf_sub.add_parser("count", help="Count stored PDFs").set_defaults(action="pdf_count")
    pdf_sub.add_parser("delete-all", help="Delete stored PDFs").set_defaults(action="pdf_delete")

    # --- markdown (top-level) ---
    plain_text = sub.add_parser("assess-text", help="Assess plain text/markdown text.")
    pt_sub = plain_text.add_subparsers(dest="pt_cmd", required=True)
    pt_sub.add_parser("start", help="Start assessment on plain text files.").set_defaults(
        action="text_start")

    return parser


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    apply_runtime_config(args)

    # Instantiate Assessment after parsing
    assess = Assessment(
        args.api_key,
        args.model,
        args.temperature,
        args.mode,               # default/global preference; text commands override via assess_mode
        args.sleep_time,
        args.retry_multiplier,
        args.retry_minimum,
        args.retry_maximum,
        args.pdf_input_path,
        args.plain_text_input_path,
        args.output,
        args.prompt_file_path,
        args.logs_output,
    )

    if args.command == "pdf" and not Assessment.is_openai_model(args.model):
        print("pdfs upload only supported using openai models")
        return 2

    # Dispatch
    action = getattr(args, "action", None)
    if action == "pdf_upload":
        pdf_upload(assess)
    elif action == "pdf_count":
        pdf_count(assess)
    elif action == "pdf_delete":
        pdf_delete(assess)
    elif action == "pdf_start":
        assess_mode = getattr(args, "assess_mode", args.mode)
        pdf_start(assess, assess_mode)
    elif action == "text_start":
        assess_mode = getattr(args, "assess_mode", args.mode)
        text_start(assess, assess_mode)
    else:
        parser.print_help()
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
