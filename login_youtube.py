"""Helper script to trigger interactive OAuth authentication for YouTube Studio & Upload."""

import os
import sys

# Add src to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from youtube_analyzer.connectors.youtube_studio import YouTubeStudioConnector

def main():
    print("=" * 60, flush=True)
    print("MEMULAI OTORISASI YOUTUBE STUDIO & UPLOAD", flush=True)
    print("Akun Google: led.dhany@gmail.com", flush=True)
    print("Scopes:", flush=True)
    print("  - https://www.googleapis.com/auth/youtube.readonly", flush=True)
    print("  - https://www.googleapis.com/auth/yt-analytics.readonly", flush=True)
    print("  - https://www.googleapis.com/auth/youtube.upload", flush=True)
    print("=" * 60, flush=True)
    
    token_path = os.path.join(current_dir, ".youtube_token.json")
    secrets_path = os.path.join(current_dir, "client_secret.json")
    
    print(f"\nSecrets file: {secrets_path}", flush=True)
    print(f"Token destination: {token_path}", flush=True)
    print("\nBrowser akan terbuka secara otomatis. Silakan pilih akun led.dhany@gmail.com dan klik 'Lanjutkan / Allow'...\n", flush=True)
    
    connector = YouTubeStudioConnector(token_path=token_path)
    success, message = connector.authenticate_interactive(client_secrets_file=secrets_path)
    
    print("\n" + "=" * 60, flush=True)
    if success:
        print("[SUKSES]", message, flush=True)
        profile = connector.get_channel_profile()
        if profile:
            print(f"Channel Terhubung: {profile.get('title')} (Subscribers: {profile.get('subscribers_display')})", flush=True)
    else:
        print("[GAGAL]", message, flush=True)
    print("=" * 60, flush=True)

if __name__ == "__main__":
    main()
