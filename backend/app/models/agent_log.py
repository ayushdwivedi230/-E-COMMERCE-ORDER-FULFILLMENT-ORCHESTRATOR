import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.database import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(String(50), primary_key=True, index=True)
    order_id = Column(String(50), ForeignKey("orders.id"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # SUCCESS, FAILED, WARNING, HELD
    input_data = Column(Text, nullable=True)  # JSON or text snapshot
    output_data = Column(Text, nullable=True)  # JSON or text result
    execution_time_ms = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    order = relationship("Order", back_populates="agent_logs")
