# GitLoop

A CLI tool that keeps you in real-time sync with GitHub commits across your repositories. Get instant notifications about new commits with detailed information.

## Features

- Real-time monitoring of GitHub commits
- Repository-specific or all-repositories monitoring
- Timezone-aware commit timestamps (IST)
- Mattermost integration for notifications
- Secure GitHub authentication using device flow
- Persistent token storage for convenience

## Installation

```bash
pip install gitloop
```

## Prerequisites

- Python 3.9 or higher
- GitHub account
- GitHub Client ID (for authentication)

## Setup

1. First-time authentication:
```bash
gitloop login
```

2. When prompted, enter your GitHub Client ID
3. Follow the URL provided and enter the verification code
4. Once authenticated, your token will be saved for future use

## Usage

### Basic Monitoring
```bash
gitloop monitor
```

### Advanced Options
```bash
# Monitor specific repository
gitloop monitor --repo "owner/repository"

# Custom polling interval (in seconds)
gitloop monitor --interval 60

# Disable sound notifications
gitloop monitor --no-sound

# Enable Mattermost notifications
gitloop monitor --mattermost "YOUR_WEBHOOK_URL"
```

### Command Line Arguments

- `--interval`: Polling interval in seconds (default: 30)
- `--repo`: Monitor specific repository (format: owner/repo)
- `--no-sound`: Disable sound notifications
- `--mattermost`: Mattermost webhook URL for notifications

## Environment Variables

- `GITHUB_CLIENT_ID`: Your GitHub Client ID
- `MATTERMOST_WEBHOOK_URL`: Webhook URL for Mattermost notifications

## Output Format

For each new commit, GitLoop displays:
- Repository name
- Author name
- Commit message
- Timestamp (IST)
- Commit URL

## Development

```bash
git clone https://github.com/RohitDarekar816/gitloop.git
cd gitloop
pip install -e .
```

## Dependencies

- requests
- colorama
- pytz
- playsound
- setuptools

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

Rohit Darekar (rohitdarekar816@gmail.com)

## Contributing

Feel free to open issues and pull requests on [GitHub](https://github.com/RohitDarekar816/gitloop).