from django.core.urlresolvers import reverse

from rest_framework import status

from hs_core.hydroshare import resource

from .base import HSRESTTestCase


class TestPublicCopyResourceEndpoint(HSRESTTestCase):
    def setUp(self):
        super(TestPublicCopyResourceEndpoint, self).setUp()

        self.rtype = 'GenericResource'
        self.title = 'My Test resource'
        res = resource.create_resource(self.rtype,
                                       self.user,
                                       self.title)

        self.pid = res.short_id
        self.resources_to_delete.append(self.pid)

    def test_copy_resource(self):
        copy_url = reverse('copy_resource_public', kwargs={'short_id': self.pid})
        response = self.client.post(copy_url, {}, format='json')
        print(response.content, type(response), response.status_code)
        self.resources_to_delete.append(response.content)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_copy_bad_resource(self):
        copy_url = reverse('copy_resource_public', kwargs={'short_id': '10101101010'})
        response = self.client.post(copy_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
