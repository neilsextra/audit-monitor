from dependency_injector import containers, providers
from manager.monitor import Monitor
from manager.command import Command
from manager.storage import Storage
from manager.executor import Executor
from manager.checkpointer import Checkpointer

class Container(containers.DeclarativeContainer):

    monitor = providers.Singleton(Monitor)
    
    command = providers.Factory(Command, monitor)
    storage = providers.Factory(Storage, monitor)
    checkpointer = providers.Factory(Checkpointer, monitor, storage)
    executor = providers.Factory(Executor, monitor, command, storage, checkpointer)
