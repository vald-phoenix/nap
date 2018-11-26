from __future__ import unicode_literals
from __future__ import absolute_import
import json
import unittest
from collections import OrderedDict

import pytest
import mock

import nap
from nap.http import NapResponse
from nap.engine import ResourceEngine
from nap.exceptions import InvalidStatusError, BadRequestError

from . import SampleResourceModel


class BaseResourceModelTest(object):

    def get_engine(self):
        engine = ResourceEngine(SampleResourceModel)
        return engine

    def get_mock_response(self, **kwargs):

        default_kwargs = {
            'status_code': 200,
            'content': '',
        }
        default_kwargs.update(kwargs)
        r = mock.Mock(**default_kwargs)

        return r


class TestResourceModelURLMethods(BaseResourceModelTest):

    def test_get_lookup_url(self):

        engine = self.get_engine()

        with pytest.raises(ValueError):
            engine.get_lookup_url(content='something')

        final_uri = engine.get_lookup_url(hello='1', what='2')
        assert final_uri == "1/2/"

        final_uri_with_params = engine.get_lookup_url(
            hello='1',
            what='2',
            extra_param='3'
        )
        assert final_uri_with_params == '1/2/?extra_param=3'
        SampleResourceModel._lookup_urls = []

    @pytest.mark.parametrize('test_kwargs', [
        OrderedDict([('a_list', [5, 4, 3]), ('b', 2), ('c', 1)]),
        OrderedDict([('a_list', [5, 4, 3]), ('c', 1), ('b', 2)]),
        OrderedDict([('b', 2), ('a_list', [5, 4, 3]), ('c', 1)]),
        OrderedDict([('b', 2), ('c', 1), ('a_list', [5, 4, 3])]),
        OrderedDict([('c', 1), ('a_list', [5, 4, 3]), ('b', 2)]),
        OrderedDict([('c', 1), ('b', 2), ('a_list', [5, 4, 3])]),
    ])
    def test_get_lookup_url_with_list_params(self, test_kwargs):
        engine = self.get_engine()

        final_uri_with_params = engine.get_lookup_url(
            hello='hai',
            what='wut',
            **test_kwargs
        )
        assert final_uri_with_params == 'hai/wut/?a_list=5&a_list=4&a_list=3&b=2&c=1'
        SampleResourceModel._lookup_urls = []

    def test_delete_url(self):

        engine = self.get_engine()
        final_uri = engine.get_delete_url(title='1')
        assert final_uri == "1/"

    def test_update_url(self):

        engine = self.get_engine()
        final_uri = engine.get_delete_url(title='1')
        assert final_uri == "1/"

    def test_create_url(self):

        engine = self.get_engine()

        prepend_urls = (nap.lookup.nap_url(r'special_create_url/', create=True, lookup=False),)
        old_urls = engine.model._meta['urls']
        new_urls = prepend_urls + old_urls
        engine.model._meta['urls'] = new_urls

        final_uri = engine.get_create_url()
        assert final_uri == "special_create_url/"

        engine.model._meta['urls'] = old_urls


class TestResourceEngineAccessMethods(BaseResourceModelTest):

    def test_get_from_uri(self, skip_cache=False):

        engine = self.get_engine()
        fake_dict = {
            'title': "A fake title",
            'content': "isnt this neat",
        }
        with mock.patch('requests.request') as get:
            stubbed_response = mock.Mock()
            stubbed_response.content = json.dumps(fake_dict)

            model_root_url = engine.model._meta['root_url']
            expected_url = "xyz/"
            stubbed_response.url = expected_url
            stubbed_response.status_code = 200

            get.return_value = stubbed_response
            obj = engine.get_from_uri('xyz', skip_cache=skip_cache)

            assert obj.title == fake_dict['title']
            assert obj.content == fake_dict['content']
            assert obj._root_url == model_root_url
            assert obj._full_url == expected_url

    @mock.patch('nap.engine.ResourceEngine.get_from_cache')
    def test_get_from_uri_skip_cache(self, *mocks):

        get_from_cache = mocks[0]
        get_from_cache.return_value = None

        self.test_get_from_uri(True)
        assert not get_from_cache.called

        self.test_get_from_uri()
        assert get_from_cache.called

    def test_request_no_root_url(self):
        engine = self.get_engine()
        root_url = engine.model._meta['root_url']
        del engine.model._meta['root_url']

        with pytest.raises(ValueError):
            engine._request('POST', 'somereallybadurl.com')

        engine.model._meta['root_url'] = root_url

    def test_get(self):

        engine = self.get_engine()
        with mock.patch('nap.engine.ResourceEngine.get_from_uri') as g:
            engine.get('/some/uri/')
            assert g.called
        with mock.patch('nap.engine.ResourceEngine.lookup') as lookup:
            engine.get(pk=1)
            assert lookup.called

    def test_lookup(self):

        engine = self.get_engine()
        with mock.patch('nap.engine.ResourceEngine.get_from_uri') as get:
            engine.lookup(hello='hello_test', what='what_test')
            get.assert_called_with('hello_test/what_test/', skip_cache=False)

        SampleResourceModel._lookup_urls = []

    def test_lookup_no_valid_urls(self):

        engine = self.get_engine()
        from pytest import raises
        with raises(ValueError):
            engine.get_lookup_url(hello='bad_hello')

        SampleResourceModel._lookup_urls = []

    def test_generate_url(self):

        engine = self.get_engine()
        rm = engine.model(hello='1', slug='slug')
        assert engine._generate_url(url_type='create', resource_obj=rm) == 'note/'

        # assert that keyword arguments take precedence over meta arguments
        essay_url = rm.objects._generate_url(url_type='create', resource_name='essay')
        assert essay_url == 'essay/'

        assert rm.objects._generate_url(url_type='update', resource_obj=rm) == 'note/slug/'
        # assert that keyword arguments take predecnce over field values
        new_slug_url = rm.objects._generate_url(url_type='update', slug='new-slug')
        assert new_slug_url == 'note/new-slug/'

    def test_validate_get_response(self):
        engine = self.get_engine()
        res = mock.Mock()
        res.status_code = 500
        with pytest.raises(InvalidStatusError):
            engine.validate_get_response(res)

    def test_obj_from_response(self):

        engine = self.get_engine()
        res = mock.Mock()
        res_dict = {'title': 'a title', 'content': 'some content'}
        res.content = json.dumps(res_dict)

        obj = engine.obj_from_response(res)

        assert obj.title == res_dict['title']
        assert obj.content == res_dict['content']


class TestResourceCollectionMethods(BaseResourceModelTest):

    def test_collection_field(self):

        SampleResourceModel._meta['collection_field'] = 'objects'
        with mock.patch('requests.request') as request:
            r = mock.Mock()
            collection_dict = {
                'meta': {'something': True},
                'objects': [
                    {'title': 'a'},
                    {'title': 'b', 'content': "b's content"},
                    {'title': 'c'},
                ]
            }
            r.content = json.dumps(collection_dict)
            r.status_code = 200
            request.return_value = r
            objects = SampleResourceModel.objects.all()
            assert request.called
        assert len(objects) == 3
        SampleResourceModel._meta['collection_field'] = None

    def test_filter(self):
        with mock.patch('requests.request') as request:
            r = mock.Mock()
            r.status_code = 200
            r.content = json.dumps([
                {'title': 'hello', 'content': 'content'},
                {'title': 'hello', 'content': 'content'}
            ])
            request.return_value = r
            dms = SampleResourceModel.objects.filter(title='title')
            assert len(dms) == 2

            r.content = json.dumps({'something': 'wrong'})
            request.return_value = r
            with pytest.raises(ValueError):
                SampleResourceModel.objects.filter(title='title')

    def test_validate_collection_response(self):
        engine = self.get_engine()
        res = mock.Mock()
        res.status_code = 500
        with pytest.raises(InvalidStatusError):
            engine.validate_collection_response(res)


class TestCacheFunctions(object):

    @mock.patch('requests.request')
    @mock.patch('nap.cache.base.BaseCacheBackend.get')
    def test_cached_result(self, *mocks):

        get = mocks[0]
        req = mocks[1]

        res_content = json.dumps({'title': 'hello!'})
        cached_response = NapResponse(
            content=res_content,
            url='some-url/',
            status_code=200,
            request_method='GET',
        )
        get.return_value = cached_response
        res = SampleResourceModel.objects.get_from_uri('some-url/')
        assert res.full_url == "some-url/"
        assert res.title == "hello!"
        assert not req.called

    @mock.patch('nap.cache.base.BaseCacheBackend.get')
    @mock.patch('nap.cache.base.BaseCacheBackend.set')
    def test_cache_set_not_called_on_cached_reselt(self, *mocks):

        get = mocks[1]
        cache_set = mocks[0]

        res_content = json.dumps({'title': 'hello!'})
        cached_response = NapResponse(
            content=res_content,
            url='some-url/',
            status_code=200,
            use_cache=True,
            request_method='GET',
        )
        get.return_value = cached_response
        SampleResourceModel.objects.get_from_uri('some-url/')
        assert not cache_set.called

    @mock.patch('nap.engine.ResourceEngine._request')
    @mock.patch('nap.cache.base.BaseCacheBackend.set')
    def test_set_cache_from_response(self, *mocks):

        cache_set = mocks[0]
        req = mocks[1]

        res_content = json.dumps({'title': 'hello!'})
        response = NapResponse(
            content=res_content,
            url='some-url/',
            status_code=200,
            request_method='GET',
        )
        req.return_value = response
        expected_cache_key = SampleResourceModel.objects.cache.get_cache_key(
            SampleResourceModel,
            response.url,
        )
        SampleResourceModel.objects.get_from_uri('some-url/')

        cache_set.assert_called_with(expected_cache_key, response, response=response)

    @mock.patch('nap.engine.ResourceEngine._request')
    @mock.patch('nap.cache.base.BaseCacheBackend.set')
    def test_set_cache_not_called(self, *mocks):

        cache_set = mocks[0]
        req = mocks[1]

        res_content = json.dumps({'id': 1, 'title': 'hello!'})
        response = NapResponse(
            content=res_content,
            url='some-url/',
            status_code=204,
            request_method='POST',
        )
        req.return_value = response
        expected_cache_key = SampleResourceModel.objects.cache.get_cache_key(SampleResourceModel, response.url)
        obj = SampleResourceModel(title='some-url/')
        obj.save()

        assert not cache_set.called

    @mock.patch('requests.request')
    @mock.patch('nap.cache.base.BaseCacheBackend.get')
    def test_invalid_cache_result_found(self, mock_get, mock_request):

        cached_response = 'Invalid cache value - should be a nap response'
        mock_get.return_value = cached_response

        response = NapResponse(
            content=json.dumps({'id': 1, 'title': 'hello!'}),
            url='some-url/',
            status_code=200,
            request_method='POST',
        )
        mock_request.return_value = response

        res = SampleResourceModel.objects.get_from_uri('some-url/')
        assert mock_request.called


class TestResourceEngineWriteMethods(BaseResourceModelTest, unittest.TestCase):

    headers = {'content-type': 'application/json'}

    def tearDown(self):
        SampleResourceModel._lookup_urls = []

    def dont_test_write_url(self):

        dm = SampleResourceModel(
            title='expected_title',
            content='Blank Content')

        url = dm.get_update_url()
        assert url == 'expected_title/'
        SampleResourceModel._lookup_urls = []

    def test_update(self):
        dm = SampleResourceModel(
            title='expected_title',
            content='Blank Content')

        with mock.patch('requests.request') as put:
            r = mock.Mock()
            r.content = ''
            r.status_code = 204
            put.return_value = r
            SampleResourceModel.objects.update(dm)
            data = SampleResourceModel.objects.serialize(dm, for_read=True)
            put.assert_called_with('PUT', "http://foo.com/v1/expected_title/",
                data=data, headers=self.headers, auth=None)
        SampleResourceModel._lookup_urls = []

    def test_create(self):

        # add a lookup url to ensure it doesn't get used
        dm = SampleResourceModel(
            title='expected_title',
            content='Blank Content',
            slug='some_slug')
        with mock.patch('requests.request') as post:
            r = mock.Mock()
            r.content = ''
            r.headers = {'location': 'http://foo.com/v1/random_title/'}
            r.status_code = 201
            post.return_value = r
            SampleResourceModel.objects.create(dm)
            data = SampleResourceModel.objects.serialize(dm, for_read=True)
            post.assert_called_with('POST', "http://foo.com/v1/note/",
                data=data, headers=self.headers, auth=None)
        SampleResourceModel._lookup_urls = []

    def test_write_with_no_lookup_url(self):

        from pytest import raises

        dm = SampleResourceModel(content='what')
        with raises(ValueError):
            SampleResourceModel.objects.update(dm)

    def test_handle_update_response(self):
        response = self.get_mock_response()
        engine = self.get_engine()

        with mock.patch('nap.engine.ResourceEngine.obj_from_response') as ofr:
            obj = engine.handle_update_response(response)
            assert not ofr.called

        assert obj is None

    def test_handle_update_response_invalid_content(self):
        response = self.get_mock_response(content='some invalid content')
        engine = self.get_engine()

        with mock.patch('nap.engine.ResourceEngine.obj_from_response') as ofr:
            ofr.side_effect = ValueError("foo")
            obj = engine.handle_update_response(response)
            # assert ofr.called

        assert obj is None

    def test_handle_update_response_with_obj(self):
        response = self.get_mock_response(content='some content')
        engine = self.get_engine()

        with mock.patch('nap.engine.ResourceEngine.obj_from_response') as ofr:
            ofr.return_value = SampleResourceModel(title='a title')
            obj = engine.handle_update_response(response)
            assert ofr.called

        assert obj.title == 'a title'

    def test_handle_create_response(self):
        response = self.get_mock_response()
        engine = self.get_engine()

        with mock.patch('nap.engine.ResourceEngine.obj_from_response') as ofr:
            obj = engine.handle_create_response(response)
            assert not ofr.called

        assert obj is None

    def test_handle_create_response_invalid_content(self):
        response = self.get_mock_response(content='some invalid content')
        engine = self.get_engine()

        with mock.patch('nap.engine.ResourceEngine.obj_from_response') as ofr:
            ofr.side_effect = ValueError("foo")
            obj = engine.handle_create_response(response)
            # assert ofr.called

        assert obj is None

    def test_handle_create_response_with_obj(self):
        response = self.get_mock_response(content='some content')
        engine = self.get_engine()

        with mock.patch('nap.engine.ResourceEngine.obj_from_response') as ofr:
            ofr.return_value = SampleResourceModel(title='a title')
            obj = engine.handle_create_response(response)
            assert ofr.called

        assert obj.title == 'a title'

    def test_validate_update_response(self):
        engine = self.get_engine()
        res = mock.Mock()
        res.status_code = 500
        with pytest.raises(InvalidStatusError):
            engine.validate_update_response(res)

        res_dict = {'your_field': 'has errors!'}
        res.content = json.dumps(res_dict)
        res.status_code = 400
        with pytest.raises(BadRequestError):
            engine.validate_update_response(res)

    def test_validate_create_response(self):
        engine = self.get_engine()
        res = mock.Mock()
        res.status_code = 500
        with pytest.raises(InvalidStatusError):
            engine.validate_create_response(res)

        res_dict = {'your_field': 'has errors!'}
        res.content = json.dumps(res_dict)
        res.status_code = 400
        with pytest.raises(BadRequestError):
            engine.validate_create_response(res)

    @mock.patch('nap.engine.ResourceEngine.validate_delete_response')
    @mock.patch('nap.engine.ResourceEngine.handle_delete_response')
    @mock.patch('nap.engine.ResourceEngine._request')
    def test_delete(self, *mocks):

        handle_delete = mocks[1]
        validate_delete = mocks[2]
        engine = self.get_engine()
        obj = SampleResourceModel(title='a title')
        engine.delete(obj)
        assert handle_delete.called
        assert validate_delete.called

    def test_validate_delete_response(self):

        engine = self.get_engine()
        res = mock.Mock()
        res.status_code = 500
        with mock.patch('nap.engine.ResourceEngine.validate_response') as vr:
            with pytest.raises(InvalidStatusError):
                engine.validate_delete_response(res)
            assert vr.called

    def test_handle_delete_response(self):
        response = self.get_mock_response()
        engine = self.get_engine()

        with mock.patch('nap.engine.ResourceEngine.obj_from_response') as ofr:
            obj = engine.handle_delete_response(response)
            assert not ofr.called

        assert obj is None

def test_modify_request():
    new_headers = {'test-header': '123'}
    default_args = SampleResourceModel._meta['default_request_args']
    default_headers = default_args['headers']

    new_headers.update(default_headers)

    with mock.patch('requests.request') as post:
        r = mock.Mock()
        r.content = '{}'
        r.status_code = 200
        post.return_value = r
        SampleResourceModel.objects.modify_request(headers=new_headers).filter()
        post.assert_called_with(
            'GET', "http://foo.com/v1/note/",
            data=None,
            headers=new_headers,
            auth=None
        )

    # ensure a subsequent, non-modified request is actually not modified
    with mock.patch('requests.request') as post2:
        r = mock.Mock()
        r.content = '{}'
        r.status_code = 200
        post2.return_value = r
        SampleResourceModel.objects.filter()
        post2.assert_called_with(
            'GET', "http://foo.com/v1/note/",
            data=None,
            headers=default_args['headers'],
            auth=None
        )

    SampleResourceModel._lookup_urls = []
