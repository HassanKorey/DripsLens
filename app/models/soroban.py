from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from app.db.database import Base

class SorobanContract(Base):
    __tablename__ = "soroban_contracts"
    id = Column(String, primary_key=True, index=True)
    wasm_id = Column(String)
    health_score = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)

class ContractEvent(Base):
    __tablename__ = "contract_events"
    id = Column(String, primary_key=True, index=True)
    contract_id = Column(String, ForeignKey("soroban_contracts.id"))
    topic = Column(String)
    data = Column(JSON)
    ledger_sequence = Column(Integer)

class StorageMetric(Base):
    __tablename__ = "storage_metrics"
    id = Column(Integer, primary_key=True, autoincrement=True)
    contract_id = Column(String, ForeignKey("soroban_contracts.id"))
    live_until_ledger_seq = Column(Integer)
