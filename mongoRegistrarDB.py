import pymongo
import json
from django.core.serializers.json import DjangoJSONEncoder
from bson import objectid

class MongoAwareEncoder(DjangoJSONEncoder):
    """JSON encoder class that adds support for Mongo objectids."""
    def default(self, o):
        if isinstance(o, objectid.ObjectId):
            return str(o)
        else:
            return super(MongoAwareEncoder,self).default(o)

class MongoRegistrarDB:

    def __init__(self):
        client = pymongo.MongoClient("127.0.0.1:27017")
        self.db = client.uclaregistrar  # collection name is uclaregistrar
        self.db.courses.create_index([("term", pymongo.ASCENDING), ("dept", pymongo.ASCENDING)])

    def dump(self):
        """
        Print the DB as a json
        """
        for doc in self.db.courses.find():
            print json.dumps({'results':doc}, cls=MongoAwareEncoder)

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
