# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import PoolMeta, Pool
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.wizard import Wizard

__all__ = ['Configuration', 'Sale',]
__metaclass__ = PoolMeta


class Configuration:
    'Sale Configuration'
    __name__ = 'sale.configuration'

    endicia_mailclass = fields.Many2One(
        'endicia.mailclass', 'Default MailClass',
    )
    endicia_label_subtype = fields.Selection([
        ('None', 'None'),
        ('Integrated', 'Integrated')
    ], 'Label Subtype')
    endicia_integrated_form_type = fields.Selection([
        ('Form2976', 'Form2976(Same as CN22)'),
        ('Form2976A', 'Form2976(Same as CP72)'),
    ], 'Integrated Form Type')
    endicia_include_postage = fields.Boolean('Include Postage ?')


class Sale:
    "Sale"
    __name__ = 'sale.sale'

    endicia_mailclass = fields.Many2One(
        'endicia.mailclass', 'MailClass', states={
            'readonly': Eval('state') != 'draft',
        }, depends=['state']
    )
    endicia_label_subtype = fields.Selection([
        ('None', 'None'),
        ('Integrated', 'Integrated')
    ], 'Label Subtype', states={
            'readonly': Eval('state') != 'draft',
        }, depends=['state']
    )
    endicia_integrated_form_type = fields.Selection([
        ('Form2976', 'Form2976(Same as CN22)'),
        ('Form2976A', 'Form2976(Same as CP72)'),
    ], 'Integrated Form Type', states={
            'readonly': Eval('state') != 'draft',
        }, depends=['state']
    )
    endicia_include_postage = fields.Boolean('Include Postage ?', states={
            'readonly': Eval('state') != 'draft',
        }, depends=['state']
    )
    is_endicia_shipping = fields.Boolean(
        'Is Endicia Shipping', depends=['carrier'],
        states={'invisible': True}
    )

    @staticmethod
    def default_endicia_mailclass():
        Config = Pool().get('sale.configuration')
        config = Config(1)
        return config.endicia_mailclass.id

    @staticmethod
    def default_endicia_label_subtype():
        Config = Pool().get('sale.configuration')
        config = Config(1)
        return config.endicia_label_subtype

    @staticmethod
    def default_endicia_integrated_form_type():
        Config = Pool().get('sale.configuration')
        config = Config(1)
        return config.endicia_integrated_form_type

    @staticmethod
    def default_endicia_include_postage():
        Config = Pool().get('sale.configuration')
        config = Config(1)
        return config.endicia_include_postage

    @classmethod
    def __setup__(cls):
        super(Sale, cls).__setup__()
        cls._error_messages.update({
            'weight_required': 'Please enter weights for the products',
            'weight_uom_required': 'Please enter weight uom for the products',
        })
        cls._buttons.update({
            'update_endicia_shipment_cost': {
                'invisible': Eval('state') == 'draft'
            }
        })

    def on_change_carrier(self):
        res = super(Sale, self).on_change_carrier()

        if self.carrier and self.carrier.carrier_cost_method == 'endicia':
            res['is_endicia_shipping'] = True
        else:
            res['is_endicia_shipping'] = False

        return res

    def _get_carrier_context(self):
        "Pass sale in the context"
        context = super(Sale, self)._get_carrier_context()

        if not self.carrier.carrier_cost_method == 'endicia':
            return context

        context = context.copy()
        context['sale'] = self.id
        return context

    def on_change_lines(self):
        """Pass a flag in context which indicates the get_sale_price method
        of FedEx carrier not to calculate cost on each line change
        """
        with Transaction().set_context({'ignore_carrier_computation': True}):
            return super(Sale, self).on_change_lines()

    def get_line_weights(self):
        """
        Return weight for lines in a matrix form
        """
        ProductUom = Pool().get('product.uom')
        weight_matrix = {}
        for line in self.lines:
            if line.product.type == 'service':
                continue
            if not line.product.weight:
                self.raise_user_error('weight_required')
            if not line.product.weight_uom:
                self.raise_user_error('weight_uom_required')

            # Find the quantity in the default uom of the product as the weight
            # is for per unit in that uom
            if line.unit.id != line.product.default_uom.id:
                quantity = ProductUom.compute_qty(
                    line.unit,
                    line.quantity,
                    line.product.default_uom
                )
            else:
                quantity = line.quantity

            weight = float(line.product.weight) * quantity

            # Endicia by default uses oz for weight purposes
            if line.product.weight_uom.symbol != 'oz':
                uom, = ProductUom.search([('symbol', '=', 'oz')])
                weight = ProductUom.compute_qty(
                    line.product.weight_uom,
                    weight,
                    uom
                )
            weight_matrix[line.id] = int(weight)
        return weight_matrix

    @classmethod
    def quote(cls, sales):
        SaleLine = Pool().get('sale.line')

        super(Sale, cls).quote(sales)
        for sale in sales:
            if sale.carrier and sale.carrier.carrier_cost_method == 'endicia':
                with Transaction().set_context({'sale': sale.id}):
                    shipment_cost = sale.carrier.get_sale_price()
                    if not shipment_cost[0]:
                        continue
                for line in sale.lines:
                    if line.shipment_cost:
                        SaleLine.delete([line])
                SaleLine.create({
                    'sale': sale.id,
                    'type': 'line',
                    'product': sale.carrier.carrier_product.id,
                    'description': sale.endicia_mailclass.name,
                    'quantity': 1,  # XXX
                    'unit': sale.carrier.carrier_product.sale_uom.id,
                    'unit_price': Decimal(shipment_cost[0]),
                    'shipment_cost': Decimal(shipment_cost[0]),
                    'amount': Decimal(shipment_cost[0]),
                    'taxes': [],
                    'sequence': 9999,  # XXX
                })

    @classmethod
    @ModelView.button
    def update_endicia_shipment_cost(cls, sales):
        "Updates the shipping line with new value if any"
        SaleLine = Pool().get('sale.line')

        for sale in sales:
            if sale.carrier and sale.carrier.carrier_cost_method == 'endicia':
                with Transaction().set_context({'sale': sale.id}):
                    shipment_cost = sale.carrier.get_sale_price()
                    if not shipment_cost[0]:
                        continue
                for line in sale.lines:
                    if line.shipment_cost and \
                            line.shipment_cost != Decimal(shipment_cost[0]):
                        SaleLine.delete([line])
                        SaleLine.create({
                            'sale': sale.id,
                            'type': 'line',
                            'product': sale.carrier.carrier_product.id,
                            'description': sale.endicia_mailclass.name,
                            'quantity': 1,  # XXX
                            'unit': sale.carrier.carrier_product.sale_uom.id,
                            'unit_price': Decimal(shipment_cost[0]),
                            'shipment_cost': Decimal(shipment_cost[0]),
                            'amount': Decimal(shipment_cost[0]),
                            'taxes': [],
                            'sequence': 9999,  # XXX
                        })


class GenerateEndiciaLabelMessage(ModelView):
    'Generate Endicia Labels Message'
    __name__ = 'generate.endicia.label.message'


class GenerateEndiciaLabel(Wizard):
    'Generate Endicia Labels'
    __name__ = 'generate.endicia.label'

    start_state = 'generate'
    #generate = 
