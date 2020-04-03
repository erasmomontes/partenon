import os
from oraculo.gods.sap import APIClient
from oraculo.gods.exceptions import NotFound
from ..base import BaseEntity
from partenon.ERP import exceptions


class ERPClient(BaseEntity):
    _client = APIClient
    _info_url = 'api_portal_clie/datos_cliente'
    _search_url = 'api_portal_clie/dame_clientes'
    _has_credit_url = 'api_portal_clie/clie_bad_credit'
    _add_email = 'api_portal_clie/add_mail_resid'
    _invoices_url = 'api_portal_clie/dame_fact_pendi'
    _invoice_binary_url = 'api_portal_clie/dame_fact_pdf'
    _advance_payment_url = 'api_portal_clie/dame_concep_lis'
    client_number = None
    client_name = None
    client_code = None

    @property
    def code(self):
        return self.client_code if self.client_code else self.client_number

    def info(self):
        client = self._client()
        body = {"I_CLIENTE": self.client_number}
        return client.post(self._info_url, body)

    def search(self):
        client = self._client()
        return client.post(
            self._search_url,
            {"CODIGO": self.code, "NOMBRE": self.client_name})

    def has_credit(self):
        client = self._client()
        return client.post(
            self._has_credit_url,
            {"I_CLIENTE": self.code})

    def add_email(self, email):
        client = self._client()
        return client.post(
            self._add_email,
            {'CODIGO_SAP': self.code, 'CORREO': email})

    def invoices(self, merchant='', language='ES'):
        invoices = self._client().post(
            self._invoices_url,
            {
                'I_CLIENTE': self.code,
                'I_IDIOMA': language,
                'I_MERCHANTNR': merchant
            }
        )
        return [BaseEntity(**invoice) for invoice in invoices]

    def invoice_pdf(self, document_number, merchant, language=''):
        invoice_binary = self._client().post(
            self._invoice_binary_url,
            {
                "I_CLIENTE": self.code,
                "I_IDIOMA": language,
                "I_DOCUMENT_NUMBER": document_number,
                "I_MERCHANTNR": merchant
            }
        )
        return BaseEntity(**invoice_binary)

    def advance_payment(self, merchant, language=''):
        advance_payment = self._client().post(
            self._advance_payment_url,
            {
                "sap_customer": self.code,
                'lang': language,
                'I_MERCHANTNR': merchant
            }
        )
        return [BaseEntity(**advance_payment)
                for advance_payment in advance_payment]


class ERPResidents(BaseEntity):
    _client = APIClient
    _search_url = 'api_portal_clie/dame_residentes'
    name = None
    client_sap = None

    def search(self):
        client = self._client()
        body = {"NOMBRE": self.name, "CLIENTE_SAP": self.client_sap}
        return client.post(self._search_url, body)

    @staticmethod
    def get_principal_email(email):
        client = APIClient()
        return client.post(
            "api_portal_clie/get_mail_princ",
            {'CORREO': email})


class ERPAviso(BaseEntity):
    _client = APIClient
    _create_url = 'api_portal_clie/crear_aviso'
    _info_url = 'api_portal_clie/info_aviso'
    _create_quotation_url = 'api_portal_clie/create_quotatio'
    _sap_customer = None
    aviso = None

    @property
    def responsable(self):
        if not hasattr(self, 'aviso'):
            raise AttributeError('Not has atribute aviso')

        body = {
            "I_AVISO": self.aviso,
            "I_IDIOMA": 'S'}
        client = self._client()
        response = client.post(self._info_url, body)
        responsable = response.get('responsable')
        return BaseEntity(**responsable)

    @property
    def client(self):
        if not hasattr(self, 'aviso'):
            raise AttributeError('Not has atribute aviso ni cliente')

        if not self._sap_customer:
            self._sap_customer = self.info(self.aviso).get('cliente')

        client = ERPClient(client_number=self._sap_customer)
        return BaseEntity(**client.info())

    def create(
            self, client_sap, text, text_larg,
            service_name, email, type_service,
            require_quotation=None):

        self._sap_customer = client_sap
        body = {
            "I_CLIENTE": client_sap,
            "I_TXT_CORTO": text,
            "I_TXT_LARGO": text_larg,
            "I_IDIOMA": "S",
            "I_TEXTO_SERVICIO": service_name,
            "I_ID_SERVICIO": type_service,
            "I_CORREO": email,
            "I_REQUIRE_QUOTATION": True if require_quotation else False}
        client = self._client()
        response = client.post(self._create_url, body)
        return ERPAviso(**response)

    def info(self, aviso, language="S"):
        body = {
            "I_AVISO": aviso,
            "I_IDIOMA": language}
        client = self._client()
        response = client.post(self._info_url, body)
        return response

    @staticmethod
    def update(
            aviso, status,
            client=APIClient,
            update_url='api_portal_clie/update_aviso'):

        client = client()
        body = {
            "I_AVISO": aviso,
            "I_STATUS": status,
            "I_IDIOMA": "S"}
        try:
            return client.post(update_url, body)
        except NotFound:
            message = 'The %s warning does not have a created order.' % aviso
            raise exceptions.NotHasOrder(message)

    @staticmethod
    def update_client(
            aviso,
            client_number,
            api_client=APIClient,
            api_url='api_portal_clie/upt_clien_aviso'):

        body = {"AVISO": aviso, "CLIENTE": client_number}
        return api_client().post(api_url, body)

    def create_quotation(self):
        if not hasattr(self, 'aviso'):
            raise AttributeError('Not has aviso set attribute')

        client = self._client()
        body = {"I_AVISO": self.aviso, "I_IDIOMA": "S"}
        response = client.post(self._create_quotation_url, body)
        return response.get('pdf')
