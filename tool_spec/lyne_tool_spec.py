"""
Tool specification for Lyne Code.

This file defines the available tools,
including their descriptions, parameters, and use cases.
"""

# Define the specifications for Lyne tool functions
# Each entry includes:
# - name: The function name as defined in the tool modules
# - module: The module where the function resides
# - description: Explanation of what the function does
# - parameters: List of dictionaries describing each parameter (name, type, required, description)
# - use_cases: List of generic scenarios where this function is appropriate

LYNE_TOOL_SPEC = [
    {
        "name": "create_file",
        "module": "tool.create",
        "description": "Create a new file with optional content. Creates parent directories if they don't exist and handles permission errors gracefully.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to create, can include directories."},
            {"name": "content", "type": "str", "required": False, "default": "",
                "description": "Content to write to the file. Empty string creates an empty file."}
        ],
        "use_cases": [
            "When you need to create a new file that doesn't exist yet.",
            "When you want to generate a file with specific content.",
            "When you need to create an empty file as a placeholder.",
            "When you want to create a file in a directory structure that may not exist.",
            "When you need to create a file for storing data, configuration, or output."
        ]
    },
    {
        "name": "create_folder",
        "module": "tool.create",
        "description": "Create a new directory structure. Creates parent directories recursively and handles permission errors.",
        "parameters": [
            {"name": "folder_path", "type": "str", "required": True,
                "description": "Path to the directory to create, can include nested directories."}
        ],
        "use_cases": [
            "When you need to create a new directory that doesn't exist yet.",
            "When you want to organize files into a specific folder structure.",
            "When you need to create nested directories for organizing content.",
            "When you want to set up a working directory for temporary operations.",
            "When you need to create a directory for storing generated or output files."
        ]
    },
    {
        "name": "delete_file",
        "module": "tool.delete",
        "description": "Delete a single file with comprehensive error handling. Checks if file exists and is actually a file before deletion.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to delete."}
        ],
        "use_cases": [
            "When you need to remove a file that is no longer needed.",
            "When you want to clean up temporary or temporary files.",
            "When you need to delete old or outdated files.",
            "When you want to remove files that have been processed or backed up.",
            "When you need to clean up files to free up disk space."
        ]
    },
    {
        "name": "delete_folder",
        "module": "tool.delete",
        "description": "Delete a directory with optional recursive deletion. Can delete empty directories or entire directory trees.",
        "parameters": [
            {"name": "folder_path", "type": "str", "required": True,
                "description": "Path to the directory to delete."},
            {"name": "recursive", "type": "bool", "required": False, "default": False,
                "description": "Whether to delete non-empty directories and all contents."}
        ],
        "use_cases": [
            "When you need to remove a directory that is no longer needed.",
            "When you want to clean up temporary working directories.",
            "When you need to remove old or outdated directory structures.",
            "When you want to clean up directories after operations are complete.",
            "When you need to remove directories to free up disk space."
        ]
    },
    {
        "name": "write_lines",
        "module": "tool.edit",
        "description": "Insert new content at a specific line number in a text file. Preserves indentation and handles line range validation.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to edit."},
            {"name": "line_number", "type": "int", "required": True,
                "description": "Line number where to insert content (1-indexed)."},
            {"name": "content", "type": "str", "required": True,
                "description": "Content to insert, can be multi-line."}
        ],
        "use_cases": [
            "When you need to add new content at a specific position in a file.",
            "When you want to insert new lines or blocks of text in an existing file.",
            "When you need to add content while preserving the file's structure.",
            "When you want to insert new entries in a file at a specific location.",
            "When you need to add content without replacing existing content."
        ]
    },
    {
        "name": "replace_lines",
        "module": "tool.edit",
        "description": "Replace a range of lines with new content in a text file. Preserves indentation and handles line range validation.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to edit."},
            {"name": "start_line", "type": "int", "required": True,
                "description": "Starting line number (1-indexed, inclusive)."},
            {"name": "end_line", "type": "int", "required": True,
                "description": "Ending line number (1-indexed, inclusive)."},
            {"name": "content", "type": "str", "required": True,
                "description": "New content to replace the specified lines."}
        ],
        "use_cases": [
            "When you need to replace existing content with new content in a file.",
            "When you want to update a specific section of a file.",
            "When you need to modify multiple lines at once in a file.",
            "When you want to replace old content with updated or corrected content.",
            "When you need to change a block of text while keeping the rest of the file intact."
        ]
    },
    {
        "name": "delete_lines",
        "module": "tool.edit",
        "description": "Delete a range of lines from a text file. Handles line range validation and provides feedback on deleted content.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to edit."},
            {"name": "start_line", "type": "int", "required": True,
                "description": "Starting line number (1-indexed, inclusive)."},
            {"name": "end_line", "type": "int", "required": True,
                "description": "Ending line number (1-indexed, inclusive)."}
        ],
        "use_cases": [
            "When you need to remove specific lines or sections from a file.",
            "When you want to clean up unwanted content from a file.",
            "When you need to delete multiple lines at once in a file.",
            "When you want to remove outdated or incorrect content from a file.",
            "When you need to reduce the size of a file by removing unnecessary content."
        ]
    },
    {
        "name": "block_edit_file",
        "module": "tool.block_edit",
        "description": "Perform block-based file editing with diff preview. Finds and replaces text blocks intelligently, handling whitespace variations.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to edit."},
            {"name": "old_string", "type": "str", "required": True,
                "description": "Text block to replace (must include sufficient context)."},
            {"name": "new_string", "type": "str", "required": True,
                "description": "New text to insert in place of the old string."}
        ],
        "use_cases": [
            "When you need to replace a specific block of text in a file.",
            "When you want to update content that spans multiple lines.",
            "When you need to make changes while preserving the surrounding context.",
            "When you want to see a preview of changes before applying them.",
            "When you need to replace text that may have slight formatting variations."
        ]
    },
    {
        "name": "fetch_content",
        "module": "tool.read",
        "description": "Read file content with precise control. Supports range reads or full reads (up to ~1000 lines in one go). Automatically rejects binary files.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to read."},
            {"name": "start_line", "type": "int", "required": False, "default": 1,
                "description": "Starting line number (1-indexed, default: 1)."},
            {"name": "end_line", "type": "int", "required": False, "default": 200,
                "description": "Ending line number (inclusive). Leave empty to stream from start."}
        ],
        "use_cases": [
            "When you need to read the content of a single file.",
            "When you want to read only a specific section of a file.",
            "When you need to examine the full file.",
            "When you need to extract content from a file for processing or analysis.",
            "When you want to read file content without loading the entire file or binary data."
        ]
    },
    {
        "name": "read_many_files",
        "module": "tool.read_many",
        "description": "Read multiple files using glob patterns and concatenate their content. Automatically excludes common build artifacts and binary files.",
        "parameters": [
            {"name": "paths", "type": "list", "required": True,
                "description": "List of glob patterns or file paths to search for."},
            {"name": "include", "type": "list", "required": False, "default": None,
                "description": "Additional glob patterns to include."},
            {"name": "exclude", "type": "list", "required": False, "default": None,
                "description": "Glob patterns to exclude from search."},
            {"name": "use_default_excludes", "type": "bool", "required": False, "default": True,
                "description": "Whether to apply default exclusion patterns (build artifacts, etc.)."},
            {"name": "recursive", "type": "bool", "required": False, "default": True,
                "description": "Whether to search recursively in subdirectories."}
        ],
        "use_cases": [
            "When you need to read multiple files that match a specific pattern.",
            "When you want to combine content from several files into one view.",
            "When you need to process multiple files with similar content or structure.",
            "When you want to read files from different locations or directories.",
            "When you need to analyze content across multiple files simultaneously."
        ]
    },
    {
        "name": "grep_search",
        "module": "tool.grep",
        "description": "Advanced text search with multiple fallback strategies. Uses git grep, system grep, and Python fallback for maximum compatibility.",
        "parameters": [
            {"name": "pattern", "type": "str", "required": True,
                "description": "Regular expression pattern to search for."},
            {"name": "path", "type": "str", "required": True,
                "description": "Path to search in (required), CRITICAL: Must be an existing directory path, NEVER a file path."},
            {"name": "max_results", "type": "int", "required": False,
                "default": 100, "description": "Maximum number of results to return."},
            {"name": "include_pattern", "type": "str", "required": False, "default": None,
                "description": "Glob pattern to filter files (e.g., '*.py', '*.{js,ts}', '*.sql')."},
            {"name": "exclude_dirs", "type": "list", "required": False, "default": None,
                "description": "List of directories to exclude from search."}
        ],
        "when_not_to_use": [
            "NEVER use on individual files, always search directories to get comprehensive results.",
            "Don't use when you want to read the full context around matches, use search_and_read instead.",
            "Don't use for reading specific files, use fetch_content instead.",
            "Don't use when you need directory structure information, use get_folder_structure instead.",
            "Don't use when you want to get file listings, use find_files_by_pattern instead.",
        ],
        "use_cases": [
            "When you need to find specific text patterns across multiple files.",
            "When you want to search for content in files that match certain criteria.",
            "When you need to locate files that contain specific text or patterns.",
            "When you want to search through files while excluding certain directories.",
            "When you need to find occurrences of text across a large codebase or project."
        ]
    },
    {
        "name": "ast_grep_search",
        "module": "tool.ast_grep",
        "description": "High performance, parallel structural code search using the ast grep. This pure Python tool is optimized for speed on multi core systems, making it ideal for searching large folders and codebases",
        "parameters": [
            {"name": "pattern", "type": "str", "required": True,
                "description": "The AST pattern to search for. Must be a structurally complete and valid code snippet."},
            {"name": "path", "type": "str", "required": True,
                "description": "The directory or single file path to search in."},
            {"name": "max_results", "type": "int", "required": False, "default": 100,
                "description": "Maximum number of structural matches to return."},
            {"name": "lang", "type": "str", "required": False, "default": None,
                "description": "Programming language of the files (e.g., 'python', 'javascript'). If omitted, it's inferred from the file extension."}
        ],
        "pattern_guidance": {
            "title": "How to Write Effective AST Patterns:",
            "rules": [
                "CRITICAL: Patterns must be structurally complete. An `if` statement needs a body, a function definition needs a body, etc. Use wildcards to represent these parts.",
                "Use `$_` as a wildcard for a single statement, expression, or block of code.",
                "Use `$$$` as a wildcard for a sequence of multiple arguments, parameters, or statements.",
                "Use uppercase metavariables like `$NAME` or `$VAR` to capture specific code parts like identifiers or expressions.",
                "Metavariables act as placeholders for code, not text. They cannot be used for operators (like `+`) or inside string literals."
            ],
            "examples": [
                {"description": "Find all Python function definitions:",
                    "good_pattern": "def $NAME($$$): $_", "bad_pattern": "def $NAME", "reason": "The bad pattern is incomplete; it lacks parameters and a function body."},
                {"description": "Find all JavaScript arrow functions assigned to a const:",
                    "good_pattern": "const $NAME = ($$$) => { $$$ }", "bad_pattern": "const $NAME =", "reason": "The bad pattern is not a valid or complete AST node."},
                {"description": "Find if-statements with a specific function call:",
                    "good_pattern": "if some_function($$$): $_", "bad_pattern": "if some_function", "reason": "The bad pattern is an incomplete expression and statement."}
            ]
        },
        "when_not_to_use": [
            "This is a powerful, precise tool for finding specific code structures. It is not ideal for broad, exploratory searches.",
            "Consider using `grep_search` first if your goal is to simply find all textual occurrences of a variable or string across the entire codebase (including non-code files).",
            "When you only need a list of files or the directory structure; use `find_files_by_pattern` or `get_folder_structure`."
        ],
        "use_cases": [
            "To find specific code structures (e.g., all function definitions, class structures) across an entire codebase.",
            "For code analysis and identifying refactoring opportunities based on precise structural patterns.",
            "To perform language aware searches",
            "When performance is critical for searching through thousands of source code files."
        ]
    },
    {
        "name": "search_and_read",
        "module": "tool.search_and_read",
        "description": "Hybrid tool that combines text search with context reading. Searches for patterns and automatically reads surrounding context for each match, eliminating the need for separate search and read operations.",
        "parameters": [
            {"name": "pattern", "type": "str", "required": True,
                "description": "Regular expression pattern to search for."},
            {"name": "path", "type": "str", "required": True,
                "description": "Path to search in (required), CRITICAL: Must be an existing directory path, NEVER a file path."},
            {"name": "max_results", "type": "int", "required": False, "default": 20,
                "description": "Maximum number of search results to process and read context for (use atleast 20 for better results)."},
            {"name": "context_lines", "type": "int", "required": False, "default": 50,
                "description": "Number of lines to read before and after each match for context."},
            {"name": "include_pattern", "type": "str", "required": False, "default": None,
                "description": "Glob pattern to filter files (e.g., '*.py', '*.{js,ts}', '*.sql')."},
            {"name": "exclude_dirs", "type": "list", "required": False, "default": None,
                "description": "List of directories to exclude from search."}
        ],
        "when_not_to_use": [
            "NEVER use for reading specific files by exact path, use fetch_content instead.",
            "Don't use when you only need to find matches without context, use grep_search instead.",
            "Don't use for getting directory structure or file lists, use get_folder_structure or find_files_by_pattern instead.",
            "Don't use when you know the exact location of content in a specific file, use fetch_content with line ranges instead.",
        ],
        "use_cases": [
            "When you need to search for text and immediately get context around each match.",
            "When you want to understand the surrounding code or content without making separate calls.",
            "When you need to analyze search results with their full context in one operation.",
            "When you want to see the function, class, or section where a search term appears.",
            "When you need to quickly understand the context of multiple search results across different files."
        ]
    },
    {
        "name": "file_exists",
        "module": "tool.directory_utils",
        "description": "Check if a file exists at the specified path. Returns a boolean indicating file existence.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to check for existence."}
        ],
        "use_cases": [
            "When you need to verify if a file exists before attempting to read or modify it.",
            "When you want to check file existence as part of a conditional operation.",
            "When you need to validate file paths before processing them.",
            "When you want to ensure a file is available before proceeding with an operation."
        ]
    },
    {
        "name": "search_index",
        "module": "tool.search_index",
        "description": "Fuzzy NAME search over files and folders using Lyne's local index. Input is a file or folder name (or part of it), and the tool returns full entries {name, path, type}. Automatically builds the index if missing.",
        "parameters": [
            {"name": "query", "type": "str", "required": True,
                "description": "File/folder name (or partial) to search for, case-insensitive."},
            {"name": "limit", "type": "int", "required": False, "default": 25,
                "description": "Maximum results to return (1–100)."}
        ],
        "when_not_to_use": [
            "Do not use for content or code pattern searches — use grep_search, search_and_read, or ast_grep_search.",
            "Do not use for live directory listings — use directory tools when you need current structure."
        ],
        "use_cases": [
            "The agent has a file or folder NAME and needs its absolute path.",
            "Locate likely targets by NAME before invoking read/edit tools.",
            "Resolve uncertain/approximate names to check if a file/folder exists and discover its exact name."
        ],
        "limitations": [
            "Name-only search; does not inspect file content.",
            "Respects index excludes (e.g., node_modules, .git, lynecode, time_machine).",
            "Results may be stale until auto-refresh triggers."
        ]
    },
    {
        "name": "folder_exists",
        "module": "tool.directory_utils",
        "description": "Check if a folder exists at the specified path. Returns a boolean indicating folder existence.",
        "parameters": [
            {"name": "folder_path", "type": "str", "required": True,
                "description": "Path to the folder to check for existence."}
        ],
        "use_cases": [
            "When you need to verify if a directory exists before creating files in it.",
            "When you want to check directory existence before performing operations.",
            "When you need to validate folder paths before processing them.",
            "When you want to ensure a directory is available before proceeding with an operation."
        ]
    },
    {
        "name": "get_folder_structure",
        "module": "tool.directory_utils",
        "description": "Get the clean structure of a folder including subfolders and files. Returns organized folders and files without unnecessary metadata. For completely empty folders, returns a clear status message to avoid repetitive calls. Return type: Dictionary for populated folders, String for empty folders.",
        "parameters": [
            {"name": "folder_path", "type": "str", "required": True,
                "description": "Path to the folder to analyze."},
            {"name": "max_depth", "type": "int", "required": False, "default": 3,
                "description": "Maximum depth to explore in the folder structure."},
            {"name": "include_files", "type": "bool", "required": False, "default": True,
                "description": "Whether to include files in the structure output."},
            {"name": "include_hidden", "type": "bool", "required": False, "default": False,
                "description": "Whether to include hidden files and folders (starting with '.')."}
        ],
        "use_cases": [
            "When you need to understand the complete organization of a directory.",
            "When you want to explore the hierarchy of folders and files in a project.",
            "When you need to analyze the structure of a codebase or project directory.",
            "When you want to get an overview of what's inside a folder without unnecessary metadata."
        ]
    },
    {
        "name": "get_file_info",
        "module": "tool.directory_utils",
        "description": "Get essential information about a file including name, size, extension, and read-only status.",
        "parameters": [
            {"name": "file_path", "type": "str", "required": True,
                "description": "Path to the file to get information for."}
        ],
        "use_cases": [
            "When you need to check essential file properties like size and extension.",
            "When you want to verify file permissions or access rights.",
            "When you need basic file information for processing decisions.",
            "When you want to understand file characteristics without unnecessary metadata."
        ]
    },
    {
        "name": "find_files_by_pattern",
        "module": "tool.directory_utils",
        "description": "Find files matching a glob pattern with options for recursive search and result limiting.",
        "parameters": [
            {"name": "pattern", "type": "str", "required": True,
                "description": "Glob pattern to search for (e.g., '*.py', '*.{txt,md}', '*.{js,ts,jsx}', '*.sql')."},
            {"name": "root_path", "type": "str", "required": True,
                "description": "Root directory to search in (required)."},
            {"name": "recursive", "type": "bool", "required": False, "default": True,
                "description": "Whether to search recursively through subdirectories."},
            {"name": "max_results", "type": "int", "required": False,
                "default": 100, "description": "Maximum number of results to return."}
        ],
        "use_cases": [
            "When you need to find all files of a specific type across a directory structure.",
            "When you want to locate files matching certain naming patterns or extensions.",
            "When you need to discover files for batch processing or analysis.",
            "When you want to find configuration files, source files, or documentation files."
        ]
    },
    {
        "name": "get_path_type",
        "module": "tool.directory_utils",
        "description": "Determine whether a path refers to a file, folder, or doesn't exist. Simple utility for path validation.",
        "parameters": [
            {"name": "path", "type": "str", "required": True,
                "description": "Path to check and determine its type."}
        ],
        "use_cases": [
            "When you need to quickly determine what type of path you're working with.",
            "When you want to validate paths before performing file or directory operations.",
            "When you need to distinguish between files and folders in a path.",
            "When you want to check if a path exists and what it refers to."
        ]
    },
    {
        "name": "get_common_paths",
        "module": "tool.directory_utils",
        "description": "Get organized overview of common paths in a directory, just files and folders for quick navigation.",
        "parameters": [
            {"name": "root_path", "type": "str", "required": True,
                "description": "Root directory to analyze (required)."},
            {"name": "max_depth", "type": "int", "required": False, "default": 2,
                "description": "Maximum depth to explore for categorization."}
        ],
        "use_cases": [
            "When you need a quick overview of what's available in a directory.",
            "When you want to understand the basic structure of files and folders in a project.",
            "When you need to get a simple list of available paths for navigation.",
            "When you want to get an organized view of a directory structure without unnecessary categorization."
        ]
    },
    {
        "name": "get_git_changes",
        "module": "tool.git_changes",
        "description": "Read git changes including status, diff, and commit history. Handles cases where git is not available or not in a git repository gracefully.",
        "parameters": [
            {"name": "path", "type": "str", "required": True,
                "description": "Path to check for git repository (required)."},
            {"name": "include_status", "type": "bool", "required": False, "default": True,
                "description": "Whether to include git status information."},
            {"name": "include_diff", "type": "bool", "required": False, "default": True,
                "description": "Whether to include unstaged changes diff."},
            {"name": "include_staged", "type": "bool", "required": False,
                "default": False, "description": "Whether to include staged changes diff."},
            {"name": "include_log", "type": "bool", "required": False, "default": False,
                "description": "Whether to include recent commit history."},
            {"name": "max_log_entries", "type": "int", "required": False, "default": 5,
                "description": "Maximum number of commit log entries to include."},
            {"name": "specific_file", "type": "str", "required": False,
                "default": None, "description": "Specific file path to limit changes to."}
        ],
        "use_cases": [
            "When you need to see what files have been modified in a git repository.",
            "When you want to review unstaged or staged changes before committing.",
            "When you need to understand the current state of your git working directory.",
            "When you want to see recent commit history for context.",
            "When you need to check git changes for specific files only.",
            "When you want to see if you're ahead or behind the remote branch."
        ]
    },
    {
        "name": "linting_checker",
        "module": "tool.linting_checker",
        "description": "Check code quality issues in multiple files using appropriate linters for each supported language. Only Supports: Python (.py), C (.c), C++ (.cpp/.cc/.cxx/.h/.hpp), JavaScript (.js), SQL (.sql).",
        "parameters": [
            {"name": "file_paths", "type": "str or list", "required": True,
                "description": "Single file path (str) or list of file paths (max 10 files) to check for linting issues."}
        ],
        "when_not_to_use": [
            "NEVER use with JSX (.jsx), TypeScript (.ts), or TSX (.tsx) files or any other language files that are not supported",
            "Don't use for performance critical scenarios requiring immediate feedback."
        ],
        "use_cases": [
            "When you have edited a file and want to check that edit is not causing any issues",
            "When you need to check code quality across multiple files of different languages.",
            "When you want to get a comprehensive overview of code issues in a project.",
            "When you need to validate code quality before committing or deploying."
        ]
    },
    {
        "name": "semgrep_scan",
        "module": "tool.semgrep",
        "description": "Run Semgrep static analysis on specified path with optional config and severity filters.",
        "parameters": [
            {"name": "path", "type": "str", "required": True, "description": "Directory or file to scan. Agent can specify exact folder/file path."},
            {"name": "severity", "type": "list", "required": False, "default": None, "description": "Subset of ['INFO','WARNING','ERROR'] to include."},
            {"name": "max_results", "type": "int", "required": False, "default": 200, "description": "Limit number of findings returned."},
            {"name": "timeout_sec", "type": "int", "required": False, "default": 60, "description": "CLI timeout in seconds."}
        ],
        "use_cases": [
            "When you need to analyze code for security vulnerabilities, bugs, or code quality issues.",
            "When investigating potential security risks in codebases or specific files.",
            "When performing code reviews to catch common security patterns and anti-patterns.",
            "When you want to scan newly added or modified code for immediate feedback.",
            "When analyzing third-party code or inherited codebases for security assessment.",
            "When you need to identify hardcoded secrets, API keys, or credentials in code."
        ],
        "when_not_to_use": [
            "Don't use for runtime or dynamic analysis, this is static code analysis only.",
            "Avoid for very large codebases without focusing on specific directories first.",
            "Don't use when you only need basic syntax checking - use language-specific linters instead.",
            "Skip if you need real-time analysis during development - this is for batch scanning."
        ]
    },
    {
        "name": "run_terminal_command",
        "module": "tool.terminal",
        "description": "Run a terminal command within the project directory subtree with mandatory confirmation, environment auto-activation (if applicable)",
        "parameters": [
            {"name": "command", "type": "str or list", "required": True,
                "description": "The command to execute. If str, parsed into argv; shell is disabled."},
            {"name": "path", "type": "str", "required": True,
                "description": "Working directory to run the command in. Must be inside the current project path."},
            {"name": "auto_activate", "type": "bool", "required": False, "default": True,
                "description": "Automatically activate local Python venv and node_modules/.bin for PATH."},
            {"name": "timeout_sec", "type": "int", "required": False, "default": 60,
                "description": "Optional timeout override (45–60 seconds)."}
        ],
        "use_cases": [
            "Install dependencies with pip/pnpm/npm/yarn (supports shell globbing and pipes)",
            "Run formatters and linters (e.g., black, ruff, eslint, prettier) using local venv/node bins",
            "Project local scripts: npm run, npx scaffolds, python -m tools",
            "Download/inspect via curl/wget/ping within project context",
            "Unarchive, move, or list files under the project subtree only"
        ],
        "when_not_to_use": [
            "Never for system level operations or commands affecting outside the project",
            "Never to execute destructive commands (blocked by guardrails)",
            "Never run long lived/interactive servers (e.g., npm run dev, webpack --watch, gunicorn without --timeout); instead, do short checks with timeout_sec=30–45"
        ]
    },
        {
        "name": "web_search",
        "module": "tool.web_search",
        "description": "Search the web and return formatted per result blocks.",
        "parameters": [
            {"name": "query", "type": "str", "required": True, "description": "Search query string."},
            {"name": "max_results", "type": "int", "required": False, "default": 5, "description": "Max results (1–10)."},
            {"name": "time_range", "type": "str", "required": False, "default": "any", "description": "any|day|week|month|year (best effort)."},
            {"name": "safe_mode", "type": "bool", "required": False, "default": True, "description": "Filter adult results (best effort)."}
        ],
        "use_cases": [
            "Locate official docs for follow up reading with read_web_page",
            "Check latest library versions, release notes, and changelogs",
            "Troubleshoot errors via StackOverflow, GitHub Issues, discussions, Reddit threads",
            "Gather grounding information and authoritative references for summaries"
        ],
        "when_not_to_use": [
            "Do not use for private/intranet or authenticated resources",
            "Avoid paywalled content scraping or bypassing site protections",
            "Do not use for streaming/interactive pages requiring JS login flows"
        ]
    },
    {
        "name": "read_web_page",
        "module": "tool.web_reader",
        "description": "Open a link and extract readable text.",
        "parameters": [
            {"name": "url", "type": "str", "required": True, "description": "http/https URL to fetch."},
            {"name": "max_chars", "type": "int", "required": False, "default": 8000, "description": "Trim extracted text to this length (≤20000)."},
            {"name": "include_links", "type": "bool", "required": False, "default": False, "description": "Include up to 20 outbound links."}
        ],
        "use_cases": [
            "Read documentation, blog posts, announcements, and news articles",
            "Extract key content from reference pages and public specs",
            "List outbound links for deeper navigation"
        ],
        "when_not_to_use": [
            "Do not use for pages requiring authentication or paywalls",
            "Avoid interactive apps/dashboards that need client side login",
            "Do not fetch non http/https or binary content"
        ]
    }
]
