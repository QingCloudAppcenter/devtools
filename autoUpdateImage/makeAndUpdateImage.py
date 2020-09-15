#!/usr/bin/env python
# coding=utf-8
from qingcloud.iaas.connection import APIConnection
import subprocess
import time
import datetime
import logging
import re
import threading
import config

"""
该脚本主要用于已部署环境的节点的制作镜像、将镜像id写入mustache文件，并重启节点
"""


class Error(Exception):
    pass


logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y/%m/%d %H:%M:%S',
    level=logging.ERROR)

conn = APIConnection(
    qy_access_key_id=config.access_key_id,
    qy_secret_access_key=config.secret_access_key,
    zone=config.zone,
    host="api.qingcloud.com", port=443, protocol="https"
)


def exec_cmd(command, timeout=20):
    start = datetime.datetime.now()
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while process.poll() is None:
        time.sleep(0.1)
        now = datetime.datetime.now()
        if timeout is not None and (now - start).seconds > timeout:
            os.kill(process.pid, signal.SIGKILL)
            os.waitpid(-1, os.WNOHANG)
            logging.error(
                "Executing [%s] TIMOUT, killed the process" % command)


def get_instance(instance_id):
    ret = conn.describe_instances(instances=[instance_id])
    logging.debug("describe_instance的结果：{}".format(ret))
    instances = ret['instance_set']
    if len(instances) != 1:
        raise Error
    return instances[0]


def capture_instance(instance_id):
    # 获取image_id
    ret = conn.capture_instance(instance=instance_id)
    logging.debug("capture_instance的结果为{}".format(ret))
    logging.info("ret is {}".format(ret))
    return ret['image_id']


def get_image(image_id):
    # 获得镜像的 id
    ret = conn.describe_images(images=[image_id])
    logging.debug("describe_images的结果为{}".format(ret))
    images = ret['image_set']
    if len(images) != 1:
        raise Error
    return images[0]


def modify_image_tag(image_id, role):
    conn.modify_image_attributes(image=image_id, image_name=role)


def start_instance(instance_id):
    conn.start_instances(instances=[instance_id])
    return


def stop_instance(private_ip):
    # 关闭节点
    return exec_cmd(
        "ssh -o ConnectTimeout=10 root@%s 'shutdown -h now'" % private_ip)


def replace_image(image_id, line_num):
    # 替换掉mustache文件中的镜像名
    f = open(config.mustache_path, 'r')
    content = f.readlines()
    for line in line_num:
        content[line-1] = re.sub(
            'img-[A-Za-z0-9]{7,9}', image_id, content[line-1])
    open(config.mustache_path, 'w').write(''.join(content))


def runForInstance(instance_info):
    role = instance_info["role"]
    instance_id = instance_info["instance_id"]
    line = instance_info["line"]
    private_ip = instance_info["private_ip"]

    logging.info('stop instance [%s]', instance_id)
    stop_instance(private_ip)
    logging.info(
        'stop instance [%s] success, get instance status', instance_id)

    while get_instance(instance_id)['status'] != 'stopped':
        logging.info(
            'instance [%s] status is not stopped, try again', instance_id)
        time.sleep(20)

    logging.info('instance [%s] status is stopped, capture', instance_id)
    image_id = capture_instance(instance_id)
    logging.info('start capture instance [%s]', instance_id)
    modify_image_tag(image_id, role)
    while get_image(image_id)['status'] != 'available':
        logging.info('instance [%s] image [%s] is not available', instance_id,
                     image_id)
        time.sleep(20)

    logging.info('replace mustache image id to [%s]', image_id)
    if lock.acquire():
        try:
            replace_image(image_id, line)
        finally:
            lock.release()

    logging.info('instance [%s] image [%s] capture success, start instance',
                 instance_id, image_id)
    start_instance(instance_id)

    while get_instance(instance_id)['status'] != 'running':
        logging.info('instance [%s] is not running, try again', instance_id)
        time.sleep(20)

    logging.info('capture_instance [%s] success image_id [%s]', instance_id,
                 image_id)


if __name__ == "__main__":
    threads = []
    lock = threading.Lock()
    for instance_info in config.instance_ids:
        threads.append(threading.Thread(
            target=runForInstance, args=(instance_info,), name=instance_info["role"]))
    for thread in threads:
        print(thread.name)
        thread.start()
    for thread in threads:
        print(thread.name)
        thread.join()

