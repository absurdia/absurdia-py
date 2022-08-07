from urllib.parse import quote_plus
from absurdia import api_requestor, error, util
from absurdia.absurdia_object import AbsurdiaObject

class APIResource(AbsurdiaObject):
    @classmethod
    def retrieve(cls, id=None, agent_token=None, **params):
        instance = cls(id, agent_token, **params)
        instance.refresh()
        return instance

    def refresh(self):
        id = self.get("id")
        if isinstance(id, str):
            self.refresh_from(self.request("get", self.class_url() + "/{id}".format(id=id)))
        return self

    @classmethod
    def class_url(cls):
        if cls == APIResource:
            raise NotImplementedError(
                "APIResource is an abstract class.  You should perform "
                "actions on its subclasses (e.g. agent, fund)"
            )
        # Namespaces are separated in object names with periods (.) and in URLs
        # with forward slashes (/), so replace the former with the latter.
        base = cls.OBJECT_NAME.replace(".", "/")
        return "/v1/%ss" % (base,)

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    @classmethod
    def _static_request(
        cls,
        method_,
        url_,
        agent_token=None,
        idempotency_key=None,
        absurdia_version=None,
        absurdia_account=None,
        **params
    ):
        requestor = api_requestor.APIRequestor(
            agent_token, api_version=absurdia_version, account=absurdia_account
        )
        headers = util.populate_headers(idempotency_key)
        response = requestor.request(method_, url_, params, headers)
        return util.convert_to_absurdia_object(
            response, agent_token, absurdia_version, absurdia_account
        )

    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    @classmethod
    def _static_request_stream(
        cls,
        method_,
        url_,
        agent_token=None,
        idempotency_key=None,
        absurdia_version=None,
        absurdia_account=None,
        **params
    ):
        requestor = api_requestor.APIRequestor(
            agent_token, api_version=absurdia_version, account=absurdia_account
        )
        headers = util.populate_headers(idempotency_key)
        response = requestor.request_stream(method_, url_, params, headers)
        return response
    
    # The `method_` and `url_` arguments are suffixed with an underscore to
    # avoid conflicting with actual request parameters in `params`.
    def _request(
        self,
        method_,
        url_,
        api_key=None,
        idempotency_key=None,
        absurdia_version=None,
        absurdia_account=None,
        headers=None,
        params=None,
    ):
        obj = AbsurdiaObject.request(
            self,
            method_,
            url_,
            params,
            headers
        )

        if type(self) is type(obj):
            self.refresh_from(obj)
            return self
        else:
            return obj


def custom_method(name, http_verb, http_path=None, is_streaming=False):
    if http_verb not in ["get", "post", "delete", "patch", "put"]:
        raise ValueError(
            "Invalid http_verb: %s. Must be one of 'get', 'post', 'patch', 'put' or 'delete'"
            % http_verb
        )
    if http_path is None:
        http_path = name

    def wrapper(cls):
        def custom_method_request(cls, sid, **params):
            url = "%s/%s/%s" % (
                cls.class_url(),
                quote_plus(util.utf8(sid)),
                http_path,
            )
            obj = cls._static_request(http_verb, url, **params)

            # For list objects, we have to attach the parameters so that they
            # can be referenced in auto-pagination and ensure consistency.
            if "object" in obj and obj.object == "list":
                obj._retrieve_params = params

            return obj

        def custom_method_request_stream(cls, sid, **params):
            url = "%s/%s/%s" % (
                cls.class_url(),
                quote_plus(util.utf8(sid)),
                http_path,
            )
            return cls._static_request_stream(http_verb, url, **params)

        if is_streaming:
            class_method_impl = classmethod(custom_method_request_stream)
        else:
            class_method_impl = classmethod(custom_method_request)

        existing_method = getattr(cls, name, None)
        if existing_method is None:
            setattr(cls, name, class_method_impl)
        else:
            # If a method with the same name we want to use already exists on
            # the class, we assume it's an instance method. In this case, the
            # new class method is prefixed with `_cls_`, and the original
            # instance method is decorated with `util.class_method_variant` so
            # that the new class method is called when the original method is
            # called as a class method.
            setattr(cls, "_cls_" + name, class_method_impl)
            instance_method = util.class_method_variant("_cls_" + name)(
                existing_method
            )
            setattr(cls, name, instance_method)

        return cls

    return wrapper

class ListableAPIResource(APIResource):
    @classmethod
    def auto_paging_iter(cls, *args, **params):
        return cls.list(*args, **params).auto_paging_iter()

    @classmethod
    def list(
        cls, agent_token=None, absurdia_account=None, **params
    ):
        requestor = api_requestor.APIRequestor(agent_token, account=absurdia_account,)
        url = cls.class_url()
        response = requestor.request("get", url, params)
        absurdia_object = util.convert_to_absurdia_object(response, agent_token, absurdia_account=absurdia_account)
        return absurdia_object