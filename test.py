import subprocess

def download_video(url, output_path):
    # Goi truc tiep file thuc thi trong he thong
    command = [
        'yt-dlp',
        '-f', 'bestvideo+bestaudio/best',
        '--merge-output-format', 'mp4',
        url,
        '-o', output_path
    ]
    
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError:
        return False
