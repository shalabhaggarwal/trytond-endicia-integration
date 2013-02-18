# -*- encoding: utf-8 -*-
"""
Customizes party address to have address in correct format for Endicia API .
"""
# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.

# pylint: disable=E1101
# pylint: disable=F0401
import string

from endicia import FromAddress, ToAddress
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool

__all__ = ['Address']
__metaclass__ = PoolMeta


class Address:
    '''
    Address
    '''
    __name__ = "party.address"

    def address_to_endicia_from_address(self):
        '''
        Converts party address to Endicia From Address.

        :param id: ID of record
        :param return: Returns instance of FromAddress
        '''
        Company = Pool().get('company.company')

        company = Transaction().context.get('company')

        phone = self.party.phone
        if phone:
            # Remove the special characters in the phone if any
            phone = "".join([char for char in phone if char in string.digits])
        return FromAddress(
            FromName = company and Company(company).name or None,
            #FromCompany = user_rec.company.name or None,
            ReturnAddress1 = self.street or None,
            ReturnAddress2 = self.streetbis or None,
            ReturnAddress3 = None,
            ReturnAddress4 = None,
            FromCity = self.city or None,
            FromState = self.subdivision and \
                self.subdivision.code[3:] or None,
            FromPostalCode = self.zip or None,
            FromPhone = phone or None,
            FromEMail = self.party.email or None,
        )

    def address_to_endicia_to_address(self):
        '''
        Converts party address to Endicia To Address.

        :param id: ID of record
        :param return: Returns instance of ToAddress
        '''
        phone = self.party.phone
        if phone:
            # Remove the special characters in the phone if any
            phone = "".join([char for char in phone if char in string.digits])
        return ToAddress(
            ToName = self.name or None,
            ToCompany = self.party and self.party.name or None,
            ToAddress1 = self.street or None,
            ToAddress2 = self.streetbis or None,
            ToAddress3 = None,
            ToAddress4 = None,
            ToCity = self.city or None,
            ToState = self.subdivision and \
                self.subdivision.code[3:] or None,
            ToPostalCode = self.zip or None,
            ToCountry = self.country and self.country.name or None,
            ToCountryCode = self.country and self.country.code or None,
            ToPhone = phone or None,
            ToEMail = self.party.email or None,
        )
