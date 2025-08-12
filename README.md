Auto-Updating Plex Media Server Repository for QNAP NAS
This repository provides an automatically updated source for Plex Media Server QPKGs, compatible with QNAP NAS devices running QTS or QuTS hero. By adding this repo to your QNAP App Center, you can install and update Plex Media Server directly, with new versions fetched automatically from Plex's official downloads as they are released.
Features

Auto-Updates: A Python script checks Plex's download page daily, downloads new QPKGs, and updates the repository.
Multi-Architecture Support: QPKGs for x86_64 (TS-NASX86) and ARM_64 (TS-NASARM_64) architectures.
QNAP App Center Integration: Add the repo URL to install/update Plex seamlessly.
GitHub-Hosted: Uses GitHub Pages for reliable hosting and GitHub Actions for automation.

User Instructions: Adding the Repository to QNAP

Open QNAP App Center:

On your QNAP NAS, log in to QTS/QuTS hero and open the App Center.


Add the Repository:

Click the gear icon (Settings) in App Center.
Select "App Repository" > "Add".
Enter:
Name: Plex Auto Repo (or any name you prefer).
URL: https://yourusername.github.io/plex-qnap-repo/repo.xml (replace yourusername with the actual GitHub username).


Click "Apply".


Install Plex:

Refresh App Center (click the refresh icon).
Find "Plex Media Server" under the repo (category: Multimedia).
Click "Install" or "Update" if a newer version is available.
After installation, access Plex at http://<NAS_IP>:32400/web.


Verify:

Check logs in /share/PlexData/Logs if issues arise.
Ensure port 32400/tcp is open on your NAS firewall.



Note: Compatible with QTS 5.0.0+ and supported NAS models (e.g., TS-x53, TVS-x72). Test on your specific model, as some older ARM devices may lack transcoding support.
Developer Instructions: Setting Up and Maintaining the Repo
Prerequisites

Python 3.8+ (for running the update script locally).
Git and a GitHub account.
Dependencies: pip install requests beautifulsoup4 lxml semver.
QNAP NAS for testing (optional, for manual verification).

Repository Structure

repo.xml: The QNAP App Center metadata file, listing available Plex QPKGs.
qpkgs/: Directory storing downloaded QPKG files (e.g., PlexMediaServer_1.40.5_x86_64.qpkg).
plex_auto_update.py: Python script to scrape Plex downloads, compute MD5 signatures, and update repo.xml.
config.json: Configuration file with repo settings (e.g., architectures, Plex URL).
.github/workflows/plex-update.yml: GitHub Actions workflow for daily updates.

Setup

Clone the Repository:
git clone https://github.com/yourusername/plex-qnap-repo.git
cd plex-qnap-repo


Install Dependencies:
pip install requests beautifulsoup4 lxml semver


Configure config.json:

Update repo_link to match your GitHub Pages URL (e.g., https://yourusername.github.io/plex-qnap-repo).
Adjust plex_downloads_url if Plex changes their download page structure.
Add more architectures in architectures if needed (e.g., TS-X41).

Example config.json:
{
  "plex_downloads_url": "https://www.plex.tv/media-server-downloads/",
  "architectures": {
    "TS-NASX86": "x86_64",
    "TS-NASARM_64": "arm_64"
  },
  "current_versions": {},
  "repo_title": "Auto-Updating Plex Repo for QNAP",
  "repo_link": "https://yourusername.github.io/plex-qnap-repo",
  "repo_description": "Automatically updated Plex Media Server QPKGs"
}


Run the Update Script Locally (optional, for testing):
python plex_auto_update.py


Checks Plex's download page, downloads new QPKGs, updates repo.xml, and commits changes.
Verify outputs: Check qpkgs/ for new files, repo.xml for updated entries.


Enable GitHub Pages:

In your GitHub repo, go to Settings > Pages.
Set Source to main branch, root directory.
Note the URL (e.g., https://yourusername.github.io/plex-qnap-repo).


Enable GitHub Actions:

The .github/workflows/plex-update.yml runs daily at midnight UTC or manually via the Actions tab.
No additional setup needed; it installs Python, dependencies, and runs plex_auto_update.py.



Testing

Local Testing:
Run python plex_auto_update.py.
Check qpkgs/ for downloaded QPKGs and repo.xml for new <item> entries.
Use md5sum to verify signatures match XML <signature> tags.


QNAP Testing:
Add the repo URL to App Center (see User Instructions).
Install Plex and verify it runs (/etc/init.d/plex.sh start via SSH if needed).
Test updates by simulating a new Plex version (edit config.json to clear current_versions and rerun script).



Maintenance

Monitor GitHub Actions: Check the Actions tab for run logs. Add notifications (e.g., email via dawidd6/action-send-mail) for failures.
Update Script: If Plex's download page changes (e.g., new HTML structure), modify fetch_latest_plex_versions() in plex_auto_update.py.
Add Architectures: Update config.json and repo.xml for new QNAP platforms (e.g., TS-X41).

Legal and Compliance

This repository mirrors official Plex QPKGs from https://www.plex.tv. Ensure compliance with Plex's terms of service regarding redistribution.
No modifications are made to QPKGs; they are downloaded as-is.
For custom Plex builds, use QNAP's QDK (QPKG Development Kit) and adhere to licensing.

Troubleshooting

App Center Doesn't Show Plex: Verify repo.xml URL is accessible (HTTPS) and XML is valid (use an online XML validator).
Download Failures: Check Action logs for HTTP errors. Plex may have changed their download page; update plex_auto_update.py.
Plex Fails to Start: Check /share/PlexData/Logs on your NAS. Ensure port 32400 is open and NAS hardware supports transcoding (if needed).

Contributing

Fork the repo, make changes, and submit a pull request.
For new features (e.g., additional apps, architectures), update config.json and test thoroughly.
Report issues via GitHub Issues.

License
This project is licensed under the MIT License. See LICENSE for details. Note: Plex Media Server QPKGs are subject to Plex's licensing terms.
Resources

Plex Downloads
QNAP QPKG Development Guidelines
Plex Forums
