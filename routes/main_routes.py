import time
from flask import Blueprint, render_template

from services.search_service import get_landing_stats

main_bp = Blueprint('main', __name__)

@main_bp.route("/", methods=["GET"])
def index():
    total_jobs, total_orgs = get_landing_stats()
    return render_template('landing.html',
                            total_jobs=total_jobs,
                            total_orgs=total_orgs,
                            time=time)


@main_bp.route("/about")
def about():
    return render_template("about.html", time=time)
