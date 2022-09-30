from enum import Enum


class RegistrationState(Enum):
    FINISHED = "finished"
    FAILED = "failed"
    ACTION = "action"
    WAIT = "wait"
