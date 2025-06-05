#!/usr/bin/env python3
"""
GitHub Obsidian MCP Server - Fixed Version
Using proven patterns from GitHub's official MCP server
"""

import os
import base64
import logging
from typing import Optional, List, Dict, Any
import requests
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER") 
GITHUB_REPO = os.getenv("GITHUB_REPO")

if not all([GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO]):
    raise ValueError("Missing required environment variables: GITHUB_TOKEN, GITHUB_OWNER, GITHUB_REPO")

BASE_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"

# Initialize FastMCP server with proper instructions
mcp = FastMCP(
    name="GitHub Obsidian Vault",
    instructions="This server provides access to GitHub-hosted Obsidian vaults. Use get_file_contents to read notes and list_directory to browse folders."
)

class GitHubClient:
    """GitHub API client with proper error handling"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"obsidian-mcp-server"
        })
    
    def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make GitHub API request with error handling"""
        try:
            response = self.session.request(method, url, **kwargs)
            
            if response.status_code == 403 and 'rate limit' in response.text.lower():
                logger.error("GitHub API rate limit exceeded")
                raise Exception("GitHub API rate limit exceeded")
            
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API request failed: {e}")
            raise Exception(f"API request failed: {str(e)}")

# Initialize GitHub client
github = GitHubClient()

@mcp.tool()
def get_file_contents(owner: str, repo: str, path: str, ref: str = "") -> str:
    """
    Get contents of a file from the GitHub repository.
    
    Args:
        owner: Repository owner (e.g., "Hparryok")
        repo: Repository name (e.g., "NeoTerra") 
        path: File path (e.g., "Welcome.md" or "folder/note.md")
        ref: Git reference - branch, tag, or commit SHA (optional)
    
    Returns:
        The file content as text
    """
    try:
        # Build URL
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        params = {}
        if ref:
            params["ref"] = ref
        
        logger.info(f"📄 Reading file: {path} from {owner}/{repo}")
        
        # Make request
        response = github.make_request("GET", url, params=params)
        
        if response.status_code == 404:
            return f"❌ File '{path}' not found in {owner}/{repo}"
        
        response.raise_for_status()
        data = response.json()
        
        # Handle directory
        if isinstance(data, list):
            files = []
            dirs = []
            for item in data:
                if item['type'] == 'dir':
                    dirs.append(f"📁 {item['name']}/")
                else:
                    files.append(f"📄 {item['name']}")
            
            result = f"📂 Contents of /{path}:\n\n"
            if dirs:
                result += "**Directories:**\n" + "\n".join(dirs) + "\n\n"
            if files:
                result += "**Files:**\n" + "\n".join(files)
            return result
        
        # Handle file
        if data.get('type') == 'file':
            try:
                content = base64.b64decode(data['content']).decode('utf-8')
                return f"📄 **{path}**\n\n{content}"
            except Exception as e:
                return f"❌ Error decoding file content: {str(e)}"
        
        return f"❌ Unknown content type for {path}"
        
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return f"❌ Error reading file: {str(e)}"

@mcp.tool() 
def list_directory(owner: str, repo: str, path: str = "", ref: str = "") -> str:
    """
    List contents of a directory in the repository.
    
    Args:
        owner: Repository owner (e.g., "Hparryok")
        repo: Repository name (e.g., "NeoTerra")
        path: Directory path (empty for root)
        ref: Git reference - branch, tag, or commit SHA (optional)
    
    Returns:
        Formatted directory listing
    """
    try:
        # Build URL  
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}" if path else f"https://api.github.com/repos/{owner}/{repo}/contents"
        params = {}
        if ref:
            params["ref"] = ref
        
        logger.info(f"📂 Listing directory: /{path} from {owner}/{repo}")
        
        # Make request
        response = github.make_request("GET", url, params=params)
        
        if response.status_code == 404:
            return f"❌ Directory '{path}' not found in {owner}/{repo}"
        
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            return f"❌ '{path}' is not a directory"
        
        # Sort items
        files = []
        dirs = []
        
        for item in data:
            if item['type'] == 'dir':
                dirs.append(f"📁 {item['name']}/")
            elif item['name'].endswith('.md'):
                files.append(f"📝 {item['name']}")
            else:
                files.append(f"📄 {item['name']}")
        
        # Format output
        location = f"/{path}" if path else "/root"
        result = f"📂 **Contents of {location}:**\n\n"
        
        if dirs:
            result += "**📁 Directories:**\n" + "\n".join(sorted(dirs)) + "\n\n"
        
        if files:
            result += "**📄 Files:**\n" + "\n".join(sorted(files))
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing directory {path}: {e}")
        return f"❌ Error listing directory: {str(e)}"

@mcp.tool()
def search_code(owner: str, repo: str, query: str) -> str:
    """
    Search for content across all files in the repository.
    
    Args:
        owner: Repository owner (e.g., "Hparryok")
        repo: Repository name (e.g., "NeoTerra")
        query: Search query
    
    Returns:
        Search results with file paths and snippets
    """
    try:
        url = "https://api.github.com/search/code"
        params = {
            "q": f"{query} repo:{owner}/{repo}",
            "per_page": 20
        }
        
        logger.info(f"🔍 Searching for: {query} in {owner}/{repo}")
        
        response = github.make_request("GET", url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['total_count'] == 0:
            return f"🔍 No results found for '{query}'"
        
        results = [f"🔍 **Found {data['total_count']} results for '{query}':**\n"]
        
        for item in data['items'][:10]:  # Limit to top 10
            file_path = item['path']
            # Try to get a snippet if available
            if 'text_matches' in item:
                for match in item['text_matches'][:1]:  # Show first match
                    fragment = match.get('fragment', '').strip()
                    if fragment:
                        results.append(f"📄 **{file_path}**")
                        results.append(f"   ```\n   {fragment}\n   ```\n")
            else:
                results.append(f"📄 **{file_path}**\n")
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Error searching for {query}: {e}")
        return f"❌ Error searching: {str(e)}"

@mcp.tool()
def create_or_update_file(owner: str, repo: str, path: str, content: str, message: str, branch: str = "main") -> str:
    """
    Create or update a file in the repository.
    
    Args:
        owner: Repository owner
        repo: Repository name  
        path: File path
        content: File content
        message: Commit message
        branch: Branch name (default: main)
    
    Returns:
        Success message with commit details
    """
    try:
        # First check if file exists
        existing_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        existing_response = github.make_request("GET", existing_url)
        
        sha = None
        if existing_response.status_code == 200:
            sha = existing_response.json().get('sha')
        
        # Create/update file
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        data = {
            "message": message,
            "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
            "branch": branch
        }
        
        if sha:
            data["sha"] = sha
        
        logger.info(f"✏️ {'Updating' if sha else 'Creating'} file: {path}")
        
        response = github.make_request("PUT", url, json=data)
        response.raise_for_status()
        
        result = response.json()
        action = "Updated" if sha else "Created"
        
        return f"✅ {action} file '{path}' successfully!\nCommit: {result['commit']['sha'][:7]}"
        
    except Exception as e:
        logger.error(f"Error creating/updating file {path}: {e}")
        return f"❌ Error creating/updating file: {str(e)}"

@mcp.tool()
def create_branch(owner: str, repo: str, branch: str, sha: str) -> str:
    """
    Create a new branch in the repository.
    
    Args:
        owner: Repository owner (e.g., "Hparryok")
        repo: Repository name (e.g., "NeoTerra")
        branch: New branch name (e.g., "feature/new-notes")
        sha: SHA to create branch from (use latest commit SHA)
    
    Returns:
        Success message with branch details
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/git/refs"
        data = {
            "ref": f"refs/heads/{branch}",
            "sha": sha
        }
        
        logger.info(f"🌿 Creating branch: {branch} from {sha[:7]}")
        
        response = github.make_request("POST", url, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        return f"✅ Created branch '{branch}' successfully!\nBranch ref: {result['ref']}\nSHA: {sha[:7]}"
        
    except Exception as e:
        logger.error(f"Error creating branch {branch}: {e}")
        return f"❌ Error creating branch: {str(e)}"

@mcp.tool()
def list_commits(owner: str, repo: str, sha: str = "", path: str = "", page: int = 1, per_page: int = 10) -> str:
    """
    Get a list of commits from the repository.
    
    Args:
        owner: Repository owner (e.g., "Hparryok")
        repo: Repository name (e.g., "NeoTerra")
        sha: Branch name, tag, or commit SHA (optional, defaults to default branch)
        path: Only commits containing this file path (optional)
        page: Page number (default: 1)
        per_page: Results per page (default: 10, max: 100)
    
    Returns:
        Formatted list of commits with details
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        params = {
            "page": page,
            "per_page": min(per_page, 100)  # GitHub max is 100
        }
        
        if sha:
            params["sha"] = sha
        if path:
            params["path"] = path
        
        logger.info(f"📜 Listing commits for {owner}/{repo}")
        
        response = github.make_request("GET", url, params=params)
        response.raise_for_status()
        
        commits = response.json()
        
        if not commits:
            return f"📜 No commits found for {owner}/{repo}"
        
        result = [f"📜 **Recent commits for {owner}/{repo}:**\n"]
        
        for commit in commits:
            sha_short = commit['sha'][:7]
            message = commit['commit']['message'].split('\n')[0]  # First line only
            author = commit['commit']['author']['name']
            date = commit['commit']['author']['date'][:10]  # Just date part
            
            result.append(f"🔸 **{sha_short}** - {message}")
            result.append(f"   👤 {author} • 📅 {date}\n")
        
        return "\n".join(result)
        
    except Exception as e:
        logger.error(f"Error listing commits: {e}")
        return f"❌ Error listing commits: {str(e)}"

@mcp.tool()
def create_pull_request(owner: str, repo: str, title: str, head: str, base: str = "main", body: str = "", draft: bool = False) -> str:
    """
    Create a new pull request.
    
    Args:
        owner: Repository owner (e.g., "Hparryok")
        repo: Repository name (e.g., "NeoTerra")
        title: PR title (e.g., "Add new daily notes")
        head: Branch containing changes (e.g., "feature/daily-notes")
        base: Branch to merge into (default: "main")
        body: PR description (optional)
        draft: Create as draft PR (default: False)
    
    Returns:
        Success message with PR details
    """
    try:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        data = {
            "title": title,
            "head": head,
            "base": base,
            "draft": draft
        }
        
        if body:
            data["body"] = body
        
        logger.info(f"🔄 Creating PR: {title}")
        
        response = github.make_request("POST", url, json=data)
        response.raise_for_status()
        
        result = response.json()
        
        pr_type = "Draft PR" if draft else "PR"
        return f"✅ Created {pr_type} #{result['number']} successfully!\n" \
               f"📋 Title: {title}\n" \
               f"🌿 {head} → {base}\n" \
               f"🔗 URL: {result['html_url']}"
        
    except Exception as e:
        logger.error(f"Error creating PR: {e}")
        return f"❌ Error creating PR: {str(e)}"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    
    print("🚀 GitHub Obsidian MCP Server Starting...")
    print(f"📝 Vault: {GITHUB_OWNER}/{GITHUB_REPO}")
    print(f"🔧 Port: {port}")
    print(f"🔗 Integration URL: https://your-app.railway.app/sse")
    
    # Run with SSE transport for remote access
    mcp.run(
        transport="sse",
        host="0.0.0.0", 
        port=port
    )
