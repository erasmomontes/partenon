import os
from oraculo.gods import faveo, faveo_db, exceptions
from . import entitys, base
from .exceptions import (
    DoesNotExist, NotSetHelpDeskUserInstance,
    NotIsInstance)


class Prioritys(object):
    _url = 'api/v1/helpdesk/priority'
    _entity = entitys.Priority
    objects = base.BaseManageEntity(_url, _entity, key_name='priority')


class Topics(object):
    _url = 'api/v1/helpdesk/help-topic'
    _entity = entitys.Topic
    objects = base.BaseManageEntity(_url, _entity, key_name='topic')


class Status(base.BaseManageEntity):
    _url = 'api/v1/helpdesk/dependency'
    _entity = entitys.State
    _client = faveo.APIClient()

    @staticmethod
    def get_entitys(
            client=faveo.APIClient(),
            url='api/v1/helpdesk/dependency',
            entity=State):
        response = client.get(url)
        status = response.get('data').get('status')
        return [entity(**state) for state in status]

    @staticmethod
    def get_state_by_name(
            name,
            client=faveo.APIClient(),
            url='api/v1/helpdesk/dependency',
            entity=State):
        response = client.get(url)
        status = response.get('data').get('status')
        for state in status:
            if state['name'] == name:
                return State(**state)
        else:
            raise DoesNotExist('Not exists Status %s ' % name)


class HelpDeskTicket(
        base.BaseEntityHelpDesk,
        base.BaseHelpDesk):
    _user = None
    _client = faveo.APIClient()
    _status_close_name = 'Closed'
    _department = os.environ.get('PARTENON_DEPARTMENT')
    _create_url = 'api/v1/helpdesk/create'
    _list_url = 'api/v1/helpdesk/my-tickets-user'
    _url_detail = 'api/v1/helpdesk/ticket'
    _url_to_change_status = 'api/v2/helpdesk/status/change'

    @property
    def state(self):
        response = self._client.get(
            self._url_detail, params=dict(id=self.ticket_id))
        ticket = response.get('data').get('ticket')
        return Status.get_state_by_name(ticket.get('status_name'))

    def create(self, subject, body, priority, topic):
        if not isinstance(priority, entitys.Priority):
            raise NotIsInstance('Priority not is instance of Priority')
        
        if not isinstance(topic, entitys.Topic):
            raise NotIsInstance('Topic not is instance of Topic')

        body = dict(
            subject=subject, body=body, first_name=self._user.first_name,
            email=self._user.email, priority=priority.priority_id,
            help_topic=topic.id, dept=self._department)

        response = self._client.post(self._create_url, body).get('response')
        return HelpDeskTicket(**response)

    def list(self):
        if not self._user:
            raise NotSetHelpDeskUserInstance('Need set _user instance')

        params = dict(user_id=self._user.id)
        response = self._client.get(self._list_url, params)
        return [HelpDeskTicket(**ticket) for ticket in response.get('tickets')]

    def change_state(self, state):
        body = dict(ticket_id=self.ticket_id, status_id=state.id)
        response = self._client.post(self._url_to_change_status, body)
        return response.get('success')

    def close(self):
        state_close = Status.get_state_by_name(self._status_close_name)
        body = dict(ticket_id=self.ticket_id, status_id=state_close.id)
        response = self._client.post(self._url_to_change_status, body)
        return response.get('success')


class HelpDeskUser(base.BaseEntityHelpDesk, base.BaseHelpDesk):
    _url = 'api/v1/helpdesk/register'
    _search_url = 'api/v1/helpdesk/agents'

    def __init__(self, *args, **kwargs):
        self.ticket = HelpDeskTicket(**{'_user': self})
        super().__init__(*args, **kwargs)

    @staticmethod
    def get(email,
            url='api/v1/users',
            client=faveo_db.APIClient):
        client = client()
        response = client.get(url, params={'email': email})
        return HelpDeskUser(**response) if response else None

    @staticmethod
    def create_user(
            email, first_name, last_name,
            url='api/v1/helpdesk/register',
            client=faveo.APIClient):
        
        client = client()
        user = HelpDeskUser.get(email)
        if user:
            return user

        params = dict(email=email, first_name=first_name, last_name=last_name)
        result = client.post(url, params)
        return HelpDeskUser(**result[0].get('user'))


class HelpDesk(object):
    pass
