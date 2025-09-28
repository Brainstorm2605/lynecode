#!/usr/bin/env python3
"""
Conversation History Management System

Handles storage, retrieval, and management of conversation history for the Lyne system.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid


class ConversationHistory:
    """Manages conversation history storage and retrieval."""

    def __init__(self, history_dir: str = "output/conversation_history"):
        """Initialize conversation history manager."""
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.conversations_index_file = self.history_dir / "conversations_index.json"
        self._ensure_index_file()

    def _ensure_index_file(self):
        """Ensure the conversations index file exists."""
        if not self.conversations_index_file.exists():
            self._write_index({"conversations": []})

    def _read_index(self) -> Dict:
        """Read conversations index from file."""
        try:
            with open(self.conversations_index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"conversations": []}

    def _write_index(self, data: Dict):
        """Write conversations index to file."""
        try:
            with open(self.conversations_index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _get_conversation_file(self, conversation_id: str) -> Path:
        """Get the file path for a specific conversation."""
        return self.history_dir / f"{conversation_id}.json"

    def _read_conversation_file(self, conversation_id: str) -> Dict:
        """Read a specific conversation file."""
        conversation_file = self._get_conversation_file(conversation_id)
        try:
            with open(conversation_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def _write_conversation_file(self, conversation_id: str, data: Dict):
        """Write a specific conversation file."""
        conversation_file = self._get_conversation_file(conversation_id)
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def create_conversation(self, title: Optional[str] = None, project_path: Optional[str] = None) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        if not title:
            title = f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        if project_path:
            project_path = str(Path(project_path).resolve())

        conversation = {
            "id": conversation_id,
            "title": title,
            "created_at": timestamp,
            "updated_at": timestamp,
            "project_path": project_path,
            "messages": [],
            "attachments": []
        }

        self._write_conversation_file(conversation_id, conversation)

        index = self._read_index()
        index["conversations"].append({
            "id": conversation_id,
            "title": title,
            "created_at": timestamp,
            "updated_at": timestamp,
            "project_path": project_path
        })
        self._write_index(index)

        return conversation_id

    def add_message(self, conversation_id: str, query: str, response: str, tools_used: List[Dict] = None):
        """Add a message to a conversation."""
        if tools_used is None:
            tools_used = []

        message = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "response": response,
            "tools_used": tools_used
        }

        conversation = self._read_conversation_file(conversation_id)
        if conversation:
            conversation["messages"].append(message)
            conversation["updated_at"] = datetime.now().isoformat()
            self._write_conversation_file(conversation_id, conversation)

            index = self._read_index()
            for conv in index["conversations"]:
                if conv["id"] == conversation_id:
                    conv["updated_at"] = datetime.now().isoformat()
                    break
            self._write_index(index)

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get a specific conversation by ID."""
        return self._read_conversation_file(conversation_id)

    def get_recent_conversations(self, limit: int = 10, project_path: Optional[str] = None) -> List[Dict]:
        """Get recent conversations sorted by last update."""
        index = self._read_index()
        conversations = []

        if project_path:
            project_path = str(Path(project_path).resolve())

        for conv_info in index["conversations"]:
            if project_path and conv_info.get("project_path") != project_path:
                continue

            conversation = self._read_conversation_file(conv_info["id"])
            if conversation:
                conversations.append(conversation)

        conversations.sort(key=lambda x: x.get(
            "updated_at", x.get("created_at", "")), reverse=True)

        return conversations[:limit]

    def get_conversation_messages(self, conversation_id: str) -> List[Dict]:
        """Get messages from a specific conversation."""
        conversation = self.get_conversation(conversation_id)
        if conversation:
            return conversation.get("messages", [])
        return []

    def _ensure_attachments(self, conversation: Dict) -> None:
        if "attachments" not in conversation or not isinstance(conversation["attachments"], list):
            conversation["attachments"] = []

    def get_attachments(self, conversation_id: str) -> List[Dict]:
        conversation = self.get_conversation(conversation_id)
        if not conversation:
            return []
        self._ensure_attachments(conversation)
        return conversation.get("attachments", [])

    def add_attachment(self, conversation_id: str, type: str, path: str, name: str) -> None:
        conversation = self._read_conversation_file(conversation_id)
        if not conversation:
            return
        self._ensure_attachments(conversation)
        file_cap = 5
        folder_cap = 5
        if type == "file":
            if len([a for a in conversation["attachments"] if a.get("type") == "file"]) >= file_cap:
                return
        if type == "folder":
            if len([a for a in conversation["attachments"] if a.get("type") == "folder"]) >= folder_cap:
                return
        exists = any(a.get("path") == path for a in conversation["attachments"])
        if not exists:
            conversation["attachments"].append({
                "type": type,
                "path": path,
                "name": name
            })
            conversation["updated_at"] = datetime.now().isoformat()
            self._write_conversation_file(conversation_id, conversation)

    def remove_attachment(self, conversation_id: str, identifier: str) -> None:
        conversation = self._read_conversation_file(conversation_id)
        if not conversation:
            return
        self._ensure_attachments(conversation)
        identifier_l = identifier.lower()
        remaining = []
        removed = False
        for a in conversation["attachments"]:
            name = str(a.get("name", "")).lower()
            path = str(a.get("path", "")).lower()
            if identifier_l == name or identifier_l == path or identifier_l in name or identifier_l in path:
                removed = True
                continue
            remaining.append(a)
        if removed:
            conversation["attachments"] = remaining
            conversation["updated_at"] = datetime.now().isoformat()
            self._write_conversation_file(conversation_id, conversation)

    def clear_attachments(self, conversation_id: str) -> None:
        conversation = self._read_conversation_file(conversation_id)
        if not conversation:
            return
        self._ensure_attachments(conversation)
        if conversation["attachments"]:
            conversation["attachments"] = []
            conversation["updated_at"] = datetime.now().isoformat()
            self._write_conversation_file(conversation_id, conversation)

    def format_conversation_title(self, conversation: Dict) -> str:
        """Format conversation for display in menu."""
        created_at = datetime.fromisoformat(conversation["created_at"])
        readable_date = created_at.strftime("%Y-%m-%d %H:%M")
        message_count = len(conversation.get("messages", []))

        return f"{conversation['title']} ({readable_date}) - {message_count} messages"

    def get_filtered_tools_for_prompt(self, tools_used: List[Dict], allowed_tools: List[str]) -> List[Dict]:
        """Filter tools for inclusion in prompts based on allowed tool names."""
        return [tool for tool in tools_used if tool.get("tool_name") in allowed_tools]

    def get_conversation_context(self, conversation_id: str, max_messages: int = 3, include_tools: bool = False, allowed_tools: List[str] = None) -> List[Dict]:
        """Get recent conversation context for prompt inclusion."""
        if allowed_tools is None:
            allowed_tools = ["block_edit_file", "write_lines", "create_folder", "create_file",
                             "get_folder_structure", "delete_file", "delete_folder", "delete_lines"]

        messages = self.get_conversation_messages(conversation_id)
        recent_messages = messages[-max_messages:] if messages else []

        context_messages = []
        for msg in recent_messages:
            context_msg = {
                "query": msg["query"],
                "response": msg["response"]
            }

            if include_tools:
                context_msg["tools_used"] = self.get_filtered_tools_for_prompt(
                    msg.get("tools_used", []), allowed_tools)

            context_messages.append(context_msg)

        return context_messages
