#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import appdaemon.plugins.hass.hassapi as hass
import slixmpp

class Chatty(hass.Hass):
    async def initialize(self):
        username = self.args["username"]
        password = self.args["password"]
        self.recipients = self.args["recipients"] # note, this is expected to be an array!

        self.start_xmpp(username, password)

        self.register_service("notify/jabber", self.on_notify_service)
        self.listen_event(self.on_notify_event, "NOTIFY_JABBER")

        self.log("Chatty started.")

    def start_xmpp(self, username, password):
        self.log("Starting chatty with username: {}".format(username))
        
        self.xmpp = XMPPconnector(username, password, self)
        self.xmpp.register_plugin('xep_0030') # Service Discovery
        self.xmpp.register_plugin('xep_0004') # Data Forms
        self.xmpp.register_plugin('xep_0060') # PubSub
        self.xmpp.register_plugin('xep_0199') # XMPP Ping

        self.xmpp.connect()
        #xmpp.process()   ## we are already async        

    def on_notify_service(self, ns, domain, service, data):
        """
        callback for service (from within appdaemon)
        """
        self._on_notify(data["message"])

    def on_notify_event(self, event_name, data, kwargs):
        """
        callback for event (from homeassistant)
        """
        self._on_notify(data["message"])

    def _on_notify(self, message):
        """
        send message to predefined XMPP contacts
        """
        for recipient in self.recipients:
            self.log("Sending '{}' to '{}'".format(message, recipient))
            self.xmpp.send_message(mto=recipient, mbody=message, mtype='chat')

    def on_incoming_message(self, msg):
        message = msg["body"]
        sender = msg["from"]
        self.log("Incoming: '{}', from '{}".format(message, sender))

        # return an answer to the sender (optional)
        return None

    
class XMPPconnector(slixmpp.ClientXMPP):
    def __init__(self, jid, password, message_handler):
        slixmpp.ClientXMPP.__init__(self, jid, password)
        self.message_handler = message_handler

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)

    def start(self, event):
        self.send_presence()
        self.get_roster()

    def message(self, msg):
        """
        called by slixmpp on incoming XMPP messages
        """

        if msg['type'] in ('chat', 'normal'):
            answer = self.message_handler.on_incoming_message(msg)

            if answer:
                msg.reply(answer).send()
