import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
import httpx

from app import app, parse_github_url, generate_insights

client = TestClient(app)


def test_parse_github_url_valid():
    cases = [
        ("https://github.com/facebook/react", ("facebook", "react")),
        ("https://github.com/microsoft/vscode/", ("microsoft", "vscode")),
        ("http://github.com/fastapi/fastapi", ("fastapi", "fastapi")),
        ("github.com/torvalds/linux", ("torvalds", "linux")),
        ("https://github.com/pallets/flask.git", ("pallets", "flask")),
        ("https://www.github.com/python/cpython", ("python", "cpython")),
    ]
    for url, expected in cases:
        assert parse_github_url(url) == expected


def test_parse_github_url_invalid():
    invalid_cases = [
        "",
        "https://gitlab.com/facebook/react",
        "https://bitbucket.org/org/repo",
        "https://github.com/only-owner",
        "https://github.com",
        "not-a-url",
        "https://github.com/owner/repo with spaces",
    ]
    for url in invalid_cases:
        with pytest.raises(ValueError):
            parse_github_url(url)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "RepoLens"


def test_serve_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "RepoLens" in response.text
    assert "Analyze Repository" in response.text


def test_analyze_endpoint_invalid_url():
    response = client.get("/api/analyze?url=https://gitlab.com/owner/repo")
    assert response.status_code == 400
    assert "Only public GitHub repositories" in response.json()["detail"]

    response = client.get("/api/analyze?url=")
    assert response.status_code == 400


def test_deterministic_insights_generation():
    mock_repo = {
        "stargazers_count": 25000,
        "forks_count": 6000,
        "open_issues_count": 45,
        "archived": False,
        "license": {"spdx_id": "MIT", "name": "MIT License"},
        "pushed_at": "2026-10-01T12:00:00Z",
    }
    mock_languages = {
        "items": [
            {"name": "Python", "bytes": 85000, "percentage": 85.0},
            {"name": "HTML", "bytes": 15000, "percentage": 15.0},
        ]
    }
    mock_readme = {
        "available": True,
        "name": "README.md",
        "preview": "RepoLens sample documentation",
    }

    insights = generate_insights(mock_repo, mock_languages, mock_readme)
    assert len(insights) >= 5

    titles = [i["title"] for i in insights]
    assert any("High Community Adoption" in t for t in titles)
    assert any("Primary Language: Python" in t for t in titles)
    assert any("Streamlined Issue Backlog" in t for t in titles)
    assert any("README Available" in t for t in titles)
    assert any("Open Source License (MIT)" in t for t in titles)


def test_analyze_endpoint_not_found():
    # Test handling of 404 from GitHub
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = httpx.Response(
            status_code=404,
            request=httpx.Request("GET", "https://api.github.com/repos/nonexistent/repo")
        )
        mock_get.return_value = mock_response

        response = client.get("/api/analyze?url=https://github.com/nonexistent/repo")
        assert response.status_code == 404
        assert "Repository not found" in response.json()["detail"]


def test_analyze_endpoint_rate_limit():
    # Test handling of 403 Rate Limit from GitHub
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_response = httpx.Response(
            status_code=403,
            headers={"x-ratelimit-remaining": "0"},
            request=httpx.Request("GET", "https://api.github.com/repos/facebook/react")
        )
        mock_get.return_value = mock_response

        response = client.get("/api/analyze?url=https://github.com/facebook/react")
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()


def test_analyze_endpoint_success_structure():
    # Test normalized response structure when GitHub returns valid data
    sample_repo_data = {
        "name": "sample-repo",
        "full_name": "testowner/sample-repo",
        "owner": {"login": "testowner", "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4"},
        "description": "A sample repository for testing",
        "html_url": "https://github.com/testowner/sample-repo",
        "topics": ["python", "fastapi"],
        "language": "Python",
        "license": {"spdx_id": "Apache-2.0", "name": "Apache License 2.0"},
        "created_at": "2021-01-01T00:00:00Z",
        "updated_at": "2026-10-01T00:00:00Z",
        "pushed_at": "2026-10-05T00:00:00Z",
        "stargazers_count": 3500,
        "forks_count": 250,
        "watchers_count": 80,
        "subscribers_count": 80,
        "open_issues_count": 12,
        "size": 1024,
        "default_branch": "main",
        "archived": False,
    }

    async def mock_client_get(url, headers=None):
        if url.endswith("/sample-repo"):
            return httpx.Response(200, json=sample_repo_data, request=httpx.Request("GET", url))
        elif url.endswith("/languages"):
            return httpx.Response(200, json={"Python": 9000, "Shell": 1000}, request=httpx.Request("GET", url))
        elif url.endswith("/contents"):
            return httpx.Response(200, json=[
                {"name": "app.py", "path": "app.py", "type": "file", "size": 500, "html_url": "https://github.com/testowner/sample-repo/blob/main/app.py"},
                {"name": "src", "path": "src", "type": "dir", "size": 0, "html_url": "https://github.com/testowner/sample-repo/tree/main/src"}
            ], request=httpx.Request("GET", url))
        elif url.endswith("/readme"):
            import base64
            b64_content = base64.b64encode(b"# Sample Project\nTesting RepoLens analyzer.").decode("utf-8")
            return httpx.Response(200, json={
                "name": "README.md",
                "size": 35,
                "content": b64_content,
                "html_url": "https://github.com/testowner/sample-repo/blob/main/README.md"
            }, request=httpx.Request("GET", url))
        elif "contributors" in url:
            return httpx.Response(
                200,
                headers={"link": '<https://api.github.com/repos/testowner/sample-repo/contributors?page=42>; rel="last"'},
                json=[{"login": "testowner"}],
                request=httpx.Request("GET", url)
            )
        return httpx.Response(404, request=httpx.Request("GET", url))

    with patch("httpx.AsyncClient.get", side_effect=mock_client_get):
        response = client.get("/api/analyze?url=https://github.com/testowner/sample-repo")
        assert response.status_code == 200
        data = response.json()

        # Check top-level keys
        assert "repository" in data
        assert "languages" in data
        assert "contents" in data
        assert "readme" in data
        assert "insights" in data

        # Check repository details
        repo = data["repository"]
        assert repo["name"] == "sample-repo"
        assert repo["owner"] == "testowner"
        assert repo["stars"] == 3500
        assert repo["contributors_count"] == 42
        assert repo["license"] == "Apache-2.0"

        # Check languages
        assert data["languages"]["total_bytes"] == 10000
        assert len(data["languages"]["items"]) == 2
        assert data["languages"]["items"][0]["name"] == "Python"
        assert data["languages"]["items"][0]["percentage"] == 90.0

        # Check contents (dirs first, then files)
        contents = data["contents"]
        assert len(contents) == 2
        assert contents[0]["type"] == "dir"
        assert contents[0]["name"] == "src"
        assert contents[1]["type"] == "file"
        assert contents[1]["name"] == "app.py"

        # Check readme
        assert data["readme"]["available"] is True
        assert "Sample Project" in data["readme"]["preview"]

        # Check insights
        assert len(data["insights"]) > 0
