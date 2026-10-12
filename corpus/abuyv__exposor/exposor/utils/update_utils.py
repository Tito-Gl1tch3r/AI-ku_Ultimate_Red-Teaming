import os
import requests
import zipfile
import hashlib
import json
import shutil
import io
from pathlib import Path
import logging
import sys


REPO_ZIP_URL = "https://github.com/abuyv/exposor/archive/refs/heads/main.zip"
INTELS_CHECKSUM_URL = "https://raw.githubusercontent.com/abuyv/exposor/refs/heads/main/exposor/intels/checksum.json"
LOCAL_CHANGELOG_FILE = "./intels_changelog.json"
TEMP_FOLDER = "./temp_repo"


def calculate_file_hash(file_path):
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()
  

def calculate_folder_checksum(folder_path, hash_algo="sha256"):
    """
    Calculate the checksum of a folder, including all files and subfolders.

    Args:
        folder_path (str | Path): Path to the folder.
        hash_algo (str): Hash algorithm to use (default: sha256).

    Returns:
        str: The checksum of the folder.
    """
    hasher = hashlib.new(hash_algo)

    for root, _, files in os.walk(folder_path):
        for file in sorted(files):  # Sort to ensure consistent order
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, folder_path)

            hasher.update(relative_path.encode("utf-8"))
            with open(file_path, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)

    return hasher.hexdigest()


def load_local_changelog():
    """Load the local changelog."""
    if os.path.isfile(LOCAL_CHANGELOG_FILE):
        with open(LOCAL_CHANGELOG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_local_changelog(changelog):
    """Save the local changelog."""
    with open(LOCAL_CHANGELOG_FILE, "w") as f:
        json.dump(changelog, f, indent=4)


def download_and_extract_zip(zip_url, extract_path):
    """Download the repository ZIP and extract it."""
    logging.debug("Downloading repository as ZIP...")
    response = requests.get(zip_url, stream=True)
    if response.status_code == 200:
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(extract_path)
        logging.debug("Repository downloaded and extracted.")
    else:
        logging.error(f"Failed to download repository: {response.status_code}")
        sys.exit(0)


def sync_intels_folder(temp_intels_path, local_intels_path):
    """Synchronize the intels folder."""
    os.makedirs(local_intels_path, exist_ok=True)
    updated_files = []

    for root, _, files in os.walk(temp_intels_path):
        for file in files:
            temp_file_path = os.path.join(root, file)
            relative_path = os.path.relpath(temp_file_path, temp_intels_path)
            local_intels_folder = local_intels_path
            local_file_path = os.path.join(local_intels_folder, relative_path)

            local_hash = 0
            if os.path.isfile(local_file_path):
                local_hash = calculate_file_hash(local_file_path)
            # Calculate hash of the remote file
            remote_hash = calculate_file_hash(temp_file_path)

            logging.debug(f"REMOTE FILE HASH: {remote_hash} LOCAL FILE HASH: {local_hash}")

            # Check if file needs to be updated
            if local_hash != remote_hash:
                # Update or add the file
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                shutil.copy2(temp_file_path, local_file_path)
                logging.debug(f"Updated: {relative_path}")
                updated_files.append(relative_path)

    return updated_files


def getchecksum(checksum_path):
    if os.path.exists(checksum_path):
        with open(checksum_path, "r") as f:
            data = json.load(f)
        return data.get("intels_hash")
    else:
        logging.debug(f"Checksum does not exist in {checksum_path}")
        return 0


def update(local_intels_path):
    try:

        response = requests.get(INTELS_CHECKSUM_URL, timeout=10)
        checksum = response.json()

        local_checksum_path = os.path.join(local_intels_path, "checksum.json")

        local_intels_hash = getchecksum(local_checksum_path)
        remote_intels_hash = checksum.get("intels_hash")

        if local_intels_hash == 0 or remote_intels_hash == 0:
            logging.error(f"Checksum does not exist for intels folder")
            return

        if local_intels_hash == remote_intels_hash:
            logging.info("No updates required. intels are up-to-date.")
            return

        logging.info("Updating intels...")

        # Step 1: Download and extract the repository
        if os.path.exists(TEMP_FOLDER):
            shutil.rmtree(TEMP_FOLDER)
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        download_and_extract_zip(REPO_ZIP_URL, TEMP_FOLDER)

        extracted_intels_path = os.path.join(TEMP_FOLDER, "exposor-main", "exposor", "intels")

        # Step 4: Synchronize the intels folder
        if os.path.exists(extracted_intels_path):
            updated_files = sync_intels_folder(extracted_intels_path, local_intels_path)
            if updated_files:
                logging.debug(f"Updated files: {', '.join(updated_files)}")
            else:
                logging.info("No updates required. intels are up-to-date.")
        else:
            logging.error("No intels folder found in the remote repository.")
    except Exception as e:
        logging.error(f"Update failed {e}")

    finally:
        if os.path.exists(TEMP_FOLDER):
            logging.info("Cleaning up temporary files...")
            shutil.rmtree(TEMP_FOLDER)
