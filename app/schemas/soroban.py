from typing import Any

from pydantic import BaseModel, Field


class SorobanContractSchema(BaseModel):
    id: str = Field(..., description="Unique Stellar Soroban contract address/ID (starts with 'C')")
    wasm_id: str | None = Field(None, description="The SHA-256 WASM bytecode hash of the deployed contract")
    health_score: int = Field(0, description="Heuristic contract health score ranging from 0 to 100")
    is_verified: bool = Field(False, description="Verification status indicating if source code matches bytecode")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "CA3D5KRYM6GYKAOWBZ75QHSQZSZEXLNRD4QMSI6LQI4TZQTHDV5BGY7V",
                "wasm_id": "7b01859664539ef4599a007f309a96f6fc19a86e9cd87c4a0aa2fe062a4fa95e",
                "health_score": 95,
                "is_verified": True,
            }
        }
    }


class ContractEventSchema(BaseModel):
    id: str = Field(..., description="Globally unique identifier of the indexed Soroban event")
    contract_id: str = Field(..., description="Originating Stellar Soroban contract ID")
    topic: str = Field(..., description="Primary topic or symbol signature of the emitted event (e.g. transfer)")
    data: dict[str, Any] = Field(..., description="Parsed JSON-compatible payload data of the event")
    ledger_sequence: int = Field(..., description="Stellar ledger sequence number where transaction closed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "evt_01HZX87654321",
                "contract_id": "CA3D5KRYM6GYKAOWBZ75QHSQZSZEXLNRD4QMSI6LQI4TZQTHDV5BGY7V",
                "topic": "transfer",
                "data": {"from": "G...", "to": "G...", "amount": "1000000"},
                "ledger_sequence": 51249302,
            }
        }
    }


class ContractMetricsSchema(BaseModel):
    contract_id: str = Field(..., description="Stellar Soroban contract identifier")
    wasm_size_bytes: int = Field(..., description="Compiled WASM binary size in bytes")
    invocation_count: int = Field(..., description="Total cumulative invocation counter recorded by the indexer")

    model_config = {
        "json_schema_extra": {
            "example": {
                "contract_id": "CA3D5KRYM6GYKAOWBZ75QHSQZSZEXLNRD4QMSI6LQI4TZQTHDV5BGY7V",
                "wasm_size_bytes": 1024,
                "invocation_count": 50,
            }
        }
    }


class ContractTTLSchema(BaseModel):
    contract_id: str = Field(..., description="Stellar Soroban contract identifier")
    liveUntilLedgerSeq: int = Field(..., description="Stellar ledger sequence until which the instance entry is live")
    remaining_days: int = Field(..., description="Estimated remaining lifespan in days before storage rent expiry")

    model_config = {
        "json_schema_extra": {
            "example": {
                "contract_id": "CA3D5KRYM6GYKAOWBZ75QHSQZSZEXLNRD4QMSI6LQI4TZQTHDV5BGY7V",
                "liveUntilLedgerSeq": 999999,
                "remaining_days": 30,
            }
        }
    }


class ContractHealthSchema(BaseModel):
    contract_id: str = Field(..., description="Stellar Soroban contract identifier")
    health_score: int = Field(..., description="Calculated WASM analyzer security and health score (0-100)")
    exported_functions: int = Field(..., description="Count of exported callable function interfaces in the WASM binary")

    model_config = {
        "json_schema_extra": {
            "example": {
                "contract_id": "CA3D5KRYM6GYKAOWBZ75QHSQZSZEXLNRD4QMSI6LQI4TZQTHDV5BGY7V",
                "health_score": 95,
                "exported_functions": 5,
            }
        }
    }