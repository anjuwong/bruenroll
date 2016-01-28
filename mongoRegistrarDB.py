import pymongo

class MongoRegistrarDB:

    def __init__(self):
        client = pymongo.MongoClient("127.0.0.1:27017")
        self.db = client.uclaregistrar  # collection name is uclaregistrar
        self.db.courses.create_index([("term", pymongo.ASCENDING), ("dept", pymongo.ASCENDING)])
        return

    def queryCourse(self, encodedterm, dept, course, prof, timestart, days):
        """
        Query the DB based on term
        Stored result as an iterable of dictionaries
        """
        cursor = self.db.courses.find(\
                    {
                        "term": encodedterm,
                        "dept": dept,
                        "title": course,
                        "prof": prof,
                        "timestart": timestart,
                        "days": days
                    }
            )
        return cursor

    def queryTerm(self, encodedterm, dept):
        """
        Returns iterable list of dictionaries of all classes in a given term
        """
        return self.db.courses.find(
            {
                "term": encodedterm,
                "dept": dept
            }
        )


    def incrementEnrollment(self, entry):
        self.db.courses.update_one({"_id": entry["_id"]},
                               {"$pop": {"enrollsdaycount": 1}})
        self.db.courses.update_one({"_id": entry["_id"]},
                               {"$push": {"enrollsdaycount": entry["enrollsdaycount"][-1]+1}})

    def addNewEnrollment(self, entry, enrollment):
        self.db.courses.update_one({"_id": entry["_id"]},
                                {"$push": {"enrolls": enrollment, "enrollsdaycount": 1}}, upsert=False)

    def addNewCourse(self, encodedterm, dept, course, prof, timestart, timeend, days, enrollment, cap):
        self.db.courses.insert_one(\
            {
                "term": encodedterm,
                "dept": dept,
                "title": course,
                "prof": prof,
                "timestart": timestart,
                "timeend": timeend,
                "days": days,
                "enrolls": [enrollment],
                "enrollsdaycount": [1],
                "cap": cap,
            }
        )

    def emptyDB(self):
        self.db.courses.remove()
