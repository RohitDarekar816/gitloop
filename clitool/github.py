from imaplib import Commands
import requests
import os
import sys
import threading
import time
from colorama import init, Fore, Style
from datetime import datetime, timedelta, timezone
import pytz
import argparse
from playsound import playsound
# import winsound

init(autoreset=True)

GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_API_URL = 'https://api.github.com'
GITHUB_DEVICE_CODE_URL = 'https://github.com/login/device/code'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'

seen_commits = set()
TOKEN_FILE = os.path.expanduser('~/.github_commit_monitor_token')

def save_token(token):
    try:
        with open(TOKEN_FILE, 'w') as f:
            f.write(token)
    except Exception as e:
        print(Fore.RED + f'[ERROR] Could not save token: {e}', file=sys.stderr)

def load_token():
    try:
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        print(Fore.RED + f'[ERROR] Could not load token: {e}', file=sys.stderr)
    return None

def is_token_valid(token):
    headers = {'Authorization': f'token {token}'}
    resp = requests.get(f'{GITHUB_API_URL}/user', headers=headers)
    return resp.status_code == 200

SOUND_FILE = './ding.wav'

# def play_notification_sound(SOUND_FILE):
#     try:
#         playsound(SOUND_FILE)
#     except Exception as e:
#         print(Fore.RED + f'[ERROR] Could not play sound: {e}', file=sys.stderr)

def github_device_flow(client_id, scope='repo'):
    # Step 1: Get device/user code
    resp = requests.post(GITHUB_DEVICE_CODE_URL, data={
        'client_id': client_id,
        'scope': scope
    }, headers={'Accept': 'application/json'})
    if resp.status_code != 200:
        print(Fore.RED + '[ERROR] Failed to start device flow', file=sys.stderr)
        sys.exit(1)
    data = resp.json()
    print(f"Go to {Fore.YELLOW}{data['verification_uri']} {Style.RESET_ALL}and enter code: {Fore.CYAN}{data['user_code']}{Style.RESET_ALL}")
    # Step 2: Poll for access token
    while True:
        time.sleep(data['interval'])
        token_resp = requests.post(GITHUB_TOKEN_URL, data={
            'client_id': client_id,
            'device_code': data['device_code'],
            'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
        }, headers={'Accept': 'application/json'})
        token_json = token_resp.json()
        if 'access_token' in token_json:
            print(Fore.GREEN + '[SUCCESS] Authenticated!')
            return token_json['access_token']
        elif token_json.get('error') == 'authorization_pending':
            continue
        else:
            print(Fore.RED + f"[ERROR] {token_json.get('error_description', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

def get_latest_commits(token, interval=30, repo_filter=None, play_sound=True):
    headers = {'Authorization': f'token {token}'}
    start_time_utc = datetime.now(timezone.utc)
    ist = pytz.timezone('Asia/Kolkata')
    while True:
        try:
            # Get user repos
            repos_resp = requests.get(f'{GITHUB_API_URL}/user/repos', headers=headers)
            if repos_resp.status_code != 200:
                print(Fore.RED + '[ERROR] Failed to fetch repos', file=sys.stderr)
                time.sleep(interval)
                continue
            repos = repos_resp.json()
            for repo in repos:
                repo_name = repo['full_name']
                if repo_filter and repo_name.lower() != repo_filter.lower():
                    continue
                commits_url = f"{GITHUB_API_URL}/repos/{repo_name}/commits"
                commits_resp = requests.get(commits_url, headers=headers, params={'per_page': 10})
                if commits_resp.status_code == 200:
                    commits = commits_resp.json()
                    # Only show commits after tool start time
                    filtered_commits = []
                    for commit in commits:
                        commit_date = commit['commit']['author']['date']
                        commit_dt_utc = datetime.strptime(commit_date, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
                        if commit_dt_utc > start_time_utc:
                            filtered_commits.append((commit_dt_utc, commit))
                    # Sort by date ascending (oldest first)
                    filtered_commits.sort(key=lambda x: x[0])
                    for commit_dt_utc, commit in filtered_commits:
                        sha = commit['sha']
                        if sha not in seen_commits:
                            seen_commits.add(sha)
                            msg = commit['commit']['message']
                            author = commit['commit']['author']['name']
                            # Convert UTC to IST
                            commit_dt_ist = commit_dt_utc.astimezone(ist)
                            timestamp_ist = commit_dt_ist.strftime('%Y-%m-%d %H:%M:%S IST')
                            url = commit['html_url']
                            print(f"{Fore.CYAN}[NEW COMMIT]{Style.RESET_ALL} Repo: {Fore.YELLOW}{repo_name}{Style.RESET_ALL}\n  Author: {Fore.GREEN}{author}{Style.RESET_ALL}\n  Message: {Fore.MAGENTA}{msg}{Style.RESET_ALL}\n  Time: {Fore.BLUE}{timestamp_ist}{Style.RESET_ALL}\n  URL: {Fore.LIGHTWHITE_EX}{url}{Style.RESET_ALL}\n", flush=True)
                            # check if mattermost webhook URL is set
                            if 'MATTERMOST_WEBHOOK_URL' in os.environ:
                                # Send notification to Mattermost
                                message = f"New commit in {repo_name} by {author}:\n Commit Msg: {msg}\nTime: {timestamp_ist}\nURL: {url}" 
                                send_notification_to_mattermost(message)
                            else:
                                print(Fore.LIGHTBLACK_EX + '[INFO] MATTERMOST_WEBHOOK_URL not set, skipping Mattermost notification.', file=sys.stderr)
                            # if play_sound:
                            #     play_notification_sound(SOUND_FILE)
                else:
                    print(Fore.RED + f'[ERROR] Failed to fetch commits for {repo_name}: {commits_resp.status_code}', file=sys.stderr)
            time.sleep(interval)
        except Exception as e:
            print(Fore.RED + f'[EXCEPTION] {e}', file=sys.stderr)
            time.sleep(interval)
            
def send_notification_to_mattermost(message):
    mattermost_webhook_url = os.environ.get('MATTERMOST_WEBHOOK_URL')
    if not mattermost_webhook_url:
        print(Fore.RED + '[ERROR] MATTERMOST_WEBHOOK_URL environment variable is not set.', file=sys.stderr)
        return

    payload = {
        'text': message
    }
    
    try:
        response = requests.post(mattermost_webhook_url, json=payload)
        if response.status_code != 200:
            print(Fore.RED + f'[ERROR] Failed to send notification to Mattermost: {response.status_code}', file=sys.stderr)
        else:
            print(Fore.GREEN + '[SUCCESS] Notification sent to Mattermost', flush=True)
    except Exception as e:
        print(Fore.RED + f'[EXCEPTION] {e}', file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(prog='gitloop', description='Real-time GitHub commit monitor (CLI)')
    subparsers = parser.add_subparsers(dest='command', help='Subcommands')

    # --- login subcommand ---
    login_parser = subparsers.add_parser('login', help='Authenticate with GitHub using a personal Client ID')

    # --- monitor subcommand (default/legacy behavior) ---
    monitor_parser = subparsers.add_parser('monitor', help='Start monitoring GitHub commits')
    monitor_parser.add_argument('--interval', type=int, default=30, help='Polling interval in seconds (default: 30)')
    monitor_parser.add_argument('--repo', type=str, help='Only monitor this repository (format: owner/repo)')
    monitor_parser.add_argument('--no-sound', action='store_true', help='Disable sound notification for new commits')
    monitor_parser.add_argument('--mattermost', type=str, help='Mattermost webhook URL for notifications (if not set, we will not send notifications)')

    # ✅ Set default to monitor (must be after defining monitor_parser)
    parser.set_defaults(command='monitor')

    args = parser.parse_args()


    if args.command == 'login':
        client_id = input(Fore.CYAN + 'Enter your GitHub Client ID: ' + Style.RESET_ALL).strip()
        if not client_id:
            print(Fore.RED + '[ERROR] Client ID is required.', file=sys.stderr)
            sys.exit(1)
        token = github_device_flow(client_id)
        save_token(token)
        print(Fore.GREEN + 'GitHub token saved. You can now run: gitloop monitor')
        sys.exit(0)

    elif args.command == 'monitor' or args.command is None:
        print(Fore.YELLOW + 'Starting GitHub CLI commit monitor...')
        token = load_token()
        if token and is_token_valid(token):
            print(Fore.GREEN + 'Loaded saved GitHub token.')
        else:
            if not GITHUB_CLIENT_ID:
                print(Fore.RED + '[ERROR] No token and no client ID found. Run `gitloop login` first.', file=sys.stderr)
                sys.exit(1)
            token = github_device_flow(GITHUB_CLIENT_ID)
            save_token(token)
            print(Fore.GREEN + 'GitHub token saved for future use.')

        interval = getattr(args, 'interval', 30)
        repo = getattr(args, 'repo', None)
        no_sound = getattr(args, 'no_sound', False)
        mattermost = getattr(args, 'mattermost', None)

        if repo:
            print(Fore.YELLOW + f'Polling for new commits in {repo} every {interval} seconds.')
        else:
            print(Fore.YELLOW + f'Polling for new commits in all repos every {interval} seconds.')
        
        if mattermost:
            os.environ['MATTERMOST_WEBHOOK_URL'] = mattermost
            print(Fore.YELLOW + f'Sending notifications to Mattermost webhook: {mattermost}')
        else:
            print(Fore.LIGHTBLACK_EX + 'No Mattermost webhook URL set, notifications will not be sent.')

        if no_sound:
            print(Fore.LIGHTBLACK_EX + 'Sound notification is disabled.')
        elif not os.path.exists(SOUND_FILE):
            print(Fore.LIGHTBLACK_EX + f'Sound file not found: {SOUND_FILE}')
        try:    
            get_latest_commits(token, interval, repo, play_sound=not no_sound)
        except KeyboardInterrupt:
            print(Fore.LIGHTBLUE_EX + '\n[INFO] Gitloop monitor stopped by user. Goodbye!')
            sys.exit(0)

    else:
        print(Fore.RED + 'Please use gitloop monitor to start monitoring your GitHub')

if __name__ == '__main__':
    main()
