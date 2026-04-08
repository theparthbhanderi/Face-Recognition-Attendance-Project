from app import app
import os
from config import ProductionConfig

def create_app():
    """Application factory"""
    app.config.from_object(ProductionConfig)
    return app

application = create_app()

if __name__ == "__main__":
    application.run()
