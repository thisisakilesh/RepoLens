import os
import re
import base64
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="RepoLens API",
    description="Developer-focused GitHub repository analyzer API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "RepoLens API is active"}


@app.get("/style.css", include_in_schema=False)
async def serve_css():
    css_file = os.path.join(STATIC_DIR, "style.css")
    if os.path.exists(css_file):
        return FileResponse(css_file, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")


@app.get("/app.js", include_in_schema=False)
async def serve_js():
    js_file = os.path.join(STATIC_DIR, "app.js")
    if os.path.exists(js_file):
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": "RepoLens", "timestamp": datetime.now(timezone.utc).isoformat()}


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Validates and extracts owner and repository name from a GitHub URL.
    Only allows github.com repositories.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL parameter is required and cannot be empty.")

    cleaned_url = url.strip()
    if not cleaned_url.startswith(("http://", "https://")):
        cleaned_url = "https://" + cleaned_url

    parsed = urlparse(cleaned_url)
    netloc = parsed.netloc.lower()
    if netloc not in ("github.com", "www.github.com"):
        raise ValueError("Only public GitHub repositories (github.com) are supported.")

    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(path_parts) < 2:
        raise ValueError(
            "Invalid GitHub repository URL. Expected format: https://github.com/owner/repository"
        )

    owner = path_parts[0]
    repo = path_parts[1]

    if repo.endswith(".git"):
        repo = repo[:-4]

    valid_pattern = re.compile(r"^[a-zA-Z0-9_.-]+$")
    if not valid_pattern.match(owner) or not valid_pattern.match(repo):
        raise ValueError("Repository URL contains invalid characters.")

    return owner, repo


def get_github_headers() -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "RepoLens-Analyzer/1.0",
    }
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"
    return headers


def format_bytes(bytes_count: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_count < 1024:
            return f"{bytes_count:.1f} {unit}" if unit != "B" else f"{bytes_count} {unit}"
        bytes_count /= 1024
    return f"{bytes_count:.1f} TB"


def clean_readme_preview(text: str, max_chars: int = 500) -> str:
    # Strip markdown images and links formatting if needed, remove consecutive newlines
    cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned


def generate_insights(repo: Dict[str, Any], languages: Dict[str, Any], readme_info: Dict[str, Any]) -> List[Dict[str, str]]:
    insights: List[Dict[str, str]] = []

    stars = repo.get("stargazers_count", 0)
    forks = repo.get("forks_count", 0)
    open_issues = repo.get("open_issues_count", 0)
    archived = repo.get("archived", False)
    license_info = repo.get("license")
    pushed_at = repo.get("pushed_at")

    # 1. Community Adoption
    if stars >= 20000:
        insights.append({
            "type": "adoption",
            "icon": "⭐",
            "title": "High Community Adoption",
            "message": f"Exceptional community adoption with over {stars:,} stars and widespread industry usage."
        })
    elif stars >= 2000:
        insights.append({
            "type": "adoption",
            "icon": "⭐",
            "title": "Strong Adoption",
            "message": f"Solid community backing with {stars:,} stars and reliable traction."
        })
    elif stars >= 100:
        insights.append({
            "type": "adoption",
            "icon": "🌱",
            "title": "Growing Community",
            "message": f"Growing developer interest with {stars:,} stars."
        })
    else:
        insights.append({
            "type": "adoption",
            "icon": "🌱",
            "title": "Early Stage Repository",
            "message": f"Early stage or niche project with {stars:,} stars."
        })

    # 2. Activity & Maintenance
    if archived:
        insights.append({
            "type": "maintenance",
            "icon": "📦",
            "title": "Archived Repository",
            "message": "This repository has been archived by the owner and is read-only."
        })
    elif pushed_at:
        try:
            push_dt = datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
            days_since_push = (datetime.now(timezone.utc) - push_dt).days
            if days_since_push <= 14:
                insights.append({
                    "type": "maintenance",
                    "icon": "⚡",
                    "title": "Actively Maintained",
                    "message": f"Very active commit activity; last push occurred {days_since_push} days ago."
                })
            elif days_since_push <= 90:
                insights.append({
                    "type": "maintenance",
                    "icon": "🔄",
                    "title": "Regularly Maintained",
                    "message": f"Recent activity within the last {days_since_push} days."
                })
            else:
                insights.append({
                    "type": "maintenance",
                    "icon": "⚠️",
                    "title": "Low Recent Activity",
                    "message": f"No code pushes recorded in the last {days_since_push} days. Maintenance may be slow."
                })
        except Exception:
            pass

    # 3. Dominant Language
    lang_items = languages.get("items", [])
    if lang_items:
        top_lang = lang_items[0]
        insights.append({
            "type": "language",
            "icon": "💻",
            "title": f"Primary Language: {top_lang['name']}",
            "message": f"{top_lang['name']} dominates the codebase ({top_lang['percentage']}% of total detected code)."
        })

    # 4. Open Issues Backlog
    if open_issues > 1000:
        insights.append({
            "type": "issues",
            "icon": "🐛",
            "title": "Substantial Issue Backlog",
            "message": f"High volume of open issues ({open_issues:,}). Requires triage or dedicated issue management."
        })
    elif open_issues > 200:
        insights.append({
            "type": "issues",
            "icon": "📋",
            "title": "Active Issue Tracking",
            "message": f"{open_issues:,} open issues tracked across bug reports and feature discussions."
        })
    else:
        insights.append({
            "type": "issues",
            "icon": "✅",
            "title": "Streamlined Issue Backlog",
            "message": f"Clean and manageable backlog with only {open_issues:,} open issues."
        })

    # 5. Fork / Ecosystem Engagement
    if forks >= 5000:
        insights.append({
            "type": "forks",
            "icon": "🍴",
            "title": "Broad Developer Contributions",
            "message": f"Over {forks:,} forks reflect extensive external contribution and dependency usage."
        })

    # 6. Documentation & License
    if not readme_info.get("available"):
        insights.append({
            "type": "documentation",
            "icon": "⚠️",
            "title": "Documentation Attention Needed",
            "message": "Documentation may be worth checking: no root README file was detected."
        })
    else:
        insights.append({
            "type": "documentation",
            "icon": "📖",
            "title": "README Available",
            "message": "Standard README documentation is present at the repository root."
        })

    if license_info and license_info.get("spdx_id") not in ("NOASSERTION", None):
        insights.append({
            "type": "license",
            "icon": "⚖️",
            "title": f"Open Source License ({license_info.get('spdx_id')})",
            "message": f"Governed under the {license_info.get('name', 'open source')} license."
        })
    else:
        insights.append({
            "type": "license",
            "icon": "⚠️",
            "title": "No Formal License Found",
            "message": "No recognized open-source license detected. Verify licensing terms before reusing."
        })

    return insights


@app.get("/api/analyze")
async def analyze_repository(url: str = Query(..., description="Public GitHub repository URL")):
    try:
        owner, repo = parse_github_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    base_api = f"https://api.github.com/repos/{owner}/{repo}"
    headers = get_github_headers()

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        # Step 1: Fetch main repository details
        try:
            repo_resp = await client.get(base_api, headers=headers)
        except httpx.RequestError:
            raise HTTPException(
                status_code=503,
                detail="Network failure: Unable to reach GitHub API. Check connection and try again."
            )

        if repo_resp.status_code == 404:
            raise HTTPException(
                status_code=404,
                detail="Repository not found. Check the URL and make sure the repository is public."
            )
        elif repo_resp.status_code == 403:
            remaining = repo_resp.headers.get("x-ratelimit-remaining")
            if remaining == "0":
                raise HTTPException(
                    status_code=429,
                    detail="GitHub API rate limit exceeded. Please wait a few minutes before trying again or configure a GITHUB_TOKEN."
                )
            raise HTTPException(
                status_code=403,
                detail="Access forbidden by GitHub API. Ensure repository is public and accessible."
            )
        elif repo_resp.status_code != 200:
            raise HTTPException(
                status_code=repo_resp.status_code,
                detail=f"GitHub API returned unexpected status code {repo_resp.status_code}."
            )

        repo_data = repo_resp.json()

        # Step 2: Fetch languages, contents, readme, contributors in parallel
        tasks = [
            client.get(f"{base_api}/languages", headers=headers),
            client.get(f"{base_api}/contents", headers=headers),
            client.get(f"{base_api}/readme", headers=headers),
            client.get(f"{base_api}/contributors?per_page=1&anon=false", headers=headers),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        languages_resp, contents_resp, readme_resp, contrib_resp = results

        # Process languages
        languages_data = {}
        total_lang_bytes = 0
        lang_items = []
        if isinstance(languages_resp, httpx.Response) and languages_resp.status_code == 200:
            raw_langs = languages_resp.json()
            total_lang_bytes = sum(raw_langs.values())
            for lang_name, byte_count in raw_langs.items():
                pct = round((byte_count / total_lang_bytes) * 100, 1) if total_lang_bytes > 0 else 0
                lang_items.append({
                    "name": lang_name,
                    "bytes": byte_count,
                    "formatted_bytes": format_bytes(byte_count),
                    "percentage": pct,
                })
        languages_data = {
            "total_bytes": total_lang_bytes,
            "formatted_total": format_bytes(total_lang_bytes),
            "items": lang_items,
        }

        # Process root contents
        contents_list = []
        if isinstance(contents_resp, httpx.Response) and contents_resp.status_code == 200:
            raw_contents = contents_resp.json()
            if isinstance(raw_contents, list):
                # Sort: directories first (alphabetical), then files (alphabetical)
                dirs = []
                files = []
                for item in raw_contents:
                    entry = {
                        "name": item.get("name"),
                        "path": item.get("path"),
                        "type": item.get("type"),  # "dir" or "file"
                        "size": item.get("size", 0),
                        "formatted_size": format_bytes(item.get("size", 0)) if item.get("type") == "file" else None,
                        "html_url": item.get("html_url"),
                    }
                    if entry["type"] == "dir":
                        dirs.append(entry)
                    else:
                        files.append(entry)
                dirs.sort(key=lambda x: x["name"].lower())
                files.sort(key=lambda x: x["name"].lower())
                contents_list = dirs + files

        # Process README
        readme_info = {
            "available": False,
            "name": None,
            "size": 0,
            "preview": None,
            "html_url": None,
        }
        if isinstance(readme_resp, httpx.Response) and readme_resp.status_code == 200:
            raw_readme = readme_resp.json()
            readme_info["available"] = True
            readme_info["name"] = raw_readme.get("name", "README.md")
            readme_info["size"] = raw_readme.get("size", 0)
            readme_info["html_url"] = raw_readme.get("html_url")
            raw_content_b64 = raw_readme.get("content", "")
            if raw_content_b64:
                try:
                    decoded = base64.b64decode(raw_content_b64).decode("utf-8", errors="replace")
                    readme_info["preview"] = clean_readme_preview(decoded, max_chars=450)
                except Exception:
                    readme_info["preview"] = "README preview could not be decoded."
            else:
                readme_info["preview"] = "README is empty."

        # Process contributors count estimation
        # GitHub's link header for /contributors?per_page=1 gives the total pages
        contributor_count = None
        if isinstance(contrib_resp, httpx.Response) and contrib_resp.status_code == 200:
            link_header = contrib_resp.headers.get("link", "")
            if link_header:
                last_page_match = re.search(r'[?&]page=(\d+)[^>]*>;\s*rel="last"', link_header)
                if last_page_match:
                    try:
                        contributor_count = int(last_page_match.group(1))
                    except ValueError:
                        pass
            if contributor_count is None:
                contrib_list = contrib_resp.json()
                if isinstance(contrib_list, list):
                    contributor_count = len(contrib_list)

        # Generate deterministic rule-based insights
        insights = generate_insights(repo_data, languages_data, readme_info)

        owner_info = repo_data.get("owner") or {}
        license_info = repo_data.get("license") or {}
        license_str = license_info.get("spdx_id") or license_info.get("name") or "None"

        # Construct normalized response
        normalized = {
            "repository": {
                "name": repo_data.get("name"),
                "full_name": repo_data.get("full_name"),
                "owner": owner_info.get("login"),
                "owner_avatar": owner_info.get("avatar_url"),
                "description": repo_data.get("description") or "No description provided.",
                "html_url": repo_data.get("html_url"),
                "topics": repo_data.get("topics", []),
                "language": repo_data.get("language") or "Not specified",
                "license": license_str,
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "pushed_at": repo_data.get("pushed_at"),
                "stars": repo_data.get("stargazers_count", 0),
                "forks": repo_data.get("forks_count", 0),
                "watchers": repo_data.get("subscribers_count", repo_data.get("watchers_count", 0)),
                "open_issues": repo_data.get("open_issues_count", 0),
                "size_kb": repo_data.get("size", 0),
                "formatted_size": format_bytes(repo_data.get("size", 0) * 1024),
                "default_branch": repo_data.get("default_branch", "main"),
                "archived": repo_data.get("archived", False),
                "contributors_count": contributor_count,
            },
            "languages": languages_data,
            "contents": contents_list,
            "readme": readme_info,
            "insights": insights,
        }

        return normalized


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
