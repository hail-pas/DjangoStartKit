import logging

import yaml
from jinja2 import Template
from kubernetes import client
from kubernetes import config as kube_config

# Configs can be set in Configuration class directly or using helper utility
from conf.config import local_configs

logger = logging.getLogger(__name__)

JOB_TEMPLATE = "tasks/yaml_template/job_template.yaml"
CRONJOB_TEMPLATE = "tasks/yaml_template/cronjob_template.yaml"


class KubeSetting(object):
    """模版替换数据"""

    def __init__(self, name, command, namespace="", image="", pvc_name="", schedule="*/5 * * * *"):
        if namespace:
            self._namespace = namespace
        else:
            self._namespace = local_configs.KUBE_NAMESPACE
        if image:
            self._image = image
        else:
            self._image = local_configs.KUBE_IMAGE
        if pvc_name:
            self._pvc_name = pvc_name
        else:
            self._pvc_name = local_configs.KUBE_PVC_NAME
        self._name = name
        self._command = command
        self._schedule = '"{}"'.format(schedule)

    @property
    def namespace(self):
        return self._namespace

    @namespace.setter
    def namespace(self, value):
        self._namespace = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        value = value.replace("_", "-")
        self._name = value

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, value):
        self._image = value

    @property
    def command(self):
        return self._command

    @command.setter
    def command(self, value):
        self._command = value

    @property
    def schedule(self):
        return self._schedule

    @schedule.setter
    def schedule(self, value):
        self._schedule = value

    @property
    def get_dict(self):
        return {
            "namespace": self._namespace,
            "name": self._name,
            "image": self._image,
            "command": self._command,
            "schedule": self._schedule,
            "pvc_name": self._pvc_name,
        }


class KubernetesAPI(object):
    """k8s 调用API"""

    def __init__(self, config_file=None):
        self.configuration = client.Configuration()
        self.configuration.verify_ssl = False
        try:
            kube_config.load_kube_config(config_file=config_file, client_configuration=self.configuration)
        except Exception as e:
            logger.warning("Get Kubernetes Config Fail!, {}".format(e))
            self.configuration.host = local_configs.KUBE_HOST
            with open("/var/run/secrets/kubernetes.io/serviceaccount/token", "r") as f:
                self.configuration.api_key["authorization"] = "Bearer %s" % f.read()

    @staticmethod
    def generate_body(yaml_path, kube_setting):
        """
        生成k8s配置body

        :param yaml_path: 模板文件路径
        :param kube_setting: 具体配置， 不能为空
        :type yaml_path str
        :type kube_setting KubeSetting
        :return:
        """
        with open(yaml_path, "r") as f:
            template = Template(f.read())
        try:
            temp_yaml = template.render(**kube_setting.get_dict)
            body = yaml.safe_load(temp_yaml)
        except Exception as e:
            logger.error("Generate Body Error : {}".format(e))
            body = None
        return body

    def create_job(self, kube_setting):
        """
        创建任务

        :param kube_setting: 具体配置，不能为空
        :type kube_setting KubeSetting
        :return:
        """
        if self.configuration:
            api_client = client.ApiClient(self.configuration)
            v1 = client.BatchV1Api(api_client)
        else:
            v1 = client.BatchV1Api()
        body = self.generate_body(JOB_TEMPLATE, kube_setting)
        if body is None:
            raise Exception("Create Job Fail! Get Body Error!")
        logger.info(body)
        try:
            response = v1.create_namespaced_job(kube_setting.namespace, body)
        except Exception as e:
            logger.exception(e)
            raise e
        return response

    def create_cron_job(self, kube_setting, **kwargs):
        """
        创建定时任务

        :param kube_setting: 具体配置， 不能为空
        :type kube_setting KubeSetting
        :return:
        """
        if self.configuration:
            api_client = client.ApiClient(self.configuration)
            v1 = client.BatchV1beta1Api(api_client)
        else:
            v1 = client.BatchV1beta1Api()
        body = self.generate_body(CRONJOB_TEMPLATE, kube_setting)
        if body is None:
            raise Exception("Create Cron Job Fail! Get Body Error!")
        logger.info(body)
        try:
            response = v1.create_namespaced_cron_job(kube_setting.namespace, body, **kwargs)
        except Exception as e:
            logger.exception(e)
            raise e
        return response
