import json
import os
import hashlib
import requests
from bs4 import BeautifulSoup
import semver  # For semantic version comparison
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom  # For pretty XML
import subprocess  # For git commits

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Constants
QPKGS_DIR = 'qpkgs'
REPO_XML = 'repo.xml'
PLEX_URL = config['plex_downloads_url']
ARCH_MAP = config['architectures']  # QNAP platformID: Plex arch suffix

def fetch_latest_plex_versions():
    """Scrape Plex downloads page for QNAP QPKG links and versions."""
    try:
        response = requests.get(PLEX_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        
        # Plex page structure: Find QNAP section (as of 2025, under platform dropdown; inspect for classes)
        # Assumption: Links are in <a> tags with href containing 'qpkg' and version in text/URL
        qpkg_links = {}
        for a in soup.find_all('a', href=True):
            href = a['href']
            if 'qpkg' in href.lower() and 'plex' in href.lower():
                # Extract version from URL, e.g., /1.40.5.8830-3f3f1a1/
                parts = href.split('/')
                version = next((p for p in parts if '-' in p and '.' in p), None)
                if version:
                    # Extract arch from URL, e.g., x86_64
                    arch = next((arch Plex for arch_plex, arch_qnap in ARCH_MAP.items() if arch_plex in href), None)
                    if arch:
                        qpkg_links.setdefault(version, {})[arch] = href
        return qpkg_links  # e.g., {'1.40.5.8830': {'x86_64': 'url', 'arm_64': 'url'}}
    except Exception as e:
        print(f"Error scraping Plex page: {e}")
        return {}

def download_qpkg(url, version, arch):
    """Download QPKG if not exists."""
    filename = f"PlexMediaServer_{version}_{arch}.qpkg"
    path = os.path.join(QPKGS_DIR, filename)
    if not os.path.exists(path):
        os.makedirs(QPKGS_DIR, exist_ok=True)
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            with open(path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded: {filename}")
            return path
        except Exception as e:
            print(f"Download failed for {url}: {e}")
            return None
    print(f"Already exists: {filename}")
    return path

def compute_md5(file_path):
    """Compute MD5 hash for QPKG."""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def update_repo_xml(new_versions):
    """Update or create repo.xml with new Plex entries."""
    # Load existing XML or create new
    if os.path.exists(REPO_XML):
        tree = ET.parse(REPO_XML)
        channel = tree.getroot().find('channel')
    else:
        root = ET.Element('rss', version="2.0", xmlns_atom="http://www.w3.org/2005/Atom")
        channel = ET.SubElement(root, 'channel')
        ET.SubElement(channel, 'title').text = config['repo_title']
        ET.SubElement(channel, 'link').text = config['repo_link']
        ET.SubElement(channel, 'description').text = config['repo_description']
        tree = ET.ElementTree(root)
    
    # Add new items for each version
    for version, arch_data in new_versions.items():
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'name').text = "Plex Media Server"
        ET.SubElement(item, 'internalName').text = "PlexMediaServer"
        ET.SubElement(item, 'changeLog').text = "https://plex.tv/changelog"  # Placeholder
        ET.SubElement(item, 'category').text = "Multimedia"
        ET.SubElement(item, 'type').text = "Entertainment"
        ET.SubElement(item, 'icon80').text = "https://your-domain.com/icons/plex-80x80.png"
        ET.SubElement(item, 'icon100').text = "https://your-domain.com/icons/plex-100x100.png"
        ET.SubElement(item, 'description').text = "<![CDATA[Plex organizes your media and streams it to any device.]]>"
        ET.SubElement(item, 'fwVersion').text = "5.0.0"
        ET.SubElement(item, 'version').text = version
        ET.SubElement(item, 'publishedDate').text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ET.SubElement(item, 'maintainer').text = "<![CDATA[Your Name]]>"
        ET.SubElement(item, 'developer').text = "<![CDATA[Plex, Inc. (auto-mirrored)]]>"
        ET.SubElement(item, 'forumlink').text = "<![CDATA[https://forums.plex.tv]]>"
        ET.SubElement(item, 'language').text = "<![CDATA[English]]>"
        ET.SubElement(item, 'snapshot').text = "<![CDATA[https://your-domain.com/screenshots/plex-ui.jpg]]>"
        ET.SubElement(item, 'bannerImg').text = "<![CDATA[]]>"
        ET.SubElement(item, 'tutorialLink').text = "<![CDATA[https://your-domain.com/tutorial]]>"
        
        for platform_id, arch in ARCH_MAP.items():
            if arch in arch_data:
                qpkg_path = arch_data[arch]['path']
                location = f"https://yourusername.github.io/plex-qnap-repo/qpkgs/PlexMediaServer_{version}_{arch}.qpkg"  # Adjust to your Pages URL
                signature = arch_data[arch]['md5']
                plat = ET.SubElement(item, 'platform')
                ET.SubElement(plat, 'platformID').text = platform_id
                ET.SubElement(plat, 'location').text = location
                ET.SubElement(plat, 'signature').text = signature
    
    # Pretty-print and save XML
    xml_str = minidom.parseString(ET.tostring(tree.getroot())).toprettyxml(indent="  ")
    with open(REPO_XML, 'w') as f:
        f.write(xml_str)
    print("Updated repo.xml")

def commit_to_git():
    """Commit changes to Git and push."""
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', 'Auto-update Plex QPKGs'], check=True)
        subprocess.run(['git', 'push'], check=True)
        print("Committed and pushed to GitHub")
    except subprocess.CalledProcessError as e:
        print(f"Git commit failed: {e}")

def main():
    # Fetch latest from Plex
    latest_versions = fetch_latest_plex_versions()
    if not latest_versions:
        print("No new versions found or scraping failed.")
        return
    
    # Load current versions from config
    current_versions = config.get('current_versions', {})
    
    new_versions = {}
    for version, links in latest_versions.items():
        # Compare versions (assume Plex versions are semver-compatible)
        if version not in current_versions or semver.compare(version, max(current_versions.keys())) > 0:
            new_versions[version] = {}
            for arch, url in links.items():
                path = download_qpkg(url, version, arch)
                if path:
                    md5 = compute_md5(path)
                    new_versions[version][arch] = {'path': path, 'md5': md5}
                    # Update config
                    current_versions.setdefault(version, []).append(ARCH_MAP[arch])  # Wait, invert for save
    
    if new_versions:
        update_repo_xml(new_versions)
        # Save updated config
        config['current_versions'] = {v: list(set(archs)) for v, archs in current_versions.items()}  # Dedup
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        commit_to_git()
    else:
        print("No updates needed.")

if __name__ == "__main__":
    main()
