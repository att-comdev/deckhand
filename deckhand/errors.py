# Copyright 2017 AT&T Intellectual Property.  All other rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class DeckhandException(Exception):
    """Base Deckhand Exception
    To correctly use this class, inherit from it and define
    a 'msg_fmt' property. That msg_fmt will get printf'd
    with the keyword arguments provided to the constructor.
    """
    msg_fmt = "An unknown exception occurred."
    code = 500

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.msg_fmt % kwargs

            except Exception:
                message = self.msg_fmt

        self.message = message
        super(DeckhandException, self).__init__(message)

    def format_message(self):
        return self.args[0]


class ApiError(Exception):
    pass


class InvalidFormat(ApiError):
    """The YAML file is incorrectly formatted and cannot be read."""


class DocumentExists(DeckhandException):
    msg_fmt = ("Document with kind %(kind)s and schemaVersion "
               "%(schema_version)s already exists.")
    code = 409


<<<<<<< HEAD
=======
class LayeringPolicyNotFound(DeckhandException):
    msg_fmt = ("LayeringPolicy with schema %(schema)s not found in the "
               "system.")
    code = 400


class LayeringPolicyMalformed(DeckhandException):
    msg_fmt = ("LayeringPolicy with schema %(schema)s is improperly formatted:"
               " %(document)s.")
    code = 400


class IndeterminateDocumentParent(DeckhandException):
    msg_fmt = ("Too many parent documents found for document %(document)s.")
    code = 400


class MissingDocumentParent(DeckhandException):
    msg_fmt = ("Missing parent document for document %(document)s.")
    code = 400


class MissingDocumentKey(DeckhandException):
    msg_fmt = ("Missing document key %(key)s from either parent or child. "
               "Parent: %(parent)s. Child: %(child)s.")


class UnsupportedActionMethod(DeckhandException):
    msg_fmt = ("Method in %(actions)s is invalid for document %(document)s.")
    code = 400


>>>>>>> 9e9c017... [feat] DECKHAND-13: Document layering (merge) logic
class RevisionNotFound(DeckhandException):
    msg_fmt = ("The requested revision %(revision)s was not found.")
    code = 403
