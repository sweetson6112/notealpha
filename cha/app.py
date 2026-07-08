import os
from flask import Flask, render_template
from config import config_map
from extensions import db, login_manager, csrf, migrate


def create_app(config_name=None):
    config_name = config_name or os.environ.get("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map["default"]))

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["EXPORT_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    from models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Blueprints
    from routes.auth import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.shipments import bp as shipments_bp
    from routes.invoices import bp as invoices_bp
    from routes.approval_note import bp as approval_note_bp
    from routes.admin import bp as admin_bp
    from routes.reports import bp as reports_bp
    from routes.api import bp as api_bp
    from routes.statutory_documents import bp as statutory_docs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(shipments_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(approval_note_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(statutory_docs_bp)

    # API blueprint is stateless JSON - exempt from CSRF (still requires login session)
    csrf.exempt(api_bp)

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {"company_name": app.config["COMPANY_NAME"], "now": datetime.utcnow()}

    @app.template_filter("inr")
    def inr_filter(value):
        from services.approval_note_generator import inr
        return inr(value)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=app.config.get("DEBUG", False))
