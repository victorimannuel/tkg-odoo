import json
import logging
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


class FathomApiClient:
    def __init__(self, env):
        self.env = env
        config = env['ir.config_parameter'].sudo()
        self.base_url = config.get_param('fathom_odoo_connector.api_base_url') or 'https://api.fathomhq.com/v1'
        self.api_key = config.get_param('fathom_odoo_connector.api_key')
        self.timeout = 30

    def _headers(self):
        if not self.api_key:
            raise UserError('Fathom API key is not configured.')
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _session(self):
        session = requests.Session()
        retry = Retry(
            total=3,
            read=3,
            connect=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def request(self, method, path, payload=None, params=None):
        url = urljoin(self.base_url.rstrip('/') + '/', path.lstrip('/'))
        try:
            response = self._session().request(
                method=method,
                url=url,
                headers=self._headers(),
                params=params,
                data=json.dumps(payload) if payload else None,
                timeout=self.timeout,
            )
            response.raise_for_status()
            if not response.text:
                return {}, response.status_code
            return response.json(), response.status_code
        except requests.RequestException as exc:
            _logger.exception('Fathom API request failed: %s %s', method, path)
            raise UserError(f'Fathom API request failed: {exc}') from exc
