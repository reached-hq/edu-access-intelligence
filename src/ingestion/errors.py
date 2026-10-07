"""One error type for every way a delivery can be refused.

`stage` says where it stopped (recorded as `failure_stage` in the control
tables) and `code` is a stable name a test or an operator can match on. The
message says what to do next. It never contains row values.
"""

# Exit codes for the command line. A refused batch and a broken setup need
# different responses, so they get different codes.
EXIT_OK = 0
EXIT_BATCH_FAILED = 1
EXIT_CONFIG_ERROR = 2
EXIT_ENVIRONMENT_ERROR = 3


class IngestionError(Exception):
    def __init__(self, stage, code, message):
        super().__init__(f"[{stage}/{code}] {message}")
        self.stage = stage
        self.code = code
        self.message = message
