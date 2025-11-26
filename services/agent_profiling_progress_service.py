"""
Agent Profiling Progress Service
=================================

Tracks progress of agent profiling batch jobs to enable recovery from failures.
Stores completed and failed agents in a JSON file.
"""

import json
from pathlib import Path
from typing import Dict, List, Set, Any
from datetime import datetime


class AgentProfilingProgressService:
    """Service for tracking agent profiling progress"""

    PROGRESS_FILE = Path(__file__).parent.parent / "data" / "agent_profiling_progress.json"

    @classmethod
    def _ensure_file_exists(cls):
        """Ensure the progress file and directory exist"""
        cls.PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not cls.PROGRESS_FILE.exists():
            cls._save_progress({
                "started_at": None,
                "last_updated_at": None,
                "completed": [],
                "failed": [],
                "total_agents": 0,
                "session_id": None
            })

    @classmethod
    def _load_progress(cls) -> Dict[str, Any]:
        """Load progress from JSON file"""
        cls._ensure_file_exists()
        with open(cls.PROGRESS_FILE, 'r') as f:
            return json.load(f)

    @classmethod
    def _save_progress(cls, progress: Dict[str, Any]):
        """Save progress to JSON file"""
        cls._ensure_file_exists()
        progress["last_updated_at"] = datetime.now().isoformat()
        with open(cls.PROGRESS_FILE, 'w') as f:
            json.dump(progress, indent=2, fp=f)

    @classmethod
    def start_session(cls, total_agents: int) -> str:
        """
        Start a new profiling session

        Args:
            total_agents: Total number of agents to process

        Returns:
            Session ID (timestamp-based)
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        progress = {
            "started_at": datetime.now().isoformat(),
            "last_updated_at": datetime.now().isoformat(),
            "completed": [],
            "failed": [],
            "total_agents": total_agents,
            "session_id": session_id
        }
        cls._save_progress(progress)
        print(f"[ProgressTracker] Started session {session_id} for {total_agents} agents")
        return session_id

    @classmethod
    def is_agent_processed(cls, agent_contact: str) -> bool:
        """
        Check if an agent has already been successfully processed

        Args:
            agent_contact: Agent phone number

        Returns:
            True if agent is in completed list
        """
        progress = cls._load_progress()
        return agent_contact in progress.get("completed", [])

    @classmethod
    def mark_completed(cls, agent_contact: str):
        """
        Mark an agent as successfully completed

        Args:
            agent_contact: Agent phone number
        """
        progress = cls._load_progress()
        if agent_contact not in progress["completed"]:
            progress["completed"].append(agent_contact)
            # Remove from failed list if present
            if agent_contact in progress.get("failed", []):
                progress["failed"].remove(agent_contact)
            cls._save_progress(progress)
            completed_count = len(progress["completed"])
            total = progress.get("total_agents", 0)
            print(f"[ProgressTracker] ✓ Marked {agent_contact} as completed ({completed_count}/{total})")

    @classmethod
    def mark_failed(cls, agent_contact: str, error_message: str):
        """
        Mark an agent as failed

        Args:
            agent_contact: Agent phone number
            error_message: Error message describing the failure
        """
        progress = cls._load_progress()
        if agent_contact not in progress.get("failed", []):
            progress["failed"].append(agent_contact)
            cls._save_progress(progress)
            print(f"[ProgressTracker] ✗ Marked {agent_contact} as failed: {error_message[:100]}")

    @classmethod
    def get_progress_summary(cls) -> Dict[str, Any]:
        """
        Get current progress summary

        Returns:
            Dictionary with progress statistics
        """
        progress = cls._load_progress()
        total = progress.get("total_agents", 0)
        completed = len(progress.get("completed", []))
        failed = len(progress.get("failed", []))
        remaining = total - completed - failed if total > 0 else 0

        return {
            "session_id": progress.get("session_id"),
            "started_at": progress.get("started_at"),
            "last_updated_at": progress.get("last_updated_at"),
            "total_agents": total,
            "completed_count": completed,
            "failed_count": failed,
            "remaining_count": remaining,
            "progress_percentage": round((completed / total * 100), 2) if total > 0 else 0,
            "completed_agents": progress.get("completed", []),
            "failed_agents": progress.get("failed", [])
        }

    @classmethod
    def get_agents_to_process(cls, all_agents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter agents list to only those not yet processed

        Args:
            all_agents: List of all agent dictionaries

        Returns:
            List of agents that still need to be processed
        """
        progress = cls._load_progress()
        completed_set = set(progress.get("completed", []))

        agents_to_process = [
            agent for agent in all_agents
            if agent.get("agent_contact") not in completed_set
        ]

        skipped = len(all_agents) - len(agents_to_process)
        if skipped > 0:
            print(f"[ProgressTracker] Skipping {skipped} already completed agents")

        return agents_to_process

    @classmethod
    def reset_progress(cls):
        """
        Reset/clear all progress tracking

        Use this to start fresh or after a successful complete batch
        """
        progress = {
            "started_at": None,
            "last_updated_at": datetime.now().isoformat(),
            "completed": [],
            "failed": [],
            "total_agents": 0,
            "session_id": None
        }
        cls._save_progress(progress)
        print("[ProgressTracker] Progress reset")

    @classmethod
    def get_failed_agents(cls) -> List[str]:
        """
        Get list of agents that failed processing

        Returns:
            List of agent contact numbers that failed
        """
        progress = cls._load_progress()
        return progress.get("failed", [])
