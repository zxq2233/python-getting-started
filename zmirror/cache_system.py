# coding=utf-8
import tempfile
import time
import pickle
from datetime import datetime

EXPIRE_NOW = 0
EXPIRE_1MIN = 60
EXPIRE_5MIN = EXPIRE_1MIN * 5
EXPIRE_30MIN = EXPIRE_1MIN * 30
EXPIRE_1HR = EXPIRE_1MIN * 60
EXPIRE_2HR = EXPIRE_1HR * 2
EXPIRE_3HR = EXPIRE_1HR * 3
EXPIRE_4HR = EXPIRE_1HR * 4
EXPIRE_6HR = EXPIRE_1HR * 6
EXPIRE_12HR = EXPIRE_1HR * 12
EXPIRE_1DAY = EXPIRE_1HR * 24
EXPIRE_2DAY = EXPIRE_1DAY * 2
EXPIRE_4DAY = EXPIRE_1DAY * 4
EXPIRE_1WEEK = EXPIRE_1DAY * 7
EXPIRE_1MOUTH = EXPIRE_1DAY * 31
EXPIRE_1YR = EXPIRE_1DAY * 365

DEFAULT_EXPIRE = EXPIRE_5MIN
mime_expire_list = {
    'application/javascript': EXPIRE_2DAY,
    'application/x-javascript': EXPIRE_2DAY,
    'text/javascript': EXPIRE_2DAY,

    'text/css': EXPIRE_2DAY,

    'text/x-cross-domain-policy': EXPIRE_2DAY,

    'application/vnd.ms-fontobject': EXPIRE_4DAY,
    'font/eot': EXPIRE_4DAY,
    'font/opentype': EXPIRE_4DAY,
    'application/x-font-ttf': EXPIRE_4DAY,
    'application/font-woff': EXPIRE_4DAY,
    'application/x-font-woff': EXPIRE_4DAY,
    'font/woff': EXPIRE_4DAY,
    'application/font-woff2': EXPIRE_4DAY,

    'audio/ogg': EXPIRE_1HR,
    'image/bmp': EXPIRE_1HR,
    'image/gif': EXPIRE_12HR,
    'image/jpeg': EXPIRE_12HR,
    'image/png': EXPIRE_12HR,
    'image/svg+xml': EXPIRE_12HR,
    'image/webp': EXPIRE_12HR,
    'video/mp4': EXPIRE_1HR,
    'video/ogg': EXPIRE_1HR,
    'video/webm': EXPIRE_1HR,

    'image/vnd.microsoft.icon': EXPIRE_12HR,
    'image/x-icon': EXPIRE_12HR,
    'application/manifest+json': EXPIRE_12HR,

    'application/atom+xml': EXPIRE_NOW,
    'application/rss+xml': EXPIRE_NOW,

    'application/json': EXPIRE_NOW,
    'application/ld+json': EXPIRE_NOW,
    'application/schema+json': EXPIRE_NOW,
    'application/vnd.geo+json': EXPIRE_NOW,
    'application/xml': EXPIRE_NOW,
    'text/xml': EXPIRE_NOW,
    'text/html': EXPIRE_NOW,
    'application/x-web-app-manifest+json': EXPIRE_NOW,
    'text/cache-manifest': EXPIRE_NOW,
}


def get_expire_from_mime(mime):
    return mime_expire_list.get(mime, DEFAULT_EXPIRE)


def _time_str_to_unix(timestring):
    try:
        t = int(time.mktime(datetime.strptime(timestring, '%a, %d %b %Y %H:%M:%S %Z').timetuple()))
    except:
        t = None
    return t


class FileCache:
    def __init__(self, max_size_kb=8192):
        self.cachedir = tempfile.TemporaryDirectory(prefix='mirror_')
        self.items_dict = {}
        self.max_size_byte = max_size_kb * 1024

    def put_obj(self, key, obj, expires=43200, obj_size=0, last_modified=None, info_dict=None):
        """

        :param last_modified: str  format: "Mon, 18 Nov 2013 09:02:42 GMT"
        :param obj_size: too big object should not be cached
        :param expires: seconds to expire
        :param info_dict: custom dict contains information, stored in memory, so can access quickly
        :type last_modified: str
        :type info_dict: dict or None
        :type obj: object
        """
        if expires <= 0 or obj_size > self.max_size_byte:
            return False

        self.delete(key)

        temp_file = tempfile.TemporaryFile(dir=self.cachedir.name)
        pickle.dump(obj, temp_file, protocol=pickle.HIGHEST_PROTOCOL)

        cache_item = (
            temp_file,  # 0 cache file object
            info_dict,  # 1 custom dict contains information
            int(time.time()),  # 2 added time (unix time)
            expires,  # 3 expires second
            _time_str_to_unix(last_modified),  # 4 last modified, unix time
        )
        self.items_dict[key] = cache_item
        return True

    def delete(self, key):
        if self._is_item_exist(key):
            self.items_dict[key][0].close()
            del self.items_dict[key]

    def check_all_expire(self, force_flush_all=False):
        keys_to_delete = []
        for item_key in self.items_dict:
            if self.is_expires(item_key) or force_flush_all:
                keys_to_delete.append(item_key)
        for key in keys_to_delete:
            self.delete(key)

    def is_cached(self, key):
        if not self._is_item_exist(key):
            return False
        if self.is_expires(key):
            self.delete(key)
            return False
        else:
            return True

    def get_obj(self, key):
        if self._is_item_exist(key):
            fp = self.items_dict[key][0]
            fp.seek(0)
            return pickle.load(fp)
        else:
            return None

    def get_info(self, key):
        if self._is_item_exist(key):
            return self.items_dict[key][1]
        else:
            return None

    def is_unchanged(self, key, last_modified=None):
        if not self._is_item_exist(key) or last_modified is None:
            return False
        else:
            ct = self.items_dict[key][4]
            if ct is None:
                return False
            elif ct == _time_str_to_unix(last_modified):
                return True

    def is_expires(self, key):
        item = self.items_dict[key]
        if time.time() > item[2] + item[3]:
            return True
        return False

    def _is_item_exist(self, key):
        return key in self.items_dict
