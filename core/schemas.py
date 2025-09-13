from pydantic import BaseModel, Field


# Pydantic Class for Structured Output. AllCriteria mode.
class AssessmentResultAllCriteria(BaseModel):
    """
    Output format for the risk-of-bias assessment.
    Each field requires explanation to guide the LLM in output generation.
    """
    explanation: str
    """"""
    result: str
    """"""


# Pydantic Class for Structured Output. PerCriteria mode.
class AssessmentResultPerCriteria(BaseModel):
    """
    Output format for the risk-of-bias assessment.
    Each field requires explanation to guide the LLM in output generation.
    """
    explanation: str = Field(..., description="A detailed reasoning that supports the decision, based on evidence from the document.")
    result: str = Field(..., description="The overall decision for this item. Respond only with one of ['yes', 'no'].")
