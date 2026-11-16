from dependency_injector import containers, providers
from manager.monitor import Monitor
from manager.command import Command
from manager.accessor import Accessor
from manager.storage import Storage
from manager.snapshot import Snapshot
from manager.checkpointer import Checkpointer

class Container(containers.DeclarativeContainer):

    monitor = providers.Singleton(Monitor)
    
    accessor = providers.Factory(Accessor, monitor)
    storage = providers.Factory(Storage, monitor)
    checkpointer = providers.Factory(Checkpointer, monitor, storage)
    snapshot = providers.Factory(Snapshot, monitor, accessor, storage, checkpointer)
    command = providers.Factory(Command, monitor, accessor, storage)
