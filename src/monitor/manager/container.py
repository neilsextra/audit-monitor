from dependency_injector import containers, providers
from manager.monitor import Monitor
from manager.command import Command
from manager.storage import Storage
from manager.executor import Executor

class Container(containers.DeclarativeContainer):

    monitor = providers.Singleton(Monitor)
    
    command = providers.Factory(Command, monitor)
    storage = providers.Factory(Storage, monitor)

    executor = providers.Factory(Executor, monitor, command, storage)
