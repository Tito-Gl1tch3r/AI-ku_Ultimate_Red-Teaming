using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Reflection;

namespace Simbad.Platform.Core.Events
{
    internal sealed class SimpleSynchronousEventDispatcher : IEventDispatcher
    {
        private static readonly ConcurrentDictionary<Type, MethodInfo> _cachedHandleMethods = new ConcurrentDictionary<Type, MethodInfo>();

        public void Dispatch(IEvent @event)
        {
            var handlerInterfaceType = typeof(IEventHandler<>).MakeGenericType(@event.GetType());
            var enumerableInterface = typeof(IEnumerable<>).MakeGenericType(handlerInterfaceType);

            var handlers = Global.Ioc.Resolver.ResolveMany(enumerableInterface);
            foreach (var handler in handlers)
            {
                var handlerType = handler.GetType();
                var handleMethod = _cachedHandleMethods.GetOrAdd(handlerType, type => type.GetMethod(nameof(IEventHandler<IEvent>.Handle)));
                handleMethod.Invoke(handler, new object[] { @event });
            }            
        }
    }
}