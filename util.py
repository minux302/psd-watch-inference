from pathlib import Path
import logging
import logging.handlers
import io
from PIL import Image
import base64


def pil_to_base64(img: Image.Image):
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def create_logger(name: str, path: Path):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    file_handler = logging.handlers.RotatingFileHandler(
        path, encoding="utf-8", maxBytes=10 * 1024 * 1024, backupCount=4
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(file_handler)
    return logger


log_path = Path(__file__).parent / ".logs"
log_path.mkdir(exist_ok=True)
client_logger = create_logger(
    "client", log_path / "client.log"
)
