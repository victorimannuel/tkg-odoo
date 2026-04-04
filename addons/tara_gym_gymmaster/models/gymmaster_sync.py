import logging
import base64
import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

from .gymmaster_mapping import GYMMASTER_ENDPOINTS


_logger = logging.getLogger(__name__)


class GymMasterSync(models.TransientModel):
    _name = "gymmaster.sync"
    _description = "GymMaster Synchronization"

    @api.model
    def _get_base_url(self):
        param = self.env["ir.config_parameter"].sudo()
        return param.get_param("gymmaster.base_url") or ""

    @api.model
    def _get_api_key(self):
        param = self.env["ir.config_parameter"].sudo()
        return param.get_param("gymmaster.api_key") or ""

    @api.model
    def _build_headers(self):
        return {
            "Accept": "application/json",
        }

    @api.model
    def _build_query_params(self, endpoint_key, when=None, company_id=None):
        api_key = self._get_api_key()
        if not api_key:
            raise UserError("GymMaster API key is not configured.")
        params = {
            "api_key": api_key,
        }
        if when:
            params["when"] = when
        if company_id:
            params["companyid"] = company_id
        return params

    @api.model
    def _fetch_from_gymmaster(self, endpoint_key, when=None, company_id=None):
        config = GYMMASTER_ENDPOINTS.get(endpoint_key)
        if not config:
            raise UserError("Unknown GymMaster endpoint key %s." % endpoint_key)
        base_url = self._get_base_url()
        if not base_url:
            raise UserError("GymMaster base URL is not configured.")
        url = "%s%s" % (base_url.rstrip("/"), config["path"])
        headers = self._build_headers()
        params = self._build_query_params(endpoint_key, when=when, company_id=company_id)
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
        except requests.exceptions.Timeout as e:
            _logger.warning("GymMaster request timeout on %s: %s", url, e)
            raise UserError("Timeout while contacting GymMaster. Please try again or use a narrower 'when' filter.") from e
        except requests.exceptions.RequestException as e:
            _logger.exception("GymMaster request error on %s", url)
            raise UserError("Error while contacting GymMaster: %s" % e) from e
        if response.status_code >= 400:
            raise UserError("GymMaster API error %s: %s" % (response.status_code, response.text))
        try:
            data = response.json()
        except ValueError as e:
            raise UserError("Invalid JSON response from GymMaster: %s" % e)
        if isinstance(data, dict):
            error_message = data.get("error")
            if error_message:
                raise UserError("GymMaster API error: %s" % error_message)
            if "result" in data:
                data = data.get("result") or []
        return data, config

    @api.model
    def _upsert_members(self, records):
        data, config = records
        model_name = config["model"]
        external_id_field = config["external_id_field"]
        key_field = config["key"]
        field_map = config["fields"]
        Model = self.env[model_name].sudo()
        if external_id_field not in Model._fields:
            raise UserError("Model %s is missing field %s for GymMaster mapping." % (model_name, external_id_field))
        ids = []
        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            ids.append(external_id)
        existing_records = Model.search([(external_id_field, "in", ids)]) if ids else Model.browse()
        existing_map = {str(getattr(rec, external_id_field)): rec for rec in existing_records}
        to_create = []
        to_update = []
        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            values = {}
            for external_name, field_name in field_map.items():
                if field_name not in Model._fields:
                    continue
                if external_name in item:
                    values[field_name] = item[external_name]
            if model_name == "gym.member" and "gender" in Model._fields:
                raw_gender = item.get("gender")
                mapped_gender = "other"
                if raw_gender:
                    code = str(raw_gender).strip().lower()
                    if code.startswith("m"):
                        mapped_gender = "male"
                    elif code.startswith("f"):
                        mapped_gender = "female"
                values["gender"] = mapped_gender
            if not values:
                continue
            values[external_id_field] = external_id
            existing = existing_map.get(external_id)
            if existing:
                update_vals = {}
                for field_name, value in values.items():
                    if existing[field_name] != value:
                        update_vals[field_name] = value
                if update_vals:
                    to_update.append((existing, update_vals))
            else:
                to_create.append(values)
        if to_create:
            Model.create(to_create)
        for record, vals in to_update:
            record.write(vals)

    @api.model
    def _upsert_memberships(self, records):
        data, config = records
        model_name = config["model"]
        external_id_field = config["external_id_field"]
        key_field = config["key"]
        field_map = config["fields"]
        Model = self.env[model_name].sudo()
        if external_id_field not in Model._fields:
            raise UserError("Model %s is missing field %s for GymMaster mapping." % (model_name, external_id_field))
        ids = []
        import re

        def _parse_price(raw):
            if isinstance(raw, (int, float)):
                return float(raw)
            s = str(raw).strip()
            s = re.sub(r"[^0-9,.\-]", "", s)
            if not s:
                return 0.0
            if "," in s and "." in s:
                s = s.replace(".", "")
                s = s.replace(",", ".")
            elif "," in s and "." not in s:
                s = s.replace(",", ".")
            try:
                return float(s)
            except ValueError:
                return 0.0

        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            ids.append(external_id)
        existing_records = Model.search([(external_id_field, "in", ids)]) if ids else Model.browse()
        existing_map = {str(getattr(rec, external_id_field)): rec for rec in existing_records}
        to_create = []
        to_update = []
        Category = self.env["product.category"].sudo()
        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            values = {}
            for external_name, field_name in field_map.items():
                if field_name not in Model._fields:
                    continue
                if external_name in item:
                    values[field_name] = item[external_name]
            if "price" in values:
                values["price"] = _parse_price(values["price"])
            raw_length = item.get("membership_length")
            if raw_length:
                parts = str(raw_length).strip().lower().split()
                if len(parts) >= 2:
                    try:
                        qty = int(parts[0])
                    except ValueError:
                        qty = 1
                    unit = parts[1]
                    if unit.endswith("s"):
                        unit = unit[:-1]
                    if unit in ("day", "week", "month", "year"):
                        unit_map = {
                            "day": "days",
                            "week": "weeks",
                            "month": "months",
                            "year": "years",
                        }
                        values["duration"] = qty
                        values["duration_uom"] = unit_map[unit]
            
            category_name = item.get("divisionname")
            if category_name and "category_id" in Model._fields:
                category = Category.search([("name", "=", category_name), ("gym_category_type", "=", "membership")], limit=1)
                if not category:
                    category = Category.create({
                        "name": category_name,
                        "gym_category_type": "membership"
                    })
                values["category_id"] = category.id
            if not values:
                continue
            values[external_id_field] = external_id
            existing = existing_map.get(external_id)
            if existing:
                update_vals = {}
                for field_name, value in values.items():
                    if existing[field_name] != value:
                        update_vals[field_name] = value
                if update_vals:
                    to_update.append((existing, update_vals))
            else:
                to_create.append(values)
        if to_create:
            Model.create(to_create)
        for record, vals in to_update:
            record.write(vals)

    @api.model
    def sync_members(self, when=None, company_id=None, batch_size=None):
        data, config = self._fetch_from_gymmaster("members", when=when, company_id=company_id)
        _logger.info("Fetched %d members from GymMaster.", len(data))
        if not data:
            return
        if not batch_size:
            self._upsert_members((data, config))
            return
        total = len(data)
        for offset in range(0, total, batch_size):
            chunk = data[offset : offset + batch_size]
            _logger.info("Upserting (%d/%d) members from GymMaster.", offset + len(chunk), total)
            if not chunk:
                continue
            self._upsert_members((chunk, config))

    @api.model
    def sync_member_photos(self, when=None, company_id=None, batch_size=None):
        data, config = self._fetch_from_gymmaster("members", when=when, company_id=company_id)
        _logger.info("Fetched %d members from GymMaster for photo sync.", len(data))
        if not data:
            return

        model_name = config["model"]
        external_id_field = config["external_id_field"]
        key_field = config["key"]
        Model = self.env[model_name].sudo()
        if external_id_field not in Model._fields:
            raise UserError("Model %s is missing field %s for GymMaster mapping." % (model_name, external_id_field))
        ids = []
        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            ids.append(external_id)
        existing_records = Model.search([(external_id_field, "in", ids)]) if ids else Model.browse()
        existing_map = {str(getattr(rec, external_id_field)): rec for rec in existing_records}
        photo_keys = [
            "memberphoto",
        ]
        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            member = existing_map.get(external_id)
            if not member:
                continue
            url = None
            for key in photo_keys:
                val = item.get(key)
                if val:
                    url = val
                    break
            if not url:
                continue
            try:
                resp = requests.get(url, timeout=30)
            except requests.RequestException as e:
                _logger.warning("Failed to download GymMaster photo for member %s: %s", external_id, e)
                continue
            if resp.status_code >= 400 or not resp.content:
                _logger.warning("Bad response downloading GymMaster photo for member %s: %s", external_id, resp.status_code)
                continue
            member.partner_id.image_1920 = base64.b64encode(resp.content)

    @api.model
    def sync_memberships(self, when=None, company_id=None, batch_size=None):
        data, config = self._fetch_from_gymmaster("memberships", when=when, company_id=company_id)
        _logger.info("Fetched %d memberships from GymMaster.", len(data))
        if not data:
            return
        if not batch_size:
            self._upsert_memberships((data, config))
            return
        total = len(data)
        for offset in range(0, total, batch_size):
            chunk = data[offset : offset + batch_size]
            _logger.info("Upserting (%d/%d) memberships from GymMaster.", len(chunk), total)
            if not chunk:
                continue
            self._upsert_memberships((chunk, config))

    @api.model
    def _upsert_products(self, records):
        data, config = records
        model_name = config["model"]
        external_id_field = config["external_id_field"]
        key_field = config["key"]
        field_map = config["fields"]
        Model = self.env[model_name].sudo()
        if external_id_field not in Model._fields:
            raise UserError("Model %s is missing field %s for GymMaster mapping." % (model_name, external_id_field))

        import re

        def _parse_price(raw):
            if isinstance(raw, (int, float)):
                return float(raw)
            s = str(raw).strip()
            s = re.sub(r"[^0-9,.\-]", "", s)
            if not s:
                return 0.0
            if "," in s and "." in s:
                s = s.replace(".", "")
                s = s.replace(",", ".")
            elif "," in s and "." not in s:
                s = s.replace(",", ".")
            try:
                return float(s)
            except ValueError:
                return 0.0

        ids = []
        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            ids.append(external_id)
        existing_records = Model.search([(external_id_field, "in", ids)]) if ids else Model.browse()
        existing_map = {str(getattr(rec, external_id_field)): rec for rec in existing_records}
        to_create = []
        to_update = []
        Category = self.env["product.category"].sudo()
        for item in data or []:
            raw_external_id = item.get(key_field)
            if raw_external_id is None:
                continue
            external_id = str(raw_external_id)
            values = {}
            for external_name, field_name in field_map.items():
                if field_name not in Model._fields:
                    continue
                if external_name in item:
                    values[field_name] = item[external_name]
            if "list_price" in values:
                values["list_price"] = _parse_price(values["list_price"])
            # Map producttype to product.category
            category_name = item.get("producttype")
            if category_name:
                category = Category.search([("name", "=", category_name), ("gym_category_type", "=", "other")], limit=1)
                if not category:
                    category = Category.create({
                        "name": category_name,
                        "gym_category_type": "other",
                    })
                values["categ_id"] = category.id
            if not values:
                continue
            values[external_id_field] = external_id
            existing = existing_map.get(external_id)
            if existing:
                update_vals = {}
                for field_name, value in values.items():
                    if existing[field_name] != value:
                        update_vals[field_name] = value
                if update_vals:
                    to_update.append((existing, update_vals))
            else:
                to_create.append(values)
        if to_create:
            Model.create(to_create)
        for record, vals in to_update:
            record.write(vals)

    @api.model
    def sync_products(self, when=None, company_id=None, batch_size=None):
        data, config = self._fetch_from_gymmaster("products", when=when, company_id=company_id)
        _logger.info("Fetched %d products from GymMaster.", len(data))
        if not data:
            return
        if not batch_size:
            self._upsert_products((data, config))
            return
        total = len(data)
        for offset in range(0, total, batch_size):
            chunk = data[offset : offset + batch_size]
            _logger.info("Upserting (%d/%d) products from GymMaster.", offset + len(chunk), total)
            if not chunk:
                continue
            self._upsert_products((chunk, config))
