import uvicorn

from app.core.config import api


def main() -> None:
    uvicorn.run("app.main:app", host=api.host, port=api.port, reload=True)


def start() -> None:
    uvicorn.run("app.main:app", host=api.host, port=api.port)


if __name__ == "__main__":
    main()
