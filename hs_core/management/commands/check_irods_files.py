# -*- coding: utf-8 -*-

"""
Check synchronization between iRODS and Django

This checks that:

1. every ResourceFile corresponds to an iRODS file
2. every iRODS file in {short_id}/data/contents corresponds to a ResourceFile
3. every iRODS directory {short_id} corresponds to a Django resource

* By default, prints errors on stdout.
* Optional argument --log instead logs output to system log.
"""

from django.core.management.base import BaseCommand
from hs_core.models import BaseResource
from hs_core.hydroshare.utils import get_resource_by_shortkey
from django_irods.storage import IrodsStorage

import logging


def check_for_dangling_irods(echo_errors=True, log_errors=False, return_errors=False):
    """ This checks for resource trees in iRODS with no correspondence to Django at all """

    istorage = IrodsStorage()  # local only
    toplevel = istorage.listdir('.')  # list the resources themselves
    logger = logging.getLogger(__name__)

    errors = []
    for id in toplevel[0]:  # directories
        try:
            get_resource_by_shortkey(id, or_404=False)
        except BaseResource.DoesNotExist:
            msg = "resource {} does not exist in Django".format(id)
            if echo_errors:
                print(msg)
            if log_errors:
                logger.error(msg)
            if return_errors:
                errors.append(msg)
    return errors


class Command(BaseCommand):
    help = "Check synchronization between iRODS and Django."

    def add_arguments(self, parser):

        # a list of resource id's, or none to check all resources
        parser.add_argument('resource_ids', nargs='*', type=str)

        # Named (optional) arguments
        parser.add_argument(
            '--log',
            action='store_true',  # True for presence, False for absence
            dest='log',           # value is options['log']
            help='log errors to system log',
        )

        # Named (optional) arguments
        parser.add_argument(
            '--unreferenced',
            action='store_true',  # True for presence, False for absence
            dest='unreferenced',           # value is options['log']
            help='check for local unreferenced iRODS files',
        )

    def handle(self, *args, **options):
        if options['unreferenced']:
            print("LOOKING FOR IRODS RESOURCES NOT IN DJANGO")
            check_for_dangling_irods(echo_errors=not options['log'],
                                     log_errors=options['log'],
                                     return_errors=False)

        elif len(options['resource_ids']) > 0:  # an array of resource short_id to check.
            for rid in options['resource_ids']:
                try:
                    resource = BaseResource.objects.get(short_id=rid)
                except BaseResource.DoesNotExist:
                    msg = "Resource with id {} not found in Django Resources".format(rid)
                    print(msg)

                print("LOOKING FOR FILE ERRORS FOR RESOURCE {}".format(rid))
                resource.check_irods_files(stop_on_error=False,
                                           echo_errors=not options['log'],
                                           log_errors=options['log'],
                                           return_errors=False)

        else:  # check all resources
            print("LOOKING FOR FILE ERRORS FOR ALL RESOURCES")
            for r in BaseResource.objects.all():
                r.check_irods_files(stop_on_error=False,
                                    echo_errors=not options['log'],  # Don't both log and echo
                                    log_errors=options['log'],
                                    return_errors=False)
