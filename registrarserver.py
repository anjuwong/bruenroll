from registrarapi import *
import flask
app = flask.Flask(__name__)

START_YEAR = 2016
CUR_YEAR = datetime.date.today().year
DB = Registrar()


@app.route('/')
def home():
    return flask.render_template("/main.html")


@app.route('/_get_departments')
def hidden_getDepts():
    return DB.getDepartmentsJSON()


@app.route('/_get_courses')
def hidden_getCourses():
    term = flask.request.args.get("term","", type=str)
    year = flask.request.args.get("year",START_YEAR, type=int)
    dept = flask.request.args.get("dept","", type=str)
    return DB.queryCoursesJSON(term, year, dept)



if __name__ == "__main__":
    app.run(debug=True)
