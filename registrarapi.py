from bs4 import BeautifulSoup
from collections import defaultdict
from re import findall
import requests
import datetime
import pymongo
import json
from bson.json_util import dumps

"""
Daily: connect to default mongoDB and update entries

Server: query the mongoDB
"""

class Registrar:

    deptList = []

    def __init__(self, db=None):
        """
        Connect to the database db or create a new one
        TODO: move the database to a different machine from the server
        TODO: store the date as another array
        :param db:
        :return:
        """
        if db is not None:
            self.db = db
        else:
            # Set up the database
            client = pymongo.MongoClient("127.0.0.1:27017")
            self.db = client.uclaregistrar  # collection name is uclaregistrar
            self.db.courses.create_index([("term", pymongo.ASCENDING), ("dept", pymongo.ASCENDING)])
        self.getDepartments()

    def getDepartments(self):
        """
        Query the registrar for a list of the departments
        Departments are listed as their registrar abbreviations in all caps
        Abbreviations are used in department's course catalog URL
        :return: list of all department abbreviations
        """
        url = 'http://www.registrar.ucla.edu/schedule/schedulehome.aspx'
        deptListId = 'ctl00_BodyContentPlaceHolder_SOCmain_lstSubjectArea'

        req = requests.get(url)
        soup = BeautifulSoup(req.text)
        classSoup = soup.find(id=deptListId)

        deptList = [option.get('value') for option in classSoup.find_all('option')]

        self.deptList = deptList
        return deptList

    def updateCourses(self, term, year, dept):
        """
        Get the course numbers for a given term for a given department
        :param term: member of (summer, fall, winter, spring)
        :param year: two-digit year, assumed 20XX
        :param dept: dept (must exist in deptList from getDepartments)
        :return: list of Course objects
        """
        assert(dept in self.deptList)
        assert(len(str(year)) == 2 or len(str(year)) == 4)
        # replace ' ' with '+' and capitalize all
        year = str(year)
        year = year[-2:]
        dept.replace(' ', '+')
        term = termSymbol(term)
        if term is None:
            return

        url = 'http://www.registrar.ucla.edu/schedule/detmain.aspx?termsel='+year+term+'&subareasel='+dept
        r = requests.get(url)
        soup = BeautifulSoup(r.text)
        courses = cleanCourses([str(c.string) for c in soup.find_all('span', 'coursehead')])
        profs = [str(fac.string[3:]) for fac in soup.find_all('span', 'fachead')]
        assert(len(courses) == len(profs))

        dgdClasses = ['dgdClassDataTimeStart',
                      'dgdClassDataTimeEnd',
                      'dgdClassDataDays',
                      'dgdClassDataEnrollTotal',
                      'dgdClassDataEnrollCap']
        tdTags = soup.find_all('td', {'class': dgdClasses})
        allTimeStarts = []
        allTimeEnds = []
        allDays = []
        allEnrolls = []
        allCaps = []

        for td in tdTags:
            # get all bolded spans within a td tag
            bolded = td.find('span', 'bold')
            if td.find('span', 'bold') is not None:
                tagClass = td["class"][0]
                if tagClass == 'dgdClassDataTimeStart':
                    allTimeStarts.append(bolded.string)
                elif tagClass == 'dgdClassDataTimeEnd':
                    allTimeEnds.append(bolded.string)
                elif tagClass == 'dgdClassDataDays':
                    allDays.append(bolded.string)
                elif tagClass == 'dgdClassDataEnrollTotal':
                    allEnrolls.append(bolded.string)
                elif tagClass == 'dgdClassDataEnrollCap':
                    allCaps.append(bolded.string)

        # Some classes may have an added bold section after to fit in a mandatory discussion section
        # They do not have a specific enrollment count
        #   Ignore them
        allTimeStarts = [allTimeStarts[i] for i in range(len(allEnrolls)) if allCaps[i] is not None]
        allTimeEnds = [allTimeEnds[i] for i in range(len(allEnrolls)) if allCaps[i] is not None]
        allDays = [allDays[i] for i in range(len(allEnrolls)) if allCaps[i] is not None]
        allEnrolls = [allEnrolls[i] for i in range(len(allEnrolls)) if allCaps[i] is not None]
        allCaps = [allCaps[i] for i in range(len(allEnrolls)) if allCaps[i] is not None]

        assert(len(allTimeStarts) == len(allTimeEnds))
        assert(len(allTimeStarts) == len(allDays))
        assert(len(allTimeStarts) == len(allEnrolls))
        assert(len(allTimeStarts) == len(allCaps))
        assert(len(allTimeStarts) == len(profs))

        for i in range(len(courses)):
            # Ignore entries that:
            #   > don't have a time (probably a research or TA class)
            #   > have empty enrollments (enrollment hasn't started yet)
            #   > 0 enrollment and 0 cap (class is probably canceled)
            if allTimeStarts[i] is None or allEnrolls[i] is None or (int(allEnrolls[i]) == 0 and int(allCaps[i]) == 0):
                continue

            if allCaps[i] is None:
                cap = 0
            else:
                cap = int(allCaps[i])
            if allEnrolls[i] is None:
                en = 0
            else:
                en = int(allEnrolls[i])

            courseCursor = self.db.courses.find(\
                    {
                        "term": encodeTerm(term, year),
                        "dept": dept,
                        "title": courses[i],
                        "prof": profs[i],
                        "timestart": allTimeStarts[i],
                        "days": allDays[i]
                    }
            )
            for crs in courseCursor:
                if crs["enrolls"][-1] == en:
                    # increment enrollsdaycount
                    # pop and push (current pymongo does not allow for updating single element of array)
                    print crs["title"] + ": increased daycount to " + str(crs["enrollsdaycount"][-1]+1) + " with " + crs["prof"]
                    self.db.courses.update_one({"_id": crs["_id"]},
                                           {"$pop": {"enrollsdaycount": 1}})
                    self.db.courses.update_one({"_id": crs["_id"]},
                                           {"$push": {"enrollsdaycount": crs["enrollsdaycount"][-1]+1}})

                else:
                    # new enrollment count; push new enrollment and enrollsdaycount
                    print crs["title"] + ": new daycount added " + str(crs["enrolls"]) + " with " + crs["prof"]
                    self.db.courses.update_one({"_id": crs["_id"]},
                                           {"$push": {"enrolls": en, "enrollsdaycount": 1}}, upsert=False)

            if courseCursor.count() == 0:
                print courses[i] + " new entry added with " + profs[i]
                self.db.courses.insert_one(\
                    {
                        "term": encodeTerm(term, year),
                        "dept": dept,
                        "title": courses[i],
                        "prof": profs[i],
                        "timestart": allTimeStarts[i],
                        "timeend": allTimeEnds[i],
                        "days": allDays[i],
                        "enrolls": [en],
                        "enrollsdaycount": [1],
                        "cap": cap,
                    }\
                )
        return

    def updateAll(self, term, year):
        depts = self.getDepartments()
        for dept in depts:
            self.updateCourses(term, year, dept)
        return

    def getDepartmentsJSON(self):
        return json.dumps(self.deptList)

    def queryCoursesJSON(self, term, year, dept):
        cursor = self.db.courses.find(
            {
                "term": encodeTerm(term, year),
                "dept": dept
            }
        )
        return dumps(cursor)

    def clearCourseCollection(self):
        self.db.courses.remove()

############################################################
#
#   HELPER FUNCTIONS
#
############################################################

def cleanCourses(courses):
    """
    Clean the coursehead values of 'LEC', 'TUT', 'SEM' and initial department label
    :param courses: ['Computer Science', 'COM SCI 31', 'LEC 1', 'LEC 2', ...]
    :return: ['COM SCI 31', 'COM SCI 31', ...]
    """
    curCourse = ""
    ret = []
    for c in courses[1:]:
        prefix = c[:4]
        if prefix == "LEC " or prefix == "SEM " or prefix == "TUT " or prefix == "LAB ":
            if c[-2:] == "80" or c[-2:] == "81":
                ret.append(curCourse + ':' + prefix)
            else:
                ret.append(curCourse)
        else:
            curCourse = c
    return ret

def isNormalClass(title):
    numbers = [int(num) for num in findall("\d+", title)]
    if max(numbers) > 289 or max(numbers) % 100 == 99:
        return False
    return True

def termSymbol(word):
    """
    Returns the letter designated for a given term
    Summer(1), Fall(F), Winter(W), Spring(S)
    :param word:
    :return:
    """
    word = word.upper()
    termDict = {
        '1'     : '1',
        'SUMMER': '1',
        'F'     : 'F',
        'FALL'  : 'F',
        'W'     : 'W',
        'WINTER': 'W',
        'S'     : 'S',
        'SPRING': 'S'
    }
    termDict = defaultdict(lambda: None, termDict)
    return termDict[word]


def encodeTerm(term, year):
    year = int(year) % 100
    termDict = {
        'W': 1,
        'S': 2,
        '1': 3,
        'F': 4
    }
    termDict = defaultdict(lambda: 0, termDict)
    return int(year)*10 + termDict[term]


def decodeTerm(term):
    year = int(term/10)
    term = term-(year*10)
    termDict = {
        1: 'W',
        2: 'S',
        3: '1',
        4: 'F'
    }
    termDict = defaultdict(lambda: None, termDict)
    return year, termDict[term]


def getCurrentActiveTerms():
    m = datetime.datetime.today().month
    terms = []
    if m <= 3:
        terms.append('W')
    elif m <= 6:
        terms.append('S')
    elif m <= 8:
        terms.append('1')
    elif m <= 12:
        terms.append('F')
    return terms[0]