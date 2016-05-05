from catalogapi import *

def main():
    catalog = Catalog()
    catalog.getDepartments()
    # print getTailNum("uclacatalog2015-16-10.htm")
    # print getTailNum("uclacatalog2015-16-16.htm")
    # print decrementTailNum("uclacatalog2015-16-10.htm")
    # print decrementTailNum("uclacatalog2015-16-16.htm")
    # print getCoursesUrls("uclacatalog2015-16-154.htm")
    # print getCoursesUrls("uclacatalog2015-16-16.htm")
    # catalog.getDescriptions("uclacatalog2015-16-775.htm", "World Arts and Cultures Courses")
    # catalog.getDescriptions("uclacatalog2015-16-294.htm", "")
    # catalog.getCourseLists("uclacatalog2015-16-294.htm", "")
    # getCourseUrl("uclacatalog2015-16-776.htm")
    catalog.getAllDescriptions()
if __name__ == "__main__":
    main()