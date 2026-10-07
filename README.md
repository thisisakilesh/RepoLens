# RepoLens

RepoLens is a fast, developer-focused GitHub repository analyzer. It takes any public GitHub repository URL, queries the GitHub REST API, and generates a comprehensive technical dashboard with vital repository metrics, language composition, root project structure, and deterministic developer insights.

---

## 🌐 Live Production Deployment

The application is deployed live on Google Firebase Hosting:
- **Primary URL**: [https://repolens-analyzer-77.web.app](https://repolens-analyzer-77.web.app)
- **Alternate URL**: [https://repolens-analyzer-77.firebaseapp.com](https://repolens-analyzer-77.firebaseapp.com)

---

## Features

- **Instant Repository Intelligence**: Deep dive into any public GitHub repository without cloning or authentication.
- **Repository Header & Specs**: Displays owner, avatar, description, direct repository link, topics/tags, primary language, license, creation, and last updated timestamps.
- **Key Statistics Dashboard**: At-a-glance cards for Stars, Forks, Watchers, Open Issues, Disk Size, and Contributors.
- **Language Composition Breakdown**: Interactive Doughnut chart powered by Chart.js with exact byte counts and calculated percentages.
- **Root Project Explorer**: Tree-style file system explorer distinguishing directories and files, complete with file sizes and direct links.
- **Deterministic Developer Insights**: Transparent, rule-based heuristics evaluating community adoption, maintenance recency, dominant language, issue backlog volume, and ecosystem health.
- **README Inspection**: Status detection and preview of root-level README files with Markdown/HTML formatting cleanup.
- **Dark Developer-Tool Aesthetics**: Clean, high-contrast dark theme built with CSS Grid and Flexbox, fully responsive across desktop, laptop, and mobile devices.
- **Robust Error Handling**: Clear, human-friendly feedback for invalid URLs, non-GitHub domains, 404 repositories, rate limits, and network errors.

---

## Tech Stack

- **Backend**: Python 3.12, FastAPI, Uvicorn, HTTPX
- **Frontend**: Vanilla HTML5, Modern CSS3 (Grid & Flexbox), Vanilla JavaScript (ES6+)
- **Data Visualization**: Chart.js (Doughnut Chart)
- **API**: GitHub REST API v3
- **Testing**: Pytest

---

## Architecture

```
User (Browser)
       │  HTTP GET /
       ▼
┌──────────────────────────────────────────────┐
│  FastAPI Backend (app.py)                    │
│  - Static File Serving (/static)             │
│  - Endpoint: /api/analyze?url=<repo-url>     │
│  - URL Validation & Normalization            │
│  - Rule-Based Developer Insights Engine      │
└──────────────────────┬───────────────────────┘
                       │  Async HTTP (HTTPX)
                       ▼
┌──────────────────────────────────────────────┐
│  GitHub REST API (api.github.com)            │
│  - /repos/{owner}/{repo}                     │
│  - /repos/{owner}/{repo}/languages           │
│  - /repos/{owner}/{repo}/contents            │
│  - /repos/{owner}/{repo}/readme              │
│  - /repos/{owner}/{repo}/contributors        │
└──────────────────────────────────────────────┘
```

---

## API Endpoints

### 1. `GET /api/analyze?url={github_url}`
Analyzes a given public GitHub repository and returns a normalized response.

**Query Parameters:**
- `url` *(string, required)*: Public GitHub repository URL (e.g., `https://github.com/facebook/react`).

**Example Response:**
```json
{
  "repository": {
    "name": "react",
    "full_name": "facebook/react",
    "owner": "facebook",
    "owner_avatar": "https://avatars.githubusercontent.com/u/69631?v=4",
    "description": "The library for web and native user interfaces.",
    "html_url": "https://github.com/facebook/react",
    "topics": ["declarative", "frontend", "javascript", "react", "ui"],
    "language": "JavaScript",
    "license": "MIT",
    "created_at": "2013-05-24T16:15:54Z",
    "updated_at": "2026-10-07T12:00:00Z",
    "pushed_at": "2026-10-07T10:00:00Z",
    "stars": 228000,
    "forks": 46000,
    "watchers": 6600,
    "open_issues": 1150,
    "size_kb": 395000,
    "formatted_size": "385.7 MB",
    "default_branch": "main",
    "archived": false,
    "contributors_count": 1650
  },
  "languages": {
    "total_bytes": 10500000,
    "formatted_total": "10.0 MB",
    "items": [
      {
        "name": "JavaScript",
        "bytes": 8500000,
        "formatted_bytes": "8.1 MB",
        "percentage": 81.0
      }
    ]
  },
  "contents": [
    {
      "name": "packages",
      "path": "packages",
      "type": "dir",
      "size": 0,
      "formatted_size": null,
      "html_url": "https://github.com/facebook/react/tree/main/packages"
    }
  ],
  "readme": {
    "available": true,
    "name": "README.md",
    "size": 4096,
    "preview": "React is a JavaScript library for building user interfaces...",
    "html_url": "https://github.com/facebook/react/blob/main/README.md"
  },
  "insights": [
    {
      "type": "adoption",
      "icon": "⭐",
      "title": "High Community Adoption",
      "message": "Exceptional community adoption with over 228,000 stars and widespread industry usage."
    }
  ]
}
```

### 2. `GET /api/health`
Health check endpoint returning service status and timestamp.

---

## Running Locally

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)

### 1. Clone or Navigate to Directory
```bash
cd RepoLens
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
```

**Windows:**
```powershell
venv\Scripts\activate
```

**macOS / Linux:**
```bash
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Optional: GitHub Personal Access Token (for higher rate limits)
GitHub allows 60 unauthenticated requests/hour per IP. For heavy usage, optionally provide a token:
```powershell
$env:GITHUB_TOKEN="your_personal_access_token_here"
```

### 5. Start the Application
```bash
python app.py
```

Open your browser at:
```
http://localhost:8000
```

---

## Running Tests

Execute the automated test suite with pytest:
```bash
pytest -v
```

---

## Screenshots

<!-- Screenshot Placeholders -->
![RepoLens Landing Page](https://via.placeholder.com/1200x600/0b0f17/38bdf8?text=RepoLens+Landing+Page)

![RepoLens Analysis Dashboard](https://via.placeholder.com/1200x800/151d2e/38bdf8?text=RepoLens+Analysis+Dashboard)

---

## Future Improvements

Future iterations could expand on the core analyzer:
- **Commit Activity Analysis**: Visualizing commit velocity, frequency charts, and peak contribution hours.
- **Contributor Network**: Graph of top maintainers, PR authors, and organization affiliations.
- **Dependency Analysis**: Automated vulnerability checks and package manifest parsing (`package.json`, `pyproject.toml`, `Cargo.toml`).
- **AI-Powered Repository Explanation**: Automated architectural breakdown and summary using Large Language Models.
- **Code Complexity Analysis**: Cyclomatic complexity scoring and hotspot identification.
- **GitHub Authentication**: OAuth integration allowing analysis of private repositories and user-scoped rates.
