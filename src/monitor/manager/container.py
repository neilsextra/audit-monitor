from dependency_injector import containers, providers
from manager.monitor import Monitor
from manager.command import Command
from manager.connector import Connector
from manager.storage import Storage
from manager.executor import Executor
from manager.checkpointer import Checkpointer

class Container(containers.DeclarativeContainer):

    monitor = providers.Singleton(Monitor)
    
    connector = providers.Factory(Connector, monitor)
    storage = providers.Factory(Storage, monitor)
    checkpointer = providers.Factory(Checkpointer, monitor, storage)
    executor = providers.Factory(Executor, monitor, connector, storage, checkpointer)
    command = providers.Factory(Command, monitor, connector, storage)
