import time
from flask import Blueprint, render_template

pages = Blueprint('pages', __name__)

@pages.route("/about")
def about():
    return render_template("about.html", time=time)

