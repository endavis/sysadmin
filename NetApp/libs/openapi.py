# openapi.py
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from jsonschema import validate, ValidationError
from urllib.parse import urlencode


class APIWrapper:
    """
    Tiny OpenAPI wrapper client for path/param discovery + calling endpoints.
    """

    def __init__(
        self,
        api_spec_path: str,
        schema_path: Optional[str],
        base_url: str,
        auth_token: Optional[str] = None,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ):
        # Load the API spec (paths as keys)
        with open(api_spec_path, encoding="utf-8") as f:
            self.api_spec: Dict[str, Any] = json.load(f)

        # Load/normalize schemas (flat name -> schema dict)
        self.schemas: Dict[str, Any] = {}
        if schema_path:
            with open(schema_path, encoding="utf-8") as f:
                raw = json.load(f)
            # If schema.json is already flat: {"AnnotationDefinition": {...}, ...}
            # use it as-is. If it's {"components": {"schemas": {...}}}, flatten it.
            if "components" in raw and isinstance(raw["components"], dict) and "schemas" in raw["components"]:
                self.schemas = raw["components"]["schemas"]
            else:
                self.schemas = raw

        # Keep a list of template paths for clarity
        self.paths: List[str] = list(self.api_spec.keys())

        # Networking defaults
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.session = session or requests.Session()
        # Default headers (can be extended per request)
        default_headers = {
            "Content-Type": "application/json",
        }
        # Add Cloud Insights API key header if provided
        if self.auth_token:
            default_headers["X-CloudInsights-ApiKey"] = self.auth_token
        self.session.headers.update(default_headers)

    # -------------------------- Internal helpers ---------------------------

    def _get_operation(self, path_template: str, method: str) -> Dict[str, Any]:
        method = method.lower()
        return self.api_spec.get(path_template, {}).get(method, {})  # type: ignore[index]

    def _resolve_ref(self, ref: str) -> Any:
        """
        Resolve refs like '#/components/schemas/SomeSchema' against self.schemas,
        which is a flat dict mapping 'SomeSchema' -> schema dict.
        """
        if not ref.startswith("#/components/schemas/"):
            return {}
        key = ref.split("/")[-1]
        return self.schemas.get(key, {})

    def _resolve_refs(self, schema: Any) -> Any:
        """
        Deep-resolve $ref in the provided schema dict/list/primitive.
        """
        if isinstance(schema, dict):
            if "$ref" in schema:
                target = self._resolve_ref(schema["$ref"])
                return self._resolve_refs(target)
            return {k: self._resolve_refs(v) for k, v in schema.items()}
        if isinstance(schema, list):
            return [self._resolve_refs(item) for item in schema]
        return schema

    def _format_path(self, path_template: str, path_params: Optional[Dict[str, Any]]) -> str:
        """
        Replace placeholders like {id} in the path template with provided values.
        Also tolerates {{id}} just in case.
        """
        path = path_template
        if path_params:
            for k, v in path_params.items():
                path = path.replace(f"{{{k}}}", str(v))  # OpenAPI style
                path = path.replace(f"{{{{{k}}}}}", str(v))  # tolerate double braces
        return path

    def _extract_parameters(self, path_template: str, method: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Return (path_params, query_params) lists from the spec entry.
        """
        op = self._get_operation(path_template, method)
        params = op.get("parameters", []) or []
        path_params = [p for p in params if p.get("in") == "path"]
        query_params = [p for p in params if p.get("in") == "query"]
        return path_params, query_params

    def _get_request_schema(self, path_template: str, method: str) -> Optional[Dict[str, Any]]:
        """
        Return the resolved JSON Schema dict for the request body if present.
        Only supports application/json for simplicity.
        """
        op = self._get_operation(path_template, method)
        content = (
            op.get("requestBody", {})
              .get("content", {})
              .get("application/json", {})
        )
        schema = content.get("schema")
        if not schema:
            return None
        return self._resolve_refs(schema)

    def _build_sample_from_schema(self, schema: Dict[str, Any]) -> Any:
        """
        Heuristic sample generator for a JSON Schema object.
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
        """
        Return list of (path, METHOD, summary) triples for quick discovery.
        """
        items: List[Tuple[str, str, Optional[str]]] = []
        for path in self.paths:
            methods = self.api_spec.get(path, {})
            for m in methods.keys():
                summary = methods[m].get("summary")
                items.append((path, m.upper(), summary))
        return items

    def get_schema_for_endpoint(self, path_template: str, method: str, human_readable: bool = True) -> Optional[Union[Dict[str, Any], str]]:
        """
        Return the requestBody schema for the given endpoint.
        If human_readable=True, return a compact dict describing fields (type/required/enum/description),
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
                    "type": sub.get("type", "object" if "properties" in sub else "unknown"),
                    "required": name in required,
                    "description": sub.get("description"),
                }
                if "enum" in sub:
                    fields[name]["enum"] = list(sub["enum"])
            info["fields"] = fields
            info["sample"] = self._build_sample_from_schema(schema)
            return info

        return describe(resolved)

    def validate_body(self, path_template: str, method: str, body: Optional[Dict[str, Any]]) -> bool:
        """
        Validate 'body' against the endpoint's resolved schema (if any).
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

    def suggest_parameters(self, path_template: str, method: str = "GET") -> Dict[str, Any]:
        """
        Return a human-readable structure with:
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
        """
        Make the HTTP call. Validates body (if schema exists) and raises for HTTP errors.
        """
        method = method.upper()

        # Validate body against the schema for the *template* path
        if not self.validate_body(path_template, method, body):
            raise ValueError("Request body validation failed.")

        # Build URL (formatting path placeholders)
        path = self._format_path(path_template, path_params)
        url = f"{self.base_url}{path}"

        # Encode query params
        if query_params:
            url += "?" + urlencode(query_params, doseq=True)

        # Merge headers
        headers = dict(self.session.headers)
        if additional_headers:
            headers.update(additional_headers)

        logging.debug(f"Calling {method} {url}")
        resp = self.session.request(method, url, json=body, headers=headers, timeout=self.timeout)
        logging.debug(f"Response: {resp.status_code}")
        resp.raise_for_status()

        # Try JSON, else return text
        try:
            return resp.json()
        except ValueError:
            return resp.text