# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from endicia import CalculatingPostageAPI
from endicia.tools import objectify_response

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction

__all__ = ['Carrier', 'EndiciaMailclass',]
__metaclass__ = PoolMeta


class Carrier:
    "Carrier"
    __name__ = 'carrier'

    @classmethod
    def __setup__(cls):
        super(Carrier, cls).__setup__()
        selection = ('endicia', 'USPS [Endicia]')
        if selection not in cls.carrier_cost_method.selection:
            cls.carrier_cost_method.selection.append(selection)

        cls._error_messages.update({
            'location_required': 'Warehouse address is required.',
        })

    def get_sale_price(self):
        """Estimates the shipment rate for the provided shipment
        """
        Company = Pool().get('company.company')
        Sale = Pool().get('sale.sale')

        if Transaction().context.get('ignore_carrier_computation') or \
                not Transaction().context.get('sale'):
            return 0, None

        sale = Sale(Transaction().context.get('sale'))

        if self.carrier_cost_method != 'endicia':
            return super(Carrier, self).get_sale_price(self)

        # Getting the api credentials to be used in shipping label generation
        # endicia credentials are in the format : 
        # EndiciaSettings(account_id, requester_id, passphrase, is_test)
        company = Company(Transaction().context.get('company'))
        endicia_credentials = company.get_endicia_credentials()

        #From location is the warehouse location. So it must be filled.
        location = sale.warehouse.address
        if not location:
            self.raise_user_error('location_required')
        line_weights = sale.get_line_weights_for_endicia()
        calculate_postage_request = CalculatingPostageAPI(
            mailclass = sale.endicia_mailclass.value,
            weightoz = sum(line_weights.values()),
            from_postal_code = location.zip,
            to_postal_code = sale.shipment_address.zip,
            to_country_code = sale.shipment_address.country.code,
            accountid = endicia_credentials.account_id,
            requesterid = endicia_credentials.requester_id,
            passphrase = endicia_credentials.passphrase,
            test = endicia_credentials.usps_test,
            )
        response = calculate_postage_request.send_request()
        return objectify_response(response).PostagePrice.\
            get('TotalAmount'), False


class EndiciaMailclass(ModelSQL, ModelView):
    "Endicia mailclass"
    __name__ = 'endicia.mailclass'

    name = fields.Char('Name', required=True, select=1)
    value = fields.Char('Value', required=True, select=1)
    method_type = fields.Selection([
        ('domestic', 'Domestic'),
        ('international', 'International'),
    ], 'Type', required=True, select=1)
