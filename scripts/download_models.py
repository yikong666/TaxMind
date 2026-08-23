"""下载 TaxMind 离线模型；模型文件位于 data/models，不提交 Git。"""
from pathlib import Path

from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    target = PROJECT_ROOT / "data" / "models" / "bge-m3"
    snapshot_download(
        repo_id="BAAI/bge-m3",
        local_dir=target,
        ignore_patterns=["*.msgpack", "*.h5", "onnx/*"],
    )
    print(f"BGE-M3 下载完成：{target}")


if __name__ == "__main__":
    main()

