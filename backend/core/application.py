from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


def configure_http(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "https://ainova-consultingcr.github.io",
            "http://127.0.0.1:5500",
            "http://localhost:5500",
        ],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.options("/{full_path:path}")
    def options_handler(full_path: str):
        return JSONResponse(content={})

    return options_handler
