"""Decode bounded synthetic financial JPEGs with an explicitly matched runtime."""
from io import BytesIO


PROFILE = "SYNTHETIC-D161-jpeg-financial-evidence"


def jpeg_runtime():
    try:
        from PIL import __version__, features
    except ImportError:
        return None
    version = features.version_feature("libjpeg_turbo")
    if not features.check_codec("jpg") or not version:
        return None
    return dict(pillow_version=__version__, libjpeg_turbo_version=version)


def decode_jpeg(raw, width, height, color_space):
    from PIL import Image, ImageFile

    if ImageFile.LOAD_TRUNCATED_IMAGES or not raw.startswith(b"\xff\xd8") or not raw.endswith(b"\xff\xd9"):
        return None
    expected_mode = "L" if color_space == "/DeviceGray" else "RGB"
    try:
        with Image.open(BytesIO(raw), formats=("JPEG",)) as image:
            if (image.mode != expected_mode or image.size != (width, height)
                    or not image.info.get("jfif") or image.info.get("progressive")
                    or any(key in image.info for key in ("icc_profile", "exif", "adobe"))):
                return None
            return image.tobytes()
    except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        return None
