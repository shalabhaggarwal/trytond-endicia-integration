# -*- encoding: utf-8 -*-
"""
Customizes company to have Endicia API Information
"""
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

# pylint: disable=E1101
# pylint: disable=F0401
from collections import namedtuple

from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['Company']
__metaclass__ = PoolMeta


class Company:
    """
    Company
    """
    __name__ = 'company.company'

    account_id = fields.Integer('Account Id')
    requester_id = fields.Char('Requester Id')
    passphrase = fields.Char('Passphrase')
    usps_test = fields.Boolean('Is Test')

    @classmethod
    def __setup__(cls):
        super(Company, cls).__setup__()
        cls._error_messages.update({
            'endicia_credentials_required': 'Please check the account '
                'settings for Endicia account.\nSome details may be missing.',
        })

    def get_endicia_credentials(self):
        """
        Returns the credentials in tuple

        :return: (account_id, requester_id, passphrase, is_test)
        """
        if not all([
                self.account_id,
                self.requester_id,
                self.passphrase
            ]):
            self.raise_user_error('endicia_credentials_required')

        EndiciaSettings = namedtuple('EndiciaSettings', [
            'account_id', 'requester_id', 'passphrase', 'usps_test'
        ])
        return EndiciaSettings(
            self.account_id,
            self.requester_id,
            self.passphrase,
            self.usps_test,
        )
