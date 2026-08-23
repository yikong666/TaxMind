"""上传文档的扩展名、魔数和容器结构校验。"""

import io
import zipfile

from backend.core.exceptions import BusinessError

TEXT_EXTENSIONS = {".md", ".txt", ".html", ".htm"}
IMAGE_SIGNATURES = {
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".webp": (b"RIFF",),
}


def validate_file_content(extension: str, content: bytes) -> str:
    """验证文件真实格式并返回可信 MIME，拒绝伪装和异常 Office 容器。"""
    if extension in TEXT_EXTENSIONS:
        if b"\x00" in content:
            raise _invalid()
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise _invalid() from exc
        return "text/html" if extension in {".html", ".htm"} else "text/plain"
    if extension == ".pdf" and content.startswith(b"%PDF-"):
        return "application/pdf"
    if extension in {".doc", ".ppt"} and content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        return "application/msword" if extension == ".doc" else "application/vnd.ms-powerpoint"
    if extension in {".docx", ".pptx"}:
        return _validate_office_container(extension, content)
    signatures = IMAGE_SIGNATURES.get(extension, ())
    if signatures and any(content.startswith(signature) for signature in signatures):
        if extension == ".webp" and content[8:12] != b"WEBP":
            raise _invalid()
        return "image/jpeg" if extension in {".jpg", ".jpeg"} else f"image/{extension[1:]}"
    raise _invalid()


def _validate_office_container(extension: str, content: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            entries = archive.infolist()
            # 限制压缩炸弹：文件数、展开总量和极端压缩比均必须受控。
            total_size = sum(item.file_size for item in entries)
            compressed = max(sum(item.compress_size for item in entries), 1)
            unsafe_archive = (
                len(entries) > 5000
                or total_size > 200 * 1024 * 1024
                or total_size / compressed > 100
            )
            if unsafe_archive:
                raise _invalid()
            names = {item.filename for item in entries}
    except (zipfile.BadZipFile, ValueError) as exc:
        raise _invalid() from exc
    required_prefix = "word/" if extension == ".docx" else "ppt/"
    has_required_content = any(name.startswith(required_prefix) for name in names)
    if "[Content_Types].xml" not in names or not has_required_content:
        raise _invalid()
    if extension == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _invalid() -> BusinessError:
    return BusinessError("文件内容与声明格式不一致", "INVALID_FILE_CONTENT")
