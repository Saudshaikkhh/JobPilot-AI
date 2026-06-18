# 🤖 AI Job Application Automation System

A powerful Python-based automation bot that intelligently searches and applies to jobs across multiple platforms (LinkedIn, Naukri, Hirist, Indeed) using saved session cookies, intelligent filtering, and human-like behavior simulation.

---

## ✨ Features

### Core Capabilities
- **Multi-Platform Support**: LinkedIn, Naukri, Hirist, Indeed
- **Intelligent Filtering**: Keywords, salary range, location, posting date, company blocklist
- **Session-Based Authentication**: Uses saved browser cookies (no manual login per run)
- **Duplicate Detection**: Prevents re-applying to the same job
- **Anti-Detection**: Human-like delays, random scrolling, realistic mouse movements
- **Dry-Run Mode**: Test the entire workflow without applying to jobs
- **Daily Limits**: Configurable application caps per platform
- **Rich CLI Dashboard**: Beautiful terminal interface with progress tracking
- **SQLite Database**: Local job tracking and application history
- **Scheduled Automation**: Daily cron-based job applications

### Safety Features
- ✅ Dry-run mode enabled by default
- ✅ Daily application limits per platform
- ✅ Session health monitoring
- ✅ Detailed logging of all activities
- ✅ Graceful error handling with recovery
- ⚠️ Credentials stored in `.env` (never committed)

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Browser Automation** | Playwright | Native async, session/cookie support |
| **Stealth/Anti-Detection** | playwright-stealth | Prevents bot detection |
| **Language** | Python 3.11+ | Modern, async-first |
| **Database** | SQLite + SQLAlchemy | Zero-config, local storage |
| **CLI Framework** | Click + Rich | Beautiful terminal UI |
| **Configuration** | YAML + .env | Human-readable config & secrets |
| **Scheduling** | APScheduler | Cron-like job scheduling |
| **HTTP Client** | httpx | Async HTTP requests |

---

## 📋 Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Playwright browsers** (chromium, firefox, webkit)
- **Session Cookies**: Extracted from your browser for each platform
- **Resume PDF**: Single or multiple resume files

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
# Clone the repository
git clone <repo_url>
cd Applying\ Job

# Create virtual environment
python -m venv .venv

# Activate venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Extract Session Cookies

You'll need to extract cookies from your browser for each platform. Here's how:

#### LinkedIn
1. Open LinkedIn in your browser
2. Press `F12` → Application/Storage tab → Cookies → `linkedin.com`
3. Find and copy: `li_at`, `JSESSIONID`, `bcookie`, `bscookie`

#### Naukri
1. Open Naukri
2. Extract: `nauk_at` (JWT token)

#### Indeed
1. Open Indeed
2. Extract: `JSESSIONID`, `INDEED_CSRF_TOKEN`

#### Hirist
1. Open Hirist
2. Extract: `JSESSIONID`

### 3. Configure Environment

Create a `.env` file in the project root:

```bash
# LinkedIn Cookies
LI_AT=your_li_at_cookie_here
LI_JSESSIONID=your_jsessionid_here
LI_BCOOKIE=your_bcookie_here
LI_BSCOOKIE=your_bscookie_here

# Naukri
NAUK_AT=your_naukri_token_here

# Indeed
INDEED_JSESSIONID=your_indeed_jsessionid_here
INDEED_CSRF_TOKEN=your_indeed_csrf_token_here

# Hirist
HIRIST_JSESSIONID=your_hirist_jsessionid_here
```

**⚠️ IMPORTANT**: Never commit `.env` to version control. It's already in `.gitignore`.

### 4. Configure Job Search

Edit `config.yaml`:

```yaml
# Search Keywords
keywords:
  - "Full Stack Developer"
  - "Senior Backend Engineer"
  - "Cloud Architect"

# Salary Range (in INR)
salary:
  min: 800000
  max: 2500000
  currency: "INR"

# Preferred Locations
locations:
  - "Bengaluru"
  - "Remote"
  - "Hybrid"
  - "Hyderabad"

# Job Type Preferences
job_types:
  - "Full-time"
  - "Contract"

# Only apply to jobs posted within N days
posted_within_days: 7

# Daily Application Limits
daily_limits:
  linkedin: 20
  naukri: 25
  hirist: 15
  indeed: 10

# Companies to Skip
blocked_companies:
  - "SpamCorp"
  - "MLM Co"
  - "BadCompany"

# Safety Settings
dry_run: true              # START with true! Test before going live
headless: false            # Show browser (helpful for debugging)
browser: "chromium"        # chromium | firefox | webkit

# Resume Path
resume_path: "resume/saud-resume.pdf"

# Schedule (APScheduler format)
schedule:
  cron: "0 9 * * *"        # Daily at 9:00 AM
  enabled: false           # Enable when ready for automation
```

### 5. Verify Setup

Run connectivity check to verify all platform sessions are valid:

```bash
python tests/run_connectivity_check.py
```

Expected output:
```
==================================================
         SESSION HEALTH & CONNECTIVITY SUMMARY
==================================================
  Linkedin     : AUTHENTICATED (OK)
  Naukri       : AUTHENTICATED (OK)
  Hirist       : AUTHENTICATED (OK)
  Indeed       : AUTHENTICATED (OK)
==================================================
```

---

## 🎮 Usage

### Command Reference

#### Run Dry-Run (Recommended First)
```bash
# Test the entire workflow without applying
python src/main.py run --dry-run

# Test single platform
python src/main.py run --platform linkedin --dry-run
```

#### Run Live Mode (Apply to Jobs)
```bash
# Apply to jobs on all platforms
python src/main.py run

# Apply only on LinkedIn
python src/main.py run --platform linkedin

# Apply with limit override
python src/main.py run --limit 5
```

#### View Application Status
```bash
# Show today's statistics
python src/main.py status

# Show detailed history
python src/main.py history

# Filter by platform
python src/main.py history --platform linkedin

# Filter by date range
python src/main.py history --days 7
```

#### Session Management
```bash
# Check all platform sessions
python src/main.py sessions

# Update expired sessions (manual)
python src/main.py sessions --refresh
```

#### Blocklist Management
```bash
# Add company to blocklist
python src/main.py blocklist add "CompanyName"

# Add keyword to blocklist
python src/main.py blocklist add "bad keyword" --type keyword

# View blocklist
python src/main.py blocklist list

# Remove from blocklist
python src/main.py blocklist remove "CompanyName"
```

#### Scheduling
```bash
# Start daily automated runs
python src/main.py schedule start

# Stop scheduled runs
python src/main.py schedule stop

# Show schedule status
python src/main.py schedule status
```

---

## 📁 Project Structure

```
Applying Job/
├── .env                          # Secrets & cookies (gitignored)
├── .gitignore
├── config.yaml                   # Job search configuration
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project metadata
├── README.md
│
├── resume/
│   └── saud-resume.pdf          # Resume for uploads
│
├── data/
│   └── job_bot.db               # SQLite database (auto-created)
│
├── logs/
│   └── bot_YYYY-MM-DD.log       # Daily log files
│
├── src/
│   ├── __init__.py
│   ├── main.py                  # CLI entry point (Click)
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Config loader (YAML + .env)
│   │   ├── database.py          # SQLite setup, SQLAlchemy
│   │   ├── models.py            # ORM models
│   │   └── logger.py            # Logging setup
│   │
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── browser_manager.py   # Playwright lifecycle & cookies
│   │   └── anti_detect.py       # Human-like behavior simulation
│   │
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract adapter interface
│   │   ├── linkedin.py          # LinkedIn Easy Apply
│   │   ├── naukri.py            # Naukri adapter
│   │   ├── hirist.py            # Hirist adapter
│   │   ├── indeed.py            # Indeed adapter
│   │   └── registry.py          # Platform registry
│   │
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── filter.py            # Job filtering logic
│   │   ├── applier.py           # Application orchestrator
│   │   └── dedup.py             # Duplicate detection
│   │
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── scheduler.py         # APScheduler cron setup
│   │
│   └── dashboard/
│       ├── __init__.py
│       └── cli_dashboard.py     # Rich CLI dashboard
│
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_filter.py
│   ├── test_dedup.py
│   ├── test_connectivity.py
│   └── run_connectivity_check.py

```

---

## 🗄️ Database Schema

### Tables

#### `applications`
Stores all job applications and attempts.

```sql
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,           -- 'linkedin', 'naukri', etc.
    job_title TEXT NOT NULL,
    company TEXT NOT NULL,
    job_url TEXT UNIQUE NOT NULL,     -- Prevents duplicates
    salary_range TEXT,
    location TEXT,
    status TEXT NOT NULL,             -- 'applied' | 'failed' | 'skipped' | 'dry_run'
    failure_reason TEXT,              -- Why it was skipped/failed
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `blocklist`
Companies and keywords to skip.

```sql
CREATE TABLE blocklist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,               -- 'company' | 'keyword'
    value TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### `session_health`
Tracks session validity per platform.

```sql
CREATE TABLE session_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT UNIQUE NOT NULL,
    last_valid TIMESTAMP,
    is_expired BOOLEAN DEFAULT 0,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 🔐 Security & Privacy

### ⚠️ Important Warnings

1. **Session Cookies Expire**: LinkedIn cookies last ~1 year, but Naukri/Indeed may expire sooner. When you see "EXPIRED" in session status, re-extract and update `.env`.

2. **Bot Detection**: LinkedIn and Indeed have aggressive bot detection. The system includes:
   - Random delays between actions (1-4 seconds)
   - Human-like mouse movements
   - Realistic scrolling behavior
   - Rotating user-agents
   - playwright-stealth plugin

3. **Account Risk**: Excessive automated applications may trigger:
   - CAPTCHA challenges
   - Temporary account restrictions
   - Action blocks

**Mitigations:**
- ✅ Start with `dry_run: true`
- ✅ Use `daily_limits` to avoid excessive applications
- ✅ Gradually increase limits as you gain confidence
- ✅ Monitor account for security alerts

### Credential Management

- Secrets stored in `.env` (never in code)
- `.env` is in `.gitignore` (never committed)
- Use `python-dotenv` to load at runtime
- Rotate cookies every 6 months as best practice

---

## 🧪 Testing

### Run Unit Tests

```bash
# Test filter logic
python -m pytest tests/test_filter.py -v

# Test deduplication
python -m pytest tests/test_dedup.py -v

# Test configuration loading
python -m pytest tests/test_config.py -v

# All tests
python -m pytest tests/ -v --cov=src
```

### Manual Verification Checklist

- [ ] **Session Validation**: `python tests/run_connectivity_check.py`
- [ ] **Dry-Run Test**: `python src/main.py run --dry-run` (verify no actual applications)
- [ ] **Single Platform**: `python src/main.py run --platform linkedin --dry-run`
- [ ] **History Check**: `python src/main.py history` (verify results logged)
- [ ] **Blocklist Test**: Add a company, verify it's skipped in next run
- [ ] **Live Apply**: Set `daily_limits.linkedin: 1`, run live mode, verify 1 application

---

## 🐛 Troubleshooting

### Common Issues

#### 1. **"NotImplementedError: _make_subprocess_transport"**
```
Error: File "asyncio\base_events.py", line 528, in _make_subprocess_transport
```
**Solution**: Ensure you're using the default ProactorEventLoopPolicy on Windows. This is auto-handled in `run_connectivity_check.py`.

#### 2. **"ValueError: I/O operation on closed pipe"**
This is a harmless cleanup warning on Windows during garbage collection. It's suppressed by default.

#### 3. **Session Validation Fails**
```
[ERROR] - LinkedIn session validated successfully (redirect to login detected)
```
**Solution**: 
- Extract fresh cookies from your browser
- Update `.env` with new values
- Run `python tests/run_connectivity_check.py` to verify

#### 4. **"No jobs found" but website has jobs**
**Solutions**:
- Check `keywords` in `config.yaml`
- Check `locations` match job listings
- Run in `headless: false` mode to see what's happening
- Check browser console (F12) for JavaScript errors

#### 5. **Rate Limited / Blocked**
**Signs**: Redirects to login, CAPTCHA appears, or "Unusual activity" message

**Recovery**:
1. Wait 24-48 hours
2. Extract fresh cookies
3. Lower `daily_limits` to 5-10
4. Verify `anti_detect` delays are working

#### 6. **Database Locked**
```
OperationalError: database is locked
```
**Solution**: Close any other processes accessing `job_bot.db`, or delete it to recreate:
```bash
rm data/job_bot.db
```

---

## 📊 Workflow Example

### Dry-Run Mode (Recommended First)

```bash
$ python src/main.py run --dry-run

==================================================
   LAUNCHING APPLICATION ENGINE (DRY-RUN)
==================================================

[09:01:23] INFO - Validating LinkedIn session...
[09:01:30] INFO - LinkedIn session: AUTHENTICATED ✅

[09:01:30] INFO - Searching: "Full Stack Developer" in "Bengaluru"
[09:01:45] INFO - Found 12 jobs

Processing jobs...
[09:01:46] DRY-RUN → "Senior Full Stack Dev" @ Razorpay → PASS (would apply)
[09:01:47] SKIP → "Junior Frontend" @ StartupX → Salary below range
[09:01:48] DRY-RUN → "Backend Engineer" @ PayU → PASS (would apply)
[09:01:49] SKIP → "QA Engineer" @ TechCorp → Keyword mismatch
...

==================================================
         SUMMARY (DRY-RUN MODE)
==================================================
  Platform   | Found | Would Apply | Skipped
  LinkedIn   |   12  |      6      |   6
  Naukri     |   15  |      8      |   7
  Hirist     |    8  |      4      |   4
  Indeed     |    5  |      2      |   3
==================================================
Total: 40 jobs found | 20 would apply | 20 skipped

✅ Dry-run complete. To apply for real, set dry_run: false in config.yaml
```

### Live Mode (After Verification)

```bash
$ python src/main.py run

[09:15:23] INFO - Validating sessions...
[09:15:30] INFO - All sessions: AUTHENTICATED ✅

[09:15:31] ✅ APPLIED → "Senior Full Stack Dev" @ Razorpay
[09:15:42] ✅ APPLIED → "Backend Engineer" @ PayU
[09:15:53] ✅ APPLIED → "Principal Engineer" @ Uber
...

==================================================
         TODAY'S APPLICATION SUMMARY
==================================================
  Platform   | Applied | Failed | Skipped | Daily Limit
  LinkedIn   |    6    |   0    |   14    |  20/20
  Naukri     |    8    |   1    |   6     |  25/25
  Hirist     |    4    |   0    |   4     |  15/15
  Indeed     |    2    |   0    |   3     |  10/10
==================================================
Total Applied: 20 | Failed: 1 | Skipped: 27
```

---

## 🔄 Platform Support Details

### LinkedIn ✅
- **Status**: Fully Supported
- **Authentication**: `li_at` + `JSESSIONID` + `bcookie`
- **Apply Method**: Easy Apply button
- **Limitations**: Strong bot detection, requires delays
- **Resume**: Auto-uploaded from saved resume

### Naukri ✅
- **Status**: Fully Supported
- **Authentication**: `nauk_at` JWT token
- **Apply Method**: One-click apply
- **Limitations**: Moderate bot detection
- **Resume**: Uses profile resume

### Hirist ✅
- **Status**: Fully Supported
- **Authentication**: `JSESSIONID`
- **Apply Method**: Direct application form
- **Limitations**: Minimal bot detection (dev-friendly)
- **Resume**: Upload required

### Indeed ✅
- **Status**: Fully Supported
- **Authentication**: `JSESSIONID` + `INDEED_CSRF_TOKEN`
- **Apply Method**: Multi-step form
- **Limitations**: Very aggressive bot detection
- **Resume**: Upload required

---

## 📈 Performance & Optimization

### Application Speed
- Average: **3-5 seconds per application**
- LinkedIn: 5-8 seconds (Easy Apply has extra steps)
- Others: 2-4 seconds

### Daily Processing
With default `daily_limits`:
- LinkedIn: 20 apps = ~2-3 minutes
- Naukri: 25 apps = ~2-3 minutes
- Hirist: 15 apps = ~1-2 minutes
- Indeed: 10 apps = ~1 minute
- **Total: ~6-9 minutes daily**

### Resource Usage
- Memory: ~150-200 MB (Playwright process)
- CPU: Low (mostly I/O bound)
- Network: ~5-10 MB per run

---

## 📝 Logging

### Log Levels

```
[INFO]    - Normal operations (job found, applied, etc.)
[WARNING] - Session expiry, retry logic triggered
[ERROR]   - Application failed, network error, validation error
[DEBUG]   - Detailed flow (use DEBUG log level to troubleshoot)
```

### Log Format

```
[2026-06-18 09:01:23] [PLATFORM] [JOB_TITLE] @ [COMPANY] → [STATUS]
```

Example:
```
[2026-06-18 09:01:23] [LinkedIn] "Senior Full Stack Dev" @ Razorpay → APPLIED ✅
[2026-06-18 09:01:51] [LinkedIn] "Backend Engineer" @ PayU → SKIPPED (salary below range)
[2026-06-18 09:02:15] [Naukri] "QA Engineer" @ TechCorp → FAILED (form validation error)
```

### Access Logs

```bash
# View today's logs
cat logs/bot_$(date +%Y-%m-%d).log

# View real-time logs
tail -f logs/bot_*.log

# Search for errors
grep ERROR logs/bot_*.log
```

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Support for more job platforms (Glassdoor, Monster, etc.)
- [ ] AI-powered cover letter generation
- [ ] Advanced filtering (skills matching, company reviews)
- [ ] Web dashboard for remote monitoring
- [ ] Telegram/Slack notifications

Please open an issue or submit a pull request.

---

## ⚖️ Legal & Ethical

### ⚠️ Disclaimer

This tool is for **personal use only**. By using it, you agree to:

1. **Comply** with each platform's Terms of Service
2. **Use responsibly** with reasonable rate limits
3. **Avoid spam** (only apply to relevant jobs)
4. **Accept risk** of account restrictions/bans

**Not recommended for:**
- Massive bulk applications (10,000+ per day)
- Applying to irrelevant jobs
- Commercial automation services
- Violating platform ToS

---

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [playwright-stealth](https://github.com/microsoft/playwright-stealth)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/)
- [Click CLI Framework](https://click.palletsprojects.com/)
- [APScheduler](https://apscheduler.readthedocs.io/)

---

## 📞 Support

### Issues & Bugs
Open an issue with:
- Python version
- Platform (Windows/macOS/Linux)
- Error message
- Steps to reproduce

### Feature Requests
Describe the feature and use case

### Security Issues
⚠️ **Do not open public issues for security concerns**. Email directly instead.

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🎯 Roadmap

### Phase 1 ✅ (Current)
- Core browser automation
- Multi-platform support
- Basic CLI interface
- SQLite logging

### Phase 2 🚧 (Planned)
- AI cover letter generation (OpenAI GPT)
- Advanced filtering (skills, company reviews)
- Email notification system
- Telegram/Slack bot integration

### Phase 3 📅 (Future)
- Web dashboard for statistics
- Mobile app for alerts
- Resume optimization suggestions
- Interview preparation resources

---

## 🙏 Acknowledgments

Inspired by job application automation best practices and anti-detection techniques used in modern web automation.

---

**Happy job hunting! 🚀**

*Last Updated: 2026-06-18*
