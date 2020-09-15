#!/usr/bin/env python
#coding=utf-8

import os
zone = ''
access_key_id = ''
secret_access_key = ''
# role: 将要制作的节点角色, instance_id: 制作镜像使用的主机, line: mustache 文件中要修改镜像的行号, private_ip: 主机 ip
instance_ids = [
    {'role': 'node', 'instance_id': 'i-xxx','line': [65, 151, 212], 'private_ip':'172.22.4.8'},
    ]
mustache_path = os.getcwd()+'/app/cluster.json.mustache'

