"""
This Python module wraps the calls and status responses provided
by the HTTP API exposed by PWI4. This code can be called directly
from other Python scripts, or can be adapted to other languages
as needed.
"""

try:
    # Python 3.x version
    from urllib.parse import urlencode
    from urllib.request import urlopen
    from urllib.error import HTTPError
except ImportError:
    # Python 2.7 version
    from urllib import urlencode
    from urllib2 import urlopen, HTTPError

class PWI4:
    """
    Client to the PWI4 telescope control application.
    """

    def __init__(self, host="localhost", port=8220):
        self.host = host
        self.port = port
        self.comm = PWI4HttpCommunicator(host, port)

    ### High-level methods #################################

    def status(self):
        return self.request_with_status("/status")

    def mount_connect(self):
        return self.request_with_status("/mount/connect")

    def mount_disconnect(self):
        return self.request_with_status("/mount/disconnect")

    def mount_enable(self, axisNum):
        return self.request_with_status("/mount/enable", axis=axisNum)

    def mount_disable(self, axisNum):
        return self.request_with_status("/mount/disable", axis=axisNum)

    def mount_set_slew_time_constant(self, value):
        return self.request_with_status("/mount/set_slew_time_constant", value=value)

    def mount_set_axis0_wrap_range_min(self, axis0_wrap_min_degs):
        # Added in PWI 4.0.13
        return self.request_with_status("/mount/set_axis0_wrap_range_min", degs=axis0_wrap_min_degs)

    def mount_find_home(self):
        return self.request_with_status("/mount/find_home")

    def mount_stop(self):
        return self.request_with_status("/mount/stop")

    def mount_goto_ra_dec_apparent(self, ra_hours, dec_degs):
        return self.request_with_status("/mount/goto_ra_dec_apparent", ra_hours=ra_hours, dec_degs=dec_degs)

    def mount_goto_ra_dec_j2000(self, ra_hours, dec_degs):
        return self.request_with_status("/mount/goto_ra_dec_j2000", ra_hours=ra_hours, dec_degs=dec_degs)

    def mount_goto_alt_az(self, alt_degs, az_degs):
        return self.request_with_status("/mount/goto_alt_az", alt_degs=alt_degs, az_degs=az_degs)

    def mount_goto_coord_pair(self, coord0, coord1, coord_type):
        """
        Set the mount target to a pair of coordinates in a specified coordinate system.
        coord_type: can currently be "altaz" or "raw"
        coord0: the azimuth coordinate for the "altaz" type, or the axis0 coordiate for the "raw" type
        coord1: the altitude coordinate for the "altaz" type, or the axis1 coordinate for the "raw" type
        """
        return self.request_with_status("/mount/goto_coord_pair", c0=coord0, c1=coord1, type=coord_type)

    def mount_offset(self, **kwargs):
        """
        One or more of the following offsets can be specified as a keyword argument:

        AXIS_reset: Clear all position and rate offsets for this axis. Set this to any value to issue the command.
        AXIS_stop_rate: Set any active offset rate to zero. Set this to any value to issue the command.
        AXIS_add_arcsec: Increase the current position offset by the specified amount
        AXIS_set_rate_arcsec_per_sec: Continually increase the offset at the specified rate

        As of PWI 4.0.11 Beta 7, the following options are also supported:
        AXIS_stop: Stop both the offset rate and any gradually-applied commands
        AXIS_stop_gradual_offset: Stop only the gradually-applied offset, and maintain the current rate
        AXIS_set_total_arcsec: Set the total accumulated offset at the time the command is received to the specified value. Any in-progress rates or gradual offsets will continue to be applied on top of this.
        AXIS_add_gradual_offset_arcsec: Gradually add the specified value to the total accumulated offset. Must be paired with AXIS_gradual_offset_rate or AXIS_gradual_offset_seconds to determine the timeframe over which the gradual offset is applied.
        AXIS_gradual_offset_rate: Paired with AXIS_add_gradual_offset_arcsec; Specifies the rate at which a gradual offset should be applied. For example, if an offset of 10 arcseconds is to be applied at a rate of 2 arcsec/sec, then it will take 5 seconds for the offset to be applied.
        AXIS_gradual_offset_seconds: Paired with AXIS_add_gradual_offset_arcsec; Specifies the time it should take to apply the gradual offset. For example, if an offset of 10 arcseconds is to be applied over a period of 2 seconds, then the offset will be increasing at a rate of 5 arcsec/sec.

        Where AXIS can be one of:

        ra: Offset the target Right Ascension coordinate
        dec: Offset the target Declination coordinate
        axis0: Offset the mount's primary axis position 
               (roughly Azimuth on an Alt-Az mount, or RA on In equatorial mount)
        axis1: Offset the mount's secondary axis position 
               (roughly Altitude on an Alt-Az mount, or Dec on an equatorial mount)
        path: Offset along the direction of travel for a moving target
        transverse: Offset perpendicular to the direction of travel for a moving target

        For example, to offset axis0 by -30 arcseconds and have it continually increase at 1
        arcsec/sec, and to also clear any existing offset in the transverse direction,
        you could call the method like this:

        mount_offset(axis0_add_arcsec=-30, axis0_set_rate_arcsec_per_sec=1, transverse_reset=0)

        """

        return self.request_with_status("/mount/offset", **kwargs)

    def mount_spiral_offset_new(self, x_step_arcsec, y_step_arcsec):
        # Added in PWI 4.0.11 Beta 8
        return self.request_with_status("/mount/spiral_offset/new", x_step_arcsec=x_step_arcsec, y_step_arcsec=y_step_arcsec)

    def mount_spiral_offset_next(self):
        # Added in PWI 4.0.11 Beta 8
        return self.request_with_status("/mount/spiral_offset/next")

    def mount_spiral_offset_previous(self):
        # Added in PWI 4.0.11 Beta 8
        return self.request_with_status("/mount/spiral_offset/previous")

    def mount_park(self):
        return self.request_with_status("/mount/park")

    def mount_set_park_here(self):
        return self.request_with_status("/mount/set_park_here")

    def mount_tracking_on(self):
        return self.request_with_status("/mount/tracking_on")

    def mount_tracking_off(self):
        return self.request_with_status("/mount/tracking_off")

    def mount_follow_tle(self, tle_line_1, tle_line_2, tle_line_3):
        return self.request_with_status("/mount/follow_tle", line1=tle_line_1, line2=tle_line_2, line3=tle_line_3)

    def mount_radecpath_new(self):
        return self.request_with_status("/mount/radecpath/new")

    def mount_radecpath_add_point(self, jd, ra_j2000_hours, dec_j2000_degs):
        return self.request_with_status("/mount/radecpath/add_point", jd=jd, ra_j2000_hours=ra_j2000_hours, dec_j2000_degs=dec_j2000_degs)

    def mount_radecpath_apply(self):
        return self.request_with_status("/mount/radecpath/apply")

    def mount_custom_path_new(self, coord_type):
        return self.request_with_status("/mount/custom_path/new", type=coord_type)

    def mount_custom_path_add_point_list(self, points):
        lines = []
        for (jd, ra, dec) in points:
            line = "%.10f,%s,%s" % (jd, ra, dec)
            lines.append(line)

        data = "\n".join(lines).encode('utf-8')

        postdata = urlencode({'data': data}).encode()

        return self.request("/mount/custom_path/add_point_list", postdata=postdata)

    def mount_custom_path_apply(self):
        return self.request_with_status("/mount/custom_path/apply")

    def mount_model_add_point(self, ra_j2000_hours, dec_j2000_degs):
        """
        Add a calibration point to the pointing model, mapping the current pointing direction
        of the telescope to the secified J2000 Right Ascension and Declination values.

        This call might be performed after manually centering a bright star with a known
        RA and Dec, or the RA and Dec might be provided by a PlateSolve solution
        from an image taken at the current location.
        """

        return self.request_with_status("/mount/model/add_point", ra_j2000_hours=ra_j2000_hours, dec_j2000_degs=dec_j2000_degs)

    def mount_model_delete_point(self, *point_indexes_0_based):
        """
        Remove one or more calibration points from the pointing model.

        Points are specified by index, ranging from 0 to (number_of_points-1).

        Added in PWI 4.0.11 beta 9

        Examples:  
          mount_model_delete_point(0)  # Delete the first point
          mount_model_delete_point(1, 3, 5)  # Delete the second, fourth, and sixth points
          mount_model_delete_point(*range(20)) # Delete the first 20 points
        """

        point_indexes_comma_separated = list_to_comma_separated_string(point_indexes_0_based)
        return self.request_with_status("/mount/model/delete_point", index=point_indexes_comma_separated)

    def mount_model_enable_point(self, *point_indexes_0_based):
        """
        Flag one or more calibration points as "enabled", meaning that these points
        will contribute to the fit of the model.

        Points are specified by index, ranging from 0 to (number_of_points-1).
        
        Added in PWI 4.0.11 beta 9

        Examples:  
          mount_model_enable_point(0)  # Enable the first point
          mount_model_enable_point(1, 3, 5)  # Enable the second, fourth, and sixth points
          mount_model_enable_point(*range(20)) # Enable the first 20 points
        """

        point_indexes_comma_separated = list_to_comma_separated_string(point_indexes_0_based)
        return self.request_with_status("/mount/model/enable_point", index=point_indexes_comma_separated)

    def mount_model_disable_point(self, *point_indexes_0_based):
        """
        Flag one or more calibration points as "disabled", meaning that these calibration
        points will still be stored but will not contribute to the fit of the model.
        
        If a point is suspected to be an outlier, it can be disabled. This will cause the model
        to re-fit, and the point's deviation from the newly-fit model can be re-examined before
        being deleted entirely.

        Points are specified by index, ranging from 0 to (number_of_points-1).
        
        Added in PWI 4.0.11 beta 9

        Examples:  
          mount_model_disable_point(0)  # Disable the first point
          mount_model_disable_point(1, 3, 5)  # Disable the second, fourth, and sixth points
          mount_model_disable_point(*range(20)) # Disable the first 20 points
          mount_model_disable_point(            # Disable all points
              *range(
                  pwi4.status().mount.model.num_points_total
               ))
        """

        point_indexes_comma_separated = list_to_comma_separated_string(point_indexes_0_based)
        return self.request_with_status("/mount/model/disable_point", index=point_indexes_comma_separated)

    def mount_model_clear_points(self):
        """
        Remove all calibration points from the pointing model.
        """

        return self.request_with_status("/mount/model/clear_points")

    def mount_model_save_as_default(self):
        """
        Save the active pointing model as the model that will be loaded
        by default the next time the mount is connected.
        """

        return self.request_with_status("/mount/model/save_as_default")

    def mount_model_save(self, filename):
        """
        Save the active pointing model to a file so that it can later be re-loaded
        by a call to mount_model_load().

        This may be useful when switching between models built for different instruments.
        For example, a system might have one model for the main telescope, and another
        model for a co-mounted telescope.
        """

        return self.request_with_status("/mount/model/save", filename=filename)

    def mount_model_load(self, filename):
        """
        Load a model from the specified file and make it the active model.

        This may be useful when switching between models built for different instruments.
        For example, a system might have one model for the main telescope, and another
        model for a co-mounted telescope.
        """

        return self.request_with_status("/mount/model/load", filename=filename)

    def focuser_connect(self):
        # Added in PWI 4.0.99 Beta 2
        return self.request_with_status("/focuser/connect")

    def focuser_disconnect(self):
        # Added in PWI 4.0.99 Beta 2
        return self.request_with_status("/focuser/disconnect")

    def focuser_enable(self):
        return self.request_with_status("/focuser/enable")

    def focuser_disable(self):
        return self.request_with_status("/focuser/disable")

    def focuser_goto(self, target):
        return self.request_with_status("/focuser/goto", target=target)

    def focuser_stop(self):
        return self.request_with_status("/focuser/stop")

    def rotator_connect(self):
        # Added in PWI 4.0.99 Beta 2
        return self.request_with_status("/rotator/connect")

    def rotator_disconnect(self):
        # Added in PWI 4.0.99 Beta 2
        return self.request_with_status("/rotator/disconnect")


    def rotator_enable(self):
        return self.request_with_status("/rotator/enable")

    def rotator_disable(self):
        return self.request_with_status("/rotator/disable")
        
    def rotator_goto_mech(self, target_degs):
        return self.request_with_status("/rotator/goto_mech", degs=target_degs)

    def rotator_goto_field(self, target_degs):
        return self.request_with_status("/rotator/goto_field", degs=target_degs)

    def rotator_offset(self, offset_degs):
        return self.request_with_status("/rotator/offset", degs=offset_degs)

    def rotator_stop(self):
        return self.request_with_status("/rotator/stop")

    def m3_goto(self, target_port):
        return self.request_with_status("/m3/goto", port=target_port)

    def m3_stop(self):
        return self.request_with_status("/m3/stop")

    def virtualcamera_take_image(self):
        """
        Returns a string containing a FITS image simulating a starfield
        at the current telescope position
        """
        return self.request("/virtualcamera/take_image")
    
    def virtualcamera_take_image_and_save(self, filename):
        """
        Request a fake FITS image from PWI4.
        Save the contents to the specified filename
        """

        contents = self.virtualcamera_take_image()
        f = open(filename, "wb")
        f.write(contents)
        f.close()

    ### Methods for testing error handling ######################

    def test_command_not_found(self):
        """
        Try making a request to a URL that does not exist.
        Useful for intentionally testing how the library will respond.
        """
        return self.request_with_status("/command/notfound")

    def test_internal_server_error(self):
        """
        Try making a request to a URL that will return a 500
        server error due to an intentionally unhandled error.
        Useful for testing how the library will respond.
        """
        return self.request_with_status("/internal/crash")
    
    def test_invalid_parameters(self):
        """
        Try making a request with intentionally missing parameters.
        Useful for testing how the library will respond.
        """
        return self.request_with_status("/mount/goto_ra_dec_apparent")

    ### Low-level methods for issuing requests ##################

    def request(self, command, **kwargs):
        return self.comm.request(command, **kwargs)

    def request_with_status(self, command, **kwargs):
        response_text = self.request(command, **kwargs)
        return self.parse_status(response_text)
    
    ### Status parsing utilities ################################

    def status_text_to_dict(self, response):
        """
        Given text with keyword=value pairs separated by newlines,
        return a dictionary with the equivalent contents.
        """

        # In Python 3, response is of type "bytes".
        # Convert it to a string for processing below
        if type(response) == bytes:
            response = response.decode('utf-8')

        response_dict = {}

        lines = response.split("\n")
        
        for line in lines:
            fields = line.split("=", 1)
            if len(fields) == 2:
                name = fields[0]
                value = fields[1]
                response_dict[name] = value
        
        return response_dict

    def parse_status(self, response_text):
        response_dict = self.status_text_to_dict(response_text)
        return PWI4Status(response_dict)
    

    
class Section(object): 
    """
    Simple object for collecting properties in PWI4Status
    """

    pass

class PWI4Status:
    """
    Wraps the status response for many PWI4 commands in a class with named members
    """

    def __init__(self, status_dict):
        self.raw = status_dict  # Allow direct access to raw entries as needed

        self.pwi4 = Section()
        self.pwi4.version = "<unknown>"
        self.pwi4.version_field = [0, 0, 0, 0]

        self.pwi4.version = self.raw["pwi4.version"] # Added in 4.0.5 beta 1

        # pwi4.version_field[] was added in 4.0.9 beta 2
        self.pwi4.version_field[0] = self.get_int("pwi4.version_field[0]", 0)
        self.pwi4.version_field[1] = self.get_int("pwi4.version_field[1]", 0)
        self.pwi4.version_field[2] = self.get_int("pwi4.version_field[2]", 0)
        self.pwi4.version_field[3] = self.get_int("pwi4.version_field[3]", 0)

        # response.timestamp_utc was added in 4.0.9 beta 2
        self.response = Section()
        self.response.timestamp_utc = self.get_string("response.timestamp_utc")


        self.site = Section()
        self.site.latitude_degs = self.get_float("site.latitude_degs")
        self.site.longitude_degs = self.get_float("site.longitude_degs")
        self.site.height_meters = self.get_float("site.height_meters")
        self.site.lmst_hours = self.get_float("site.lmst_hours")

        self.mount = Section()
        self.mount.is_connected = self.get_bool("mount.is_connected")
        self.mount.geometry = self.get_int("mount.geometry")
        self.mount.timestamp_utc = self.get_string("mount.timestamp_utc") # Added in 4.0.9 beta 7
        self.mount.julian_date = self.get_float("mount.julian_date")  # Added in 4.0.9 beta 2
        self.mount.slew_time_constant = self.get_float("mount.slew_time_constant")  # Added in 4.0.9 beta 6
        self.mount.ra_apparent_hours = self.get_float("mount.ra_apparent_hours")
        self.mount.dec_apparent_degs = self.get_float("mount.dec_apparent_degs")
        self.mount.ra_j2000_hours = self.get_float("mount.ra_j2000_hours")
        self.mount.dec_j2000_degs = self.get_float("mount.dec_j2000_degs")
        self.mount.target_ra_apparent_hours = self.get_float("mount.target_ra_apparent_hours") # Added in 4.0.5 beta 1
        self.mount.target_dec_apparent_degs = self.get_float("mount.target_dec_apparent_degs") # Added in 4.0.5 beta 1
        self.mount.azimuth_degs = self.get_float("mount.azimuth_degs")
        self.mount.altitude_degs = self.get_float("mount.altitude_degs")
        self.mount.is_slewing = self.get_bool("mount.is_slewing")
        self.mount.is_tracking = self.get_bool("mount.is_tracking")
        self.mount.field_angle_here_degs = self.get_float("mount.field_angle_here_degs")
        self.mount.field_angle_at_target_degs = self.get_float("mount.field_angle_at_target_degs")
        self.mount.field_angle_rate_at_target_degs_per_sec = self.get_float("mount.field_angle_rate_at_target_degs_per_sec")
        self.mount.path_angle_at_target_degs = self.get_float("mount.path_angle_at_target_degs")
        self.mount.path_angle_rate_at_target_degs_per_sec = self.get_float("mount.path_angle_rate_at_target_degs_per_sec")
        self.mount.distance_to_sun_degs = self.get_float("mount.distance_to_sun_degs")      # Added in 4.0.13
        self.mount.axis0_wrap_range_min_degs = self.get_float("mount.axis0_wrap_range_min_degs") # Added in 4.0.13


        self.mount.axis0 = Section()
        self.mount.axis1 = Section()
        self.mount.axis = [self.mount.axis0, self.mount.axis1]

        for axis_index in range(2):
            axis = self.mount.axis[axis_index]
            prefix = "mount.axis%d." % axis_index

            axis.is_enabled = self.get_bool(prefix + "is_enabled")
            axis.rms_error_arcsec = self.get_float(prefix + "rms_error_arcsec")
            axis.dist_to_target_arcsec = self.get_float(prefix + "dist_to_target_arcsec")
            axis.servo_error_arcsec = self.get_float(prefix + "servo_error_arcsec")
            axis.min_mech_position_degs = self.get_float(prefix + "min_mech_position_degs") # Added in 4.0.13
            axis.max_mech_position_degs = self.get_float(prefix + "max_mech_position_degs") # Added in 4.0.13
            axis.target_mech_position_degs = self.get_float(prefix + "target_mech_position_degs") # Added in 4.0.13
            axis.position_degs = self.get_float(prefix + "position_degs")
            axis.position_timestamp_str = self.get_string(prefix + "position_timestamp") # Added in 4.0.9 beta 2
            axis.max_velocity_degs_per_sec = self.get_float(prefix + "max_velocity_degs_per_sec") # Added in 4.0.13
            axis.setpoint_velocity_degs_per_sec = self.get_float(prefix + "setpoint_velocity_degs_per_sec") # Added in 4.0.13
            axis.measured_velocity_degs_per_sec = self.get_float(prefix + "measured_velocity_degs_per_sec") # Added in 4.0.13
            axis.acceleration_degs_per_sec_sqr = self.get_float(prefix + "acceleration_degs_per_sec_sqr") # Added in 4.0.13
            axis.measured_current_amps = self.get_float(prefix + "measured_current_amps") # Added in 4.0.13
        
        self.mount.model = Section()
        self.mount.model.filename = self.get_string("mount.model.filename")
        self.mount.model.num_points_total = self.get_int("mount.model.num_points_total")
        self.mount.model.num_points_enabled = self.get_int("mount.model.num_points_enabled")
        self.mount.model.rms_error_arcsec = self.get_float("mount.model.rms_error_arcsec")

        # mount.offests.* was added in PWI 4.0.11 Beta 5
        if "mount.offsets.ra_arcsec.total" not in self.raw:
            self.mount.offsets = None  # Offset reporting not supported by running version of PWI4
        else:
            self.mount.offsets = Section()

            self.mount.offsets.ra_arcsec = Section()
            self.mount.offsets.ra_arcsec.total=self.get_float("mount.offsets.ra_arcsec.total")
            self.mount.offsets.ra_arcsec.rate=self.get_float("mount.offsets.ra_arcsec.rate")
            self.mount.offsets.ra_arcsec.gradual_offset_progress=self.get_float("mount.offsets.ra_arcsec.gradual_offset_progress")

            self.mount.offsets.dec_arcsec = Section()
            self.mount.offsets.dec_arcsec.total=self.get_float("mount.offsets.dec_arcsec.total")
            self.mount.offsets.dec_arcsec.rate=self.get_float("mount.offsets.dec_arcsec.rate")
            self.mount.offsets.dec_arcsec.gradual_offset_progress=self.get_float("mount.offsets.dec_arcsec.gradual_offset_progress")

            self.mount.offsets.axis0_arcsec = Section()
            self.mount.offsets.axis0_arcsec.total=self.get_float("mount.offsets.axis0_arcsec.total")
            self.mount.offsets.axis0_arcsec.rate=self.get_float("mount.offsets.axis0_arcsec.rate")
            self.mount.offsets.axis0_arcsec.gradual_offset_progress=self.get_float("mount.offsets.axis0_arcsec.gradual_offset_progress")

            self.mount.offsets.axis1_arcsec = Section()
            self.mount.offsets.axis1_arcsec.total=self.get_float("mount.offsets.axis1_arcsec.total")
            self.mount.offsets.axis1_arcsec.rate=self.get_float("mount.offsets.axis1_arcsec.rate")
            self.mount.offsets.axis1_arcsec.gradual_offset_progress=self.get_float("mount.offsets.axis1_arcsec.gradual_offset_progress")

            self.mount.offsets.path_arcsec = Section()
            self.mount.offsets.path_arcsec.total=self.get_float("mount.offsets.path_arcsec.total")
            self.mount.offsets.path_arcsec.rate=self.get_float("mount.offsets.path_arcsec.rate")
            self.mount.offsets.path_arcsec.gradual_offset_progress=self.get_float("mount.offsets.path_arcsec.gradual_offset_progress")
            
            self.mount.offsets.transverse_arcsec = Section()
            self.mount.offsets.transverse_arcsec.total=self.get_float("mount.offsets.transverse_arcsec.total")
            self.mount.offsets.transverse_arcsec.rate=self.get_float("mount.offsets.transverse_arcsec.rate")
            self.mount.offsets.transverse_arcsec.gradual_offset_progress=self.get_float("mount.offsets.transverse_arcsec.gradual_offset_progress")

        self.focuser = Section()
        self.focuser.exists = self.get_bool("focuser.exists", False) # Added in 4.0.99 Beta 2
        self.focuser.is_connected = self.get_bool("focuser.is_connected")
        self.focuser.is_enabled = self.get_bool("focuser.is_enabled")
        self.focuser.position = self.get_float("focuser.position")
        self.focuser.is_moving = self.get_bool("focuser.is_moving")
        
        self.rotator = Section()
        self.rotator.exists = self.get_bool("rotator.exists", False) # Added in 4.0.99 Beta 2
        self.rotator.is_connected = self.get_bool("rotator.is_connected")
        self.rotator.is_enabled = self.get_bool("rotator.is_enabled")
        self.rotator.mech_position_degs = self.get_float("rotator.mech_position_degs")
        self.rotator.field_angle_degs = self.get_float("rotator.field_angle_degs")
        self.rotator.is_moving = self.get_bool("rotator.is_moving")
        self.rotator.is_slewing = self.get_bool("rotator.is_slewing")

        self.m3 = Section()
        self.m3.exists = self.get_bool("m3.exists", False) # Added in 4.0.99 Beta 2
        self.m3.port = self.get_int("m3.port")

        self.autofocus = Section()
        self.autofocus.is_running = self.get_bool("autofocus.is_running")
        self.autofocus.success = self.get_bool("autofocus.success")
        self.autofocus.best_position = self.get_float("autofocus.best_position")
        self.autofocus.tolerance = self.get_float("autofocus.tolerance")


    def get_bool(self, name, value_if_missing=None):
        if name not in self.raw:
            return value_if_missing
        return self.raw[name].lower() == "true"

    def get_float(self, name, value_if_missing=None):
        if name not in self.raw:
            return value_if_missing
        return float(self.raw[name])

    def get_int(self, name, value_if_missing=None):
        if name not in self.raw:
            return value_if_missing
        return int(self.raw[name])
    
    def get_string(self, name, value_if_missing=None):
        if name not in self.raw:
            return value_if_missing
        return self.raw[name]

    def __repr__(self):
        """
        Format all of the keywords and values we have received
        """

        max_key_length = max(len(x) for x in self.raw.keys())

        lines = []

        line_format = "%-" + str(max_key_length) + "s: %s"

        for key in sorted(self.raw.keys()):
            value = self.raw[key]
            lines.append(line_format % (key, value))
        return "\n".join(lines)

class PWI4HttpCommunicator:
    """
    Manages communication with PWI4 via HTTP.
    """

    def __init__(self, host="localhost", port=8220):
        self.host = host
        self.port = port

        self.timeout_seconds = 3

    def make_url(self, path, **kwargs):
        """
        Utility function that takes a set of keyword=value arguments
        and converts them into a properly formatted URL to send to PWI.
        Special characters (spaces, colons, plus symbols, etc.) are encoded as needed.

        Example:
          make_url("/mount/gotoradec2000", ra=10.123, dec="15 30 45") -> "http://localhost:8220/mount/gotoradec2000?ra=10.123&dec=15%2030%2045"
        """

        # Construct the basic URL, excluding the keyword parameters; for example: "http://localhost:8220/specified/path?"
        url = "http://" + self.host + ":" + str(self.port) + path + "?"

        # For every keyword=value argument given to this function,
        # construct a string of the form "key1=val1&key2=val2".
        keyword_values = list(kwargs.items()) # Need to explicitly convert this to list() for Python 3.x
        urlparams = urlencode(keyword_values)

        # In URLs, spaces can be encoded as "+" characters or as "%20".
        # This will convert plus symbols to percent encoding for improved compatibility.
        urlparams = urlparams.replace("+", "%20")

        # Build the final URL and return it.
        url = url + urlparams
        return url

    def request(self, path, postdata=None, **kwargs):
        """
        Issue a request to PWI using the keyword=value parameters
        supplied to the function, and return the response received from
        PWI.

        Example:
          pwi_request("/mount/gotoradec2000", ra=10.123, dec="15 30 45")
        
        will construct the appropriate URL and issue the request to the server.

        If the postdata argument is specified, this will make a POST request
        instead of a GET request, and postdata will be used as the body of the
        POST request.

        The server response payload will be returned, or an exception will be thrown
        if there was an error with the request.
        """

        # Construct the URL that we will request
        url = self.make_url(path, **kwargs)

        # Open a connection to the server, issue the request, and try to receive the response.
        # The server will return an HTTP Status Code as part of the response.
        # If the status code indicates an error, an HTTPError will be thrown.
        try:
            response = urlopen(url, data=postdata, timeout=self.timeout_seconds)
        except HTTPError as e:
            if e.code == 404:
                error_message = "Command not found"
            elif e.code == 400:
                error_message = "Bad request"
            elif e.code == 500:
                error_message = "Internal server error (possibly a bug in PWI)"
            else:
                error_message = str(e)

            try:
                error_details = e.read()  # Try to read the payload of the response for error information
                error_message = error_message + ": " + error_details
            except:
                pass # If that failed, we won't include any further details
            
            raise Exception(error_message) # TODO: Consider a custom exception here

            
        except Exception as e:
            # This will often be a urllib2.URLError to indicate that a connection
            # could not be made to the server, but we'll handle any exception here
            raise

        payload = response.read()
        return payload

    
def list_to_comma_separated_string(value_list):
    """
    Convert list of values (e.g. [3, 1, 5]) into a comma-separated string (e.g. "3,1,5")
    """

    return ",".join([str(x) for x in value_list])