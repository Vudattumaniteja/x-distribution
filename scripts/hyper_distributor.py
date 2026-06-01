import os
import glob

def get_file_list(subdir):
    path = os.path.join("tmp_hyper", subdir, "*.json")
    if subdir == "transcripts":
        path = os.path.join("tmp_hyper", subdir, "*.txt")
    return sorted(glob.glob(path))

def distribute(files, n):
    if not files: return [[] for _ in range(n)]
    k, m = divmod(len(files), n)
    return [files[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]

def main():
    # X Pipeline
    x_files = get_file_list("x_radar_standalone")
    x_dist = distribute(x_files, 2)
    for i, batch in enumerate(x_dist):
        print(f"X Agent {i+1}: {len(batch)} files")
        with open(f"tmp_hyper/x_agent_{i+1}_queue.txt", 'w') as f:
            f.write('\n'.join(batch))

    # Corp Pipeline (Sitemaps + Announcements)
    corp_files = get_file_list("corporate_announcements") + get_file_list("sitemap_history")
    corp_dist = distribute(corp_files, 2)
    for i, batch in enumerate(corp_dist):
        print(f"Corp Agent {i+1}: {len(batch)} files")
        with open(f"tmp_hyper/corp_agent_{i+1}_queue.txt", 'w') as f:
            f.write('\n'.join(batch))

    # Reddit Pipeline
    reddit_files = get_file_list("reddit_raw_standalone")
    reddit_dist = distribute(reddit_files, 3)
    for i, batch in enumerate(reddit_dist):
        print(f"Reddit Agent {i+1}: {len(batch)} files")
        with open(f"tmp_hyper/reddit_agent_{i+1}_queue.txt", 'w') as f:
            f.write('\n'.join(batch))

    # YouTube Pipeline
    yt_files = get_file_list("transcripts")
    yt_dist = distribute(yt_files, 4)
    for i, batch in enumerate(yt_dist):
        print(f"YT Agent {i+1}: {len(batch)} files")
        with open(f"tmp_hyper/yt_agent_{i+1}_queue.txt", 'w') as f:
            f.write('\n'.join(batch))

if __name__ == "__main__":
    main()
