import json
import os
import requests
import semver  # For semantic version comparison
from datetime import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom  # For pretty XML
import subprocess  # For git commits
from urllib.parse import urljoin

# Load config
with open('config.json', 'r') as f:
    config = json.load(f)

# Constants
QPKGS_DIR = 'qpkgs'
REPO_XML = 'repo.xml'
PLEX_API_URL = 'https://plex.tv/api/downloads/5.json'  # Plex Media Server API
ARCH_MAP = config['architectures']  # QNAP platformID: Plex arch suffix

def fetch_latest_plex_versions():
    """Fetch Plex QPKG versions from the Plex API with detailed debug."""
    try:
        response = requests.get(PLEX_API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        print(f"Raw API response: {json.dumps(data, indent=2)}")  # Debug full response
        
        qpkg_links = {}
        # Target the QNAP section under "nas"
        qnap_data = data.get('nas', {}).get('QNAP', {})
        version = qnap_data.get('version')
        if version and semver.VersionInfo.is_valid(version.split('-')[0]):
            releases = qnap_data.get('releases', [])
            for release in releases:
                distro = release.get('distro')
                if distro == 'qnap':
                    build = release.get('build', '').lower().replace('linux-', '')  # Strip 'linux-' prefix
                    arch = next((arch_qnap for arch_plex, arch_qnap in ARCH_MAP.items() if arch_plex in build), None)
                    if arch:
                        url = release.get('url')
                        md5 = release.get('checksum')
                        if url and md5:
                            full_url = urljoin(PLEX_API_URL, url) if not url.startswith('http') else url
                            qpkg_links.setdefault(version, {})[arch] = {'url': full_url, 'md5': md5}
                            print(f"Found version: {version}, arch: {arch}, url: {full_url}, md5: {md5}")
        
        return qpkg_links if qpkg_links else {}
    except Exception as e:
        print(f"Error fetching Plex API: {e}")
        print("API failed; checking for manual QPKGs in qpkgs/ for debug:")
        qpkg_links = {}
        for filename in os.listdir(QPKGS_DIR):
            if filename.startswith('PlexMediaServer_') and filename.endswith('.qpkg'):
                parts = filename.split('_')
                if len(parts) >= 3:
                    version = parts[1]
                    arch = parts[2].replace('.qpkg', '')
                    if arch in ARCH_MAP.values():
                        path = os.path.join(QPKGS_DIR, filename)
                        qpkg_links.setdefault(version, {})[arch] = {'path': path}
                        print(f"Found manual version: {version}, arch: {arch}, path: {path}")
        return qpkg_links

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

def update_repo_xml(new_versions):
    """Update or create repo.xml with new Plex entries."""
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
    
    for version, arch_data in new_versions.items():
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'name').text = "Plex Media Server"
        ET.SubElement(item, 'internalName').text = "PlexMediaServer"
        ET.SubElement(item, 'changeLog').text = "https://plex.tv/changelog"
        ET.SubElement(item, 'category').text = "Multimedia"
        ET.SubElement(item, 'type').text = "Entertainment"
        ET.SubElement(item, 'icon80').text = "https://dogemackenzie.github.io/plex-qnap-repo/assets/plex-80x80.png"
        ET.SubElement(item, 'icon100').text = "https://dogemackenzie.github.io/plex-qnap-repo/assets/plex-100x100.png"
        ET.SubElement(item, 'description').text = "<![CDATA[Plex organizes your media and streams it to any device.]]>"
        ET.SubElement(item, 'fwVersion').text = "5.0.0"
        ET.SubElement(item, 'version').text = version
        ET.SubElement(item, 'publishedDate').text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ET.SubElement(item, 'maintainer').text = "<![CDATA[DogeMackenzie]]>"
        ET.SubElement(item, 'developer').text = "<![CDATA[Plex, Inc. (auto-mirrored)]]>"
        ET.SubElement(item, 'forumlink').text = "<![CDATA[https://forums.plex.tv]]>"
        ET.SubElement(item, 'language').text = "<![CDATA[English]]>"
        ET.SubElement(item, 'snapshot').text = "https://dogemackenzie.github.io/plex-qnap-repo/assets/plex-ui.jpg"
        ET.SubElement(item, 'bannerImg').text = "<![CDATA[]]>"
        ET.SubElement(item, 'tutorialLink').text = "<![CDATA[https://dogemackenzie.github.io/plex-qnap-repo]]>"
        
        for platform_id, arch in ARCH_MAP.items():
            if arch in arch_data:
                qpkg_path = arch_data[arch].get('path', '')
                if qpkg_path:
                    location = f"https://dogemackenzie.github.io/plex-qnap-repo/qpkgs/PlexMediaServer_{version}_{arch}.qpkg"
                    plat = ET.SubElement(item, 'platform')
                    ET.SubElement(plat, 'platformID').text = platform_id
                    ET.SubElement(plat, 'location').text = location
                    if 'md5' in arch_data[arch]:
                        ET.SubElement(plat, 'signature').text = arch_data[arch]['md5']

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
    latest_versions = fetch_latest_plex_versions()
    if not latest_versions:
        print("No new versions found or scraping failed.")
        return
    
    current_versions = config.get('current_versions', {})
    print(f"Current versions in config: {current_versions}")  # Debug current versions
    new_versions = {}
    for version, links in latest_versions.items():
        base_version = version.split('-')[0]  # Use base version for comparison
        print(f"Checking version: {base_version}, current versions: {[v.split('-')[0] for v in current_versions.keys()]}")  # Debug comparison
        if base_version not in [v.split('-')[0] for v in current_versions.keys()]:
            new_versions[version] = {}
            for arch, info in links.items():
                path = info.get('path')
                if not path:  # Download if not a manual file
                    path = download_qpkg(info['url'], version, arch)
                if path:
                    new_versions[version][arch] = {'path': path, 'md5': info.get('md5')}
                    current_versions[version] = current_versions.get(version, []) + [arch]
    
    if new_versions:
        update_repo_xml(new_versions)
        config['current_versions'] = {v: list(set(archs)) for v, archs in current_versions.items()}
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        commit_to_git()
    else:
        print("No updates needed.")

if __name__ == "__main__":
    main()