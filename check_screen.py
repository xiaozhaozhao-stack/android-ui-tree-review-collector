from __future__ import annotations

from pathlib import Path

import direct_collect as collector


ALL_TEXT_FILE = Path("output/screen_all_text.txt")
CANDIDATE_FILE = Path("output/screen_candidate_comments.txt")


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for line in lines:
            file.write(line + "\n")


def main() -> None:
    print("[check screen] start")
    device = collector.connect_device()
    nodes = collector.get_text_nodes(device)
    all_texts = []
    candidates = []

    for node in nodes:
        text = collector.clean_text(node.text)
        if not text or text in all_texts:
            continue
        all_texts.append(text)
        if collector.is_candidate_comment(text):
            candidates.append(text)

    write_lines(ALL_TEXT_FILE, all_texts)
    write_lines(CANDIDATE_FILE, candidates)

    print(f"All readable texts: {len(all_texts)}")
    print(f"Candidate comments: {len(candidates)}")
    print(f"Saved: {ALL_TEXT_FILE}")
    print(f"Saved: {CANDIDATE_FILE}")
    print()
    print("First readable texts:")
    for text in all_texts[:40]:
        print(text[:120])


if __name__ == "__main__":
    main()

