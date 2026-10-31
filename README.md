# Game Session Tracker

A local Windows desktop application for tracking how long games and applications run, including background and minimized programs.

Game Session Tracker monitors process lifetimes rather than the currently focused window. Switching to another application does not stop a session: a tracked program continues accumulating time until its process exits.

All tracking data is stored locally. The application provides category-based statistics, CSV exports, a system tray menu, and diagnostic reports for troubleshooting.

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Getting Started](#getting-started)
- [Interface Guide](#interface-guide)
- [Understanding the Time Metrics](#understanding-the-time-metrics)
- [Pause, Stop, Reset, and Exit](#pause-stop-reset-and-exit)
- [Configuration](#configuration)
- [Categories](#categories)
- [Event Sources and Accuracy](#event-sources-and-accuracy)
- [Local Data](#local-data)
- [CSV Export](#csv-export)
- [Logging and Diagnostics](#logging-and-diagnostics)
- [Updating and Backing Up](#updating-and-backing-up)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Known Limitations](#known-limitations)
- [License](#license)

## Features

- Track applications regardless of window focus.
- Include minimized applications and background processes that pass the configured filters.
- Identify process instances using PID and process creation time.
- Group processes with the same executable path into an application.
- Avoid double-counting overlapping processes in the main application-time metric.
- View today's activity, historical sessions, and category statistics.
- Select reporting periods and export summaries to CSV.
- Edit application display names and categories.
- Configure allowlists, exclusions, user filters, and Windows session filters.
- Reset detection state without deleting saved applications or session history.
- Restore, pause, stop, or exit through the system tray menu.
- Export diagnostic information to a TXT file.
- Maintain readable and structured logs with automatic rotation.

### What This Application Does Not Measure

This is a process-runtime tracker, not an active-window productivity tracker.

It does not measure how long you actively interact with an application, whether you are looking at its window, keyboard or mouse activity, time spent on individual websites, or the contents of application windows.

A program left running in the background can continue accumulating runtime.

## Requirements

- Windows 10 or Windows 11.
- Python 3.10 or newer, including Tkinter.
- A writable project directory.
- An internet connection for the initial dependency installation.

Administrator privileges are not automatically requested. If WMI process events are inaccessible, the application falls back to periodic process checks.

The Windows GUI, event source, tray integration, and packaged executable should be verified in your target environment. Automated tests do not replace those checks.

## Installation

### Option 1: Included Startup Script

1. Download and extract the project.
2. Open the extracted project directory.
3. Run `start.bat`.

The script creates a `.venv` virtual environment if necessary, installs the required packages, and starts the application.

The script runs dependency installation when launched, so an existing environment may still cause `pip` to check package requirements.

### Option 2: Manual Installation

Open PowerShell in the project directory:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

You do not need to activate the virtual environment when using its Python executable directly.

For subsequent launches:

```powershell
.\.venv\Scripts\python.exe main.py
```

### Running from PyCharm

1. Open the project root directory.
2. Select `.venv\Scripts\python.exe` as the project interpreter.
3. Run `main.py`.

Do not run individual files inside `src` as standalone scripts unless they explicitly provide a command-line entry point.

## Getting Started

1. Start the application.
2. Check the tracking status and event source near the top of the window.
3. Launch a game or another application.
4. Wait for the minimum-lifetime threshold and the next storage/UI update.
5. Open the Today tab to view its recorded runtime.
6. Use Statistics to explore activity by category.
7. Exit through the application or system tray menu when finished.

The default configuration considers processes belonging to the current user and Windows session, subject to system-process filters and exclusions.

Applications may remain untracked if they are excluded, inaccessible, or terminate before their metadata can be collected.

## Interface Guide

The current interface uses Russian labels. English translations below are provided for reference.

### Main Controls

| Interface label | Meaning |
|---|---|
| `Запуск` | Start or resume the tracker |
| `Пауза обработки` | Pause or resume queue processing |
| `Остановить` | Stop the tracking engine |
| `Сброс детекции` | Reset detection state |
| `Обновить` | Refresh the current report |
| `Выход` | Exit the application |

### Today — `Сегодня`

Displays an application summary for the current local calendar day:

- Application name and category.
- Application runtime.
- Summed process runtime.
- Percentage share.
- Session count.
- Number of active processes.

Click a table heading to sort the table.

### History — `История`

Select a start and end date using the `YYYY-MM-DD` format. The end date is inclusive.

The tab provides an aggregated application summary, a detailed list of up to 1,000 sessions in the selected period, and CSV export of the aggregated summary.

The display limit does not delete older database records.

Intervals crossing a selected date boundary are clipped when calculating the summary. The detailed session table retains the original session timestamps.

### Statistics — `Статистика`

The Statistics tab contains an overview and individual category tabs:

| Stored category | Interface label |
|---|---|
| Games | `Игры` |
| Browser | `Браузеры` |
| Communication | `Коммуникация` |
| System | `Система` |
| Development | `Разработка` |
| Work | `Работа` |
| Media | `Медиа` |
| Other | `Остальные` |

Custom categories found in the rules or database are added automatically.

Available periods:

- Today.
- Last 7 calendar days, including today.
- Last 30 calendar days, including today.
- A custom date range of up to 366 days.

Each category report includes application and session counts, active process count, runtime summaries, a daily chart, top applications, a sortable table, and CSV export.

The overview also compares categories. Empty categories display an empty-data message rather than fabricated activity.

### Settings — `Настройки`

Settings are edited as JSON and validated before saving.

This section also provides a category-rule editor, a button to open the data directory, diagnostic TXT export, and session-history deletion with confirmation.

Stop the tracker before clearing history.

## Understanding the Time Metrics

Several applications can run at once, and one application can have several processes. These situations require different time metrics.

### Application Time

Application time merges overlapping intervals for processes with the same executable path.

Example:

- Process A runs from 10:00 to 11:00.
- Process B, using the same executable path, runs from 10:30 to 11:30.

Application time is **1 hour 30 minutes**, not two hours.

### Process Time

Process time adds each process duration independently. For the same example:

```text
1 hour + 1 hour = 2 process-hours
```

### Time with at Least One Application Running

This metric merges intervals across all applications in the selected report or category.

It answers: for how long was at least one of these applications running?

### Percentage Share

- A category's share is calculated against the sum of application time across the full report.
- An application's table share is calculated within the currently displayed report.

These percentages describe recorded application runtime, not exclusive human attention.

### Important Consequences

- The sum of runtime across different applications can exceed 24 hours in one day.
- Multiple windows belonging to one process do not create separate process sessions.
- Different executable paths are treated as different applications.
- Helper executables are not automatically combined into one product.
- A process already running when the tracker starts can receive its original system creation time, including runtime before the tracker was opened.

## Pause, Stop, Reset, and Exit

### Pause Processing

Pause suspends detection-queue processing. Incoming events can continue accumulating in the persistent buffer.

It does not subtract paused time from a process's lifetime.

### Stop

Stop shuts down the tracking engine and saves pending results.

It does not mark every tracked application as terminated merely because the tracker stopped. Open records are reconciled when tracking starts again.

### Reset Detection

Reset clears transient detection state and makes deferred tasks eligible for reconsideration.

It does not delete the application registry, saved sessions, or historical statistics.

### Exit

Exit closes the application and saves pending tracking results.

If tray minimization is enabled and the tray icon started successfully, closing the main window hides it instead. Use Exit to terminate the application completely.

## Configuration

The main configuration file is `config_v2.json`.

Configuration changes are checked approximately every two seconds while the tracking engine is running. Invalid configuration does not replace the last valid configuration.

Changes to `workers`, `database`, and `theme` require an application restart.

### Detection Modes

| Mode | Behavior |
|---|---|
| `all_user_apps` | Consider all processes that pass filters and exclusions |
| `strict` | Consider only allowlisted names; mandatory filters still apply |
| `allowlist_with_exclusions` | Use the allowlist and additionally apply name/path exclusions |

Example configuration fragment:

```json
{
  "mode": "all_user_apps",
  "allowlist": [
    "chrome.exe",
    "Risk of Rain 2.exe"
  ],
  "excluded_processes": [
    "unwanted-helper.exe"
  ],
  "excluded_paths": []
}
```

This is a fragment, not a replacement for the complete configuration file.

Name and path exclusions use exact matches. Wildcard patterns are not supported.

### Important Settings

| Setting | Purpose |
|---|---|
| `workers` | Concurrent detection workers: 1 or 2 |
| `minimum_lifetime_seconds` | Minimum process lifetime before acceptance |
| `reconcile_seconds` | Reconciliation interval in event-driven mode |
| `fallback_seconds` | Process-check interval in fallback mode |
| `retry_seconds` | Initial retry delay for failed metadata collection |
| `max_retry_seconds` | Maximum retry delay |
| `flush_seconds` | Result-storage flush interval |
| `batch_size` | Storage batch size |
| `current_user_only` | Restrict detection to the current user |
| `current_session_only` | Restrict detection to the current Windows session |
| `excluded_users` | Excluded process-owner accounts |
| `excluded_session_ids` | Excluded Windows session IDs |
| `excluded_processes` | Excluded executable names |
| `excluded_paths` | Excluded executable paths |
| `exclude_os_background` | Apply the known OS-background process-name filter |
| `exclude_self_and_children` | Exclude the tracker and identified child processes |
| `ui_refresh_seconds` | Automatic report refresh interval |
| `log_level` | `INFO`, `DEBUG`, or `WARNING` |
| `metrics_seconds` | Diagnostic metrics interval |
| `minimize_to_tray` | Hide the window on close when the tray is available |
| `database` | SQLite database path |

### System-Process Filtering

Filtering includes kernel PIDs 0 and 4, the tracker and identified children, excluded Windows sessions and users, known OS-background process names, and user-defined name/path exclusions.

The known OS-background filter is a configurable name-based heuristic, not a complete Windows service classifier.

An allowlist entry can override that name-based heuristic, but it does not override kernel PID, user, or session restrictions.

## Categories

Category rules are stored in `categories.json`.

```json
{
  "rules": {
    "chrome.exe": {
      "display_name": "Google Chrome",
      "category": "Browser"
    },
    "risk of rain 2.exe": {
      "display_name": "Risk of Rain 2",
      "category": "Games"
    },
    "my-tool.exe": {
      "display_name": "My Tool",
      "category": "Custom"
    }
  }
}
```

Process-name matching is case-insensitive. Unknown applications default to `Other`.

Changing a rule can update the displayed name and category of previously saved records for that application. Categories are not stored as an immutable historical classification.

## Event Sources and Accuracy

### WMI Mode

The tracker attempts to subscribe to:

```text
Win32_ProcessStartTrace
Win32_ProcessStopTrace
```

When available, these events provide process-lifecycle notifications.

### Polling Fallback

If WMI is unavailable or access is denied, the application periodically compares running processes.

In this mode:

- Processes that start and stop between checks may be missed.
- Process termination times can be approximate.
- Approximate endings are marked in storage and the history view.

A reconciliation pass also helps recover records when a termination event is missed.

The interface displays the current source and fallback reason. The application does not claim event-level accuracy while polling.

## Local Data

Runtime files are created in the project directory. For a packaged executable, they are stored beside the executable.

| File | Purpose |
|---|---|
| `process_tracker_v2.db` | Application registry, sessions, pending tasks, and event buffer |
| `config_v2.json` | Configuration |
| `categories.json` | Application naming and category rules |
| `tracker.log` | Readable diagnostic log |
| `tracker.jsonl` | Structured diagnostic log |
| Rotated log files | Previous log segments |

The application does not automatically upload these files.

## CSV Export

CSV exports contain the loaded aggregated report:

- Application and category.
- Application time in numeric seconds.
- Process time in numeric seconds.
- Session count.
- Average session duration.
- Percentage share.
- Active process count.
- First and last activity timestamps.

Files use UTF-8 with BOM and a semicolon delimiter.

After changing the reporting period, wait for the report to finish loading before exporting.

## Logging and Diagnostics

### Log Files

`tracker.log` is intended for manual reading.

`tracker.jsonl` contains one JSON event per line, including timestamp with timezone, severity, `run_id`, event code, thread name, event-specific context, and traceback/error identifier when applicable.

Repeated messages are rate-limited and counted. Each log rotates at approximately 2 MB, with three backup files per log type.

### Interpreting Metrics

| Metric | Meaning |
|---|---|
| `observed` | Observed processes before all acceptance filters |
| `inflight` | Detection tasks currently assigned to workers |
| `failures` | Accumulated failed detection attempts |
| `average_ms` | Average detection-task processing time, not CPU usage |
| `pending` | Stored pending tasks, including deferred and parked entries |
| `parked` | Filtered entries waiting for reset/configuration changes |
| `spool` | Durable incoming-event buffer |
| `open_sessions` | Saved sessions without a recorded end |
| `source` | WMI, polling, or startup state |
| `source_reason` | Reason for a fallback when available |

A large `pending` count is not by itself proof that all entries are actively being processed or that the queue is growing indefinitely.

### Exporting a Diagnostic TXT Report

Open:

```text
Настройки → Экспорт диагностики TXT
```

The report can include Python/Windows/package versions, configuration, current tracker metrics, current-run event counters, warning/error summaries, and recent log fragments.

Log input is limited to 512 KiB per file and 2 MiB in total. Older content may be omitted. Log-tail summaries may include multiple application launches; current-run counters are reported separately.

If the GUI does not start, run `export_diagnostics.bat`, or:

```powershell
.\.venv\Scripts\python.exe -m src.utils.diagnostics --output diagnostics.txt
```

The command-line export does not include live tracker metrics.

### Privacy

Diagnostic exports offer best-effort masking of Windows home-directory paths and selected configuration values.

Review the TXT before sharing it. Application names, custom text, exception messages, or other identifying information may remain.

Original log files are not anonymized. No automatic report upload is performed.

## Updating and Backing Up

1. Exit the application completely, including the tray process.
2. Back up the project data.
3. Extract the new version into a separate directory.
4. Transfer compatible configuration, category rules, and database files.
5. Start the new version and verify the event source and history.

The `process_tracker_v2.db` schema is compatible with the preceding Beta 0.3/0.4 project versions.

Earlier databases named `tracker.db` or `process_tracker.db` may use different schemas. Do not rename them to make them appear compatible.

SQLite can use `-wal` and `-shm` companion files. Do not discard an active WAL file when copying a database. Prefer a proper SQLite backup if the database has not been cleanly closed.

Existing records are not automatically removed when new process filters are introduced.

If you transfer an older `categories.json`, newer default category rules are not automatically merged into it.

## Troubleshooting

### Python Interpreter Not Found

Select `.venv\Scripts\python.exe` inside the current project. Do not reuse an interpreter path belonging to a deleted or moved project.

### An Application Does Not Appear

Check its actual executable name, detection mode, allowlist, exclusions, user/session restrictions, and minimum-lifetime threshold.

Wait for the report to refresh. A process may also be inaccessible or finish before the tracker can collect its metadata.

### WMI Access Denied

The application should switch to polling and display the fallback reason.

Export diagnostics to inspect the error. Do not weaken Windows security settings solely to enable tracking.

### Category Is Incorrect

Add or edit the executable rule in `categories.json` or the category editor.

### Runtime Seems Too Large

Check whether you are viewing application time, process time, a sum across concurrently running applications, or a process that started before the tracker.

These values have different meanings.

### Application Is Already Running

Check the system tray. A Windows mutex prevents a second instance of this release from starting in the same user session.

### Collecting a Useful Bug Report

Include:

- Application version.
- Steps to reproduce.
- Expected and actual behavior.
- A diagnostic TXT reviewed for private information.
- Whether the issue occurs in source mode or a packaged EXE.
- Whether the source is WMI or polling.

Do not publish your database or unreviewed logs unnecessarily.

## Development

### Run Tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover statistics, filtering, database operations, retry/event races, logging, and diagnostic redaction.

The included results describe automated checks, not complete Windows GUI or performance certification.

### Build an Executable

Run `build.bat`.

The script uses PyInstaller. Verify the generated executable separately, including WMI imports, fallback behavior, tray behavior, database access, shutdown, and diagnostic export.

### Project Structure

```text
game-session-tracker/
├── main.py
├── requirements.txt
├── pyproject.toml
├── config_v2.json
├── categories.json
├── start.bat
├── build.bat
├── export_diagnostics.bat
├── README.md
├── CHANGELOG.md
├── LOG_ANALYSIS.md
├── RELEASE_CHECKLIST.md
├── TEST_RESULTS.txt
├── LICENSE
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── settings.py
│   ├── categories.py
│   ├── filtering.py
│   ├── database.py
│   ├── tracker.py
│   ├── statistics.py
│   ├── windows_monitor.py
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py
│   │   └── category_stats.py
│   └── utils/
│       ├── __init__.py
│       ├── logger.py
│       ├── diagnostics.py
│       ├── export.py
│       └── time_utils.py
└── tests/
    └── test_release.py
```

## Known Limitations

- WMI availability depends on the Windows environment and permissions.
- Polling cannot guarantee detection of short-lived processes.
- End times recovered without a termination event are approximate.
- Protected or inaccessible processes may remain untracked.
- OS-background filtering is heuristic.
- Helper executables are not automatically grouped into product families.
- Large reporting ranges load matching sessions into memory.
- Disk failure or exhaustion can cause event loss.
- Persistent retry scheduling can be affected by changes to the system clock.
- Automatic Windows startup, notifications, and language switching are not implemented.
- CPU, memory, and disk usage should be measured in the target environment; fixed resource usage is not guaranteed.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for the full license text.

Third-party dependencies retain their own licenses.
