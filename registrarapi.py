from bs4 import BeautifulSoup
from collections import defaultdict
from re import findall
import requests
import datetime
import pymongo
import json
from bson.json_util import dumps
import mongoRegistrarDB

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
            self.db = mongoRegistrarDB.MongoRegistrarDB()
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
        Put it into the database
        :param term: member of (summer, fall, winter, spring)
        :param year: two-digit year, assumed 20XX
        :param dept: dept (must exist in deptList from getDepartments)
        :return:
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

        if len(courses) == 0:
            return

        assert(len(courses) == len(profs))

        dgdClasses = ['dgdClassDataSectionNumber',
                      'dgdClassDataDays',
                      'dgdClassDataTimeStart',
                      'dgdClassDataTimeEnd',
                      'dgdClassDataEnrollTotal',
                      'dgdClassDataEnrollCap']
        tdTags = soup.find_all('td', {'class': dgdClasses})
        allTimeStarts = []
        allTimeEnds = []
        allDays = []
        allEnrolls = []
        allCaps = []

        encodeTag = {}
        encodeTag['dgdClassDataSectionNumber'] = 1
        encodeTag['dgdClassDataDays'] = 2
        encodeTag['dgdClassDataTimeStart'] = 3
        encodeTag['dgdClassDataTimeEnd'] = 4
        encodeTag['dgdClassDataEnrollTotal'] = 5
        encodeTag['dgdClassDataEnrollCap'] = 6
        prevEncoding = 0
        stage = {}
        stage['dgdClassDataDays'] = ''
        stage['dgdClassDataTimeStart'] = ''
        stage['dgdClassDataTimeEnd'] = ''
        stage['dgdClassDataEnrollTotal'] = ''
        stage['dgdClassDataEnrollCap'] = ''
        expectedSum = 21
        stagingSum = 0
        for td in tdTags:
            # get all bolded spans within a td tag
            bolded = td.find('span', 'bold')
            if td.find('span', 'bold') is not None:
                tagClass = td["class"][0]
                if prevEncoding > encodeTag[tagClass]:
                    # if we're at the front of a new set of dgdClass tags
                    if stagingSum == expectedSum:
                        # good: add everything to each list
                        allDays.append(stage['dgdClassDataDays'])
                        allTimeStarts.append(stage['dgdClassDataTimeStart'])
                        allTimeEnds.append(stage['dgdClassDataTimeEnd'])
                        allEnrolls.append(stage['dgdClassDataEnrollTotal'])
                        allCaps.append(stage['dgdClassDataEnrollCap'])
                        stagingSum = 0
                    else:
                        stagingSum = 0
                # ignore tags with missing section number
                if tagClass == 'dgdClassDataSectionNumber' and bolded.string is None:
                    continue
                stagingSum += encodeTag[tagClass]
                prevEncoding = encodeTag[tagClass]
                stage[tagClass] = bolded.string

        if stagingSum == expectedSum:
            # Finish off the end
            allDays.append(stage['dgdClassDataDays'])
            allTimeStarts.append(stage['dgdClassDataTimeStart'])
            allTimeEnds.append(stage['dgdClassDataTimeEnd'])
            allEnrolls.append(stage['dgdClassDataEnrollTotal'])
            allCaps.append(stage['dgdClassDataEnrollCap'])
        # Some classes may have an added bold section after to fit in a mandatory discussion section
        # They do not have a specific enrollment count
        #   Ignore them
        allTimeStarts = [allTimeStarts[i] for i in range(len(allEnrolls)) if allDays[i] is not ""]
        allTimeEnds = [allTimeEnds[i] for i in range(len(allEnrolls)) if allDays[i] is not ""]
        allDays = [allDays[i] for i in range(len(allEnrolls)) if allDays[i] is not ""]
        allEnrolls = [allEnrolls[i] for i in range(len(allEnrolls)) if allDays[i] is not ""]
        allCaps = [allCaps[i] for i in range(len(allEnrolls)) if allDays[i] is not ""]

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

            courseCursor = self.db.queryCourse(
                    encodeTerm(term, year),
                    dept,
                    courses[i],
                    profs[i],
                    allTimeStarts[i],
                    allDays[i])

            for crs in courseCursor:
                if crs["enrolls"][-1] == en:
                    # increment enrollsdaycount
                    # pop and push (current pymongo does not allow for updating single element of array)
                    print crs["title"] + ": increased daycount to " + str(crs["enrollsdaycount"][-1]+1) + " with " + crs["prof"]
                    self.db.incrementEnrollment(crs)
                else:
                    # new enrollment count; push new enrollment and enrollsdaycount
                    print crs["title"] + ": new daycount added [" + str(crs["enrolls"]) + ", " + str(en) + "] with " + crs["prof"]
                    self.db.addNewEnrollment(crs, en)

            if courseCursor.count() == 0:
                print courses[i] + " new entry added with " + profs[i]
                self.db.addNewCourse(
                        encodeTerm(term, year),
                        dept,
                        courses[i],
                        profs[i],
                        allTimeStarts[i],
                        allTimeEnds[i],
                        allDays[i],
                        en,
                        cap)
        return

    def updateAll(self, term, year):
        depts = self.getDepartments()
        for dept in depts:
            self.updateCourses(term, year, dept)
        return

    def getDepartmentsJSON(self):
        return json.dumps(self.deptList)

    def queryCoursesJSON(self, term, year, dept):
        cursor = self.db.queryTerm(encodeTerm(term, year), dept)
        return dumps(cursor)

    def clearCourseCollection(self):
        self.db.emptyDB()

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
    """
    Returns whether title belongs to a research-based class
    :param title: string containing the full course name, number, section
    :return: false if the class is a research class (courseno. _9X), else true
    """
    numbers = [int(num) for num in findall("\d+", title)]
    if max(numbers) > 289 or max(numbers) % 100 > 90:
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
    """
    Terms are encoded as XXY
    XX: the year in 20XX
    Y: {1,2,3,4} based on the season
    :param term: season, given as a single char
    :param year: given as either 20XX or just XX
    :return: encoding, given as XXY
    """
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
    """
    Terms are encoded as XXY
    XX: the year in 20XX
    Y: {1,2,3,4} based on the season
    :param term: encoded XXY term
    :return: tuple containing the year (XX) and the season
    """
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
    """
    Gets the current active terms based on the date
    First checks what the current quarter is
    Second checks when enrollment passes open
    :return: list of terms with currently active enrollment numbers
    """
    m = datetime.datetime.today().month
    terms = []
    if m <= 3:     # 1 through 3
        terms.append('W')
    elif m <= 6:   # 4 through 6
        terms.append('S')
    elif m <= 8:   # 7 through 8
        terms.append('1')
    elif m <= 12:  # 9 through 12
        terms.append('F')

    # Rough estimate for when first pass starts
    if m == 2 or m == 3:
        terms.append('S')
    elif m == 7 or m == 8:
        terms.append('F')
    elif m == 10 or m == 11:
        terms.append('W')
    return terms[0]
