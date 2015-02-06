from openerp import _, api, fields, models
import urllib
import json
import logging
from openerp import exceptions
_logger = logging.getLogger(__name__)


class yahoo_getter(models.Model):
    _inherit = "res.currency.rate.provider"

    @api.one
    def _request_to_yahoo_finance(self):
        base_obj = self.env['res.currency.rate.provider'].search([('service_provider', '=', 'yahoo_finance')])
        if base_obj:
            currencies_to_update = map(lambda x: x.name, self.currency_ids)
            base_currency = map(lambda x: x.name, self.base_currency_id)

            all_pairs = []
            for multiple in currencies_to_update:
                for single in base_currency:
                    pairs = single + multiple
                    all_pairs.append(pairs)
            all_pairs = ",".join(all_pairs)

            request_url = "http://query.yahooapis.com/v1/public/yql?q=select * from yahoo.finance.xchange where pair in('{0}')&format=json&env=store://datatables.org/alltableswithkeys".format(all_pairs)

            try:
                parse_url = urllib.urlopen(request_url).read()
                return parse_url
            except (IOError, NameError):
                raise exceptions.Warning(_('Not valid URL.. !'))

    @api.one
    def _parse_currency_data_yahoo_finance(self):
        try:
            raw_data = json.dumps(self._request_to_yahoo_finance())
            json_data = json.loads(raw_data)
            try:
                all_vals = []
                unlist_json = json.loads(json_data[0])
                try:
                    exchange_rate = unlist_json['query']['results']['rate']['Rate']
                    map_id = unlist_json['query']['results']['rate']['Name'].split(' ')[-1]
                    cur_id = self.env['res.currency'].search([('name', 'ilike', map_id)])
                    dict = {'currency_id': cur_id.id, 'rate': exchange_rate}
                    all_vals.append(dict)
                    return all_vals
                except TypeError:
                    vals = unlist_json['query']['results']['rate']
                    for i in vals:
                        exchange_rate = i['Rate']
                        map_id = i['Name'].split(' ')[-1]
                        cur_id = self.env['res.currency'].search([('name', 'ilike', map_id)])
                        dict = {'currency_id': cur_id.id, 'rate': exchange_rate}
                        all_vals.append(dict)
                    return all_vals
            except (KeyError, TypeError):
                raise exceptions.Warning(_('No data found in yahoo finance!!'))
        except (IOError, NameError):
            raise exceptions.Warning(_('Not valid URL.. !'))
