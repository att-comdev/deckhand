..
  Copyright 2017 AT&T Intellectual Property.
  All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

Deckhand Exceptions
===================

+--------------------------------+-----------------------------------------------------------------------------------+
| Exception                      | Error Description                                                                 |
+================================+===================================================================================+
| BarbicanException              | An error occurred with Barbican.                                                  |
|                                |                                                                                   |
|                                | **Message:** *<various>*.                                                         |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| DocumentExists                 | A document attempted to be put into a bucket where another document with the same |
|                                | schema and metadata.name already exist.                                           |
|                                |                                                                                   |
|                                | **Message:** *Document with schema <schema> and metadata.name <name> already      |
|                                | exists in bucket <bucket>*.                                                       |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| DocumentNotFound               | The requested document could not be found.                                        |
|                                |                                                                                   |
|                                | **Message:** *The requested document <document> was not found*.                   |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| InvalidDocumentFormat          | Schema validations failed for the provided document.                              |
|                                |                                                                                   |
|                                | **Message:** *The provided document failed schema validation. Details: <various>*.|
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| IndeterminateDocumentParent    | More then one parent document as found for a document.                            |
|                                |                                                                                   |
|                                | **Message:** *Too many parent documents found for document <document>*.           |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| LayeringPolicyNotFound         | Required LayeringPolicy was not found for layering.                               |
|                                |                                                                                   |
|                                | **Message:** *Required LayeringPolicy was not found for layering*.                |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| MissingDocumentKey             | The key does not exist in the "rendered_data".                                    |
|                                |                                                                                   |
|                                | **Message:** *Missing document key <key> from either parent or child. "Parent:    |
|                                | <parent> Child: <child>*.                                                         |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| MissingDocumentPattern         | 'Pattern' is not None and data[jsonpath] doesn't exist.                           |
|                                |                                                                                   |
|                                | **Message:** *Missing document pattern <pattern> in <data> at path <path>*.       |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| PolicyNotAuthorized            | The policy action is not found in the list of registered rules.                   |
|                                |                                                                                   |
|                                | **Message:** *Policy doesn't allow <action> to be performed*.                     |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| RevisionTagBadFormat           | The tag data is neither None nor dictionary.                                      |
|                                |                                                                                   |
|                                | **Message:** *The requested tag data <data> must either be null or dictionary*.   |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| RevisionTagNotFound            | The tag for the revision id was not found.                                        |
|                                |                                                                                   |
|                                | **Message:** *The requested tag '<tag>' for revision <revision> was not found*.   |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| RevisionNotFound               | The revision cannot be found or doesn't exist.                                    |
|                                |                                                                                   |
|                                | **Message:** *The requested revision <revision> was not found*.                   |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| SingletonDocumentConflict      | A singleton document already exist within the system.                             |
|                                |                                                                                   |
|                                | **Message:** *A singleton document by the name <document> already exists in the   |
|                                | system. The new document <conflict> cannot be created. To create a document with  |
|                                | a new name, delete the current one first*.                                        |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| SubstitutionFailure            | An unknown error occurred during substitution.                                    |
|                                |                                                                                   |
|                                | **Message:** *An unknown exception occurred while trying to perform substitution. |
|                                | Details: <detail>*.                                                               |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| UnsupportedActionMethod        | The action is not in the list of supported methods.                               |
|                                |                                                                                   |
|                                | **Message:** *Method in <actions> is invalid for document <document>*.            |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
| ValidationNotFound             | The requested validation was not found.                                           |
|                                |                                                                                   |
|                                | **Message:** *The requested validation entry <entry_id> was not found for         |
|                                | validation name <validation_name> and revision ID <revision_id>*.                 |
|                                |                                                                                   |
|                                | **Troubleshoot:**                                                                 |
+--------------------------------+-----------------------------------------------------------------------------------+
