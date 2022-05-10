import traceback


class BaseAPI:
    # TODO: 对接第三方接口设计
    api_name = ""
    api_url_dict = {}
    domain = ""
    headers = {
        "content-type": "application/json",
    }
    req_kwargs = {
        "headers": headers,
        "timeout": 10,
    }

    @classmethod
    def _get_response(cls, **kwargs):
        data = kwargs
        func_name = traceback.extract_stack()[-2][2]
        try:
            api_info = cls.api_url_dict[func_name]
        except KeyError as e:
            raise NotImplementedError(f"{cls.api_name}API: {e.args[0]} is not implemented!")
        method = api_info["method"]
        url = cls.domain + api_info["url"]

        # 超时
        try:
            if requests.post == method:
                response = method(url, json.dumps(data), **cls.req_kwargs)
            else:
                response = method(url, data, **cls.req_kwargs)
        except ReadTimeout:
            logger.error(f"XEV error: 请求超时{func_name},{data}, {cls.req_kwargs} ")
            raise ValidationError(f"{func_name} timeout")
        except Exception:
            raise ValidationError(f"{func_name} error")

        # 解析json
        try:
            response = json.loads(response.content.strip())
        except Exception as e:
            logger.error(f"XEV error: 第三方对接出现错误{e}，{response.content}")
            raise ValidationError(f"{func_name} json data parse failure")

        # 返回接口出错
        if response.get("code") != "000000":
            message = response.get("message")
            logger.error(f"XEV error: response: {response} url: {url} data: {data} error: {message}")
            raise ValidationError(f"{func_name} {message}")
        logger.info(f"XEV success: response: {response} url: {url} data: {data}")
        return response