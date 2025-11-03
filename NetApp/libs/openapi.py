"""Wrapper for openapi based API."""

# openapi.py

import json
import logging
import requests
from typing import Any, Dict, List, Optional, Tuple, Union
from jsonschema import validate, ValidationError
from urllib.parse import urlencode


class APIWrapper:
    """Tiny OpenAPI wrapper client for path/param discovery + calling endpoints."""

    def __init__(
        self,
        api_json_file: str,
        base_url: str,
        auth_header: dict[str, str] | None = None,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
        base_api_path: str = "",
    ):
        """Initialize the class.

        :param api_json_file: the api json file to parse
        :type api_json_file: str
        :param base_url: the base url for the api
        :type base_url: str
        :param auth_header: the auth header to use
        :type auth_header: dict[str, str] | None
        :param timeout: the timeout value
        :type timeout: float
        :param session: an already existing session to use
        :type session: Optional[requests.Session]
        :param base_api_path: the base path of all api paths
        :type base_api_path: str
        """
        # Load the API spec
        with open(api_json_file, encoding="utf-8") as f:
            self.api_spec: Dict[str, Any] = json.load(f)

        self.base_api_path = base_api_path
        if not base_api_path:
            try:
                self.base_api_path = self.api_spec["basePath"]
            except KeyError:
                pass

        if not base_api_path:
            logging.warning(f"No base api path found for base_url: {base_url}")

        if not auth_header:
            auth_header = {}

        # Networking defaults
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        # Default headers (can be extended per request)
        default_headers = {
            "Content-Type": "application/json",
        }

        self.session.headers.update(default_headers)
        self.session.headers.update(auth_header)

    # -------------------------- Internal helpers ---------------------------

    def _get_operation(self, api_path: str, method: str) -> Dict[str, Any]:
        """Get the operation for an API path.

        :param api_path: the api path to use, such as /storage/assets
        :type api_path: str
        :param method: the method (get, put, etc)
        :type method: str
        :return: various info about the path and method
        :rtype: Dict[str, Any]
        """
        method = method.lower()
        path = self.api_spec["paths"].get(api_path, {})
        if not path:
            logging.error(f"_get_operation: did not find {api_path}")
        operation = path.get(method, {})
        if not operation:
            logging.error(f"_get_operation: could not find {operation} for {api_path}")
        return operation

    def _resolve_ref(self, ref: str) -> Any:
        """Resolve refs like '#/components/schemas/SomeSchema' against the api_spec."""
        if not ref.startswith("#"):
            return {}

        keys = ref.split("/")
        del keys[0]  # delete the #

        new_ref = self.api_spec
        for key in keys:
            new_ref = new_ref[key]
        return new_ref

    def _resolve_refs(self, schema: Any) -> Any:
        """Deep-resolve $ref in the provided schema dict/list/primitive."""
        if isinstance(schema, dict):
            if "$ref" in schema:
                target = self._resolve_ref(schema["$ref"])
                return self._resolve_refs(target)
            return {k: self._resolve_refs(v) for k, v in schema.items()}
        if isinstance(schema, list):
            return [self._resolve_refs(item) for item in schema]
        return schema

    def _format_path(
        self, path_template: str, path_params: Optional[Dict[str, Any]]
    ) -> str:
        """Replace placeholders like {id} in the path template with provided values.

        Also tolerates {{id}} just in case.
        """
        path = f"{self.base_api_path}{path_template}"
        if path_params:
            for k, v in path_params.items():
                path = path.replace(f"{{{k}}}", str(v))  # OpenAPI style
                path = path.replace(f"{{{{{k}}}}}", str(v))  # tolerate double braces
        return path

    def _extract_parameters(
        self, path_template: str, method: str
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Return (path_params, query_params) lists from the spec entry."""
        op = self._get_operation(path_template, method)
        params = op.get("parameters", []) or []
        path_params = [p for p in params if p.get("in") == "path"]
        query_params = [p for p in params if p.get("in") == "query"]
        return path_params, query_params

    def _get_request_schema(
        self, path_template: str, method: str
    ) -> Optional[Dict[str, Any]]:
        """Return the resolved JSON Schema dict for the request body if present.

        Only supports application/json for simplicity.
        """
        op = self._get_operation(path_template, method)

        content = (
            op.get("requestBody", {}).get("content", {}).get("application/json", {})
        )

        if not content:
            logging.error(
                f"_get_request_schema: no content for {path_template}:{method}"
            )

        schema = content.get("schema")

        if not schema:
            return None
        return self._resolve_refs(schema)

    def _build_sample_from_schema(self, schema: Dict[str, Any]) -> Any:
        """Heuristic sample generator for a JSON Schema object.

        Produces a minimal readable skeleton with placeholder values.
        """
        t = schema.get("type")
        if not t and "oneOf" in schema:
            return self._build_sample_from_schema(schema["oneOf"][0])
        if t == "object" or ("properties" in schema):
            props = schema.get("properties", {})
            required = set(schema.get("required", []))
            sample = {}
            for name, sub in props.items():
                sub = self._resolve_refs(sub)
                subtype = sub.get("type")
                enum = sub.get("enum")
                if enum:
                    value = enum[0]
                elif subtype == "string" or subtype is None:
                    value = f"<{name}>"
                elif subtype == "integer":
                    value = 0
                elif subtype == "number":
                    value = 0.0
                elif subtype == "boolean":
                    value = False
                elif subtype == "array":
                    value = [self._build_sample_from_schema(sub.get("items", {}))]
                elif subtype == "object":
                    value = self._build_sample_from_schema(sub)
                else:
                    value = None
                # include comments for required
                sample[name] = value
                # If description present, tack on a pseudo-comment key (human readable)
                if "description" in sub:
                    sample[f"__desc__{name}"] = sub["description"]
                if name in required:
                    sample[f"__required__{name}"] = True
            return sample
        if t == "array":
            return [self._build_sample_from_schema(schema.get("items", {}))]
        if t == "string":
            return "<string>"
        if t == "integer":
            return 0
        if t == "number":
            return 0.0
        if t == "boolean":
            return False
        # Default fallback:
        return {}

    # ------------------------------ Public API ------------------------------

    def list_endpoints(self) -> List[Tuple[str, str, Optional[str]]]:
        """Return list of (path, METHOD, summary) triples for quick discovery."""
        items: List[Tuple[str, str, Optional[str]]] = []
        for path in self.api_spec["paths"]:

            methods = self.api_spec["paths"].get(path, {})

            for m in methods.keys():
                if "summary" in methods[m]:
                    summary = methods[m].get("summary")
                    items.append((path, m.upper(), summary))
                elif "description" in methods[m]:
                    summary = methods[m].get("description")
                    if "." in summary:
                        summary = summary.split(".")[0]
                    items.append((path, m.upper(), summary))

        return items

    def get_request_schema_for_endpoint(
        self, path_template: str, method: str = "GET", human_readable: bool = True
    ) -> Optional[Union[Dict[str, Any], str]]:
        """Return the requestBody schema for the given endpoint.

        If human_readable=True, return a compact dict describing fields
        (type/required/enum/description),
        plus a 'sample' field with a minimal example body.
        """
        resolved = self._get_request_schema(path_template, method)

        if not resolved:
            return None

        if not human_readable:
            return resolved

        def describe(schema: Dict[str, Any]) -> Dict[str, Any]:
            info: Dict[str, Any] = {"type": schema.get("type", "object")}
            props = schema.get("properties", {})
            required = set(schema.get("required", []))
            fields: Dict[str, Any] = {}
            for name, sub in props.items():
                sub = self._resolve_refs(sub)
                fields[name] = {
                    "type": sub.get(
                        "type", "object" if "properties" in sub else "unknown"
                    ),
                    "required": name in required,
                    "description": sub.get("description"),
                }
                if "enum" in sub:
                    fields[name]["enum"] = list(sub["enum"])
            info["fields"] = fields
            info["sample"] = self._build_sample_from_schema(schema)
            return info

        return describe(resolved)

    def validate_body(
        self,
        path_template: str,
        method: str = "GET",
        body: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Validate 'body' against the endpoint's resolved schema (if any).

        If no body or no schema is present, returns True.
        """
        if body is None:
            return True
        schema = self._get_request_schema(path_template, method)
        if not schema:
            return True
        try:
            validate(instance=body, schema=schema)
            return True
        except ValidationError as e:
            logging.error(f"Request body validation error: {e.message}")
            return False

    def suggest_parameters(
        self, path_template: str, method: str = "GET"
    ) -> Dict[str, Any]:
        """Return a human-readable structure.

        - path_params: name, type, required, description
        - query_params: name, type, required, description
        - headers: default headers this client will send
        - body: sample JSON body (if any)
        - summary: brief endpoint summary from spec
        """
        method = method.upper()
        op = self._get_operation(path_template, method)
        path_params, query_params = self._extract_parameters(path_template, method)

        def simplify(param: Dict[str, Any]) -> Dict[str, Any]:
            sch = param.get("schema", {})
            return {
                "name": param.get("name"),
                "in": param.get("in"),
                "type": sch.get("type"),
                "required": param.get("required", False),
                "description": param.get("description"),
                "enum": sch.get("enum"),
                "format": sch.get("format"),
            }

        path_list = [simplify(p) for p in path_params]
        query_list = [simplify(p) for p in query_params]

        schema = self._get_request_schema(path_template, method)
        body_sample = self._build_sample_from_schema(schema) if schema else None

        return {
            "path": path_template,
            "method": method,
            "summary": op.get("summary"),
            "path_params": path_list,
            "query_params": query_list,
            "headers": dict(self.session.headers),
            "body_sample": body_sample,
        }

    def call_endpoint(
        self,
        path_template: str,
        method: str = "GET",
        path_params: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        """Make the HTTP call.

        Validates body (if schema exists) and raises for HTTP errors.
        """
        method = method.upper()
        # path_template = f"{self.base_api_path}{path_template}"

        # Validate body against the schema for the *template* path
        if not self.validate_body(path_template, method, body):
            raise ValueError("Request body validation failed.")

        # Build URL (formatting path placeholders)
        path = self._format_path(path_template, path_params)
        logging.debug(f"API Path: {path}")
        url = f"{self.base_url}{path}"
        logging.debug(f"API URL: {url}")

        # Encode query params
        if query_params:
            url += "?" + urlencode(query_params, doseq=True)

        # Merge headers
        headers = dict(self.session.headers)
        if additional_headers:
            headers.update(additional_headers)

        logging.debug(f"Calling {method} {url} {headers}")
        resp = self.session.request(
            method, url, json=body, headers=headers, timeout=self.timeout, verify=False
        )
        logging.debug(f"Response Status Code: {resp.status_code}")
        resp.raise_for_status()

        # Try JSON, else return text
        try:
            logging.debug(f"Response Text: {resp.text}")
            return resp.json()
        except ValueError:
            return resp.text
