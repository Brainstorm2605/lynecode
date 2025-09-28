"""
File: prompt_manager/__init__.py
Description: Initialization file for the prompt_manager package.
"""

import os
from typing import Dict, Optional, List
from .prompts import (
    PLANNER_PROMPT,
    MAIN_PROMPT
)

class PromptManager:
    """Manager for accessing system prompts"""
    
    def __init__(self):
        """Initialize the prompt manager with predefined prompts"""
        self.prompts: Dict[str, str] = {
            "planner_prompt": PLANNER_PROMPT,
            "main_prompt": MAIN_PROMPT
        }
    
    def get_prompt(self, prompt_name: str) -> Optional[str]:
        """
        Get a prompt by name.
        
        Args:
            prompt_name: Name of the prompt
            
        Returns:
            The prompt text or None if not found
        """
        prompt = self.prompts.get(prompt_name)
        if prompt is None:
            import logging
            logging.getLogger(__name__).warning(f"Prompt '{prompt_name}' not found in PromptManager.")
        return prompt
    
    def list_prompts(self) -> list:
        """
        List all available prompts.

        Returns:
            List of prompt names
        """
        return list(self.prompts.keys())

    def format_conversation_history_for_planner(self, conversation_context: List[Dict]) -> str:
        """
        Format conversation history for inclusion in planner prompt.

        Args:
            conversation_context: List of recent conversation messages

        Returns:
            Formatted conversation history string
        """
        if not conversation_context:
            return ""

        history_text = "\nRECENT CONVERSATION HISTORY:\n"
        for i, msg in enumerate(conversation_context, 1):
            history_text += f"\n--- Conversation {i} ---\n"
            history_text += f"User Query: {msg['query']}\n"
            history_text += f"Response: {msg['response']}\n"
            if 'tools_used' in msg and msg['tools_used']:
                history_text += "Tools Used:\n"
                for tool in msg['tools_used']:
                    history_text += f"  - {tool['tool_name']}: {tool['parameters']}\n"
            history_text += "\n"

        return history_text

    def format_conversation_history_for_main(self, conversation_context: List[Dict]) -> str:
        """
        Format conversation history for inclusion in main prompt.

        Args:
            conversation_context: List of recent conversation messages

        Returns:
            Formatted conversation history string
        """
        if not conversation_context:
            return ""

        history_text = "\nRECENT CONVERSATION CONTEXT:\n"
        for i, msg in enumerate(conversation_context, 1):
            history_text += f"\n--- Recent Chat {i} ---\n"
            history_text += f"Query: {msg['query']}\n"
            history_text += f"Response: {msg['response']}\n"
            if 'tools_used' in msg and msg['tools_used']:
                filtered_tools = [tool for tool in msg['tools_used'] if tool['tool_name'] in [
                    'block_edit_file', 'write_lines', 'create_folder', 'create_file',
                    'get_folder_structure', 'delete_file', 'delete_folder', 'delete_lines'
                ]]
                if filtered_tools:
                    history_text += "Relevant Tools Used:\n"
                    for tool in filtered_tools:
                        history_text += f"  - {tool['tool_name']}: {tool['parameters']}\n"
            history_text += "\n"

        return history_text

# Create a default prompt manager instance
default_prompt_manager = PromptManager()

def get_prompt(prompt_name: str) -> Optional[str]:
    """
    Get a prompt by name using the default prompt manager.
    
    Args:
        prompt_name: Name of the prompt
        
    Returns:
        The prompt text or None if not found
    """
    return default_prompt_manager.get_prompt(prompt_name)

__all__ = ['PromptManager', 'get_prompt', 'default_prompt_manager']
