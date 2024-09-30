import os
import requests
import zipfile
import shutil
import subprocess

GITHUB_API_URL = 'https://api.github.com/repos/{owner}/{repo}/releases/latest'
LOCAL_VERSION_FILE = 'version.txt'
GAME_DIRECTORY = 'bin/'
GAME_EXECUTABLE = 'bin/2DLOS.exe'  # Path to the game executable
DOWNLOAD_PATH = 'downloaded_update.zip'


def get_local_version():
    """Read the local version from the version.txt file."""
    if os.path.exists(LOCAL_VERSION_FILE):
        with open(LOCAL_VERSION_FILE, 'r') as f:
            return f.read().strip()
    return None


def get_latest_version(owner, repo):
    """Fetch the latest release information from GitHub."""
    url = GITHUB_API_URL.format(owner=owner, repo=repo)
    response = requests.get(url)
    if response.status_code == 200:
        latest_release = response.json()
        latest_version = latest_release['tag_name']
        download_url = latest_release['assets'][0]['browser_download_url']
        return latest_version, download_url
    else:
        print("URL: {}".format(url))
        print(f"Failed to check for updates. HTTP Status Code: {response.status_code}")
        return None, None


def download_update(download_url):
    """Download the latest release from GitHub."""
    response = requests.get(download_url, stream=True)
    with open(DOWNLOAD_PATH, 'wb') as f:
        shutil.copyfileobj(response.raw, f)
    print(f"Update downloaded to {DOWNLOAD_PATH}")


def install_update():
    """Install the downloaded update (assumes a zip file)."""
    with zipfile.ZipFile(DOWNLOAD_PATH, 'r') as zip_ref:
        zip_ref.extractall(GAME_DIRECTORY)
    print(f"Update installed to {GAME_DIRECTORY}")
    os.remove(DOWNLOAD_PATH)


def update_version_file(new_version):
    """Update the version file with the new version."""
    with open(LOCAL_VERSION_FILE, 'w') as f:
        f.write(new_version)
    print(f"Updated local version to {new_version}")


def check_for_updates(owner, repo):
    """Check for updates and install if a new version is found."""
    local_version = get_local_version()
    latest_version, download_url = get_latest_version(owner, repo)

    if latest_version is None:
        print("Could not retrieve the latest version.")
        return

    if local_version is None or local_version != latest_version:
        print(f"New version available: {latest_version}")
        download_update(download_url)
        install_update()
        update_version_file(latest_version)
    else:
        print("Game is up-to-date.")


def launch_game():
    """Launch the game."""
    subprocess.run([GAME_EXECUTABLE])


if __name__ == '__main__':
    # Replace with your actual GitHub repository owner and name
    owner = 'dargust'
    repo = '2D-LOS-Sim'

    # Step 1: Check for updates
    check_for_updates(owner, repo)

    # Step 2: Launch the game
    launch_game()
