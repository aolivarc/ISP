import os
import unittest

from isp.db import db

dir_path = os.path.dirname(os.path.abspath(__file__))
db.set_db_url("sqlite:///{}/isp_test.db".format(dir_path))
db.start()

from isp.db.models import FirstPolarityModel, MomentTensorModel, EventArrayModel, PhaseInfoModel,\
    EventLocationModel, ArrayAnalysisModel


class MyTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        # create all tables into db.
        db.create_all()

    @classmethod
    def tearDownClass(cls) -> None:
        # remove db file when test is done.
        db.remove_sqlite_db()

    def test_event_location(self):
        print("run test")
        print(EventLocationModel.get_all())
        print(FirstPolarityModel.get_all())
        print(MomentTensorModel.get_all())
        print(ArrayAnalysisModel.get_all())
        print(EventArrayModel.get_all())
        print(PhaseInfoModel.get_all())



if __name__ == '__main__':
    unittest.main()
