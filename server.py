import os
import base64
import requests
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("GitHub Obsidian Reader", 
    instructions="This server can read notes from a GitHub-hosted Obsidian vault.")

# GitHub configuration from environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER")
GITHUB_REPO = os.getenv("GITHUB_REPO")
BASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

def get_file_from_github(file_path: str):
    """Get file content from GitHub API"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Obsidian-MCP-Server"
    }
    
    url = f"{BASE_URL}/contents/{file_path}"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 404:
        return None
    
    response.raise_for_status()
    return response.json()

def get_directory_from_github(dir_path: str = ""):
    """Get directory contents from GitHub API"""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Obsidian-MCP-Server"
    }
    
    if dir_path and dir_path.strip():
        url = f"{BASE_URL}/contents/{dir_path.strip()}"
    else:
        url = f"{BASE_URL}/contents"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 404:
        return None
    
    response.raise_for_status()
    return response.json()

@mcp.tool()
def read_note(file_path: str) -> str:
    """
    Read the contents of a markdown note from the GitHub vault.
    
    Args:
        file_path: Path to the markdown file (e.g., "notes/my-note.md" or just "my-note")
    
    Returns:
        The content of the note
    """
    # Add .md extension if not present
    if not file_path.endswith('.md'):
        file_path += '.md'
    
    print(f"🔍 Attempting to read: {file_path}")
    
    file_data = get_file_from_github(file_path)
    if not file_data:
        # Try some common locations
        common_paths = [
            f"notes/{file_path}",
            f"content/{file_path}",
            f"docs/{file_path}"
        ]
        
        for path in common_paths:
            print(f"🔍 Trying: {path}")
            file_data = get_file_from_github(path)
            if file_data:
                file_path = path
                break
        
        if not file_data:
            return f"❌ Note '{file_path}' not found. Available locations to try: root, notes/, content/, docs/"
    
    # Decode base64 content
    try:
        content = base64.b64decode(file_data['content']).decode('utf-8')
        return f"📄 **{file_path}**\n\n{content}"
    except Exception as e:
        return f"❌ Error reading file: {str(e)}"

@mcp.tool()
def list_notes(directory: str = "") -> str:
    """
    List all notes and directories in your GitHub Obsidian vault.
    
    Args:
        directory: Directory path to list (empty string for root directory)
    
    Returns:
        Formatted list of files and directories in the vault
    """
    print(f"📂 Listing contents of: {'root' if not directory else directory}")
    
    try:
        contents = get_directory_from_github(directory)
        if contents is None:
            return f"❌ Directory '{directory or 'root'}' not found in vault"
        
        # Organize contents
        markdown_files = []
        directories = []
        other_files = []
        
        for item in contents:
            if item['type'] == 'dir':
                directories.append(f"📁 {item['name']}/")
            elif item['name'].endswith('.md'):
                size_kb = round(item['size'] / 1024, 1) if item['size'] else 0
                markdown_files.append(f"📄 {item['name']} ({size_kb}KB)")
            else:
                other_files.append(f"📄 {item['name']}")
        
        # Build response
        result = []
        path_display = f"/{directory}" if directory else "root"
        result.append(f"📂 **Contents of {path_display}:**\n")
        
        if directories:
            result.append("**Directories:**")
            result.extend(sorted(directories))
            result.append("")
        
        if markdown_files:
            result.append("**Markdown Notes:**")
            result.extend(sorted(markdown_files))
            result.append("")
        
        if other_files:
            result.append("**Other Files:**")
            result.extend(sorted(other_files))
            result.append("")
        
        total_files = len(markdown_files) + len(other_files)
        result.append(f"**Total:** {len(directories)} directories, {len(markdown_files)} notes, {total_files} total files")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"❌ Error listing directory: {str(e)}"

if __name__ == "__main__":
    # Get port from Railway
    port = int(os.getenv("PORT", 8000))
    
    print("🚀 GitHub Obsidian MCP Server Starting...")
    print(f"📝 Vault: {GITHUB_OWNER}/{GITHUB_REPO}")
    print(f"🔧 Port: {port}")
    
    # Run with SSE transport for Claude remote integrations
    mcp.run(
        transport="sse",
        host="0.0.0.0",
        port=port
    )