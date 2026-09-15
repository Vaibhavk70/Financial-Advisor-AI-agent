from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from typing import Literal
from enum import Enum
from typing import List, Optional




class LLMRouterOutput(BaseModel):
    """Output schema for router agent"""
    intent: Literal["SIMPLE", "COMPLEX"] = Field(description="Intent of the user query ")


router_output_parser = PydanticOutputParser(pydantic_object=LLMRouterOutput)