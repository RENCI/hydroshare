import os
from dateutil import parser

from django.conf import settings

from hs_core.models import ResourceFile
from hs_core.hydroshare import add_resource_files
from hs_core.views.utils import create_folder, move_or_rename_file_or_folder, zip_folder, \
    unzip_file, remove_folder
from hs_core.views.utils import run_ssh_command
from theme.models import UserProfile
from django_irods.icommands import SessionException


class MockIRODSTestCaseMixin(object):
    def setUp(self):
        super(MockIRODSTestCaseMixin, self).setUp()
        # only mock up testing iRODS operations when local iRODS container is not used
        if settings.IRODS_HOST != 'data.local.org':
            from mock import patch
            self.irods_patchers = (
                patch("hs_core.hydroshare.hs_bagit.delete_bag"),
                patch("hs_core.hydroshare.hs_bagit.create_bag"),
                patch("hs_core.hydroshare.hs_bagit.create_bag_files"),
                patch("hs_core.tasks.create_bag_by_irods"),
                patch("hs_core.hydroshare.utils.copy_resource_files_and_AVUs"),
            )
            for patcher in self.irods_patchers:
                patcher.start()

    def tearDown(self):
        if settings.IRODS_HOST != 'data.local.org':
            for patcher in self.irods_patchers:
                patcher.stop()
        super(MockIRODSTestCaseMixin, self).tearDown()


class TestCaseCommonUtilities(object):
    def create_irods_user_in_user_zone(self):
        # create corresponding irods account in user zone
        try:
            exec_cmd = "{0} {1} {2}".format(settings.HS_USER_ZONE_PROXY_USER_CREATE_USER_CMD,
                                            self.user.username, self.user.username)
            output = run_ssh_command(host=settings.HS_USER_ZONE_HOST,
                                     uname=settings.HS_USER_ZONE_PROXY_USER,
                                     pwd=settings.HS_USER_ZONE_PROXY_USER_PWD,
                                     exec_cmd=exec_cmd)
            if output:
                if 'ERROR:' in output.upper():
                    # irods account failed to create
                    self.assertRaises(SessionException(-1, output, output))

            user_profile = UserProfile.objects.filter(user=self.user).first()
            user_profile.create_irods_user_account = True
            user_profile.save()
        except Exception as ex:
            self.assertRaises(SessionException(-1, ex.message, ex.message))

    def delete_irods_user_in_user_zone(self):
        # delete irods test user in user zone
        try:
            exec_cmd = "{0} {1}".format(settings.HS_USER_ZONE_PROXY_USER_DELETE_USER_CMD,
                                        self.user.username)
            output = run_ssh_command(host=settings.HS_USER_ZONE_HOST,
                                     uname=settings.HS_USER_ZONE_PROXY_USER,
                                     pwd=settings.HS_USER_ZONE_PROXY_USER_PWD,
                                     exec_cmd=exec_cmd)
            if output:
                if 'ERROR:' in output.upper():
                    # there is an error from icommand run, report the error
                    self.assertRaises(SessionException(-1, output, output))

            user_profile = UserProfile.objects.filter(user=self.user).first()
            user_profile.create_irods_user_account = False
            user_profile.save()
        except Exception as ex:
            # there is an error from icommand run, report the error
            self.assertRaises(SessionException(-1, ex.message, ex.message))

    def resource_file_oprs(self):
        """
        This is a common test utility function to be called by both regular folder operation
        testing and federated zone folder operation testing.
        Make sure the calling TestCase object has the following attributes defined before calling
        this method:
        self.res: resource that has been created that contains files listed in file_name_list
        self.user: owner of the resource
        self.file_name_list: a list of three file names that have been added to the res object
        self.test_file_1 needs to be present for the calling object for doing regular folder
        operations without involving federated zone so that the same opened file can be readded
        to the resource for testing the case where zipping cannot overwrite existing file
        """
        user = self.user
        res = self.res
        file_name_list = self.file_name_list
        # create a folder, if folder is created successfully, no exception is raised, otherwise,
        # an iRODS exception will be raised which will be caught by the test runner and mark as
        # a test failure
        create_folder(res.short_id, 'data/contents/sub_test_dir')
        istorage = res.get_irods_storage()
        if res.resource_federation_path:
            res_path = os.path.join(res.resource_federation_path, res.short_id, 'data', 'contents')
            store = istorage.listdir(res_path)
        else:
            store = istorage.listdir(res.short_id + '/data/contents')
        self.assertIn('sub_test_dir', store[0], msg='resource does not contain sub folder created')

        # rename the third file in file_name_list
        move_or_rename_file_or_folder(user, res.short_id,
                                      'data/contents/' + file_name_list[2],
                                      'data/contents/new_' + file_name_list[2])
        # move the first two files in file_name_list to the new folder
        move_or_rename_file_or_folder(user, res.short_id,
                                      'data/contents/' + file_name_list[0],
                                      'data/contents/sub_test_dir/' + file_name_list[0])
        move_or_rename_file_or_folder(user, res.short_id,
                                      'data/contents/' + file_name_list[1],
                                      'data/contents/sub_test_dir/' + file_name_list[1])

        updated_res_file_names = []
        for rf in ResourceFile.objects.filter(object_id=res.id):
            if res.resource_federation_path:
                updated_res_file_names.append(rf.fed_resource_file_name_or_path)
            else:
                updated_res_file_names.append(rf.resource_file.name)

        if res.resource_federation_path:
            path_prefix = 'data/contents/'
        else:
            path_prefix = res.short_id + '/data/contents/'
        self.assertIn(path_prefix + 'new_' + file_name_list[2], updated_res_file_names,
                      msg="resource does not contain the updated file new_" + file_name_list[2])
        self.assertNotIn(path_prefix + file_name_list[2], updated_res_file_names,
                         msg='resource still contains the old file ' + file_name_list[2] +
                             ' after renaming')
        self.assertIn(path_prefix + 'sub_test_dir/' + file_name_list[0], updated_res_file_names,
                      msg='resource does not contain ' + file_name_list[0] + ' moved to a folder')
        self.assertNotIn(path_prefix + file_name_list[0], updated_res_file_names,
                         msg='resource still contains the old ' + file_name_list[0] +
                             'after moving to a folder')
        self.assertIn(path_prefix + 'sub_test_dir/' + file_name_list[1], updated_res_file_names,
                      msg='resource does not contain ' + file_name_list[1] +
                          'moved to a new folder')
        self.assertNotIn(path_prefix + file_name_list[1], updated_res_file_names,
                         msg='resource still contains the old ' + file_name_list[1] +
                             ' after moving to a folder')

        # zip the folder
        output_zip_fname, size = \
            zip_folder(user, res.short_id, 'data/contents/sub_test_dir',
                       'sub_test_dir.zip', True)
        self.assertGreater(size, 0, msg='zipped file has a size of 0')
        # Now resource should contain only two files: new_file3.txt and sub_test_dir.zip
        # since the folder is zipped into sub_test_dir.zip with the folder deleted
        self.assertEqual(res.files.all().count(), 2,
                         msg="resource file count didn't match-")

        # test unzip does not allow override of existing files
        # add an existing file in the zip to the resource
        if res.resource_federation_path:
            fed_test_file1_full_path = '/{zone}/home/{uname}/{fname}'.format(
                zone=settings.HS_USER_IRODS_ZONE, uname=user.username, fname=file_name_list[0])
            add_resource_files(res.short_id, fed_res_file_names=[fed_test_file1_full_path],
                               fed_copy_or_move='copy',
                               fed_zone_home_path=res.resource_federation_path)

        else:
            add_resource_files(res.short_id, self.test_file_1)

        create_folder(res.short_id, 'data/contents/sub_test_dir')
        move_or_rename_file_or_folder(user, res.short_id,
                                      'data/contents/' + file_name_list[0],
                                      'data/contents/sub_test_dir/' + file_name_list[0])
        # Now resource should contain three files: file3_new.txt, sub_test_dir.zip, and file1.txt
        self.assertEqual(res.files.all().count(), 3, msg="resource file count didn't match")
        with self.assertRaises(SessionException):
            unzip_file(user, res.short_id, 'data/contents/sub_test_dir.zip', False)

        # Resource should still contain three files: file3_new.txt, sub_test_dir.zip, and file1.txt
        file_cnt = res.files.all().count()
        self.assertEqual(file_cnt, 3, msg="resource file count didn't match - " +
                                          str(file_cnt) + " != 3")

        # test unzipping the file succeeds now after deleting the existing file
        remove_folder(user, res.short_id, 'data/contents/sub_test_dir')
        # Now resource should contain two files: file3_new.txt and sub_test_dir.zip
        file_cnt = res.files.all().count()
        self.assertEqual(file_cnt, 2, msg="resource file count didn't match - " +
                                          str(file_cnt) + " != 2")
        unzip_file(user, res.short_id, 'data/contents/sub_test_dir.zip', True)
        # Now resource should contain three files: file1.txt, file2.txt, and file3_new.txt
        self.assertEqual(res.files.all().count(), 3, msg="resource file count didn't match")
        updated_res_file_names = []
        for rf in ResourceFile.objects.filter(object_id=res.id):
            if res.resource_federation_path:
                updated_res_file_names.append(rf.fed_resource_file_name_or_path)
            else:
                updated_res_file_names.append(rf.resource_file.name)
        self.assertNotIn(path_prefix + 'sub_test_dir.zip', updated_res_file_names,
                         msg="resource still contains the zip file after unzipping")
        self.assertIn(path_prefix + 'sub_test_dir/' + file_name_list[0], updated_res_file_names,
                      msg='resource does not contain unzipped file ' + file_name_list[0])
        self.assertIn(path_prefix + 'sub_test_dir/' + file_name_list[1], updated_res_file_names,
                      msg='resource does not contain unzipped file ' + file_name_list[1])
        self.assertIn(path_prefix + 'new_' + file_name_list[2], updated_res_file_names,
                      msg='resource does not contain unzipped file new_' + file_name_list[2])

        # rename a folder
        move_or_rename_file_or_folder(user, res.short_id,
                                      'data/contents/sub_test_dir', 'data/contents/sub_dir')
        updated_res_file_names = []
        for rf in ResourceFile.objects.filter(object_id=res.id):
            if res.resource_federation_path:
                updated_res_file_names.append(rf.fed_resource_file_name_or_path)
            else:
                updated_res_file_names.append(rf.resource_file.name)

        self.assertNotIn(path_prefix + 'sub_test_dir/' + file_name_list[0], updated_res_file_names,
                         msg='resource still contains ' + file_name_list[0] +
                             ' in the old folder after renaming')
        self.assertIn(path_prefix + 'sub_dir/' + file_name_list[0], updated_res_file_names,
                      msg='resource does not contain ' + file_name_list[0] +
                          ' in the new folder after renaming')
        self.assertNotIn(path_prefix + 'sub_test_dir/' + file_name_list[1], updated_res_file_names,
                         msg='resource still contains ' + file_name_list[1] +
                             ' in the old folder after renaming')
        self.assertIn(path_prefix + 'sub_dir/' + file_name_list[1], updated_res_file_names,
                      msg='resource does not contain ' + file_name_list[1] +
                          ' in the new folder after renaming')

        # remove a folder
        remove_folder(user, res.short_id, 'data/contents/sub_dir')
        # Now resource only contains one file
        self.assertEqual(res.files.all().count(), 1, msg="resource file count didn't match")
        if res.resource_federation_path:
            res_fname = ResourceFile.objects.filter(
                object_id=res.id)[0].fed_resource_file_name_or_path
        else:
            res_fname = ResourceFile.objects.filter(object_id=res.id)[0].resource_file.name
        self.assertEqual(res_fname, path_prefix + 'new_' + file_name_list[2])

    def raster_metadata_extraction(self):
        """
        This is a common test utility function to be called by both regular raster metadata
        extraction testing and federated zone raster metadata extraction testing.
        Make sure the calling TestCase object has self.resRaster attribute defined before calling
        this method which is the raster resource that has been created containing valid raster
        files.
        """
        # there should be 2 content files
        self.assertEqual(self.resRaster.files.all().count(), 2)

        # test core metadata after metadata extraction
        extracted_title = "My Test Raster Resource"
        self.assertEqual(self.resRaster.metadata.title.value, extracted_title)

        # there should be 1 creator
        self.assertEqual(self.resRaster.metadata.creators.all().count(), 1)

        # there should be 1 coverage element - box type
        self.assertEqual(self.resRaster.metadata.coverages.all().count(), 1)
        self.assertEqual(self.resRaster.metadata.coverages.all().filter(type='box').count(), 1)

        box_coverage = self.resRaster.metadata.coverages.all().filter(type='box').first()
        self.assertEqual(box_coverage.value['projection'], 'WGS 84 EPSG:4326')
        self.assertEqual(box_coverage.value['units'], 'Decimal degrees')
        self.assertEqual(box_coverage.value['northlimit'], 42.11071605314457)
        self.assertEqual(box_coverage.value['eastlimit'], -111.45699925047542)
        self.assertEqual(box_coverage.value['southlimit'], 41.66417975061928)
        self.assertEqual(box_coverage.value['westlimit'], -111.81761887121905)

        # there should be 2 format elements
        self.assertEqual(self.resRaster.metadata.formats.all().count(), 2)
        self.assertEqual(self.resRaster.metadata.formats.all().filter(
            value='application/vrt').count(), 1)
        self.assertEqual(self.resRaster.metadata.formats.all().filter(
            value='image/tiff').count(), 1)

        # testing extended metadata element: original coverage
        ori_coverage = self.resRaster.metadata.originalCoverage
        self.assertNotEqual(ori_coverage, None)
        self.assertEqual(ori_coverage.value['northlimit'], 4662392.446916306)
        self.assertEqual(ori_coverage.value['eastlimit'], 461954.01909127034)
        self.assertEqual(ori_coverage.value['southlimit'], 4612592.446916306)
        self.assertEqual(ori_coverage.value['westlimit'], 432404.01909127034)
        self.assertEqual(ori_coverage.value['units'], 'meter')
        self.assertEqual(ori_coverage.value['projection'],
                         'NAD83 / UTM zone 12N Transverse_Mercator')

        # testing extended metadata element: cell information
        cell_info = self.resRaster.metadata.cellInformation
        self.assertEqual(cell_info.rows, 1660)
        self.assertEqual(cell_info.columns, 985)
        self.assertEqual(cell_info.cellSizeXValue, 30.0)
        self.assertEqual(cell_info.cellSizeYValue, 30.0)
        self.assertEqual(cell_info.cellDataType, 'Float32')

        # testing extended metadata element: band information
        self.assertEqual(self.resRaster.metadata.bandInformation.count(), 1)
        band_info = self.resRaster.metadata.bandInformation.first()
        self.assertEqual(band_info.noDataValue, '-3.40282346639e+38')
        self.assertEqual(band_info.maximumValue, '3031.44311523')
        self.assertEqual(band_info.minimumValue, '1358.33459473')

    def netcdf_metadata_extraction(self):
        """
        This is a common test utility function to be called by both regular netcdf metadata
        extraction testing and federated zone netCDF metadata extraction testing.
        Make sure the calling TestCase object has self.resNetcdf attribute defined before calling
        this method which is the netCDF resource that has been created containing valid netCDF
        files.
        """
        # there should 2 content file
        self.assertEqual(self.resNetcdf.files.all().count(), 2)

        # test core metadata after metadata extraction
        extracted_title = "Snow water equivalent estimation at TWDEF site from Oct 2009 to " \
                          "June 2010"
        self.assertEqual(self.resNetcdf.metadata.title.value, extracted_title)

        # there should be an abstract element
        self.assertNotEqual(self.resNetcdf.metadata.description, None)
        extracted_abstract = "This netCDF data is the simulation output from Utah Energy Balance " \
                             "(UEB) model.It includes the simulation result of snow water " \
                             "equivalent during the period Oct. 2009 to June 2010 for TWDEF site " \
                             "in Utah."
        self.assertEqual(self.resNetcdf.metadata.description.abstract, extracted_abstract)

        # there should be one source element
        self.assertEqual(self.resNetcdf.metadata.sources.all().count(), 1)

        # there should be one license element:
        self.assertNotEqual(self.resNetcdf.metadata.rights.statement, 1)

        # there should be one relation element
        self.assertEqual(self.resNetcdf.metadata.relations.all().filter(type='cites').count(), 1)

        # there should be 2 creator
        self.assertEqual(self.resNetcdf.metadata.creators.all().count(), 2)

        # there should be one contributor
        self.assertEqual(self.resNetcdf.metadata.contributors.all().count(), 1)

        # there should be 2 coverage element - box type and period type
        self.assertEqual(self.resNetcdf.metadata.coverages.all().count(), 2)
        self.assertEqual(self.resNetcdf.metadata.coverages.all().filter(type='box').count(), 1)
        self.assertEqual(self.resNetcdf.metadata.coverages.all().filter(type='period').count(), 1)

        box_coverage = self.resNetcdf.metadata.coverages.all().filter(type='box').first()
        self.assertEqual(box_coverage.value['projection'], 'WGS 84 EPSG:4326')
        self.assertEqual(box_coverage.value['units'], 'Decimal degrees')
        self.assertEqual(box_coverage.value['northlimit'], 41.867126409)
        self.assertEqual(box_coverage.value['eastlimit'], -111.505940368)
        self.assertEqual(box_coverage.value['southlimit'], 41.8639080745)
        self.assertEqual(box_coverage.value['westlimit'], -111.51138808)

        temporal_coverage = self.resNetcdf.metadata.coverages.all().filter(type='period').first()
        self.assertEqual(parser.parse(temporal_coverage.value['start']).date(),
                         parser.parse('10/01/2009').date())
        self.assertEqual(parser.parse(temporal_coverage.value['end']).date(),
                         parser.parse('05/30/2010').date())

        # there should be 2 format elements
        self.assertEqual(self.resNetcdf.metadata.formats.all().count(), 2)
        self.assertEqual(self.resNetcdf.metadata.formats.all().filter(value='text/plain').count(),
                         1)
        self.assertEqual(self.resNetcdf.metadata.formats.all().filter(
            value='application/x-netcdf').count(), 1)

        # there should be one subject element
        self.assertEqual(self.resNetcdf.metadata.subjects.all().count(), 1)
        subj_element = self.resNetcdf.metadata.subjects.all().first()
        self.assertEqual(subj_element.value, 'Snow water equivalent')

        # testing extended metadata element: original coverage
        ori_coverage = self.resNetcdf.metadata.ori_coverage.all().first()
        self.assertNotEqual(ori_coverage, None)
        self.assertEqual(ori_coverage.projection_string_type, 'Proj4 String')
        proj_text = '+proj=tmerc +lon_0=-111.0 +lat_0=0.0 +x_0=500000.0 +y_0=0.0 +k_0=0.9996'
        self.assertEqual(ori_coverage.projection_string_text, proj_text)
        self.assertEqual(ori_coverage.value['northlimit'], '4.63515e+06')
        self.assertEqual(ori_coverage.value['eastlimit'], '458010.0')
        self.assertEqual(ori_coverage.value['southlimit'], '4.63479e+06')
        self.assertEqual(ori_coverage.value['westlimit'], '457560.0')
        self.assertEqual(ori_coverage.value['units'], 'Meter')
        self.assertEqual(ori_coverage.value['projection'], 'transverse_mercator')

        # testing extended metadata element: variables
        self.assertEqual(self.resNetcdf.metadata.variables.all().count(), 5)

        # test time variable
        var_time = self.resNetcdf.metadata.variables.all().filter(name='time').first()
        self.assertNotEqual(var_time, None)
        self.assertEqual(var_time.unit, 'hours since 2009-10-1 0:0:00 UTC')
        self.assertEqual(var_time.type, 'Float')
        self.assertEqual(var_time.shape, 'time')
        self.assertEqual(var_time.descriptive_name, 'time')

        # test x variable
        var_x = self.resNetcdf.metadata.variables.all().filter(name='x').first()
        self.assertNotEqual(var_x, None)
        self.assertEqual(var_x.unit, 'Meter')
        self.assertEqual(var_x.type, 'Float')
        self.assertEqual(var_x.shape, 'x')
        self.assertEqual(var_x.descriptive_name, 'x coordinate of projection')

        # test y variable
        var_y = self.resNetcdf.metadata.variables.all().filter(name='y').first()
        self.assertNotEqual(var_y, None)
        self.assertEqual(var_y.unit, 'Meter')
        self.assertEqual(var_y.type, 'Float')
        self.assertEqual(var_y.shape, 'y')
        self.assertEqual(var_y.descriptive_name, 'y coordinate of projection')

        # test SWE variable
        var_swe = self.resNetcdf.metadata.variables.all().filter(name='SWE').first()
        self.assertNotEqual(var_swe, None)
        self.assertEqual(var_swe.unit, 'm')
        self.assertEqual(var_swe.type, 'Float')
        self.assertEqual(var_swe.shape, 'y,x,time')
        self.assertEqual(var_swe.descriptive_name, 'Snow water equivalent')
        self.assertEqual(var_swe.method, 'model simulation of UEB model')
        self.assertEqual(var_swe.missing_value, '-9999')

        # test grid mapping variable
        var_grid = self.resNetcdf.metadata.variables.all().filter(
            name='transverse_mercator').first()
        self.assertNotEqual(var_grid, None)
        self.assertEqual(var_grid.unit, 'Unknown')
        self.assertEqual(var_grid.type, 'Unknown')
        self.assertEqual(var_grid.shape, 'Not defined')