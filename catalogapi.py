from bs4 import BeautifulSoup
from re import findall
import requests
import datetime
import json
import string

"""
getDepartments: () => [(deptNum, department name)]
getCourses: deptNum => [[(courseId:string, review:string)]]
getAllCourses: [deptNum] => [[(courseId:string, review:string)]]
getCourseName: from something

* map the registrarapi departments to the courseId strings
* map the courseId strings to the course listings on bruinwalk
* if the class is already catalogued, we should ignore
"""
BASE_URL = "http://catalog.registrar.ucla.edu/"
CATALOG_URL = BASE_URL+"catalog-curricul.htm"

class Catalog:

    def __init__(self, savehome="./descriptions.txt"):
        self.SAVE_HOME = savehome


    def getDepartments(self):
        soup = getSoup("catalog-curricul.htm")
        tableSoup = soup.find_all("td", "cellbody")

        # <a class="main" href="uclacatalog2015-16-10.htm">African American Studies</a>
        deptSoup = [td.find("a", "main") for td in tableSoup]

        # ('uclacatalog2015-16-10.htm', u'African American Studies')
        deptList = [(dept.get("href"), dept.get_text()) for dept in deptSoup if dept is not None]

        # Filter out those that aren't .....NUM.htm, as that is the supposed format of the catalog
        deptList = [dept for dept in deptList if dept[0][-5].isdigit()]

        # Sort by the urlTails of hrefs
        deptList = sorted(deptList, key=lambda tup: getTailNum(tup[0]))
        print deptList
        self.deptList = deptList
        return deptList

    def getDescriptions(self, urlTail, deptName):
        """
        Go to the URL tail, search for COURSE link
        Parse the course bodies
        [("598. Research for and Preparation of Master&#8216;s Thesis. (2 to 8)",
           "Tutorial, to be arranged. Research for and preparation of M.A. or M.F.A. thesis. S/U grading.")]
        :param urlTail:
        :return:
        """
        soup = getSoup(urlTail)
        if soup.find("span","coursetitle") is None:
            return []

        courses = [getDescription(body, deptName) for body in soup.find_all("p", "coursebody")]

        # self.saveList(courses)
        return courses

    def getCourseLists(self, urlTail, deptName):
        """
        If the page is a list of HEAD, TITLE, TITLE, TITLE, parse differently
        find all course-list-subhead tags
        find all coursebody tags

        :param urlTail:
        :param deptName:
        :return:
        """
        soup = getSoup(urlTail)
        subheads = soup.find_all("p", "course-list-subhead")
        coursebodies = soup.find_all("p", "coursebody")
        if len(subheads) == 0:
            return []

        courses = []
        for t in zip(subheads, coursebodies):
            department = t[0].get_text().replace("\n","")

            # [u'', u'152. Ukrainian Literature', ...]
            courseList = t[1].get_text().split("\n")

            # [u'152. Ukrainian Literature', ...]
            courseList = courseList[1:]

            courses += [(department+" "+course, department+" "+course) for course in courseList]

        return courses


    def getAllDescriptions(self):
        """
        Order the deptList by urlTail value (url, dept name)
        For the Ith entry, look at the 1+1th urlTail-1
        :return:
        """
        self.wfile = open(self.SAVE_HOME, "wb")

        for dept in self.deptList:
            # self.wfile = open(self.SAVE_HOME, "wb")
            # urlTail = getCourseUrl(dept[0])
            urlTails = getCoursesUrls(dept[0])
            # print str(urlTails)+"!"
            deptName = dept[1]
            courses = []
            # For each COURSE type (e.g. Greek, Latin, Classics) get descriptions
            for urlTail_, deptName_ in urlTails:
                if deptName_ == "COURSES":
                    deptName_ = deptName
                descriptions = self.getDescriptions(urlTail_, deptName_)
                if len(descriptions) == 0:
                    descriptions = self.getCourseLists(urlTail_, deptName_)
                if len(descriptions) == 0:
                    descriptions = []

                courses += descriptions

            # courses = self.getDescriptions(urlTail, deptName)
            # print deptName+"!"

            self.saveList(courses)
            # self.wfile.close()


        # for deptNum in range(len(self.deptList)-1):
        #     urlTail = decrementTailNum(self.deptList[deptNum+1][0])
        #     deptName = self.deptList[deptNum][1]
        #     courses = self.getDescriptions(urlTail, deptName)
        #     self.saveList(courses)
        #     # [self.save(tup) for tup in courses]
        # lastUrlTail = getCourseUrl(self.deptList[-1][0])
        # lastDeptName = self.deptList[-1][1]
        # lastCourses = self.getDescriptions(lastUrlTail, lastDeptName)
        # self.saveList(lastCourses)
        self.wfile.close()
        # [self.save(tup) for tup in lastCourses]
        return



    def save(self, tuple):
        print "!@#$%"
        print tuple[0]
        print tuple[1]
        return


    def saveList(self, descriptionList):

        if len(descriptionList) == 0:
            return
        descriptions = ["!@#$%\n"+desc[0]+"\n"+desc[1]+"\n" for desc in descriptionList if len(desc) > 0]
        descriptions = "".join(descriptions)
        descriptions = removeNonAscii(descriptions)
        print descriptions
        self.wfile.write(descriptions)


    def load(self, filename):
        return

def removeNonAscii(s):
    return "".join(i for i in s if ord(i)<128)

def getSoup(urlTail):
    DEPT_URL = BASE_URL + urlTail
    req = requests.get(DEPT_URL)
    return BeautifulSoup(req.text)

def getCourseUrl(urlTail):
    soup = getSoup(urlTail)
    links = soup.find_all("dd")
    url = links[-1].find("a").get("href")
    return url

def getCoursesUrls(urlTail):
    """
    urlTail is home for department
    :param urlTail:
    :return:
    """
    soup = getSoup(urlTail)
    links = soup.find_all("dd")
    urls = [(url.find("a").get("href"), url.get_text().replace(" COURSES","")) for url in links if "COURSES" in url.get_text()]
    return urls

def getTailNum(url):
    # uclacatalog2015-16-10.htm => 10
    url = url[:-4]
    for i in range(1,len(url)):
        if not url[-i].isdigit():
            return int(url[-i+1:])

def decrementTailNum(url):
    tailNum = getTailNum(url)
    return url[:-len(str(tailNum))-4] + str(tailNum-1) + ".htm"

def getDescription(soup, deptName):
    """
    "<p class="coursebody"><span class="coursetitle">
        598. Research for and Preparation of Master&#8217;s Thesis. (2 to 8)</span>
        Tutorial, to be arranged. Research for and preparation of M.A. or M.F.A. thesis. S/U grading.</p>"
        =>("598. Research for and Preparation of Master&#8216;s Thesis. (2 to 8)",
           "Tutorial, to be arranged. Research for and preparation of M.A. or M.F.A. thesis. S/U grading.")
    :param soup:
    :return:
    """

    # Assume at the time of call, we have verified that there is a coursetitle
    courseTitle = soup.find("span","coursetitle")
    # In case of a body with no title, just move on
    if courseTitle is None:
        return []
    courseTitle = courseTitle.get_text()

    review = [s for s in soup.children if isinstance(s, basestring)]
    if len(review) == 0:
        # Check if there there's a description after the parentheses
        endParenInd = courseTitle.index(")")
        if not endParenInd == len(courseTitle)-1:
            review = [courseTitle[endParenInd+1:]]
            courseTitle = courseTitle[:endParenInd]

    if len(review) == 0:
        review = [""]
    courseTitle = courseTitle.replace("\n", "")
    review[0] = review[0].replace("\n","")
    desc = (deptName+" "+courseTitle, review[0])
    return desc