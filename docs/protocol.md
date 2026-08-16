## Overall

All communications between frontend and backend are sent in the format of JSON via socket.

## Request

### Keys

- `action` The action to be conducted by the backend
- `source` The frontend that send this request. See complete list at constants.py:SOURCES
- `cwd` The current working directory of frontend. The missing of this key may cause error of a relative path is sent to back
- Other keys depending on the action.

## Response

### Response code

Key: `code`

- 0 OK. The main goal of the action successfully completed, though some additional goal (for example, auto set metadata of `lib add`) might have failed. In that case, the failed sub-goal should be visible in message.
- 1 Failed. Backend can not conduct this action. More information should be available in message.
- 2 Failed to connect to CADENCE backend. This response was not sent by backend but by client.py
- 3 Default code, should not be used under any circumstances. Receiving this code means response.py:Response._response was accidentally called outside the class.

### Message

Key: `msg`

A message about the result of the action. Only summarizing information may be shown in this message. Full results (for example, result of list sub-command) should be put under the `attachment` key.
For multi-stage actions such as restart (including jump to beginning and delete memorized position) the result of different stages should be separated by "|".

### Attachment

Key: `attachment`

A list or dictionary of information requested by the frontend.

### Failed actions

Key: `failed`

A list of messages of failed sub-actions during a batch action such as `lib scan`.