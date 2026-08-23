"""下载 TaxMind 离线模型；模型文件位于 data/models，不提交 Git。"""
from pathlib import Path

from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    # 模型文件体积较大，统一放在 Git 忽略的运行时目录中。
    models = [
        ("BAAI/bge-m3", "bge-m3"),
        ("BAAI/bge-reranker-v2-m3", "bge-reranker-v2-m3"),
    ]
    for repository, directory in models:
        target = PROJECT_ROOT / "data" / "models" / directory
        snapshot_download(
            repo_id=repository,
            local_dir=target,
            ignore_patterns=["*.msgpack", "*.h5", "onnx/*"],
        )
        print(f"模型下载完成：{target}")


if __name__ == "__main__":
    main()
