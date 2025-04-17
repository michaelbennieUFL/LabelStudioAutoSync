# LabelStudioAutoSync

![圖片](https://github.com/user-attachments/assets/09ec3702-d0fd-4b10-b3b8-55d9f669d0e9)

This application provides an interactive Text User Interface (TUI) for managing export storages in Label Studio projects.


## Features

- Lists all available export storages across all projects
- Allows setting update frequency for each storage (hours 1-24 or days 1-10)
- Provides option to sync a storage immediately with extended timeout (10 minutes)
- Tracks last sync time and calculates next sync time based on frequency
- Automatically sets up cron jobs for scheduled syncing
- Persists configuration between runs
- Interactive blessed-based TUI with keyboard navigation

## Setup

1. Create a `.env` file in the project root with the following content:
   ```
   LABEL_STUDIO_URL=your_label_studio_url
   API_KEY=your_api_key
   ```

2. Install required dependencies:
   ```
   pip install python-dotenv blessed python-crontab
   ```

3. Run the application:
   ```
   python sync.py
   ```

## Usage

The application presents an interactive interface:

- Use **↑/↓** arrow keys to navigate between storages
- Press **c** to configure the selected storage:
  - Choose frequency unit (h for hours, d for days)
  - Enter frequency value (1-24 hours or 1-10 days)
  - Configuration is automatically saved and cron jobs are updated
- Press **s** to sync the selected storage immediately
  - Sync operations have a 10-minute timeout to handle long-running operations
- Press **x** to clear a cron jonb
- Press **q** to quit the application

## Configuration Persistence

The application saves all configuration to a `storage_config.json` file in the project directory. This includes:
- Update frequencies for each storage
- Last sync times
- Next scheduled sync times

This configuration is loaded each time the application starts, ensuring your settings are preserved between runs.

## Automatic Scheduling

When you configure a storage with an update frequency, the application automatically:
1. Creates or updates cron jobs to run at the specified intervals
2. Removes any outdated cron jobs
3. Ensures the sync operations run in the background without manual intervention

## Command-line Usage

For advanced users or scripting:

```
python sync.py --sync ID
```

This will sync the storage with the specified ID and exit, which is the command used by the automatically created cron jobs.
