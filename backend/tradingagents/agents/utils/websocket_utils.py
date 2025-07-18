"""Utilities for WebSocket progress updates in agents."""

from typing import Dict, Any, Optional


def create_agent_config(agent_name: str, step: Optional[str] = None) -> Dict[str, Any]:
    """Create a config dict with metadata for agent identification.
    
    Args:
        agent_name: Name of the agent (e.g., "News Analyst", "Fundamentals Analyst")
        step: Optional step description (e.g., "Collecting data", "Analyzing trends")
    
    Returns:
        Config dict with metadata for callbacks
    """
    metadata = {
        "agent_name": agent_name,
    }
    
    if step:
        metadata["step"] = step
    
    return {
        "metadata": metadata,
        "tags": [f"agent:{agent_name.lower().replace(' ', '_')}"],
    }