using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using Simbad.Platform.Core;
using Simbad.Platform.Core.Events;
using Simbad.Platform.Core.Substance.Registration;
using Simbad.Platform.Persistence.Storage;

namespace Simbad.Platform.Persistence.Transactions
{
    public sealed class UnitOfWork : IUnitOfWork
    {
        private readonly ICollection<UowAction> _actions = new List<UowAction>();

        private readonly object _syncRoot = new object();

        private readonly IStorageAdapter _storageAdapter;

        private List<IEvent> _events = new List<IEvent>();

        private readonly IEventDispatcher _dispatcher;

        public UnitOfWork()
        {
            _storageAdapter = Global.Ioc.Resolver.Resolve<IStorageAdapter>();
            _dispatcher = Global.Ioc.Resolver.Resolve<IEventDispatcher>();
        }

        public void Commit()
        {
            lock (_syncRoot)
            {
                var events = _events;

                Thread.MemoryBarrier();
                _events = new List<IEvent>();

                foreach (var @event in events)
                {
                    _dispatcher.Dispatch(@event);
                }

                ApplyActions();
            }
        }

        public void TrackEvents(ICollection<IEvent> events)
        {
            lock (_syncRoot)
            {
                _events.AddRange(events);
            }
        }

        private void ApplyActions()
        {
            lock (_syncRoot)
            {
                var actionsCopy = _actions.OrderBy(x => x.ActionType).ToList();
                _actions.Clear();

                _storageAdapter.Transaction(
                    tw =>
                    {
                        foreach (var uowAction in actionsCopy)
                        {
                            ApplyAction(uowAction, tw);
                        }
                    });
            }
        }

        private static void ApplyAction(UowAction action, ITransactionWrapper transaction)
        {
            switch (action.ActionType)
            {
                case UowActionType.Save:
                    transaction.Save(action.Dao, action.BusinessObjectType);
                    break;
                case UowActionType.DeleteAll:
                    transaction.DeleteAll(action.BusinessObjectType);
                    break;
                case UowActionType.Delete:
                    transaction.Delete(action.Id, action.BusinessObjectType);
                    break;
                default:
                    throw new ArgumentOutOfRangeException();
            }
        }

        public void Save(object dao, Type type)
        {
            // todo [kk]: check that type is derived from PersistenceModel

            lock (_syncRoot)
            {
                _actions.Add(new UowAction
                {
                    ActionType = UowActionType.Save,
                    Dao = dao as Dao,
                    BusinessObjectType = type,
                });
            }
        }

        public void Delete(Guid id, Type type)
        {
            lock (_syncRoot)
            {
                _actions.Add(new UowAction
                {
                    ActionType = UowActionType.Delete,
                    BusinessObjectType = type,
                    Id = id,
                });
            }
        }

        public void DeleteAll(Type type)
        {
            lock (_syncRoot)
            {
                _actions.Add(new UowAction
                {
                    ActionType = UowActionType.DeleteAll,
                    BusinessObjectType = type,
                });
            }
        }

        private enum UowActionType
        {
            Save = 0,
            DeleteAll = 1,
            Delete = 2,
        }

        private sealed class UowAction
        {
            public Dao Dao { get; set; }

            public UowActionType ActionType { get; set; }

            public Type BusinessObjectType { get; set; }

            public Guid Id { get; set; }
        }
    }
}