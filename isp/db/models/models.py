# just for test implementation

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship

from isp.db import db
from isp.db.models import RelationShip
from isp.db.models.base_model import BaseModel


class FirstPolarityModel(db.Model, BaseModel):
    __tablename__ = 'first_polarity'

    id = Column(String(16), primary_key=True)
    event_info_id = Column(String(16), ForeignKey("event_locations.id"), nullable=False, unique=True)
    strike_fp = Column(Float, nullable=True)
    dip_fp = Column(Float, nullable=True)
    rake_fp = Column(Float, nullable=True)
    misfit_fp = Column(Float, nullable=True)
    azimuthal_fp_Gap = Column(Float, nullable=True)
    station_fp_polarities_count = Column(Integer, nullable=True)

    def __repr__(self):
        return "FirstPolarityModel({})".format(self.to_dict())


class MomentTensorModel(db.Model, BaseModel):
    __tablename__ = 'moment_tensor'

    id = Column(String(16), primary_key=True)
    event_info_id = Column(String(16), ForeignKey("event_locations.id"), nullable=False, unique=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    depth = Column(Float, nullable=False)
    mw_mt = Column(Float, nullable=True)
    mo = Column(Float, nullable=True)
    strike_mt = Column(Float, nullable=True)
    dip_mt = Column(Float, nullable=True)
    rake_mt = Column(Float, nullable=True)
    mrr = Column(Float, nullable=True)
    moo = Column(Float, nullable=True)
    mff = Column(Float, nullable=True)
    mro = Column(Float, nullable=True)
    mrf = Column(Float, nullable=True)
    mof = Column(Float, nullable=True)
    dc = Column(Float, nullable=True)
    clvd = Column(Float, nullable=True)

    def __repr__(self):
        return "MomentTensorModel({})".format(self.to_dict())


class PhaseInfoModel(db.Model, BaseModel):
    __tablename__ = 'phase_info'

    id = Column(String(16), primary_key=True)
    event_info_id = Column(String(16), ForeignKey("event_locations.id"), nullable=False, unique=True)
    station_code = Column(String(5), nullable=False)
    channel = Column(String(5), nullable=False)
    phase = Column(String(1), nullable=False)
    polarity = Column(String(1), nullable=False)
    time = Column(DateTime, nullable=False)
    amplitude = Column(Float, nullable=False)
    travel_time = Column(Float, nullable=False)
    rms = Column(Float, nullable=False)
    residual = Column(Float, nullable=False)
    weight = Column(Float, nullable=False)
    s_dist = Column(Float, nullable=False)
    s_az = Column(Float, nullable=False)
    r_az = Column(Float, nullable=False)
    r_dip = Column(Float, nullable=False)

    def __repr__(self):
        return "PhaseInfoModel({})".format(self.to_dict())


class EventArrayModel(db.Model, BaseModel):

    # The name of the table at the data base.
    __tablename__ = "event_array"

    # The table columns.
    event_info_id = Column(String(16), ForeignKey("event_locations.id"), primary_key=True)
    array_analysis_id = Column(String(16), ForeignKey("array_analysis.id"), primary_key=True, unique=True)

    def __repr__(self):
        return "EventArrayModel(event_info_id={}, array_analysis_id={})".format(self.event_info_id,
                                                                                self.array_analysis_id)


class EventLocationModel(db.Model, BaseModel):
    __tablename__ = 'event_locations'

    id = Column(String(16), primary_key=True)
    origin_time = Column(DateTime, nullable=False)
    transformation = Column(String(10),  nullable=False)
    rms = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    depth = Column(Float, nullable=False)
    uncertainty = Column(Float, nullable=False)
    max_horizontal_error = Column(Float, nullable=False)
    min_horizontal_error = Column(Float, nullable=False)
    ellipse_azimuth = Column(Float, nullable=False)
    number_of_phases = Column(Integer, nullable=False)
    azimuthal_gap = Column(Integer, nullable=False)
    max_distance = Column(Float, nullable=False)
    min_distance = Column(Float, nullable=False)
    mb = Column(Float, nullable=True)
    mb_error = Column(Float, nullable=True)
    ms = Column(Float, nullable=True)
    ms_error = Column(Float, nullable=True)
    ml = Column(Float, nullable=True)
    ml_error = Column(Float, nullable=True)
    mw = Column(Float, nullable=True)
    mw_error = Column(Float, nullable=True)
    first_polarity = relationship(RelationShip.FIRST_POLARITY, backref="event_location",
                                  cascade="save-update, merge, delete", lazy=True)
    moment_tensor = relationship(RelationShip.MOMENT_TENSOR, backref="event_location",
                                 cascade="save-update, merge, delete", lazy=True)
    phase_info = relationship(RelationShip.PHASE_INFO, backref="event_location",
                              cascade="save-update, merge, delete", lazy=True)
    event_arrays = relationship(RelationShip.EVENT_ARRAY, backref="event_location",
                                cascade="save-update, merge, delete", lazy=True)

    def __repr__(self):
        return "EventLocationModel(id={}, origin_time={}, latitude={}, longitude={})".\
            format(self.id, self.origin_time, self.latitude, self.longitude)

    @property
    def get_arrays(self):
        """ Get a list of ArrayAnalysisModel for this event_location."""
        return [ArrayAnalysisModel.find_by_id(event_array.array_analysis_id)
                for event_array in self.event_arrays if event_array]

    def add_array(self, array_analysis_id: str):
        """
        Link an ArrayAnalysisModel to this event_location.

        Important: This will not be added to the database until this entity is saved.

        :param array_analysis_id: The current id of the array_analysis.
        """

        event_arrays = EventArrayModel(event_info_id=self.id, array_analysis_id=array_analysis_id)
        self.event_arrays.append(event_arrays)


class ArrayAnalysisModel(db.Model, BaseModel):
    __tablename__ = 'array_analysis'

    id = Column(String(16), primary_key=True)
    latitude_ref = Column(Float, nullable=False)
    longitude_ref = Column(Float, nullable=False)
    slowness = Column(Float, nullable=True)
    slowness_err = Column(Float, nullable=True)
    back_azimuth = Column(Float, nullable=True)
    back_azimuth_err = Column(Float, nullable=True)
    rel_power = Column(Float, nullable=True)
    event_array = relationship(RelationShip.EVENT_ARRAY, backref="array_analysis",
                               cascade="save-update, merge, delete", lazy=True)

    def __repr__(self):
        return "ArrayAnalysisModel({})".format(self.to_dict())

    @property
    def get_event_location(self):
        """ Get a list of ArrayAnalysisModel for this event_location."""
        return ArrayAnalysisModel.find_by_id(self.event_array.array_analysis_id)
