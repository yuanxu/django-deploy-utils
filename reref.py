# coding=utf-8
#!/bin/bash
# 本程序的目的是在前端发布时，自动将.html文件中引用到的静态文件文件更新为:{原文件名}_hash.{ext}
# 参考:
#   http://www.infoq.com/cn/articles/front-end-engineering-and-performance-optimization-part1

import hashlib
import re
import shutil
import os
import importlib
import sys
from bs4 import BeautifulSoup
import codecs
import logging


settings = None   # django Settings文件

replace_re = re.compile('({{\s*STATIC_URL\s*}})')

logger = logging.getLogger()

DEBUG = True


def _copy_hashed_file(origin_file_name):
    '''
    复制文件的hash版本
    @return 新文件的文件名(不含路径信息)
    '''
    hash_code = ''
    with open(origin_file_name, 'r') as f:
        hash_code = hashlib.sha1(f.read()).hexdigest()
    dir_name = os.path.dirname(origin_file_name)
    file_name, extname = os.path.splitext(origin_file_name)
    file_name = origin_file_name[len(dir_name) + 1:len(origin_file_name) - len(extname)]
    t_filename = '%s/%s_%s%s' % (dir_name, file_name, hash_code[0:7], extname)
    shutil.copyfile(origin_file_name, t_filename)
    return t_filename


def _load_settings(path):
    sys.path.append(path)
    global settings
    settings = importlib.import_module('settings')


def _ref_file(filename):
    soup = BeautifulSoup(codecs.open(filename, encoding='UTF-8'), 'html5lib')

    def _ref_node(node_name, attr_name, **kwargs):
        '''
        处理相应节点
        '''
        for tag in soup.find_all(node_name, **kwargs):
            attr_value = tag[attr_name] if attr_name in tag.attrs else None
            if attr_value and not (attr_value.startswith('http') or attr_value.startswith('//')):
                tag[attr_name] = _gen_new_ref(attr_value)

    def _gen_new_ref(v):
        '''
        生成新的文件，并返回文件名
        '''
        if not 'STATIC_URL' in v:
            return v
        for path in settings.STATICFILES_DIRS:
            map_path = r'%s/' % path
            old_file = replace_re.sub(map_path, v)
            if not os.path.exists(old_file):
                continue

            new_file = _copy_hashed_file(old_file)
            new_file = new_file.replace(map_path, '{{ STATIC_URL }}')
            logger.info(u'源文件:%s 目标文件:%s' % (old_file, new_file))
            return new_file

    _ref_node('script', 'src')
    _ref_node('link', 'href', rel='stylesheet')

    body = ''.join(unicode(l) for l in soup.body.contents)  # 去掉自动增加的不必要的<html><body>等标签
    if not DEBUG:
        f = codecs.open(filename, 'r+', encoding='UTF-8')
        f.write(body)
        f.close()
    else:
        print body


def scan_ref():
    def _scan_ref(file_or_dir):
        if os.path.isdir(file_or_dir):
            for f in os.listdir(file_or_dir):
                f = os.path.join(file_or_dir, f)
                logger.info(u'进入目录:%s' % f)
                _scan_ref(f)
                logging.info('\r\n\r\n')
        else:
            logger.info(u'开始处理文件:%s' % file_or_dir)
            _ref_file(file_or_dir)

    for d in settings.TEMPLATE_DIRS:
        for f in os.listdir(d):
            _scan_ref(os.path.join(d, f))

    logger.info(u'\r\n\r\n处理完成.')


if __name__ == '__main__':
    pass
