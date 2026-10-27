"""假的 stdio MCP 服务器：只列工具、回固定文本，用来模拟用户装的 MCP。"""
import json
import sys

NAME = sys.argv[1]
OBJ = {"type": "object", "properties": {"id": {"type": "string", "description": "Identifier of the item."},
                                        "query": {"type": "string", "description": "Free-text query."}}}
TOOLS = {
    "notes": {
        "search_notes": "Search the user's personal notes by keyword, tag or date range. Returns matching note titles, snippets and ids, newest first.",
        "get_note": "Fetch the full Markdown body and metadata of one note by id.",
        "create_note": "Create a new note with a title, Markdown body and optional tags. Returns the new note id.",
        "update_note": "Replace the body or tags of an existing note. Use get_note first to avoid overwriting edits.",
        "list_tags": "List every tag used in the notebook with the number of notes carrying it.",
    },
    "jira": {
        name: f"{desc} Requires the JIRA_TOKEN environment variable. Accepts project keys like SHOP or ADMIN. "
              "Fields follow the Jira REST v3 schema; custom fields are returned under customfield_* keys. "
              "Rate limited to 10 requests per second per token; on HTTP 429 wait and retry."
        for name, desc in {
            "get_issue": "Fetch a Jira issue with summary, description, status, assignee, labels and comments.",
            "search_issues": "Search Jira issues with JQL and return key, summary, status and assignee for each match.",
            "create_issue": "Create a Jira issue in a project with a type, summary, description and optional labels.",
            "update_issue": "Update fields of an existing Jira issue such as summary, description, labels or priority.",
            "transition_issue": "Move a Jira issue to another workflow status, for example To Do, In Progress or Done.",
            "add_comment": "Add a comment to a Jira issue. Supports Atlassian Document Format or plain text.",
            "list_sprints": "List active and future sprints of a Jira board with start and end dates.",
            "get_sprint_issues": "List issues in a sprint with status, story points and assignee.",
            "list_projects": "List Jira projects visible to the token with key, name and lead.",
            "get_user": "Look up a Jira user by account id or email and return display name and timezone.",
            "list_components": "List the components of a Jira project with their default assignees.",
            "get_changelog": "Return the change history of a Jira issue, newest first.",
        }.items()
    },
}[NAME]

for line in sys.stdin:
    try:
        request = json.loads(line)
    except ValueError:
        continue
    if "id" not in request:
        continue
    method, params = request.get("method"), request.get("params") or {}
    if method == "initialize":
        result = {"protocolVersion": params.get("protocolVersion", "2025-06-18"), "capabilities": {"tools": {}},
                  "serverInfo": {"name": NAME, "version": "1.0.0"}}
    elif method == "tools/list":
        result = {"tools": [{"name": n, "description": d, "inputSchema": OBJ} for n, d in TOOLS.items()]}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": f"{NAME}: ok"}]}
    elif method == "ping":
        result = {}
    else:
        print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "error": {"code": -32601, "message": "method not found"}}), flush=True)
        continue
    print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": result}), flush=True)
