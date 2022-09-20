# coding=utf-8
import logging
import datetime
import posixpath
from datetime import datetime
from urllib.parse import urljoin

import six
from oss2 import BUCKET_ACL_PRIVATE, Auth, Bucket, Service, BucketIterator, ObjectIterator, http, to_string
from django.conf import settings
from oss2.exceptions import AccessDenied, NoSuchBucket
from django.core.files import File
from django.utils.encoding import force_text, force_bytes
from django.core.exceptions import SuspiciousOperation
from django.utils.deconstruct import deconstructible
from django.core.files.storage import Storage

from conf.config import local_configs

logger = logging.getLogger("storages.oss")


def _normalize_endpoint(endpoint):
    if not endpoint.startswith("http://") and not endpoint.startswith("https://"):  # noqa
        return "https://" + endpoint
    else:
        return endpoint


class AliyunOperationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class BucketOperationMixin(object):
    def _get_bucket(self, auth):
        if self.cname:  # noqa
            bucket = Bucket(auth, self.cname, self.bucket_name, is_cname=True)  # noqa
        else:
            bucket = Bucket(auth, self.endpoint, self.bucket_name)  # noqa

        try:
            bucket.get_bucket_info()
        except NoSuchBucket:
            raise AliyunOperationError(f"{self.bucket_name} don't exist!")  # noqa
        else:
            return bucket

    def _list_bucket(self, service):  # noqa
        return [bucket.name for bucket in BucketIterator(service)]

    def _list_prefix_bucket(self, service, prefix):  # noqa
        return [bucket.name for bucket in BucketIterator(service, prefix=prefix)]

    def _create_bucket(self, auth):
        bucket = self._get_bucket(auth)
        bucket.create_bucket(local_configs.OSS.BUCKET_ACL_TYPE)
        return bucket

    # def _delete_bucket(self, bucket):  # noqa
    #     try:
    #         bucket.delete_bucket()
    #     except BucketNotEmpty:
    #         raise AliyunOperationError('bucket is not empty.')
    #     except NoSuchBucket:
    #         raise AliyunOperationError('bucket does not exist.')
    #


@deconstructible
class AliyunBaseStorage(BucketOperationMixin, Storage):  # noqa
    """
    Aliyun OSS2 Storage
    """

    location = ""

    def __init__(
        self,
        access_key_id=None,
        access_key_secret=None,
        endpoint=None,
        external_endpoint=None,
        bucket_name=None,
        cname=None,
        expire_time=None,
        location="",
    ):
        self.access_key_id = access_key_id if access_key_id else local_configs.OSS.ACCESS_KEY_ID
        self.access_key_secret = access_key_secret if access_key_secret else local_configs.OSS.ACCESS_KEY_SECRET
        self.endpoint = _normalize_endpoint(endpoint if endpoint else local_configs.OSS.ENDPOINT)
        external_endpoint = external_endpoint if external_endpoint else local_configs.OSS.EXTERNAL_ENDPOINT
        self.external_endpoint = None
        if external_endpoint:
            self.external_endpoint = _normalize_endpoint(external_endpoint)
        self.bucket_name = bucket_name if bucket_name else local_configs.OSS.BUCKET_NAME
        self.cname = cname if cname else local_configs.OSS.CNAME
        self.expire_time = expire_time if expire_time else int(local_configs.OSS.EXPIRE_TIME)

        self.auth = Auth(self.access_key_id, self.access_key_secret)
        self.service = Service(self.auth, self.endpoint)
        self.bucket = Bucket(self.auth, self.endpoint, self.bucket_name)
        self.location = location

        try:
            if self.bucket_name not in self._list_bucket(self.service):
                # self.bucket = self._create_bucket(self.auth)
                raise SuspiciousOperation("Bucket '%s' does not exist." % self.bucket_name)
            else:
                # change bucket acl if not consists
                self.bucket = self._get_bucket(self.auth)
                self.bucket_acl = self.bucket.get_bucket_acl().acl
                if self.bucket_acl != local_configs.OSS.BUCKET_ACL_TYPE:
                    raise SuspiciousOperation(
                        "Acl '%s' of Bucket '%s' does not match config '%s'." % self.bucket_acl,
                        self.bucket_name,
                        local_configs.OSS.BUCKET_ACL_TYPE,
                    )
        except AccessDenied:
            # 当启用了RAM访问策略，是不允许list和create bucket的
            self.bucket = self._get_bucket(self.auth)

    def _clean_name(self, name):  # noqa
        """
        Cleans the name so that Windows style paths work
        """
        # Normalize Windows style paths
        clean_name = posixpath.normpath(name).replace("\\", "/")

        # os.path.normpath() can strip trailing slashes so we implement
        # a workaround here.
        if name.endswith("/") and not clean_name.endswith("/"):
            # Add a trailing slash as it was stripped.
            return clean_name + "/"
        else:
            return clean_name

    def _normalize_name(self, name):
        """
        Normalizes the name so that paths like /path/to/ignored/../foo.txt
        work. We check to make sure that the path pointed to is not outside
        the directory specified by the LOCATION setting.
        """

        base_path = force_text(self.location)
        base_path = base_path.rstrip("/")

        final_path = urljoin(base_path.rstrip("/") + "/", name)

        base_path_len = len(base_path)
        if not final_path.startswith(base_path) or final_path[base_path_len : base_path_len + 1] not in (
            "",
            "/",
        ):  # noqa
            raise SuspiciousOperation("Attempted access to '%s' denied." % name)
        return final_path.lstrip("/")

    def _get_target_name(self, name):
        name = self._normalize_name(self._clean_name(name))
        if six.PY2:
            name = name.encode("utf-8")
        return name

    def _open(self, name, mode="rb"):
        return AliyunFile(name, self, mode)

    def _save(self, name, content):
        # 为保证django行为的一致性，保存文件时，应该返回相对于`media path`的相对路径。
        target_name = self._get_target_name(name)

        content.open()
        content_str = b"".join(chunk for chunk in content.chunks())
        self.bucket.put_object(target_name, content_str)
        content.close()

        return self._clean_name(name)

    def get_file_header(self, name):
        name = self._get_target_name(name)
        return self.bucket.head_object(name)

    def exists(self, name):
        return self.bucket.object_exists(name)

    def size(self, name):
        file_info = self.get_file_header(name)
        return file_info.content_length

    def modified_time(self, name):
        file_info = self.get_file_header(name)
        return datetime.datetime.fromtimestamp(file_info.last_modified)

    def listdir(self, name):
        name = self._normalize_name(self._clean_name(name))
        if name and name.endswith("/"):
            name = name[:-1]

        files = []
        dirs = set()

        for obj in ObjectIterator(self.bucket, prefix=name, delimiter="/"):
            if obj.is_prefix():
                dirs.add(obj.key)
            else:
                files.append(obj.key)

        return list(dirs), files

    def url(self, name):
        name = self._normalize_name(self._clean_name(name))
        _url = self.bucket.sign_url(
            "GET",
            name,
            # params={"x-oss-process": "image/resize,h_100,m_lfit"},
            expires=self.expire_time,
            slash_safe=True,
        )
        return _url

    def read(self, name):
        pass

    def delete(self, name):
        name = self._get_target_name(name)
        result = self.bucket.delete_object(name)
        if result.status >= 400:
            raise AliyunOperationError(result.resp)


class AliyunMediaStorage(AliyunBaseStorage):  # noqa
    location = settings.MEDIA_URL


class AliyunStaticStorage(AliyunBaseStorage):  # noqa
    location = settings.STATIC_URL


class AliyunFile(File):
    def __init__(self, name, storage, mode):
        self._storage = storage
        self._name = name[len(self._storage.location) :]
        self._mode = mode
        self.file = six.BytesIO()
        self._is_dirty = False
        self._is_read = False
        super(AliyunFile, self).__init__(self.file, self._name)

    def read(self, num_bytes=None):
        if not self._is_read:
            content = self._storage.bucket.get_object(self._name)
            self.file = six.BytesIO(content.read())
            self._is_read = True

        if num_bytes is None:
            data = self.file.read()
        else:
            data = self.file.read(num_bytes)

        if "b" in self._mode:
            return data
        else:
            return force_text(data)

    def write(self, content):
        if "w" not in self._mode:
            raise AliyunOperationError("Operation write is not allowed.")

        self.file.write(force_bytes(content))
        self._is_dirty = True
        self._is_read = True

    def close(self):
        if self._is_dirty:
            self.file.seek(0)
            self._storage._save(self._name, self.file)  # noqa
        self.file.close()
