/* ==========================================================================
   RepoLens — Client Application
   ========================================================================== */

(function () {
  'use strict';

  // DOM Elements
  const form = document.getElementById('analyze-form');
  const repoInput = document.getElementById('repo-url');
  const analyzeBtn = document.getElementById('analyze-btn');
  const loadingState = document.getElementById('loading-state');
  const errorState = document.getElementById('error-state');
  const errorTitle = document.getElementById('error-title');
  const errorMessage = document.getElementById('error-message');
  const dismissErrorBtn = document.getElementById('dismiss-error-btn');
  const dashboard = document.getElementById('dashboard');
  const sampleButtons = document.querySelectorAll('.sample-btn');

  // Chart instance holder
  let languageChart = null;

  // Modern language colors palette for Chart.js
  const LANG_COLORS = [
    '#38bdf8', // sky/blue
    '#a855f7', // purple
    '#22c55e', // green
    '#f59e0b', // amber
    '#f43f5e', // rose
    '#06b6d4', // cyan
    '#ec4899', // pink
    '#8b5cf6', // violet
    '#10b981', // emerald
    '#64748b'  // slate / other
  ];

  // Helper: Format Date
  function formatDate(isoString) {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      });
    } catch {
      return isoString;
    }
  }

  // Helper: Format Numbers with Commas
  function formatNumber(num) {
    if (num === null || num === undefined) return '—';
    return Number(num).toLocaleString('en-US');
  }

  // Show / Hide helpers
  function showLoading() {
    loadingState.classList.remove('hidden');
    errorState.classList.add('hidden');
    analyzeBtn.disabled = true;
    analyzeBtn.querySelector('.btn-text').textContent = 'Analyzing...';
  }

  function hideLoading() {
    loadingState.classList.add('hidden');
    analyzeBtn.disabled = false;
    analyzeBtn.querySelector('.btn-text').textContent = 'Analyze Repository';
  }

  function showError(title, message) {
    hideLoading();
    errorTitle.textContent = title || 'Unable to analyze repository';
    errorMessage.textContent = message || 'An unexpected error occurred. Please try again.';
    errorState.classList.remove('hidden');
    // Scroll error into view if needed
    errorState.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function hideError() {
    errorState.classList.add('hidden');
  }

  // Render Repository Header & Specs
  function renderHeader(repo) {
    document.getElementById('repo-owner').textContent = repo.owner;
    document.getElementById('repo-name').textContent = repo.name;
    document.getElementById('repo-description').textContent = repo.description;

    const avatarEl = document.getElementById('owner-avatar');
    if (repo.owner_avatar) {
      avatarEl.src = repo.owner_avatar;
      avatarEl.alt = `${repo.owner} avatar`;
      avatarEl.style.display = 'block';
    } else {
      avatarEl.style.display = 'none';
    }

    const githubLinkEl = document.getElementById('github-link');
    githubLinkEl.href = repo.html_url;

    // Topics tags
    const topicsContainer = document.getElementById('repo-topics');
    topicsContainer.innerHTML = '';
    if (repo.topics && repo.topics.length > 0) {
      repo.topics.forEach(topic => {
        const tag = document.createElement('span');
        tag.className = 'topic-tag';
        tag.textContent = topic;
        topicsContainer.appendChild(tag);
      });
    }

    // Specs
    document.getElementById('spec-language').textContent = repo.language || '—';
    document.getElementById('spec-license').textContent = repo.license || 'None';
    document.getElementById('spec-created').textContent = formatDate(repo.created_at);
    document.getElementById('spec-updated').textContent = formatDate(repo.updated_at);
    document.getElementById('spec-branch').textContent = repo.default_branch || 'main';
  }

  // Render Key Statistics Cards
  function renderStats(repo) {
    document.getElementById('stat-stars').textContent = formatNumber(repo.stars);
    document.getElementById('stat-forks').textContent = formatNumber(repo.forks);
    document.getElementById('stat-watchers').textContent = formatNumber(repo.watchers);
    document.getElementById('stat-issues').textContent = formatNumber(repo.open_issues);
    document.getElementById('stat-size').textContent = repo.formatted_size || `${repo.size_kb} KB`;
    document.getElementById('stat-contributors').textContent = repo.contributors_count !== null 
      ? formatNumber(repo.contributors_count) 
      : 'N/A';
  }

  // Render Language Analysis & Chart.js Doughnut
  function renderLanguages(languages) {
    const listContainer = document.getElementById('language-list');
    const totalBytesEl = document.getElementById('languages-total-bytes');
    listContainer.innerHTML = '';

    const items = languages.items || [];
    totalBytesEl.textContent = languages.formatted_total || '0 B';

    if (items.length === 0) {
      listContainer.innerHTML = '<div class="state-desc">No language statistics detected in this repository.</div>';
      if (languageChart) {
        languageChart.destroy();
        languageChart = null;
      }
      return;
    }

    const labels = items.map(item => item.name);
    const dataValues = items.map(item => item.bytes);
    const backgroundColors = items.map((_, i) => LANG_COLORS[i % LANG_COLORS.length]);

    // Build list
    items.forEach((item, index) => {
      const color = backgroundColors[index];
      const row = document.createElement('div');
      row.className = 'lang-row';
      row.innerHTML = `
        <div class="lang-identity">
          <span class="lang-dot" style="background-color: ${color}"></span>
          <span class="lang-name">${item.name}</span>
        </div>
        <div class="lang-stats">
          <span class="lang-bytes mono">${item.formatted_bytes}</span>
          <span class="lang-pct mono">${item.percentage}%</span>
        </div>
      `;
      listContainer.appendChild(row);
    });

    // Destroy prior chart if present
    if (languageChart) {
      languageChart.destroy();
    }

    const canvas = document.getElementById('language-chart');
    const ctx = canvas.getContext('2d');

    languageChart = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: dataValues,
          backgroundColor: backgroundColors,
          borderWidth: 1,
          borderColor: '#151d2e',
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: '#0e1524',
            titleColor: '#f1f5f9',
            bodyColor: '#94a3b8',
            borderColor: '#242f47',
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label: function (context) {
                const item = items[context.dataIndex];
                return ` ${item.name}: ${item.percentage}% (${item.formatted_bytes})`;
              }
            }
          }
        },
        cutout: '72%'
      }
    });
  }

  // Render Developer Insights
  function renderInsights(insights) {
    const container = document.getElementById('insights-list');
    container.innerHTML = '';

    if (!insights || insights.length === 0) {
      container.innerHTML = '<div class="state-desc">No insights available for this repository.</div>';
      return;
    }

    const ICONS = {
      adoption: '⭐',
      maintenance: '⚡',
      language: '💻',
      issues: '🐛',
      forks: '🍴',
      documentation: '📖',
      license: '⚖️'
    };

    insights.forEach(item => {
      const card = document.createElement('div');
      card.className = 'insight-item';
      const icon = ICONS[item.type] || item.icon || '💡';
      card.innerHTML = `
        <span class="insight-icon">${icon}</span>
        <div class="insight-content">
          <div class="insight-title">${item.title}</div>
          <div class="insight-desc">${item.message}</div>
        </div>
      `;
      container.appendChild(card);
    });
  }

  // Render Root Project Structure
  function renderStructure(contents) {
    const treeContainer = document.getElementById('explorer-tree');
    const countEl = document.getElementById('structure-count');
    treeContainer.innerHTML = '';

    if (!contents || contents.length === 0) {
      countEl.textContent = '0 items';
      treeContainer.innerHTML = '<div style="padding: 1rem; color: var(--text-muted);">Root contents unavailable.</div>';
      return;
    }

    countEl.textContent = `${contents.length} root items`;

    contents.forEach(item => {
      const isDir = item.type === 'dir';
      const icon = isDir ? '📁' : '📄';
      const link = document.createElement('a');
      link.className = `explorer-item ${isDir ? 'item-is-dir' : 'item-is-file'}`;
      link.href = item.html_url || '#';
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.title = `Open ${item.name} on GitHub`;

      link.innerHTML = `
        <div class="item-left">
          <span class="item-icon">${icon}</span>
          <span class="item-name">${item.name}</span>
        </div>
        ${!isDir && item.formatted_size ? `<span class="item-size mono">${item.formatted_size}</span>` : ''}
      `;

      treeContainer.appendChild(link);
    });
  }

  // Render README Analysis
  function renderReadme(readme) {
    const badgeEl = document.getElementById('readme-status-badge');
    const previewBox = document.getElementById('readme-preview-box');

    if (readme && readme.available) {
      badgeEl.className = 'badge-readme available';
      badgeEl.innerHTML = `<span>README</span> <strong>✓ Available</strong>`;
      previewBox.textContent = readme.preview || 'README is available but preview could not be generated.';
    } else {
      badgeEl.className = 'badge-readme unavailable';
      badgeEl.innerHTML = `<span>README</span> <strong>⚠ No README detected</strong>`;
      previewBox.textContent = 'No README file was found in the repository root.\n\nProviding a clear README helps developers understand project goals, installation, and usage.';
    }
  }

  // Parse GitHub URL on client
  function parseGithubUrl(url) {
    if (!url || typeof url !== 'string') throw new Error('Repository URL cannot be empty.');
    let clean = url.trim();
    if (!clean.startsWith('http://') && !clean.startsWith('https://')) {
      clean = 'https://' + clean;
    }
    const parsed = new URL(clean);
    const host = parsed.hostname.toLowerCase();
    if (host !== 'github.com' && host !== 'www.github.com') {
      throw new Error('Only public GitHub repositories (github.com) are supported.');
    }
    const parts = parsed.pathname.replace(/^\/|\/$/g, '').split('/');
    if (parts.length < 2) {
      throw new Error('Invalid URL format. Expected: https://github.com/owner/repository');
    }
    const owner = parts[0];
    let repo = parts[1];
    if (repo.endsWith('.git')) repo = repo.slice(0, -4);
    const valid = /^[a-zA-Z0-9_.-]+$/;
    if (!valid.test(owner) || !valid.test(repo)) {
      throw new Error('Repository URL contains invalid characters.');
    }
    return { owner, repo };
  }

  // Format bytes helper
  function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let val = bytes;
    for (const unit of units) {
      if (val < 1024) return unit === 'B' ? `${val} B` : `${val.toFixed(1)} ${unit}`;
      val /= 1024;
    }
    return `${val.toFixed(1)} TB`;
  }

  // Client-side rule-based insights generator
  function generateClientInsights(repoData, languagesData, readmeInfo) {
    const insights = [];
    const stars = repoData.stargazers_count || 0;
    const forks = repoData.forks_count || 0;
    const openIssues = repoData.open_issues_count || 0;
    const archived = repoData.archived || false;
    const license = repoData.license;
    const pushed = repoData.pushed_at;

    if (stars >= 20000) {
      insights.push({ type: 'adoption', title: 'High Community Adoption', message: `Exceptional community adoption with over ${stars.toLocaleString()} stars and widespread industry usage.` });
    } else if (stars >= 2000) {
      insights.push({ type: 'adoption', title: 'Strong Adoption', message: `Solid community backing with ${stars.toLocaleString()} stars and reliable traction.` });
    } else if (stars >= 100) {
      insights.push({ type: 'adoption', title: 'Growing Community', message: `Growing developer interest with ${stars.toLocaleString()} stars.` });
    } else {
      insights.push({ type: 'adoption', title: 'Early Stage Repository', message: `Early stage or niche project with ${stars.toLocaleString()} stars.` });
    }

    if (archived) {
      insights.push({ type: 'maintenance', title: 'Archived Repository', message: 'This repository has been archived by the owner and is read-only.' });
    } else if (pushed) {
      const days = Math.floor((Date.now() - new Date(pushed).getTime()) / (1000 * 60 * 60 * 24));
      if (days <= 14) {
        insights.push({ type: 'maintenance', title: 'Actively Maintained', message: `Very active commit activity; last push occurred ${days} days ago.` });
      } else if (days <= 90) {
        insights.push({ type: 'maintenance', title: 'Regularly Maintained', message: `Recent activity within the last ${days} days.` });
      } else {
        insights.push({ type: 'maintenance', title: 'Low Recent Activity', message: `No code pushes recorded in the last ${days} days. Maintenance may be slow.` });
      }
    }

    const items = languagesData.items || [];
    if (items.length > 0) {
      insights.push({ type: 'language', title: `Primary Language: ${items[0].name}`, message: `${items[0].name} dominates the codebase (${items[0].percentage}% of total detected code).` });
    }

    if (openIssues > 1000) {
      insights.push({ type: 'issues', title: 'Substantial Issue Backlog', message: `High volume of open issues (${openIssues.toLocaleString()}). Requires triage or dedicated issue management.` });
    } else if (openIssues > 200) {
      insights.push({ type: 'issues', title: 'Active Issue Tracking', message: `${openIssues.toLocaleString()} open issues tracked across bug reports and feature discussions.` });
    } else {
      insights.push({ type: 'issues', title: 'Streamlined Issue Backlog', message: `Clean and manageable backlog with only ${openIssues.toLocaleString()} open issues.` });
    }

    if (forks >= 5000) {
      insights.push({ type: 'forks', title: 'Broad Developer Contributions', message: `Over ${forks.toLocaleString()} forks reflect extensive external contribution and dependency usage.` });
    }

    if (!readmeInfo.available) {
      insights.push({ type: 'documentation', title: 'Documentation Attention Needed', message: 'Documentation may be worth checking: no root README file was detected.' });
    } else {
      insights.push({ type: 'documentation', title: 'README Available', message: 'Standard README documentation is present at the repository root.' });
    }

    if (license && license.spdx_id && license.spdx_id !== 'NOASSERTION') {
      insights.push({ type: 'license', title: `Open Source License (${license.spdx_id})`, message: `Governed under the ${license.name || 'open source'} license.` });
    } else {
      insights.push({ type: 'license', title: 'No Formal License Found', message: 'No recognized open-source license detected. Verify licensing terms before reusing.' });
    }

    return insights;
  }

  // Direct client-side analysis using GitHub REST API
  async function analyzeClientSide(owner, repo) {
    const baseApi = `https://api.github.com/repos/${owner}/${repo}`;
    const headers = { 'Accept': 'application/vnd.github.v3+json' };

    const repoRes = await fetch(baseApi, { headers });
    if (repoRes.status === 404) {
      throw new Error('Repository not found. Check the URL and make sure the repository is public.');
    }
    if (repoRes.status === 403) {
      throw new Error('GitHub API rate limit exceeded. Please wait a few minutes before trying again.');
    }
    if (!repoRes.ok) {
      throw new Error(`GitHub API returned status code ${repoRes.status}.`);
    }

    const repoData = await repoRes.json();

    const [langRes, contentsRes, readmeRes, contribRes] = await Promise.allSettled([
      fetch(`${baseApi}/languages`, { headers }),
      fetch(`${baseApi}/contents`, { headers }),
      fetch(`${baseApi}/readme`, { headers }),
      fetch(`${baseApi}/contributors?per_page=1`, { headers })
    ]);

    // Process languages
    let langItems = [];
    let totalLangBytes = 0;
    if (langRes.status === 'fulfilled' && langRes.value.ok) {
      const raw = await langRes.value.json();
      totalLangBytes = Object.values(raw).reduce((a, b) => a + b, 0);
      for (const [name, bytes] of Object.entries(raw)) {
        const pct = totalLangBytes > 0 ? Number(((bytes / totalLangBytes) * 100).toFixed(1)) : 0;
        langItems.push({ name, bytes, formatted_bytes: formatBytes(bytes), percentage: pct });
      }
    }
    const languagesData = {
      total_bytes: totalLangBytes,
      formatted_total: formatBytes(totalLangBytes),
      items: langItems
    };

    // Process contents
    let contentsList = [];
    if (contentsRes.status === 'fulfilled' && contentsRes.value.ok) {
      const raw = await contentsRes.value.json();
      if (Array.isArray(raw)) {
        const dirs = [];
        const files = [];
        raw.forEach(item => {
          const entry = {
            name: item.name,
            path: item.path,
            type: item.type,
            size: item.size || 0,
            formatted_size: item.type === 'file' ? formatBytes(item.size || 0) : null,
            html_url: item.html_url
          };
          if (entry.type === 'dir') dirs.push(entry);
          else files.push(entry);
        });
        dirs.sort((a, b) => a.name.localeCompare(b.name));
        files.sort((a, b) => a.name.localeCompare(b.name));
        contentsList = [...dirs, ...files];
      }
    }

    // Process README
    let readmeInfo = { available: false, name: null, size: 0, preview: null, html_url: null };
    if (readmeRes.status === 'fulfilled' && readmeRes.value.ok) {
      const raw = await readmeRes.value.json();
      readmeInfo.available = true;
      readmeInfo.name = raw.name || 'README.md';
      readmeInfo.size = raw.size || 0;
      readmeInfo.html_url = raw.html_url;
      if (raw.content) {
        try {
          const decoded = atob(raw.content.replace(/\s/g, ''));
          const cleaned = decoded.replace(/!\[.*?\]\(.*?\)/g, '').replace(/<[^>]+>/g, '').replace(/\n{3,}/g, '\n\n').trim();
          readmeInfo.preview = cleaned.length > 450 ? cleaned.slice(0, 450).trim() + '...' : cleaned;
        } catch {
          readmeInfo.preview = 'README preview could not be decoded.';
        }
      }
    }

    // Contributors count
    let contributorCount = null;
    if (contribRes.status === 'fulfilled' && contribRes.value.ok) {
      const link = contribRes.value.headers.get('link') || '';
      const match = link.match(/[?&]page=(\d+)[^>]*>;\s*rel="last"/);
      if (match) contributorCount = parseInt(match[1], 10);
    }

    const insights = generateClientInsights(repoData, languagesData, readmeInfo);

    return {
      repository: {
        name: repoData.name,
        full_name: repoData.full_name,
        owner: repoData.owner ? repoData.owner.login : '',
        owner_avatar: repoData.owner ? repoData.owner.avatar_url : '',
        description: repoData.description || 'No description provided.',
        html_url: repoData.html_url,
        topics: repoData.topics || [],
        language: repoData.language || 'Not specified',
        license: (repoData.license && (repoData.license.spdx_id || repoData.license.name)) || 'None',
        created_at: repoData.created_at,
        updated_at: repoData.updated_at,
        pushed_at: repoData.pushed_at,
        stars: repoData.stargazers_count || 0,
        forks: repoData.forks_count || 0,
        watchers: repoData.subscribers_count || repoData.watchers_count || 0,
        open_issues: repoData.open_issues_count || 0,
        size_kb: repoData.size || 0,
        formatted_size: formatBytes((repoData.size || 0) * 1024),
        default_branch: repoData.default_branch || 'main',
        archived: repoData.archived || false,
        contributors_count: contributorCount
      },
      languages: languagesData,
      contents: contentsList,
      readme: readmeInfo,
      insights
    };
  }

  // Main Analysis Dispatcher
  async function analyzeRepository(url) {
    if (!url) return;

    showLoading();

    try {
      let data = null;
      let parsed = null;
      try {
        parsed = parseGithubUrl(url);
      } catch (err) {
        showError('Invalid repository URL', err.message);
        return;
      }

      // Try FastAPI backend first
      try {
        const apiUrl = `/api/analyze?url=${encodeURIComponent(url.trim())}`;
        const response = await fetch(apiUrl);
        if (response.ok) {
          data = await response.json();
        } else if (response.status === 404 || response.status === 502 || response.status === 500) {
          // If server /api/analyze isn't found (static Firebase Hosting CDN), fall through to client-side
          data = await analyzeClientSide(parsed.owner, parsed.repo);
        } else {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || 'Analysis request failed.');
        }
      } catch (backendErr) {
        // Fallback to direct client-side analysis
        try {
          data = await analyzeClientSide(parsed.owner, parsed.repo);
        } catch (clientErr) {
          showError('Unable to analyze repository', clientErr.message || backendErr.message);
          return;
        }
      }

      // Success: Render dashboard sections
      renderHeader(data.repository);
      renderStats(data.repository);
      renderLanguages(data.languages);
      renderInsights(data.insights);
      renderStructure(data.contents);
      renderReadme(data.readme);

      hideLoading();
      dashboard.classList.remove('hidden');

      // Scroll to dashboard smoothly
      dashboard.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      console.error('Fetch error:', err);
      showError(
        'Connection error',
        'Unable to connect to GitHub. Please check your network connection and try again.'
      );
    }
  }

  // Event Listeners
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    const url = repoInput.value.trim();
    if (url) {
      analyzeRepository(url);
    }
  });

  sampleButtons.forEach(btn => {
    btn.addEventListener('click', function () {
      const url = this.getAttribute('data-url');
      if (url) {
        repoInput.value = url;
        analyzeRepository(url);
      }
    });
  });

  dismissErrorBtn.addEventListener('click', function () {
    hideError();
  });

})();
