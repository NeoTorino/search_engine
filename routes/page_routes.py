import time
from flask import Blueprint, render_template

pages = Blueprint('pages', __name__)

@pages.route("/about")
def about():
    return render_template("about.html", time=time)

@pages.route("/organizations")
def organizations():
    return render_template("organizations.html", time=time)

@pages.route("/sources")
def sources():
    return render_template("sources.html", time=time)

@pages.route("/stats")
def stats():
    return render_template("stats.html", time=time)