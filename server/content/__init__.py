from flask import Blueprint

from .feed import feed_bp
from .posts import posts_bp
from .comments import comments_bp
from .replies import replies_bp

content_bp = Blueprint("content", __name__, url_prefix="/api")

content_bp.register_blueprint(feed_bp)
content_bp.register_blueprint(posts_bp)
content_bp.register_blueprint(comments_bp)
content_bp.register_blueprint(replies_bp)

__all__ = ["content_bp"]
