import datetime
import json
from copy import deepcopy

import absurdia
from absurdia import api_requestor, util


def _compute_diff(current, previous):
    if isinstance(current, dict):
        previous = previous or {}
        diff = current.copy()
        for key in set(previous.keys()) - set(diff.keys()):
            diff[key] = ""
        return diff
    return current if current is not None else ""


def _serialize_list(array, previous):
    array = array or []
    previous = previous or []
    params = {}

    for i, v in enumerate(array):
        previous_item = previous[i] if len(previous) > i else None
        if hasattr(v, "serialize"):
            params[str(i)] = v.serialize(previous_item)
        else:
            params[str(i)] = _compute_diff(v, previous_item)

    return params


class AbsurdiaObject(dict):
    class ReprJSONEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return api_requestor._encode_datetime(obj)
            return super(AbsurdiaObject.ReprJSONEncoder, self).default(obj)

    def __init__(
        self,
        id=None,
        agent_token=None,
        absurdia_version=None,
        absurdia_account=None,
        last_response=None,
        **params
    ):
        super(AbsurdiaObject, self).__init__()

        self._unsaved_values = set()
        self._transient_values = set()
        self._last_response = last_response

        self._retrieve_params = params
        self._previous = None

        object.__setattr__(self, "agent_token", agent_token)
        object.__setattr__(self, "absurdia_version", absurdia_version)
        object.__setattr__(self, "absurdia_account", absurdia_account)

        if id:
            self["id"] = id

    @property
    def last_response(self):
        return self._last_response

    def update(self, update_dict):
        for k in update_dict:
            self._unsaved_values.add(k)

        return super(AbsurdiaObject, self).update(update_dict)

    def __setattr__(self, k, v):
        if k[0] == "_" or k in self.__dict__:
            return super(AbsurdiaObject, self).__setattr__(k, v)

        self[k] = v
        return None

    def __getattr__(self, k):
        if k[0] == "_":
            raise AttributeError(k)

        try:
            return self[k]
        except KeyError as err:
            raise AttributeError(*err.args)

    def __delattr__(self, k):
        if k[0] == "_" or k in self.__dict__:
            return super(AbsurdiaObject, self).__delattr__(k)
        else:
            del self[k]

    def __setitem__(self, k, v):
        if v == "":
            raise ValueError(
                "You cannot set %s to an empty string on this object. "
                "The empty string is treated specially in our requests. "
                "If you'd like to delete the property using the save() method on this object, you may set %s.%s = None. "
                "Alternatively, you can pass %s='' to delete the property when using a resource method such as modify()."
                % (k, str(self), k, k)
            )

        # Allows for unpickling in Python 3.x
        if not hasattr(self, "_unsaved_values"):
            self._unsaved_values = set()

        self._unsaved_values.add(k)

        super(AbsurdiaObject, self).__setitem__(k, v)

    def __getitem__(self, k):
        try:
            return super(AbsurdiaObject, self).__getitem__(k)
        except KeyError as err:
            if k in self._transient_values:
                raise KeyError(
                    "%r.  HINT: The %r attribute was set in the past."
                    "It was then wiped when refreshing the object with "
                    "the result returned by Stripe's API, probably as a "
                    "result of a save().  The attributes currently "
                    "available on this object are: %s"
                    % (k, k, ", ".join(list(self.keys())))
                )
            else:
                raise err

    def __delitem__(self, k):
        super(AbsurdiaObject, self).__delitem__(k)

        # Allows for unpickling in Python 3.x
        if hasattr(self, "_unsaved_values") and k in self._unsaved_values:
            self._unsaved_values.remove(k)

    # Custom unpickling method that uses `update` to update the dictionary
    # without calling __setitem__, which would fail if any value is an empty
    # string
    def __setstate__(self, state):
        self.update(state)

    # Custom pickling method to ensure the instance is pickled as a custom
    # class and not as a dict, otherwise __setstate__ would not be called when
    # unpickling.
    def __reduce__(self):
        reduce_value = (
            type(self),  # callable
            (  # args
                self.get("id", None),
                self.agent_token,
                self.absurdia_version,
                self.absurdia_account,
            ),
            dict(self),  # state
        )
        return reduce_value

    @classmethod
    def construct_from(
        cls,
        values,
        agent_token,
        absurdia_version=None,
        absurdia_account=None,
        last_response=None,
    ):
        instance = cls(
            values.get("id"),
            agent_token=agent_token,
            absurdia_version=absurdia_version,
            absurdia_account=absurdia_account,
            last_response=last_response,
        )
        instance.refresh_from(
            values,
            agent_token=agent_token,
            absurdia_version=absurdia_version,
            absurdia_account=absurdia_account,
            last_response=last_response,
        )
        return instance

    def refresh_from(
        self,
        values,
        agent_token=None,
        partial=False,
        absurdia_version=None,
        absurdia_account=None,
        last_response=None,
    ):
        self.agent_token = agent_token or getattr(values, "agent_token", None)
        self.absurdia_version = absurdia_version or getattr(
            values, "absurdia_version", None
        )
        self.absurdia_account = absurdia_account or getattr(
            values, "absurdia_account", None
        )
        self._last_response = last_response or getattr(
            values, "_last_response", None
        )

        # Wipe old state before setting new.  This is useful for e.g.
        # updating a customer, where there is no persistent card
        # parameter.  Mark those values which don't persist as transient
        if partial:
            self._unsaved_values = self._unsaved_values - set(values)
        else:
            removed = set(self.keys()) - set(values)
            self._transient_values = self._transient_values | removed
            self._unsaved_values = set()
            self.clear()

        self._transient_values = self._transient_values - set(values)

        for k, v in values.items():
            super(AbsurdiaObject, self).__setitem__(
                k,
                util.convert_to_absurdia_object(
                    v, agent_token, absurdia_version, absurdia_account
                ),
            )

        self._previous = values

    @classmethod
    def api_base(cls):
        return absurdia.api_base

    def request(self, method, url, params=None, headers=None):
        if params is None:
            params = self._retrieve_params
        requestor = api_requestor.APIRequestor(
            token=self.agent_token,
            api_version=self.absurdia_version,
            account=self.absurdia_account,
        )
        response = requestor.request(method, url, params, headers)

        return util.convert_to_absurdia_object(
            response, self.agent_token, self.absurdia_version, self.absurdia_account
        )

    def request_stream(self, method, url, params=None, headers=None):
        if params is None:
            params = self._retrieve_params
        requestor = api_requestor.APIRequestor(
            agent_token=self.agent_token,
            api_base=self.api_base(),
            api_version=self.absurdia_version,
            account=self.absurdia_account,
        )
        response, _ = requestor.request_stream(method, url, params, headers)

        return response

    def __repr__(self):
        ident_parts = [type(self).__name__]

        if isinstance(self.get("object"), str):
            ident_parts.append(self.get("object"))

        if isinstance(self.get("id"), str):
            ident_parts.append("id=%s" % (self.get("id"),))

        unicode_repr = "<%s at %s> JSON: %s" % (
            " ".join(ident_parts),
            hex(id(self)),
            str(self),
        )

        return unicode_repr

    def __str__(self):
        return json.dumps(
            self.to_dict_recursive(),
            sort_keys=True,
            indent=2,
            cls=self.ReprJSONEncoder,
        )

    def to_dict(self):
        return dict(self)

    def to_dict_recursive(self):
        def maybe_to_dict_recursive(value):
            if value is None:
                return None
            elif isinstance(value, AbsurdiaObject):
                return value.to_dict_recursive()
            else:
                return value

        return {
            key: list(map(maybe_to_dict_recursive, value))
            if isinstance(value, list)
            else maybe_to_dict_recursive(value)
            for key, value in dict(self).items()
        }

    @property
    def id(self):
        return self.id

    def serialize(self, previous):
        params = {}
        unsaved_keys = self._unsaved_values or set()
        previous = previous or self._previous or {}

        for k, v in iter(self):
            if k == "id" or (isinstance(k, str) and k.startswith("_")):
                continue
            elif isinstance(v, absurdia.api_resources.abstract.APIResource):
                continue
            elif hasattr(v, "serialize"):
                child = v.serialize(previous.get(k, None))
                if child != {}:
                    params[k] = child
            elif k in unsaved_keys:
                params[k] = _compute_diff(v, previous.get(k, None))
            elif k == "additional_owners" and v is not None:
                params[k] = _serialize_list(v, previous.get(k, None))

        return params

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __copy__(self):
        copied = AbsurdiaObject(
            self.get("id"),
            self.agent_token,
            absurdia_version=self.absurdia_version,
            absurdia_account=self.absurdia_account,
        )

        copied._retrieve_params = self._retrieve_params

        for k, v in iter(self):
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(AbsurdiaObject, copied).__setitem__(k, v)

        return copied

    # This class overrides __setitem__ to throw exceptions on inputs that it
    # doesn't like. This can cause problems when we try to copy an object
    # wholesale because some data that's returned from the API may not be valid
    # if it was set to be set manually. Here we override the class' copy
    # arguments so that we can bypass these possible exceptions on __setitem__.
    def __deepcopy__(self, memo):
        copied = self.__copy__()
        memo[id(self)] = copied

        for k, v in iter(self):
            # Call parent's __setitem__ to avoid checks that we've added in the
            # overridden version that can throw exceptions.
            super(AbsurdiaObject, copied).__setitem__(k, deepcopy(v, memo))

        return copied