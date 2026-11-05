"""Test to guarantee src/youtube_analyzer and api/youtube_analyzer are 100% byte-for-byte identical.

This prevents the critical blindspot where changes made in src/ are not deployed to Vercel (or vice-versa).
"""

from pathlib import Path


def test_src_and_api_packages_are_in_sync():
    repo_root = Path(__file__).resolve().parent.parent.parent
    src_dir = repo_root / "src" / "youtube_analyzer"
    api_dir = repo_root / "api" / "youtube_analyzer"

    assert src_dir.exists(), f"Source package dir does not exist: {src_dir}"
    assert api_dir.exists(), f"Vercel bundle dir does not exist: {api_dir}"

    src_files = {p.relative_to(src_dir): p for p in src_dir.rglob("*.py")}
    api_files = {p.relative_to(api_dir): p for p in api_dir.rglob("*.py")}

    assert set(src_files.keys()) == set(api_files.keys()), (
        f"File list mismatch between src and api: {set(src_files.keys()) ^ set(api_files.keys())}"
    )

    for rel_path, src_path in src_files.items():
        api_path = api_files[rel_path]
        src_content = src_path.read_text(encoding="utf-8")
        api_content = api_path.read_text(encoding="utf-8")
        assert src_content == api_content, (
            f"Content mismatch between {src_path} and {api_path}. Run sync to keep them identical!"
        )
