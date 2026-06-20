import uvicorn
from database.db import init_db
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info("Starting AI Impact Scoring Engine")
    init_db()
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
