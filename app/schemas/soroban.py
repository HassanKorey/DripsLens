from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class SorobanContractSchema(BaseModel):
    id: str = Field(description="The Soroban contract ID")
    wasm_id: Optional[str] = Field(None, description="The WASM hash of the contract")
    health_score: int = Field(0, description="Health score 0-100")
    is_verified: bool = Field(False, description="Verification status")

class ContractEventSchema(BaseModel):
    id: str = Field(description="Event ID")
    contract_id: str = Field(description="Originating contract ID")
    topic: str = Field(description="Event topic")
    data: Dict[str, Any] = Field(description="Event payload")
    ledger_sequence: int = Field(description="Ledger sequence")
