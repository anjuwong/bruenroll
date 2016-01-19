from registrarapi import *

def main():
    # registrarapi.getDepartments()
    # print registrarapi.encodeTerm('S')
    r = Registrar()
    # r.clearCourseCollection()
    r.updateCourses(getCurrentActiveTerms(), 2016, 'COM SCI')
    # print r.queryCoursesJSON("W", 2016, "COM SCI")
    return

if __name__ == "__main__":
    main()